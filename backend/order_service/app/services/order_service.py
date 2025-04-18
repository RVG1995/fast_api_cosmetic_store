import logging
from ..utils.rabbit_utils import get_connection, close_connection, declare_queue
import json
import aio_pika
# Импортируем функцию проверки настроек уведомлений
import sys
import os

# Путь до директории backend/order_service
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, current_dir)

# Импортируем модуль напрямую
import notification_api

logger = logging.getLogger(__name__)


def create_order_email_content(order_data, new_status_name=None, stock=None):
    if new_status_name:
        # Создаем словарь для сообщения, используя только данные, которые точно не требуют lazy loading
        message_body = {
            "order_number": order_data.order_number,
            "full_name": order_data.full_name,
            "created_at": order_data.created_at.isoformat() if order_data.created_at else None,
            "status": new_status_name,
            "total_price": order_data.total_price,
            "is_paid": order_data.is_paid,
            "email": order_data.email,
            "phone": order_data.phone,
            "region": order_data.region,
            "city": order_data.city,
            "street": order_data.street,
            "discount_amount": 0,
            "promo_code": None,
            "items": []
        }
        
        # Безопасно добавляем скидку
        discount_amount = getattr(order_data, 'discount_amount', 0)
        if discount_amount is not None:
            message_body["discount_amount"] = discount_amount
        
        # Безопасно добавляем информацию о промокоде
        # Не обращаемся напрямую к order_data.promo_code, так как это может вызвать lazy loading
        # Вместо этого проверим, есть ли в объекте заказа словарь с данными о промокоде
        if hasattr(order_data, 'promo_code_dict') and order_data.promo_code_dict:
            message_body["promo_code"] = order_data.promo_code_dict
        
        # Добавляем товары, если они уже загружены
        if hasattr(order_data, 'items') and order_data.items:
            items = []
            for item in order_data.items:
                items.append({
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "product_price": item.product_price,
                    "total_price": item.total_price
                })
            message_body["items"] = items

        # Добавляем информацию о типе события
        message_body["event_type"] = "order.status_changed"
    elif isinstance(order_data, list):
        # Случай для списка товаров с низким остатком
        message_body = {
            "low_stock_products": order_data,
            "event_type": "product.low_stock"
        }
    elif stock is not None:
        # Устаревший случай для одного товара с низким остатком
        message_body = {
            "product_name": order_data,
            "stock": stock,
            "event_type": "product.low_stock"
        }
    else:
        # Создаем словарь для сообщения, используя только данные, которые точно не требуют lazy loading
        message_body = {
            "order_number": order_data.order_number,
            "full_name": order_data.full_name,
            "created_at": order_data.created_at.isoformat() if order_data.created_at else None,
            "status": order_data.status.name if hasattr(order_data, 'status') and order_data.status else "Неизвестно",
            "total_price": order_data.total_price,
            "is_paid": order_data.is_paid,
            "email": order_data.email,
            "phone": order_data.phone,
            "region": order_data.region,
            "city": order_data.city,
            "street": order_data.street,
            "discount_amount": 0,
            "promo_code": None,
            "items": []
        }
        
        # Безопасно добавляем скидку
        discount_amount = getattr(order_data, 'discount_amount', 0)
        if discount_amount is not None:
            message_body["discount_amount"] = discount_amount
        
        # Безопасно добавляем информацию о промокоде
        # Не обращаемся напрямую к order_data.promo_code, так как это может вызвать lazy loading
        # Вместо этого проверим, есть ли в объекте заказа словарь с данными о промокоде
        if hasattr(order_data, 'promo_code_dict') and order_data.promo_code_dict:
            message_body["promo_code"] = order_data.promo_code_dict
        
        # Добавляем товары, если они уже загружены
        if hasattr(order_data, 'items') and order_data.items:
            items = []
            for item in order_data.items:
                items.append({
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "product_price": item.product_price,
                    "total_price": item.total_price
                })
            message_body["items"] = items
        
        # Добавляем информацию о типе события
        message_body["event_type"] = "order.created"
            
    return message_body


