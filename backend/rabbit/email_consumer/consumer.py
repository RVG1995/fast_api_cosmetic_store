import asyncio
import json
import os
import logging
import time
from typing import Dict, Any, Callable, List, Optional
from datetime import datetime, timedelta

import aio_pika
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Настройки RabbitMQ
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")

# Настройки для Dead Letter Exchange
DLX_NAME = "dead_letter_exchange"
DLX_QUEUE = "failed_messages"
# Максимальное количество попыток обработки сообщения
MAX_RETRY_COUNT = 3
# Задержка перед повторной попыткой в миллисекундах
RETRY_DELAY_MS = 5000

# Настройки SMTP
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@example.com")

# Путь к директории с шаблонами
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Настройки для реконнекта
MAX_RECONNECT_ATTEMPTS = 10
INITIAL_RECONNECT_DELAY = 1  # Начальная задержка в секундах
MAX_RECONNECT_DELAY = 30     # Максимальная задержка в секундах
CONNECTION_CHECK_INTERVAL = 5  # Интервал проверки соединения в секундах


async def close_connection(connection: aio_pika.Connection) -> None:
    """
    Закрывает соединение с RabbitMQ
    
    Args:
        connection: Соединение с RabbitMQ для закрытия
    """
    if connection and not connection.is_closed:
        await connection.close()
        logger.info("Соединение с RabbitMQ закрыто")


async def send_email(recipient: str, subject: str, html_content: str) -> None:
    """
    Отправляет email с помощью aiosmtplib
    
    Args:
        recipient: Email получателя
        subject: Тема письма
        html_content: HTML-содержимое письма
    """
    # Создаем сообщение
    message = MIMEMultipart()
    message["From"] = SMTP_FROM
    message["To"] = recipient
    message["Subject"] = subject
    
    # Добавляем HTML-содержимое
    message.attach(MIMEText(html_content, "html"))
    
    try:
        # Отправляем письмо
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=True
        )
        logger.info(f"Письмо успешно отправлено на {recipient}")
    except Exception as e:
        logger.error(f"Ошибка при отправке письма: {e}")
        raise


def load_template(template_name: str) -> str:
    """
    Загружает HTML шаблон из файла
    
    Args:
        template_name: Имя файла шаблона (без пути)
    
    Returns:
        str: Содержимое шаблона
    """
    template_path = os.path.join(TEMPLATES_DIR, template_name)
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Ошибка при загрузке шаблона {template_name}: {e}")
        raise


