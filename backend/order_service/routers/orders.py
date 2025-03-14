from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import os
from dotenv import load_dotenv

from database import get_db
from models import OrderModel
from schemas import (
    OrderCreate, OrderUpdate, OrderResponse, OrderDetailResponse, 
    OrderStatusHistoryCreate, PaginatedResponse, OrderStatistics
)
from services import (
    create_order, get_order_by_id, get_orders, update_order, 
    change_order_status, cancel_order, get_order_statistics
)
from dependencies import (
    get_current_user, get_admin_user, get_order_filter_params,
    check_products_availability, get_products_info, get_user_cart, clear_user_cart
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

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_new_order(
    order_data: OrderCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Создание нового заказа.
    
    - **order_data**: Данные для создания заказа
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        
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
        
        # Создаем заказ
        order = await create_order(
            session=session,
            user_id=user_id,
            order_data=order_data,
            product_service_url=PRODUCT_SERVICE_URL
        )
        
        # Очищаем корзину пользователя
        await clear_user_cart(user_id)
        
        return order
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

@router.post("/from-cart", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order_from_cart(
    shipping_address_id: Optional[int] = None,
    contact_phone: Optional[str] = None,
    contact_email: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Создание заказа из корзины пользователя.
    
    - **shipping_address_id**: ID адреса доставки
    - **contact_phone**: Контактный телефон
    - **contact_email**: Контактный email
    - **notes**: Примечания к заказу
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        
        # Получаем корзину пользователя
        cart = await get_user_cart(user_id)
        
        # Проверяем, есть ли товары в корзине
        if not cart.get("items"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Корзина пуста",
            )
        
        # Создаем данные для заказа
        order_data = OrderCreate(
            items=[{"product_id": item["product_id"], "quantity": item["quantity"]} for item in cart["items"]],
            shipping_address_id=shipping_address_id,
            contact_phone=contact_phone,
            contact_email=contact_email,
            notes=notes
        )
        
        # Создаем заказ
        order = await create_order(
            session=session,
            user_id=user_id,
            order_data=order_data,
            product_service_url=PRODUCT_SERVICE_URL
        )
        
        # Очищаем корзину пользователя
        await clear_user_cart(user_id)
        
        return order
    except ValueError as e:
        logger.error(f"Ошибка при создании заказа из корзины: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при создании заказа из корзины: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при создании заказа из корзины",
        )

@router.get("", response_model=PaginatedResponse)
async def list_orders(
    filters = Depends(get_order_filter_params),
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение списка заказов с пагинацией и фильтрацией.
    
    - **page**: Номер страницы
    - **size**: Размер страницы
    - **status_id**: ID статуса заказа
    - **user_id**: ID пользователя (только для администраторов)
    - **order_by**: Поле для сортировки
    - **order_dir**: Направление сортировки
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Если пользователь не администратор, то он может видеть только свои заказы
        if not is_admin:
            filters.user_id = user_id
        
        # Получаем заказы
        orders, total = await get_orders(
            session=session,
            filters=filters,
            user_id=None if is_admin else user_id
        )
        
        # Формируем ответ
        return PaginatedResponse(
            items=[OrderResponse.from_orm(order) for order in orders],
            total=total,
            page=filters.page,
            size=filters.size,
            pages=0  # Будет вычислено в валидаторе
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка заказов: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка заказов",
        )

@router.get("/my", response_model=PaginatedResponse)
async def list_my_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status_id: Optional[int] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение списка заказов текущего пользователя.
    
    - **page**: Номер страницы
    - **size**: Размер страницы
    - **status_id**: ID статуса заказа
    """
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
        
        # Получаем заказы
        orders, total = await get_orders(
            session=session,
            filters=filters,
            user_id=user_id
        )
        
        # Формируем ответ
        return PaginatedResponse(
            items=[OrderResponse.from_orm(order) for order in orders],
            total=total,
            page=filters.page,
            size=filters.size,
            pages=0  # Будет вычислено в валидаторе
        )
    except Exception as e:
        logger.error(f"Ошибка при получении списка заказов пользователя: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении списка заказов",
        )

@router.get("/{order_id}", response_model=OrderDetailResponse)
async def get_order(
    order_id: int = Path(..., ge=1),
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение информации о заказе по ID.
    
    - **order_id**: ID заказа
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Получаем заказ
        order = await get_order_by_id(
            session=session,
            order_id=order_id,
            user_id=None if is_admin else user_id
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )
        
        return OrderDetailResponse.from_orm(order)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении информации о заказе: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении информации о заказе",
        )

@router.put("/{order_id}", response_model=OrderResponse)
async def update_order_info(
    order_id: int = Path(..., ge=1),
    order_data: OrderUpdate = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Обновление информации о заказе.
    
    - **order_id**: ID заказа
    - **order_data**: Данные для обновления
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Обновляем заказ
        order = await update_order(
            session=session,
            order_id=order_id,
            order_data=order_data,
            user_id=None if is_admin else user_id
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )
        
        return OrderResponse.from_orm(order)
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

@router.post("/{order_id}/status", response_model=OrderResponse)
async def change_status(
    order_id: int = Path(..., ge=1),
    status_data: OrderStatusHistoryCreate = None,
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Изменение статуса заказа (только для администраторов).
    
    - **order_id**: ID заказа
    - **status_data**: Данные о новом статусе
    """
    try:
        # Получаем ID пользователя из токена
        user_id = current_user["user_id"]
        is_admin = current_user.get("is_admin", False)
        
        # Изменяем статус заказа
        order = await change_order_status(
            session=session,
            order_id=order_id,
            status_data=status_data,
            user_id=user_id,
            is_admin=is_admin
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Заказ с ID {order_id} не найден",
            )
        
        return OrderResponse.from_orm(order)
    except ValueError as e:
        logger.error(f"Ошибка при изменении статуса заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при изменении статуса заказа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при изменении статуса заказа",
        )

@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order_endpoint(
    order_id: int = Path(..., ge=1),
    cancel_reason: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Отмена заказа.
    
    - **order_id**: ID заказа
    - **cancel_reason**: Причина отмены
    """
    try:
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
        
        return OrderResponse.from_orm(order)
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

@router.get("/statistics", response_model=OrderStatistics)
async def get_statistics(
    current_user: Dict[str, Any] = Depends(get_admin_user),
    session: AsyncSession = Depends(get_db)
):
    """
    Получение статистики по заказам (только для администраторов).
    """
    try:
        # Получаем статистику
        statistics = await get_order_statistics(session=session)
        
        return statistics
    except Exception as e:
        logger.error(f"Ошибка при получении статистики по заказам: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Произошла ошибка при получении статистики по заказам",
        ) 