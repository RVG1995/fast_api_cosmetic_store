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