"""Tests for seo_module_registry.py — _merge_unique, _enrich_module, audit."""
from __future__ import annotations

import re
from pathlib import Path

from backend.fastapi.app.seo_module_registry import (
    _enrich_module_for_production,
    _merge_unique,
    _module_readiness_score,
    audit_ahrefs_core_tool_parity,
    audit_seo_module_registry,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _frontend_catalog_ahrefs_pairs() -> set[tuple[str, str]]:
    catalog_path = _REPO_ROOT / "frontend" / "app" / "seo" / "module-catalog.ts"
    text = catalog_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"routePath:\s*'(?P<route>/seo/[^']+)'\s*,\s*moduleKey:\s*'(?P<module>ahrefs-[^']+)'"
    )
    return {(match.group("route"), match.group("module")) for match in pattern.finditer(text)}


def _frontend_route_file_exists(route_path: str) -> bool:
    if not route_path.startswith("/seo/"):
        return False
    slug = route_path.removeprefix("/seo/").strip("/")
    if not slug:
        return False
    return (_REPO_ROOT / "frontend" / "app" / "seo" / slug / "page.tsx").exists()


class TestMergeUnique:
    def test_basic_merge(self):
        result = _merge_unique(["a", "b"], ["b", "c"])
        assert result == ["a", "b", "c"]

    def test_none_primary_uses_fallback(self):
        result = _merge_unique(None, ["x", "y"])
        assert result == ["x", "y"]

    def test_empty_fallback(self):
        result = _merge_unique(["a"], [])
        assert result == ["a"]

    def test_deduplicates(self):
        result = _merge_unique(["a", "a"], ["a", "b"])
        assert result.count("a") == 1

    def test_strips_whitespace(self):
        result = _merge_unique(["  hello  "], ["world"])
        assert "hello" in result

    def test_empty_strings_excluded(self):
        result = _merge_unique(["", "valid"], ["also"])
        assert "" not in result


class TestEnrichModuleForProduction:
    def _base_module(self, **kwargs) -> dict:
        return {
            "key": "test-module",
            "display_name": "Test Module",
            "group": "seo",
            "description": "A test module",
            "route_path": "/test",
            "implemented": True,
            "backend_ready": True,
            "frontend_ready": True,
            "database_ready": True,
            **kwargs,
        }

    def test_adds_default_integrations(self):
        m = self._base_module()
        enriched = _enrich_module_for_production(m)
        assert "postgres" in enriched["integrations"]
        assert "redis" in enriched["integrations"]

    def test_preserves_existing_integrations(self):
        m = self._base_module(integrations=["custom-db"])
        enriched = _enrich_module_for_production(m)
        assert "custom-db" in enriched["integrations"]
        assert "postgres" in enriched["integrations"]

    def test_adds_supported_channels(self):
        m = self._base_module()
        enriched = _enrich_module_for_production(m)
        assert len(enriched["supported_channels"]) > 0

    def test_adds_automation_features(self):
        m = self._base_module()
        enriched = _enrich_module_for_production(m)
        assert len(enriched["automation_features"]) > 0

    def test_adds_analytics_features(self):
        m = self._base_module()
        enriched = _enrich_module_for_production(m)
        assert len(enriched["analytics_features"]) > 0

    def test_adds_enterprise_features(self):
        m = self._base_module()
        enriched = _enrich_module_for_production(m)
        assert len(enriched["enterprise_features"]) > 0

    def test_adds_ai_models(self):
        m = self._base_module()
        enriched = _enrich_module_for_production(m)
        assert len(enriched["ai_models"]) > 0

    def test_adds_delivery_constraints(self):
        m = self._base_module()
        enriched = _enrich_module_for_production(m)
        assert len(enriched["delivery_constraints"]) > 0

    def test_original_not_mutated(self):
        m = self._base_module(integrations=["orig"])
        original_integrations = list(m.get("integrations", []))
        _enrich_module_for_production(m)
        # m["integrations"] should be unchanged
        assert m.get("integrations") == original_integrations


