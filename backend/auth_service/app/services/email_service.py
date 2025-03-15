import logging
from ..utils.celery_utils import send_celery_task

logger = logging.getLogger(__name__)

def send_verification_email(user_id, email, verification_link):
    """
    Отправляет email для подтверждения регистрации через Celery.
    
    Args:
        user_id (str): ID пользователя
        email (str): Email пользователя
        verification_link (str): Ссылка для подтверждения email
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Отправка email для подтверждения пользователю {email}")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'auth.send_verification_email',
        args=[user_id, email, verification_link]
    )
    
    return task_id

def send_password_reset_email(user_id, email, reset_link):
    """
    Отправляет email для сброса пароля через Celery.
    
    Args:
        user_id (str): ID пользователя
        email (str): Email пользователя
        reset_link (str): Ссылка для сброса пароля
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info(f"Отправка email для сброса пароля пользователю {email}")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'auth.send_password_reset',
        args=[user_id, email, reset_link]
    )
    
    return task_id

def cleanup_expired_tokens():
    """
    Запускает задачу очистки истекших токенов.
    
    Returns:
        str или None: ID задачи Celery или None в случае ошибки
    """
    logger.info("Запуск задачи очистки истекших токенов")
    
    # Отправляем задачу в Celery через утилиту
    task_id = send_celery_task(
        'auth.cleanup_expired_tokens',
        args=[7]  # Хранить токены 7 дней
    )
    
    return task_id 