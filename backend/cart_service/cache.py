"""Сервис кэширования для корзины с использованием Redis."""

import json
import logging
from functools import wraps
from datetime import datetime
from typing import Optional, Any, Callable, TypeVar
import hashlib
import redis.asyncio as redis

from config import settings, get_redis_url, get_cache_ttl, get_cache_keys

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cart_cache")

# Настройки Redis из конфигурации
REDIS_HOST = settings.REDIS_HOST
REDIS_PORT = settings.REDIS_PORT
REDIS_DB = settings.REDIS_DB  # Cart service использует DB 3
REDIS_PASSWORD = settings.REDIS_PASSWORD

# Настройки кэширования из конфигурации
CACHE_ENABLED = settings.CACHE_ENABLED

# Время жизни кэша
CACHE_TTL = get_cache_ttl()

# Префиксы ключей кэша
CACHE_KEYS = get_cache_keys()

# Собственный JSONEncoder для обработки даты и времени и байтов
class DateTimeEncoder(json.JSONEncoder):
    """Класс для сериализации объектов datetime и bytes в JSON"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        return super().default(obj)

class CacheService:
    """Сервис кэширования данных с использованием Redis"""
    
    def __init__(self):
        """Инициализация сервиса кэширования"""
        self.enabled = CACHE_ENABLED
        self.redis = None
            
        if not self.enabled:
            logger.info("Кэширование отключено в настройках")
            return
            
        logger.info("Кэширование включено, инициализация соединения с Redis")
    
    async def initialize(self):
        """Асинхронная инициализация соединения с Redis"""
        if not self.enabled:
            return
            
        try:
            # Используем helper-функцию для получения URL Redis
            redis_url = get_redis_url()
            
            # Создаем асинхронное подключение к Redis с использованием нового API
            self.redis = await redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True  # Декодируем ответы для поддержки JSON
            )
            
            logger.info("Подключение к Redis для кэширования успешно: %s:%d/%d", REDIS_HOST, REDIS_PORT, REDIS_DB)
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error("Ошибка подключения к Redis для кэширования: %s", str(e))
            self.redis = None
            self.enabled = False
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Получает значение из кэша по ключу
        
        Args:
            key: Ключ кэша
            
        Returns:
            Optional[Any]: Значение из кэша или None, если ключ не найден
        """
        if not self.enabled or not self.redis:
            return None
            
        try:
            data = await self.redis.get(key)
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
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.warning("Ошибка при получении данных из кэша (%s): %s", key, str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """
        Сохраняет значение в кэш
        
        Args:
            key: Ключ кэша
            value: Значение для сохранения
            ttl: Время жизни ключа в секундах
            
        Returns:
            bool: True при успешном сохранении, иначе False
        """
        if not self.enabled or not self.redis:
            return False
            
        try:
            # Рекурсивно проверяем и преобразуем bytes объекты
            def convert_bytes(obj):
                if isinstance(obj, bytes):
                    return obj.decode('utf-8', errors='replace')
                elif isinstance(obj, dict):
                    return {k: convert_bytes(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_bytes(item) for item in obj]
                elif isinstance(obj, tuple):
                    return tuple(convert_bytes(item) for item in obj)
                return obj
            
            # Преобразуем bytes перед сериализацией
            value_to_store = convert_bytes(value)
            
            await self.redis.setex(key, ttl, json.dumps(value_to_store, cls=DateTimeEncoder))
            logger.debug("Данные сохранены в кэш: %s (TTL: %dс)", key, ttl)
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.warning("Ошибка при сохранении данных в кэш (%s): %s", key, str(e))
            return False
        except (TypeError, ValueError) as e:
            logger.error("Ошибка при сериализации данных для кэша (%s): %s", key, str(e))
            # Логируем тип объекта, вызвавшего ошибку
            logger.error("Тип проблемного объекта: %s", type(value))
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Удаляет ключ из кэша
        
        Args:
            key: Ключ для удаления
            
        Returns:
            bool: True при успешном удалении, иначе False
        """
        if not self.enabled or not self.redis:
            return False
            
        try:
            await self.redis.delete(key)
            logger.debug("Данные удалены из кэша: %s", key)
            return True
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.warning("Ошибка при удалении ключа из кэша (%s): %s", key, str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Удаляет ключи, соответствующие шаблону
        
        Args:
            pattern: Шаблон ключей для удаления (например, "cart:user:*")
            
        Returns:
            int: Количество удаленных ключей
        """
        if not self.enabled or not self.redis:
            return 0
            
        try:
            keys = await self.redis.keys(pattern)
            count = 0
            if keys:
                count = await self.redis.delete(*keys)
                logger.debug("Удалено %d ключей по шаблону: %s", len(keys), pattern)
            return count
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.warning("Ошибка при удалении данных из кэша по шаблону (%s): %s", pattern, str(e))
            return 0
    
    def get_key_for_function(self, prefix: str, *args, **kwargs) -> str:
        """
        Формирует ключ кэша для функции на основе аргументов
        
        Args:
            prefix: Префикс ключа (обычно имя функции)
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы
            
        Returns:
            str: Ключ кэша
        """
        # Создаем хеш от аргументов функции
        key_parts = [prefix]
        
        # Добавляем позиционные аргументы
        if args:
            for arg in args:
                if hasattr(arg, "__dict__"):
                    # Для объектов используем строковое представление
                    key_parts.append(str(arg))
                else:
                    key_parts.append(str(arg))
        
        # Добавляем именованные аргументы в отсортированном порядке
        if kwargs:
            for k in sorted(kwargs.keys()):
                if k == "db" or k == "session":
                    # Пропускаем сессию базы данных
                    continue
                if hasattr(kwargs[k], "__dict__"):
                    # Для объектов используем строковое представление
                    key_parts.append(f"{k}:{str(kwargs[k])}")
                else:
                    key_parts.append(f"{k}:{str(kwargs[k])}")
        
        # Объединяем все части ключа
        key_str = ":".join(key_parts)
        
        # Если ключ получился слишком длинным, хешируем его
        if len(key_str) > 100:
            key_hash = hashlib.md5(key_str.encode()).hexdigest()
            return f"{prefix}:hash:{key_hash}"
            
        return key_str
    
    async def close(self):
        """Закрывает соединение с Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Соединение с Redis закрыто")

# Создаем глобальный экземпляр сервиса кэширования
cache_service = CacheService()

# Функции-обертки для обратной совместимости

async def get_redis():
    """
    Получает или создает подключение к Redis
    
    Returns:
        Redis: Клиент Redis или None в случае ошибки
    """
    if not cache_service.redis:
        await cache_service.initialize()
    return cache_service.redis

async def close_redis():
    """Закрывает соединение с Redis"""
    await cache_service.close()

async def cache_get(key: str) -> Optional[Any]:
    """
    Получает данные из кэша
    
    Args:
        key (str): Ключ кэша
        
    Returns:
        Optional[Any]: Данные из кэша или None, если данные не найдены
    """
    return await cache_service.get(key)

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
    return await cache_service.set(key, data, ttl)

async def cache_delete(key: str) -> bool:
    """
    Удаляет данные из кэша
    
    Args:
        key (str): Ключ кэша
        
    Returns:
        bool: True, если данные успешно удалены, иначе False
    """
    return await cache_service.delete(key)

async def cache_delete_pattern(pattern: str) -> bool:
    """
    Удаляет данные из кэша по шаблону ключа
    
    Args:
        pattern (str): Шаблон ключа (например, "cart:user:*")
        
    Returns:
        bool: True, если данные успешно удалены, иначе False
    """
    count = await cache_service.delete_pattern(pattern)
    return count > 0

# Функции инвалидации кэша

async def invalidate_user_cart_cache(user_id: int) -> None:
    """
    Инвалидирует кэш корзины пользователя
    
    Args:
        user_id (int): ID пользователя
    """
    logger.info("Инвалидация кэша корзины пользователя: %d", user_id)
    # Удаляем кэш корзины
    await cache_service.delete("%s%d" % (CACHE_KEYS['cart_user'], user_id))
    # Удаляем кэш сводки корзины
    await cache_service.delete("%s%d" % (CACHE_KEYS['cart_summary_user'], user_id))
    # Удаляем кэш списка корзин в админке
    await cache_service.delete_pattern("%s*" % CACHE_KEYS['admin_carts'])

async def invalidate_session_cart_cache(session_id: str) -> None:
    """
    Инвалидирует кэш корзины сессии
    
    Args:
        session_id (str): ID сессии
    """
    logger.info("Инвалидация кэша корзины сессии: %s", session_id)
    # Удаляем кэш корзины
    await cache_service.delete("%s%s" % (CACHE_KEYS['cart_session'], session_id))
    # Удаляем кэш сводки корзины
    await cache_service.delete("%s%s" % (CACHE_KEYS['cart_summary_session'], session_id))

async def invalidate_admin_carts_cache() -> None:
    """
    Инвалидирует кэш списка корзин в админке
    """
    logger.info("Инвалидация кэша списка корзин в админке")
    await cache_service.delete_pattern("%s*" % CACHE_KEYS['admin_carts'])

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
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not cache_service.enabled or not cache_service.redis:
                # Если кэширование отключено, просто выполняем функцию
                return await func(*args, **kwargs)
                
            # Строим ключ кэша
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_service.get_key_for_function(key_prefix, *args, **kwargs)
            
            # Проверяем кэш
            cached_data = await cache_service.get(cache_key)
            if cached_data is not None:
                logger.debug("Возвращены кэшированные данные для %s: %s", func.__name__, cache_key)
                return cached_data
            
            # Выполняем функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем результат в кэш
            if result is not None:
                try:
                    # Рекурсивно преобразуем bytes перед сохранением
                    def convert_bytes(obj):
                        if isinstance(obj, bytes):
                            return obj.decode('utf-8', errors='replace')
                        elif isinstance(obj, dict):
                            return {k: convert_bytes(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [convert_bytes(item) for item in obj]
                        elif isinstance(obj, tuple):
                            return tuple(convert_bytes(item) for item in obj)
                        return obj
                    
                    result_to_cache = convert_bytes(result)
                    await cache_service.set(cache_key, result_to_cache, ttl)
                    logger.debug("Данные сохранены в кэш для %s: %s", func.__name__, cache_key)
                except Exception as e:
                    logger.error("Ошибка при сохранении в кэш для %s: %s", func.__name__, str(e))
            
            return result
        return wrapper
    return decorator