class TestModuleReadinessScore:
    def test_fully_ready_module_scores_high(self):
        m = {
            "implemented": True,
            "backend_ready": True,
            "frontend_ready": True,
            "database_ready": True,
            "integrations": ["db"],
            "supported_channels": ["web"],
            "architecture_layers": ["api"],
            "automation_features": ["scheduling"],
            "analytics_features": ["metrics"],
            "enterprise_features": ["rbac"],
            "ai_models": ["llama"],
            "delivery_constraints": ["approval"],
        }
        score = _module_readiness_score(m)
        assert score == 100.0

    def test_empty_module_scores_zero(self):
        score = _module_readiness_score({})
        assert score == 0.0

    def test_partial_module_scores_between(self):
        m = {"implemented": True, "backend_ready": True}
        score = _module_readiness_score(m)
        assert 0.0 < score < 100.0


class TestAuditSeoModuleRegistry:
    def test_returns_required_keys(self):
        result = audit_seo_module_registry(None)
        assert "total_modules" in result
        assert "duplicate_keys" in result
        assert "duplicate_routes" in result
        assert "missing_required" in result
        assert "missing_advanced" in result
        assert "low_readiness" in result

    def test_empty_input_zero_modules(self):
        # Empty list is falsy, so function defaults to real registry.
        # Instead test with a single non-matching module.
        result = audit_seo_module_registry([{"key": "x", "display_name": "X", "group": "g", "description": "d", "route_path": "/x"}])
        assert result["total_modules"] == 1

    def test_detects_duplicate_keys(self):
        modules = [
            {"key": "mod1", "display_name": "M1", "group": "g", "description": "d", "route_path": "/a"},
            {"key": "mod1", "display_name": "M2", "group": "g", "description": "d", "route_path": "/b"},
        ]
        result = audit_seo_module_registry(modules)
        assert "mod1" in result["duplicate_keys"]

    def test_detects_duplicate_routes(self):
        modules = [
            {"key": "mod1", "display_name": "M1", "group": "g", "description": "d", "route_path": "/same"},
            {"key": "mod2", "display_name": "M2", "group": "g", "description": "d", "route_path": "/same"},
        ]
        result = audit_seo_module_registry(modules)
        assert "/same" in result["duplicate_routes"]

    def test_detects_missing_required_fields(self):
        modules = [{"key": "mod1"}]
        result = audit_seo_module_registry(modules)
        missing_fields = [item["field"] for item in result["missing_required"]]
        assert "display_name" in missing_fields

    def test_runs_against_real_registry(self):
        # Smoke test: registry should be a non-empty list of dicts
        result = audit_seo_module_registry(None)
        assert isinstance(result["total_modules"], int)
        assert result["total_modules"] > 0


class TestAhrefsCoreToolParity:
    def test_ahrefs_parity_rows_present(self):
        result = audit_ahrefs_core_tool_parity()
        assert result["total_tools"] >= 10
        assert isinstance(result["rows"], list)
        assert any(row["tool_key"] == "site-explorer" for row in result["rows"])

    def test_ahrefs_parity_has_vendors_and_routes(self):
        result = audit_ahrefs_core_tool_parity()
        for row in result["rows"]:
            assert row["route_path"].startswith("/seo/")
            assert len(row["vendors"]) > 0

    def test_ahrefs_parity_contract_matches_frontend_catalog_and_routes(self):
        """
        Permanent drift guard:
        every backend Ahrefs parity row must be represented in frontend catalog
        and have a concrete frontend route file.
        """
        result = audit_ahrefs_core_tool_parity()
        catalog_pairs = _frontend_catalog_ahrefs_pairs()
        catalog_routes = {route for route, _ in catalog_pairs}
        catalog_modules = {module for _, module in catalog_pairs}

        assert result["missing_parity_modules"] == []
        assert result["missing_counterparts"] == []

        for row in result["rows"]:
            route_path = str(row["route_path"])
            parity_module_key = str(row["parity_module_key"])
            assert route_path in catalog_routes
            assert parity_module_key in catalog_modules
            assert _frontend_route_file_exists(route_path)
            assert float(row["coverage_pct"]) == 100.0
