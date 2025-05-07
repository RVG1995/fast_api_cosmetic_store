"""Сервис кэширования на основе Redis с асинхронной поддержкой для уведомлений."""

import json
import logging
import hashlib
from functools import wraps

from typing import Any, Optional, List, Dict, Callable
import redis.asyncio as redis

from config import settings, get_redis_url

logger = logging.getLogger("notifications_cache")

# Настройки кэширования
CACHE_ENABLED = True  # По умолчанию включено

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
            if settings.REDIS_PASSWORD:
                redis_url += f":{settings.REDIS_PASSWORD}@"
            redis_url += f"{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            
            # Создаем асинхронное подключение к Redis с использованием нового API
            self.redis = await redis.Redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True  # Декодируем ответы для поддержки JSON
            )
            
            logger.info("Подключение к Redis для кэширования успешно: %s:%s/%s", settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
        except (redis.ConnectionError, redis.TimeoutError, redis.RedisError) as e:
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
                return json.loads(data)
            return None
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.error("Ошибка при получении данных из кэша: %s", str(e))
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
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
            serialized = json.dumps(value, default=str)
            if ttl:
                await self.redis.setex(key, ttl, serialized)
            else:
                await self.redis.set(key, serialized)
            return True
        except (redis.RedisError, json.JSONDecodeError) as e:
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
        except redis.RedisError as e:
            logger.error("Ошибка при удалении ключа из кэша: %s", str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Удаляет ключи, соответствующие шаблону
        
        Args:
            pattern: Шаблон ключей для удаления (например, "notifications:*")
            
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
        except redis.RedisError as e:
            logger.error("Ошибка при удалении ключей по шаблону %s: %s", pattern, str(e))
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

# Функция для получения соединения с Redis
async def get_redis():
    """Инициализирует и возвращает клиент Redis."""
    if not cache_service.redis:
        await cache_service.initialize()
    return cache_service.redis

# Функция для закрытия соединения
async def close_redis():
    """Закрывает соединение с Redis."""
    await cache_service.close()

# Функции для работы с кэшем настроек уведомлений
async def cache_get_settings(user_id: int) -> Optional[List[Dict]]:
    """Получает настройки уведомлений пользователя из кэша."""
    key = f"notifications:settings:{user_id}"
    return await cache_service.get(key)

async def cache_set_settings(user_id: int, settings_data: List[Dict]) -> bool:
    """Сохраняет настройки уведомлений пользователя в кэш."""
    key = f"notifications:settings:{user_id}"
    return await cache_service.set(key, settings_data, settings.SETTINGS_CACHE_TTL)

async def cache_delete_settings(user_id: int) -> bool:
    """Удаляет настройки уведомлений пользователя из кэша."""
    key = f"notifications:settings:{user_id}"
    return await cache_service.delete(key)

async def invalidate_settings_cache(user_id: int) -> bool:
    """
    Инвалидирует весь кэш настроек уведомлений для пользователя.
    Используется после изменения настроек.
    """
    pattern = f"notifications:settings:{user_id}"
    deleted = await cache_service.delete_pattern(pattern)
    return deleted > 0

# Декоратор для кэширования результатов асинхронных функций
def cached(ttl: int, prefix: str = None, key_builder: Callable = None):
    """
    Декоратор для кэширования результатов асинхронных функций.
    
    Args:
        ttl: Время жизни кэша в секундах
        prefix: Префикс ключа кэша (по умолчанию имя функции)
        key_builder: Функция для построения ключа кэша
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Если кэширование отключено, просто возвращаем результат функции
            if not cache_service.enabled or not cache_service.redis:
                return await func(*args, **kwargs)
            
            # Формируем ключ кэша
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = cache_service.get_key_for_function(
                    prefix or func.__name__, 
                    *args, 
                    **kwargs
                )
            
            # Пытаемся получить результат из кэша
            cached_data = await cache_service.get(cache_key)
            if cached_data is not None:
                logger.debug("Возвращены кэшированные данные для %s", cache_key)
                return cached_data
            
            # Если в кэше нет, выполняем функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем результат в кэш, только если он не None
            if result is not None:
                await cache_service.set(cache_key, result, ttl)
                logger.debug("Результат функции %s сохранен в кэш: %s", func.__name__, cache_key)
            
            return result
        return wrapper
    return decorator
