"""Сервисный слой для работы с заказами."""

from typing import List, Optional, Tuple, Dict, Any
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from models import OrderModel, OrderItemModel, OrderStatusModel, OrderStatusHistoryModel, PromoCodeModel, PromoCodeUsageModel
from schemas import OrderCreate, OrderUpdate, OrderStatusHistoryCreate, OrderFilterParams, OrderStatistics
from dependencies import check_products_availability, get_products_info
from product_api import get_product_api
from cache import (
    invalidate_order_cache, invalidate_statistics_cache)

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
    
    # Проверяем, что указан тип доставки
    if not order_data.delivery_type:
        logger.error("Не указан способ доставки")
        raise ValueError("Необходимо выбрать способ доставки")
    
    # Для пунктов выдачи проверяем, что указан адрес пункта
    if order_data.delivery_type in ["boxberry_pickup_point", "cdek_pickup_point"] and not order_data.boxberry_point_address:
        logger.error("Не указан адрес пункта выдачи")
        raise ValueError("Необходимо указать адрес пункта выдачи")
    
    # Получаем информацию о товарах
    product_ids = [item.product_id for item in order_data.items]
    products_info = await get_products_info(product_ids)
    
    # Получаем API для работы с товарами
    product_api = await get_product_api()
    
    # Проверка наличия товаров
    availability = await check_products_availability(product_ids)
    
    # Проверяем, все ли товары доступны
    unavailable_products = [pid for pid, available in availability.items() if not available]
    if unavailable_products:
        logger.error("Товары с ID %s недоступны для заказа", unavailable_products)
        raise ValueError(f"Товары с ID {unavailable_products} недоступны для заказа")
    
    # Проверяем, достаточно ли товаров на складе
    for item in order_data.items:
        product_id = item.product_id
        quantity = item.quantity
        
        # Получаем информацию о продукте и проверяем доступное количество
        is_available, product_info = await product_api.check_stock(product_id, quantity)
        
        if not is_available:
            if not product_info:
                logger.error("Товар с ID %s не найден", product_id)
                raise ValueError(f"Товар с ID {product_id} не найден")
            else:
                logger.error("Недостаточное количество товара %s: запрошено %s, доступно %s", product_id, quantity, product_info.stock)
                raise ValueError(f"Недостаточное количество товара '{product_info.name}': запрошено {quantity}, доступно {product_info.stock}")
    
    # Создаем заказ
    total_price = 0  # Будет рассчитано на основе товаров
    
    # Проверяем промокод, если он указан
    promo_code = None
    promo_code_id = None
    discount_amount = 0
    
    if order_data.promo_code:
        is_valid, message, promo_code = await check_promo_code(
            session=session,
            code=order_data.promo_code,
            email=order_data.email,
            phone=order_data.phone,
            user_id=user_id
        )
        
        if not is_valid:
            logger.warning("Промокод %s не валиден: %s", order_data.promo_code, message)
            raise ValueError(message)
        
        logger.info("Промокод %s применен", order_data.promo_code)
        promo_code_id = promo_code.id
    
    # Создаем заказ с новыми полями
    order = OrderModel(
        user_id=user_id,
        status_id=default_status.id,
        total_price=total_price,  # Временное значение, будет обновлено
        full_name=order_data.full_name,
        email=order_data.email,
        phone=order_data.phone,
        delivery_address=order_data.delivery_address,
        comment=order_data.comment,
        promo_code_id=promo_code_id,
        discount_amount=0,  # Будет обновлено после расчета скидки
        is_paid=False,
        personal_data_agreement=order_data.personal_data_agreement,
        receive_notifications=order_data.receive_notifications,
        # Данные о доставке
        delivery_type=order_data.delivery_type,
        boxberry_point_address=order_data.boxberry_point_address if hasattr(order_data, 'boxberry_point_address') else None,
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
            logger.warning("Не удалось получить информацию о товаре %s", product_id)
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
            logger.error("Не удалось обновить количество товара %s", product_id)
        
        # Добавляем к общей стоимости заказа
        total_price += product_info["price"] * quantity
    
    # Применяем скидку, если есть промокод
    if promo_code:
        # Расчитываем размер скидки
        discount_amount = await calculate_discount(promo_code, total_price)
        
        # Обновляем сумму заказа с учетом скидки
        total_price = max(0, total_price - discount_amount)
        
        # Сохраняем информацию об использовании промокода
        promo_code_usage = PromoCodeUsageModel(
            promo_code_id=promo_code.id,
            email=order_data.email,
            phone=order_data.phone,
            user_id=user_id,
        )
        session.add(promo_code_usage)
    
    # Обновляем общую стоимость заказа и скидку
    order.total_price = total_price
    order.discount_amount = discount_amount
    
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
    logger.info("Кэш заказа %s и связанных списков инвалидирован после создания", order.id)
    
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
    logger.info("Запрос получения заказа: order_id=%s, user_id=%s", order_id, user_id if user_id is not None else 'None (admin)')
    
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
            logger.info("Применение фильтра по user_id=%s", user_id)
            query = query.filter(OrderModel.user_id == user_id)
        
        # Выполняем запрос
        result = await session.execute(query)
        order = result.scalars().first()
        
        # Логируем результат
        if order:
            logger.info("Заказ найден: order_id=%s, user_id=%s, status=%s", order_id, order.user_id, order.status_id if hasattr(order, 'status_id') else 'N/A')
            # Выводим информацию о товарах в заказе
            if hasattr(order, 'items') and order.items:
                logger.info("Количество товаров в заказе: %s", len(order.items))
        else:
            # Если заказ не найден, логируем подробную информацию для отладки
            logger.warning("Заказ с ID %s не найден. Фильтр по пользователю: %s", order_id, user_id is not None)
            # Проверим, существует ли заказ вообще
            check_query = select(OrderModel).filter(OrderModel.id == order_id)
            check_result = await session.execute(check_query)
            check_order = check_result.scalars().first()
            if check_order:
                logger.warning("Заказ с ID %s существует, но не доступен для пользователя %s. Владелец заказа: %s", order_id, user_id, check_order.user_id)
        
        return order
    except Exception as e:
        logger.error("Ошибка при выполнении запроса заказа: %s", str(e))
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
            logger.error("Статус с ID %s не найден", order_data.status_id)
            raise ValueError(f"Статус с ID {order_data.status_id} не найден")
        
        order.status_id = order_data.status_id
    
    # Обновляем данные заказа
    if order_data.full_name is not None:
        order.full_name = order_data.full_name
    
    if order_data.email is not None:
        order.email = order_data.email
    
    if order_data.phone is not None:
        order.phone = order_data.phone
    
    if order_data.delivery_address is not None:
        order.delivery_address = order_data.delivery_address
    
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
    logger.info("Кэш заказа %s инвалидирован после обновления", order_id)
    
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
        logger.error("Пользователь %s не имеет доступа к заказу %s", user_id, order_id)
        return None
    
    # Получаем новый статус
    new_status = await session.get(OrderStatusModel, status_data.status_id)
    if not new_status:
        logger.error("Статус с ID %s не найден", status_data.status_id)
        raise ValueError(f"Статус с ID {status_data.status_id} не найден")
    
    # Проверяем, что новый статус отличается от текущего
    if order.status_id == new_status.id:
        logger.warning("Попытка установить тот же статус (%s) для заказа %s. Операция отменена.", new_status.id, order_id)
        raise ValueError(f"Заказ уже имеет статус '{new_status.name}'")
        
    # Проверяем возможность отмены заказа
    if order.status_id != new_status.id:
        current_status = await session.get(OrderStatusModel, order.status_id)
        if current_status and current_status.is_final:
            logger.error("Невозможно изменить статус заказа %s, так как текущий статус является финальным", order_id)
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
    logger.info("Кэш заказа %s и статистики инвалидирован после изменения статуса", order_id)
    
    return order

async def update_order_items(
    order_id: int,
    items_to_add: List[Dict[str, Any]],
    items_to_update: Dict[int, int],
    items_to_remove: List[int],
    session: AsyncSession,
    user_id: Optional[int] = None
) -> Optional[Any]:
    """
    Обновляет элементы заказа.
    
    Args:
        order_id: ID заказа
        items_to_add: Список словарей с данными новых товаров для добавления
        items_to_update: Словарь {id_товара_в_заказе: новое_количество}
        items_to_remove: Список ID товаров для удаления из заказа
        session: Сессия БД
        user_id: ID пользователя, выполняющего действие
        
    Returns:
        Обновленный заказ или None при ошибке
    """
    logger = logging.getLogger("order_service")
    logger.info("Запрос получения заказа: order_id=%s, user_id=%s (admin)", order_id, user_id if user_id is not None else 'None (admin)')
    
    # Получаем заказ со всеми связанными данными
    order_stmt = select(OrderModel).where(OrderModel.id == order_id).options(
        selectinload(OrderModel.items),
        selectinload(OrderModel.status),
        selectinload(OrderModel.status_history).selectinload(OrderStatusHistoryModel.status)
    )
    
    result = await session.execute(order_stmt)
    order = result.scalar_one_or_none()
    
    if not order:
        logger.warning("Заказ с ID %s не найден", order_id)
        return None
    
    logger.info("Заказ найден: order_id=%s, user_id=%s, status=%s", order.id, order.user_id, order.status_id)
    logger.info("Количество товаров в заказе: %s", len(order.items))
    
    # Загружаем промокод отдельно, если он есть
    promo_code = None
    if order.promo_code_id:
        promo_stmt = select(PromoCodeModel).where(PromoCodeModel.id == order.promo_code_id)
        promo_result = await session.execute(promo_stmt)
        promo_code = promo_result.scalar_one_or_none()
    
    logger.info("Начало обновления элементов заказа %s", order_id)
    
    try:
        # Получаем API для работы с товарами
        product_api = await get_product_api()
        
        # 1. Добавление новых товаров
        if items_to_add:
            logger.info("Добавление новых товаров в заказ %s: %s", order_id, items_to_add)
            
            # Получаем информацию о товарах из сервиса продуктов
            product_ids = [item['product_id'] for item in items_to_add]
            products_info = await get_products_info(product_ids)
            
            # Проверяем наличие товаров в результате
            for item in items_to_add:
                product_id = item['product_id']
                quantity = item['quantity']
                
                # Проверяем доступность товара на складе
                is_available, product_info = await product_api.check_stock(product_id, quantity)
                
                if not is_available:
                    if not product_info:
                        logger.warning("Продукт с ID %s не найден", product_id)
                        continue
                    else:
                        logger.warning("Недостаточно товара %s на складе: запрошено %s, доступно %s", product_id, quantity, product_info.stock)
                        continue
                
                # Уменьшаем количество товара на складе
                success = await product_api.update_stock(product_id, -quantity)
                if not success:
                    logger.error("Не удалось обновить количество товара %s на складе", product_id)
                    continue
                
                # Получаем информацию о товаре
                product_info_dict = products_info.get(product_id)
                if not product_info_dict:
                    logger.warning("Не удалось получить информацию о товаре %s", product_id)
                    continue
                
                # Создаем новый товар в заказе
                new_item = OrderItemModel(
                    order_id=order_id,
                    product_id=product_id,
                    product_name=product_info_dict["name"],
                    product_price=product_info_dict["price"],
                    quantity=quantity,
                    total_price=product_info_dict["price"] * quantity
                )
                
                session.add(new_item)
        
        # 2. Обновление количества товаров
        if items_to_update:
            logger.info("Обновление количества товаров в заказе %s: %s", order_id, items_to_update)
            
            for item_id, new_quantity in items_to_update.items():
                # Находим товар в заказе
                item = next((i for i in order.items if i.id == item_id), None)
                
                if not item:
                    logger.warning("Товар с ID %s не найден в заказе %s", item_id, order_id)
                    continue
                
                # Вычисляем изменение количества
                quantity_diff = new_quantity - item.quantity
                
                if quantity_diff == 0:
                    logger.info("Количество товара %s не изменилось", item.product_id)
                    continue
                
                # Если уменьшаем количество, возвращаем товары на склад
                # Если увеличиваем, уменьшаем количество на складе
                success = await product_api.update_stock(item.product_id, -quantity_diff)
                if not success:
                    logger.error("Не удалось обновить количество товара %s на складе", item.product_id)
                    continue
                
                # Обновляем количество товара в заказе
                item.quantity = new_quantity
                item.total_price = item.product_price * new_quantity
        
        # 3. Удаление товаров из заказа
        if items_to_remove:
            logger.info("Удаление товаров из заказа %s: %s", order_id, items_to_remove)
            
            for item_id in items_to_remove:
                # Находим товар в заказе
                item = next((i for i in order.items if i.id == item_id), None)
                
                if not item:
                    logger.warning("Товар с ID %s не найден в заказе %s", item_id, order_id)
                    continue
                
                # Возвращаем товары на склад
                success = await product_api.update_stock(item.product_id, item.quantity)
                if not success:
                    logger.error("Не удалось обновить количество товара %s на складе", item.product_id)
                    continue
                
                # Удаляем товар из заказа
                await session.delete(item)
        
        # Обновляем общую сумму заказа
        await session.flush()  # Применяем все изменения перед обновлением
        await session.refresh(order, ["items"])
        
        # Проверяем, остались ли товары в заказе
        if not order.items or len(order.items) == 0:
            logger.info("В заказе %s не осталось товаров, устанавливаем сумму 0", order_id)
            total_price = 0
            order.discount_amount = 0
        else:
            total_price = sum(item.total_price for item in order.items)
            
            # Применяем скидку, если есть промокод
            if promo_code:
                if promo_code.discount_percent:
                    discount = int(total_price * promo_code.discount_percent / 100)
                    total_price -= discount
                    order.discount_amount = discount
                elif promo_code.discount_amount:
                    discount = min(promo_code.discount_amount, total_price)
                    total_price -= discount
                    order.discount_amount = discount
        
        logger.info("Обновляем общую сумму заказа %s: %s", order_id, total_price)
        order.total_price = total_price
        
        await session.commit()
        
        # Инвалидация Redis кэша
        await invalidate_order_cache(order_id)
        
        # Принудительное обновление сессии для избежания кэширования SQLAlchemy
        session.expire_all()
        
        logger.info("Элементы заказа %s успешно обновлены", order_id)
        
        # Получаем обновленный заказ для возврата с отключенным кэшированием
        order_stmt = select(OrderModel).where(OrderModel.id == order_id).options(
            selectinload(OrderModel.items),
            selectinload(OrderModel.status),
            selectinload(OrderModel.status_history).selectinload(OrderStatusHistoryModel.status)
        )
        
        if promo_code:
            order_stmt = order_stmt.options(
                selectinload(OrderModel.promo_code)
            )
            
        # Отключаем кэширование для получения актуальных данных
        result = await session.execute(order_stmt, execution_options={"cacheable": False})
        logger.info("Получен результат запроса с отключенным кэшированием для заказа %s", order_id)
        return result.scalar_one_or_none()
        
    except (sqlalchemy.exc.SQLAlchemyError, ValueError, RuntimeError) as e:
        logger.error("Ошибка при обновлении элементов заказа %s: %s", order_id, str(e))
        await session.rollback()
        return None

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
        logger.error("Пользователь %s не имеет доступа к заказу %s", user_id, order_id)
        return None
    
    # Получаем текущий статус заказа
    current_status = await session.get(OrderStatusModel, order.status_id)
    if not current_status:
        logger.error("Статус заказа %s не найден", order_id)
        return None
    
    # Проверяем возможность отмены заказа
    if not current_status.allow_cancel and not is_admin:
        logger.error("Невозможно отменить заказ %s, так как текущий статус не позволяет отмену", order_id)
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
    logger.info("Кэш заказа %s и статистики инвалидирован после отмены заказа", order_id)
    
    return order

async def get_order_statistics(session: AsyncSession) -> OrderStatistics:
    """
    Получение статистики по заказам
    
    Args:
        session: Сессия базы данных
        
    Returns:
        Статистика по заказам
    """
    # Получаем ID статуса "Отменен"
    canceled_status_query = select(OrderStatusModel.id).filter(OrderStatusModel.name == "Отменен")
    canceled_status_result = await session.execute(canceled_status_query)
    canceled_status_id = canceled_status_result.scalar()
    
    # Создаем базовый фильтр для исключения отмененных заказов
    exclude_canceled = []
    canceled_filter = []
    if canceled_status_id:
        exclude_canceled = [OrderModel.status_id != canceled_status_id]
        canceled_filter = [OrderModel.status_id == canceled_status_id]
    
    # Общее количество заказов (включая отмененные)
    total_orders_query = select(func.count(OrderModel.id))
    total_orders_result = await session.execute(total_orders_query)
    total_orders = total_orders_result.scalar() or 0
    
    # Общая выручка (исключая отмененные заказы)
    total_revenue_query = select(func.sum(OrderModel.total_price))
    if exclude_canceled:
        total_revenue_query = total_revenue_query.where(*exclude_canceled)
    total_revenue_result = await session.execute(total_revenue_query)
    total_revenue = total_revenue_result.scalar() or 0
    
    # Сумма отмененных заказов
    canceled_revenue_query = select(func.sum(OrderModel.total_price))
    if canceled_filter:
        canceled_revenue_query = canceled_revenue_query.where(*canceled_filter)
    canceled_revenue_result = await session.execute(canceled_revenue_query)
    canceled_revenue = canceled_revenue_result.scalar() or 0
    
    # Активные заказы (без отмененных) для расчета средней стоимости
    active_orders_query = select(func.count(OrderModel.id))
    if exclude_canceled:
        active_orders_query = active_orders_query.where(*exclude_canceled)
    active_orders_result = await session.execute(active_orders_query)
    active_orders_count = active_orders_result.scalar() or 0
    
    # Средняя стоимость заказа (исключая отмененные)
    average_order_value = round(total_revenue / active_orders_count, 2) if active_orders_count > 0 else 0
    
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
        orders_by_payment_method=orders_by_payment_method,
        canceled_orders_revenue=canceled_revenue
    )

