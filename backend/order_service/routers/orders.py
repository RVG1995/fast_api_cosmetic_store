import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import os
from dotenv import load_dotenv
from datetime import datetime
import hashlib
import sys
from notification_api import check_notification_settings
from fastapi.encoders import jsonable_encoder

from database import get_db
from models import OrderModel, OrderStatusModel, OrderStatusHistoryModel, PromoCodeModel
from schemas import (
    OrderCreate, OrderUpdate, OrderResponse, OrderDetailResponse, 
    OrderStatusHistoryCreate, PaginatedResponse, OrderStatistics, BatchStatusUpdate,
    OrderItemsUpdate, OrderItemsUpdateResponse, PromoCodeResponse, OrderResponseWithPromo, OrderDetailResponseWithPromo
)
from services import (
    create_order, get_order_by_id, get_orders, update_order, 
    change_order_status, cancel_order, get_order_statistics, get_user_order_statistics,
    update_order_items
)
from dependencies import (
    get_current_user, get_admin_user, get_order_filter_params,
    check_products_availability, get_products_info, clear_user_cart
)
from auth import User
from cache import (
    get_cached_order, cache_order, invalidate_order_cache,
    get_cached_user_orders, cache_user_orders,
    get_cached_order_statistics, cache_order_statistics, invalidate_statistics_cache,
    get_cached_orders_list, cache_orders_list, invalidate_cache, CacheKeys, invalidate_user_orders_cache
)

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

