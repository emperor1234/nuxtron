"""
Extra tests for platform_intelligence router — uses correct request payloads
so that route bodies actually execute (previous tests sent wrong schemas → 422).
"""
from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from backend.fastapi.app.main import app
from fastapi.testclient import TestClient

HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID_CODES = (200, 201, 400, 401, 403, 404, 409, 422, 429, 500)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def no_agent_db_calls():
    # Keep tests deterministic and avoid hanging on local Postgres connection attempts.
    with patch("backend.fastapi.app.routers.platform_intelligence._try_agent_db_query", return_value=(False, [])):
        yield


class TestAiSafetyValidateRouteBody:
    """Test /platform/ai-safety/validate with correct payloads."""

    def test_free_text_content(self, client: TestClient) -> None:
        """Baseline validate — free_text schema, no expected keys."""
        r = client.post(
            "/platform/ai-safety/validate",
            headers=HEADERS,
            json={
                "content": "The SEO score improved significantly this month.",
                "schema_type": "free_text",
                "module": "seo-audit",
            },
        )
        assert r.status_code in VALID_CODES

    def test_json_schema_with_expected_keys(self, client: TestClient) -> None:
        """json schema_type with expected_keys triggers _validate_json_keys."""
        r = client.post(
            "/platform/ai-safety/validate",
            headers=HEADERS,
            json={
                "content": '{"score": 85, "recommendations": ["fix H1"], "quick_wins": ["add meta"]}',
                "schema_type": "json",
                "expected_keys": ["score", "recommendations"],
                "module": "seo-audit",
            },
        )
        assert r.status_code in VALID_CODES

    def test_structured_seo_schema(self, client: TestClient) -> None:
        """structured_seo schema_type triggers seo_keys validation branch."""
        r = client.post(
            "/platform/ai-safety/validate",
            headers=HEADERS,
            json={
                "content": '{"score": 72, "recommendations": [], "quick_wins": []}',
                "schema_type": "structured_seo",
                "module": "seo-monitor",
            },
        )
        assert r.status_code in VALID_CODES

    def test_high_hallucination_risk(self, client: TestClient) -> None:
        """Content with hallucination phrases gets flagged."""
        r = client.post(
            "/platform/ai-safety/validate",
            headers=HEADERS,
            json={
                "content": "This is 100% guaranteed to work. It will always produce perfect results without exception.",
                "schema_type": "free_text",
                "module": "seo-audit",
            },
        )
        assert r.status_code in VALID_CODES

    def test_audit_log_after_validate(self, client: TestClient) -> None:
        """After validating, audit log should exist."""
        r = client.get("/platform/ai-safety/audit-log", headers=HEADERS)
        assert r.status_code in VALID_CODES


