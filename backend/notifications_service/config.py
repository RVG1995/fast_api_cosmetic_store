"""Конфигурационные настройки для сервиса уведомлений."""

import os
import pathlib
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # RabbitMQ settings
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_USER: str = "user"
    RABBITMQ_PASS: str = "password"
    EVENT_EXCHANGE: str = "events"
    EVENT_ROUTING_KEYS: str = "review.created,review.reply,service.critical_error,order.created,order.status_changed,product.low_stock"
    
    # Database settings
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5437/notifications_db"
    
    # Spam prevention threshold (seconds)
    SPAM_THRESHOLD: int = 300

    # SMTP settings
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""

    # Push notifications queue name
    PUSH_QUEUE: str = "push_notifications"

    # Auth service settings
    AUTH_SERVICE_URL: str = "http://localhost:8000"
    JWT_SECRET_KEY: str = "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke"
    ALGORITHM: str = "HS256"
    INTERNAL_SERVICE_KEY: str = "test"

    # Dead Letter Exchange и retry для очередей уведомлений
    DLX_NAME: str = "dead_letter_exchange"
    DLX_QUEUE: str = "failed_notifications"
    MAX_RETRY_COUNT: int = 3
    RETRY_DELAY_MS: int = 5000
    
    # Настройки для реконнекта
    MAX_RECONNECT_ATTEMPTS: int = 10
    INITIAL_RECONNECT_DELAY: float = 1.0
    MAX_RECONNECT_DELAY: float = 30.0
    CONNECTION_CHECK_INTERVAL: float = 5.0

    # Event types
    EVENT_TYPE_ORDER_STATUS_CHANGED: str = "order.status_changed"

    # Redis settings for notifications cache
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 5
    # TTL for notification settings cache in seconds
    SETTINGS_CACHE_TTL: int = 60
    
    # Service clients
    SERVICE_CLIENT_ID: str = "notifications"
    SERVICE_CLIENTS_RAW: str = ""  # "orders:orders_secret,notifications:notifications_secret"
    SERVICE_TOKEN_EXPIRE_MINUTES: int = 30
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    )


def get_env_file_path() -> str | None:
    """Определяет путь к .env файлу."""
    current_dir = pathlib.Path(__file__).parent.absolute()
    env_file = current_dir / ".env"
    parent_env_file = current_dir.parent / ".env"
    
    if env_file.exists():
        return str(env_file)
    elif parent_env_file.exists():
        return str(parent_env_file)
    return None


settings = Settings()


def get_db_url() -> str:
    """Возвращает URL для подключения к базе данных."""
    return settings.DATABASE_URL


def get_redis_url() -> str:
    """Возвращает URL для подключения к Redis."""
    return settings.REDIS_URL


def get_event_routing_keys() -> list[str]:
    """Возвращает список ключей маршрутизации событий."""
    return settings.EVENT_ROUTING_KEYS.split(",")


def get_service_clients() -> dict[str, str]:
    """Возвращает словарь с учетными данными сервисов для межсервисной авторизации."""
    if not settings.SERVICE_CLIENTS_RAW:
        return {}
    return {kv.split(":")[0]: kv.split(":")[1] for kv in settings.SERVICE_CLIENTS_RAW.split(",") if ":" in kv} 