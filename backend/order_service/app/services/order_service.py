import logging
from ..utils.celery_utils import send_celery_task

logger = logging.getLogger(__name__)

def send_order_confirmation(order_id, email):
    """
    Отправляет email с подтверждением заказа через Celery.
    
    Args:
        order_id (str): ID заказа
        email (str): Email пользователя
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Отправка подтверждения заказа {order_id} на email {email}")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'order.send_order_confirmation',
        args=[order_id, email]
    )
    
    return task_id

def update_order_status(order_id, new_status, notify=True):
    """
    Асинхронно обновляет статус заказа и отправляет уведомление, если нужно.
    
    Args:
        order_id (str): ID заказа
        new_status (str): Новый статус заказа
        notify (bool): Отправлять ли уведомление о смене статуса
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Обновление статуса заказа {order_id} на '{new_status}'")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'order.update_order_status',
        args=[order_id, new_status, notify]
    )
    
    return task_id

def process_abandoned_orders(hours=24):
    """
    Запускает обработку заброшенных заказов (не оплаченных в течение определенного времени).
    
    Args:
        hours (int): Количество часов, после которых неоплаченный заказ считается заброшенным
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Запуск обработки заброшенных заказов старше {hours} часов")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'order.process_abandoned_orders',
        args=[hours]
    )
    
    return task_id 