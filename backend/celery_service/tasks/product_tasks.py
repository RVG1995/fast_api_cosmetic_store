import logging
import os
import sys
from pathlib import Path

# Добавляем родительскую директорию в sys.path, если её ещё нет
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Импортируем celery_app
from celery_app import app

logger = logging.getLogger(__name__)
PRODUCT_SERVICE_URL = os.getenv('PRODUCT_SERVICE_URL', 'http://product_service:8001')

@app.task(name='product.update_search_index', bind=True, queue='product')
def update_search_index(self):
    """
    Задача для обновления поискового индекса продуктов.
    
    Returns:
        dict: Информация о результате операции
    """
    logger.info("Запуск обновления поискового индекса продуктов")
    try:
        # В реальной реализации здесь будет HTTP-запрос к product_service
        # или прямое обращение к базе данных/поисковому движку
        
        # Временная заглушка
        return {
            "status": "success", 
            "message": "Поисковый индекс продуктов успешно обновлен"
        }
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении поискового индекса: {str(e)}")
        self.retry(exc=e, countdown=60 * 5, max_retries=3)  # Повторная попытка через 5 минут


@app.task(name='product.process_images', bind=True, queue='product')
def process_images(self, product_id, image_urls):
    """
    Задача для обработки изображений продукта (оптимизация, создание миниатюр и т.д.).
    
    Args:
        product_id (str): ID продукта
        image_urls (list): Список URL-адресов изображений для обработки
        
    Returns:
        dict: Информация о результате операции с ссылками на обработанные изображения
    """
    logger.info(f"Обработка изображений для продукта {product_id}, кол-во: {len(image_urls)}")
    try:
        # Здесь должен быть код для загрузки и обработки изображений,
        # а также HTTP-запрос к product_service для обновления ссылок на изображения
        
        # Временная заглушка
        processed_images = [f"processed_{url}" for url in image_urls]
        thumbnails = [f"thumbnail_{url}" for url in image_urls]
        
        return {
            "status": "success", 
            "message": f"Изображения для продукта {product_id} обработаны",
            "processed_images": processed_images,
            "thumbnails": thumbnails
        }
    
    except Exception as e:
        logger.error(f"Ошибка при обработке изображений: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=3)


@app.task(name='product.update_stock', bind=True, queue='product')
def update_stock(self, product_id, quantity_delta, reason="manual_update"):
    """
    Задача для обновления количества товара на складе.
    
    Args:
        product_id (str): ID продукта
        quantity_delta (int): Изменение количества (положительное - приход, отрицательное - расход)
        reason (str): Причина изменения количества
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Обновление запасов продукта {product_id}: {quantity_delta:+d}, причина: {reason}")
    try:
        # Здесь должен быть HTTP-запрос к product_service для обновления запасов
        
        # Временная заглушка
        return {
            "status": "success", 
            "message": f"Запасы продукта {product_id} обновлены ({quantity_delta:+d})",
            "new_quantity": 100  # В реальной реализации здесь будет фактическое обновленное количество
        }
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении запасов продукта: {str(e)}")
        self.retry(exc=e, countdown=30, max_retries=3)


@app.task(name='product.send_low_stock_alert', bind=True, queue='product')
def send_low_stock_alert(self, product_ids):
    """
    Задача для отправки уведомлений о низком запасе продуктов.
    
    Args:
        product_ids (list): Список ID продуктов с низким запасом
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Отправка уведомлений о низком запасе для {len(product_ids)} продуктов")
    try:
        # Здесь должен быть код для отправки уведомлений администраторам
        
        # Временная заглушка
        return {
            "status": "success", 
            "message": f"Уведомления о низком запасе отправлены для {len(product_ids)} продуктов",
            "sent_notifications": len(product_ids)
        }
    
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений о низком запасе: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=3) 