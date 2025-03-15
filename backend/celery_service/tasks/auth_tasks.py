import logging
import os
import sys
from pathlib import Path
import httpx
from email.message import EmailMessage
import aiosmtplib
import asyncio

# Добавляем родительскую директорию в sys.path, если её ещё нет
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Импортируем celery_app
from celery_app import app

logger = logging.getLogger(__name__)
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://auth_service:8000')

# Получаем настройки SMTP из переменных окружения
MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
MAIL_FROM = os.getenv('MAIL_FROM', 'test@example.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', 465))
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_STARTTLS = os.getenv('MAIL_STARTTLS', 'False').lower() == 'true'
MAIL_SSL_TLS = os.getenv('MAIL_SSL_TLS', 'True').lower() == 'true'

@app.task(name='auth.cleanup_expired_tokens', bind=True, queue='auth')
def cleanup_expired_tokens(self, retention_days=7):
    """
    Задача для очистки истекших токенов из базы данных.
    
    Args:
        retention_days (int): Количество дней хранения истекших токенов
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Запуск очистки истекших токенов старше {retention_days} дней")
    try:
        # В реальной реализации здесь будет HTTP-запрос к auth_service
        # или прямое обращение к базе данных
        
        # Временная заглушка
        return {
            "status": "success", 
            "message": f"Очистка истекших токенов выполнена",
            "deleted_count": 0
        }
    
    except Exception as e:
        logger.error(f"Ошибка при очистке истекших токенов: {str(e)}")
        self.retry(exc=e, countdown=60 * 5, max_retries=3)  # Повторная попытка через 5 минут


@app.task(name='auth.send_verification_email', bind=True, queue='auth')
def send_verification_email(self, user_id, email, verification_link):
    """
    Задача для отправки email с подтверждением регистрации.
    
    Args:
        user_id (str): ID пользователя
        email (str): Email адрес пользователя
        verification_link (str): Ссылка для подтверждения email
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Отправка email для подтверждения регистрации пользователя {user_id}")
    try:
        # Создаем сообщение
        message = EmailMessage()
        message["From"] = MAIL_FROM
        message["To"] = email
        message["Subject"] = "Подтверждение регистрации"
        
        # Содержимое письма
        body = f"""
        Спасибо за регистрацию!
        
        Для активации аккаунта перейдите по ссылке:
        {verification_link}
        
        С уважением,
        Команда Cosmetic Store
        """
        message.set_content(body)
        
        # Отправка email через SMTP
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def send_mail():
            # Создаем SMTP клиент с нужными параметрами
            smtp_client = aiosmtplib.SMTP(
                hostname=MAIL_SERVER, 
                port=MAIL_PORT,
                use_tls=MAIL_SSL_TLS
            )
                
            try:
                await smtp_client.connect()
                # Если нужен STARTTLS (обычно для порта 587)
                if MAIL_STARTTLS:
                    await smtp_client.starttls()
                
                if MAIL_USERNAME and MAIL_PASSWORD:
                    await smtp_client.login(MAIL_USERNAME, MAIL_PASSWORD)
                    
                await smtp_client.send_message(message)
            finally:
                await smtp_client.quit()
        
        loop.run_until_complete(send_mail())
        
        return {
            "status": "success", 
            "message": f"Email с подтверждением отправлен на {email}"
        }
    
    except Exception as e:
        logger.error(f"Ошибка при отправке email с подтверждением: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=5)  # Повторная попытка через минуту


@app.task(name='auth.send_password_reset', bind=True, queue='auth')
def send_password_reset(self, user_id, email, reset_link):
    """
    Задача для отправки email со ссылкой для сброса пароля.
    
    Args:
        user_id (str): ID пользователя
        email (str): Email адрес пользователя
        reset_link (str): Ссылка для сброса пароля
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Отправка email для сброса пароля пользователя {user_id}")
    try:
        # Создаем сообщение
        message = EmailMessage()
        message["From"] = MAIL_FROM
        message["To"] = email
        message["Subject"] = "Сброс пароля"
        
        # Содержимое письма
        body = f"""
        Вы запросили сброс пароля.
        
        Для сброса пароля перейдите по ссылке:
        {reset_link}
        
        Если вы не запрашивали сброс пароля, проигнорируйте это письмо.
        
        С уважением,
        Команда Cosmetic Store
        """
        message.set_content(body)
        
        # Отправка email через SMTP
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def send_mail():
            # Создаем SMTP клиент с нужными параметрами
            smtp_client = aiosmtplib.SMTP(
                hostname=MAIL_SERVER, 
                port=MAIL_PORT,
                use_tls=MAIL_SSL_TLS
            )
                
            try:
                await smtp_client.connect()
                # Если нужен STARTTLS (обычно для порта 587)
                if MAIL_STARTTLS:
                    await smtp_client.starttls()
                
                if MAIL_USERNAME and MAIL_PASSWORD:
                    await smtp_client.login(MAIL_USERNAME, MAIL_PASSWORD)
                    
                await smtp_client.send_message(message)
            finally:
                await smtp_client.quit()
        
        loop.run_until_complete(send_mail())
        
        return {
            "status": "success", 
            "message": f"Email для сброса пароля отправлен на {email}"
        }
    
    except Exception as e:
        logger.error(f"Ошибка при отправке email для сброса пароля: {str(e)}")
        self.retry(exc=e, countdown=60, max_retries=5)


@app.task(name='auth.notify_suspicious_activity', bind=True, queue='auth')
def notify_suspicious_activity(self, user_id, activity_type, details):
    """
    Задача для уведомления о подозрительной активности аккаунта.
    
    Args:
        user_id (str): ID пользователя
        activity_type (str): Тип подозрительной активности
        details (dict): Детали активности
        
    Returns:
        dict: Информация о результате операции
    """
    logger.info(f"Уведомление о подозрительной активности для пользователя {user_id}: {activity_type}")
    try:
        # Здесь должен быть код для уведомления пользователя и/или администраторов
        
        # Временная заглушка
        return {
            "status": "success", 
            "message": f"Уведомление о подозрительной активности отправлено"
        }
    
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о подозрительной активности: {str(e)}")
        self.retry(exc=e, countdown=30, max_retries=3)