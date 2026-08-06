"""Tests for pure helper functions in ai_brain.py and event_bus.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.ai_brain import _as_dict, _as_list

# ─── ai_brain: _as_dict ──────────────────────────────────────────────────────

class TestAsDict:
    def test_dict_passthrough(self):
        d = {"key": "value"}
        assert _as_dict(d) == d

    def test_non_dict_returns_empty(self):
        assert _as_dict("string") == {}
        assert _as_dict(42) == {}
        assert _as_dict([1, 2, 3]) == {}
        assert _as_dict(None) == {}

    def test_nested_dict(self):
        d = {"a": {"b": 1}}
        assert _as_dict(d) == d


# ─── ai_brain: _as_list ──────────────────────────────────────────────────────

class TestAsList:
    def test_list_passthrough(self):
        lst = [1, 2, 3]
        assert _as_list(lst) == lst

    def test_non_list_returns_empty(self):
        assert _as_list("string") == []
        assert _as_list(42) == []
        assert _as_list(None) == []

    def test_dict_returns_empty(self):
        assert _as_list({"key": "value"}) == []

    def test_empty_list(self):
        assert _as_list([]) == []

    def test_tuple_returns_empty(self):
        # tuples are not lists
        assert _as_list((1, 2, 3)) == []
