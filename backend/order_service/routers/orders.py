"""API эндпоинты сервиса заказов для пользователей.
Предоставляет интерфейсы как для авторизованных, так и для анонимных пользователей."""

import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db
from models import PromoCodeModel
from schemas import (
    OrderCreate, OrderResponse, OrderDetailResponse, 
    PaginatedResponse, OrderStatistics, PromoCodeResponse, 
    OrderResponseWithPromo, OrderDetailResponseWithPromo, OrderItemCreate
)
from services import (
    create_order, get_order_by_id, get_orders, 
    cancel_order, get_user_order_statistics
)
from dependencies import (
    get_current_user, get_order_filter_params,
    check_products_availability, get_products_info
)
from cache import (
    get_cached_order, cache_order, invalidate_order_cache,
    get_cached_user_orders, cache_user_orders,
    get_cached_order_statistics, cache_order_statistics, 
    CacheKeys, invalidate_statistics_cache
)
from notification_api import check_notification_settings

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger("order_router")

# Получение URL сервиса продуктов
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://localhost:8001")

# Создание роутера
router = APIRouter(
    prefix="/orders",
    tags=["orders"],
    responses={404: {"description": "Not found"}},
)

@router.post("", response_model=OrderResponseWithPromo, status_code=status.HTTP_201_CREATED)
async def create_new_order(
    order_data: OrderCreate,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Создание нового заказа. Доступно как для авторизованных, так и для анонимных пользователей.
    
    - **order_data**: Данные для создания заказа
    """
    try:
        logger.info("Получен запрос на создание заказа: %s", order_data)
        
        # Получаем ID пользователя из токена (если пользователь авторизован)
        user_id = current_user.get("user_id") if current_user else None
        
        # Получаем токен авторизации (если пользователь авторизован)
        token = current_user.get("token") if current_user else None
        
        # Проверяем наличие товаров
        product_ids = [item.product_id for item in order_data.items]
        availability = await check_products_availability(product_ids)
        
        # Проверяем, все ли товары доступны
        unavailable_products = [pid for pid, available in availability.items() if not available]
        if unavailable_products:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Товары с ID {unavailable_products} недоступны для заказа",
            )
            
        # Проверяем тип доставки
        if not order_data.delivery_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимо выбрать способ доставки",
            )
            
        # Для пунктов выдачи проверяем, что указан адрес пункта
        if order_data.delivery_type in ["boxberry_pickup_point", "cdek_pickup_point"] and not order_data.boxberry_point_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимо указать адрес пункта выдачи",
            )
        
        # Создаем заказ
        order = await create_order(
            session=session,
            user_id=user_id,
            order_data=order_data,
            product_service_url=PRODUCT_SERVICE_URL,
            token=token
        )
        
        # Если пользователь авторизован, очищаем его корзину
        # if user_id:
        #     try:
        #         await clear_user_cart(user_id)
        #     except Exception as e:
        #         logger.warning(f"Не удалось очистить корзину пользователя: {str(e)}")
        
        # Явно коммитим сессию, чтобы убедиться, что все связанные данные загружены
        await session.commit()
        
        # Вручную запрашиваем заказ со всеми связанными данными
        loaded_order = await get_order_by_id(session, order.id)
        
        # Если у заказа есть промокод, загружаем его
        if loaded_order.promo_code_id:
            # Загружаем промокод
            promo_code = await session.get(PromoCodeModel, loaded_order.promo_code_id)
            if promo_code:
                # Создаем словарь с данными промокода для передачи в RabbitMQ
                loaded_order.promo_code_dict = {
                    "code": promo_code.code,
                    "discount_percent": promo_code.discount_percent or 0
                }
                logger.info("Для нового заказа %s загружен промокод %s", loaded_order.id, promo_code.code)
        
        # Отправляем подтверждение заказа на email через Notifications Service
        try:
            # Проверяем, авторизован ли пользователь
            if user_id:
                # Для авторизованных пользователей всегда проверяем настройки уведомлений
                logger.info("Отправка уведомления о создании заказа для авторизованного пользователя: %s", user_id)
                await check_notification_settings(loaded_order.user_id, "order.created", loaded_order.id)
            else:
                # Для неавторизованных пользователей проверяем согласие на получение уведомлений
                if loaded_order.receive_notifications and loaded_order.email:
                    logger.info("Отправка уведомления о создании заказа для неавторизованного пользователя на email: %s", order_data.email)
                    # Для неавторизованных пользователей отправляем уведомление напрямую, без проверки настроек
                    # Здесь можно использовать другой метод для отправки, который не проверяет настройки пользователя
                    # Например, direct_notification_service или аналогичный
                    await check_notification_settings(None, "order.created", loaded_order.id)
                else:
                    logger.info("Уведомление о создании заказа не отправлено: неавторизованный пользователь не дал согласие или не указал email")
        except (ConnectionError, TimeoutError, ValueError) as e:
            logger.error("Ошибка при отправке email о заказе: %s", str(e))
        
        # Явно инвалидируем кэш заказов перед возвратом ответа
        await invalidate_order_cache(order.id)
        await invalidate_statistics_cache()  # Также инвалидируем кэш статистики и отчетов
        logger.info("Кэш заказа %s и связанных списков инвалидирован перед возвратом ответа", order.id)
        
        # Преобразуем модель в схему без промокода
        order_response = OrderResponse.model_validate(loaded_order)
        
        # Создаем расширенный ответ с возможностью добавления промокода
        response_with_promo = OrderResponseWithPromo(**order_response.model_dump())
        
        # Если у заказа есть промокод, загружаем его данные вручную
        if loaded_order.promo_code_id:
            try:
                promo_code = await session.get(PromoCodeModel, loaded_order.promo_code_id)
                if promo_code:
                    response_with_promo.promo_code = PromoCodeResponse.model_validate(promo_code)
                    logger.info("Для нового заказа %s загружен промокод %s", loaded_order.id, promo_code.code)
            except (ValueError, AttributeError, KeyError) as e:
                logger.warning("Не удалось загрузить промокод %s для заказа %s: %s", loaded_order.promo_code_id, loaded_order.id, str(e))
        
        # Кэшируем результат в любом случае, но с разными ключами
        cache_key = f"{CacheKeys.ORDER_PREFIX}{order.id}"
        if user_id:
            # Для авторизованных пользователей - отдельный кэш
            cache_key = f"{CacheKeys.ORDER_PREFIX}{order.id}:user:{user_id}"
        
        await cache_order(order.id, response_with_promo, cache_key=cache_key)
        logger.info("Данные о заказе %s добавлены в кэш с ключом %s", order.id, cache_key)
        
        return response_with_promo
    except ValueError as e:
        logger.error("Ошибка при создании заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error("Непредвиденная ошибка при создании заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании заказа",
        ) from e

@router.get("", response_model=PaginatedResponse)
async def list_my_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status_id: Optional[int] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение списка заказов текущего пользователя.
    
    - **page**: Номер страницы
    - **size**: Размер страницы
    - **status_id**: ID статуса заказа
    """
    # Проверяем, авторизован ли пользователь
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Для просмотра заказов необходима авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        
        # Создаем параметры фильтрации
        filters = get_order_filter_params(
            page=page,
            size=size,
            status_id=status_id,
            user_id=user_id
        )
        
        # Создаем ключ для кэша на основе параметров фильтрации
        cache_key = f"p{page}_s{size}_st{status_id or 'all'}"
        
        # Пытаемся получить данные из кэша
        cached_orders = await get_cached_user_orders(user_id, cache_key)
        if cached_orders:
            logger.info("Данные о заказах пользователя %s получены из кэша", user_id)
            return cached_orders
        
        # Если данных нет в кэше, получаем из БД
        orders, total = await get_orders(
            session=session,
            filters=filters,
            user_id=user_id
        )
        
        # Формируем ответ с преобразованием моделей в схемы
        order_responses = []
        for order in orders:
            # Создаем базовый объект OrderResponse без промокода
            order_response = OrderResponse.model_validate(order)
            
            # Если у заказа есть промокод, создаем OrderResponseWithPromo
            if order.promo_code_id:
                # Создаем расширенный ответ с информацией о промокоде
                with_promo = OrderResponseWithPromo(**order_response.model_dump())
                
                try:
                    # Получаем промокод и устанавливаем его
                    promo_code = await session.get(PromoCodeModel, order.promo_code_id)
                    if promo_code:
                        with_promo.promo_code = PromoCodeResponse.model_validate(promo_code)
                        logger.info("Для заказа %s загружен промокод %s", order.id, promo_code.code)
                except (ValueError, AttributeError, KeyError) as e:
                    logger.warning("Не удалось загрузить промокод %s для заказа %s: %s", order.promo_code_id, order.id, str(e))
                
                order_responses.append(with_promo)
            else:
                # Заказ без промокода, используем обычный OrderResponse
                order_responses.append(order_response)
        
        response = PaginatedResponse(
            items=order_responses,
            total=total,
            page=filters.page,
            size=filters.size,
            pages=0  # Будет вычислено в валидаторе
        )
        
        # Кэшируем результат
        await cache_user_orders(user_id, cache_key, response)
        logger.info("Данные о заказах пользователя %s добавлены в кэш", user_id)
        
        return response
    except Exception as e:
        logger.error("Ошибка при получении списка заказов пользователя: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка заказов",
        ) from e

@router.get("/statistics", response_model=OrderStatistics)
async def get_user_statistics(
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение статистики по заказам текущего пользователя
    """
    # Проверяем, авторизован ли пользователь
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Для получения статистики необходима авторизация",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id = current_user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не удалось определить пользователя"
        )
    
    try:
        # Пытаемся получить данные из кэша
        cached_statistics = await get_cached_order_statistics(user_id)
        if cached_statistics:
            logger.info("Статистика заказов пользователя %s получена из кэша", user_id)
            return cached_statistics
        
        # Если данных нет в кэше, получаем из БД
        statistics = await get_user_order_statistics(session, user_id)
        
        # Кэшируем результат
        await cache_order_statistics(statistics, user_id)
        logger.info("Статистика заказов пользователя %s добавлена в кэш", user_id)
        
        return statistics
    except Exception as e:
        logger.error("Ошибка при получении статистики заказов пользователя: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики заказов"
        ) from e

@router.get("/{order_id}", response_model=OrderDetailResponseWithPromo)
async def get_order(
    order_id: int = Path(..., ge=1),
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение информации о заказе пользователя по ID.
    
    - **order_id**: ID заказа
    """
    try:
        # Проверяем, авторизован ли пользователь
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Для просмотра заказа необходима авторизация",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Определяем пользователя
        user_id = current_user["user_id"]
        
        # Пытаемся получить данные из кэша
        cached_order = await get_cached_order(order_id, user_id)
        if cached_order:
            logger.info("Данные о заказе %s получены из кэша для пользователя %s", order_id, user_id)
            return cached_order
            
        # Получаем заказ
        order = await get_order_by_id(
            session=session,
            order_id=order_id,
            user_id=user_id
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )
        
        # Преобразуем модель в схему без промокода
        order_response = OrderDetailResponse.model_validate(order)
        
        # Создаем расширенный ответ с возможностью добавления промокода
        response_with_promo = OrderDetailResponseWithPromo(**order_response.model_dump())
        
        # Вручную обрабатываем промокод
        if order.promo_code_id:
            try:
                promo_code = await session.get(PromoCodeModel, order.promo_code_id)
                if promo_code:
                    response_with_promo.promo_code = PromoCodeResponse.model_validate(promo_code)
                    logger.info("Для заказа %s загружен промокод %s", order.id, promo_code.code)
            except (ValueError, AttributeError, KeyError) as e:
                logger.warning("Не удалось загрузить промокод %s для заказа %s: %s", order.promo_code_id, order.id, str(e))
        
        # Кэшируем результат
        cache_key = f"{CacheKeys.ORDER_PREFIX}{order_id}"
        if user_id:
            cache_key = f"{CacheKeys.ORDER_PREFIX}{order_id}:user:{user_id}"
            
        await cache_order(order_id, response_with_promo, cache_key=cache_key)
        logger.info("Данные о заказе %s добавлены в кэш с ключом %s", order_id, cache_key)
        
        return response_with_promo
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при получении информации о заказе: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении информации о заказе",
        ) from e

@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order_endpoint(
    order_id: int = Path(..., ge=1),
    cancel_reason: Optional[str] = None,
    current_user: Optional[Dict[str, Any]] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Отмена заказа пользователем. Заказ можно отменить только если его статус позволяет отмену.
    
    - **order_id**: ID заказа
    - **cancel_reason**: Причина отмены
    """
    try:
        # Проверяем, авторизован ли пользователь
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Для отмены заказа необходима авторизация",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Отменяем заказ
        order = await cancel_order(
            session=session,
            order_id=order_id,
            user_id=user_id,
            is_admin=is_admin,
            cancel_reason=cancel_reason
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )
        
        # Коммитим сессию
        await session.commit()
        
        # Вручную запрашиваем заказ со всеми связанными данными
        loaded_order = await get_order_by_id(session, order.id)
        
        # Инвалидируем кэш заказа
        await invalidate_order_cache(order_id)
        # Инвалидируем кэш статистики
        await invalidate_statistics_cache()
        logger.info("Кэш заказа %s и статистики инвалидирован после отмены заказа", order_id)
        
        # Преобразуем модель в схему
        return OrderResponse.model_validate(loaded_order)
    except ValueError as e:
        logger.error("Ошибка при отмене заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Непредвиденная ошибка при отмене заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при отмене заказа",
        ) from e

@router.post("/{order_id}/reorder", status_code=status.HTTP_201_CREATED)
async def reorder_endpoint(
    order_id: int = Path(..., ge=1),
    personal_data_agreement: bool = Body(..., embed=True, description="Согласие на обработку персональных данных"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Повторение заказа - создание нового заказа с теми же товарами.
    
    - **order_id**: ID заказа для повторения
    """
    try:
        # Проверяем авторизацию пользователя
        if not current_user or not current_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Для повторения заказа необходимо авторизоваться"
            )
        # Проверяем согласие на обработку персональных данных
        if not personal_data_agreement:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для повторения заказа необходимо согласие на обработку персональных данных"
            )
        
        user_id = current_user.get("user_id")
        token = current_user.get("token")
        
        # Получаем исходный заказ по ID
        original_order = await get_order_by_id(session, order_id)
        if not original_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден"
            )
        
        # Проверяем, принадлежит ли заказ текущему пользователю
        if original_order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет прав для повторения этого заказа"
            )
        
        # Получаем список товаров из заказа
        items = []
        product_ids = []
        for item in original_order.items:
            items.append({
                "product_id": item.product_id,
                "quantity": item.quantity
            })
            product_ids.append(item.product_id)
        
        # Проверяем доступность товаров
        availability = await check_products_availability(product_ids)
        
        # Проверяем, все ли товары доступны
        unavailable_products = [pid for pid, available in availability.items() if not available]
        if unavailable_products:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Товары с ID {unavailable_products} больше недоступны для заказа"
            )
        
        # Получаем информацию о товарах
        products_info = await get_products_info(product_ids, token)
        
        # Преобразуем товары в формат для создания заказа
        order_items = []
        for item in original_order.items:
            order_items.append(OrderItemCreate(
                product_id=item.product_id,
                quantity=item.quantity
            ))
        
        # Создаем данные для нового заказа, сохраняя настройки доставки
        new_order_data = OrderCreate(
            full_name=original_order.full_name,
            email=original_order.email,
            phone=original_order.phone,
            delivery_address=original_order.delivery_address,
            comment=f"Повторный заказ на основе заказа #{original_order.id}",
            personal_data_agreement=personal_data_agreement,
            items=order_items,
            delivery_type=original_order.delivery_type,
            boxberry_point_address=original_order.boxberry_point_address
        )
        
        # Проверяем тип доставки
        if not new_order_data.delivery_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимо выбрать способ доставки"
            )
        
        # Для пунктов выдачи проверяем, что указан адрес пункта
        if new_order_data.delivery_type in ["boxberry_pickup_point", "cdek_pickup_point"] and not new_order_data.boxberry_point_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимо указать адрес пункта выдачи"
            )
        
        # Создаем новый заказ
        new_order = await create_order(
            session=session,
            user_id=user_id,
            order_data=new_order_data,
            product_service_url=PRODUCT_SERVICE_URL,
            token=token
        )
        
        # Коммитим сессию
        await session.commit()
        
        # Получаем созданный заказ
        created_order = await get_order_by_id(session, new_order.id)
        
        # Возвращаем информацию о созданном заказе
        response_data = OrderResponse.model_validate(created_order)
        return {
            "success": True,
            "message": "Заказ успешно повторен",
            "order": response_data,
            "order_id": new_order.id
        }
    except HTTPException:
        raise
    except ValueError as e:
        logger.error("Ошибка при повторении заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error("Непредвиденная ошибка при повторении заказа: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при повторении заказа"
        ) from e

