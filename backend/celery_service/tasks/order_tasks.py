import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
import httpx
from email.message import EmailMessage
import aiosmtplib
import asyncio
import json

# Добавляем родительскую директорию в sys.path, если её ещё нет
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Импортируем celery_app
from celery_app import app

logger = logging.getLogger(__name__)
ORDER_SERVICE_URL = os.getenv('ORDER_SERVICE_URL', 'http://localhost:8003')
# Сервисный API-ключ для внутренней авторизации между микросервисами
SERVICE_API_KEY = os.getenv('SERVICE_API_KEY', 'service_secret_key_for_internal_use')

# Получаем конфигурацию почтового сервера из переменных окружения
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_PORT = int(os.getenv("MAIL_PORT", 465))
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "False").lower() == "true"
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "True").lower() == "true"
MAIL_TIMEOUT = int(os.getenv("MAIL_TIMEOUT", 30))  # Таймаут по умолчанию 30 секунд

@app.task(name='order.process_abandoned_orders', bind=True, queue='order')
def process_abandoned_orders(self, hours=24):
    """
    Задача для обработки заброшенных заказов (не оплаченных в течение определенного времени).
    
    Args:
        hours (int): Количество часов, после которых неоплаченный заказ считается заброшенным
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Запуск обработки заброшенных заказов старше {hours} часов")
    try:
        # В реальной реализации здесь будет HTTP-запрос к order_service
        # или прямое обращение к базе данных
        
        # Временная заглушка
        return {
            "status": "success", 
            "message": f"Обработка заброшенных заказов выполнена", 
            "processed_count": 0
        }
    
    except Exception as e:
        logger.error(f"Ошибка при обработке заброшенных заказов: {str(e)}")
        self.retry(exc=e, countdown=60 * 10, max_retries=3)  # Повторная попытка через 10 минут


@app.task(name='order.send_order_confirmation', bind=True, queue='order')
def send_order_confirmation(self, order_id, email):
    """
    Задача для отправки подтверждения заказа по электронной почте.
    
    Args:
        order_id (str): ID заказа
        email (str): Email адрес для отправки подтверждения
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Отправка подтверждения заказа {order_id} на email {email}")
    try:
        # Получаем данные о заказе через API
        order_data = get_order_data(order_id)
        if not order_data:
            logger.error(f"Не удалось получить данные заказа {order_id}")
            raise ValueError(f"Заказ {order_id} не найден")
        
        # Создаем сообщение
        message = EmailMessage()
        message["From"] = MAIL_FROM
        message["To"] = email
        message["Subject"] = f"Подтверждение заказа #{order_id}"
        
        # Форматируем содержимое письма
        html_content = create_order_email_content(order_data)
        message.set_content(html_content, subtype='html')
        
        # Отправка email через SMTP
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def send_mail():
            # Создаем SMTP клиент с нужными параметрами
            smtp_client = aiosmtplib.SMTP(
                hostname=MAIL_SERVER, 
                port=MAIL_PORT,
                use_tls=MAIL_SSL_TLS,
                timeout=MAIL_TIMEOUT  # Используем таймаут из переменных окружения
            )
                
            try:
                logger.info(f"Подключение к SMTP серверу {MAIL_SERVER}:{MAIL_PORT}, SSL/TLS: {MAIL_SSL_TLS}")
                await smtp_client.connect()
                
                # Если нужен STARTTLS (обычно для порта 587)
                if MAIL_STARTTLS:
                    logger.info("Запуск STARTTLS")
                    await smtp_client.starttls()
                
                if MAIL_USERNAME and MAIL_PASSWORD:
                    logger.info(f"Авторизация пользователя {MAIL_USERNAME}")
                    await smtp_client.login(MAIL_USERNAME, MAIL_PASSWORD)
                    
                logger.info(f"Отправка email на {message['To']}")
                await smtp_client.send_message(message)
                logger.info("Email успешно отправлен")
            except aiosmtplib.errors.SMTPConnectTimeoutError:
                logger.error(f"Таймаут подключения к SMTP серверу {MAIL_SERVER}:{MAIL_PORT}")
                raise
            except aiosmtplib.errors.SMTPAuthenticationError:
                logger.error(f"Ошибка аутентификации на SMTP сервере для пользователя {MAIL_USERNAME}")
                raise
            except Exception as e:
                logger.error(f"Ошибка при отправке email: {str(e)}, {type(e)}")
                raise
            finally:
                try:
                    if hasattr(smtp_client, "is_connected") and smtp_client.is_connected:
                        await smtp_client.quit()
                except Exception as quit_error:
                    logger.warning(f"Ошибка при закрытии SMTP соединения: {str(quit_error)}")
        
        try:
            loop.run_until_complete(send_mail())
        except Exception as loop_error:
            logger.error(f"Ошибка при выполнении цикла событий: {str(loop_error)}")
            raise
        finally:
            loop.close()
        
        return {
            "status": "success", 
            "message": f"Подтверждение заказа {order_id} отправлено на {email}"
        }
    
    except Exception as e:
        logger.error(f"Ошибка при отправке подтверждения заказа: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=5)  # Повторная попытка через минуту


@app.task(name='order.update_order_status', bind=True, queue='order')
def update_order_status(self, order_id, new_status, notification=True):
    """
    Задача для обновления статуса заказа и отправки уведомления.
    
    Args:
        order_id (str): ID заказа
        new_status (str): Новый статус заказа
        notification (bool): Отправлять ли уведомление о смене статуса
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Обновление статуса заказа {order_id} на '{new_status}'")
    try:
        # Здесь должен быть HTTP-запрос к order_service для обновления статуса
        
        # Получаем данные о заказе через API
        order_data = get_order_data(order_id)
        if not order_data:
            logger.error(f"Не удалось получить данные заказа {order_id}")
            raise ValueError(f"Заказ {order_id} не найден")
        
        # Временная заглушка
        result = {
            "status": "success", 
            "message": f"Статус заказа {order_id} обновлен на '{new_status}'"
        }
        
        # Если требуется отправка уведомления, запускаем соответствующую задачу
        if notification and order_data.get('email'):
            send_status_update_email.delay(order_id, new_status, order_data['email'])
            
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса заказа: {str(e)}")
        self.retry(exc=e, countdown=30, max_retries=3)


@app.task(name='order.send_status_update', bind=True, queue='order')
def send_status_update_email(self, order_id, new_status, email):
    """
    Задача для отправки уведомления об изменении статуса заказа.
    
    Args:
        order_id (str): ID заказа
        new_status (str): Новый статус заказа
        email (str): Email адрес для отправки уведомления
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Отправка уведомления о смене статуса заказа {order_id} на '{new_status}' на email {email}")
    try:
        # Получаем данные о заказе через API
        order_data = get_order_data(order_id)
        if not order_data:
            logger.error(f"Не удалось получить данные заказа {order_id}")
            raise ValueError(f"Заказ {order_id} не найден")
        
        # Создаем сообщение
        message = EmailMessage()
        message["From"] = MAIL_FROM
        message["To"] = email
        message["Subject"] = f"Изменение статуса заказа #{order_id}"
        
        # Форматируем содержимое письма
        html_content = create_status_update_email_content(order_data, new_status)
        message.set_content(html_content, subtype='html')
        
        # Отправка email через SMTP
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def send_mail():
            # Создаем SMTP клиент с нужными параметрами
            smtp_client = aiosmtplib.SMTP(
                hostname=MAIL_SERVER, 
                port=MAIL_PORT,
                use_tls=MAIL_SSL_TLS,
                timeout=MAIL_TIMEOUT  # Используем таймаут из переменных окружения
            )
                
            try:
                logger.info(f"Подключение к SMTP серверу {MAIL_SERVER}:{MAIL_PORT}, SSL/TLS: {MAIL_SSL_TLS}")
                await smtp_client.connect()
                
                # Если нужен STARTTLS (обычно для порта 587)
                if MAIL_STARTTLS:
                    logger.info("Запуск STARTTLS")
                    await smtp_client.starttls()
                
                if MAIL_USERNAME and MAIL_PASSWORD:
                    logger.info(f"Авторизация пользователя {MAIL_USERNAME}")
                    await smtp_client.login(MAIL_USERNAME, MAIL_PASSWORD)
                    
                logger.info(f"Отправка email на {message['To']}")
                await smtp_client.send_message(message)
                logger.info("Email успешно отправлен")
            except aiosmtplib.errors.SMTPConnectTimeoutError:
                logger.error(f"Таймаут подключения к SMTP серверу {MAIL_SERVER}:{MAIL_PORT}")
                raise
            except aiosmtplib.errors.SMTPAuthenticationError:
                logger.error(f"Ошибка аутентификации на SMTP сервере для пользователя {MAIL_USERNAME}")
                raise
            except Exception as e:
                logger.error(f"Ошибка при отправке email: {str(e)}, {type(e)}")
                raise
            finally:
                try:
                    if hasattr(smtp_client, "is_connected") and smtp_client.is_connected:
                        await smtp_client.quit()
                except Exception as quit_error:
                    logger.warning(f"Ошибка при закрытии SMTP соединения: {str(quit_error)}")
        
        try:
            loop.run_until_complete(send_mail())
        except Exception as loop_error:
            logger.error(f"Ошибка при выполнении цикла событий: {str(loop_error)}")
            raise
        finally:
            loop.close()
        
        return {
            "status": "success", 
            "message": f"Уведомление о смене статуса заказа {order_id} на '{new_status}' отправлено на {email}"
        }
    
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о смене статуса заказа: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=5)  # Повторная попытка через минуту


