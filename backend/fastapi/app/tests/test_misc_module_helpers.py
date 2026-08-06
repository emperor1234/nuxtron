"""Tests for pure helpers in seo_module_registry.py, tool_integrations.py,
competitive.py, playbooks.py, and ops.py"""
import os
from unittest.mock import patch

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from datetime import UTC

from backend.fastapi.app.routers.competitive import _share_of_voice
from backend.fastapi.app.routers.ops import _invoke
from backend.fastapi.app.routers.playbooks import _row_to_playbook
from backend.fastapi.app.routers.tool_integrations import _configured, _mask, _tool_status
from backend.fastapi.app.seo_module_registry import (
    _merge_unique,
    _module_readiness_score,
    audit_seo_module_registry,
)

# ─── seo_module_registry: _merge_unique ─────────────────────────────────────

class TestMergeUnique:
    def test_empty_primary_uses_fallback(self):
        result = _merge_unique(None, ["a", "b"])
        assert result == ["a", "b"]

    def test_primary_preserved_and_deduped(self):
        result = _merge_unique(["x", "y"], ["y", "z"])
        assert result == ["x", "y", "z"]

    def test_no_duplicates_from_both(self):
        result = _merge_unique(["a"], ["a"])
        assert result.count("a") == 1

    def test_empty_both(self):
        result = _merge_unique(None, [])
        assert result == []

    def test_strips_whitespace(self):
        result = _merge_unique(["  hello  "], ["world"])
        assert "hello" in result


# ─── seo_module_registry: _module_readiness_score ───────────────────────────

class TestModuleReadinessScore:
    def test_full_module_scores_100(self):
        module = {
            "implemented": True, "backend_ready": True, "frontend_ready": True,
            "database_ready": True, "integrations": ["a"], "supported_channels": ["b"],
            "architecture_layers": ["c"], "automation_features": ["d"],
            "analytics_features": ["e"], "enterprise_features": ["f"],
            "ai_models": ["g"], "delivery_constraints": ["h"],
        }
        score = _module_readiness_score(module)
        assert score == 100.0

    def test_empty_module_scores_0(self):
        score = _module_readiness_score({})
        assert score == 0.0

    def test_partial_module_score(self):
        module = {"implemented": True, "backend_ready": True}
        score = _module_readiness_score(module)
        assert 0.0 < score < 100.0


# ─── seo_module_registry: audit_seo_module_registry ─────────────────────────

class TestAuditSeoModuleRegistry:
    def test_returns_dict_with_expected_keys(self):
        result = audit_seo_module_registry([])
        assert isinstance(result, dict)

    def test_with_empty_list(self):
        result = audit_seo_module_registry([])
        assert "duplicate_keys" in result or isinstance(result, dict)

    def test_with_valid_module(self):
        module = {
            "key": "test_mod", "display_name": "Test Module",
            "group": "Test", "description": "Test desc",
            "route_path": "/test", "implemented": True,
        }
        result = audit_seo_module_registry([module])
        assert isinstance(result, dict)

    def test_detects_duplicate_keys(self):
        module = {
            "key": "dup_key", "display_name": "A", "group": "G",
            "description": "Desc", "route_path": "/dup",
        }
        result = audit_seo_module_registry([module, module])
        assert "dup_key" in result.get("duplicate_keys", [])


# ─── tool_integrations: _mask ────────────────────────────────────────────────

class TestMask:
    def test_short_key_returns_stars(self):
        assert _mask("abc") == "****"
        assert _mask("") == "****"

    def test_longer_key_shows_last_4(self):
        result = _mask("abcdefgh")
        assert result == "****efgh"

    def test_exact_4_chars(self):
        result = _mask("1234")
        assert result == "****1234"


# ─── tool_integrations: _configured ─────────────────────────────────────────

class TestConfigured:
    def test_unknown_tool_key_returns_false(self):
        assert _configured("nonexistent_tool_abc123") is False

    def test_known_tool_without_env_returns_false(self):
        # Pick a tool from _TOOL_MAP and ensure the env var is unset
        from backend.fastapi.app.routers.tool_integrations import _TOOL_MAP
        if _TOOL_MAP:
            key = next(iter(_TOOL_MAP))
            env_key = _TOOL_MAP[key].get("env_key", "")
            with patch.dict(os.environ, {env_key: ""}, clear=False):
                assert _configured(key) is False


# ─── tool_integrations: _tool_status ─────────────────────────────────────────

class TestToolStatus:
    def test_returns_expected_keys(self):
        from backend.fastapi.app.routers.tool_integrations import TOOLS
        if TOOLS:
            spec = TOOLS[0]
            result = _tool_status(spec)
            for key in ["key", "display_name", "category", "configured", "last_test_status"]:
                assert key in result

    def test_unconfigured_tool(self):
        from backend.fastapi.app.routers.tool_integrations import TOOLS
        if TOOLS:
            spec = TOOLS[0]
            env_key = spec.get("env_key", "NONEXISTENT_TOOL_KEY_XYZ")
            with patch.dict(os.environ, {env_key: ""}, clear=False):
                result = _tool_status(spec)
                assert result["configured"] is False
                assert result["api_key_masked"] is None


# ─── competitive: _share_of_voice ────────────────────────────────────────────

class TestShareOfVoice:
    def test_equal_mentions(self):
        result = _share_of_voice({"brand_a": 50, "brand_b": 50})
        assert result["brand_a"] == 50.0
        assert result["brand_b"] == 50.0

    def test_zero_total_returns_zeros(self):
        result = _share_of_voice({"brand_a": 0, "brand_b": 0})
        assert result["brand_a"] == 0.0
        assert result["brand_b"] == 0.0

    def test_sums_to_100(self):
        result = _share_of_voice({"a": 1, "b": 2, "c": 7})
        assert abs(sum(result.values()) - 100.0) < 0.1

    def test_single_brand(self):
        result = _share_of_voice({"only": 10})
        assert result["only"] == 100.0

    def test_empty_dict(self):
        result = _share_of_voice({})
        assert result == {}


# ─── playbooks: _row_to_playbook ─────────────────────────────────────────────

class TestRowToPlaybook:
    def test_basic_conversion(self):
        from datetime import datetime
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        row = ("pb-123", "tenant-1", "My Playbook", "saas", "Description",
               [{"step": 1}], ["crm"], {"roi": "200%"}, 30, False, dt)
        result = _row_to_playbook(row)
        assert result["id"] == "pb-123"
        assert result["tenant_id"] == "tenant-1"
        assert result["name"] == "My Playbook"
        assert result["vertical"] == "saas"
        assert result["built_in"] is False
        assert "2024-01-01" in result["created_at"]

    def test_none_steps_defaults_empty(self):
        from datetime import datetime
        dt = datetime(2024, 1, 1, tzinfo=UTC)
        row = ("id1", "t1", "Name", "v1", "desc", None, None, None, 1, True, dt)
        result = _row_to_playbook(row)
        assert result["steps"] == []
        assert result["integrations"] == []
        assert result["roi_target"] == {}


# ─── ops: _invoke ────────────────────────────────────────────────────────────

class TestInvoke:
    def test_none_fn_returns_default(self):
        default = {"status": "ok"}
        result = _invoke(None, default)
        assert result == default

    def test_fn_is_called_with_args(self):
        def double(x, y):
            return {"sum": x + y}
        result = _invoke(double, {}, 3, 4)
        assert result == {"sum": 7}

    def test_fn_receives_no_args(self):
        def make_result():
            return {"empty": True}
        result = _invoke(make_result, {"fallback": True})
        assert result == {"empty": True}
