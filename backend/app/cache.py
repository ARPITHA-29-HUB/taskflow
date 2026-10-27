import json
import logging
import uuid
from typing import Any, Optional

import redis
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger("taskflow.cache")
logger.setLevel(logging.INFO)

REDIS_URL = settings.REDIS_URL
DEFAULT_CACHE_TTL = 60  # seconds


class CacheService:
    """Resilient Cache-Aside service with logging and automatic database fallback."""

    _client: Optional[redis.Redis]

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        if redis_client is not None:
            self._client = redis_client
        else:
            try:
                self._client = redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=0.5,
                    socket_timeout=0.5,
                )
            except Exception as e:
                logger.warning(f"[CACHE INIT WARNING] Failed to configure Redis client: {e}")
                self._client = None

    def get(self, key: str) -> Optional[dict]:
        """Fetch cached JSON payload. Returns None on cache miss or Redis failure."""
        if not self._client:
            return None

        try:
            raw_data = self._client.get(key)
            if raw_data is not None:
                logger.info(f"[CACHE HIT] key={key}")
                return json.loads(raw_data)
            logger.info(f"[CACHE MISS] key={key}")
            return None
        except RedisError as e:
            logger.warning(f"[CACHE ERROR] Redis unavailable during GET, falling back to database: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
        """Store JSON-serializable value in cache with TTL. Fails gracefully if Redis is down."""
        if not self._client:
            return False

        try:
            serialized = json.dumps(value)
            self._client.setex(key, ttl, serialized)
            logger.info(f"[CACHE SET] key={key} ttl={ttl}s")
            return True
        except RedisError as e:
            logger.warning(f"[CACHE ERROR] Redis unavailable during SET, skipping cache write: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Evict a key from the cache (invalidation)."""
        if not self._client:
            return False

        try:
            self._client.delete(key)
            logger.info(f"[CACHE INVALIDATE] key={key}")
            return True
        except RedisError as e:
            logger.warning(f"[CACHE ERROR] Redis unavailable during DELETE: {e}")
            return False

    def invalidate_project_summary(self, project_id: uuid.UUID | str) -> bool:
        """Helper to invalidate a specific project's summary cache."""
        key = f"project:{project_id}:summary"
        return self.delete(key)


# Global singleton instance
cache_service = CacheService()


def get_cache() -> CacheService:
    """FastAPI dependency for accessing the cache service."""
    return cache_service
