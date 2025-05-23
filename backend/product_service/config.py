"""Конфигурационные настройки для сервиса продуктов."""

import os
import pathlib
from typing import Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Настройки базы данных
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/product_db"
    
    # Настройки Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 1  # Product service использует DB 1
    
    # Настройки кэширования
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 600  # 10 минут по умолчанию
    PRODUCT_CACHE_TTL: int = 600  # 10 минут для продуктов
    CATEGORY_CACHE_TTL: int = 1800  # 30 минут для категорий
    
    # Настройки JWT
    JWT_SECRET_KEY: str = "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke"
    JWT_ALGORITHM: str = "HS256"
    
    # Настройки API
    API_MAX_RETRIES: int = 3  # Максимальное число повторных попыток
    
    # Настройки для статических файлов
    UPLOAD_DIR: str = "static/images"
    STATIC_DIR: str = "static"
    
    # Межсервисная авторизация
    SERVICE_CLIENT_ID: str = "products"
    SERVICE_CLIENTS_RAW: str = ""  # "products:products_secret,orders:orders_secret"
    SERVICE_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Настройки пагинации по умолчанию
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
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
    return settings.DATABASE_URL


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
        "default": settings.CACHE_TTL,
        "product": settings.PRODUCT_CACHE_TTL,
        "category": settings.CATEGORY_CACHE_TTL,
    }


def get_cache_keys() -> Dict[str, str]:
    """Возвращает префиксы ключей кэша."""
    return {
        "products": "products:",  # Кэш продуктов: products:{product_id}
        "categories": "categories:",  # Кэш категорий: categories:{category_id}
        "subcategories": "subcategories:",  # Кэш подкатегорий: subcategories:{subcategory_id}
        "brands": "brands:",  # Кэш брендов: brands:{brand_id}
        "countries": "countries:",  # Кэш стран: countries:{country_id}
    }


def get_cors_origins() -> List[str]:
    """Возвращает список разрешенных источников для CORS."""
    return [
        "http://localhost:3000",  # адрес фронтенда
        "http://127.0.0.1:3000",  # альтернативный адрес локального фронтенда
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:8002",
        "http://127.0.0.1:8002",
        "http://localhost:8003",
        "http://127.0.0.1:8003",
    ] 