"""Кэш для настроек уведомлений с использованием Redis."""
import json
import logging
from typing import Optional, List, Dict

from redis.asyncio import Redis, from_url
from redis.exceptions import RedisError

from .config import REDIS_URL, SETTINGS_CACHE_TTL

logger = logging.getLogger("notifications_cache")

async def get_redis() -> Optional[Redis]:
    """Get or create a Redis connection without global"""
    if not hasattr(get_redis, "client"):
        try:
            get_redis.client = await from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info("Connected to Redis: %s", REDIS_URL)
        except RedisError as e:
            logger.error("Redis connect error: %s", e)
            get_redis.client = None
    return get_redis.client

async def close_redis() -> None:
    """Close Redis connection"""
    if hasattr(get_redis, "client"):
        try:
            await get_redis.client.close()
            logger.info("Redis connection closed")
        except RedisError as e:
            logger.error("Redis close error: %s", e)
        delattr(get_redis, "client")

async def cache_get_settings(user_id: int) -> Optional[List[Dict]]:
    """Retrieve cached notification settings for a user"""
    redis = await get_redis()
    if not redis:
        return None
    key = f"notifications:settings:{user_id}"
    try:
        data = await redis.get(key)
        if data:
            logger.debug("Cache hit for user %s settings", user_id)
            return json.loads(data)
        logger.debug("Cache miss for user %s settings", user_id)
    except RedisError as e:
        logger.warning("Redis get error for key %s: %s", key, e)
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
        logger.debug("Cached settings for user %s (TTL=%ss)", user_id, SETTINGS_CACHE_TTL)
        return True
    except RedisError as e:
        logger.warning("Redis set error for key %s: %s", key, e)
    return False

async def cache_delete_settings(user_id: int) -> bool:
    """Delete cached notification settings for a user"""
    redis = await get_redis()
    if not redis:
        return False
    key = f"notifications:settings:{user_id}"
    try:
        await redis.delete(key)
        logger.debug("Deleted cache for user %s", user_id)
        return True
    except RedisError as e:
        logger.warning("Redis delete error for key %s: %s", key, e)
    return False

async def invalidate_settings_cache(user_id: int) -> bool:
    """
    Инвалидация кэша настроек уведомлений - удаляет старый кэш
    и делает его недействительным, чтобы следующий запрос получил
    актуальные данные из базы данных.
    """
    logger.info("Invalidating notification settings cache for user %s", user_id)
    return await cache_delete_settings(user_id)