async def get_order_statistics_by_date(
    session: AsyncSession, 
    date_from: Optional[str] = None, 
    date_to: Optional[str] = None
) -> OrderStatistics:
    """
    Получение статистики по заказам с фильтрацией по дате
    
    Args:
        session: Сессия базы данных
        date_from: Дата начала периода в формате YYYY-MM-DD
        date_to: Дата окончания периода в формате YYYY-MM-DD
        
    Returns:
        Статистика по заказам за указанный период
    """
    # Создаем фильтры по датам
    filters = []
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").replace(hour=0, minute=0, second=0)
            filters.append(OrderModel.created_at >= date_from_obj)
        except ValueError:
            logger.error("Неверный формат date_from: %s", date_from)
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            filters.append(OrderModel.created_at <= date_to_obj)
        except ValueError:
            logger.error("Неверный формат date_to: %s", date_to)
    
    # Получаем ID статуса "Отменен"
    canceled_status_query = select(OrderStatusModel.id).filter(OrderStatusModel.name == "Отменен")
    canceled_status_result = await session.execute(canceled_status_query)
    canceled_status_id = canceled_status_result.scalar()
    
    # Создаем фильтры для исключения и выбора отмененных заказов
    exclude_canceled = list(filters)  # копируем базовые фильтры
    canceled_filter = list(filters)   # копируем базовые фильтры для отмененных
    if canceled_status_id:
        exclude_canceled.append(OrderModel.status_id != canceled_status_id)
        canceled_filter.append(OrderModel.status_id == canceled_status_id)
    
    # Общее количество заказов с учетом фильтра (включая отмененные)
    total_orders_query = select(func.count(OrderModel.id))
    if filters:
        total_orders_query = total_orders_query.where(*filters)
    total_orders_result = await session.execute(total_orders_query)
    total_orders = total_orders_result.scalar() or 0
    
    # Общая выручка с учетом фильтра (исключая отмененные)
    total_revenue_query = select(func.sum(OrderModel.total_price))
    if exclude_canceled:
        total_revenue_query = total_revenue_query.where(*exclude_canceled)
    total_revenue_result = await session.execute(total_revenue_query)
    total_revenue = total_revenue_result.scalar() or 0
    
    # Сумма отмененных заказов
    canceled_revenue_query = select(func.sum(OrderModel.total_price))
    if canceled_filter:
        canceled_revenue_query = canceled_revenue_query.where(*canceled_filter)
    canceled_revenue_result = await session.execute(canceled_revenue_query)
    canceled_revenue = canceled_revenue_result.scalar() or 0
    
    # Активные заказы (без отмененных) для расчета средней стоимости
    active_orders_query = select(func.count(OrderModel.id))
    if exclude_canceled:
        active_orders_query = active_orders_query.where(*exclude_canceled)
    active_orders_result = await session.execute(active_orders_query)
    active_orders_count = active_orders_result.scalar() or 0
    
    # Средняя стоимость заказа
    average_order_value = round(total_revenue / active_orders_count, 2) if active_orders_count > 0 else 0
    
    # Количество заказов по статусам с учетом фильтра
    orders_by_status_query = select(
        OrderStatusModel.name,
        func.count(OrderModel.id)
    ).join(
        OrderModel,
        OrderStatusModel.id == OrderModel.status_id
    )
    
    if filters:
        orders_by_status_query = orders_by_status_query.where(*filters)
    
    orders_by_status_query = orders_by_status_query.group_by(OrderStatusModel.name)
    orders_by_status_result = await session.execute(orders_by_status_query)
    orders_by_status = {row[0]: row[1] for row in orders_by_status_result}
    
    # Так как payment_method удалено, возвращаем пустой словарь
    orders_by_payment_method = {}
    
    return OrderStatistics(
        total_orders=total_orders,
        total_revenue=total_revenue,
        average_order_value=average_order_value,
        orders_by_status=orders_by_status,
        orders_by_payment_method=orders_by_payment_method,
        canceled_orders_revenue=canceled_revenue
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
    # Получаем ID статуса "Отменен"
    canceled_status_query = select(OrderStatusModel.id).filter(OrderStatusModel.name == "Отменен")
    canceled_status_result = await session.execute(canceled_status_query)
    canceled_status_id = canceled_status_result.scalar()
    
    # Базовый фильтр по пользователю
    user_filter = [OrderModel.user_id == user_id]
    
    # Создаем фильтры для исключения и выбора отмененных заказов
    exclude_canceled = list(user_filter)  # копируем базовые фильтры
    canceled_filter = list(user_filter)   # копируем базовые фильтры для отмененных
    if canceled_status_id:
        exclude_canceled.append(OrderModel.status_id != canceled_status_id)
        canceled_filter.append(OrderModel.status_id == canceled_status_id)
    
    # Общее количество заказов пользователя (включая отмененные)
    total_orders_query = select(func.count(OrderModel.id)).where(OrderModel.user_id == user_id)
    total_orders_result = await session.execute(total_orders_query)
    total_orders = total_orders_result.scalar() or 0
    
    # Общая сумма заказов пользователя (исключая отмененные)
    total_revenue_query = select(func.sum(OrderModel.total_price))
    total_revenue_query = total_revenue_query.where(*exclude_canceled)
    total_revenue_result = await session.execute(total_revenue_query)
    total_revenue = total_revenue_result.scalar() or 0
    
    # Сумма отмененных заказов пользователя
    canceled_revenue_query = select(func.sum(OrderModel.total_price))
    canceled_revenue_query = canceled_revenue_query.where(*canceled_filter)
    canceled_revenue_result = await session.execute(canceled_revenue_query)
    canceled_revenue = canceled_revenue_result.scalar() or 0
    
    # Активные заказы (без отмененных) для расчета средней стоимости
    active_orders_query = select(func.count(OrderModel.id))
    active_orders_query = active_orders_query.where(*exclude_canceled)
    active_orders_result = await session.execute(active_orders_query)
    active_orders_count = active_orders_result.scalar() or 0
    
    # Средняя стоимость заказа
    average_order_value = round(total_revenue / active_orders_count, 2) if active_orders_count > 0 else 0
    
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
        orders_by_payment_method=orders_by_payment_method,
        canceled_orders_revenue=canceled_revenue
    )

