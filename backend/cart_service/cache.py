"""Модуль для работы с кэшированием корзин в Redis."""

import json
import logging
import os
import pathlib
from datetime import datetime
from typing import Optional, Any, Callable, TypeVar
from dotenv import load_dotenv
from redis import asyncio as aioredis

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_cache")

# Определяем пути к .env файлам
current_dir = pathlib.Path(__file__).parent.absolute()
env_file = current_dir / ".env"
parent_env_file = current_dir.parent / ".env"

# Загружаем переменные окружения
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
    logger.info("Переменные окружения загружены из %s", env_file)
elif parent_env_file.exists():
    load_dotenv(dotenv_path=parent_env_file)
    logger.info("Переменные окружения загружены из %s", parent_env_file)

# URL соединения с Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Время жизни кэша
CACHE_TTL = {
    "cart": int(os.getenv("CART_CACHE_TTL", "60")),  # 60 секунд для корзины
    "cart_summary": int(os.getenv("CART_SUMMARY_CACHE_TTL", "30")),  # 30 секунд для сводки корзины
    "admin_carts": int(os.getenv("ADMIN_CARTS_CACHE_TTL", "30"))  # 30 секунд для списка корзин в админке
}

# Префиксы ключей кэша
CACHE_KEYS = {
    "cart_user": "cart:user:",  # Корзина пользователя - cart:user:{user_id}
    "cart_session": "cart:session:",  # Корзина сессии - cart:session:{session_id}
    "cart_summary_user": "cart:summary:user:",  # Сводка корзины пользователя
    "cart_summary_session": "cart:summary:session:",  # Сводка корзины сессии
    "admin_carts": "admin:carts:"  # Список корзин для администраторов с параметрами
}

# Собственный JSONEncoder для обработки даты и времени
class DateTimeEncoder(json.JSONEncoder):
    """Класс для сериализации объектов datetime в JSON"""
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

# Одиночное подключение к Redis
class RedisConnection:
    """Класс для управления единым подключением к Redis."""
    _client = None
    
    @classmethod
    async def get_client(cls):
        """Возвращает существующее или создает новое подключение к Redis."""
        if cls._client is None:
            try:
                cls._client = await aioredis.from_url(
                    REDIS_URL, 
                    encoding="utf-8", 
                    decode_responses=True
                )
                logger.info("Установлено подключение к Redis: %s", REDIS_URL)
            except (aioredis.ConnectionError, aioredis.ResponseError) as e:
                logger.error("Ошибка подключения к Redis: %s", str(e))
                cls._client = None
        return cls._client
    
    @classmethod
    async def close(cls):
        """Закрывает соединение с Redis."""
        if cls._client:
            await cls._client.close()
            cls._client = None
            logger.info("Соединение с Redis закрыто")

async def get_redis():
    """
    Получает или создает подключение к Redis
    
    Returns:
        Redis: Клиент Redis или None в случае ошибки
    """
    return await RedisConnection.get_client()

async def close_redis():
    """Закрывает соединение с Redis"""
    await RedisConnection.close()

async def cache_get(key: str) -> Optional[Any]:
    """
    Получает данные из кэша
    
    Args:
        key (str): Ключ кэша
        
    Returns:
        Optional[Any]: Данные из кэша или None, если данные не найдены
    """
    redis = await get_redis()
    if not redis:
        return None
    
    try:
        data = await redis.get(key)
        if data:
            logger.debug("Данные получены из кэша: %s", key)
            parsed = json.loads(data)
            # Если в кэше не словарь, возвращаем как есть (например, строку-токен)
            if not isinstance(parsed, dict):
                return parsed
            # Функция десериализации datetime внутри словаря
            def datetime_parser(dct):
                for k, v in dct.items():
                    if isinstance(v, str):
                        try:
                            if 'T' in v and ('+' in v or 'Z' in v or '-' in v[10:]):
                                dct[k] = datetime.fromisoformat(v.replace('Z', '+00:00'))
                        except (ValueError, TypeError):
                            pass
                    elif isinstance(v, dict):
                        dct[k] = datetime_parser(v)
                return dct
            return datetime_parser(parsed)
            
        return None
    except (aioredis.ConnectionError, aioredis.ResponseError, json.JSONDecodeError) as e:
        logger.warning("Ошибка при получении данных из кэша (%s): %s", key, str(e))
        return None

async def cache_set(key: str, data: Any, ttl: int) -> bool:
    """
    Сохраняет данные в кэш
    
    Args:
        key (str): Ключ кэша
        data (Any): Данные для сохранения
        ttl (int): Время жизни кэша в секундах
        
    Returns:
        bool: True, если данные успешно сохранены, иначе False
    """
    redis = await get_redis()
    if not redis:
        return False
    
    try:
        await redis.setex(key, ttl, json.dumps(data, cls=DateTimeEncoder))
        logger.debug("Данные сохранены в кэш: %s (TTL: %dс)", key, ttl)
        return True
    except (aioredis.ConnectionError, aioredis.ResponseError, TypeError) as e:
        logger.warning("Ошибка при сохранении данных в кэш (%s): %s", key, str(e))
        return False

