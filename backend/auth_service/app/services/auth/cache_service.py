"""Сервис кэширования для аутентификации с использованием Redis."""

import hashlib
import json
import logging
import os
import pickle
from functools import wraps
from typing import Any, Optional, Union, Callable

from redis import asyncio as aioredis
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

logger = logging.getLogger(__name__)

# Настройки Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_CACHE_DB", "1"))  # Используем отдельную БД для кэша
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Настройки кэширования
DEFAULT_CACHE_TTL = int(os.getenv("DEFAULT_CACHE_TTL", "3600"))  # 1 час по умолчанию
USER_CACHE_TTL = int(os.getenv("USER_CACHE_TTL", "300"))  # 5 минут для пользовательских данных
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

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
            redis_url += f"{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            
            # Создаем асинхронное подключение к Redis с использованием нового API
            self.redis = await aioredis.Redis.from_url(
                redis_url,
                socket_timeout=3,
                decode_responses=True  # Автоматически декодируем ответы из байтов в строки
            )
            
            logger.info("Подключение к Redis для кэширования успешно: %s:%s/%s", REDIS_HOST, REDIS_PORT, REDIS_DB)
        except (RedisConnectionError, RedisTimeoutError) as e:
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
                try:
                    # Если данные хранятся как pickle
                    if isinstance(data, bytes):
                        return pickle.loads(data)
                    elif isinstance(data, str) and data.startswith(b'\x80\x04'):
                        # Предположительно это pickle в строковом представлении
                        return pickle.loads(data.encode('latin1'))
                    
                    # Если это JSON строка
                    try:
                        return json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        # Если не JSON и не pickle, возвращаем как есть
                        return data
                except (pickle.UnpicklingError, TypeError):
                    # Если не удалось десериализовать, возвращаем как есть
                    return data
            return None
        except RedisError as e:
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
            # Сериализуем данные с помощью pickle для сохранения типов данных
            data = pickle.dumps(value)
            await self.redis.setex(key, ttl, data)
            return True
        except RedisError as e:
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
        except RedisError as e:
            logger.error("Ошибка при удалении ключа из кэша: %s", str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Удаляет ключи, соответствующие шаблону
        
        Args:
            pattern: Шаблон ключей для удаления (например, "user:*")
            
        Returns:
            int: Количество удаленных ключей
        """
        if not self.enabled or not self.redis:
            return 0
            
        try:
            # Используем команду SCAN для поиска ключей по шаблону (безопаснее чем KEYS)
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
        except RedisError as e:
            logger.error("Ошибка при удалении ключей по шаблону %s: %s", pattern, str(e))
            return 0
    
    def get_key_for_user(self, user_id: Union[int, str], action: str) -> str:
        """
        Формирует ключ кэша для пользовательских данных
        
        Args:
            user_id: ID пользователя
            action: Название действия/метода
            
        Returns:
            str: Ключ кэша
        """
        return f"user:{user_id}:{action}"
    
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
            logger.info("Соединение с Redis закрыто")

# Создаем глобальный экземпляр сервиса кэширования
cache_service = CacheService()

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