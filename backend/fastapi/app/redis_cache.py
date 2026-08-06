"""
Async Redis cache layer for Nuxtron FastAPI services.
Provides a drop-in decorator for caching GET endpoint responses.
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
from collections.abc import Callable
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger("nuxtron.cache")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", "60"))  # seconds

_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis | None:
    """Return a shared async Redis connection pool, or None if unavailable."""
    global _pool  # noqa: PLW0603
    if _pool is not None:
        return _pool
    try:
        client = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await client.ping()
        _pool = client
        logger.info("Redis cache connected: %s", REDIS_URL)
    except Exception as exc:  # pragma: no cover
        logger.warning("Redis cache unavailable — running without cache: %s", exc)
        _pool = None
    return _pool


async def cache_get(key: str) -> Any | None:
    client = await get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.debug("Cache GET error for %s: %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
    client = await get_redis()
    if client is None:
        return
    try:
        await client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.debug("Cache SET error for %s: %s", key, exc)


def make_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    raw = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"nuxtron:{prefix}:{digest}"


def cached(prefix: str, ttl: int = DEFAULT_TTL) -> Callable:
    """Decorator to cache async function return values in Redis."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Skip caching for non-GET-like calls (args with Request objects)
            key = make_cache_key(prefix, **{k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool))})
            cached_val = await cache_get(key)
            if cached_val is not None:
                return cached_val
            result = await func(*args, **kwargs)
            await cache_set(key, result, ttl)
            return result
        return wrapper
    return decorator