def get_order_data(order_id):
    """
    Получает данные о заказе через API сервиса заказов
    
    Args:
        order_id (str): ID заказа
        
    Returns:
        dict: Данные о заказе или None в случае ошибки
    """
    try:
        url = f"{ORDER_SERVICE_URL}/orders/{order_id}"
        
        # Добавляем заголовок с сервисным API-ключом для внутренней авторизации
        headers = {
            "Authorization": f"Bearer {SERVICE_API_KEY}",
            "X-Service-Name": "celery_service"
        }
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)
            
            if response.status_code == 200:
                return response.json()
            
            logger.error(f"Ошибка при получении данных заказа: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Ошибка при получении данных заказа {order_id}: {str(e)}")
        return None


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
                    <td>{order_data.get('created_at', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Статус:</strong></td>
                    <td>{order_data.get('status', {}).get('name', 'Новый')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Способ оплаты:</strong></td>
                    <td>{order_data.get('payment_method', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Способ доставки:</strong></td>
                    <td>{order_data.get('delivery_method', 'Н/Д')}</td>
                </tr>
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
                        {order_data.get('house', '')}, 
                        {order_data.get('apartment', '')}
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


def create_status_update_email_content(order_data, new_status):
    """
    Создает HTML-содержимое для письма с уведомлением об изменении статуса заказа
    
    Args:
        order_data (dict): Данные о заказе
        new_status (str): Новый статус заказа
        
    Returns:
        str: HTML-содержимое письма
    """
    # Получаем описание статуса
    status_descriptions = {
        "Новый": "Ваш заказ принят и ожидает обработки.",
        "Обработан": "Ваш заказ обработан и готовится к отправке.",
        "Оплачен": "Ваш заказ оплачен. Спасибо за покупку!",
        "Отправлен": "Ваш заказ отправлен. Скоро вы получите трек-номер для отслеживания.",
        "Доставлен": "Ваш заказ доставлен. Надеемся, вы довольны покупкой!",
        "Отменен": "Ваш заказ был отменен.",
        "Возврат": "Запрос на возврат заказа принят и обрабатывается."
    }
    
    status_description = status_descriptions.get(new_status, "Статус вашего заказа изменился.")
    
    # Формируем HTML-шаблон
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Изменение статуса заказа #{order_data.get('id')}</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 650px; margin: 0 auto;">
        <div style="background-color: #f8f9fa; padding: 20px; text-align: center; margin-bottom: 20px;">
            <h1 style="color: #4a5568; margin: 0;">Статус заказа изменен</h1>
            <p style="font-size: 18px; margin-top: 10px;">Заказ #{order_data.get('id')}</p>
        </div>
        
        <div style="padding: 0 20px;">
            <p>Здравствуйте, {order_data.get('full_name', 'уважаемый клиент')}!</p>
            <p>Статус вашего заказа был изменен на <strong>"{new_status}"</strong>.</p>
            <p>{status_description}</p>
            
            <h2 style="color: #4a5568; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">Данные заказа:</h2>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <tr>
                    <td style="padding: 5px 0; width: 150px;"><strong>Номер заказа:</strong></td>
                    <td>{order_data.get('id')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Дата:</strong></td>
                    <td>{order_data.get('created_at', 'Н/Д')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Новый статус:</strong></td>
                    <td><strong>{new_status}</strong></td>
                </tr>
                <tr>
                    <td style="padding: 5px 0;"><strong>Сумма заказа:</strong></td>
                    <td>{order_data.get('total_price', 0):.2f} ₽</td>
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