"""Модуль для работы с кэшированием данных в Redis."""

import os
from typing import Any, Optional, Dict, Union, Callable
import logging
import hashlib
from functools import wraps

import pickle
import redis.asyncio as redis

logger = logging.getLogger("order_cache")

# Настройки Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = 2  # Order service использует DB 2
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

# Настройки кэширования
DEFAULT_CACHE_TTL = int(os.getenv("ORDER_CACHE_TTL", "300"))  # 5 минут по умолчанию
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

class CacheKeys:
    """Константы для ключей кэша"""
    ORDER_PREFIX = "order:"  # Префикс для ключей заказов
    USER_ORDERS_PREFIX = "user_orders:"  # Префикс для ключей списков заказов пользователя
    ADMIN_ORDERS_PREFIX = "admin_orders:"  # Префикс для ключей списков заказов в админке
    ORDER_STATUSES = "order_statuses"  # Ключ для списка статусов заказов
    ORDER_STATISTICS = "order_statistics"  # Ключ для статистики заказов
    USER_STATISTICS_PREFIX = "user_statistics:"  # Префикс для ключей статистики пользователя
    PRODUCTS_INFO_PREFIX = "products_info:"  # Префикс для ключей информации о продуктах
    PROMO_CODES = "promo_codes"  # Ключ для списка промокодов
    PROMO_CODE_PREFIX = "promo_code:"  # Префикс для ключей промокодов

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
            self.redis = await redis.Redis.from_url(
                redis_url,
                socket_timeout=3,
                decode_responses=False  # Не декодируем ответы для поддержки pickle
            )
            
            logger.info("Подключение к Redis для кэширования успешно: %s:%s/%s", REDIS_HOST, REDIS_PORT, REDIS_DB)
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
                return pickle.loads(data)
            return None
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
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
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
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
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Удаляет ключи, соответствующие шаблону
        
        Args:
            pattern: Шаблон ключей для удаления (например, "order:*")
            
        Returns:
            int: Количество удаленных ключей
        """
        if not self.enabled or not self.redis:
            return 0
            
        try:
            deleted_keys = []
            async for key in self.redis.scan_iter(match=pattern):
                deleted_keys.append(key)
            
            if deleted_keys:
                await self.redis.delete(*deleted_keys)
                logger.info("Удалены ключи по шаблону %s: %s шт.", pattern, len(deleted_keys))
                return len(deleted_keys)
            return 0
        except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
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

# Функции-обертки над методами CacheService для совместимости

async def get_cached_data(key: str) -> Optional[Any]:
    return await cache_service.get(key)

async def set_cached_data(key: str, data: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    return await cache_service.set(key, data, ttl)

async def invalidate_cache(*patterns: str) -> None:
    try:
        deleted_count = 0
        for pattern in patterns:
            count = await cache_service.delete_pattern(pattern)
            deleted_count += count
        
        if deleted_count > 0:
            logger.info("Всего удалено ключей: %s", deleted_count)
        else:
            logger.info("Не найдено ключей для удаления по шаблонам: %s", patterns)
    except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
        logger.error("Cache invalidation error: %s", str(e))

async def close_redis() -> None:
    await cache_service.close()

# Специализированные функции для кэширования заказов

async def cache_order(order_id: int, order_data: Dict[str, Any], admin: bool = False) -> None:
    """
    Кэширование данных заказа
    
    Args:
        order_id: ID заказа
        order_data: Данные заказа для кэширования
        admin: Флаг, указывающий, что кэширование выполняется для админской панели
    """
    try:
        key = f"{CacheKeys.ORDER_PREFIX}{order_id}"
        await cache_service.set(key, order_data, DEFAULT_CACHE_TTL)
        logger.info("Заказ %s успешно кэширован%s", order_id, ' (админ)' if admin else '')
    except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
        logger.error("Ошибка при кэшировании заказа %s: %s", order_id, str(e))

async def get_cached_order(order_id: int, admin: bool = False) -> Optional[Dict[str, Any]]:
    """
    Получение данных заказа из кэша
    
    Args:
        order_id: ID заказа
        admin: Флаг, указывающий, что получение выполняется для админской панели
        
    Returns:
        Данные заказа или None, если нет в кэше
    """
    try:
        key = f"{CacheKeys.ORDER_PREFIX}{order_id}"
        data = await cache_service.get(key)
        if data:
            logger.info("Найден кэш для заказа %s%s", order_id, ' (админ)' if admin else '')
            return data
        logger.info("Кэш для заказа %s не найден%s", order_id, ' (админ)' if admin else '')
        return None
    except (redis.ConnectionError, redis.TimeoutError, redis.ResponseError) as e:
        logger.error("Ошибка при получении заказа %s из кэша: %s", order_id, str(e))
        return None

async def invalidate_order_cache(order_id: int) -> None:
    """Инвалидация кэша конкретного заказа"""
    await invalidate_cache(f"{CacheKeys.ORDER_PREFIX}{order_id}")
    # Инвалидируем также связанные ключи
    await invalidate_cache(f"{CacheKeys.USER_ORDERS_PREFIX}*")
    await invalidate_cache(f"{CacheKeys.ADMIN_ORDERS_PREFIX}*")
    await invalidate_cache(f"{CacheKeys.ORDER_STATISTICS}*")
    logger.info("Инвалидирован кэш заказа %s и связанных списков", order_id)

async def cache_orders_list(filter_params: str, orders_data: Any) -> bool:
    """Кэширование списка заказов"""
    key = f"{CacheKeys.ADMIN_ORDERS_PREFIX}{filter_params}"
    return await set_cached_data(key, orders_data)

async def get_cached_orders_list(filter_params: str) -> Optional[Any]:
    """Получение кэшированного списка заказов"""
    key = f"{CacheKeys.ADMIN_ORDERS_PREFIX}{filter_params}"
    return await get_cached_data(key)

async def cache_user_orders(user_id: int, filter_params: str, orders_data: Any) -> bool:
    """Кэширование списка заказов пользователя"""
    key = f"{CacheKeys.USER_ORDERS_PREFIX}{user_id}:{filter_params}"
    return await set_cached_data(key, orders_data)

async def get_cached_user_orders(user_id: int, filter_params: str) -> Optional[Any]:
    """Получение кэшированного списка заказов пользователя"""
    key = f"{CacheKeys.USER_ORDERS_PREFIX}{user_id}:{filter_params}"
    return await get_cached_data(key)

async def cache_order_statistics(statistics_data: Any, user_id: Optional[int] = None) -> bool:
    """Кэширование статистики заказов"""
    key = f"{CacheKeys.ORDER_STATISTICS}user_{user_id}" if user_id else f"{CacheKeys.ORDER_STATISTICS}all"
    return await set_cached_data(key, statistics_data)

async def get_cached_order_statistics(user_id: Optional[int] = None) -> Optional[Any]:
    """Получение кэшированной статистики заказов"""
    key = f"{CacheKeys.ORDER_STATISTICS}user_{user_id}" if user_id else f"{CacheKeys.ORDER_STATISTICS}all"
    return await get_cached_data(key)

async def invalidate_statistics_cache() -> None:
    """Инвалидация кэша статистики"""
    await invalidate_cache(f"{CacheKeys.ORDER_STATISTICS}*")

async def cache_order_statuses(statuses_data: Any) -> bool:
    """Кэширование списка статусов заказов"""
    key = CacheKeys.ORDER_STATUSES
    return await set_cached_data(key, statuses_data)

async def get_cached_order_statuses() -> Optional[Any]:
    """Получение кэшированного списка статусов заказов"""
    key = CacheKeys.ORDER_STATUSES
    return await get_cached_data(key)

async def invalidate_order_statuses_cache() -> None:
    """Инвалидация кэша статусов заказов"""
    await invalidate_cache(f"{CacheKeys.ORDER_STATUSES}*")

async def invalidate_user_orders_cache(user_id: int) -> None:
    """Инвалидация кэша заказов пользователя"""
    await invalidate_cache(f"{CacheKeys.USER_ORDERS_PREFIX}{user_id}:*")
    logger.info("Инвалидирован кэш заказов пользователя %s", user_id)

async def invalidate_promo_code_cache(promo_code_id: int) -> None:
    """
    Инвалидация кэша промокода по ID
    
    Args:
        promo_code_id: ID промокода
    """
    # Формируем ключ для кэша промокода
    cache_key = f"{CacheKeys.PROMO_CODE_PREFIX}{promo_code_id}"
    
    # Удаляем кэш
    await cache_service.delete(cache_key)
    
    # Дополнительно инвалидируем общий кэш промокодов
    await cache_service.delete(CacheKeys.PROMO_CODES)
    
    logger.info("Кэш промокода с ID %s инвалидирован", promo_code_id)

async def cache_promo_code_check(email: str, phone: str, promo_code_id: int, result: bool) -> None:
    """
    Кеширование результата проверки промокода
    
    Args:
        email: Email пользователя
        phone: Телефон пользователя
        promo_code_id: ID промокода
        result: Результат проверки (True/False)
    """
    # Формируем ключ для кэша
    cache_key = f"promo_check:{email}:{phone}:{promo_code_id}"
    
    # Кешируем результат на 1 час
    await cache_service.set(cache_key, result, 3600)
    
    logger.info("Результат проверки промокода %s для %s/%s закеширован", promo_code_id, email, phone)

async def get_cached_promo_code_check(email: str, phone: str, promo_code_id: int) -> Optional[bool]:
    """
    Получение кешированного результата проверки промокода
    
    Args:
        email: Email пользователя
        phone: Телефон пользователя
        promo_code_id: ID промокода
    
    Returns:
        Optional[bool]: Кешированный результат или None, если кеша нет
    """
    # Формируем ключ для кэша
    cache_key = f"promo_check:{email}:{phone}:{promo_code_id}"
    
    # Получаем результат из кэша
    return await cache_service.get(cache_key)

# Декоратор для кэширования
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
