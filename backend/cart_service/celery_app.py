"""Celery configuration for cart service with scheduled tasks and Redis backend."""

import logging
import os
import pathlib
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_celery")

# Определяем пути к .env файлам
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Проверяем и загружаем .env файлы
if env_file.exists():
    logger.info("Загружаем .env из %s", env_file)
    load_dotenv(dotenv_path=env_file)
elif parent_env_file.exists():
    logger.info("Загружаем .env из %s", parent_env_file)
    load_dotenv(dotenv_path=parent_env_file)
else:
    logger.warning("Файл .env не найден!")

# URL для подключения к брокеру Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
logger.info("URL для Redis: %s", REDIS_URL)

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