"""
Конфигурация для RabbitMQ email consumer с использованием Pydantic Settings.
"""
import os
import logging
import pathlib
from typing import Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    # Настройки RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_USER: str = "user"
    RABBITMQ_PASS: str = "password"
    
    # Настройки для Dead Letter Exchange
    DLX_NAME: str = "dead_letter_exchange"
    DLX_QUEUE: str = "failed_messages"
    # Максимальное количество попыток обработки сообщения
    MAX_RETRY_COUNT: int = 3
    # Задержка перед повторной попыткой в миллисекундах
    RETRY_DELAY_MS: int = 5000
    
    # Настройки SMTP
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@example.com"
    
    # Настройки Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 6  # Email consumer использует DB 6
    
    # Настройки кэширования
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 300  # 5 минут по умолчанию
    
    # Настройки для реконнекта
    MAX_RECONNECT_ATTEMPTS: int = 10
    INITIAL_RECONNECT_DELAY: int = 1  # Начальная задержка в секундах
    MAX_RECONNECT_DELAY: int = 30     # Максимальная задержка в секундах
    CONNECTION_CHECK_INTERVAL: int = 5  # Интервал проверки соединения в секундах
    
    # URL сервисов
    PRODUCT_SERVICE_URL: str = "http://localhost:8001"
    CART_SERVICE_URL: str = "http://localhost:8002"
    ORDER_SERVICE_URL: str = "http://localhost:8003"
    AUTH_SERVICE_URL: str = "http://localhost:8000"
    
    # Настройки JWT для межсервисной аутентификации
    JWT_SECRET_KEY: str = "your-secret-key"
    JWT_ALGORITHM: str = "HS256"
    SERVICE_CLIENT_ID: str = "rabbit"
    SERVICE_CLIENTS_RAW: str = ""  # "rabbit:rabbit_secret,orders:orders_secret"
    SERVICE_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Email администратора для уведомлений
    ADMIN_EMAIL: str = "rvg95@mail.ru"
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
    )

# Функция для определения путей к файлам .env
def get_env_file_path() -> Optional[str]:
    """Определяет путь к .env файлу."""
    current_dir = pathlib.Path(__file__).parent.absolute()
    env_file = current_dir / ".env"
    parent_env_file = current_dir.parent / ".env"
    
    if env_file.exists():
        return str(env_file)
    elif parent_env_file.exists():
        return str(parent_env_file)
    return None

# Инициализируем настройки
settings = Settings()

def get_rabbitmq_url() -> str:
    """Возвращает URL для подключения к RabbitMQ."""
    return f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}@{settings.RABBITMQ_HOST}/"

def get_redis_url() -> str:
    """Возвращает URL для подключения к Redis."""
    redis_url = "redis://"
    if settings.REDIS_PASSWORD:
        redis_url += f":{settings.REDIS_PASSWORD}@"
    redis_url += f"{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    return redis_url

def get_service_clients() -> Dict[str, str]:
    """Возвращает словарь с учетными данными сервисов для межсервисной авторизации."""
    if not settings.SERVICE_CLIENTS_RAW:
        return {}
    return {kv.split(":")[0]: kv.split(":")[1] for kv in settings.SERVICE_CLIENTS_RAW.split(",") if ":" in kv}

# Путь к директории с шаблонами
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates") 