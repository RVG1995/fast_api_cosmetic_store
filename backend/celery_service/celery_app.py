import os
from celery import Celery
import logging
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from celery.signals import task_prerun, task_postrun  # Правильный импорт сигналов

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('celery_service')

# Загрузка переменных окружения
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    logger.info(f"Загрузка переменных окружения из {env_path}")
    load_dotenv(dotenv_path=env_path)
else:
    logger.warning(f"Файл .env не найден в {env_path}, используются только системные переменные")

# Определение URL для Redis из переменных окружения
def get_redis_url() -> str:
    """Получение URL для Redis из переменных окружения"""
    # Если задан полный URL, используем его
    redis_url = os.getenv('REDIS_URL')
    if redis_url:
        return redis_url
    
    # Иначе строим URL из отдельных компонентов
    host = os.getenv('REDIS_HOST', 'localhost')
    port = os.getenv('REDIS_PORT', '6379')
    db = os.getenv('REDIS_DB', '0')
    password = os.getenv('REDIS_PASSWORD', '')
    
    if password:
        return f"redis://:{password}@{host}:{port}/{db}"
    return f"redis://{host}:{port}/{db}"

# Инициализация Celery
app = Celery('celery_service')

# Базовая конфигурация
app.conf.update(
    broker_url=get_redis_url(),
    result_backend=get_redis_url(),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
    worker_hijack_root_logger=False,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
)

# Настройка очередей для разных микросервисов
app.conf.task_routes = {
    'auth.*': {'queue': 'auth'},
    'cart.*': {'queue': 'cart'},
    'order.*': {'queue': 'order'},
    'product.*': {'queue': 'product'},
}

# Импортируем расписание из отдельного файла
try:
    # Сначала пробуем импортировать напрямую
    try:
        from schedule import beat_schedule
        app.conf.beat_schedule = beat_schedule
        logger.info("Загружено расписание задач из schedule.py")
    # Если не получается, пробуем относительный импорт
    except ImportError:
        try:
            from .schedule import beat_schedule
            app.conf.beat_schedule = beat_schedule
            logger.info("Загружено расписание задач из .schedule.py")
        except ImportError:
            # Как вариант, может потребоваться использовать динамический импорт
            import importlib.util
            import os
            
            schedule_path = os.path.join(os.path.dirname(__file__), 'schedule.py')
            if os.path.exists(schedule_path):
                spec = importlib.util.spec_from_file_location("schedule", schedule_path)
                schedule_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(schedule_module)
                
                app.conf.beat_schedule = schedule_module.beat_schedule
                logger.info("Загружено расписание задач динамически из schedule.py")
            else:
                raise ImportError("Файл schedule.py не найден")
except Exception as e:
    logger.warning(f"Не удалось импортировать beat_schedule из schedule.py: {e}")

# Автообнаружение задач
app.autodiscover_tasks(['tasks'])

# Хук для логирования запуска задач
@task_prerun.connect  # Используем импортированный сигнал
def task_prerun_handler(task_id, task, args, kwargs, **kw):
    logger.info(f'Выполняется задача {task.name}[{task_id}] с аргументами {args} {kwargs}')

# Хук для логирования завершения задач
@task_postrun.connect  # Используем импортированный сигнал
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **kw):
    logger.info(f'Задача {task.name}[{task_id}] завершена со статусом {state}')

if __name__ == '__main__':
    app.start() 