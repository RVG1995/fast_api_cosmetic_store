"""Модуль для работы с кэшированием данных в Redis.

Этот модуль предоставляет функции для кэширования и получения данных из Redis,
включая специализированные функции для работы с заказами, промокодами и статистикой.
"""

import os
import logging
import pickle
from typing import Any, Optional, Dict

import redis.asyncio as redis

logger = logging.getLogger("order_cache")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("ORDER_CACHE_TTL", "300"))  # 5 минут по умолчанию

redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=False)

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
    
    @classmethod
    def get_order_key(cls, order_id: int) -> str:
        """Возвращает ключ для кэша заказа."""
        return f"{cls.ORDER_PREFIX}{order_id}"
    
    @classmethod
    def get_user_orders_key(cls, user_id: int, filter_params: str) -> str:
        """Возвращает ключ для кэша списка заказов пользователя."""
        return f"{cls.USER_ORDERS_PREFIX}{user_id}:{filter_params}"

async def get_cached_data(key: str) -> Optional[Any]:
    """Получает данные из кэша по ключу.

    Args:
        key: Ключ для получения данных из кэша

    Returns:
        Данные из кэша или None, если данные не найдены
    """
    try:
        data = await redis_client.get(key)
        return pickle.loads(data) if data else None
    except (redis.RedisError, pickle.PickleError) as e:
        logger.error("Cache get error: %s", str(e))
        return None

async def set_cached_data(key: str, data: Any, ttl: int = CACHE_TTL) -> bool:
    """Сохраняет данные в кэш.

    Args:
        key: Ключ для сохранения данных
        data: Данные для сохранения
        ttl: Время жизни кэша в секундах

    Returns:
        True если данные успешно сохранены, иначе False
    """
    try:
        await redis_client.set(key, pickle.dumps(data), ex=ttl)
        return True
    except (redis.RedisError, pickle.PickleError) as e:
        logger.error("Cache set error: %s", str(e))
        return False

async def invalidate_cache(*patterns: str) -> None:
    """Инвалидирует кэш по указанным шаблонам ключей.

    Args:
        *patterns: Шаблоны ключей для инвалидации
    """
    try:
        deleted_keys = []
        for pattern in patterns:
            keys_to_delete = []
            async for key in redis_client.scan_iter(match=pattern):
                keys_to_delete.append(key)
                deleted_keys.append(key.decode('utf-8') if isinstance(key, bytes) else key)
            
            if keys_to_delete:
                await redis_client.delete(*keys_to_delete)
                logger.info("Удалены ключи по шаблону %s: %s", pattern, keys_to_delete)
        
        if deleted_keys:
            logger.info("Всего удалено ключей: %d", len(deleted_keys))
        else:
            logger.info("Не найдено ключей для удаления по шаблонам: %s", patterns)
    except (redis.RedisError, ValueError) as e:
        logger.error("Cache invalidation error: %s", str(e))

async def close_redis() -> None:
    """Закрывает соединение с Redis."""
    try:
        await redis_client.close()
    except redis.RedisError as e:
        logger.error("Redis close error: %s", str(e))

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
        key = f"order:{order_id}"
        await redis_client.set(key, pickle.dumps(order_data), ex=CACHE_TTL)
        logger.info("Заказ %d успешно кэширован%s", order_id, " (админ)" if admin else "")
    except (redis.RedisError, pickle.PickleError) as e:
        logger.error("Ошибка при кэшировании заказа %d: %s", order_id, str(e))

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
        key = f"order:{order_id}"
        data = await redis_client.get(key)
        if data:
            logger.info("Найден кэш для заказа %d%s", order_id, " (админ)" if admin else "")
            return pickle.loads(data)
        logger.info("Кэш для заказа %d не найден%s", order_id, " (админ)" if admin else "")
        return None
    except (redis.RedisError, pickle.PickleError) as e:
        logger.error("Ошибка при получении заказа %d из кэша: %s", order_id, str(e))
        return None

async def invalidate_order_cache(order_id: int) -> None:
    """Инвалидация кэша конкретного заказа"""
    await invalidate_cache(f"{CacheKeys.ORDER_PREFIX}{order_id}")
    # Инвалидируем также связанные ключи
    await invalidate_cache(f"{CacheKeys.USER_ORDERS_PREFIX}*")
    await invalidate_cache(f"{CacheKeys.ADMIN_ORDERS_PREFIX}*")
    await invalidate_cache(f"{CacheKeys.ORDER_STATISTICS}*")
    logger.info("Инвалидирован кэш заказа %d и связанных списков", order_id)

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
    logger.info("Инвалидирован кэш заказов пользователя %d", user_id)

async def invalidate_promo_code_cache(promo_code_id: int) -> None:
    """Инвалидирует кэш промокода.
    
    Args:
        promo_code_id: ID промокода
    """
    # Формируем ключ для кэша промокода
    cache_key = f"{CacheKeys.PROMO_CODE_PREFIX}{promo_code_id}"
    
    # Удаляем кэш
    await invalidate_cache(cache_key)

async def cache_promo_code_check(email: str, phone: str, promo_code_id: int, result: bool) -> None:
    """Кэширует результат проверки промокода.
    
    Args:
        email: Email пользователя
        phone: Телефон пользователя
        promo_code_id: ID промокода
        result: Результат проверки
    """
    # Формируем ключ для кэша
    cache_key = f"promo_check:{email}:{phone}:{promo_code_id}"
    
    # Кэшируем результат
    await set_cached_data(cache_key, result, ttl=60)  # TTL 1 минута

async def get_cached_promo_code_check(email: str, phone: str, promo_code_id: int) -> Optional[bool]:
    """Получает кэшированный результат проверки промокода.
    
    Args:
        email: Email пользователя
        phone: Телефон пользователя
        promo_code_id: ID промокода
        
    Returns:
        Optional[bool]: Результат проверки или None, если кэш отсутствует
    """
    # Формируем ключ для кэша
    cache_key = f"promo_check:{email}:{phone}:{promo_code_id}"
    
    # Получаем результат из кэша
    return await get_cached_data(cache_key)
