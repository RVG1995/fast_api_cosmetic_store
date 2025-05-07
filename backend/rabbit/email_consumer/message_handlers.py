"""
Обработчики сообщений из разных очередей RabbitMQ.
"""
import json
import os
import asyncio
import logging
import httpx

import aio_pika

from config import logger, MAX_RETRY_COUNT
from email_utils import send_email
from email_templates import (
    create_order_email_content,
    create_status_update_email_content,
    create_registration_email_content, 
    create_password_reset_email_content
)
from connection_utils import get_connection_with_retry, close_connection
from orders_api import check_order_info


async def process_email_message(message: aio_pika.IncomingMessage) -> None:
    """
    Обрабатывает входящее сообщение из очереди email_message
    
    Args:
        message: Сообщение из очереди
    """
    try:
        # Получаем данные сообщения
        message_body = json.loads(message.body.decode())
        
        # Проверяем счетчик попыток
        headers = message.headers or {}
        retry_count = headers.get('x-retry-count', 0)
        if retry_count > 0:
            logger.info("Повторная попытка %d/%d для сообщения email_message: %s", retry_count, MAX_RETRY_COUNT, message_body)
        else:
            logger.info("Получено сообщение email_message: %s", message_body)
        
        # Извлекаем необходимые данные
        order_number = message_body["order_id"]

        # Получаем информацию о заказе
        order_info = await check_order_info(order_number)
        if not order_info:
            logger.warning("Не удалось получить информацию о заказе %s", order_number)
            await message.reject(requeue=False)
            return


        
        # Формируем содержимое письма
        subject = f"Подтверждение заказа {order_info.get('order_number')}"
        html_content = create_order_email_content(order_info)
        
        # Отправляем письмо
        await send_email(order_info.get('email'), subject, html_content)
        
        logger.info("Сообщение для заказа %s успешно обработано", order_number)
        
        # Подтверждаем успешную обработку
        await message.ack()
    except (aio_pika.exceptions.AMQPException, json.JSONDecodeError, asyncio.TimeoutError, ValueError) as e:
        error_msg = f"Ошибка при обработке сообщения: {e}"
        logger.error(error_msg)
        
        # Проверяем счетчик повторных попыток
        headers = message.headers or {}
        retry_count = headers.get('x-retry-count', 0)
        
        if retry_count < MAX_RETRY_COUNT:
            # Увеличиваем счетчик попыток
            retry_count += 1
            headers['x-retry-count'] = retry_count
            headers['x-last-error'] = str(e)
            
            # Публикуем в очередь retry через новое соединение
            retry_connection = await get_connection_with_retry()
            retry_channel = await retry_connection.channel()
            retry_queue = f"email_message.retry"
            await retry_channel.default_exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    headers=headers,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=retry_queue
            )
            await close_connection(retry_connection)
            logger.info("Сообщение помещено в очередь %s для повторной попытки %d/%d", retry_queue, retry_count, MAX_RETRY_COUNT)
            await message.ack()
        else:
            # Отклоняем сообщение, чтобы оно попало в DLX
            logger.warning("Превышено количество попыток (%d). Сообщение будет перемещено в DLX.", MAX_RETRY_COUNT)
            await message.reject(requeue=False)


