from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from sqlalchemy.orm import selectinload
import logging
from datetime import datetime

from models import OrderModel, OrderItemModel, OrderStatusModel, OrderStatusHistoryModel, ShippingAddressModel, BillingAddressModel
from schemas import OrderCreate, OrderUpdate, OrderStatusHistoryCreate, OrderFilterParams, OrderStatistics
from dependencies import check_products_availability, get_products_info
from product_api import ProductAPI, get_product_api
from cache import (
    invalidate_order_cache, invalidate_statistics_cache, invalidate_order_statuses_cache,
    cache_order, get_cached_order, cache_order_statistics, invalidate_cache, CacheKeys, invalidate_user_orders_cache
)

# Настройка логирования
logger = logging.getLogger("order_service")

# Сервисные функции для работы с заказами
async def create_order(
    session: AsyncSession,
    user_id: Optional[int],
    order_data: OrderCreate,
    product_service_url: str,
    token: Optional[str] = None
) -> OrderModel:
    """
    Создание нового заказа
    
    Args:
        session: Сессия базы данных
        user_id: ID пользователя, создающего заказ (может быть None для анонимных пользователей)
        order_data: Данные для создания заказа
        product_service_url: URL сервиса продуктов для проверки наличия товаров
        token: Токен авторизации для запросов к другим сервисам
        
    Returns:
        Созданный заказ
    """
    # Получаем статус по умолчанию для нового заказа
    default_status = await OrderStatusModel.get_default(session)
    if not default_status:
        logger.error("Не найден статус заказа по умолчанию")
        raise ValueError("Не найден статус заказа по умолчанию")
    
    # Получаем информацию о товарах
    product_ids = [item.product_id for item in order_data.items]
    products_info = await get_products_info(product_ids, token)
    
    # Получаем API для работы с товарами
    product_api = await get_product_api()
    
    # Проверка наличия товаров
    availability = await check_products_availability(product_ids, token)
    
    # Проверяем, все ли товары доступны
    unavailable_products = [pid for pid, available in availability.items() if not available]
    if unavailable_products:
        logger.error(f"Товары с ID {unavailable_products} недоступны для заказа")
        raise ValueError(f"Товары с ID {unavailable_products} недоступны для заказа")
    
    # Создаем заказ
    total_price = 0  # Будет рассчитано на основе товаров
    
    # Создаем заказ с новыми полями
    order = OrderModel(
        user_id=user_id,
        status_id=default_status.id,
        total_price=total_price,  # Временное значение, будет обновлено
        full_name=order_data.full_name,
        email=order_data.email,
        phone=order_data.phone,
        region=order_data.region,
        city=order_data.city,
        street=order_data.street,
        comment=order_data.comment,
        is_paid=False
    )
    session.add(order)
    await session.flush()
    
    # Создаем элементы заказа
    for item in order_data.items:
        product_id = item.product_id
        quantity = item.quantity
        
        # Получаем информацию о товаре
        product_info = products_info.get(product_id)
        if not product_info:
            logger.warning(f"Не удалось получить информацию о товаре {product_id}")
            continue
        
        # Создаем элемент заказа
        order_item = OrderItemModel(
            order_id=order.id,
            product_id=product_id,
            product_name=product_info["name"],
            product_price=product_info["price"],
            quantity=quantity,
            total_price=product_info["price"] * quantity
        )
        session.add(order_item)
        
        # Обновляем количество товара на складе
        success = await product_api.update_stock(product_id, -quantity, token)
        if not success:
            logger.warning(f"Не удалось обновить количество товара {product_id}")
        
        # Добавляем к общей стоимости заказа
        total_price += product_info["price"] * quantity
    
    # Обновляем общую стоимость заказа
    order.total_price = total_price
    
    # Добавляем запись в историю статусов
    await OrderStatusHistoryModel.add_status_change(
        session=session,
        order_id=order.id,
        status_id=default_status.id,
        changed_by_user_id=user_id,
        notes="Заказ создан"
    )
    
    await session.flush()
    
    # Инвалидируем кэш после создания заказа
    await invalidate_order_cache(order.id)
    logger.info(f"Кэш заказа {order.id} и связанных списков инвалидирован после создания")
    
    return order

