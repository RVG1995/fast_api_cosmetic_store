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