# Создание роутера для админ-панели
admin_router = APIRouter(
    prefix="/admin/orders",
    tags=["admin_orders"],
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
        logger.info(f"Получен запрос на создание заказа: {order_data}")
        
        # Получаем ID пользователя из токена (если пользователь авторизован)
        user_id = current_user.get("user_id") if current_user else None
        
        # Получаем токен авторизации (если пользователь авторизован)
        token = current_user.get("token") if current_user else None
        
        # Проверяем наличие товаров
        product_ids = [item.product_id for item in order_data.items]
        availability = await check_products_availability(product_ids, token)
        
        # Проверяем, все ли товары доступны
        unavailable_products = [pid for pid, available in availability.items() if not available]
        if unavailable_products:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Товары с ID {unavailable_products} недоступны для заказа",
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
                logger.info(f"Для нового заказа {loaded_order.id} загружен промокод {promo_code.code}")
        
        # Отправляем подтверждение заказа на email через Notifications Service
        try:
            if order_data.email and user_id != None:
                logger.info(f"Отправка подтверждения заказа на email: {order_data.email}")
                # CONVERT loaded_order to plain dict for JSON payload
                payload = jsonable_encoder(loaded_order)
                await check_notification_settings(loaded_order.user_id, "order.created", payload)
        except Exception as e:
            logger.error(f"Ошибка при отправке email о заказе: {str(e)}")
        
        # Явно инвалидируем кэш заказов перед возвратом ответа
        await invalidate_order_cache(order.id)
        logger.info(f"Кэш заказа {order.id} и связанных списков инвалидирован перед возвратом ответа")
        
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
                    logger.info(f"Для нового заказа {loaded_order.id} загружен промокод {promo_code.code}")
            except Exception as e:
                logger.warning(f"Не удалось загрузить промокод {loaded_order.promo_code_id} для заказа {loaded_order.id}: {str(e)}")
        
        return response_with_promo
    except ValueError as e:
        logger.error(f"Ошибка при создании заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при создании заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании заказа",
        )

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
            logger.info(f"Данные о заказах пользователя {user_id} получены из кэша")
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
                        logger.info(f"Для заказа {order.id} загружен промокод {promo_code.code}")
                except Exception as e:
                    logger.warning(f"Не удалось загрузить промокод {order.promo_code_id} для заказа {order.id}: {str(e)}")
                
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
        logger.info(f"Данные о заказах пользователя {user_id} добавлены в кэш")
        
        return response
    except Exception as e:
        logger.error(f"Ошибка при получении списка заказов пользователя: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка заказов",
        )

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
            logger.info(f"Статистика заказов пользователя {user_id} получена из кэша")
            return cached_statistics
        
        # Если данных нет в кэше, получаем из БД
        statistics = await get_user_order_statistics(session, user_id)
        
        # Кэшируем результат
        await cache_order_statistics(statistics, user_id)
        logger.info(f"Статистика заказов пользователя {user_id} добавлена в кэш")
        
        return statistics
    except Exception as e:
        logger.error(f"Ошибка при получении статистики заказов пользователя: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики заказов"
        )

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
        user_id = None
        
        # Если запрос от внутреннего сервиса, разрешаем получение заказа без проверки user_id
        if current_user.get("is_service"):
            logger.info(f"Внутренний запрос от сервиса {current_user.get('service_name')} для заказа {order_id}")
            user_id = None  # None означает получение заказа без проверки принадлежности конкретному пользователю
        else:
            # Получаем ID пользователя из токена для обычных пользователей
            user_id = current_user["user_id"]
        
        # Пытаемся получить данные из кэша, если запрос не от сервиса
        # Для запросов от сервисов всегда получаем свежие данные
        if not current_user.get("is_service"):
            cached_order = await get_cached_order(order_id)
            if cached_order:
                # Проверка доступа пользователя к заказу
                if user_id and cached_order.user_id != user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"У вас нет доступа к заказу с ID {order_id}",
                    )
                logger.info(f"Данные о заказе {order_id} получены из кэша")
                return cached_order
            
        # Получаем заказ
        order = await get_order_by_id(
            session=session,
            order_id=order_id,
            user_id=user_id  # Если user_id=None и запрос от сервиса, то заказ будет получен без проверки пользователя
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
                    logger.info(f"Для заказа {order.id} загружен промокод {promo_code.code}")
            except Exception as e:
                logger.warning(f"Не удалось загрузить промокод {order.promo_code_id} для заказа {order.id}: {str(e)}")
        
        # Кэшируем результат, если запрос не от сервиса
        if not current_user.get("is_service"):
            await cache_order(order_id, response_with_promo)
            logger.info(f"Данные о заказе {order_id} добавлены в кэш")
        
        return response_with_promo
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о заказе: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении информации о заказе",
        )

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
        logger.info(f"Кэш заказа {order_id} и статистики инвалидирован после отмены заказа")
        
        # Преобразуем модель в схему
        return OrderResponse.model_validate(loaded_order)
    except ValueError as e:
        logger.error(f"Ошибка при отмене заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при отмене заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при отмене заказа",
        )

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
        availability = await check_products_availability(product_ids, token)
        
        # Проверяем, все ли товары доступны
        unavailable_products = [pid for pid, available in availability.items() if not available]
        if unavailable_products:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Товары с ID {unavailable_products} больше недоступны для заказа"
            )
        
        # Получаем информацию о товарах
        products_info = await get_products_info(product_ids, token)
        
        # Создаем новые данные для заказа на основе старого
        from schemas import OrderCreate, OrderItemCreate
        
        # Преобразуем товары в формат для создания заказа
        order_items = []
        for item in original_order.items:
            order_items.append(OrderItemCreate(
                product_id=item.product_id,
                quantity=item.quantity
            ))
        
        new_order_data = OrderCreate(
            full_name=original_order.full_name,
            email=original_order.email,
            phone=original_order.phone,
            region=original_order.region,
            city=original_order.city,
            street=original_order.street,
            comment=f"Повторный заказ на основе заказа #{original_order.id}",
            personal_data_agreement=personal_data_agreement,
            items=order_items
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
        logger.error(f"Ошибка при повторении заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при повторении заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при повторении заказа"
        )

# Административные маршруты
@admin_router.get("", response_model=PaginatedResponse)
async def list_all_orders(
    filters = Depends(get_order_filter_params),
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение списка всех заказов (только для администраторов).
    
    Поддерживает фильтрацию по различным параметрам.
    """
    try:
        # Создаем ключ для кэша на основе параметров фильтрации
        filter_params = filters.model_dump_json()
        cache_key = hashlib.md5(filter_params.encode()).hexdigest()
        
        # Пытаемся получить данные из кэша
        cached_orders = await get_cached_orders_list(cache_key)
        if cached_orders:
            logger.info(f"Данные о всех заказах получены из кэша по ключу {cache_key}")
            return cached_orders
        
        # Если данных нет в кэше, получаем из БД
        orders, total = await get_orders(
            session=session,
            filters=filters
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
                        logger.info(f"Для заказа {order.id} загружен промокод {promo_code.code} (в админ списке)")
                except Exception as e:
                    logger.warning(f"Не удалось загрузить промокод {order.promo_code_id} для заказа {order.id}: {str(e)}")
                
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
        await cache_orders_list(cache_key, response)
        logger.info(f"Данные о всех заказах добавлены в кэш по ключу {cache_key}")
        
        return response
    except Exception as e:
        logger.error(f"Ошибка при получении списка заказов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка заказов",
        )

@admin_router.get("/statistics", response_model=OrderStatistics)
async def get_admin_orders_statistics(
    session: AsyncSession = Depends(get_db),
    admin_user: Dict[str, Any] = Depends(get_admin_user)
):
    """
    Получение статистики по всем заказам (только для администраторов)
    """
    try:
        # Пытаемся получить данные из кэша
        cached_statistics = await get_cached_order_statistics()
        if cached_statistics:
            logger.info("Статистика всех заказов получена из кэша")
            return cached_statistics
        
        # Если данных нет в кэше, получаем из БД
        statistics = await get_order_statistics(session)
        
        # Кэшируем результат
        await cache_order_statistics(statistics)
        logger.info("Статистика всех заказов добавлена в кэш")
        
        return statistics
    except Exception as e:
        logger.error(f"Ошибка при получении статистики заказов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при получении статистики заказов"
        )

@admin_router.get("/{order_id}", response_model=OrderDetailResponseWithPromo)
async def get_order_admin(
    order_id: int = Path(..., ge=1),
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение информации о заказе по ID (только для администраторов)
    
    - **order_id**: ID заказа
    """
    try:
        # Пытаемся получить данные из кэша
        cached_order = await get_cached_order(order_id, admin=True)
        if cached_order:
            logger.info(f"Данные о заказе {order_id} получены из кэша (админ)")
            return cached_order
            
        # Получаем заказ
        order = await get_order_by_id(session, order_id)
        
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
                    logger.info(f"Для заказа {order.id} загружен промокод {promo_code.code} (админ)")
            except Exception as e:
                logger.warning(f"Не удалось загрузить промокод {order.promo_code_id} для заказа {order.id}: {str(e)}")
        
        # Кэшируем результат
        await cache_order(order_id, response_with_promo, admin=True)
        logger.info(f"Данные о заказе {order_id} добавлены в кэш (админ)")
        
        return response_with_promo
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о заказе (админ): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении информации о заказе",
        )

@admin_router.put("/{order_id}", response_model=OrderResponse)
async def update_order_admin(
    order_id: int = Path(..., ge=1),
    order_data: OrderUpdate = Body(...),
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Обновление информации о заказе (только для администраторов).
    
    - **order_id**: ID заказа
    - **order_data**: Данные для обновления
    """
    try:
        # Обновляем заказ
        order = await update_order(
            session=session,
            order_id=order_id,
            order_data=order_data
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )
        
        # Добавляем запись в историю статусов, если статус был изменен
        if order_data.status_id is not None:
            # Используем комментарий, если он предоставлен, иначе используем стандартное сообщение
            status_note = order_data.comment if order_data.comment else "Статус обновлен администратором"
            
            await OrderStatusHistoryModel.add_status_change(
                session=session,
                order_id=order.id,
                status_id=order_data.status_id,
                changed_by_user_id=current_user["user_id"],
                notes=status_note
            )
        
        # Коммитим сессию
        await session.commit()
        
        # Вручную запрашиваем заказ со всеми связанными данными
        loaded_order = await get_order_by_id(session, order.id)
        
        # Инвалидируем кэш заказа
        await invalidate_order_cache(order_id)
        # Инвалидируем кэш статистики, если изменился статус
        if order_data.status_id is not None:
            await invalidate_statistics_cache()
        logger.info(f"Кэш заказа {order_id} инвалидирован после обновления заказа")
        
        # Преобразуем модель в схему
        return OrderResponse.model_validate(loaded_order)
    except ValueError as e:
        logger.error(f"Ошибка при обновлении заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при обновлении заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при обновлении заказа",
        )

@admin_router.post("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int = Path(..., ge=1),
    status_data: dict = Body(...),
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Обновление статуса заказа (только для администраторов).
    Упрощенный эндпоинт для обновления только статуса.
    
    - **order_id**: ID заказа
    - **status_data**: Данные о новом статусе:
      - status_id: ID нового статуса
      - comment: Комментарий к изменению статуса (опционально)
    """
    try:
        logger.info(f"Запрос на обновление статуса заказа. ID: {order_id}, данные: {status_data}")
        
        # Проверяем наличие обязательного поля status_id
        if not status_data.get("status_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не указан ID статуса",
            )
        
        # Создаем объект OrderUpdate только с нужными полями
        status_id = status_data.get("status_id")
        comment = status_data.get("comment")
        
        # Проверяем, что статус существует
        status_name = await session.get(OrderStatusModel, status_id)
        if not status_name:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Статус с ID {status_id} не найден",
            )
        
        # Получаем текущий заказ
        order = await get_order_by_id(session, order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )
        
        # Обновляем статус заказа
        order.status_id = status_id
        session.add(order)
        
        # Добавляем запись в историю статусов
        status_note = comment if comment else "Статус обновлен администратором"
        await OrderStatusHistoryModel.add_status_change(
            session=session,
            order_id=order_id,
            status_id=status_id,
            changed_by_user_id=current_user["user_id"],
            notes=status_note
        )
        
        # Получаем информацию о новом статусе
        new_status = await session.get(OrderStatusModel, status_id)
        new_status_name = new_status.name if new_status else "Неизвестный"
        
        # Получаем информацию о старом статусе
        old_status = await session.get(OrderStatusModel, order.status_id)
        old_status_name = old_status.name if old_status else "Неизвестный"
        
        # Фиксируем изменения в базе данных
        await session.commit()
        
        # Инвалидируем кэш заказа
        await invalidate_order_cache(order_id)
        # Инвалидируем кэш статистики
        await invalidate_statistics_cache()
        logger.info(f"Кэш заказа {order_id} и статистики инвалидирован после изменения статуса с '{old_status_name}' на '{new_status_name}'")
        
        # Обновляем заказ в сессии
        updated_order = await get_order_by_id(session, order_id)

        # Если у заказа есть промокод, загружаем его ПЕРЕД отправкой уведомления
        if updated_order.promo_code_id:
            # Загружаем промокод
            promo_code = await session.get(PromoCodeModel, updated_order.promo_code_id)
            if promo_code:
                # Создаем словарь с данными промокода для передачи в RabbitMQ
                updated_order.promo_code_dict = {
                    "code": promo_code.code,
                    "discount_percent": promo_code.discount_percent or 0
                }
                logger.info(f"Для заказа {updated_order.id} загружен промокод {promo_code.code} (при обновлении статуса)")
        
        # Получаем токен авторизации из текущего пользователя
        token = current_user.get("token")
        
        # Отправляем уведомление об изменении статуса ПОСЛЕ того, как загрузили промокод
        try:
            from app.services.order_service import update_order_status
            if order.email:
                # Передаем токен для проверки настроек уведомлений
                result = await update_order_status(updated_order, new_status_name, token)
                if result:
                    logger.info(f"Отправка уведомления об изменении статуса заказа {order_id} с '{old_status_name}' на '{new_status_name}' на email: {order.email}")
                else:
                    logger.info(f"Уведомление об изменении статуса заказа {order_id} не отправлено (отключено в настройках)")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об изменении статуса: {str(e)}")
        
        return OrderResponse.model_validate(updated_order)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса заказа: {str(e)}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Произошла ошибка при обновлении статуса заказа: {str(e)}",
        )

