"""
Модуль для работы с кэшированием данных в Redis.
"""

import os
from typing import Any, Optional
import logging
import pickle

import redis.asyncio as redis

# Настройка логирования
logger = logging.getLogger("email_consumer_cache")

# Настройки Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = 6  # Email consumer использует DB 6
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Настройки кэширования
DEFAULT_CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 минут по умолчанию
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"


class CacheService:
    """Упрощенный сервис кэширования данных с использованием Redis"""
    
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
            self.redis = await redis.Redis.from_url(
                redis_url,
                socket_timeout=3,
                decode_responses=False  # Не декодируем ответы для поддержки pickle
            )
            
            logger.info("Подключение к Redis для кэширования успешно: %s:%s/%s", REDIS_HOST, REDIS_PORT, REDIS_DB)
        except Exception as e:
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
        except Exception as e:
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
        except Exception as e:
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
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
            logger.error("Ошибка при удалении ключа из кэша: %s", str(e))
            return False
    
    async def close(self):
        """Закрывает соединение с Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Соединение с Redis закрыто")


# Создаем глобальный экземпляр сервиса кэширования
cache_service = CacheService()


# Функции-обертки над методами CacheService для совместимости
async def get_cached_data(key: str) -> Optional[Any]:
    """
    Получает значение из кэша по ключу
    
    Args:
        key: Ключ кэша
        
    Returns:
        Optional[Any]: Значение из кэша или None, если ключ не найден
    """
    if not cache_service.redis:
        await cache_service.initialize()
    return await cache_service.get(key)


async def set_cached_data(key: str, data: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """
    Сохраняет значение в кэш
    
    Args:
        key: Ключ кэша
        data: Значение для сохранения
        ttl: Время жизни ключа в секундах
        
    Returns:
        bool: True при успешном сохранении, иначе False
    """
    if not cache_service.redis:
        await cache_service.initialize()
    return await cache_service.set(key, data, ttl)



async def close_redis() -> None:
    """Закрывает соединение с Redis"""
    await cache_service.close()
