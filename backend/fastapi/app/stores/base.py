"""
Base class for stores that must be correct across multiple gunicorn/uvicorn
workers (PDR §6.4 / WO-4).

Each store keeps a small per-process cache for latency, but treats PostgreSQL as
the source of truth: every write goes to PG first (so other workers see it on
their next read), and every read that misses cache falls through to PG.

A Postgres blip degrades gracefully: a failed read serves the stale cache if
available (loud in logs/metrics) rather than 500-ing; a failed write rolls back
and raises so the caller can decide (the store never silently drops data).
"""
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger('nuxtron.stores')

T = TypeVar('T')


class PersistentStore(ABC, Generic[T]):
    """
    Subclasses implement the three PG operations; this base adds the cache
    layer and fail-safe logging so a PG outage is loud rather than silently
    returning wrong data.
    """

    def __init__(self, *, cache_ttl_seconds: int = 30) -> None:
        self._cache: dict[str, tuple[float, list[T]]] = {}
        self._cache_ttl_seconds = cache_ttl_seconds

    @abstractmethod
    async def _write_to_db(self, session: AsyncSession, tenant_id: str, item: T) -> None:
        """Persist a single item. Must not commit (the base class commits)."""

    @abstractmethod
    async def _read_from_db(self, session: AsyncSession, tenant_id: str) -> list[T]:
        """Read all items for a tenant, newest-first is conventional."""

    async def append(self, session: AsyncSession, tenant_id: str, item: T) -> None:
        """Write-through: PG first, then invalidate cache for the tenant."""
        try:
            await self._write_to_db(session, tenant_id, item)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                'persistent_store_write_failed',
                extra={'tenant_id': tenant_id, 'store': type(self).__name__},
            )
            raise
        # Invalidate so the next read repopulates from PG.
        self._cache.pop(tenant_id, None)

    async def list_for_tenant(self, session: AsyncSession, tenant_id: str) -> list[T]:
        """Read-through with TTL cache; serves stale cache if PG is unreachable."""
        cached = self._cache.get(tenant_id)
        if cached and (time.monotonic() - cached[0]) < self._cache_ttl_seconds:
            return cached[1]

        try:
            items = await self._read_from_db(session, tenant_id)
        except Exception:
            logger.exception(
                'persistent_store_read_failed_serving_stale_cache',
                extra={'tenant_id': tenant_id, 'store': type(self).__name__},
            )
            if cached:
                return cached[1]
            raise

        self._cache[tenant_id] = (time.monotonic(), items)
        return items

    def invalidate(self, tenant_id: str | None = None) -> None:
        """Drop the cache for a tenant (or the whole cache if None)."""
        if tenant_id is None:
            self._cache.clear()
        else:
            self._cache.pop(tenant_id, None)
