import logging
from ..utils.celery_utils import send_celery_task

logger = logging.getLogger(__name__)

def process_product_images(product_id, image_urls):
    """
    Запускает асинхронную обработку изображений продукта.
    
    Args:
        product_id (str): ID продукта
        image_urls (list): Список URL-адресов изображений для обработки
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Запуск обработки изображений для продукта {product_id}, количество: {len(image_urls)}")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'product.process_images',
        args=[product_id, image_urls]
    )
    
    return task_id

def update_product_stock(product_id, quantity_delta, reason="manual_update"):
    """
    Асинхронно обновляет запасы товара на складе.
    
    Args:
        product_id (str): ID продукта
        quantity_delta (int): Изменение количества (положительное - приход, отрицательное - расход)
        reason (str): Причина изменения количества
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Обновление запасов продукта {product_id}: {quantity_delta:+d}, причина: {reason}")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'product.update_stock',
        args=[product_id, quantity_delta, reason]
    )
    
    return task_id

def update_search_index():
    """
    Запускает обновление поискового индекса продуктов.
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info("Запуск обновления поискового индекса продуктов")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'product.update_search_index'
    )
    
    return task_id

def send_low_stock_alert(product_ids):
    """
    Отправляет уведомления о низком запасе продуктов.
    
    Args:
        product_ids (list): Список ID продуктов с низким запасом
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Отправка уведомлений о низком запасе для {len(product_ids)} продуктов")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'product.send_low_stock_alert',
        args=[product_ids]
    )
    
    return task_id 