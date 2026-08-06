"""
Unit tests for modules/ — ai_internal_linking, entity_first_seo, seo_ai_monitor.
Uses AsyncMock for DB, EventBus, and LLM dependencies.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import asyncio
from unittest.mock import AsyncMock, MagicMock

from backend.fastapi.app.event_bus import Event, EventBus, EventType
from backend.fastapi.app.llm_pool import LLMPool
from backend.fastapi.app.modules.ai_internal_linking import AIInternalLinkingEngine
from backend.fastapi.app.modules.entity_first_seo import EntityFirstSEO
from backend.fastapi.app.modules.seo_ai_monitor import SEOAIMonitor

# ── Shared fixtures / helpers ────────────────────────────────────────────────

def make_event_bus() -> EventBus:
    """Return a real EventBus (no Redis) — subscribe works in memory."""
    bus = EventBus(redis_url="redis://localhost:9999")  # port never connects
    return bus


def make_llm_pool() -> LLMPool:
    pool = LLMPool(site_id="test-site")
    return pool


def make_db() -> AsyncMock:
    conn = AsyncMock()
    # cursor() context manager
    cur = AsyncMock()
    cur.fetchall = AsyncMock(return_value=[])
    cur.fetchone = AsyncMock(return_value=None)
    cur.execute = AsyncMock()
    cur.__aenter__ = AsyncMock(return_value=cur)
    cur.__aexit__ = AsyncMock(return_value=None)
    conn.cursor = MagicMock(return_value=cur)
    conn.commit = AsyncMock()
    return conn


# ── EventBus ─────────────────────────────────────────────────────────────────

class TestEventBus:
    def test_subscribe_registers_handler(self) -> None:
        bus = make_event_bus()
        handler = AsyncMock()
        bus.subscribe(
            event_type=EventType.PAGES_ANALYZED,
            handler=handler,
            site_id="test-site",
        )
        key = "test-site:pages_analyzed"
        assert key in bus.subscribers
        assert handler in bus.subscribers[key]

    def test_subscribe_without_site_id(self) -> None:
        bus = make_event_bus()
        handler = AsyncMock()
        bus.subscribe(event_type=EventType.ENTITIES_EXTRACTED, handler=handler)
        key = "entities_extracted"
        assert key in bus.subscribers

    def test_event_from_json_roundtrip(self) -> None:
        ev = Event(
            id="abc-123",
            type=EventType.PAGES_ANALYZED,
            site_id="site-1",
            source_module_id="mod-1",
            source_module_type="seo-ai",
            payload={"pages": 10},
        )
        serialized = ev.to_json()
        ev2 = Event.from_json(serialized)
        assert ev2.id == "abc-123"
        assert ev2.site_id == "site-1"
        assert ev2.payload == {"pages": 10}

    def test_event_type_is_str_enum(self) -> None:
        for et in EventType:
            assert isinstance(et.value, str)


# ── AIInternalLinkingEngine ──────────────────────────────────────────────────

class TestAIInternalLinkingEngine:
    def make_engine(self) -> AIInternalLinkingEngine:
        return AIInternalLinkingEngine(
            site_id="test-site",
            module_id="mod-link-1",
            db_conn=make_db(),
            event_bus=make_event_bus(),
            llm_pool=make_llm_pool(),
        )

    def test_instantiation(self) -> None:
        eng = self.make_engine()
        assert eng.site_id == "test-site"
        assert eng.module_id == "mod-link-1"

    def test_subscribes_to_entities_extracted(self) -> None:
        bus = make_event_bus()
        AIInternalLinkingEngine(
            site_id="test-site",
            module_id="mod-link-1",
            db_conn=make_db(),
            event_bus=bus,
            llm_pool=make_llm_pool(),
        )
        key = "test-site:entities_extracted"
        assert key in bus.subscribers
        assert len(bus.subscribers[key]) == 1

    def test_on_entities_extracted_skips_wrong_site(self) -> None:
        """Events for other sites should be ignored."""
        eng = self.make_engine()
        event = Event(
            type=EventType.ENTITIES_EXTRACTED,
            site_id="different-site",  # not this engine's site
            payload={"entities_extracted": 5},
        )
        # Should return without doing anything — just verify it doesn't raise
        asyncio.run(eng._on_entities_extracted(event))

    def test_run_handles_empty_db(self) -> None:
        """run() with empty DB should complete without error."""
        eng = self.make_engine()
        result = asyncio.run(
            eng.run(run_id="run-001", trigger_event=None)
        )
        assert isinstance(result, dict)


# ── EntityFirstSEO ────────────────────────────────────────────────────────────

class TestEntityFirstSEO:
    def make_engine(self) -> EntityFirstSEO:
        return EntityFirstSEO(
            site_id="test-site",
            module_id="mod-entity-1",
            db_conn=make_db(),
            event_bus=make_event_bus(),
            llm_pool=make_llm_pool(),
        )

    def test_instantiation(self) -> None:
        eng = self.make_engine()
        assert eng.site_id == "test-site"
        assert eng.module_id == "mod-entity-1"

    def test_subscribes_to_pages_analyzed(self) -> None:
        bus = make_event_bus()
        EntityFirstSEO(
            site_id="test-site",
            module_id="mod-entity-1",
            db_conn=make_db(),
            event_bus=bus,
            llm_pool=make_llm_pool(),
        )
        key = "test-site:pages_analyzed"
        assert key in bus.subscribers
        assert len(bus.subscribers[key]) == 1

    def test_on_pages_analyzed_skips_wrong_site(self) -> None:
        eng = self.make_engine()
        event = Event(
            type=EventType.PAGES_ANALYZED,
            site_id="different-site",
            payload={"pages": 5},
        )
        asyncio.run(eng._on_pages_analyzed(event))

    def test_deduplicate_entities_removes_duplicates(self) -> None:
        eng = self.make_engine()
        entities = [
            {"name": "Python", "type": "concept"},
            {"name": "python", "type": "concept"},  # same, diff case
            {"name": "FastAPI", "type": "product"},
        ]
        deduped = eng._deduplicate_entities(entities)
        names = [e["name"].lower() for e in deduped]
        assert len(set(names)) == len(names)  # no duplicates

    def test_run_handles_empty_db(self) -> None:
        eng = self.make_engine()
        result = asyncio.run(eng.run(run_id="run-001", trigger_event=None))
        assert isinstance(result, dict)


# ── SEOAIMonitor ─────────────────────────────────────────────────────────────

class TestSEOAIMonitor:
    def make_monitor(self) -> SEOAIMonitor:
        return SEOAIMonitor(
            site_id="test-site",
            module_id="mod-seo-1",
            db_conn=make_db(),
            event_bus=make_event_bus(),
            llm_pool=make_llm_pool(),
        )

    def test_instantiation(self) -> None:
        mon = self.make_monitor()
        assert mon.site_id == "test-site"
        assert mon.module_id == "mod-seo-1"

    def test_has_http_client(self) -> None:
        mon = self.make_monitor()
        assert mon.http is not None

    def test_run_with_explicit_empty_pages(self) -> None:
        """run() with an empty pages list should complete quickly."""
        mon = self.make_monitor()
        result = asyncio.run(mon.run(run_id="run-001", pages=[]))
        assert isinstance(result, dict)

    def test_run_handles_empty_db(self) -> None:
        mon = self.make_monitor()
        result = asyncio.run(mon.run(run_id="run-002", pages=None, limit=5))
        assert isinstance(result, dict)

    def test_close_does_not_raise(self) -> None:
        mon = self.make_monitor()
        asyncio.run(mon.close())
