"""Роутер для управления настройками уведомлений и обработки событий уведомлений."""

from typing import List, Dict
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from notifications_service import send_email_message, update_order_status, send_notification_to_rabbit

from models import NotificationSetting
from schemas import NotificationSettingCreate, NotificationSettingUpdate, NotificationSettingResponse, NotificationEvent, UserNotificationActivation
from database import get_db
from auth import require_user, require_admin, verify_service_jwt, User
from cache import (
    cache_get_settings, cache_set_settings, 
    invalidate_settings_cache
)

logger = logging.getLogger("notifications_service.settings_router")

router = APIRouter()

# Типы событий
EVENT_TYPE_REVIEW_CREATED = "review.created"
EVENT_TYPE_REVIEW_REPLY = "review.reply"
EVENT_TYPE_SERVICE_ERROR = "service.critical_error"
EVENT_TYPE_ORDER_CREATED = "order.created"
EVENT_TYPE_ORDER_STATUS_CHANGED = "order.status_changed"
EVENT_TYPE_PRODUCT_LOW_STOCK = "product.low_stock"

# События, доступные только для администраторов
ADMIN_ONLY_EVENT_TYPES = [
    EVENT_TYPE_REVIEW_CREATED,
]

# События, доступные для обычных пользователей
USER_EVENT_TYPES = [
    EVENT_TYPE_REVIEW_REPLY,
    EVENT_TYPE_ORDER_CREATED,
    EVENT_TYPE_ORDER_STATUS_CHANGED,
]

# Маппинг event_type -> название на русском
EVENT_TYPE_LABELS = {
    "review.created": "Новый отзыв на товар",
    "review.reply": "Ответ на ваш отзыв",
    "service.critical_error": "Критическая ошибка сервиса",
    "order.created": "Создание заказа",
    "order.status_changed": "Изменение статуса заказа",
    "product.low_stock": "Низкий остаток товара"
}

