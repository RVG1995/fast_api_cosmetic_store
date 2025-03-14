import os
import logging
import pickle
import redis.asyncio as redis
from typing import Any

# Настройка логирования
logger = logging.getLogger("product_service")

# Инициализация Redis клиента
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.getenv("CACHE_TTL", "600"))  # TTL кэша в секундах (по умолчанию 10 минут)
redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=False)

# Ключи для кэширования различных типов данных
CACHE_KEYS = {
    "products": "products:",
    "categories": "categories:",
    "subcategories": "subcategories:",
    "brands": "brands:",
    "countries": "countries:",
}

async def cache_get(key: str) -> Any:
    """
    Получить данные из кэша по ключу
    """
    try:
        data = await redis_client.get(key)
        if data:
            return pickle.loads(data)
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении данных из кэша: {str(e)}")
        return None

async def cache_set(key: str, value: Any, ttl: int = CACHE_TTL) -> bool:
    """
    Сохранить данные в кэш
    """
    try:
        await redis_client.set(key, pickle.dumps(value), ex=ttl)
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных в кэш: {str(e)}")
        return False

async def cache_delete_pattern(pattern: str) -> bool:
    """
    Удалить все ключи, соответствующие шаблону
    """
    try:
        cursor = 0
        while True:
            cursor, keys = await redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                await redis_client.delete(*keys)
            if cursor == 0:
                break
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении ключей из кэша: {str(e)}")
        return False

async def invalidate_cache(entity_type: str = None):
    """
    Инвалидировать кэш для определенного типа сущностей или всего кэша
    """
    try:
        if entity_type:
            pattern = f"{CACHE_KEYS.get(entity_type, entity_type)}*"
            logger.info(f"Инвалидация кэша для {entity_type} по шаблону: {pattern}")
            return await cache_delete_pattern(pattern)
        else:
            # Инвалидировать весь кэш, связанный с продуктами
            for key_prefix in CACHE_KEYS.values():
                await cache_delete_pattern(f"{key_prefix}*")
            logger.info("Инвалидация всего кэша")
            return True
    except Exception as e:
        logger.error(f"Ошибка при инвалидации кэша: {str(e)}")
        return False

async def close_redis_connection():
    """
    Закрыть соединение с Redis
    """
    try:
        await redis_client.close()
        logger.info("Соединение с Redis закрыто")
        return True
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения с Redis: {str(e)}")
        return False 