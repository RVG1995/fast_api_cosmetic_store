import logging
import pickle
import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError, ResponseError as RedisResponseError
from config import settings

logger = logging.getLogger("favorite_service")

REDIS_HOST = settings.REDIS_HOST
REDIS_PORT = settings.REDIS_PORT
REDIS_PASSWORD = settings.REDIS_PASSWORD
REDIS_DB = settings.REDIS_DB
DEFAULT_CACHE_TTL = 900  # 15 минут

class CacheService:
    def __init__(self):
        self.redis = None

    async def initialize(self):
        try:
            redis_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            if REDIS_PASSWORD:
                redis_url = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
            self.redis = await redis.Redis.from_url(
                redis_url,
                socket_timeout=3,
                decode_responses=False
            )
            logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}/9")
        except (RedisConnectionError, RedisTimeoutError, RedisResponseError) as e:
            logger.error(f"Redis connection error: {e}")
            self.redis = None

    async def get(self, key: str):
        if not self.redis:
            return None
        try:
            data = await self.redis.get(key)
            if data:
                return pickle.loads(data)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value, ttl: int = DEFAULT_CACHE_TTL):
        if not self.redis:
            return False
        try:
            await self.redis.set(key, pickle.dumps(value), ex=ttl)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str):
        if not self.redis:
            return False
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def delete_pattern(self, pattern: str):
        if not self.redis:
            return 0
        try:
            keys_to_delete = []
            cur = 0
            while True:
                cur, keys = await self.redis.scan(cursor=cur, match=pattern, count=100)
                keys_to_delete.extend(keys)
                if cur == 0:
                    break
            if keys_to_delete:
                return await self.redis.delete(*keys_to_delete)
            return 0
        except Exception as e:
            logger.error(f"Cache delete_pattern error: {e}")
            return 0

    async def invalidate_cache(self, prefix: str = None):
        if not self.redis:
            return 0
        try:
            if prefix:
                pattern = f"{prefix}*"
                logger.info(f"Invalidating cache for pattern: {pattern}")
                return await self.delete_pattern(pattern)
            else:
                logger.info("Invalidating all cache in db9")
                return await self.redis.flushdb()
        except Exception as e:
            logger.error(f"Cache invalidate_cache error: {e}")
            return 0

    async def close(self):
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")

cache_service = CacheService() 