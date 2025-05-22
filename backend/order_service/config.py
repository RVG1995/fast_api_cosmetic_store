"""Конфигурационные настройки для сервиса заказов."""

import os
import pathlib
from typing import Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Настройки базы данных
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5435/orders_db"
    
    # Настройки Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 2  # Order service использует DB 2
    
    # Настройки кэширования
    CACHE_ENABLED: bool = True
    ORDER_CACHE_TTL: int = 300  # 5 минут для заказа
    ORDERS_LIST_CACHE_TTL: int = 60  # 1 минута для списка заказов
    STATISTICS_CACHE_TTL: int = 1800  # 30 минут для статистики
    USER_STATISTICS_CACHE_TTL: int = 300  # 5 минут для статистики пользователя
    
    # Настройки JWT
    JWT_SECRET_KEY: str = "zAP5LmC8N7e3Yq9x2Rv4TsX1Wp7Bj5Ke"
    JWT_ALGORITHM: str = "HS256"
    
    # Настройки API
    API_MAX_RETRIES: int = 3  # Максимальное число повторных попыток
    
    # Настройки внешних сервисов
    PRODUCT_SERVICE_URL: str = "http://localhost:8001"
    CART_SERVICE_URL: str = "http://localhost:8002"
    AUTH_SERVICE_URL: str = "http://localhost:8000"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8005"
    
    # Межсервисная авторизация
    SERVICE_CLIENT_ID: str = "orders"
    SERVICE_CLIENTS_RAW: str = ""  # "orders:orders_secret,carts:carts_secret"
    SERVICE_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Настройки для отправки уведомлений
    NOTIFY_ON_ORDER_STATUS_CHANGE: bool = True
    
    # Настройки пагинации по умолчанию
    DEFAULT_PAGE_SIZE: int = 10
    MAX_PAGE_SIZE: int = 100
    
    # Путь к директории загрузок
    UPLOAD_DIR: str = "static/uploads"
    
    # RabbitMQ settings (если используется)
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_USER: str = "user"
    RABBITMQ_PASS: str = "password"

    DADATA_TOKEN: str = ""

    BOXBERRY_STATUSES: dict = {
        1 : 'Не в акте',
        5 : 'В обработке',
        7 : 'Ошибка выгрузки',
        10 : 'Получена информация о заказе. Отправление еще не передано на доставку в Boxberry',
        76 : 'Заказ передан на доставку',
        77 : 'Отправлен на сортировочный терминал',
        80 : 'Поступил на сортировочный терминал',
        90 : 'Ожидает отправки в город Получателя',
        100 : 'В пути в город Получателя',
        110 : 'Поступил в город для передачи Курьеру',
        115 : 'Обработка на складе курьерской доставки',
        120 : 'В городе Получателя. Ожидайте поступления в Пункт выдачи',
        125 : 'Передан на доставку до пункта выдачи',
        130 : 'Передан на Курьерскую доставку, курьер позвонит за 30-60 минут до доставки',
        135 : 'Передано курьеру, курьер позвонит за 30-60 минут до доставки',
        137 : 'Перенос срока курьерской доставки',
        140 : 'Доступен к получению в Пункте выдачи',
        150 : 'Успешно Выдан',
        160 : 'Заказ передан на возврат в Интернет-магазин',
        170 : 'Заказ в пути в Интернет-магазин	',
        180 : 'Возвращено в пункт приема',
        190 : 'Заказ возвращен в Интернет-магазин',
    }

    
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
        "order": settings.ORDER_CACHE_TTL,
        "orders_list": settings.ORDERS_LIST_CACHE_TTL,
        "statistics": settings.STATISTICS_CACHE_TTL,
        "user_statistics": settings.USER_STATISTICS_CACHE_TTL
    }


def get_cache_keys() -> Dict[str, str]:
    """Возвращает префиксы ключей кэша."""
    return {
        "order": "order:",  # Кэш заказа: order:{order_id}
        "user_orders": "orders:user:",  # Кэш заказов пользователя: orders:user:{user_id}:{page}:{size}
        "admin_orders": "orders:admin:",  # Кэш всех заказов для админа с параметрами
        "statistics": "statistics:",  # Кэш статистики: statistics:all
        "user_statistics": "statistics:user:"  # Кэш статистики пользователя: statistics:user:{user_id}
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