@router.post("/check-can-review", status_code=status.HTTP_200_OK)
async def check_can_review(
    request_data: Dict[str, Any] = Body(...),
    session: AsyncSession = Depends(get_db)
):
    """
    Проверка, может ли пользователь оставить отзыв на товар
    (заказал товар и заказ доставлен)
    """
    try:
        user_id = request_data.get("user_id")
        product_id = request_data.get("product_id")
        
        if not user_id or not product_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимо указать user_id и product_id"
            )
        
        # Проверяем, есть ли завершенные заказы с этим товаром у пользователя
        query = text("""
            SELECT COUNT(*) FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            WHERE o.user_id = :user_id 
            AND oi.product_id = :product_id
            AND o.status_id = 5
        """)
        
        result = await session.execute(
            query, 
            {"user_id": user_id, "product_id": product_id}
        )
        count = result.scalar_one()
        
        return {"can_review": count > 0}
    except Exception as e:
        logger.error("Ошибка при проверке возможности оставить отзыв: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке возможности оставить отзыв"
        ) from e

@router.post("/check-can-review-store", status_code=status.HTTP_200_OK)
async def check_can_review_store(
    request_data: Dict[str, Any] = Body(...),
    session: AsyncSession = Depends(get_db)
):
    """
    Проверка, может ли пользователь оставить отзыв на магазин
    (имеет хотя бы один завершенный заказ)
    """
    try:
        user_id = request_data.get("user_id")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Необходимо указать user_id"
            )
        
        # Проверяем, есть ли завершенные заказы у пользователя
        query = text("""
            SELECT COUNT(*) FROM orders o
            WHERE o.user_id = :user_id 
            AND o.status_id = 5
        """)
        
        result = await session.execute(query, {"user_id": user_id})
        count = result.scalar_one()
        
        return {"can_review": count > 0}
    except Exception as e:
        logger.error("Ошибка при проверке возможности оставить отзыв на магазин: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке возможности оставить отзыв на магазин"
        ) from e

@router.post("/{order_id}/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_notifications(
    order_id: int = Path(..., ge=1),
    email: str = Body(..., embed=True),
    session: AsyncSession = Depends(get_db)
):
    """
    Отменить подписку на уведомления по email для неавторизованного пользователя.
    
    - **order_id**: ID заказа
    - **email**: Email, указанный при создании заказа для подтверждения
    """
    try:
        # Получаем заказ
        order = await get_order_by_id(session, order_id)
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )
        
        # Проверяем принадлежность к пользователю
        if order.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Данный метод доступен только для заказов, созданных без регистрации",
            )
        
        # Проверяем email
        if order.email.lower() != email.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Указанный email не совпадает с email, указанным при создании заказа",
            )
        
        # Обновляем флаг получения уведомлений
        order.receive_notifications = False
        session.add(order)
        await session.commit()
        
        # Инвалидируем кэш заказа
        await invalidate_order_cache(order_id)
        logger.info("Кэш заказа %s инвалидирован после отмены подписки на уведомления", order_id)
        
        return {
            "success": True,
            "message": "Вы успешно отписались от уведомлений о заказе"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Ошибка при отмене подписки на уведомления: %s", str(e))
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при отмене подписки на уведомления",
        ) from e