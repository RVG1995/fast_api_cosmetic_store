"""
Сервис уведомлений для обработки и отправки различных типов уведомлений через RabbitMQ.
"""

import logging
import sys
import os
from typing import Optional

import json
import aio_pika
from .rabbit_utils import get_connection, close_connection, declare_queue

# Путь до директории backend/order_service
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, current_dir)

logger = logging.getLogger(__name__)


def create_order_email_content(order_data, new_status_name=None, stock=None):
    """
    Создает содержимое email-сообщения на основе данных заказа.
    
    Args:
        order_data: Данные заказа
        new_status_name: Новый статус заказа (опционально)
        stock: Количество товара на складе (опционально)
        
    Returns:
        dict: Словарь с данными для email-сообщения
    """
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
    order_data, new_status_name, token=None
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
        
        # Подготовка информации о заказе для логов (словарь или объект)
        if isinstance(order_data, dict):
            order_id = order_data.get('id') or order_data.get('order_number')
            promo_code = order_data.get('promo_code') or order_data.get('promo_code_dict')
        else:
            order_id = getattr(order_data, 'id', None)
            promo_code = getattr(order_data, 'promo_code_dict', None)
        if promo_code:
            logger.info("Для заказа %s найден promo_code: %s", order_id, promo_code)
        else:
            logger.warning("Для заказа %s перед отправкой update_message отсутствует promo_code", order_id)

        # Формируем тело сообщения для RabbitMQ
        if isinstance(order_data, dict):
            message_body = dict(order_data)
            message_body['status'] = new_status_name
            message_body['event_type'] = 'order.status_changed'
        else:
            message_body = create_order_email_content(order_data, new_status_name)
        
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

async def notification_message_about_low_stock(
    low_stock_products,
    user_id: Optional[str] = None,
    token: Optional[str] = None
):
    """
    Отправляет уведомление о товарах с низким остатком в очередь RabbitMQ
    
    Args:
        low_stock_products: Список товаров с низким остатком, каждый товар содержит id, name и stock
        user_id: ID пользователя для проверки настроек уведомлений (для обратной совместимости)
        token: JWT токен для авторизации в сервисе уведомлений
    """
    # Получение списка администраторов
    admins = await notification_api.get_admin_users(token)
    
    if not admins:
        logger.warning("Не найдены администраторы для отправки уведомлений о низком остатке товаров")
        # Если администраторы не найдены, используем старую логику с одним пользователем
        if user_id:
            settings = await notification_api.check_notification_settings(user_id, "product.low_stock", token)
            if settings["email_enabled"]:
                await _send_low_stock_notification(low_stock_products)
            else:
                logger.info("Email уведомления о низком остатке товаров отключены для пользователя %s, email не будет отправлен", user_id)
        else:
            # Если не указан ID пользователя и нет администраторов, отправляем уведомление по умолчанию
            await _send_low_stock_notification(low_stock_products)
        return
    
    # Флаг для отслеживания, было ли отправлено хотя бы одно уведомление
    notification_sent = False
    
    # Отправка уведомлений всем администраторам с включенными уведомлениями
    for admin in admins:
        admin_id = str(admin.get("id"))
        settings = await notification_api.check_notification_settings(admin_id, "product.low_stock", token)
        
        if settings["email_enabled"]:
            # Если ещё не отправили уведомление - отправляем его
            if not notification_sent:
                await _send_low_stock_notification(low_stock_products)
                notification_sent = True
            logger.info("Отправлено уведомление о низком остатке товаров администратору %s", admin_id)
        else:
            logger.info("Email уведомления о низком остатке товаров отключены для администратора %s", admin_id)
            
    if not notification_sent:
        logger.warning("Ни один администратор не имеет включенных уведомлений о низком остатке товаров")

# Вспомогательная функция для фактической отправки уведомления
async def _send_low_stock_notification(low_stock_products):
    """
    Вспомогательная функция для отправки уведомления о низком остатке товаров
    
    Args:
        low_stock_products: Список товаров с низким остатком
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
        logger.info("Отправлено уведомление о %d товарах с низким остатком", len(low_stock_products))
    finally:
        # Закрываем соединение в любом случае
        await close_connection(connection)
