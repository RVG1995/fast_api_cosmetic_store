"""Модуль с централизованными настройками сервиса аутентификации."""

import os
from datetime import timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Настройки базы данных
    DB_HOST: str = "localhost"
    DB_PORT: int = 5433
    DB_NAME: str = "auth_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    
    # Настройки Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    
    # Настройки кэширования
    DEFAULT_CACHE_TTL: int = 3600  # 1 час по умолчанию
    USER_CACHE_TTL: int = 300  # 5 минут для пользовательских данных
    CACHE_ENABLED: bool = True
    
    # Настройки JWT
    JWT_SECRET_KEY: str = "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14  # 14 дней
    SERVICE_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_ISSUER: str = "auth_service"
    JWT_AUDIENCE: str = "frontend"
    VERIFY_JWT_AUDIENCE: bool = False
    # Device binding / single-session-per-device
    DEVICE_ID_SALT: str = "dev_salt"
    DEVICE_BIND_REFRESH: bool = True
    SINGLE_SESSION_PER_DEVICE: bool = False
    
    # Настройки защиты от брутфорса
    MAX_FAILED_ATTEMPTS: int = 5
    BLOCK_TIME: int = 300  # 5 минут
    ATTEMPT_TTL: int = 3600  # 1 час
    
    # Настройки суперадминистратора
    SUPERADMIN_EMAIL: str = ""
    SUPERADMIN_PASSWORD: str = ""
    SUPERADMIN_FIRST_NAME: str = "Admin"
    SUPERADMIN_LAST_NAME: str = "User"
    
    # Настройки дефолтного пользователя
    DEFAULT_USER_EMAIL: str = ""
    DEFAULT_USER_PASSWORD: str = ""
    DEFAULT_USER_FIRST_NAME: str = "Default"
    DEFAULT_USER_LAST_NAME: str = "User"
    
    # Настройки загрузки файлов
    UPLOAD_DIR: str = "static/images"
    
    # Настройки RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_USER: str = "user"
    RABBITMQ_PASS: str = "password"
    
    # Dead Letter Exchange настройки
    DLX_NAME: str = "dead_letter_exchange"
    DLX_QUEUE: str = "failed_messages"
    RETRY_DELAY_MS: int = 5000
    
    # Другие параметры из логов
    DATABASE_URL: str = ""
    SERVICE_CLIENTS_RAW: str = ""
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    )


settings = Settings()


def get_db_url() -> str:
    """Формирует URL-строку для подключения к базе данных."""
    return (f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@"
            f"{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")


def get_access_token_expires_delta() -> timedelta:
    """Возвращает время жизни токена доступа."""
    return timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)


def get_service_token_expires_delta() -> timedelta:
    """Возвращает время жизни сервисного токена."""
    return timedelta(minutes=settings.SERVICE_TOKEN_EXPIRE_MINUTES)


def get_refresh_token_expires_delta() -> timedelta:
    """Возвращает время жизни refresh-токена."""
    return timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)


def get_origins() -> list[str]:
    """Возвращает список разрешенных источников для CORS."""
    return [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1",
    ] 