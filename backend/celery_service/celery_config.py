from celery import Celery
import logging
from celery.signals import task_prerun, task_postrun
from config import get_redis_url

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('celery_service')

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

# Импортируем расписание из отдельного файла
try:
    from schedule import beat_schedule
    app.conf.beat_schedule = beat_schedule
    logger.info("Загружено расписание задач из schedule.py")
except Exception as e:
    logger.warning(f"Не удалось импортировать beat_schedule из schedule.py: {e}")

# Хуки для логирования
@task_prerun.connect
def task_prerun_handler(task_id, task, args, kwargs, **kw):
    logger.info(f'Выполняется задача {task.name}[{task_id}] с аргументами {args} {kwargs}')

@task_postrun.connect
def task_postrun_handler(task_id, task, args, kwargs, retval, state, **kw):
    logger.info(f'Задача {task.name}[{task_id}] завершена со статусом {state}')