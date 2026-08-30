"""Rate limiting utilities with Redis backend and in-process fallback."""

import os
import threading
import time

from .security_redis import fixed_window_increment


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


# In-process fallback state
_rate_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = {}


def enforce_rate_limit_in_process(key: str, limit: int, window_seconds: int) -> None:
    """Per-process fallback limiter, used only when Redis is unavailable.
    
    This is the ORIGINAL implementation. Kept as a floor so a Redis outage
    degrades rate limiting back to "per-process" (the pre-existing behavior)
    rather than disabling it outright.
    """
    now = time.time()
    cutoff = now - window_seconds
    with _rate_lock:
        bucket = [ts for ts in _rate_buckets.get(key, []) if ts >= cutoff]
        if len(bucket) >= limit:
            raise RateLimitExceededError('Rate limit exceeded. Please retry later.')
        bucket.append(now)
        _rate_buckets[key] = bucket


def enforce_rate_limit(key: str, limit: int, window_seconds: int) -> None:
    """Shared-across-workers/replicas rate limiter, backed by Redis.
    
    Previously this was a per-process dict + lock: under N uvicorn/gunicorn
    workers or N horizontally-scaled replicas, the effective limit was
    limit * N and it reset on every deploy. Redis makes the limit real
    across the whole deployment. Falls back to the in-process limiter (not to
    "allow everything") if Redis is unreachable, so an infra outage degrades
    rate limiting rather than disabling it.
    """
    allowed, count = fixed_window_increment(f'nuxtron:ratelimit:{key}', limit=limit, window_seconds=window_seconds)
    if count == 0:
        # fixed_window_increment returns (True, 0) when Redis itself is down
        # (fail-open by its own contract) — fall back to the in-process
        # limiter instead of silently allowing unlimited requests.
        enforce_rate_limit_in_process(key, limit, window_seconds)
        return
    if not allowed:
        raise RateLimitExceededError('Rate limit exceeded. Please retry later.')


def reset_rate_limits_for_tests() -> None:
    """Test helper to isolate rate limiter state between test cases.
    
    Clears both the in-process fallback bucket and any Redis-backed counters
    (best-effort — a missing/unreachable Redis in test environments is
    expected and not an error here).
    """
    with _rate_lock:
        _rate_buckets.clear()
    try:
        from .security_redis import get_sync_redis

        client = get_sync_redis()
        if client is not None:
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match='nuxtron:ratelimit:*', count=500)
                if keys:
                    client.delete(*keys)
                if cursor == 0:
                    break
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug('Redis cleanup failed during test reset: %s', exc)


def get_rate_buckets() -> dict[str, list[float]]:
    """Get the current rate buckets for metrics."""
    return _rate_buckets


def get_rate_lock() -> threading.Lock:
    """Get the rate lock for metrics collection."""
    return _rate_lock


def clear_rate_buckets() -> None:
    """Clear rate buckets during shutdown."""
    with _rate_lock:
        _rate_buckets.clear()
