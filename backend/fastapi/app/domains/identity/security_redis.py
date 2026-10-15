"""Synchronous Redis helper for security counters used from sync route handlers.

``app/redis_cache.py`` already provides an async Redis client for response
caching, but several auth handlers in ``routers/auth.py`` are plain sync
functions (registered directly as FastAPI route callables, run in FastAPI's
threadpool) — converting them to ``async def`` would make their existing
blocking ``psycopg``/bcrypt/argon2 calls block the event loop instead, which
is a worse trade. This module gives those sync call sites a Redis-backed
fixed-window counter without that conversion.

Used today for per-account / per-IP login brute-force throttling
(``routers/auth.py``). Shares the same ``REDIS_URL`` as the async cache.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

try:
    import redis as redis_sync
except ModuleNotFoundError:  # Optional dependency in local/test environments.
    redis_sync: Any = None

logger = logging.getLogger("nuxtron.security.redis")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_client: redis_sync.Redis | None = None
_client_init_failed = False
_retry_after_monotonic = 0.0
_RETRY_INTERVAL_SECONDS = 5.0


def get_sync_redis() -> redis_sync.Redis | None:
    """Return a shared sync Redis client, or None if unavailable.

    Only attempts to connect once per process; a failed connection does not
    retry on every call (avoids paying a connection-timeout cost per request
    when Redis is genuinely down).
    """
    global _client, _client_init_failed, _retry_after_monotonic  # noqa: PLW0603
    if redis_sync is None:
        _client_init_failed = True
        _retry_after_monotonic = time.monotonic() + _RETRY_INTERVAL_SECONDS
        logger.warning("Sync Redis client is not installed; shared security counters are unavailable.")
        return None
    if _client is not None:
        return _client
    now = time.monotonic()
    if _client_init_failed and now < _retry_after_monotonic:
        return None
    try:
        client = redis_sync.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        _client = client
        _client_init_failed = False
        _retry_after_monotonic = 0.0
        return _client
    except Exception:
        _client_init_failed = True
        _retry_after_monotonic = time.monotonic() + _RETRY_INTERVAL_SECONDS
        logger.warning("Sync Redis unavailable; shared security counters are unavailable.")
        return None


def security_redis_ready() -> bool:
    """Return whether the shared Redis security-counter store answers a ping."""
    global _client, _client_init_failed, _retry_after_monotonic  # noqa: PLW0603
    client = get_sync_redis()
    if client is None:
        return False
    try:
        client.ping()
        return True
    except Exception:
        _client = None
        _client_init_failed = True
        _retry_after_monotonic = time.monotonic() + _RETRY_INTERVAL_SECONDS
        logger.warning("Sync Redis readiness probe failed; shared security counters are unavailable.")
        return False


def fixed_window_increment(key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Increment a fixed-window counter and report whether it's still within ``limit``.

    Returns ``(allowed, current_count)``. Fails OPEN (``allowed=True``,
    ``current_count=0``) if Redis is unreachable — this is a defense-in-depth
    throttle layered on top of the existing per-tenant rate limiter, not the
    only protection, so an infra outage here must not lock every user out of
    login.
    """
    client = get_sync_redis()
    if client is None:
        return True, 0
    try:
        pipe = client.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, window_seconds, nx=True)
        count, _ = pipe.execute()
        count = int(count)
        return count <= limit, count
    except Exception:
        logger.warning("Redis counter increment failed; using the local limiter fallback.")
        return True, 0


def reset_counter(key: str) -> None:
    client = get_sync_redis()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception:
        logger.warning("Redis counter reset failed for key=%s", key, exc_info=True)