async def send_email_message(
    order_data, token=None
):
    """
    Отправляет сообщение с данными для email в очередь
    
    Args:
        order_data: Данные заказа
        token: JWT токен для авторизации в сервисе уведомлений
    """
    # Проверяем настройки уведомлений пользователя
    user_id = str(order_data.user_id) if hasattr(order_data, 'user_id') and order_data.user_id else None
    
    # Если пользователь авторизован - проверяем его настройки уведомлений для созданных заказов
    if user_id:
        settings = await notification_api.check_notification_settings(user_id, "order.created", token)
        if not settings["email_enabled"]:
            logger.info(f"Email уведомления отключены для пользователя {user_id}, email не будет отправлен")
            return None
    
    connection = await get_connection()
    
    try:
        # Создаем канал
        channel = await connection.channel()
        
        # Объявляем очередь с использованием общей функции
        queue = await declare_queue(channel, "email_message")

        message_body = create_order_email_content(order_data)
        
        # Отправляем сообщение
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        logger.info(f"RabbitMQ: {json.dumps(message_body, ensure_ascii=False)}")
        return "message_sent"
    finally:
        # Закрываем соединение в любом случае
        await close_connection(connection)


async def update_order_status(
    order_data, new_status_name, token=None
):
    """
    Отправляет сообщение об изменении статуса заказа с данными для email в очередь
    
    Args:
        order_data: Данные заказа
        new_status_name: Название нового статуса
        token: JWT токен для авторизации в сервисе уведомлений
    """
    # Проверяем настройки уведомлений пользователя
    user_id = str(order_data.user_id) if hasattr(order_data, 'user_id') and order_data.user_id else None
    
    # Если пользователь авторизован - проверяем его настройки уведомлений для изменения статуса заказа
    if user_id:
        settings = await notification_api.check_notification_settings(user_id, "order.status_changed", token)
        if not settings["email_enabled"]:
            logger.info(f"Email уведомления об изменении статуса отключены для пользователя {user_id}, email не будет отправлен")
            return None
    
    connection = await get_connection()
    
    try:
        # Создаем канал
        channel = await connection.channel()
        
        # Объявляем очередь с использованием общей функции
        queue = await declare_queue(channel, "update_message")
        
        # Логируем информацию о промокоде для отладки
        if hasattr(order_data, 'promo_code_dict'):
            logger.info(f"Для заказа {order_data.id} перед отправкой update_message найден promo_code_dict: {order_data.promo_code_dict}")
        else:
            logger.warning(f"Для заказа {order_data.id} перед отправкой update_message отсутствует promo_code_dict")
            
        if hasattr(order_data, 'promo_code_id') and order_data.promo_code_id:
            logger.info(f"Для заказа {order_data.id} найден promo_code_id: {order_data.promo_code_id}")
        
        # Создаем сообщение
        message_body = create_order_email_content(order_data, new_status_name)  
        
        # Проверяем, что промокод есть в сообщении
        if 'promo_code' in message_body and message_body['promo_code']:
            logger.info(f"Промокод успешно добавлен в сообщение: {message_body['promo_code']}")
        else:
            logger.warning(f"Промокод отсутствует в сообщении для заказа {order_data.id}")
        
        # Отправляем сообщение
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        logger.info(f"RabbitMQ: {json.dumps(message_body, ensure_ascii=False)}")
        return "message_sent"
    finally:
        # Закрываем соединение в любом случае
        await close_connection(connection)

async def notification_message_about_low_stock(
    low_stock_products
):
    """
    Отправляет уведомление о товарах с низким остатком в очередь RabbitMQ
    
    Args:
        low_stock_products: Список товаров с низким остатком, каждый товар содержит id, name и stock
    """
    connection = await get_connection()
    
    try:
        # Создаем канал
        channel = await connection.channel()
        
        # Объявляем очередь с использованием общей функции
        queue = await declare_queue(channel, "notification_message")
        
        # Создаем сообщение
        message_body = create_order_email_content(order_data=low_stock_products)  
        
        # Отправляем сообщение
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        logger.info(f"Отправлено уведомление о {len(low_stock_products)} товарах с низким остатком")
    finally:
        # Закрываем соединение в любом случае
        await close_connection(connection)