async def cache_delete(key: str) -> bool:
    """
    Удаляет данные из кэша
    
    Args:
        key (str): Ключ кэша
        
    Returns:
        bool: True, если данные успешно удалены, иначе False
    """
    redis = await get_redis()
    if not redis:
        return False
    
    try:
        await redis.delete(key)
        logger.debug("Данные удалены из кэша: %s", key)
        return True
    except (aioredis.ConnectionError, aioredis.ResponseError) as e:
        logger.warning("Ошибка при удалении данных из кэша (%s): %s", key, str(e))
        return False

async def cache_delete_pattern(pattern: str) -> bool:
    """
    Удаляет данные из кэша по шаблону ключа
    
    Args:
        pattern (str): Шаблон ключа (например, "cart:user:*")
        
    Returns:
        bool: True, если данные успешно удалены, иначе False
    """
    redis = await get_redis()
    if not redis:
        return False
    
    try:
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
            logger.debug("Удалено %d ключей по шаблону: %s", len(keys), pattern)
        return True
    except (aioredis.ConnectionError, aioredis.ResponseError) as e:
        logger.warning("Ошибка при удалении данных из кэша по шаблону (%s): %s", pattern, str(e))
        return False

# Функции инвалидации кэша

async def invalidate_user_cart_cache(user_id: int) -> None:
    """
    Инвалидирует кэш корзины пользователя
    
    Args:
        user_id (int): ID пользователя
    """
    logger.info("Инвалидация кэша корзины пользователя: %d", user_id)
    # Удаляем кэш корзины
    await cache_delete(f"{CACHE_KEYS['cart_user']}{user_id}")
    # Удаляем кэш сводки корзины
    await cache_delete(f"{CACHE_KEYS['cart_summary_user']}{user_id}")
    # Удаляем кэш списка корзин в админке
    await cache_delete_pattern(f"{CACHE_KEYS['admin_carts']}*")

async def invalidate_session_cart_cache(session_id: str) -> None:
    """
    Инвалидирует кэш корзины сессии
    
    Args:
        session_id (str): ID сессии
    """
    logger.info("Инвалидация кэша корзины сессии: %s", session_id)
    # Удаляем кэш корзины
    await cache_delete(f"{CACHE_KEYS['cart_session']}{session_id}")
    # Удаляем кэш сводки корзины
    await cache_delete(f"{CACHE_KEYS['cart_summary_session']}{session_id}")

async def invalidate_admin_carts_cache() -> None:
    """
    Инвалидирует кэш списка корзин в админке
    """
    logger.info("Инвалидация кэша списка корзин в админке")
    await cache_delete_pattern(f"{CACHE_KEYS['admin_carts']}*")

# Декоратор для кэширования

T = TypeVar("T")

def cached(
    key_prefix: str,
    ttl: int,
    key_builder: Optional[Callable[..., str]] = None
):
    """
    Декоратор для кэширования результатов асинхронных функций
    
    Args:
        key_prefix (str): Префикс ключа кэша
        ttl (int): Время жизни кэша в секундах
        key_builder (Optional[Callable[..., str]]): Функция для построения ключа кэша
            принимает те же аргументы, что и декорируемая функция
            
    Returns:
        Callable: Декоратор
        
    Example:
        @cached(
            key_prefix="cart:user:",
            ttl=CACHE_TTL["cart"],
            key_builder=lambda user_id, **kwargs: f"{user_id}"
        )
        async def get_user_cart(user_id: int, db: AsyncSession) -> CartSchema:
            # ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Строим ключ кэша
            if key_builder:
                key_suffix = key_builder(*args, **kwargs)
            else:
                # По умолчанию используем все аргументы функции как часть ключа
                key_parts = []
                for arg in args:
                    if hasattr(arg, "__dict__"):
                        # Для объектов используем строковое представление
                        key_parts.append(str(arg))
                    else:
                        key_parts.append(str(arg))
                
                for k, v in kwargs.items():
                    if k == "db" or k == "session":
                        # Пропускаем сессию базы данных
                        continue
                    if hasattr(v, "__dict__"):
                        # Для объектов используем строковое представление
                        key_parts.append(f"{k}:{str(v)}")
                    else:
                        key_parts.append(f"{k}:{str(v)}")
                
                key_suffix = ":".join(key_parts)
            
            cache_key = f"{key_prefix}{key_suffix}"
            
            # Проверяем кэш
            cached_data = await cache_get(cache_key)
            if cached_data is not None:
                logger.debug("Возвращены кэшированные данные для %s: %s", func.__name__, cache_key)
                return cached_data
            
            # Выполняем функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем результат в кэш
            if result is not None:
                try:
                    # Пытаемся сериализовать и сохранить в кэш
                    await cache_set(cache_key, result, ttl)
                    logger.debug("Результат функции %s сохранен в кэш: %s", func.__name__, cache_key)
                except (aioredis.ConnectionError, aioredis.ResponseError, TypeError) as e:
                    # В случае ошибки сериализации логируем и продолжаем без кеширования
                    logger.warning("Ошибка при кешировании результата %s: %s", func.__name__, str(e))
            
            return result
        return wrapper
    return decorator 