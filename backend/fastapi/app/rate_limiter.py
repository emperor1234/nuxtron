"""Rate limiting utilities with Redis backend and in-process fallback."""

import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .domains.identity.security_redis import fixed_window_increment


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


# In-process fallback state
_rate_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = {}


@dataclass(frozen=True)
class RateLimitMetrics:
    """Immutable point-in-time view of in-process limiter activity."""

    active_keys: int
    sample_count: int
    bucket_sizes: Mapping[str, int]


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


def reset_rate_limits_for_tests(*, include_redis: bool = False) -> None:
    """Test helper to isolate rate limiter state between test cases.

    Local state is always cleared. Redis cleanup is opt-in for explicit
    integration tests so the default per-test fixture never performs SCAN.
    """
    with _rate_lock:
        _rate_buckets.clear()
    if not include_redis:
        return
    try:
        from .domains.identity.security_redis import get_sync_redis

        client: Any = get_sync_redis()
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


def rate_limit_metrics_snapshot() -> RateLimitMetrics:
    """Return metrics without exposing mutable limiter internals."""
    with _rate_lock:
        sizes = {key: len(samples) for key, samples in _rate_buckets.items()}
    return RateLimitMetrics(
        active_keys=len(sizes),
        sample_count=sum(sizes.values()),
        bucket_sizes=MappingProxyType(sizes),
    )


def clear_rate_buckets() -> None:
    """Clear rate buckets during shutdown."""
    with _rate_lock:
        _rate_buckets.clear()