@admin_router.post("/{order_id}/items", response_model=OrderItemsUpdateResponse)
async def update_order_items_endpoint(
    order_id: int,
    items_data: OrderItemsUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """Обновление товаров в заказе (админский доступ)"""
    logger = logging.getLogger("order_router")
    logger.info(f"Запрос на обновление элементов заказа {order_id}: items_to_add={items_data.items_to_add} items_to_update={items_data.items_to_update} items_to_remove={items_data.items_to_remove}")
    
    try:
        # Получаем текущий статус заказа
        order = await get_order_by_id(session, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        
        # Проверка статуса заказа - запрещаем редактировать товары для определенных статусов
        non_editable_statuses = ["Отправлен", "Доставлен", "Отменен", "Оплачен"]
        if order.status and order.status.name in non_editable_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Редактирование товаров невозможно для заказа в статусе '{order.status.name}'"
            )
        
        # Подготавливаем данные для обновления
        items_to_add = [item.model_dump() for item in items_data.items_to_add] if items_data.items_to_add else []
        items_to_update = items_data.items_to_update if items_data.items_to_update else {}
        items_to_remove = items_data.items_to_remove if items_data.items_to_remove else []
        
        # Вызываем сервисную функцию
        updated_order = await update_order_items(
            order_id=order_id,
            items_to_add=items_to_add,
            items_to_update=items_to_update,
            items_to_remove=items_to_remove,
            session=session,
            user_id=int(current_user.get("sub")) if current_user.get("sub") else None
        )
        
        if not updated_order:
            raise HTTPException(status_code=400, detail="Ошибка при обновлении элементов заказа")
        
        # Создаем ответ с данными заказа
        order_dict = {
            "id": updated_order.id,
            "user_id": updated_order.user_id,
            "status_id": updated_order.status_id,
            "status": {
                "id": updated_order.status.id,
                "name": updated_order.status.name,
                "description": updated_order.status.description,
                "color": updated_order.status.color,
                "allow_cancel": updated_order.status.allow_cancel,
                "is_final": updated_order.status.is_final,
                "sort_order": updated_order.status.sort_order
            },
            "created_at": updated_order.created_at,
            "updated_at": datetime.now(),
            "total_price": updated_order.total_price,
            "promo_code_id": updated_order.promo_code_id,
            "discount_amount": updated_order.discount_amount,
            "full_name": updated_order.full_name,
            "email": updated_order.email,
            "phone": updated_order.phone,
            "region": updated_order.region,
            "city": updated_order.city,
            "street": updated_order.street,
            "comment": updated_order.comment,
            "is_paid": updated_order.is_paid,
            "items": [
                {
                    "id": item.id,
                    "order_id": item.order_id,
                    "product_id": item.product_id,
                    "product_name": item.product_name,
                    "product_price": item.product_price,
                    "quantity": item.quantity,
                    "total_price": item.total_price
                } 
                for item in updated_order.items
            ],
            "order_number": f"{updated_order.id}-{updated_order.created_at.year}"
        }
        
        # Добавляем данные о промокоде, если он есть
        if hasattr(updated_order, 'promo_code') and updated_order.promo_code:
            promo = updated_order.promo_code
            order_dict["promo_code"] = {
                "id": promo.id,
                "code": promo.code,
                "discount_percent": promo.discount_percent,
                "discount_amount": promo.discount_amount,
                "valid_until": promo.valid_until,
                "is_active": promo.is_active,
                "created_at": promo.created_at,
                "updated_at": datetime.now()
            }
        
        return OrderItemsUpdateResponse(success=True, order=order_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении элементов заказа: {str(e)}")
        return OrderItemsUpdateResponse(
            success=False, 
            errors={"message": f"Ошибка при обновлении элементов заказа: {str(e)}"}
        )

@admin_router.post("/batch-status", response_model=List[OrderResponse])
async def update_batch_status(
    update_data: BatchStatusUpdate,
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Обновление статуса для нескольких заказов одновременно (только для администраторов).
    
    - **update_data**: Данные для массового обновления статусов
    """
    try:
        # Проверяем существование статуса
        status = await session.get(OrderStatusModel, update_data.status_id)
        if not status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Статус с ID {update_data.status_id} не найден",
            )
        
        updated_orders = []
        for order_id in update_data.order_ids:
            try:
                # Создаем данные для обновления
                order_data = OrderUpdate(status_id=update_data.status_id)
                
                # Обновляем заказ
                order = await update_order(
                    session=session,
                    order_id=order_id,
                    order_data=order_data
                )
                
                if order:
                    # Добавляем запись в историю статусов
                    await OrderStatusHistoryModel.add_status_change(
                        session=session,
                        order_id=order.id,
                        status_id=update_data.status_id,
                        changed_by_user_id=current_user["user_id"],
                        notes=update_data.notes or "Массовое обновление статуса"
                    )
                    
                    loaded_order = await get_order_by_id(session, order.id)
                    updated_orders.append(loaded_order)
            except Exception as e:
                logger.error(f"Ошибка при обновлении заказа {order_id}: {str(e)}")
                # Продолжаем с другими заказами
        
        # Коммитим сессию
        await session.commit()
        
        # Преобразуем модели в схемы
        return [OrderResponse.model_validate(order) for order in updated_orders]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при массовом обновлении статусов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при массовом обновлении статусов",
        )

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
        logger.error(f"Ошибка при проверке возможности оставить отзыв: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке возможности оставить отзыв"
        )

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
        logger.error(f"Ошибка при проверке возможности оставить отзыв на магазин: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при проверке возможности оставить отзыв на магазин"
        ) 