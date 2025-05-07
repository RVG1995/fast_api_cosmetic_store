"""Модуль с централизованными настройками сервиса корзины."""

import os
import pathlib
from typing import Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Настройки базы данных
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5434/cart_db"
    
    # Настройки Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_DB: int = 3  # Cart service использует DB 3
    
    # Настройки кэширования
    CACHE_ENABLED: bool = True
    CART_CACHE_TTL: int = 60  # 60 секунд для корзины
    CART_SUMMARY_CACHE_TTL: int = 30  # 30 секунд для сводки корзины
    ADMIN_CARTS_CACHE_TTL: int = 30  # 30 секунд для списка корзин в админке
    PRODUCT_CACHE_TTL: int = 300  # 5 минут для данных о продуктах
    
    # Настройки API
    API_MAX_RETRIES: int = 3  # Максимальное число повторных попыток
    
    # Настройки JWT
    JWT_SECRET_KEY: str = "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke"
    JWT_ALGORITHM: str = "HS256"
    
    # Настройки внешних сервисов
    PRODUCT_SERVICE_URL: str = "http://localhost:8001"
    CART_SERVICE_URL: str = "http://localhost:8002"
    AUTH_SERVICE_URL: str = "http://localhost:8000"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8005"
    
    # Межсервисная авторизация
    SERVICE_CLIENT_ID: str = "carts"
    SERVICE_CLIENTS_RAW: str = ""  # "orders:orders_secret,carts:carts_secret,rabbit:rabbit_secret"
    SERVICE_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Максимальный размер корзины для хранения в куках (в байтах)
    MAX_COOKIE_SIZE: int = 4000  # ~4KB - безопасный размер для большинства браузеров
    
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
        "cart": settings.CART_CACHE_TTL,
        "cart_summary": settings.CART_SUMMARY_CACHE_TTL,
        "admin_carts": settings.ADMIN_CARTS_CACHE_TTL
    }


def get_cache_keys() -> Dict[str, str]:
    """Возвращает префиксы ключей кэша."""
    return {
        "cart_user": "cart:user:",  # Корзина пользователя - cart:user:{user_id}
        "cart_session": "cart:session:",  # Корзина сессии - cart:session:{session_id}
        "cart_summary_user": "cart:summary:user:",  # Сводка корзины пользователя
        "cart_summary_session": "cart:summary:session:",  # Сводка корзины сессии
        "admin_carts": "admin:carts:"  # Список корзин для администраторов с параметрами
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
    ] 