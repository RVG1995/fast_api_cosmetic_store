"""
Модуль кэширования для product_service. Использует Redis для хранения кэша, поддерживает асинхронные операции, TTL, инвалидацию и декоратор для кэширования функций.
"""

import os
import logging
import hashlib
from typing import Any, Optional, Callable
from functools import wraps

import pickle
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError, ResponseError as RedisResponseError

# Настройка логирования
logger = logging.getLogger("product_service")

# Настройки Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = 1  # Product service использует DB 1
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Настройки кэширования
DEFAULT_CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))  # TTL кэша в секундах (по умолчанию 10 минут)
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

# Ключи для кэширования различных типов данных
CACHE_KEYS = {
    "products": "products:",
    "categories": "categories:",
    "subcategories": "subcategories:",
    "brands": "brands:",
    "countries": "countries:",
}

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
            # Создаем строку подключения Redis
            redis_url = "redis://"
            if REDIS_PASSWORD:
                redis_url += f":{REDIS_PASSWORD}@"
            redis_url += f"{REDIS_HOST}:{REDIS_PORT}"  # Убираем REDIS_DB из URL
            
            # Создаем асинхронное подключение к Redis с использованием нового API
            self.redis = await redis.Redis.from_url(
                redis_url,
                socket_timeout=3,
                decode_responses=False  # Не декодируем ответы для поддержки pickle
            )
            
            # Явно выбираем базу данных после создания соединения
            await self.redis.select(REDIS_DB)
            
            logger.info("Подключение к Redis для кэширования успешно: %s:%s/%s", REDIS_HOST, REDIS_PORT, REDIS_DB)
        except (RedisConnectionError, RedisTimeoutError, RedisResponseError) as e:
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
                return pickle.loads(data)
            return None
        except (RedisConnectionError, RedisTimeoutError, RedisResponseError, pickle.PickleError) as e:
            logger.error("Ошибка при получении данных из кэша: %s", str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
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
            await self.redis.set(key, pickle.dumps(value), ex=ttl)
            return True
        except (RedisConnectionError, RedisTimeoutError, RedisResponseError, pickle.PickleError) as e:
            logger.error("Ошибка при сохранении данных в кэш: %s", str(e))
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
            return True
        except (RedisConnectionError, RedisTimeoutError, RedisResponseError) as e:
            logger.error("Ошибка при удалении ключа из кэша: %s", str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Удаляет ключи, соответствующие шаблону
        
        Args:
            pattern: Шаблон ключей для удаления (например, "products:*")
            
        Returns:
            int: Количество удаленных ключей
        """
        if not self.enabled or not self.redis:
            return 0
            
        try:
            # Используем команду SCAN для поиска ключей по шаблону
            keys_to_delete = []
            cur = 0
            while True:
                cur, keys = await self.redis.scan(cursor=cur, match=pattern, count=100)
                keys_to_delete.extend(keys)
                if cur == 0:
                    break
            
            # Удаляем найденные ключи
            if keys_to_delete:
                return await self.redis.delete(*keys_to_delete)
            return 0
        except (RedisConnectionError, RedisTimeoutError, RedisResponseError) as e:
            logger.error("Ошибка при удалении ключей по шаблону %s: %s", pattern, str(e))
            return 0
    
    async def invalidate_cache(self, entity_type: str = None) -> bool:
        """
        Инвалидирует кэш для определенного типа сущностей или всего кэша
        
        Args:
            entity_type: Тип сущности (products, categories, и т.д.)
            
        Returns:
            bool: True при успешной инвалидации, иначе False
        """
        try:
            if entity_type:
                pattern = f"{CACHE_KEYS.get(entity_type, entity_type)}*"
                logger.info("Инвалидация кэша для %s по шаблону: %s", entity_type, pattern)
                await self.delete_pattern(pattern)
                
                # Если инвалидируем продукты, то также инвалидируем кэш в формате, используемом cart_service
                if entity_type == "products":
                    logger.info("Инвалидация кэша продуктов для cart_service")
                    await self.delete_pattern("product:*")
                return True
            else:
                # Инвалидировать весь кэш, связанный с продуктами
                for key_prefix in CACHE_KEYS.values():
                    await self.delete_pattern(f"{key_prefix}*")
                
                # Инвалидируем кэш продуктов для cart_service
                logger.info("Инвалидация кэша продуктов для cart_service")
                await self.delete_pattern("product:*")
                
                logger.info("Инвалидация всего кэша")
                return True
        except (RedisConnectionError, RedisTimeoutError, RedisResponseError) as e:
            logger.error("Ошибка при инвалидации кэша: %s", str(e))
            return False
    
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
                key_parts.append(str(arg))
        
        # Добавляем именованные аргументы в отсортированном порядке
        if kwargs:
            for k in sorted(kwargs.keys()):
                key_parts.append(f"{k}:{kwargs[k]}")
        
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
            logger.info("Соединение с Redis для кэширования закрыто")

# Создаем глобальный экземпляр сервиса кэширования
cache_service = CacheService()

# Старые функции, переработанные для использования нового CacheService
async def cache_get(key: str) -> Any:
    """
    Получить данные из кэша по ключу
    """
    return await cache_service.get(key)

async def cache_set(key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """
    Сохранить данные в кэш
    """
    return await cache_service.set(key, value, ttl)

async def cache_delete_pattern(pattern: str) -> bool:
    """
    Удалить все ключи, соответствующие шаблону
    """
    deleted = await cache_service.delete_pattern(pattern)
    return deleted > 0

async def invalidate_cache(entity_type: str = None):
    """
    Инвалидировать кэш для определенного типа сущностей или всего кэша
    """
    return await cache_service.invalidate_cache(entity_type)

async def close_redis_connection():
    """
    Закрыть соединение с Redis
    """
    await cache_service.close()
    return True

# Декоратор для кэширования результатов функций
def cached(ttl: int = DEFAULT_CACHE_TTL, prefix: str = None, key_builder: Callable = None):
    """
    Декоратор для кэширования результатов асинхронных функций
    
    Args:
        ttl: Время жизни кэша в секундах
        prefix: Префикс ключа кэша (по умолчанию имя функции)
        key_builder: Функция для построения ключа кэша (если нужна особая логика)
        
    Returns:
        Callable: Декорированная функция
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not cache_service.enabled or not cache_service.redis:
                # Если кэширование отключено, просто выполняем функцию
                return await func(*args, **kwargs)
                
            # Определяем ключ кэша
            if key_builder:
                # Если указан пользовательский построитель ключа
                cache_key = key_builder(*args, **kwargs)
            else:
                # По умолчанию используем имя функции как префикс
                func_prefix = prefix or func.__name__
                cache_key = cache_service.get_key_for_function(func_prefix, *args, **kwargs)
                
            # Пытаемся получить результат из кэша
            cached_result = await cache_service.get(cache_key)
            
            if cached_result is not None:
                logger.debug("Получены данные из кэша для ключа: %s", cache_key)
                return cached_result
                
            # Если в кэше нет, выполняем функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем результат в кэш
            if result is not None:
                await cache_service.set(cache_key, result, ttl)
                logger.debug("Сохранены данные в кэш для ключа: %s", cache_key)
                
            return result
            
        return wrapper
    return decorator
