"""Tests for the PG-backed PersistentStore base + notification reference (WO-4).

Run isolated from the repo conftest (which pulls the full celery/sqlalchemy app
stack). The verification script in the PR exercises this with a real SQLite
async session.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.stores.base import PersistentStore
from app.stores.notifications import Base as NotifBase
from app.stores.notifications import NotificationStore


@asynccontextmanager
async def _sqlite_session_factory() -> AsyncIterator[AsyncSession]:
    """An ephemeral async SQLite session with the notification table created."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(NotifBase.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


def test_write_then_read_across_simulated_workers() -> None:
    async def scenario() -> None:
        async with _sqlite_session_factory() as db_session_factory:
            tenant_id = 'tenant-a'
            item = {'id': str(uuid.uuid4()), 'user_id': 'u1', 'message': 'hello'}

            store_w1 = NotificationStore()
            async with db_session_factory() as session_worker_1:
                await store_w1.append(session_worker_1, tenant_id, item)

            # Simulate a second worker process: fresh session + fresh cache.
            store_w2 = NotificationStore()
            async with db_session_factory() as session_worker_2:
                results = await store_w2.list_for_tenant(session_worker_2, tenant_id)

            assert any(r['id'] == item['id'] for r in results), results

    asyncio.run(scenario())


def test_tenant_isolation() -> None:
    async def scenario() -> None:
        async with _sqlite_session_factory() as db_session_factory:
            store = NotificationStore()
            async with db_session_factory() as session:
                await store.append(
                    session, 'tenant-a', {'id': str(uuid.uuid4()), 'user_id': 'u1', 'message': 'a'}
                )
                await store.append(
                    session, 'tenant-b', {'id': str(uuid.uuid4()), 'user_id': 'u2', 'message': 'b'}
                )

            async with db_session_factory() as session:
                results_a = await store.list_for_tenant(session, 'tenant-a')
            assert all(r['message'] != 'b' for r in results_a), results_a

    asyncio.run(scenario())


def test_read_cache_hit_avoids_db() -> None:
    """After a read, a second read within TTL must not hit the DB again."""

    calls = {'reads': 0}

    class _CountingStore(PersistentStore[dict]):
        async def _write_to_db(self, session, tenant_id, item):  # type: ignore[no-untyped-def]
            pass

        async def _read_from_db(self, session, tenant_id):  # type: ignore[no-untyped-def]
            calls['reads'] += 1
            return [{'x': 1}]

    store = _CountingStore(cache_ttl_seconds=60)

    async def scenario() -> None:
        @asynccontextmanager
        async def empty_session() -> AsyncIterator[None]:
            yield None

        await store.list_for_tenant(empty_session(), 't')  # type: ignore[arg-type]
        await store.list_for_tenant(empty_session(), 't')  # type: ignore[arg-type]

    asyncio.run(scenario())
    assert calls['reads'] == 1, 'second read should have been a cache hit'