async def get_order_by_id(session: AsyncSession, order_id: int, user_id: Optional[int] = None) -> Optional[OrderModel]:
    """
    Получение заказа по ID
    
    Args:
        session: Сессия базы данных
        order_id: ID заказа
        user_id: ID пользователя (для проверки доступа)
        
    Returns:
        Заказ или None, если заказ не найден или пользователь не имеет доступа
    """
    # Логирование запроса
    logger.info(f"Запрос получения заказа: order_id={order_id}, user_id={user_id if user_id is not None else 'None (admin)'}")
    
    try:
        # Формируем запрос с джойнами для загрузки всех связанных данных
        query = select(OrderModel).options(
            selectinload(OrderModel.items),
            selectinload(OrderModel.status),
            selectinload(OrderModel.status_history).selectinload(OrderStatusHistoryModel.status)
        ).filter(OrderModel.id == order_id)
        
        # Если указан пользователь, фильтруем только его заказы
        # Для администратора user_id=None, поэтому фильтрация не применяется
        if user_id is not None:
            logger.info(f"Применение фильтра по user_id={user_id}")
            query = query.filter(OrderModel.user_id == user_id)
        
        # Выполняем запрос
        result = await session.execute(query)
        order = result.scalars().first()
        
        # Логируем результат
        if order:
            logger.info(f"Заказ найден: order_id={order_id}, user_id={order.user_id}, status={order.status_id if hasattr(order, 'status_id') else 'N/A'}")
            # Выводим информацию о товарах в заказе
            if hasattr(order, 'items') and order.items:
                logger.info(f"Количество товаров в заказе: {len(order.items)}")
        else:
            # Если заказ не найден, логируем подробную информацию для отладки
            logger.warning(f"Заказ с ID {order_id} не найден. Фильтр по пользователю: {user_id is not None}")
            # Проверим, существует ли заказ вообще
            check_query = select(OrderModel).filter(OrderModel.id == order_id)
            check_result = await session.execute(check_query)
            check_order = check_result.scalars().first()
            if check_order:
                logger.warning(f"Заказ с ID {order_id} существует, но не доступен для пользователя {user_id}. Владелец заказа: {check_order.user_id}")
        
        return order
    except Exception as e:
        logger.error(f"Ошибка при выполнении запроса заказа: {str(e)}")
        raise

async def get_orders(
    session: AsyncSession,
    filters: OrderFilterParams,
    user_id: Optional[int] = None
) -> Tuple[List[OrderModel], int]:
    """
    Получение списка заказов с фильтрацией и пагинацией
    
    Args:
        session: Сессия базы данных
        filters: Параметры фильтрации и пагинации
        user_id: ID пользователя (для фильтрации по пользователю)
        
    Returns:
        Кортеж из списка заказов и общего количества заказов
    """
    if user_id is not None:
        return await OrderModel.get_by_user(
            session=session,
            user_id=user_id,
            page=filters.page,
            limit=filters.size,
            status_id=filters.status_id
        )
    else:
        return await OrderModel.get_all(
            session=session,
            page=filters.page,
            limit=filters.size,
            status_id=filters.status_id,
            user_id=filters.user_id,
            id=filters.id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            order_by=filters.order_by,
            order_dir=filters.order_dir,
            username=filters.username
        )

async def update_order(
    session: AsyncSession,
    order_id: int,
    order_data: OrderUpdate,
    user_id: Optional[int] = None
) -> Optional[OrderModel]:
    """
    Обновление информации о заказе
    
    Args:
        session: Сессия базы данных
        order_id: ID заказа
        order_data: Данные для обновления
        user_id: ID пользователя (для проверки доступа, если указан)
        
    Returns:
        Обновленный заказ или None, если заказ не найден
    """
    # Получаем заказ
    order = await get_order_by_id(session, order_id, user_id)
    if not order:
        return None
    
    # Обновляем статус заказа
    if order_data.status_id is not None:
        # Проверяем существование статуса
        status = await session.get(OrderStatusModel, order_data.status_id)
        if not status:
            logger.error(f"Статус с ID {order_data.status_id} не найден")
            raise ValueError(f"Статус с ID {order_data.status_id} не найден")
        
        order.status_id = order_data.status_id
    
    # Обновляем данные заказа
    if order_data.full_name is not None:
        order.full_name = order_data.full_name
    
    if order_data.email is not None:
        order.email = order_data.email
    
    if order_data.phone is not None:
        order.phone = order_data.phone
    
    if order_data.region is not None:
        order.region = order_data.region
    
    if order_data.city is not None:
        order.city = order_data.city
    
    if order_data.street is not None:
        order.street = order_data.street
    
    if order_data.comment is not None:
        order.comment = order_data.comment
    
    if order_data.is_paid is not None:
        order.is_paid = order_data.is_paid
    
    order.updated_at = datetime.utcnow()
    await session.flush()
    
    # Инвалидируем кэш после обновления заказа
    await invalidate_order_cache(order_id)
    # Если изменился статус, то инвалидируем кэш статистики
    if order_data.status_id is not None:
        await invalidate_statistics_cache()
    logger.info(f"Кэш заказа {order_id} инвалидирован после обновления")
    
    return order

