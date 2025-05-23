"""
Сервис уведомлений для обработки и отправки различных типов уведомлений через RabbitMQ.
"""

import logging
import sys
import os
from typing import Optional

import json
import aio_pika
from rabbit_utils import get_connection, close_connection, declare_queue

# Путь до директории backend/order_service
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, current_dir)

logger = logging.getLogger(__name__)

async def send_email_message(
 order_id: int
):
    """
    Отправляет сообщение с данными для email в очередь
    
    Args:
        order_data: Данные заказа
        token: JWT токен для авторизации в сервисе уведомлений
    """
   
    
    connection = await get_connection()
    
    try:
        # Создаем канал
        channel = await connection.channel()
        
        # Объявляем очередь с использованием общей функции
        queue = await declare_queue(channel, "email_message")

        # Всегда используем переданный dict как тело сообщения

        message_body = {
            "order_id": order_id
        }
        
        # Отправляем сообщение
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        logger.info("RabbitMQ: %s", json.dumps(message_body, ensure_ascii=False))
        return "message_sent"
    finally:
        # Закрываем соединение в любом случае
        await close_connection(connection)


async def update_order_status(
    order_id: int
):
    """
    Отправляет сообщение об изменении статуса заказа с данными для email в очередь
    
    Args:
        order_data: Данные заказа
        new_status_name: Название нового статуса
        token: JWT токен для авторизации в сервисе уведомлений
    """ 
    
    connection = await get_connection()
    
    try:
        # Создаем канал
        channel = await connection.channel()
        
        # Объявляем очередь с использованием общей функции
        queue = await declare_queue(channel, "update_message")
        
        message_body = {
            "order_id": order_id
        }
        
        # Отправляем сообщение
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(message_body).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        logger.info("RabbitMQ: %s", json.dumps(message_body, ensure_ascii=False))
        return "message_sent"
    finally:
        # Закрываем соединение в любом случае
        await close_connection(connection)



# Новая функция для отправки уведомлений в RabbitMQ
async def send_notification_to_rabbit(data: dict):
    """
    Отправляет данные для уведомления в очередь RabbitMQ
    
    Args:
        data: Словарь с данными для отправки
            Для уведомлений о низком остатке товаров:
            {
                "low_stock_products": [
                    {"id": int, "name": str, "stock": int},
                    ...
                ]
            }
    
    Returns:
        str: "message_sent" если успешно отправлено
    """
    connection = await get_connection()
    
    try:
        # Создаем канал
        channel = await connection.channel()
        
        # Объявляем очередь для уведомлений
        queue = await declare_queue(channel, "notification_message")
        
        # Отправляем сообщение
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(data).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue.name
        )
        
        logger.info("RabbitMQ: %s", json.dumps(data, ensure_ascii=False))
        return "message_sent"
    except Exception as e:
        logger.error("Ошибка при отправке сообщения в RabbitMQ: %s", str(e))
        raise
    finally:
        # Закрываем соединение в любом случае
        await close_connection(connection)
