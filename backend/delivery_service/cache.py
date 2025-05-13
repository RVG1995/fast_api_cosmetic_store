"""Модуль для работы с кэшированием данных в Redis."""

from typing import Any, Optional, Dict, Union, Callable
import logging
import hashlib
from functools import wraps

import pickle
import redis.asyncio as redis

from config import settings, get_redis_url, get_cache_ttl, get_cache_keys

logger = logging.getLogger("order_cache")

# Настройки кэширования из конфигурации
DEFAULT_CACHE_TTL = settings.ORDER_CACHE_TTL
CACHE_ENABLED = settings.CACHE_ENABLED

class CacheKeys:
    """Константы для ключей кэша"""
    ORDER_PREFIX = "order:"  # Префикс для ключей заказов
    USER_ORDERS_PREFIX = "user_orders:"  # Префикс для ключей списков заказов пользователя
    ADMIN_ORDERS_PREFIX = "admin_orders:"  # Префикс для ключей списков заказов в админке
    ORDER_STATUSES = "order_statuses"  # Ключ для списка статусов заказов
    ORDER_STATISTICS = "order_statistics"  # Ключ для статистики заказов
    ORDER_REPORTS_PREFIX = "order_statistics:report:"  # Префикс для ключей отчетов заказов
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
            # Получаем URL для Redis из конфигурации
            redis_url = get_redis_url()
            
            # Создаем асинхронное подключение к Redis с использованием нового API
            self.redis = await redis.Redis.from_url(
                redis_url,
                socket_timeout=3,
                decode_responses=False  # Не декодируем ответы для поддержки pickle
            )
            
            logger.info("Подключение к Redis для кэширования успешно: %s:%s/%s", 
                       settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
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
            sorted_kwargs = sorted(kwargs.items())
            for key, value in sorted_kwargs:
                key_parts.append(f"{key}={value}")
        
        # Создаем полный ключ
        full_key = ":".join(key_parts)
        
        # Если ключ слишком длинный, создаем хеш
        if len(full_key) > 250:
            return f"{prefix}:{hashlib.md5(full_key.encode()).hexdigest()}"
        
        return full_key
    
    async def close(self):
        """Закрывает соединение с Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Соединение с Redis закрыто")

# Создаем экземпляр сервиса кэширования
cache_service = CacheService()

# Функции-хелперы для работы с кэшем
async def get_cached_data(key: str) -> Optional[Any]:
    """Получает данные из кэша"""
    return await cache_service.get(key)

async def set_cached_data(key: str, data: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """Сохраняет данные в кэш"""
    return await cache_service.set(key, data, ttl)

async def invalidate_cache(*patterns: str) -> None:
    """
    Инвалидирует кэш по указанным шаблонам
    
    Args:
        *patterns: Шаблоны ключей для инвалидации
    """
    if not patterns:
        return
        
    for pattern in patterns:
        if not pattern:
            continue
        
        logger.info("Инвалидация кэша по шаблону: %s", pattern)
        await cache_service.delete_pattern(pattern)

# Закрытие соединения с Redis
async def close_redis() -> None:
    """Закрывает соединение с Redis"""
    await cache_service.close()

# Функции для кэширования заказов
async def cache_order(order_id: int, order_data: Dict[str, Any], admin: bool = False, cache_key: Optional[str] = None) -> None:
    """
    Кэширует данные заказа
    
    Args:
        order_id: ID заказа
        order_data: Данные заказа для кэширования
        admin: Флаг для отличия административного и пользовательского кэша
        cache_key: Произвольный ключ кэша (если None, будет сгенерирован автоматически)
    """
    if not CACHE_ENABLED:
        return
        
    try:
        # Определяем ключ кэша
        key = cache_key or (f"{CacheKeys.ORDER_PREFIX}{order_id}" + ("_admin" if admin else ""))
        
        # Получаем TTL для заказа из конфигурации
        ttl = get_cache_ttl().get("order", DEFAULT_CACHE_TTL)
        
        # Кэшируем данные
        await set_cached_data(key, order_data, ttl)
    except Exception as e:
        logger.error("Ошибка при кэшировании заказа %s: %s", order_id, str(e))

async def get_cached_order(order_id, user_id=None, admin=False):
    """
    Получает данные заказа из кэша
    
    Args:
        order_id: ID заказа
        user_id: ID пользователя (опционально, для логирования)
        admin: Флаг для отличия административного и пользовательского кэша
        
    Returns:
        Optional[Dict[str, Any]]: Данные заказа или None, если не найдены в кэше
    """
    if not CACHE_ENABLED:
        return None
        
    try:
        # Определяем ключ кэша
        key = f"{CacheKeys.ORDER_PREFIX}{order_id}" + ("_admin" if admin else "")
        
        # Получаем данные из кэша
        data = await get_cached_data(key)
        
        if data:
            logger.info("Найдены кэшированные данные заказа %s%s", 
                      order_id, f" для пользователя {user_id}" if user_id else "")
        
        return data
    except Exception as e:
        logger.error("Ошибка при получении заказа %s из кэша: %s", order_id, str(e))
        return None

async def invalidate_order_cache(order_id: int) -> None:
    """
    Инвалидирует кэш для заказа по ID
    
    Args:
        order_id: ID заказа
    """
    if not CACHE_ENABLED:
        return
        
    try:
        # Инвалидируем кэш заказа (и админский и пользовательский)
        await invalidate_cache(
            f"{CacheKeys.ORDER_PREFIX}{order_id}*",  # Все варианты этого заказа
            f"{CacheKeys.USER_ORDERS_PREFIX}*",  # Все списки заказов пользователей
            f"{CacheKeys.ADMIN_ORDERS_PREFIX}*",  # Все списки заказов в админке
        )
    except Exception as e:
        logger.error("Ошибка при инвалидации кэша заказа %s: %s", order_id, str(e))

# Функции для кэширования списков заказов
async def cache_orders_list(filter_params: str, orders_data: Any) -> bool:
    """Кэширует список заказов в административной панели"""
    key = f"{CacheKeys.ADMIN_ORDERS_PREFIX}{filter_params}"
    ttl = get_cache_ttl().get("orders_list", DEFAULT_CACHE_TTL)
    return await set_cached_data(key, orders_data, ttl)

async def get_cached_orders_list(filter_params: str) -> Optional[Any]:
    """Получает список заказов из кэша административной панели"""
    key = f"{CacheKeys.ADMIN_ORDERS_PREFIX}{filter_params}"
    return await get_cached_data(key)

async def cache_user_orders(user_id: int, filter_params: str, orders_data: Any) -> bool:
    """Кэширует список заказов пользователя"""
    key = f"{CacheKeys.USER_ORDERS_PREFIX}{user_id}:{filter_params}"
    ttl = get_cache_ttl().get("orders_list", DEFAULT_CACHE_TTL)
    return await set_cached_data(key, orders_data, ttl)

async def get_cached_user_orders(user_id: int, filter_params: str) -> Optional[Any]:
    """Получает список заказов пользователя из кэша"""
    key = f"{CacheKeys.USER_ORDERS_PREFIX}{user_id}:{filter_params}"
    return await get_cached_data(key)

async def cache_order_statistics(statistics_data: Any, user_id: Optional[int] = None) -> bool:
    """Кэширует статистику заказов (общую или для конкретного пользователя)"""
    key = CacheKeys.ORDER_STATISTICS if user_id is None else f"{CacheKeys.USER_STATISTICS_PREFIX}{user_id}"
    ttl = get_cache_ttl().get("statistics" if user_id is None else "user_statistics", DEFAULT_CACHE_TTL)
    return await set_cached_data(key, statistics_data, ttl)

async def get_cached_order_statistics(user_id: Optional[int] = None) -> Optional[Any]:
    """Получает статистику заказов из кэша (общую или для конкретного пользователя)"""
    key = CacheKeys.ORDER_STATISTICS if user_id is None else f"{CacheKeys.USER_STATISTICS_PREFIX}{user_id}"
    return await get_cached_data(key)

async def invalidate_statistics_cache() -> None:
    """Инвалидирует кэш статистики заказов"""
    await invalidate_cache(
        CacheKeys.ORDER_STATISTICS, 
        f"{CacheKeys.USER_STATISTICS_PREFIX}*",
        f"{CacheKeys.ORDER_REPORTS_PREFIX}*"  # Инвалидация кэша отчетов
    )

async def cache_order_statuses(statuses_data: Any) -> bool:
    """Кэширует список статусов заказов"""
    ttl = get_cache_ttl().get("statistics", DEFAULT_CACHE_TTL)
    return await set_cached_data(CacheKeys.ORDER_STATUSES, statuses_data, ttl)

async def get_cached_order_statuses() -> Optional[Any]:
    """Получает список статусов заказов из кэша"""
    return await get_cached_data(CacheKeys.ORDER_STATUSES)

async def invalidate_order_statuses_cache() -> None:
    """Инвалидирует кэш списка статусов заказов"""
    await cache_service.delete(CacheKeys.ORDER_STATUSES)

async def invalidate_user_orders_cache(user_id: int) -> None:
    """Инвалидирует кэш списков заказов пользователя"""
    await invalidate_cache(f"{CacheKeys.USER_ORDERS_PREFIX}{user_id}:*")

async def invalidate_promo_code_cache(promo_code_id: int) -> None:
    """
    Инвалидирует кэш для промокода по ID
    
    Args:
        promo_code_id: ID промокода
    """
    if not CACHE_ENABLED:
        return
        
    try:
        # Инвалидируем кэш промокода и список всех промокодов
        await invalidate_cache(
            f"{CacheKeys.PROMO_CODE_PREFIX}{promo_code_id}*",  # Конкретный промокод
            f"{CacheKeys.PROMO_CODES}*",  # Список всех промокодов
        )
        
        # Инвалидируем также кэш проверок промокодов, содержащий этот ID
        # Это сложнее сделать по шаблону, поэтому лучше инвалидировать все проверки
        await invalidate_cache(f"{CacheKeys.PROMO_CODE_PREFIX}check:*")
    except Exception as e:
        logger.error("Ошибка при инвалидации кэша промокода %s: %s", promo_code_id, str(e))

async def cache_promo_code_check(email: str, phone: str, promo_code_id: int, result: bool) -> None:
    """
    Кэширует результат проверки промокода для пользователя
    
    Args:
        email: Email пользователя
        phone: Телефон пользователя 
        promo_code_id: ID промокода
        result: Результат проверки (True/False)
    """
    if not email and not phone:
        return
        
    # Создаем хеш для идентификации пользователя
    user_hash = hashlib.md5((email or '') + (phone or '')).hexdigest()
    
    # Создаем ключ кэша
    key = f"{CacheKeys.PROMO_CODE_PREFIX}check:{promo_code_id}:{user_hash}"
    
    # Устанавливаем TTL для проверки промокода (обычно короткий, 5-10 минут)
    ttl = 600  # 10 минут
    
    await set_cached_data(key, result, ttl)

async def get_cached_promo_code_check(email: str, phone: str, promo_code_id: int) -> Optional[bool]:
    """
    Получает результат проверки промокода для пользователя из кэша
    
    Args:
        email: Email пользователя
        phone: Телефон пользователя
        promo_code_id: ID промокода
        
    Returns:
        Optional[bool]: Кэшированный результат проверки или None, если не найден
    """
    if not email and not phone:
        return None
        
    # Создаем хеш для идентификации пользователя
    user_hash = hashlib.md5((email or '') + (phone or '')).hexdigest()
    
    # Создаем ключ кэша
    key = f"{CacheKeys.PROMO_CODE_PREFIX}check:{promo_code_id}:{user_hash}"
    
    return await get_cached_data(key)

async def invalidate_reports_cache() -> None:
    """Инвалидирует кэш отчетов заказов"""
    await invalidate_cache(f"{CacheKeys.ORDER_REPORTS_PREFIX}*")