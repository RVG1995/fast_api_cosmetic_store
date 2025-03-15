import logging
from ..utils.celery_utils import send_celery_task

logger = logging.getLogger(__name__)

def send_order_confirmation(order_id, email):
    """
    Отправляет email с подтверждением заказа через Celery.
    
    Args:
        order_id (int): ID заказа
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
    
    if task_id:
        logger.info(f"Задача отправки подтверждения заказа {order_id} поставлена в очередь, task_id: {task_id}")
    else:
        logger.error(f"Не удалось отправить задачу подтверждения заказа {order_id} в Celery")
    
    return task_id

def update_order_status(order_id, new_status, old_status=None, email=None, notify=True):
    """
    Асинхронно обновляет статус заказа и отправляет уведомление, если нужно.
    
    Args:
        order_id (int): ID заказа
        new_status (str): Новый статус заказа
        old_status (str, optional): Предыдущий статус заказа
        email (str, optional): Email пользователя
        notify (bool): Отправлять ли уведомление о смене статуса
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Обновление статуса заказа {order_id} с '{old_status}' на '{new_status}'")
    
    if notify and email:
        # Отправляем задачу на уведомление о смене статуса через Celery
        task_id = send_celery_task(
            'order.send_status_update',
            args=[order_id, new_status, email]
        )
        
        if task_id:
            logger.info(f"Задача отправки уведомления о смене статуса заказа {order_id} поставлена в очередь, task_id: {task_id}")
        else:
            logger.error(f"Не удалось отправить задачу уведомления о смене статуса заказа {order_id} в Celery")
        
        return task_id
    else:
        logger.info(f"Уведомление о смене статуса заказа {order_id} отключено или email не указан")
        return None

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
    
    if task_id:
        logger.info(f"Задача обработки заброшенных заказов поставлена в очередь, task_id: {task_id}")
    else:
        logger.error(f"Не удалось отправить задачу обработки заброшенных заказов в Celery")
    
    return task_id 