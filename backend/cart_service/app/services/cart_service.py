import logging
from ..utils.celery_utils import send_celery_task

logger = logging.getLogger(__name__)

def merge_carts(anonymous_cart_id, user_cart_id):
    """
    Запускает асинхронное объединение анонимной корзины с корзиной пользователя.
    
    Args:
        anonymous_cart_id (str): ID анонимной корзины
        user_cart_id (str): ID корзины пользователя
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Запуск задачи объединения корзин {anonymous_cart_id} и {user_cart_id}")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'cart.merge_carts',
        args=[anonymous_cart_id, user_cart_id]
    )
    
    return task_id

def cleanup_old_carts(days=1):
    """
    Запускает асинхронную очистку старых анонимных корзин.
    
    Args:
        days (int): Количество дней, после которых корзина считается устаревшей
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Запуск задачи очистки старых корзин старше {days} дней")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'cart.cleanup_old_anonymous_carts',
        args=[days]
    )
    
    return task_id

def update_cart_items_availability():
    """
    Запускает асинхронную проверку и обновление доступности товаров в корзинах.
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info("Запуск задачи обновления доступности товаров в корзинах")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'cart.update_items_availability'
    )
    
    return task_id 