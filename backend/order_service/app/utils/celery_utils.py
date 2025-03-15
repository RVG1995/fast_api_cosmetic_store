import json
import os
import redis
import uuid
import logging

logger = logging.getLogger(__name__)

# Получаем настройки подключения к Redis из переменных окружения или используем значения по умолчанию
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379") 
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

def send_celery_task(task_name, args=None, kwargs=None, queue=None):
    """
    Отправка задачи в очередь Celery через Redis.
    
    Args:
        task_name (str): Имя задачи в формате 'service.task_name'
        args (list, optional): Позиционные аргументы задачи
        kwargs (dict, optional): Именованные аргументы задачи
        queue (str, optional): Имя очереди. Если не указано, берется из task_name
        
    Returns:
        str: ID задачи
    """
    args = args or []
    kwargs = kwargs or {}
    
    # Если очередь не указана, берем её из имени задачи (первая часть до точки)
    if queue is None:
        queue = task_name.split('.')[0]
    
    try:
        # Создаем соединение с Redis
        r = redis.Redis(
            host=REDIS_HOST,
            port=int(REDIS_PORT),
            db=int(REDIS_DB),
            password=REDIS_PASSWORD or None,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        
        # Генерируем уникальный ID задачи
        task_id = str(uuid.uuid4())
        
        # Создаем сообщение задачи в формате Celery
        task_message = {
            "id": task_id,
            "task": task_name,
            "args": args,
            "kwargs": kwargs,
            "retries": 0,
            "eta": None,
            "expires": None,
        }
        
        # Сериализуем сообщение в JSON
        json_message = json.dumps(task_message)
        
        # Публикуем сообщение в очередь Celery
        r.lpush(f'celery:{queue}', json_message)
        
        logger.info(f"Задача {task_name} с ID {task_id} отправлена в очередь {queue}")
        return task_id
        
    except Exception as e:
        logger.error(f"Ошибка при отправке задачи {task_name} в Celery: {str(e)}")
        # В случае ошибки возвращаем None и не прерываем работу приложения
        return None

def check_task_status(task_id):
    """
    Проверяет статус задачи Celery по её ID.
    
    Args:
        task_id (str): ID задачи
    
    Returns:
        dict или None: Информация о статусе задачи или None, если задача не найдена
    """
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=int(REDIS_PORT),
            db=int(REDIS_DB),
            password=REDIS_PASSWORD or None,
            socket_timeout=5
        )
        
        # Проверяем результат в хранилище результатов Celery
        result_key = f'celery-task-meta-{task_id}'
        result = r.get(result_key)
        
        if result:
            return json.loads(result)
        
        return None
    
    except Exception as e:
        logger.error(f"Ошибка при проверке статуса задачи {task_id}: {str(e)}")
        return None 