def create_order_email_content(order_data):
    """
    Создает HTML-содержимое для письма с подтверждением заказа
    
    Args:
        order_data (dict): Данные о заказе
        
    Returns:
        str: HTML-содержимое письма
    """
    items_html = ""
    total = 0
    
    for item in order_data.get('items', []):
        price = item.get('product_price', 0)
        quantity = item.get('quantity', 1)
        item_total = price * quantity
        total += item_total
        
        items_html += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item.get('product_name', 'Товар')}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: center;">{quantity}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{price:.2f} ₽</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{item_total:.2f} ₽</td>
        </tr>
        """
    
    # Получаем статус - может быть как строкой, так и словарем
    status = order_data.get('status', 'Новый')
    if isinstance(status, dict):
        status = status.get('name', 'Новый')
    
    # Форматируем дату из ISO формата в читаемый вид
    formatted_date = "Н/Д"
    created_at = order_data.get('created_at', '')
    
    if created_at:
        try:
            # Преобразуем строку в объект datetime
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))           
            # Форматируем дату в виде "день месяц год"
            formatted_date = f"{dt.day}-{dt.month}-{dt.year}"
        except Exception as e:
            logger.warning(f"Ошибка при форматировании даты: {e}")
            formatted_date = created_at.split('T')[0] if 'T' in created_at else created_at
    
    # Информация о промокоде и скидке
    discount_info = ""
    # Берем promo_code из promo_code или promo_code_dict
    promo_code = order_data.get('promo_code') or order_data.get('promo_code_dict')
    discount_amount = order_data.get('discount_amount', 0)
    
    if promo_code and discount_amount > 0:
        discount_percent = promo_code.get('discount_percent')
        if discount_percent:
            discount_info = f"""
            <tr>
                <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка по промокоду {promo_code.get('code')} ({discount_percent}%):</td>
                <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
            </tr>
            """
        else:
            discount_info = f"""
            <tr>
                <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка по промокоду {promo_code.get('code')}:</td>
                <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
            </tr>
            """
    elif discount_amount > 0:
        discount_info = f"""
        <tr>
            <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка:</td>
            <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
        </tr>
        """
    
    # Формируем HTML-шаблон
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Подтверждение заказа #{order_data.get('id')}</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;">
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;">
            <h1 style="color: #4a5568; margin: 0;">Ваш заказ подтвержден</h1>
            <p style="font-size: 18px; margin-top: 10px;">Заказ #{order_data.get('id')}</p>
        </div>
        
        <div style="padding: 0 20px;">
            <p>Здравствуйте, {order_data.get('full_name', 'уважаемый клиент')}!</p>
            <p>Благодарим вас за заказ в нашем магазине. Ваш заказ был успешно создан и находится в обработке.</p>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Данные заказа:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 5px 0; width: 150px;"><strong>Номер заказа:</strong></td>
                    <td>{order_data.get('id')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Дата:</strong></td>
                    <td>{formatted_date}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Статус:</strong></td>
                    <td>{status}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Способ оплаты:</strong></td>
                    <td>{order_data.get('payment_method', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Способ доставки:</strong></td>
                    <td>{order_data.get('delivery_method', 'Н/Д')}</td>
                </tr>
                {f'<tr><td style="padding: 5px 0;"><strong>Промокод:</strong></td><td>{promo_code.get("code")}</td></tr>' if promo_code else ''}
            </table>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Список товаров:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <thead>
                    <tr style="background-color: #f1f5f9;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Наименование</th>
                        <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Кол-во</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Цена</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Сумма</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
                <tfoot>
                    {discount_info}
                    <tr>
                        <td colspan="3" style="padding: 10px; text-align: right; font-weight: bold;">Итого:</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">{order_data.get('total_price', total):.2f} ₽</td>
                    </tr>
                </tfoot>
            </table>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Данные доставки:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <tr>
                    <td style="padding: 5px 0; width: 150px;"><strong>Получатель:</strong></td>
                    <td>{order_data.get('full_name', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Телефон:</strong></td>
                    <td>{order_data.get('phone', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Email:</strong></td>
                    <td>{order_data.get('email', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Адрес доставки:</strong></td>
                    <td>
                        {order_data.get('region', '')}, 
                        {order_data.get('city', '')}, 
                        {order_data.get('street', '')},
                    </td>
                </tr>
            </table>
            
            <p>Мы свяжемся с вами, как только заказ будет готов к отправке.</p>
            <p>Если у вас возникли вопросы по заказу, напишите нам на электронную почту или позвоните по телефону поддержки.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px;">
                <p>С уважением,<br>Команда "Косметик-стор"</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


def create_status_update_email_content(order_data):
    """
    Создает HTML-содержимое для письма с уведомлением об изменении статуса заказа
    
    Args:
        order_data (dict): Данные о заказе
        
    Returns:
        str: HTML-содержимое письма
    """
    # Получаем статус - может быть как строкой, так и словарем
    status = order_data.get('status', 'Новый')
    if isinstance(status, dict):
        status = status.get('name', 'Новый')

    # Отладочное логирование для промокода и скидки
    # Берем promo_code из promo_code или promo_code_dict
    promo_code = order_data.get('promo_code') or order_data.get('promo_code_dict')
    discount_amount = order_data.get('discount_amount', 0)
    
    if promo_code:
        logger.info(f"Промокод в create_status_update_email_content: {promo_code}")
    else:
        logger.warning(f"Промокод отсутствует в create_status_update_email_content для заказа {order_data.get('order_number')}")
        
    logger.info(f"Сумма скидки в create_status_update_email_content: {discount_amount}")

    # Формируем таблицу с товарами
    items_html = ""
    total = 0
    
    for item in order_data.get('items', []):
        price = item.get('product_price', 0)
        quantity = item.get('quantity', 1)
        item_total = price * quantity
        total += item_total
        
        items_html += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item.get('product_name', 'Товар')}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: center;">{quantity}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{price:.2f} ₽</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">{item_total:.2f} ₽</td>
        </tr>
        """

    # Форматируем дату из ISO формата в читаемый вид
    formatted_date = "Н/Д"
    created_at = order_data.get('created_at', '')
    
    if created_at:
        try:
            # Преобразуем строку в объект datetime
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))           
            # Словарь с русскими названиями месяцев
            months = {
                1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
                5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
                9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
            }
            
            # Форматируем дату в виде "день месяц год"
            formatted_date = f"{dt.day} {months[dt.month]} {dt.year}"
        except Exception as e:
            logger.warning(f"Ошибка при форматировании даты: {e}")
            formatted_date = created_at.split('T')[0] if 'T' in created_at else created_at

    # Информация о промокоде и скидке
    discount_info = ""
    
    if promo_code and discount_amount > 0:
        discount_percent = promo_code.get('discount_percent')
        if discount_percent:
            discount_info = f"""
            <tr>
                <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка по промокоду {promo_code.get('code')} ({discount_percent}%):</td>
                <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
            </tr>
            """
        else:
            discount_info = f"""
            <tr>
                <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка по промокоду {promo_code.get('code')}:</td>
                <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
            </tr>
            """
    elif discount_amount > 0:
        discount_info = f"""
        <tr>
            <td colspan="3" style="padding: 10px; text-align: right; font-style: italic;">Скидка:</td>
            <td style="padding: 10px; text-align: right; font-style: italic;">-{discount_amount:.2f} ₽</td>
        </tr>
        """
        
    # Формируем HTML-шаблон
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Изменение статуса заказа #{order_data.get('order_number')}</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;">
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;">
            <h1 style="color: #4a5568; margin: 0;">Статус заказа изменен</h1>
            <p style="font-size: 18px; margin-top: 10px;">Заказ #{order_data.get('order_number')}</p>
        </div>
        
        <div style="padding: 0 20px;">
            <p>Здравствуйте, {order_data.get('full_name', 'уважаемый клиент')}!</p>
            <p>Статус вашего заказа был изменен на <strong>"{status}"</strong>.</p>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Данные заказа:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 5px 0; width: 150px;"><strong>Номер заказа:</strong></td>
                    <td>{order_data.get('order_number')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Дата:</strong></td>
                    <td>{formatted_date}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Новый статус:</strong></td>
                    <td><strong>{status}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Сумма заказа:</strong></td>
                    <td>{order_data.get('total_price', 0):.2f} ₽</td>
                </tr>
                {f'<tr><td style="padding: 5px 0;"><strong>Промокод:</strong></td><td>{promo_code.get("code")}</td></tr>' if promo_code else ''}
            </table>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Список товаров:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <thead>
                    <tr style="background-color: #f1f5f9;">
                        <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Наименование</th>
                        <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Кол-во</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Цена</th>
                        <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Сумма</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
                <tfoot>
                    {discount_info}
                    <tr>
                        <td colspan="3" style="padding: 10px; text-align: right; font-weight: bold;">Итого:</td>
                        <td style="padding: 10px; text-align: right; font-weight: bold;">{order_data.get('total_price', total):.2f} ₽</td>
                    </tr>
                </tfoot>
            </table>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Данные доставки:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <tr>
                    <td style="padding: 5px 0; width: 150px;"><strong>Получатель:</strong></td>
                    <td>{order_data.get('full_name', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Телефон:</strong></td>
                    <td>{order_data.get('phone', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Email:</strong></td>
                    <td>{order_data.get('email', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Адрес доставки:</strong></td>
                    <td>
                        {order_data.get('region', '')}, 
                        {order_data.get('city', '')}, 
                        {order_data.get('street', '')},
                    </td>
                </tr>
            </table>
            
            <p>Если у вас возникли вопросы по заказу, напишите нам на электронную почту или позвоните по телефону поддержки.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px;">
                <p>С уважением,<br>Команда "Косметик-стор"</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


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
            logger.info(f"Повторная попытка {retry_count}/{MAX_RETRY_COUNT} для сообщения email_message: {message_body}")
        else:
            logger.info(f"Получено сообщение email_message: {message_body}")
        
        # Извлекаем необходимые данные
        email = message_body["email"]
        order_number = message_body.get("id") or message_body.get("id")
        
        # Формируем содержимое письма
        subject = f"Подтверждение заказа #{order_number}"
        html_content = create_order_email_content(message_body)
        
        # Отправляем письмо
        await send_email(email, subject, html_content)
        
        logger.info(f"Сообщение для заказа {order_number} успешно обработано")
        
        # Подтверждаем успешную обработку
        await message.ack()
    except Exception as e:
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
            logger.info(f"Сообщение помещено в очередь {retry_queue} для повторной попытки {retry_count}/{MAX_RETRY_COUNT}")
            await message.ack()
        else:
            # Отклоняем сообщение, чтобы оно попало в DLX
            logger.warning(f"Превышено количество попыток ({MAX_RETRY_COUNT}). Сообщение будет перемещено в DLX.")
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
            logger.info(f"Повторная попытка {retry_count}/{MAX_RETRY_COUNT} для сообщения notification_message")
        else:
            logger.info(f"Получено уведомление о товарах с низким остатком")
        
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
            
            logger.info(f"Уведомление о {len(low_stock_products)} товарах с низким остатком успешно отправлено на {admin_email}")
        
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
            
            logger.info(f"Уведомление о низком остатке товара '{product_name}' (остаток: {stock}) успешно отправлено на {admin_email}")
        
        else:
            logger.error("Некорректный формат сообщения об остатке товаров")
        
        # Подтверждаем успешную обработку
        await message.ack()
    except Exception as e:
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
            logger.info(f"Сообщение помещено в очередь {retry_queue} для повторной попытки {retry_count}/{MAX_RETRY_COUNT}")
            await message.ack()
        else:
            # Отклоняем сообщение, чтобы оно попало в DLX
            logger.warning(f"Превышено количество попыток ({MAX_RETRY_COUNT}). Сообщение будет перемещено в DLX.")
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
            logger.info(f"Повторная попытка {retry_count}/{MAX_RETRY_COUNT} для сообщения update_message: {message_body}")
        else:
            logger.info(f"Получено сообщение update_message: {message_body}")
        
        # Добавляем отладочное логирование для промокода
        if 'promo_code' in message_body:
            logger.info(f"Промокод в update_message: {message_body['promo_code']}")
        else:
            logger.warning(f"Промокод отсутствует в update_message для заказа {message_body.get('order_number')}")
            
        if 'discount_amount' in message_body:
            logger.info(f"Сумма скидки в update_message: {message_body['discount_amount']}")
            
        # Извлекаем необходимые данные
        email = message_body["email"]
        order_number = message_body["order_number"]
        
        # Формируем содержимое письма
        subject = f"Обновление статуса заказа #{order_number}"
        html_content = create_status_update_email_content(message_body)
        
        # Отправляем письмо
        await send_email(email, subject, html_content)
        
        logger.info(f"Сообщение для заказа {order_number} успешно обработано")
        
        # Подтверждаем успешную обработку
        await message.ack()
    except Exception as e:
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
            logger.info(f"Сообщение помещено в очередь {retry_queue} для повторной попытки {retry_count}/{MAX_RETRY_COUNT}")
            await message.ack()
        else:
            # Отклоняем сообщение, чтобы оно попало в DLX
            logger.warning(f"Превышено количество попыток ({MAX_RETRY_COUNT}). Сообщение будет перемещено в DLX.")
            await message.reject(requeue=False)


def create_registration_email_content(activation_data):
    """
    Создает HTML-содержимое для письма с подтверждением регистрации
    
    Args:
        activation_data (dict): Данные для активации аккаунта
        
    Returns:
        str: HTML-содержимое письма
    """
    activation_link = activation_data.get('activation_link', '#')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Подтверждение регистрации</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;">
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;">
            <h1 style="color: #4a5568; margin: 0;">Подтверждение регистрации</h1>
            <p style="font-size: 18px; margin-top: 10px;">Kosmetik-Store</p>
        </div>
        
        <div style="padding: 0 20px;">
            <p>Здравствуйте!</p>
            <p>Благодарим вас за регистрацию в интернет-магазине Kosmetik-Store.</p>
            <p>Для завершения регистрации и активации вашей учетной записи, пожалуйста, нажмите на кнопку ниже:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{activation_link}" style="background-color: #4a5568; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;">Подтвердить регистрацию</a>
            </div>
            
            <p>Если кнопка не работает, скопируйте и вставьте следующую ссылку в адресную строку браузера:</p>
            <p style="word-break: break-all; background-color: #f1f5f9; padding: 10px; border-radius: 4px;">{activation_link}</p>
            
            <p>Если вы не регистрировались на нашем сайте, проигнорируйте это письмо.</p>
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px;">
                <p>С уважением,<br>Команда "Косметик-стор"</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html


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
            logger.info(f"Повторная попытка {retry_count}/{MAX_RETRY_COUNT} для сообщения registration_message")
        else:
            logger.info(f"Получено сообщение registration_message: {message_body}")
        
        # Извлекаем необходимые данные
        email = message_body["email"]
        user_id = message_body["user_id"]
        activation_link = message_body["activation_link"]
        
        # Формируем содержимое письма
        subject = "Подтверждение регистрации на сайте Kosmetik-Store"
        html_content = create_registration_email_content(message_body)
        
        # Отправляем письмо
        await send_email(email, subject, html_content)
        
        logger.info(f"Сообщение для пользователя {user_id} успешно обработано")
        
        # Подтверждаем успешную обработку
        await message.ack()
    except Exception as e:
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
            logger.info(f"Сообщение помещено в очередь {retry_queue} для повторной попытки {retry_count}/{MAX_RETRY_COUNT}")
            await message.ack()
        else:
            # Отклоняем сообщение, чтобы оно попало в DLX
            logger.warning(f"Превышено количество попыток ({MAX_RETRY_COUNT}). Сообщение будет перемещено в DLX.")
            await message.reject(requeue=False)


def create_password_reset_email_content(reset_data):
    reset_link = reset_data.get('reset_link', '#')
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='UTF-8'>
        <title>Сброс пароля</title>
    </head>
    <body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;'>
        <div style='background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;'>
            <h1 style='color: #4a5568; margin: 0;'>Сброс пароля</h1>
            <p style='font-size: 18px; margin-top: 10px;'>Kosmetik-Store</p>
        </div>
        <div style='padding: 0 20px;'>
            <p>Здравствуйте!</p>
            <p>Вы запросили сброс пароля для своей учетной записи.</p>
            <p>Для установки нового пароля, пожалуйста, нажмите на кнопку ниже:</p>
            <div style='text-align: center; margin: 30px 0;'>
                <a href='{reset_link}' style='background-color: #4a5568; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;'>Сбросить пароль</a>
            </div>
            <p>Если кнопка не работает, скопируйте и вставьте следующую ссылку в адресную строку браузера:</p>
            <p style='word-break: break-all; background-color: #f1f5f9; padding: 10px; border-radius: 4px;'>{reset_link}</p>
            <p>Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.</p>
            <div style='margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; color: #718096; font-size: 14px;'>
                <p>С уважением,<br>Команда "Косметик-стор"</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


async def password_reset_message(message: aio_pika.IncomingMessage) -> None:
    try:
        message_body = json.loads(message.body.decode())
        email = message_body["email"]
        user_id = message_body["user_id"]
        reset_link = message_body["reset_link"]
        subject = "Сброс пароля на сайте Kosmetik-Store"
        html_content = create_password_reset_email_content(message_body)
        await send_email(email, subject, html_content)
        logger.info(f"Сообщение для сброса пароля пользователя {user_id} успешно обработано")
        await message.ack()
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения сброса пароля: {e}")
        await message.reject(requeue=False)


# Определяем словарь с очередями и их обработчиками
QUEUE_HANDLERS = {
    "email_message": process_email_message,
    "update_message": update_status_email_message,
    "notification_message": notification_message,
    "registration_message": registration_message,
    "password_reset_message": password_reset_message,
    # Можно добавить больше очередей и их обработчиков здесь
}


async def get_connection_with_retry() -> aio_pika.Connection:
    """
    Устанавливает соединение с RabbitMQ с механизмом повторных попыток
    при неудаче
    
    Returns:
        aio_pika.Connection: Установленное соединение
    """
    reconnect_delay = INITIAL_RECONNECT_DELAY
    attempts = 0
    
    while attempts < MAX_RECONNECT_ATTEMPTS:
        try:
            connection = await aio_pika.connect_robust(
                host=RABBITMQ_HOST,
                login=RABBITMQ_USER,
                password=RABBITMQ_PASS
            )
            logger.info("Соединение с RabbitMQ установлено успешно")
            return connection
        except Exception as e:
            attempts += 1
            logger.error(f"Ошибка подключения к RabbitMQ ({attempts}/{MAX_RECONNECT_ATTEMPTS}): {e}")
            
            if attempts >= MAX_RECONNECT_ATTEMPTS:
                logger.critical("Превышено максимальное количество попыток подключения")
                raise
            
            logger.info(f"Повторная попытка через {reconnect_delay} сек...")
            await asyncio.sleep(reconnect_delay)
            
            # Экспоненциальное увеличение задержки с ограничением
            reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)


class RabbitMQConsumer:
    """Класс для управления подключением и потреблением сообщений из RabbitMQ"""
    
    def __init__(self, queue_handlers: Dict[str, Callable]):
        """
        Инициализирует consumer
        
        Args:
            queue_handlers: Словарь с именами очередей и их обработчиками
        """
        self.queue_handlers = queue_handlers
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.is_running = False
        self.connection_check_task: Optional[asyncio.Task] = None
        self._running_future: Optional[asyncio.Future] = None
        
    async def setup(self) -> None:
        """Устанавливает соединение и настраивает канал"""
        self.connection = await get_connection_with_retry()
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=10)
        
    async def check_connection(self) -> None:
        """Периодически проверяет состояние соединения и восстанавливает его при необходимости"""
        while self.is_running:
            try:
                # Проверяем, работает ли соединение
                if self.connection and self.connection.is_closed:
                    logger.warning("Обнаружено закрытое соединение. Запуск переподключения...")
                    await self._reconnect()
                
                # Ждем перед следующей проверкой
                await asyncio.sleep(CONNECTION_CHECK_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка при проверке соединения: {e}")
                await asyncio.sleep(INITIAL_RECONNECT_DELAY)
    
    async def _reconnect(self) -> None:
        """Процедура переподключения при разрыве соединения"""
        try:
            # Закрываем старое соединение, если оно еще открыто
            if self.connection and not self.connection.is_closed:
                await close_connection(self.connection)
                
            # Устанавливаем новое соединение
            await self.setup()
            await self._setup_consumers()
            logger.info("Переподключение выполнено успешно")
        except Exception as e:
            logger.error(f"Ошибка при переподключении: {e}")
    
    async def _setup_consumers(self) -> None:
        """Настраивает потребителей сообщений для всех очередей"""
        try:
            # Создаем Dead Letter Exchange
            dlx = await self.channel.declare_exchange(
                DLX_NAME,
                aio_pika.ExchangeType.DIRECT,
                durable=True
            )
            
            # Создаем очередь для неудачных сообщений
            failed_queue = await self.channel.declare_queue(
                DLX_QUEUE,
                durable=True
            )
            
            # Привязываем очередь к DLX для всех маршрутов
            await failed_queue.bind(dlx, routing_key="#")
            logger.info(f"Настроен Dead Letter Exchange {DLX_NAME} и очередь {DLX_QUEUE}")
            
            # Настраиваем обработчики для основных очередей
            for queue_name, handler in self.queue_handlers.items():
                # Создаем очередь для отложенных сообщений (retry)
                retry_queue_name = f"{queue_name}.retry"
                retry_queue = await self.channel.declare_queue(
                    retry_queue_name,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": "",  # Используем default exchange
                        "x-dead-letter-routing-key": queue_name,  # Возвращаем в оригинальную очередь
                        "x-message-ttl": RETRY_DELAY_MS  # Задержка перед повторной попыткой
                    }
                )
                
                # Создаем основную очередь с DLX
                queue = await self.channel.declare_queue(
                    queue_name,
                    durable=True,
                    arguments={
                        "x-dead-letter-exchange": DLX_NAME,
                        "x-dead-letter-routing-key": queue_name
                    }
                )
                
                await queue.consume(handler)
                logger.info(f"Настроен обработчик для очереди {queue_name} с поддержкой DLX")
        except Exception as e:
            logger.error(f"Ошибка при настройке очередей: {e}")
            raise
    
    async def start(self) -> None:
        """Запускает consumer"""
        self.is_running = True
        await self.setup()
        await self._setup_consumers()
        
        # Запускаем задачу проверки соединения
        self.connection_check_task = asyncio.create_task(self.check_connection())
        
        logger.info(f"Consumer запущен. Ожидание сообщений из {len(self.queue_handlers)} очередей")
        
        # Создаем Future, который никогда не завершится, чтобы процесс не завершался
        self._running_future = asyncio.Future()
        try:
            await self._running_future
        except asyncio.CancelledError:
            self.is_running = False
            logger.info("Consumer остановлен")
    
    async def stop(self) -> None:
        """Останавливает consumer"""
        self.is_running = False
        
        # Останавливаем задачу проверки соединения
        if self.connection_check_task and not self.connection_check_task.done():
            self.connection_check_task.cancel()
            try:
                await self.connection_check_task
            except asyncio.CancelledError:
                pass
        
        # Останавливаем основной цикл
        if hasattr(self, '_running_future') and self._running_future and not self._running_future.done():
            self._running_future.cancel()
            try:
                await self._running_future
            except asyncio.CancelledError:
                pass
        
        # Закрываем соединение
        if self.connection:
            await close_connection(self.connection)


async def main() -> None:
    """Основная функция для запуска consumer"""
    consumer = RabbitMQConsumer(QUEUE_HANDLERS)
    
    try:
        await consumer.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Consumer остановлен пользователем") 