@router.get("/settings", response_model=List[NotificationSettingResponse])
async def get_settings(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    """Получение настроек уведомлений пользователя."""
    logger.info("[GET /settings] user_id=%s", user.id)
    user_id = user.id
    
    # Попытка получить настройки из кеша
    cached = await cache_get_settings(user_id)
    if cached is not None:
        logger.info("[GET /settings] cache hit user_id=%s", user_id)
        # Добавляем event_type_label, если его нет (для старого кэша)
        for s in cached:
            if "event_type_label" not in s:
                s["event_type_label"] = EVENT_TYPE_LABELS.get(s["event_type"], s["event_type"])
        return cached
    
    # Определяем доступные типы событий на основе роли пользователя
    allowed_event_types = USER_EVENT_TYPES.copy()
    if user.is_admin or user.is_super_admin:
        allowed_event_types.extend(ADMIN_ONLY_EVENT_TYPES)
    
    logger.debug("Allowed event types for user %s: %s", user_id, allowed_event_types)
        
    result = await db.execute(
        select(NotificationSetting)
        .where(
            NotificationSetting.user_id == user_id, 
            NotificationSetting.event_type.in_(allowed_event_types)
        )
    )
    settings = result.scalars().all()
    
    # Если настроек вообще нет, создаем базовые
    if not settings:
        logger.info("No settings found for user %s, creating default settings", user_id)
        defaults = []
        for event_type in allowed_event_types:
            new_setting = NotificationSetting(
                user_id=user_id,
                event_type=event_type,
                email=user.email or f"user{user_id}@example.com",
                email_enabled=False,
                push_enabled=False
            )
            db.add(new_setting)
            defaults.append(new_setting)
        
        try:
            await db.commit()
            for setting in defaults:
                await db.refresh(setting)
            # Кэшируем созданные настройки
            data = [
                {
                    **NotificationSettingResponse.model_validate(s).model_dump(),
                    "event_type_label": EVENT_TYPE_LABELS.get(s.event_type, s.event_type)
                }
                for s in defaults
            ]
            await cache_set_settings(user_id, data)
            return data
        except (IntegrityError, SQLAlchemyError) as e:
            logger.error("Error creating default settings: %s", str(e))
            await db.rollback()
            # Даже если не удалось сохранить, вернем временные объекты
            return defaults
    
    # Кэшируем существующие настройки
    data = [
        {
            **NotificationSettingResponse.model_validate(s).model_dump(),
            "event_type_label": EVENT_TYPE_LABELS.get(s.event_type, s.event_type)
        }
        for s in settings
    ]
    await cache_set_settings(user_id, data)
    return data

# Новый эндпоинт для проверки настроек пользователя
@router.get(
    "/settings/check/{user_id}/{event_type}",
    response_model=Dict[str, bool],
    dependencies=[Depends(verify_service_jwt)]
)
async def check_settings(
    user_id: int, 
    event_type: str,
    db: AsyncSession = Depends(get_db)
):
    """Проверка настроек уведомлений для указанного пользователя и типа события."""
    logger.info("[GET /settings/check] user_id=%s, event_type=%s", user_id, event_type)
    # Попытка использовать закэшированные настройки
    cached = await cache_get_settings(int(user_id))
    if cached is not None:
        logger.info("[GET /settings/check] cache hit user_id=%s", user_id)
        for s in cached:
            if s.get("event_type") == event_type:
                return {"email_enabled": s.get("email_enabled", False), "push_enabled": s.get("push_enabled", False)}
        return {"email_enabled": False, "push_enabled": False}
    # Не в кэше, получаем из БД и обновляем полный кэш
    result = await db.execute(
        select(NotificationSetting)
        .where(NotificationSetting.user_id == user_id)
    )
    all_settings = result.scalars().all()
    # Формируем кэш
    data = [
        {
            **NotificationSettingResponse.model_validate(s).model_dump(),
            "event_type_label": EVENT_TYPE_LABELS.get(s.event_type, s.event_type)
        }
        for s in all_settings
    ]
    await cache_set_settings(int(user_id), data)
    # Поиск нужного события
    setting = next((s for s in all_settings if s.event_type == event_type), None)
    if not setting:
        return {"email_enabled": False, "push_enabled": False}
    return {"email_enabled": setting.email_enabled, "push_enabled": setting.push_enabled}


@router.post("/settings/events", dependencies=[Depends(verify_service_jwt)])
async def receive_notification(event: NotificationEvent, db: AsyncSession = Depends(get_db)):
    """Обработка входящих событий уведомлений."""
    logger.info("[POST /settings/events] event_type=%s, user_id=%s", event.event_type, event.user_id)
    
    # Если это событие о низком остатке товаров
    if event.event_type == EVENT_TYPE_PRODUCT_LOW_STOCK:
        if event.low_stock_products:
            logger.info("Получено уведомление о низком остатке товаров: %d товаров", len(event.low_stock_products))
            # Отправляем событие напрямую в очередь RabbitMQ для обработки
            await send_notification_to_rabbit({
                "low_stock_products": event.low_stock_products
            })
            return {"status": "success", "message": "Уведомление о низком остатке товаров отправлено в очередь"}
        else:
            logger.warning("Получено уведомление о низком остатке товаров без данных о товарах")
            return {"status": "error", "message": "Не предоставлены данные о товарах"}
    
    # Обрабатываем другие типы событий
    if event.user_id is not None:
        flags = await check_settings(event.user_id, event.event_type, db)
        if flags['email_enabled'] == True and event.event_type == 'order.created' and event.order_id:
            await send_email_message(event.order_id)
        elif flags['email_enabled'] == True and event.event_type == 'order.status_changed' and event.order_id:
            await update_order_status(event.order_id)
    elif event.user_id is None and event.order_id:
        if event.event_type == 'order.created':
            await send_email_message(event.order_id)
        elif event.event_type == 'order.status_changed':
            await update_order_status(event.order_id)
            
    return {"status": "success", "message": "Уведомление обработано"}


@router.post("/settings", response_model=NotificationSettingResponse)
async def create_setting(setting: NotificationSettingCreate, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    """Создание новой настройки уведомлений."""
    logger.info("[POST /settings] user_id=%s, payload=%s", user.id, setting.model_dump())
    
    # Проверяем, имеет ли пользователь право на настройку указанного типа события
    event_type = setting.event_type
    if event_type in ADMIN_ONLY_EVENT_TYPES and not (user.is_admin or user.is_super_admin):
        raise HTTPException(status_code=403, detail="You don't have permission to configure this notification type")
    
    data = setting.model_dump()
    data['user_id'] = user.id
    obj = NotificationSetting(**data)
    db.add(obj)
    try:
        await db.commit()
        await db.refresh(obj)
        # Инвалидируем и пересоздаем кэш настроек для пользователя
        await invalidate_settings_cache(user.id)
        # Читаем все настройки пользователя и кэшируем их
        result_all = await db.execute(
            select(NotificationSetting).where(NotificationSetting.user_id == user.id)
        )
        all_settings = result_all.scalars().all()
        data_all = [
            {
                **NotificationSettingResponse.model_validate(s).model_dump(),
                "event_type_label": EVENT_TYPE_LABELS.get(s.event_type, s.event_type)
            }
            for s in all_settings
        ]
        await cache_set_settings(user.id, data_all)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Setting already exists") from exc
    return obj

@router.patch("/settings", response_model=NotificationSettingResponse)
async def update_setting(event_type: str, update: NotificationSettingUpdate, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    """Обновление существующей настройки уведомлений."""
    logger.info("[PATCH /settings] user_id=%s, event_type=%s, update=%s", user.id, event_type, update.model_dump(exclude_none=True))
    
    # Проверяем, имеет ли пользователь право на настройку указанного типа события
    if event_type in ADMIN_ONLY_EVENT_TYPES and not (user.is_admin or user.is_super_admin):
        raise HTTPException(status_code=403, detail="You don't have permission to configure this notification type")
    
    user_id = user.id
    result = await db.execute(
        select(NotificationSetting)
        .where(NotificationSetting.user_id == user_id, NotificationSetting.event_type == event_type)
    )
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Setting not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    # Инвалидируем и пересоздаем кэш настроек для пользователя
    await invalidate_settings_cache(user.id)
    result_all = await db.execute(
        select(NotificationSetting).where(NotificationSetting.user_id == user.id)
    )
    all_settings = result_all.scalars().all()
    data_all = [
        {
            **NotificationSettingResponse.model_validate(s).model_dump(),
            "event_type_label": EVENT_TYPE_LABELS.get(s.event_type, s.event_type)
        }
        for s in all_settings
    ]
    await cache_set_settings(user.id, data_all)
    return obj

# --- Админские эндпоинты ---
@router.get(
    "/admin/settings",
    response_model=List[NotificationSettingResponse],
    dependencies=[Depends(require_admin)]
)
async def admin_get_all_settings(db: AsyncSession = Depends(get_db)):
    """Получение всех настроек уведомлений (только для администраторов)."""
    logger.info("[GET /admin/settings]")
    result = await db.execute(select(NotificationSetting))
    return result.scalars().all()

@router.delete(
    "/admin/settings/{user_id}/{event_type}",
    dependencies=[Depends(require_admin)]
)
async def admin_delete_setting(
    user_id: int,
    event_type: str,
    db: AsyncSession = Depends(get_db)
):
    """Удаление настройки уведомлений пользователя (только для администраторов)."""
    logger.info("[DELETE /admin/settings/%s/%s] user_id=%s, event_type=%s", user_id, event_type, user_id, event_type)
    result = await db.execute(
        select(NotificationSetting)
        .where(NotificationSetting.user_id == user_id,
               NotificationSetting.event_type == event_type)
    )
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Setting not found")
    await db.delete(obj)
    await db.commit()
    # Инвалидируем и пересоздаем кэш настроек пользователя
    await invalidate_settings_cache(user_id)
    result_all = await db.execute(
        select(NotificationSetting).where(NotificationSetting.user_id == user_id)
    )
    all_settings = result_all.scalars().all()
    data_all = [
        {
            **NotificationSettingResponse.model_validate(s).model_dump(),
            "event_type_label": EVENT_TYPE_LABELS.get(s.event_type, s.event_type)
        }
        for s in all_settings
    ]
    await cache_set_settings(user_id, data_all)
    return {"detail": "Deleted"}

@router.post(
    "/service/activate-notifications",
    dependencies=[Depends(verify_service_jwt)]
)
async def activate_user_notifications(
    data: UserNotificationActivation,
    db: AsyncSession = Depends(get_db)
):
    """
    Активация всех доступных уведомлений для пользователя.
    Может вызываться только из других сервисов с service token.
    
    Args:
        data: Данные для активации уведомлений
        db: Сессия базы данных
    
    Returns:
        Dict[str, Any]: Результат операции и количество активированных настроек
    """
    logger.info("[POST /service/activate-notifications] Получен запрос на активацию уведомлений: user_id=%s, email=%s, is_admin=%s", 
               data.user_id, data.email, data.is_admin)
    
    # Определяем доступные типы событий для пользователя
    event_types = USER_EVENT_TYPES.copy()
    
    if data.is_admin:
        event_types.extend(ADMIN_ONLY_EVENT_TYPES)
    
    logger.debug("Типы событий для активации: %s", event_types)
    
    activated_count = 0
    user_id = int(data.user_id)
    
    try:
        # Проверяем существующие настройки
        result = await db.execute(
            select(NotificationSetting)
            .where(NotificationSetting.user_id == user_id)
        )
        existing_settings = {setting.event_type: setting for setting in result.scalars().all()}
        logger.debug("Найдено существующих настроек: %d", len(existing_settings))
        
        # Создаем или обновляем настройки для каждого типа события
        for event_type in event_types:
            if event_type in existing_settings:
                # Обновляем существующую настройку
                setting = existing_settings[event_type]
                if not setting.email_enabled:
                    setting.email_enabled = True
                    setting.email = data.email
                    activated_count += 1
                    logger.debug("Обновлена настройка: user_id=%s, event_type=%s", user_id, event_type)
            else:
                # Создаем новую настройку
                new_setting = NotificationSetting(
                    user_id=user_id,
                    event_type=event_type,
                    email=data.email,
                    email_enabled=True,
                    push_enabled=False
                )
                db.add(new_setting)
                activated_count += 1
                logger.debug("Создана новая настройка: user_id=%s, event_type=%s", user_id, event_type)
        
        # Сохраняем изменения
        await db.commit()
        logger.info("Изменения сохранены в БД. Активировано настроек: %d", activated_count)
        
        # Инвалидируем и обновляем кэш
        await invalidate_settings_cache(user_id)
        
        # Получаем обновленные настройки для обновления кэша
        result_all = await db.execute(
            select(NotificationSetting).where(NotificationSetting.user_id == user_id)
        )
        all_settings = result_all.scalars().all()
        data_all = [
            {
                **NotificationSettingResponse.model_validate(s).model_dump(),
                "event_type_label": EVENT_TYPE_LABELS.get(s.event_type, s.event_type)
            }
            for s in all_settings
        ]
        await cache_set_settings(user_id, data_all)
        logger.info("Кэш обновлен для user_id=%s", user_id)
        
        return {
            "status": "success",
            "message": f"Activated {activated_count} notification settings",
            "activated_count": activated_count
        }
    except Exception as e:
        logger.error("Ошибка при активации уведомлений: %s", str(e))
        await db.rollback()
        return {
            "status": "error",
            "message": f"Error activating notifications: {str(e)}",
            "activated_count": 0
        }
