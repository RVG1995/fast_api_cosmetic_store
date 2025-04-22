import os
import json
import logging
from typing import Any, Optional, List, Dict
# Современный импорт для Redis вместо устаревшего
from redis.asyncio import Redis, from_url
from .config import REDIS_URL, SETTINGS_CACHE_TTL

logger = logging.getLogger("notifications_cache")

# Global Redis client
_redis_client: Optional[Redis] = None

async def get_redis() -> Optional[Redis]:
    """Get or create a Redis connection"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = await from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"Connected to Redis: {REDIS_URL}")
        except Exception as e:
            logger.error(f"Redis connect error: {e}")
            _redis_client = None
    return _redis_client

async def close_redis() -> None:
    """Close Redis connection"""
    global _redis_client
    if _redis_client:
        try:
            await _redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Redis close error: {e}")
        _redis_client = None

async def cache_get_settings(user_id: int) -> Optional[List[Dict]]:
    """Retrieve cached notification settings for a user"""
    redis = await get_redis()
    if not redis:
        return None
    key = f"notifications:settings:{user_id}"
    try:
        data = await redis.get(key)
        if data:
            logger.debug(f"Cache hit for user {user_id} settings")
            return json.loads(data)
        logger.debug(f"Cache miss for user {user_id} settings")
    except Exception as e:
        logger.warning(f"Redis get error for key {key}: {e}")
    return None

async def cache_set_settings(user_id: int, settings: List[Dict]) -> bool:
    """Cache notification settings for a user"""
    redis = await get_redis()
    if not redis:
        return False
    key = f"notifications:settings:{user_id}"
    try:
        serialized = json.dumps(settings, default=str)
        await redis.setex(key, SETTINGS_CACHE_TTL, serialized)
        logger.debug(f"Cached settings for user {user_id} (TTL={SETTINGS_CACHE_TTL}s)")
        return True
    except Exception as e:
        logger.warning(f"Redis set error for key {key}: {e}")
    return False

async def cache_delete_settings(user_id: int) -> bool:
    """Delete cached notification settings for a user"""
    redis = await get_redis()
    if not redis:
        return False
    key = f"notifications:settings:{user_id}"
    try:
        await redis.delete(key)
        logger.debug(f"Deleted cache for user {user_id}")
        return True
    except Exception as e:
        logger.warning(f"Redis delete error for key {key}: {e}")
    return False

async def invalidate_settings_cache(user_id: int) -> bool:
    """
    Инвалидация кэша настроек уведомлений - удаляет старый кэш
    и делает его недействительным, чтобы следующий запрос получил
    актуальные данные из базы данных.
    """
    logger.info(f"Invalidating notification settings cache for user {user_id}")
    return await cache_delete_settings(user_id) 