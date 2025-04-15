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
        logger.info(f"Заказ {order_id} успешно кэширован{' (админ)' if admin else ''}")
    except Exception as e:
        logger.error(f"Ошибка при кэшировании заказа {order_id}: {str(e)}")

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
            logger.info(f"Найден кэш для заказа {order_id}{' (админ)' if admin else ''}")
            return pickle.loads(data)
        logger.info(f"Кэш для заказа {order_id} не найден{' (админ)' if admin else ''}")
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении заказа {order_id} из кэша: {str(e)}")
        return None

async def invalidate_order_cache(order_id: int) -> None:
    """Инвалидация кэша конкретного заказа"""
    await invalidate_cache(f"{CacheKeys.ORDER_PREFIX}{order_id}")
    # Инвалидируем также связанные ключи
    await invalidate_cache(f"{CacheKeys.USER_ORDERS_PREFIX}*")
    await invalidate_cache(f"{CacheKeys.ADMIN_ORDERS_PREFIX}*")
    await invalidate_cache(f"{CacheKeys.ORDER_STATISTICS}*")
    logger.info(f"Инвалидирован кэш заказа {order_id} и связанных списков")

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
    logger.info(f"Инвалидирован кэш заказов пользователя {user_id}")

async def invalidate_promo_code_cache(promo_code_id: int) -> None:
    """
    Инвалидация кэша промокода по ID
    
    Args:
        promo_code_id: ID промокода
    """
    # Получаем соединение с Redis
    redis = await get_redis()
    
    # Формируем ключ для кэша промокода
    cache_key = f"{CacheKeys.PROMO_CODE_PREFIX}{promo_code_id}"
    
    # Удаляем кэш
    await redis.delete(cache_key)
    
    # Дополнительно инвалидируем общий кэш промокодов
    await redis.delete(CacheKeys.PROMO_CODES)
    
    logger.info(f"Кэш промокода с ID {promo_code_id} инвалидирован")

async def cache_promo_code_check(email: str, phone: str, promo_code_id: int, result: bool) -> None:
    """
    Кеширование результата проверки промокода
    
    Args:
        email: Email пользователя
        phone: Телефон пользователя
        promo_code_id: ID промокода
        result: Результат проверки (True/False)
    """
    # Получаем соединение с Redis
    redis = await get_redis()
    
    # Формируем ключ для кэша
    cache_key = f"promo_check:{email}:{phone}:{promo_code_id}"
    
    # Кешируем результат на 1 час
    await redis.set(cache_key, str(result), ex=3600)
    
    logger.info(f"Результат проверки промокода {promo_code_id} для {email}/{phone} закеширован")

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
    # Получаем соединение с Redis
    redis = await get_redis()
    
    # Формируем ключ для кэша
    cache_key = f"promo_check:{email}:{phone}:{promo_code_id}"
    
    # Получаем результат из кэша
    result = await redis.get(cache_key)
    
    if result is not None:
        return result.decode() == "True"
    
    return None 