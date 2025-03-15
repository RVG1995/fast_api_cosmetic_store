import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем родительскую директорию в sys.path, если её ещё нет
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Импортируем celery_app
from celery_app import app

logger = logging.getLogger(__name__)
ORDER_SERVICE_URL = os.getenv('ORDER_SERVICE_URL', 'http://order_service:8003')

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
        # Здесь должен быть код для отправки email с подтверждением
        # и/или обновление статуса заказа через HTTP-запрос к order_service
        
        # Временная заглушка
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
        
        # Временная заглушка
        result = {
            "status": "success", 
            "message": f"Статус заказа {order_id} обновлен на '{new_status}'"
        }
        
        # Если требуется отправка уведомления, запускаем соответствующую задачу
        if notification:
            # В реальной реализации здесь будет вызов задачи для отправки уведомления
            # например: send_status_notification.delay(order_id, new_status)
            pass
            
        return result
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса заказа: {str(e)}")
        self.retry(exc=e, countdown=30, max_retries=3) 