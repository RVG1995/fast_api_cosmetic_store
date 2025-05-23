"""
Конфигурация для сервиса отзывов с использованием Pydantic Settings.
"""
import os
import logging
import pathlib
from typing import Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы для пагинации
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 50

class Settings(BaseSettings):
    # Настройки базы данных
    REVIEW_DB_HOST: str = "localhost"
    REVIEW_DB_PORT: str = "5436"
    REVIEW_DB_NAME: str = "review_db"
    REVIEW_DB_USER: str = "postgres"
    REVIEW_DB_PASSWORD: str = "postgres"
    
    # Настройки Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 4  # Review service использует DB 4
    
    # Настройки кэширования
    CACHE_ENABLED: bool = True
    
    # Настройки JWT
    JWT_SECRET_KEY: str = "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke"
    JWT_ALGORITHM: str = "HS256"
    
    # URL сервисов
    AUTH_SERVICE_URL: str = "http://localhost:8000"
    PRODUCT_SERVICE_URL: str = "http://localhost:8001"
    ORDER_SERVICE_URL: str = "http://localhost:8003"
    
    # Настройки статических файлов
    STATIC_DIR: str = "static"
    
    # Настройки CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1",
    ]
    
    # Настройки для межсервисной авторизации
    SERVICE_CLIENT_ID: str = "reviews"
    SERVICE_CLIENTS_RAW: str = ""  # "reviews:reviews_secret,products:products_secret"
    SERVICE_TOKEN_EXPIRE_MINUTES: int = 30
    
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

def get_db_url() -> str:
    """Возвращает URL для подключения к базе данных."""
    return f"postgresql+asyncpg://{settings.REVIEW_DB_USER}:{settings.REVIEW_DB_PASSWORD}@{settings.REVIEW_DB_HOST}:{settings.REVIEW_DB_PORT}/{settings.REVIEW_DB_NAME}"

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

def get_cache_ttl() -> Dict[str, int]:
    """Возвращает словарь с настройками TTL для разных типов кэша."""
    return {
        "review": 3600,  # 1 час для отдельного отзыва
        "reviews": 1800,  # 30 минут для списков отзывов
        "statistics": 3600,  # 1 час для статистики
        "permissions": 300,  # 5 минут для проверки разрешений пользователя
    }

def get_cache_keys() -> Dict[str, str]:
    """
    Получение ключей для кэширования
    
    Returns:
        Dict[str, str]: Словарь ключей кэша
    """
    return {
        "review": "review_service:review:",
        "product_reviews": "review_service:product_reviews:",
        "store_reviews": "review_service:store_reviews:",
        "user_reviews": "review_service:user_reviews:",
        "permissions": "review_service:permissions:",
        "product_statistics": "review_service:product_statistics:",
        "store_statistics": "review_service:store_statistics:",
        "product_review_stats": "review_service:product_review_stats:",
        "store_review_stats": "review_service:store_review_stats:",
        "test": "review_service:test:",
        "product_batch_statistics": "review_service:product_batch_stats:",
        "review_detail": "review_service:review_detail:",
        "user_permissions": "review_service:user_permissions:"
    }

def get_cors_origins() -> List[str]:
    """Возвращает список разрешенных источников для CORS."""
    return settings.CORS_ORIGINS 