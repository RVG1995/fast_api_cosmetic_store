from celery import Celery
from celery.schedules import crontab
import logging

from config import settings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_celery")

# URL для подключения к брокеру Redis
REDIS_URL = settings.REDIS_URL
logger.info(f"URL для Redis: {REDIS_URL}")

# Инициализация Celery с настройками
app = Celery(
    'cart_tasks',
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Настройка Celery
app.conf.update(
    # Настройка часового пояса
    timezone='Europe/Moscow',
    
    # Добавляем новую настройку для повторных подключений при запуске
    broker_connection_retry_on_startup=True,
    
    # Настройка для отключения проверок несоответствия времени
    worker_disable_rate_limits=True,
    
    # Отключаем mingle - поиск других воркеров (это устраняет проблему с brpop)
    worker_enable_remote_control=False,
    
    # Устанавливаем время ожидания синхронизации узлов
    broker_connection_timeout=10,
    
    # Запуск задач в режиме eager для отладки (по желанию, в продакшене отключить)
    # task_always_eager=True,
    
    # Настройка расписания задач
    beat_schedule={
        'cleanup-anonymous-carts-at-midnight': {
            'task': 'tasks.cleanup_old_anonymous_carts',
            'schedule': crontab(hour=0, minute=0),  # Запуск каждый день в полночь
            'args': (1,),  # Аргумент: количество дней для очистки
        },
    },
)

# Автоматическое обнаружение и импорт задач из файла tasks.py
app.autodiscover_tasks(['tasks']) 