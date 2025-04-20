from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
import logging
from .notifications_service import send_email_message

from . import models, schemas
from .database import get_db
from .auth import require_user, require_admin, verify_service_key, User

logger = logging.getLogger("notifications_service.settings_router")

router = APIRouter()

# Типы событий
EVENT_TYPE_REVIEW_CREATED = "review.created"
EVENT_TYPE_REVIEW_REPLY = "review.reply"
EVENT_TYPE_SERVICE_ERROR = "service.critical_error"
EVENT_TYPE_ORDER_CREATED = "order.created"
EVENT_TYPE_ORDER_STATUS_CHANGED = "order.status_changed"
EVENT_TYPE_ORDER_STATUS_CHANGE = "order.status_change"
EVENT_TYPE_PRODUCT_LOW_STOCK = "product.low_stock"

# События, доступные только для администраторов
ADMIN_ONLY_EVENT_TYPES = [
    EVENT_TYPE_REVIEW_CREATED,
    EVENT_TYPE_SERVICE_ERROR,
    EVENT_TYPE_PRODUCT_LOW_STOCK
]

# События, доступные для обычных пользователей
USER_EVENT_TYPES = [
    EVENT_TYPE_REVIEW_REPLY,
    EVENT_TYPE_ORDER_CREATED,
    EVENT_TYPE_ORDER_STATUS_CHANGED,
    EVENT_TYPE_ORDER_STATUS_CHANGE
]