async def change_order_status(
    session: AsyncSession,
    order_id: int,
    status_data: OrderStatusHistoryCreate,
    user_id: int,
    is_admin: bool = False
) -> Optional[OrderModel]:
    """
    Изменение статуса заказа
    
    Args:
        session: Сессия базы данных
        order_id: ID заказа
        status_data: Данные для изменения статуса
        user_id: ID пользователя, изменяющего статус
        is_admin: Флаг, указывающий, является ли пользователь администратором
        
    Returns:
        Заказ с обновленным статусом или None, если заказ не найден
    """
    # Получаем заказ
    order = await get_order_by_id(session, order_id)
    if not order:
        return None
    
    # Проверяем доступ пользователя
    if not is_admin and order.user_id != user_id:
        logger.error(f"Пользователь {user_id} не имеет доступа к заказу {order_id}")
        return None
    
    # Получаем новый статус
    new_status = await session.get(OrderStatusModel, status_data.status_id)
    if not new_status:
        logger.error(f"Статус с ID {status_data.status_id} не найден")
        raise ValueError(f"Статус с ID {status_data.status_id} не найден")
    
    # Проверяем, что новый статус отличается от текущего
    if order.status_id == new_status.id:
        logger.warning(f"Попытка установить тот же статус ({new_status.id}) для заказа {order_id}. Операция отменена.")
        raise ValueError(f"Заказ уже имеет статус '{new_status.name}'")
        
    # Проверяем возможность отмены заказа
    if order.status_id != new_status.id:
        current_status = await session.get(OrderStatusModel, order.status_id)
        if current_status and current_status.is_final:
            logger.error(f"Невозможно изменить статус заказа {order_id}, так как текущий статус является финальным")
            raise ValueError("Невозможно изменить статус заказа, так как текущий статус является финальным")
    
    # Обновляем статус заказа
    order.status_id = new_status.id
    order.updated_at = datetime.utcnow()
    
    # Добавляем запись в историю статусов
    await OrderStatusHistoryModel.add_status_change(
        session=session,
        order_id=order.id,
        status_id=new_status.id,
        changed_by_user_id=user_id,
        notes=status_data.notes
    )
    
    await session.flush()
    
    # Инвалидируем кэш после изменения статуса заказа
    await invalidate_order_cache(order_id)
    await invalidate_statistics_cache()
    logger.info(f"Кэш заказа {order_id} и статистики инвалидирован после изменения статуса")
    
    return order

