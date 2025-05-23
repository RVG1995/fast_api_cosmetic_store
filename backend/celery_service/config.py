"""Конфигурационные настройки для сервиса заказов."""

import os
import pathlib
from typing import Dict, List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
   
    # Настройки Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 8  # Order service использует DB 2
   
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
    ORDER_SERVICE_URL: str = "http://localhost:8003"
    
    # Межсервисная авторизация
    SERVICE_CLIENT_ID: str = "celery"
    SERVICE_CLIENTS_RAW: str = ""  # "orders:orders_secret,carts:carts_secret"
    SERVICE_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Настройки для отправки уведомлений
    NOTIFY_ON_ORDER_STATUS_CHANGE: bool = True
    
    # RabbitMQ settings (если используется)
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_USER: str = "user"
    RABBITMQ_PASS: str = "password"

    BOXBERRY_TOKEN: str = ""
    BOXBERRY_COUNTRY_RUSSIA_CODE: str = "643"
    BOXBERRY_API_URL: str = "https://api.boxberry.ru/json.php"
    BOXBERRY_CACHE_TTL: int = 86400 
    BOXBERRY_MAX_SIDE_LENGTH: int = 120
    BOXBERRY_MAX_PVZ_SIDE_LENGTH: int = 185
    BOXBERRY_MAX_TOTAL_DIMENSIONS: int = 250

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