async def check_promo_code(
    session: AsyncSession,
    code: str,
    email: str,
    phone: str,
    user_id: Optional[int] = None
) -> Tuple[bool, str, Optional[PromoCodeModel]]:
    """
    Проверка промокода
    
    Args:
        session: Сессия базы данных
        code: Код промокода
        email: Email пользователя
        phone: Телефон пользователя
        user_id: ID пользователя (может быть None для анонимных пользователей)
    
    Returns:
        Tuple[bool, str, Optional[PromoCodeModel]]: 
            - Флаг валидности
            - Сообщение о результате проверки
            - Объект промокода (если промокод валиден)
    """
    logger.info("Проверка промокода %s для пользователя %s, %s", code, email, phone)
    
    # Находим промокод по коду
    promo_code = await PromoCodeModel.get_by_code(session, code)
    
    # Проверяем существование промокода
    if not promo_code:
        logger.warning("Промокод %s не найден", code)
        return False, "Промокод не найден", None
    
    # Проверяем срок действия промокода
    if promo_code.valid_until < datetime.now():
        if promo_code.is_active:
            promo_code.is_active = False
            await session.commit()
        logger.warning("Промокод %s истек %s", code, promo_code.valid_until)
        return False, "Срок действия промокода истек", None
    
    # Проверяем активность промокода
    if not promo_code.is_active:
        logger.warning("Промокод %s не активен", code)
        return False, "Промокод не активен", None
    
    # Проверяем, использовал ли пользователь промокод ранее
    already_used = await PromoCodeUsageModel.check_usage(session, promo_code.id, email, phone)
    if already_used:
        logger.warning("Промокод %s уже использован с email %s или телефоном %s", code, email, phone)
        return False, "Вы уже использовали этот промокод", None
    
    # Все проверки пройдены
    logger.info("Промокод %s валиден для пользователя %s, %s", code, email, phone)
    return True, "Промокод применен", promo_code

async def calculate_discount(
    promo_code: PromoCodeModel,
    total_price: int
) -> int:
    """
    Расчет скидки на основе промокода
    
    Args:
        promo_code: Объект промокода
        total_price: Общая стоимость заказа
    
    Returns:
        int: Сумма скидки в рублях
    """
    if promo_code.discount_percent is not None:
        # Расчет скидки в процентах
        discount = int(total_price * promo_code.discount_percent / 100)
    elif promo_code.discount_amount is not None:
        # Фиксированная скидка
        discount = min(promo_code.discount_amount, total_price)  # Скидка не может быть больше стоимости заказа
    else:
        # На всякий случай
        discount = 0
    
    return discount 