async def notification_message(message: aio_pika.IncomingMessage) -> None:
    """
    Обрабатывает входящее сообщение c уведомлением о низком остатке товаров
    
    Args:
        message: Сообщение из очереди
    """
    try:
        # Получаем данные сообщения
        message_body = json.loads(message.body.decode())
        
        # Проверяем счетчик попыток
        headers = message.headers or {}
        retry_count = headers.get('x-retry-count', 0)
        if retry_count > 0:
            logger.info("Повторная попытка %d/%d для сообщения notification_message", retry_count, MAX_RETRY_COUNT)
        else:
            logger.info("Получено уведомление о товарах с низким остатком")
        
        # Извлекаем необходимые данные
        if "low_stock_products" in message_body:
            low_stock_products = message_body["low_stock_products"]
            
            # Формируем содержимое письма для администратора
            admin_email = os.getenv("ADMIN_EMAIL", "rvg95@mail.ru")
            subject = f"Внимание! Товары с низким остатком ({len(low_stock_products)} шт.)"
            
            # Создаем HTML-таблицу с товарами
            products_table = ""
            for product in low_stock_products:
                products_table += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd;">{product['id']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd;">{product['name']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: center; 
                        color: {'red' if product['stock'] < 5 else 'orange'}; font-weight: bold;">
                        {product['stock']}
                    </td>
                </tr>
                """
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Низкий остаток товаров</title>
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;">
                <div style="background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;">
                    <h1 style="color: #e53e3e; margin: 0;">Внимание! Товары с низким остатком</h1>
                </div>
                
                <div style="padding: 0 20px;">
                    <p>Следующие товары имеют низкий остаток и требуют пополнения:</p>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <thead>
                            <tr style="background-color: #f1f5f9;">
                                <th style="padding: 10px; border: 1px solid #ddd;">ID</th>
                                <th style="padding: 10px; border: 1px solid #ddd;">Наименование</th>
                                <th style="padding: 10px; border: 1px solid #ddd;">Остаток</th>
                            </tr>
                        </thead>
                        <tbody>
                            {products_table}
                        </tbody>
                    </table>
                    
                    <p>Необходимо пополнить запасы данных товаров в ближайшее время.</p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px;">
                        <p>С уважением,<br>Система уведомлений Kosmetik-Store</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Отправляем письмо администратору
            await send_email(admin_email, subject, html_content)
            
            logger.info("Уведомление о %d товарах с низким остатком успешно отправлено на %s", len(low_stock_products), admin_email)
        
        # Обработка устаревшего формата сообщения (для обратной совместимости)
        elif "product_name" in message_body and "stock" in message_body:
            product_name = message_body["product_name"]
            stock = message_body["stock"]
            
            # Формируем содержимое письма для администратора
            admin_email = os.getenv("ADMIN_EMAIL", "rvg95@mail.ru")
            subject = f"Внимание! Низкий остаток товара: {product_name}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Низкий остаток товара</title>
            </head>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;">
                <div style="background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;">
                    <h1 style="color: #e53e3e; margin: 0;">Внимание! Низкий остаток товара</h1>
                </div>
                
                <div style="padding: 0 20px;">
                    <p><strong>Товар:</strong> {product_name}</p>
                    <p><strong>Текущий остаток:</strong> {stock} шт.</p>
                    <p>Необходимо пополнить запасы данного товара в ближайшее время.</p>
                    
                    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px;">
                        <p>С уважением,<br>Система уведомлений Kosmetik-Store</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Отправляем письмо администратору
            await send_email(admin_email, subject, html_content)
            
            logger.info("Уведомление о низком остатке товара '%s' (остаток: %s) успешно отправлено на %s", product_name, stock, admin_email)
        
        else:
            logger.error("Некорректный формат сообщения об остатке товаров")
        
        # Подтверждаем успешную обработку
        await message.ack()
    except (aio_pika.exceptions.AMQPException, json.JSONDecodeError, asyncio.TimeoutError, ValueError) as e:
        error_msg = f"Ошибка при обработке уведомления: {e}"
        logger.error(error_msg)
        
        # Проверяем счетчик повторных попыток
        headers = message.headers or {}
        retry_count = headers.get('x-retry-count', 0)
        
        if retry_count < MAX_RETRY_COUNT:
            # Увеличиваем счетчик попыток
            retry_count += 1
            headers['x-retry-count'] = retry_count
            headers['x-last-error'] = str(e)
            
            # Публикуем в очередь retry через новое соединение
            retry_connection = await get_connection_with_retry()
            retry_channel = await retry_connection.channel()
            retry_queue = f"notification_message.retry"
            await retry_channel.default_exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    headers=headers,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=retry_queue
            )
            await close_connection(retry_connection)
            logger.info("Сообщение помещено в очередь %s для повторной попытки %d/%d", retry_queue, retry_count, MAX_RETRY_COUNT)
            await message.ack()
        else:
            # Отклоняем сообщение, чтобы оно попало в DLX
            logger.warning("Превышено количество попыток (%d). Сообщение будет перемещено в DLX.", MAX_RETRY_COUNT)
            await message.reject(requeue=False)


async def update_status_email_message(message: aio_pika.IncomingMessage) -> None:
    """
    Обрабатывает входящее сообщение из очереди update_message
    
    Args:
        message: Сообщение из очереди
    """
    try:
        # Получаем данные сообщения
        message_body = json.loads(message.body.decode())
        
        # Проверяем счетчик попыток
        headers = message.headers or {}
        retry_count = headers.get('x-retry-count', 0)
        if retry_count > 0:
            logger.info("Повторная попытка %d/%d для сообщения update_message: %s", retry_count, MAX_RETRY_COUNT, message_body)
        else:
            logger.info("Получено сообщение update_message: %s", message_body)
        
        # Извлекаем необходимые данные
        order_number = message_body["order_id"]

        # Получаем информацию о заказе
        order_info = await check_order_info(order_number)
        if not order_info:
            logger.warning("Не удалось получить информацию о заказе %s", order_number)
            await message.reject(requeue=False)
            return
        
        # Формируем содержимое письма
        subject = f"Обновление статуса заказа {order_info.get('order_number')}"
        html_content = create_status_update_email_content(order_info)
        
        # Отправляем письмо
        await send_email(order_info.get('email'), subject, html_content)
        
        logger.info("Сообщение для заказа %s успешно обработано", order_number)
        
        # Подтверждаем успешную обработку
        await message.ack()
    except (aio_pika.exceptions.AMQPException, json.JSONDecodeError, asyncio.TimeoutError, ValueError) as e:
        error_msg = f"Ошибка при обработке сообщения: {e}"
        logger.error(error_msg)
        
        # Проверяем счетчик повторных попыток
        headers = message.headers or {}
        retry_count = headers.get('x-retry-count', 0)
        
        if retry_count < MAX_RETRY_COUNT:
            # Увеличиваем счетчик попыток
            retry_count += 1
            headers['x-retry-count'] = retry_count
            headers['x-last-error'] = str(e)
            
            # Публикуем в очередь retry через новое соединение
            retry_connection = await get_connection_with_retry()
            retry_channel = await retry_connection.channel()
            retry_queue = f"update_message.retry"
            await retry_channel.default_exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    headers=headers,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=retry_queue
            )
            await close_connection(retry_connection)
            logger.info("Сообщение помещено в очередь %s для повторной попытки %d/%d", retry_queue, retry_count, MAX_RETRY_COUNT)
            await message.ack()
        else:
            # Отклоняем сообщение, чтобы оно попало в DLX
            logger.warning("Превышено количество попыток (%d). Сообщение будет перемещено в DLX.", MAX_RETRY_COUNT)
            await message.reject(requeue=False)


async def registration_message(message: aio_pika.IncomingMessage) -> None:
    """
    Обрабатывает входящее сообщение из очереди registration_message
    
    Args:
        message: Сообщение из очереди
    """
    try:
        # Получаем данные сообщения
        message_body = json.loads(message.body.decode())
        
        # Проверяем счетчик попыток
        headers = message.headers or {}
        retry_count = headers.get('x-retry-count', 0)
        if retry_count > 0:
            logger.info("Повторная попытка %d/%d для сообщения registration_message", retry_count, MAX_RETRY_COUNT)
        else:
            logger.info("Получено сообщение registration_message: %s", message_body)
        
        # Извлекаем необходимые данные
        email = message_body["email"]
        user_id = message_body["user_id"]
        activation_link = message_body["activation_link"]
        
        # Формируем содержимое письма
        subject = "Подтверждение регистрации на сайте Kosmetik-Store"
        html_content = create_registration_email_content(message_body)
        
        # Отправляем письмо
        await send_email(email, subject, html_content)
        
        logger.info("Сообщение для пользователя %s успешно обработано", user_id)
        
        # Подтверждаем успешную обработку
        await message.ack()
    except (aio_pika.exceptions.AMQPException, json.JSONDecodeError, asyncio.TimeoutError, ValueError) as e:
        error_msg = f"Ошибка при обработке сообщения: {e}"
        logger.error(error_msg)
        
        # Проверяем счетчик повторных попыток
        headers = message.headers or {}
        retry_count = headers.get('x-retry-count', 0)
        
        if retry_count < MAX_RETRY_COUNT:
            # Увеличиваем счетчик попыток
            retry_count += 1
            headers['x-retry-count'] = retry_count
            headers['x-last-error'] = str(e)
            
            # Публикуем в очередь retry через новое соединение
            retry_connection = await get_connection_with_retry()
            retry_channel = await retry_connection.channel()
            retry_queue = f"registration_message.retry"
            await retry_channel.default_exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    headers=headers,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=retry_queue
            )
            await close_connection(retry_connection)
            logger.info("Сообщение помещено в очередь %s для повторной попытки %d/%d", retry_queue, retry_count, MAX_RETRY_COUNT)
            await message.ack()
        else:
            # Отклоняем сообщение, чтобы оно попало в DLX
            logger.warning("Превышено количество попыток (%d). Сообщение будет перемещено в DLX.", MAX_RETRY_COUNT)
            await message.reject(requeue=False)


async def password_reset_message(message: aio_pika.IncomingMessage) -> None:
    """
    Обрабатывает входящее сообщение из очереди password_reset_message
    
    Args:
        message: Сообщение из очереди
    """
    try:
        message_body = json.loads(message.body.decode())
        email = message_body["email"]
        user_id = message_body["user_id"]
        reset_link = message_body["reset_link"]
        subject = "Сброс пароля на сайте Kosmetik-Store"
        html_content = create_password_reset_email_content(message_body)
        await send_email(email, subject, html_content)
        logger.info("Сообщение для сброса пароля пользователя %s успешно обработано", user_id)
        await message.ack()
    except (aio_pika.exceptions.AMQPException, json.JSONDecodeError, asyncio.TimeoutError, ValueError) as e:
        error_msg = f"Ошибка при обработке сообщения сброса пароля: {e}"
        logger.error(error_msg)
        await message.reject(requeue=False)


# Определяем словарь с очередями и их обработчиками
QUEUE_HANDLERS = {
    "email_message": process_email_message,
    "update_message": update_status_email_message,
    "notification_message": notification_message,
    "registration_message": registration_message,
    "password_reset_message": password_reset_message,
} 