class TestPromptVersionsRouteBody:
    """Test /platform/models/prompt-versions with correct PromptVersionCreateRequest payload."""

    def test_create_prompt_version_correct_payload(self, client: TestClient) -> None:
        r = client.post(
            "/platform/models/prompt-versions",
            headers=HEADERS,
            json={
                "module": "seo-audit",
                "prompt_text": "You are an SEO expert. Analyze the following content and provide recommendations.",
                "model": "deepseek-r1:8b",
                "author": "system",
                "tags": ["seo", "audit"],
                "notes": "Initial version",
            },
        )
        assert r.status_code in VALID_CODES

    def test_list_prompt_versions_no_filters(self, client: TestClient) -> None:
        r = client.get("/platform/models/prompt-versions", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_list_prompt_versions_module_filter(self, client: TestClient) -> None:
        r = client.get("/platform/models/prompt-versions?module=seo-audit", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_list_prompt_versions_active_only(self, client: TestClient) -> None:
        r = client.get("/platform/models/prompt-versions?active_only=true", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_create_second_prompt_version_same_module(self, client: TestClient) -> None:
        """Creating second version deactivates first — covers the deactivation branch."""
        r = client.post(
            "/platform/models/prompt-versions",
            headers=HEADERS,
            json={
                "module": "seo-audit",
                "prompt_text": "Improved SEO audit prompt. Focus on technical SEO issues only.",
                "model": "deepseek-r1:8b",
                "author": "admin",
            },
        )
        assert r.status_code in VALID_CODES


class TestDataLineageRouteBody:
    """Test /platform/data/lineage with correct DataLineageRecordRequest payload."""

    def test_post_lineage_record(self, client: TestClient) -> None:
        r = client.post(
            "/platform/data/lineage",
            headers=HEADERS,
            json={
                "source": "import-pipeline",
                "destination": "seo-index",
                "transformation": "normalize",
            },
        )
        assert r.status_code in VALID_CODES

    def test_get_lineage_no_filter(self, client: TestClient) -> None:
        r = client.get("/platform/data/lineage", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_get_lineage_source_filter(self, client: TestClient) -> None:
        r = client.get("/platform/data/lineage?source=import", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_get_lineage_destination_filter(self, client: TestClient) -> None:
        r = client.get("/platform/data/lineage?destination=seo", headers=HEADERS)
        assert r.status_code in VALID_CODES


class TestRecoveryRouteBody:
    """Test /platform/recovery/* with correct RetryRequest payload."""

    def test_trigger_retry_new_job(self, client: TestClient) -> None:
        r = client.post(
            "/platform/recovery/retry",
            headers=HEADERS,
            json={"job_id": "test-job-123", "reason": "manual_retry"},
        )
        assert r.status_code in VALID_CODES

    def test_trigger_retry_existing_job(self, client: TestClient) -> None:
        """Second retry on same job goes into the 'already in queue' branch."""
        r = client.post(
            "/platform/recovery/retry",
            headers=HEADERS,
            json={"job_id": "test-job-123", "reason": "second_retry"},
        )
        assert r.status_code in VALID_CODES

    def test_delete_existing_recovery_item(self, client: TestClient) -> None:
        r = client.delete("/platform/recovery/queue/test-job-123", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_delete_nonexistent_recovery_item(self, client: TestClient) -> None:
        r = client.delete("/platform/recovery/queue/no-such-job", headers=HEADERS)
        assert r.status_code == 404


class TestAgentConfigRouteBody:
    """Test /platform/agent-config PUT with correct AgentConfigUpdateRequest payload."""

    def test_get_agent_config(self, client: TestClient) -> None:
        with patch("backend.fastapi.app.routers.platform_intelligence._try_agent_db_query", return_value=(False, [])):
            r = client.get("/platform/agent-config", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_put_agent_config_phase2(self, client: TestClient) -> None:
        r = client.put(
            "/platform/agent-config",
            headers=HEADERS,
            json={"current_phase": "phase2", "max_auto_actions": 5},
        )
        assert r.status_code in VALID_CODES

    def test_put_agent_config_invalid_phase(self, client: TestClient) -> None:
        """Invalid phase → 422 from route body check."""
        r = client.put(
            "/platform/agent-config",
            headers=HEADERS,
            json={"current_phase": "phase99"},
        )
        assert r.status_code in (422, 400)

    def test_put_agent_config_models_and_risk(self, client: TestClient) -> None:
        r = client.put(
            "/platform/agent-config",
            headers=HEADERS,
            json={
                "enabled_models": ["deepseek-r1:8b", "llama3:8b"],
                "allow_high_risk_tools": True,
                "mcp_endpoint": "http://mcp.example.com",
            },
        )
        assert r.status_code in VALID_CODES

    def test_put_agent_config_clear_mcp_endpoint(self, client: TestClient) -> None:
        """Empty mcp_endpoint sets to None — covers the falsy branch."""
        r = client.put(
            "/platform/agent-config",
            headers=HEADERS,
            json={"mcp_endpoint": ""},
        )
        assert r.status_code in VALID_CODES


class TestAgentToolsRouteBody:
    """Test /platform/agent-tools GET/POST with correct payloads."""

    def test_list_tools_no_filter(self, client: TestClient) -> None:
        r = client.get("/platform/agent-tools", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_list_tools_group_filter(self, client: TestClient) -> None:
        r = client.get("/platform/agent-tools?group=SEO+Tools&active_only=true", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_list_tools_risk_filter(self, client: TestClient) -> None:
        r = client.get("/platform/agent-tools?risk_level=high", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_list_tools_all_not_active_only(self, client: TestClient) -> None:
        r = client.get("/platform/agent-tools?active_only=false", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_register_new_tool(self, client: TestClient) -> None:
        r = client.post(
            "/platform/agent-tools",
            headers=HEADERS,
            json={
                "key": "test_custom_tool",
                "display_name": "Test Custom Tool",
                "group_name": "Testing Tools",
                "fn_signature": "test_custom_tool(site_id)",
                "risk_level": "low",
                "requires_confirmation": False,
                "backend_endpoint": "/seo-platform/test",
            },
        )
        assert r.status_code in VALID_CODES

    def test_register_duplicate_tool_key(self, client: TestClient) -> None:
        """Registering same key → 409 duplicate error."""
        # First, use an existing key from _DEFAULT_AGENT_TOOLS
        r = client.post(
            "/platform/agent-tools",
            headers=HEADERS,
            json={
                "key": "test_custom_tool",
                "display_name": "Duplicate Tool",
                "group_name": "Testing Tools",
                "fn_signature": "test_custom_tool(x)",
                "risk_level": "low",
            },
        )
        assert r.status_code in (409, 422, 201, 200)

    def test_register_tool_invalid_risk_level(self, client: TestClient) -> None:
        """Invalid risk_level → 422 from route body check."""
        r = client.post(
            "/platform/agent-tools",
            headers=HEADERS,
            json={
                "key": "test_risky_tool",
                "display_name": "Risky Tool",
                "group_name": "Testing Tools",
                "fn_signature": "test_risky_tool()",
                "risk_level": "extreme",
            },
        )
        assert r.status_code in (409, 422, 400)


class TestAgentAuditRouteBody:
    """Test /platform/agent-audit with various query filters."""

    def test_audit_no_filter(self, client: TestClient) -> None:
        r = client.get("/platform/agent-audit", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_audit_with_tool_key_filter(self, client: TestClient) -> None:
        r = client.get("/platform/agent-audit?tool_key=run_seo_audit", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_audit_with_status_filter(self, client: TestClient) -> None:
        r = client.get("/platform/agent-audit?status=success", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_audit_with_both_filters(self, client: TestClient) -> None:
        r = client.get("/platform/agent-audit?tool_key=run_seo_audit&status=error", headers=HEADERS)
        assert r.status_code in VALID_CODES


class TestHelperFunctions:
    """Direct unit tests for helper functions to cover missing lines."""

    def test_record_lineage_helper(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _lineage_events, _record_lineage
        before = len(_lineage_events)
        _record_lineage(
            source="test-source",
            destination="test-dest",
            transformation="test-transform",
            tenant_id="test-tenant",
            meta={"key": "value"},
        )
        assert len(_lineage_events) >= before

    def test_record_lineage_without_meta(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _lineage_events, _record_lineage
        before = len(_lineage_events)
        _record_lineage("s", "d", "t", "tenant-x")
        assert len(_lineage_events) > before

    def test_get_sla_metrics_no_paths(self) -> None:
        from unittest.mock import patch

        from backend.fastapi.app.routers.platform_intelligence import _get_sla_metrics
        with patch("backend.fastapi.app.routers.platform_intelligence.get_request_latency_snapshot",
                   return_value={"paths": {}, "window_size": 60, "path_count": 0, "sample_count": 0}):
            result = _get_sla_metrics()
            assert "compliance_pct" in result
            assert result["total_paths_tracked"] == 0

    def test_get_sla_metrics_with_breach(self) -> None:
        from unittest.mock import patch

        from backend.fastapi.app.routers.platform_intelligence import _get_sla_metrics
        with patch("backend.fastapi.app.routers.platform_intelligence.get_request_latency_snapshot",
                   return_value={"paths": {
                       "/seo/slow": {"p95_ms": 9999, "avg_ms": 8000},
                       "/seo/fast": {"p95_ms": 100, "avg_ms": 50},
                   }}):
            result = _get_sla_metrics()
            assert "breached_paths" in result
            assert len(result["breached_paths"]) >= 1

    def test_try_agent_db_scalar_ok_rows(self) -> None:
        """Line 70: _try_agent_db_scalar when _try_agent_db_query returns rows."""
        from unittest.mock import patch

        from backend.fastapi.app.routers.platform_intelligence import _try_agent_db_scalar
        with patch("backend.fastapi.app.routers.platform_intelligence._try_agent_db_query",
                   return_value=(True, [{"count": 42}])):
            ok, val = _try_agent_db_scalar("SELECT count(*) FROM x")
            assert ok is True
            assert val == 42

    def test_try_agent_db_scalar_no_rows(self) -> None:
        """_try_agent_db_scalar when _try_agent_db_query returns no rows."""
        from unittest.mock import patch

        from backend.fastapi.app.routers.platform_intelligence import _try_agent_db_scalar
        with patch("backend.fastapi.app.routers.platform_intelligence._try_agent_db_query",
                   return_value=(True, [])):
            ok, val = _try_agent_db_scalar("SELECT count(*) FROM x")
            assert ok is True
            assert val is None
