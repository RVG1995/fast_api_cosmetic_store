import os
import logging
import pickle
import redis.asyncio as redis
from typing import Any, Optional, List, Dict

logger = logging.getLogger("order_cache")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("ORDER_CACHE_TTL", 300))  # 5 минут по умолчанию

redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=False)

class CacheKeys:
    ORDER = "order:"
    ORDERS_LIST = "orders:"
    USER_ORDERS = "user_orders:"
    STATISTICS = "stats:"
    ORDER_STATUSES = "order_statuses:"

async def get_cached_data(key: str) -> Optional[Any]:
    try:
        data = await redis_client.get(key)
        return pickle.loads(data) if data else None
    except Exception as e:
        logger.error(f"Cache get error: {str(e)}")
        return None

async def set_cached_data(key: str, data: Any, ttl: int = CACHE_TTL) -> bool:
    try:
        await redis_client.set(key, pickle.dumps(data), ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Cache set error: {str(e)}")
        return False

async def invalidate_cache(*patterns: str) -> None:
    try:
        deleted_keys = []
        for pattern in patterns:
            keys_to_delete = []
            async for key in redis_client.scan_iter(match=pattern):
                keys_to_delete.append(key)
                deleted_keys.append(key.decode('utf-8') if isinstance(key, bytes) else key)
            
            if keys_to_delete:
                await redis_client.delete(*keys_to_delete)
                logger.info(f"Удалены ключи по шаблону {pattern}: {keys_to_delete}")
        
        if deleted_keys:
            logger.info(f"Всего удалено ключей: {len(deleted_keys)}")
        else:
            logger.info(f"Не найдено ключей для удаления по шаблонам: {patterns}")
    except Exception as e:
        logger.error(f"Cache invalidation error: {str(e)}")

async def close_redis() -> None:
    try:
        await redis_client.close()
    except Exception as e:
        logger.error(f"Redis close error: {str(e)}")

# Специализированные функции для кэширования заказов

async def cache_order(order_id: int, order_data: Any) -> bool:
    """Кэширование данных о заказе"""
    key = f"{CacheKeys.ORDER}{order_id}"
    return await set_cached_data(key, order_data)

async def get_cached_order(order_id: int) -> Optional[Any]:
    """Получение кэшированных данных о заказе"""
    key = f"{CacheKeys.ORDER}{order_id}"
    return await get_cached_data(key)

async def invalidate_order_cache(order_id: int) -> None:
    """Инвалидация кэша конкретного заказа"""
    await invalidate_cache(f"{CacheKeys.ORDER}{order_id}")
    # Инвалидируем также связанные ключи
    await invalidate_cache(f"{CacheKeys.ORDERS_LIST}*")
    await invalidate_cache(f"{CacheKeys.USER_ORDERS}*")
    await invalidate_cache(f"{CacheKeys.STATISTICS}*")
    logger.info(f"Инвалидирован кэш заказа {order_id} и связанных списков")

async def cache_orders_list(filter_params: str, orders_data: Any) -> bool:
    """Кэширование списка заказов"""
    key = f"{CacheKeys.ORDERS_LIST}{filter_params}"
    return await set_cached_data(key, orders_data)

async def get_cached_orders_list(filter_params: str) -> Optional[Any]:
    """Получение кэшированного списка заказов"""
    key = f"{CacheKeys.ORDERS_LIST}{filter_params}"
    return await get_cached_data(key)

async def cache_user_orders(user_id: int, filter_params: str, orders_data: Any) -> bool:
    """Кэширование списка заказов пользователя"""
    key = f"{CacheKeys.USER_ORDERS}{user_id}:{filter_params}"
    return await set_cached_data(key, orders_data)

async def get_cached_user_orders(user_id: int, filter_params: str) -> Optional[Any]:
    """Получение кэшированного списка заказов пользователя"""
    key = f"{CacheKeys.USER_ORDERS}{user_id}:{filter_params}"
    return await get_cached_data(key)

async def cache_order_statistics(statistics_data: Any, user_id: Optional[int] = None) -> bool:
    """Кэширование статистики заказов"""
    key = f"{CacheKeys.STATISTICS}user_{user_id}" if user_id else f"{CacheKeys.STATISTICS}all"
    return await set_cached_data(key, statistics_data)

async def get_cached_order_statistics(user_id: Optional[int] = None) -> Optional[Any]:
    """Получение кэшированной статистики заказов"""
    key = f"{CacheKeys.STATISTICS}user_{user_id}" if user_id else f"{CacheKeys.STATISTICS}all"
    return await get_cached_data(key)

async def invalidate_statistics_cache() -> None:
    """Инвалидация кэша статистики"""
    await invalidate_cache(f"{CacheKeys.STATISTICS}*")

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
    await invalidate_cache(f"{CacheKeys.USER_ORDERS}{user_id}:*")
    logger.info(f"Инвалидирован кэш заказов пользователя {user_id}") 