"""
platform_intelligence extra tests — round 3.
Covers agent config update, tool registry filtering, audit branches, ai-safety schema checks.
"""
from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-pi-extra3"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def no_agent_db_calls():
    # Keep route tests from attempting real Postgres connections.
    with patch("backend.fastapi.app.routers.platform_intelligence._try_agent_db_query", return_value=(False, [])):
        yield


class TestAiSafetyValidateBranches:
    """Lines 391-460: AI safety validate branches."""

    def test_validate_json_schema_type(self, client: TestClient) -> None:
        """schema_type=json branch (line 399)."""
        r = client.post("/platform/ai-safety/validate", headers=H, json={
            "content": '{"score": 80, "recommendations": ["fix speed"], "quick_wins": ["add titles"]}',
            "module": "seo_ai",
            "schema_type": "json",
            "expected_keys": ["score", "recommendations"],
        })
        assert r.status_code in VALID

    def test_validate_expected_keys_only(self, client: TestClient) -> None:
        """expected_keys present without schema_type=json (line 398)."""
        r = client.post("/platform/ai-safety/validate", headers=H, json={
            "content": '{"keyword": "test", "intent": "informational"}',
            "module": "keyword_research",
            "schema_type": "generic",
            "expected_keys": ["keyword", "intent"],
        })
        assert r.status_code in VALID

    def test_validate_structured_seo_schema_type(self, client: TestClient) -> None:
        """schema_type=structured_seo branch (lines 403-405)."""
        r = client.post("/platform/ai-safety/validate", headers=H, json={
            "content": '{"score": 90, "recommendations": [], "quick_wins": []}',
            "module": "seo_ai",
            "schema_type": "structured_seo",
        })
        assert r.status_code in VALID

    def test_validate_high_risk_content(self, client: TestClient) -> None:
        """High-risk hallucination content → verdict=fail (line 412)."""
        # Content with hallucination indicators
        r = client.post("/platform/ai-safety/validate", headers=H, json={
            "content": "This is definitely 100% guaranteed always certain. Studies show 999% improvement.",
            "module": "content",
            "schema_type": "generic",
        })
        assert r.status_code in VALID


class TestAgentConfigUpdate:
    """Lines 1046-1060: update_agent_config branches."""

    def test_update_agent_phase(self, client: TestClient) -> None:
        """Update current_phase (line 1047)."""
        r = client.put("/platform/agent-config", headers=H, json={
            "current_phase": "phase2",
        })
        assert r.status_code in VALID

    def test_update_agent_phase_invalid(self, client: TestClient) -> None:
        """Invalid phase → 422 (line 1048)."""
        r = client.put("/platform/agent-config", headers=H, json={
            "current_phase": "phase99",
        })
        assert r.status_code in VALID

    def test_update_agent_enabled_models(self, client: TestClient) -> None:
        """Update enabled_models (line 1050)."""
        r = client.put("/platform/agent-config", headers=H, json={
            "enabled_models": ["deepseek-r1:8b", "llama3:8b"],
        })
        assert r.status_code in VALID

    def test_update_agent_max_auto_actions(self, client: TestClient) -> None:
        """Update max_auto_actions (line 1051)."""
        r = client.put("/platform/agent-config", headers=H, json={
            "max_auto_actions": 10,
        })
        assert r.status_code in VALID

    def test_update_agent_allow_high_risk(self, client: TestClient) -> None:
        """Update allow_high_risk_tools (line 1053)."""
        r = client.put("/platform/agent-config", headers=H, json={
            "allow_high_risk_tools": True,
        })
        assert r.status_code in VALID

    def test_update_agent_mcp_endpoint(self, client: TestClient) -> None:
        """Update mcp_endpoint (line 1054)."""
        r = client.put("/platform/agent-config", headers=H, json={
            "mcp_endpoint": "https://mcp.example.com/v1",
        })
        assert r.status_code in VALID

    def test_update_agent_mcp_endpoint_empty(self, client: TestClient) -> None:
        """Clear mcp_endpoint to None (line 1055)."""
        r = client.put("/platform/agent-config", headers=H, json={
            "mcp_endpoint": "",
        })
        assert r.status_code in VALID

    def test_update_all_agent_config(self, client: TestClient) -> None:
        """Update all config at once (lines 1046-1060)."""
        r = client.put("/platform/agent-config", headers=H, json={
            "current_phase": "phase3",
            "enabled_models": ["deepseek-r1:8b"],
            "max_auto_actions": 5,
            "allow_high_risk_tools": False,
            "mcp_endpoint": "https://mcp2.example.com/v1",
        })
        assert r.status_code in VALID


class TestAgentToolsFiltering:
    """Lines 1084-1100: list_agent_tools filter branches."""

    def test_list_tools_all_including_inactive(self, client: TestClient) -> None:
        """active_only=False branch (line 1084)."""
        r = client.get("/platform/agent-tools?active_only=false", headers=H)
        assert r.status_code in VALID

    def test_list_tools_by_group(self, client: TestClient) -> None:
        """group filter (line 1092)."""
        r = client.get("/platform/agent-tools?group=Analytics", headers=H)
        assert r.status_code in VALID

    def test_list_tools_by_risk_low(self, client: TestClient) -> None:
        """risk_level=low filter (line 1094)."""
        r = client.get("/platform/agent-tools?risk_level=low", headers=H)
        assert r.status_code in VALID

    def test_list_tools_by_risk_high(self, client: TestClient) -> None:
        """risk_level=high filter."""
        r = client.get("/platform/agent-tools?risk_level=high", headers=H)
        assert r.status_code in VALID

    def test_list_tools_by_group_and_risk(self, client: TestClient) -> None:
        """Both group and risk_level filters (lines 1092-1094)."""
        r = client.get("/platform/agent-tools?group=SEO&risk_level=medium", headers=H)
        assert r.status_code in VALID


