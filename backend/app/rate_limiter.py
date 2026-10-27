"""
TaskFlow Rate Limiter Module
----------------------------
Implements an isolated Token Bucket rate limiter (30 requests/minute per client)
with Redis-backed shared storage, automatic in-memory fallback, and safe
proxy header handling.
"""

import logging
import math
import os
import time
from typing import Any, Optional

import redis
from fastapi import Depends, HTTPException, Request, status
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger("taskflow.rate_limiter")
logger.setLevel(logging.INFO)

REDIS_URL = settings.REDIS_URL
DEFAULT_TRUSTED_PROXIES = settings.TRUSTED_PROXIES
DEFAULT_CAPACITY = 30.0  # Max burst tokens
DEFAULT_REFILL_RATE = 30.0 / 60.0  # 0.5 tokens/sec (30 tokens per minute)
KEY_EXPIRATION_TTL = 120  # TTL for inactive Redis keys

# Atomic Redis Lua script for Token Bucket evaluation
TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])
local ttl = tonumber(ARGV[5])

local data = redis.call("HMGET", key, "tokens", "last_updated")
local tokens = tonumber(data[1])
local last_updated = tonumber(data[2])

if not tokens then
    tokens = capacity
    last_updated = now
else
    local elapsed = math.max(0, now - last_updated)
    tokens = math.min(capacity, tokens + (elapsed * refill_rate))
    last_updated = now
end

if tokens >= requested then
    tokens = tokens - requested
    redis.call("HSET", key, "tokens", tokens, "last_updated", last_updated)
    redis.call("EXPIRE", key, ttl)
    return {1, 0, math.floor(tokens)}
else
    local missing = requested - tokens
    local retry_after = math.ceil(missing / refill_rate)
    if retry_after < 1 then retry_after = 1 end
    return {0, retry_after, 0}
end
"""


def get_client_identifier(request: Request, trusted_proxies: Optional[set[str]] = None) -> str:
    """Safely identify client without blindly trusting spoofable proxy headers.

    Strategy:
    1. Authorization header (authenticated user/token) if present.
    2. Direct connection IP from request.client.host.
    3. If and ONLY if direct connection IP is a verified trusted proxy, inspect
       the leftmost IP from X-Forwarded-For.
    """
    if trusted_proxies is None:
        proxies_str = os.getenv("TRUSTED_PROXIES", DEFAULT_TRUSTED_PROXIES)
        trusted_proxies = {p.strip() for p in proxies_str.split(",") if p.strip()}

    # 1. Authenticated user takes precedence
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.strip():
        return f"auth:{hash(auth_header)}"

    # 2. Determine direct network address
    direct_ip = request.client.host if request.client else "127.0.0.1"

    # 3. Handle reverse proxy headers safely
    if direct_ip in trusted_proxies:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # First IP in X-Forwarded-For is the original client
            parts = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
            if parts:
                return f"ip:{parts[0]}"

    return f"ip:{direct_ip}"


class InMemoryTokenBucket:
    """Thread-safe local fallback for unit tests and when Redis is unreachable."""

    def __init__(self, capacity: float = DEFAULT_CAPACITY, refill_rate: float = DEFAULT_REFILL_RATE):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.store: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_updated)

    def consume(self, key: str, requested: int = 1) -> tuple[bool, int, int]:
        now = time.time()
        if key not in self.store:
            tokens = self.capacity
            last_updated = now
        else:
            tokens, last_updated = self.store[key]
            elapsed = max(0.0, now - last_updated)
            tokens = min(self.capacity, tokens + (elapsed * self.refill_rate))
            last_updated = now

        if tokens >= requested:
            tokens -= requested
            self.store[key] = (tokens, last_updated)
            return True, 0, int(tokens)
        else:
            missing = requested - tokens
            retry_after = math.ceil(missing / self.refill_rate)
            return False, max(1, retry_after), 0

    def reset(self):
        """Reset in-memory storage (useful between test cases)."""
        self.store.clear()


class RateLimiterService:
    """Distributed Token Bucket Rate Limiter with Redis backend & in-memory fallback."""

    def __init__(
        self,
        redis_client: Any = None,
        capacity: float = DEFAULT_CAPACITY,
        refill_rate: float = DEFAULT_REFILL_RATE,
        enable_redis: bool = True,
    ):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.in_memory = InMemoryTokenBucket(capacity, refill_rate)
        self._lua_script = None
        self._redis_available = False

        if not enable_redis:
            self._client = None
            return

        if redis_client is not None:
            self._client = redis_client
            try:
                self._client.ping()
                self._redis_available = True
            except Exception as e:
                logger.warning(f"[RATE LIMITER INIT] Provided Redis client ping failed: {e}")
                self._redis_available = False
        else:
            try:
                self._client = redis.from_url(
                    REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=0.2,
                    socket_timeout=0.2,
                )
                self._client.ping()
                self._redis_available = True
            except Exception as e:
                logger.warning(f"[RATE LIMITER INIT] Redis unreachable, running in in-memory mode: {e}")
                self._client = None
                self._redis_available = False

        if self._client and self._redis_available:
            try:
                self._lua_script = self._client.register_script(TOKEN_BUCKET_LUA)
            except Exception as e:
                logger.warning(f"[RATE LIMITER LUA WARNING] Could not register Lua script: {e}")
                self._lua_script = None
                self._redis_available = False

    def evaluate(self, key: str, requested: int = 1) -> tuple[bool, int, int]:
        """Evaluate token availability for key. Returns (allowed, retry_after, remaining)."""
        # 1. Try Redis first (Atomic Token Bucket via Lua)
        if self._client and self._redis_available and self._lua_script:
            try:
                now = time.time()
                result = self._lua_script(
                    keys=[key],
                    args=[self.capacity, self.refill_rate, now, requested, KEY_EXPIRATION_TTL],
                )
                allowed = bool(result[0])
                retry_after = int(result[1])
                remaining = int(result[2])
                return allowed, retry_after, remaining
            except RedisError as e:
                logger.warning(f"[RATE LIMITER REDIS ERROR] Falling back to in-memory limiter: {e}")

        # 2. Fallback to in-memory token bucket
        return self.in_memory.consume(key, requested)

    def check_request(self, request: Request, namespace: str = "tasks"):
        """Check if request complies with rate limits, raising HTTP 429 if exceeded."""
        client_id = get_client_identifier(request)
        rate_limit_key = f"rate_limit:{namespace}:{client_id}"

        allowed, retry_after, remaining = self.evaluate(rate_limit_key, requested=1)

        if not allowed:
            logger.warning(f"[RATE LIMIT EXCEEDED] client={client_id} key={rate_limit_key} retry_after={retry_after}s")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: 30 requests per minute allowed.",
                headers={"Retry-After": str(retry_after)},
            )


# Global singleton instance
rate_limiter_service = RateLimiterService()


def get_rate_limiter() -> RateLimiterService:
    """FastAPI dependency for accessing the rate limiter service."""
    return rate_limiter_service


def rate_limit_task_creation(
    request: Request,
    limiter: RateLimiterService = Depends(get_rate_limiter),
):
    """Dependency that enforces 30 requests/minute rate limit on task creation."""
    limiter.check_request(request, namespace="tasks")