@router.get("/settings", response_model=List[schemas.NotificationSettingResponse])
async def get_settings(user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    logger.info(f"[GET /settings] user_id={user.id}")
    user_id = str(user.id)
    
    # Определяем доступные типы событий на основе роли пользователя
    allowed_event_types = USER_EVENT_TYPES.copy()
    if user.is_admin or user.is_super_admin:
        allowed_event_types.extend(ADMIN_ONLY_EVENT_TYPES)
    
    logger.debug(f"Allowed event types for user {user_id}: {allowed_event_types}")
        
    result = await db.execute(
        select(models.NotificationSetting)
        .where(
            models.NotificationSetting.user_id == user_id, 
            models.NotificationSetting.event_type.in_(allowed_event_types)
        )
    )
    settings = result.scalars().all()
    
    # Если настроек вообще нет, создаем базовые
    if not settings:
        logger.info(f"No settings found for user {user_id}, creating default settings")
        defaults = []
        for event_type in allowed_event_types:
            new_setting = models.NotificationSetting(
                user_id=user_id,
                event_type=event_type,
                email=user.email or f"user{user_id}@example.com",
                email_enabled=True,
                push_enabled=True
            )
            db.add(new_setting)
            defaults.append(new_setting)
        
        try:
            await db.commit()
            for setting in defaults:
                await db.refresh(setting)
            return defaults
        except Exception as e:
            logger.error(f"Error creating default settings: {str(e)}")
            await db.rollback()
            # Даже если не удалось сохранить, вернем временные объекты
            return defaults
    
    return settings

# Новый эндпоинт для проверки настроек пользователя
@router.get(
    "/settings/check/{user_id}/{event_type}",
    response_model=Dict[str, bool],
    dependencies=[Depends(verify_service_key)]
)
async def check_settings(
    user_id: str, 
    event_type: str,
    db: AsyncSession = Depends(get_db)
):
    """Проверка настроек уведомлений для указанного пользователя и типа события"""
    logger.info(f"[GET /settings/check] user_id={user_id}, event_type={event_type}")
    
    # Обрабатываем специальный случай несоответствия между order.status_changed и order.status_change
    search_event_types = [event_type]
    if event_type == EVENT_TYPE_ORDER_STATUS_CHANGED:
        search_event_types.append(EVENT_TYPE_ORDER_STATUS_CHANGE)
    elif event_type == EVENT_TYPE_ORDER_STATUS_CHANGE:
        search_event_types.append(EVENT_TYPE_ORDER_STATUS_CHANGED)
    
    # Поиск настроек с учетом возможных вариантов имен события
    setting = None
    for search_event_type in search_event_types:
        result = await db.execute(
            select(models.NotificationSetting)
            .where(
                models.NotificationSetting.user_id == user_id,
                models.NotificationSetting.event_type == search_event_type
            )
        )
        setting = result.scalars().first()
        if setting:
            logger.info(f"[GET /settings/check] Found settings for {search_event_type}")
            break
    
    if not setting:
        # Возвращаем настройки по умолчанию, если не найдены
        return {"email_enabled": True, "push_enabled": True}
        
    return {
        "email_enabled": setting.email_enabled,
        "push_enabled": setting.push_enabled
    }


@router.post("/settings/events", dependencies=[Depends(verify_service_key)])
async def receive_notification(event: schemas.NotificationEvent, db: AsyncSession = Depends(get_db)):
    logger.info(f"[POST /settings/events] event_type={event.event_type}, user_id={event.user_id}, payload={event.payload}")
    flags = await check_settings(event.user_id, event.event_type, db)
    if flags['email_enabled']:
        if event.payload.get('email') and event.payload.get('user_id'):
            await send_email_message(event.payload)


@router.post("/settings", response_model=schemas.NotificationSettingResponse)
async def create_setting(setting: schemas.NotificationSettingCreate, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    logger.info(f"[POST /settings] user_id={user.id}, payload={setting.model_dump()}")
    
    # Проверяем, имеет ли пользователь право на настройку указанного типа события
    event_type = setting.event_type
    if event_type in ADMIN_ONLY_EVENT_TYPES and not (user.is_admin or user.is_super_admin):
        raise HTTPException(status_code=403, detail="You don't have permission to configure this notification type")
    
    data = setting.model_dump()
    data['user_id'] = str(user.id)
    obj = models.NotificationSetting(**data)
    db.add(obj)
    try:
        await db.commit()
        await db.refresh(obj)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Setting already exists")
    return obj

@router.patch("/settings", response_model=schemas.NotificationSettingResponse)
async def update_setting(event_type: str, update: schemas.NotificationSettingUpdate, user: User = Depends(require_user), db: AsyncSession = Depends(get_db)):
    logger.info(f"[PATCH /settings] user_id={user.id}, event_type={event_type}, update={update.model_dump(exclude_none=True)}")
    
    # Проверяем, имеет ли пользователь право на настройку указанного типа события
    if event_type in ADMIN_ONLY_EVENT_TYPES and not (user.is_admin or user.is_super_admin):
        raise HTTPException(status_code=403, detail="You don't have permission to configure this notification type")
    
    user_id = str(user.id)
    result = await db.execute(
        select(models.NotificationSetting)
        .where(models.NotificationSetting.user_id == user_id, models.NotificationSetting.event_type == event_type)
    )
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Setting not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.commit()
    await db.refresh(obj)
    return obj

# --- Админские эндпоинты ---
@router.get(
    "/admin/settings",
    response_model=List[schemas.NotificationSettingResponse],
    dependencies=[Depends(require_admin)]
)
async def admin_get_all_settings(db: AsyncSession = Depends(get_db)):
    logger.info("[GET /admin/settings]")
    """Просмотр всех настроек (только для админов)"""
    result = await db.execute(select(models.NotificationSetting))
    return result.scalars().all()

@router.delete(
    "/admin/settings/{user_id}/{event_type}",
    dependencies=[Depends(require_admin)]
)
async def admin_delete_setting(
    user_id: str,
    event_type: str,
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"[DELETE /admin/settings/{{user_id}}/{{event_type}}] user_id={user_id}, event_type={event_type}")
    """Удаление настройки пользователя (только для админов)"""
    result = await db.execute(
        select(models.NotificationSetting)
        .where(models.NotificationSetting.user_id == user_id,
               models.NotificationSetting.event_type == event_type)
    )
    obj = result.scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Setting not found")
    await db.delete(obj)
    await db.commit()
    return {"detail": "Deleted"} 