import logging

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError, RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self._redis = None
        self._available = False

    async def initialize(self):
        """Initialize Redis connection. If it fails, the client will work in no-cache mode."""
        try:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await self._redis.ping()
            self._available = True
            logger.info("Redis connection established successfully")
        except (ConnectionError, RedisError, OSError) as e:
            logger.warning(f"Redis connection failed: {e}. Running in no-cache mode.")
            self._redis = None
            self._available = False

    async def close(self):
        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")

    @property
    def client(self):
        return self._redis

    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._available

    async def get(self, key: str) -> str | None:
        """Get value from Redis. Returns None if Redis is unavailable."""
        if not self._available:
            return None
        try:
            return await self._redis.get(key)
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    async def set(self, key: str, value: str, ex: int | None = None):
        """Set value in Redis. Silently fails if Redis is unavailable."""
        if not self._available:
            return
        try:
            await self._redis.set(key, value, ex=ex)
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis set failed: {e}")

    async def delete(self, key: str):
        """Delete key from Redis. Silently fails if Redis is unavailable."""
        if not self._available:
            return
        try:
            await self._redis.delete(key)
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis delete failed: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis. Returns False if Redis is unavailable."""
        if not self._available:
            return False
        try:
            return await self._redis.exists(key)
        except (ConnectionError, RedisError) as e:
            logger.warning(f"Redis exists failed: {e}")
            return False


redis_client = RedisClient()
