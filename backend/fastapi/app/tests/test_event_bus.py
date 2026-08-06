"""Tests for event_bus.py — Event, EventBus, subscribe/dispatch/unsubscribe."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from backend.fastapi.app.event_bus import (
    Event,
    EventBus,
    EventSeverity,
    EventType,
    get_event_bus,
)

# ── Event dataclass ──────────────────────────────────────────────────────────

class TestEvent:
    def test_defaults_populated(self):
        e = Event()
        assert e.id  # uuid auto-set
        assert e.type == EventType.PAGES_ANALYZED
        assert e.severity == EventSeverity.INFO

    def test_to_json_roundtrip(self):
        e = Event(
            type=EventType.ENTITIES_EXTRACTED,
            site_id="mysite",
            source_module_id="mod1",
            source_module_type="seo-ai",
            payload={"count": 5},
        )
        json_str = e.to_json()
        e2 = Event.from_json(json_str)
        assert e2.type == EventType.ENTITIES_EXTRACTED
        assert e2.site_id == "mysite"
        assert e2.payload == {"count": 5}

    def test_from_json_restores_severity(self):
        e = Event(severity=EventSeverity.ERROR)
        e2 = Event.from_json(e.to_json())
        assert e2.severity == EventSeverity.ERROR

    def test_event_type_enum_values(self):
        assert EventType.PAGES_ANALYZED == "pages_analyzed"
        assert EventType.ANOMALY_DETECTED == "anomaly_detected"

    def test_event_severity_values(self):
        assert EventSeverity.INFO == "info"
        assert EventSeverity.WARNING == "warning"
        assert EventSeverity.ERROR == "error"


# ── EventBus.subscribe ───────────────────────────────────────────────────────

class TestEventBusSubscribe:
    def test_subscribe_stores_handler(self):
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(EventType.PAGES_ANALYZED, handler)
        assert handler in bus.subscribers["pages_analyzed"]

    def test_subscribe_with_site_id(self):
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(EventType.PAGES_ANALYZED, handler, site_id="mysite")
        assert handler in bus.subscribers["mysite:pages_analyzed"]

    def test_subscribe_string_event_type(self):
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe("pages_analyzed", handler)
        assert handler in bus.subscribers["pages_analyzed"]

    def test_subscribe_multiple_handlers(self):
        bus = EventBus()
        h1, h2 = MagicMock(), MagicMock()
        bus.subscribe(EventType.PAGES_ANALYZED, h1)
        bus.subscribe(EventType.PAGES_ANALYZED, h2)
        assert len(bus.subscribers["pages_analyzed"]) == 2


# ── EventBus.unsubscribe ─────────────────────────────────────────────────────

class TestEventBusUnsubscribe:
    def test_unsubscribe_specific_handler(self):
        bus = EventBus()
        h1, h2 = MagicMock(), MagicMock()
        bus.subscribe(EventType.PAGES_ANALYZED, h1)
        bus.subscribe(EventType.PAGES_ANALYZED, h2)
        asyncio.run(bus.unsubscribe(EventType.PAGES_ANALYZED, h1))
        assert h1 not in bus.subscribers.get("pages_analyzed", [])
        assert h2 in bus.subscribers["pages_analyzed"]

    def test_unsubscribe_all_handlers(self):
        bus = EventBus()
        bus.subscribe(EventType.PAGES_ANALYZED, MagicMock())
        asyncio.run(bus.unsubscribe(EventType.PAGES_ANALYZED))
        assert "pages_analyzed" not in bus.subscribers

    def test_unsubscribe_nonexistent_key(self):
        bus = EventBus()
        # Should not raise
        asyncio.run(bus.unsubscribe(EventType.PAGES_ANALYZED, MagicMock()))


# ── EventBus._dispatch_event ─────────────────────────────────────────────────

class TestEventBusDispatch:
    def test_dispatch_calls_global_handler(self):
        bus = EventBus()
        results = []

        async def handler(event: Event):
            results.append(event.type)

        bus.subscribe(EventType.PAGES_ANALYZED, handler)

        event = Event(type=EventType.PAGES_ANALYZED, site_id="s1",
                      source_module_id="m1", source_module_type="seo")
        asyncio.run(bus._dispatch_event(event))
        assert EventType.PAGES_ANALYZED in results

    def test_dispatch_calls_site_specific_handler(self):
        bus = EventBus()
        results = []

        async def handler(event: Event):
            results.append(event.site_id)

        bus.subscribe(EventType.PAGES_ANALYZED, handler, site_id="mysite")

        event = Event(type=EventType.PAGES_ANALYZED, site_id="mysite",
                      source_module_id="m1", source_module_type="seo")
        asyncio.run(bus._dispatch_event(event))
        assert "mysite" in results

    def test_dispatch_no_matching_handler(self):
        bus = EventBus()
        # Should not raise if no handlers
        event = Event(type=EventType.ENTITIES_EXTRACTED, site_id="s1",
                      source_module_id="m1", source_module_type="seo")
        asyncio.run(bus._dispatch_event(event))  # should complete without error

    def test_dispatch_sync_handler(self):
        bus = EventBus()
        results = []

        def sync_handler(event: Event):
            results.append("called")

        bus.subscribe(EventType.PAGES_ANALYZED, sync_handler)

        event = Event(type=EventType.PAGES_ANALYZED, site_id="s",
                      source_module_id="m", source_module_type="t")
        asyncio.run(bus._dispatch_event(event))
        assert "called" in results

    def test_handler_exception_does_not_propagate(self):
        bus = EventBus()

        async def bad_handler(event: Event):
            raise ValueError("oops")

        bus.subscribe(EventType.PAGES_ANALYZED, bad_handler)

        event = Event(type=EventType.PAGES_ANALYZED, site_id="s",
                      source_module_id="m", source_module_type="t")
        # Should not raise despite handler error (gather return_exceptions=True)
        asyncio.run(bus._dispatch_event(event))


# ── EventBus.close ───────────────────────────────────────────────────────────

class TestEventBusClose:
    def test_close_without_connect(self):
        bus = EventBus()
        # close with no redis_client — should not raise
        asyncio.run(bus.close())
        assert bus.running is False

    def test_close_with_mock_client(self):
        bus = EventBus()
        mock_client = AsyncMock()
        mock_pubsub = AsyncMock()
        bus.redis_client = mock_client
        bus.pubsub = mock_pubsub
        bus.running = True
        asyncio.run(bus.close())
        mock_client.close.assert_awaited_once()
        mock_pubsub.close.assert_awaited_once()
        assert bus.running is False


# ── get_event_bus ─────────────────────────────────────────────────────────────

class TestGetEventBus:
    def test_returns_event_bus_instance(self):
        import backend.fastapi.app.event_bus as eb_mod
        eb_mod._event_bus = None  # reset singleton
        bus = get_event_bus()
        assert isinstance(bus, EventBus)

    def test_returns_same_instance(self):
        import backend.fastapi.app.event_bus as eb_mod
        eb_mod._event_bus = None
        b1 = get_event_bus()
        b2 = get_event_bus()
        assert b1 is b2

    def test_cleanup(self):
        import backend.fastapi.app.event_bus as eb_mod
        eb_mod._event_bus = None  # clean up after test


# ── wait_for_event (timeout path) ────────────────────────────────────────────

class TestWaitForEvent:
    def test_wait_for_event_timeout_returns_none(self):
        bus = EventBus()
        result = asyncio.run(bus.wait_for_event(
            EventType.PAGES_ANALYZED, "some-site", timeout_seconds=0.01
        ))
        assert result is None
