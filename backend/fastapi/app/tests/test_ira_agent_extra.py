"""
Tests for IRAAgentRuntime._is_framework_ready and _resolve_auto_framework.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

from backend.fastapi.app.ira_agent import IRAAgentRuntime


def _make_runtime(**kwargs) -> IRAAgentRuntime:
    defaults = {
        "now_iso_fn": lambda: "2024-01-01T00:00:00Z",
        "retrieve_knowledge": lambda q, n, t: [],
        "upsert_structured_memory": lambda s, k, d: d,
        "get_short_term_messages": lambda tid, n: [],
        "compose_response": lambda ctx, msgs: "response",
        "brain_reason": None,
        "get_auto_framework_preference": None,
    }
    defaults.update(kwargs)
    return IRAAgentRuntime(**defaults)


class TestIsFrameworkReady:
    def test_returns_true_when_available_and_secure(self) -> None:
        rt = _make_runtime()
        status = {"langchain": {"available": True, "secure": True}}
        assert rt._is_framework_ready(status, "langchain") is True

    def test_returns_false_when_not_available(self) -> None:
        rt = _make_runtime()
        status = {"langchain": {"available": False, "secure": True}}
        assert rt._is_framework_ready(status, "langchain") is False

    def test_returns_false_when_not_secure(self) -> None:
        rt = _make_runtime()
        status = {"langchain": {"available": True, "secure": False}}
        assert rt._is_framework_ready(status, "langchain") is False

    def test_returns_false_for_missing_framework(self) -> None:
        rt = _make_runtime()
        assert rt._is_framework_ready({}, "langchain") is False

    def test_returns_false_for_empty_entry(self) -> None:
        rt = _make_runtime()
        status = {"langchain": {}}
        assert rt._is_framework_ready(status, "langchain") is False


class TestResolveAutoFramework:
    def test_uses_tenant_preferred_framework_when_ready(self) -> None:
        rt = _make_runtime(get_auto_framework_preference=lambda tid: "semantic_kernel")
        status = {
            "langchain": {"available": True, "secure": True},
            "semantic_kernel": {"available": True, "secure": True},
        }
        fw, reason = rt._resolve_auto_framework(status=status, tenant_id="t1")
        assert fw == "semantic_kernel"
        assert "tenant policy" in reason

    def test_falls_back_to_langchain_when_preferred_not_ready(self) -> None:
        rt = _make_runtime(get_auto_framework_preference=lambda tid: "semantic_kernel")
        status = {
            "langchain": {"available": True, "secure": True},
            "semantic_kernel": {"available": False, "secure": True},
        }
        fw, _ = rt._resolve_auto_framework(status=status, tenant_id="t1")
        assert fw == "langchain"

    def test_falls_back_to_semantic_kernel(self) -> None:
        rt = _make_runtime()
        status = {
            "langchain": {"available": False, "secure": True},
            "semantic_kernel": {"available": True, "secure": True},
        }
        fw, _ = rt._resolve_auto_framework(status=status, tenant_id="t1")
        assert fw == "semantic_kernel"

    def test_falls_back_to_native_secure_loop(self) -> None:
        rt = _make_runtime()
        status = {
            "langchain": {"available": False, "secure": True},
            "semantic_kernel": {"available": False, "secure": True},
        }
        fw, reason = rt._resolve_auto_framework(status=status, tenant_id="t1")
        assert fw == "native_secure_loop"
        assert "fallback" in reason

    def test_ignores_invalid_preference(self) -> None:
        rt = _make_runtime(get_auto_framework_preference=lambda tid: "invalid-framework")
        status = {"langchain": {"available": True, "secure": True}}
        fw, _ = rt._resolve_auto_framework(status=status, tenant_id="t1")
        assert fw == "langchain"  # ignores invalid, falls back to langchain

    def test_no_preference_function(self) -> None:
        rt = _make_runtime(get_auto_framework_preference=None)
        status = {"langchain": {"available": True, "secure": True}}
        fw, _ = rt._resolve_auto_framework(status=status, tenant_id="t1")
        assert fw == "langchain"
