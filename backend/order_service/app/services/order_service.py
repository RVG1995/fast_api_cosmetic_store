import logging
from ..utils.rabbit_utils import get_connection, close_connection, declare_queue
import json
import aio_pika

logger = logging.getLogger(__name__)


def create_order_email_content(order_data, new_status_name=None, stock=None):
    if new_status_name:
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
            "items": [
                    {
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "product_price": item.product_price,
                        "total_price": item.total_price
                    } for item in order_data.items
                ] if order_data.items else []
        }
    elif isinstance(order_data, list):
        # Случай для списка товаров с низким остатком
        message_body = {
            "low_stock_products": order_data
        }
    elif stock is not None:
        # Устаревший случай для одного товара с низким остатком
        message_body = {
            "product_name": order_data,
            "stock": stock
        }
    else:
        message_body = {
            "order_number": order_data.order_number,
            "full_name": order_data.full_name,
            "created_at": order_data.created_at.isoformat() if order_data.created_at else None,
            "status": order_data.status.name if order_data.status else "Неизвестно",
            "total_price": order_data.total_price,
            "is_paid": order_data.is_paid,
            "email": order_data.email,
            "phone": order_data.phone,
            "region": order_data.region,
            "city": order_data.city,
            "street": order_data.street,
            "items": [
                    {
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "product_price": item.product_price,
                        "total_price": item.total_price
                    } for item in order_data.items
                ] if order_data.items else []
        }
    return message_body


async def send_email_message(
    order_data
):
    """
    Отправляет сообщение с данными для email в очередь
    
    Args:
        email: Email получателя
        order_id: Номер заказа
        products: Список продуктов в заказе
    """
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
    finally:
        # Закрываем соединение в любом случае
        await close_connection(connection)


async def update_order_status(
    order_data, new_status_name
):
    """
    Отправляет сообщение об изменении статуса заказа с данными для email в очередь
    
    Args:
        email: Email получателя
        order_id: Номер заказа
        products: Список продуктов в заказе
    """
    connection = await get_connection()
    
    try:
        # Создаем канал
        channel = await connection.channel()
        
        # Объявляем очередь с использованием общей функции
        queue = await declare_queue(channel, "update_message")
        
        # Создаем сообщение
        message_body = create_order_email_content(order_data, new_status_name)  
        
        # Отправляем сообщение
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        logger.info(f"RabbitMQ: {json.dumps(message_body, ensure_ascii=False)}")
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