async def cancel_order(
    session: AsyncSession,
    order_id: int,
    user_id: int,
    is_admin: bool = False,
    cancel_reason: Optional[str] = None
) -> Optional[OrderModel]:
    """
    Отмена заказа
    
    Args:
        session: Сессия базы данных
        order_id: ID заказа
        user_id: ID пользователя, отменяющего заказ
        is_admin: Флаг, указывающий, является ли пользователь администратором
        cancel_reason: Причина отмены
        
    Returns:
        Отмененный заказ или None, если заказ не найден
    """
    # Получаем заказ
    order = await get_order_by_id(session, order_id)
    if not order:
        return None
    
    # Проверяем доступ пользователя
    if not is_admin and order.user_id != user_id:
        logger.error(f"Пользователь {user_id} не имеет доступа к заказу {order_id}")
        return None
    
    # Получаем текущий статус заказа
    current_status = await session.get(OrderStatusModel, order.status_id)
    if not current_status:
        logger.error(f"Статус заказа {order_id} не найден")
        return None
    
    # Проверяем возможность отмены заказа
    if not current_status.allow_cancel and not is_admin:
        logger.error(f"Невозможно отменить заказ {order_id}, так как текущий статус не позволяет отмену")
        raise ValueError("Невозможно отменить заказ, так как текущий статус не позволяет отмену")
    
    # Получаем статус "Отменен"
    cancel_status_query = select(OrderStatusModel).filter(OrderStatusModel.name == "Отменен")
    result = await session.execute(cancel_status_query)
    cancel_status = result.scalars().first()
    
    if not cancel_status:
        logger.error("Статус 'Отменен' не найден")
        raise ValueError("Статус 'Отменен' не найден")
    
    # Обновляем статус заказа
    order.status_id = cancel_status.id
    order.updated_at = datetime.utcnow()
    
    # Добавляем запись в историю статусов
    notes = cancel_reason if cancel_reason else "Заказ отменен"
    await OrderStatusHistoryModel.add_status_change(
        session=session,
        order_id=order.id,
        status_id=cancel_status.id,
        changed_by_user_id=user_id,
        notes=notes
    )
    
    await session.flush()
    
    # Инвалидируем кэш после отмены заказа
    await invalidate_order_cache(order_id)
    await invalidate_statistics_cache()
    logger.info(f"Кэш заказа {order_id} и статистики инвалидирован после отмены заказа")
    
    return order

async def get_order_statistics(session: AsyncSession) -> OrderStatistics:
    """
    Получение статистики по заказам
    
    Args:
        session: Сессия базы данных
        
    Returns:
        Статистика по заказам
    """
    # Общее количество заказов
    total_orders_query = select(func.count(OrderModel.id))
    total_orders_result = await session.execute(total_orders_query)
    total_orders = total_orders_result.scalar() or 0
    
    # Общая выручка
    total_revenue_query = select(func.sum(OrderModel.total_price))
    total_revenue_result = await session.execute(total_revenue_query)
    total_revenue = total_revenue_result.scalar() or 0
    
    # Средняя стоимость заказа
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Количество заказов по статусам
    orders_by_status_query = select(
        OrderStatusModel.name,
        func.count(OrderModel.id)
    ).join(
        OrderModel,
        OrderStatusModel.id == OrderModel.status_id
    ).group_by(
        OrderStatusModel.name
    )
    orders_by_status_result = await session.execute(orders_by_status_query)
    orders_by_status = {row[0]: row[1] for row in orders_by_status_result}
    
    # Так как payment_method удалено, возвращаем пустой словарь
    orders_by_payment_method = {}
    
    return OrderStatistics(
        total_orders=total_orders,
        total_revenue=total_revenue,
        average_order_value=average_order_value,
        orders_by_status=orders_by_status,
        orders_by_payment_method=orders_by_payment_method
    )

async def get_user_order_statistics(session: AsyncSession, user_id: int) -> OrderStatistics:
    """
    Получение статистики по заказам конкретного пользователя
    
    Args:
        session: Сессия базы данных
        user_id: ID пользователя
        
    Returns:
        Статистика по заказам пользователя
    """
    # Общее количество заказов пользователя
    total_orders_query = select(func.count(OrderModel.id)).where(OrderModel.user_id == user_id)
    total_orders_result = await session.execute(total_orders_query)
    total_orders = total_orders_result.scalar() or 0
    
    # Общая сумма заказов пользователя
    total_revenue_query = select(func.sum(OrderModel.total_price)).where(OrderModel.user_id == user_id)
    total_revenue_result = await session.execute(total_revenue_query)
    total_revenue = total_revenue_result.scalar() or 0
    
    # Средняя стоимость заказа
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Количество заказов по статусам
    orders_by_status_query = select(
        OrderStatusModel.name,
        func.count(OrderModel.id)
    ).join(
        OrderModel,
        OrderStatusModel.id == OrderModel.status_id
    ).where(
        OrderModel.user_id == user_id
    ).group_by(
        OrderStatusModel.name
    )
    orders_by_status_result = await session.execute(orders_by_status_query)
    orders_by_status = {row[0]: row[1] for row in orders_by_status_result}
    
    # Так как payment_method удалено, возвращаем пустой словарь
    orders_by_payment_method = {}
    
    return OrderStatistics(
        total_orders=total_orders,
        total_revenue=total_revenue,
        average_order_value=average_order_value,
        orders_by_status=orders_by_status,
        orders_by_payment_method=orders_by_payment_method
    ) 