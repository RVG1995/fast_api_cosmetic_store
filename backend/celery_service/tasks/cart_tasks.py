import logging
import os
import sys
from pathlib import Path
import httpx

# Добавляем родительскую директорию в sys.path, если её ещё нет
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Импортируем celery_app
from celery_app import app

logger = logging.getLogger(__name__)
CART_SERVICE_URL = os.getenv('CART_SERVICE_URL', 'http://cart_service:8000')
# Сервисный API-ключ для внутренней авторизации между микросервисами
INTERNAL_SERVICE_KEY = os.getenv('INTERNAL_SERVICE_KEY', 'test')

@app.task(name='cart.cleanup_old_anonymous_carts', bind=True, queue='cart')
def cleanup_old_anonymous_carts(self, days=1):
    """
    Задача для очистки анонимных корзин старше определенного количества дней.
    
    Args:
        days (int): Количество дней, после которых анонимная корзина считается устаревшей
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Запуск очистки анонимных корзин старше {days} дней")
    try:
        # Выполняем HTTP-запрос к cart_service для удаления устаревших корзин
        headers = {
            "Content-Type": "application/json",
            "service-key": INTERNAL_SERVICE_KEY
        }
        
        logger.info(f"Отправка запроса на {CART_SERVICE_URL}/cart/cleanup с days={days}")
        response = httpx.post(
            f"{CART_SERVICE_URL}/cart/cleanup",
            json={"days": days},
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            deleted_count = result.get("deleted_count", 0)
            logger.info(f"Успешно удалено {deleted_count} устаревших анонимных корзин")
            return {
                "status": "success", 
                "message": f"Очистка корзин старше {days} дней выполнена", 
                "deleted_count": deleted_count
            }
        else:
            logger.error(f"Ошибка при вызове API удаления корзин: {response.status_code} - {response.text}")
            raise Exception(f"API error: {response.status_code} - {response.text}")
    
    except Exception as e:
        logger.error(f"Ошибка при очистке анонимных корзин: {str(e)}")
        self.retry(exc=e, countdown=60 * 5, max_retries=3)  # Повторная попытка через 5 минут, максимум 3 попытки