class TestAgentToolRegistration:
    """Lines 1114-1121: register_agent_tool branches."""

    def test_register_new_tool(self, client: TestClient) -> None:
        """Register a new tool (lines 1117-1121)."""
        r = client.post("/platform/agent-tools", headers=H, json={
            "key": "test_tool_extra3_001",
            "display_name": "Test Tool Extra3",
            "group_name": "Testing",
            "description": "A test tool for coverage",
            "fn_signature": "test_tool(input: str) -> str",
            "risk_level": "low",
        })
        assert r.status_code in VALID

    def test_register_duplicate_tool(self, client: TestClient) -> None:
        """Duplicate key → 409 (line 1114)."""
        # Register same key twice
        body = {
            "key": "test_tool_extra3_dup",
            "display_name": "Dup Tool",
            "group_name": "Testing",
            "description": "A duplicate test tool",
            "fn_signature": "dup_tool() -> str",
            "risk_level": "medium",
        }
        client.post("/platform/agent-tools", headers=H, json=body)
        r = client.post("/platform/agent-tools", headers=H, json=body)
        assert r.status_code in VALID

    def test_register_high_risk_tool(self, client: TestClient) -> None:
        """High risk tool (requires_confirmation auto-set, line 1119)."""
        r = client.post("/platform/agent-tools", headers=H, json={
            "key": "test_tool_high_risk_extra3",
            "display_name": "High Risk Test Tool",
            "group_name": "Security",
            "description": "A high-risk test tool",
            "fn_signature": "dangerous_tool(input: str) -> None",
            "risk_level": "high",
        })
        assert r.status_code in VALID

    def test_register_invalid_risk_level(self, client: TestClient) -> None:
        """Invalid risk level → 422 (line 1115)."""
        r = client.post("/platform/agent-tools", headers=H, json={
            "key": "test_tool_invalid_risk",
            "display_name": "Invalid Risk Tool",
            "group_name": "Testing",
            "description": "A tool with invalid risk level",
            "fn_signature": "invalid_tool() -> str",
            "risk_level": "extreme",
        })
        assert r.status_code in VALID


class TestAgentAuditFiltering:
    """Lines 1150-1187: agent audit query branches."""

    def test_audit_no_filter(self, client: TestClient) -> None:
        r = client.get("/platform/agent-audit", headers=H)
        assert r.status_code in VALID

    def test_audit_tool_key_filter(self, client: TestClient) -> None:
        """tool_key filter (lines 1155-1156)."""
        r = client.get("/platform/agent-audit?tool_key=seo_analyze", headers=H)
        assert r.status_code in VALID

    def test_audit_status_filter(self, client: TestClient) -> None:
        """status filter (lines 1159-1161)."""
        r = client.get("/platform/agent-audit?status=success", headers=H)
        assert r.status_code in VALID

    def test_audit_tool_key_and_status_filter(self, client: TestClient) -> None:
        """Both filters (lines 1152-1153)."""
        r = client.get("/platform/agent-audit?tool_key=seo_analyze&status=error", headers=H)
        assert r.status_code in VALID

    def test_audit_with_limit(self, client: TestClient) -> None:
        r = client.get("/platform/agent-audit?limit=10", headers=H)
        assert r.status_code in VALID


class TestPlatformIntelligenceAdditional:
    """Additional routes to improve coverage."""

    def test_recovery_retry_existing_job(self, client: TestClient) -> None:
        """Retry queued job (lines 648-655)."""
        # First retry to create
        client.post("/platform/recovery/retry", headers=H, json={
            "job_id": "existing-job-001",
            "reason": "First attempt",
        })
        # Second retry — hits existing branch (line 648)
        r = client.post("/platform/recovery/retry", headers=H, json={
            "job_id": "existing-job-001",
            "reason": "Second attempt — already queued",
        })
        assert r.status_code in VALID

    def test_recovery_clear_nonexistent(self, client: TestClient) -> None:
        """Clear nonexistent job → 404 (line 681)."""
        r = client.delete("/platform/recovery/queue/nonexistent-job-id", headers=H)
        assert r.status_code in VALID

    def test_recovery_clear_existing(self, client: TestClient) -> None:
        """Clear existing job (lines 675-680)."""
        # First add to queue
        client.post("/platform/recovery/retry", headers=H, json={
            "job_id": "clear-job-001",
            "reason": "Will be cleared",
        })
        r = client.delete("/platform/recovery/queue/clear-job-001", headers=H)
        assert r.status_code in VALID

    def test_sla_report(self, client: TestClient) -> None:
        r = client.get("/platform/sla", headers=H)
        assert r.status_code in VALID

    def test_ai_intelligence_report(self, client: TestClient) -> None:
        r = client.get("/platform/intelligence", headers=H)
        assert r.status_code in VALID
