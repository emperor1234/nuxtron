"""Tests for memory_stores.get_all_stores and event_bus.Event methods."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.event_bus import Event, EventSeverity, EventType
from backend.fastapi.app.memory_stores import get_all_stores


class TestGetAllStores:
    def test_returns_dict(self):
        stores = get_all_stores()
        assert isinstance(stores, dict)

    def test_contains_expected_keys(self):
        stores = get_all_stores()
        assert "suitecrm" in stores
        assert "posthog" in stores
        assert "growth_suite" in stores

    def test_values_are_lists(self):
        stores = get_all_stores()
        for key, value in stores.items():
            assert isinstance(value, list), f"{key} should be a list"


class TestEventToJson:
    def test_to_json_returns_string(self):
        event = Event(
            type=EventType.PAGES_ANALYZED,
            site_id="test-site",
            source_module_id="seo",
        )
        json_str = event.to_json()
        assert isinstance(json_str, str)
        assert "test-site" in json_str

    def test_to_json_contains_type(self):
        event = Event(type=EventType.CONTENT_GENERATED)
        json_str = event.to_json()
        assert "content_generated" in json_str

    def test_from_json_roundtrip(self):
        original = Event(
            type=EventType.METRICS_COMPUTED,
            site_id="roundtrip-site",
            source_module_id="analytics",
            severity=EventSeverity.WARNING,
        )
        json_str = original.to_json()
        restored = Event.from_json(json_str)
        assert restored.type == original.type
        assert restored.site_id == original.site_id
        assert restored.severity == original.severity

    def test_from_json_restores_event_type(self):
        event = Event(type=EventType.ERROR_OCCURRED)
        restored = Event.from_json(event.to_json())
        assert restored.type == EventType.ERROR_OCCURRED

    def test_from_json_restores_severity(self):
        for severity in [EventSeverity.INFO, EventSeverity.WARNING, EventSeverity.ERROR]:
            event = Event(severity=severity)
            restored = Event.from_json(event.to_json())
            assert restored.severity == severity
