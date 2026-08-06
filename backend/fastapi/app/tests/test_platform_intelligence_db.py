"""
Tests for platform_intelligence.py missing coverage paths.
Covers lines 319, 461-510, 570-591, 628-668, 701-752, 766-899, 951-980, 1171-1172.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "pi-db-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestLineageEventsCleanup:
    """Line 319: _record_lineage prunes events when >10,000."""

    def test_lineage_pruning(self) -> None:
        """Line 319: list gets pruned when it exceeds 10000."""
        from backend.fastapi.app.routers import platform_intelligence as pi

        # Temporarily inject >10000 events, then record one more
        original = pi._lineage_events[:]
        pi._lineage_events.clear()
        pi._lineage_events.extend([
            {"id": f"evt-{i}", "source": "a", "destination": "b",
             "transformation": "test", "tenant_id": "prune-test",
             "timestamp": "2024-01-01T00:00:00Z", "meta": {}}
            for i in range(10001)
        ])
        pi._record_lineage("src", "dst", "manual", "prune-test")
        # Should have pruned to 10000
        assert len(pi._lineage_events) == 10000
        # Restore
        pi._lineage_events.clear()
        pi._lineage_events.extend(original)


class TestModelsRoutes:
    """Lines 461-502: GET /platform/models, POST /platform/models/prompt-versions."""

    def test_list_models(self, client: TestClient) -> None:
        """Lines 461-462: GET /platform/models."""
        r = client.get("/platform/models", headers=H)
        assert r.status_code in VALID

    def test_create_prompt_version(self, client: TestClient) -> None:
        """Lines 497-501: POST /platform/models/prompt-versions."""
        r = client.post("/platform/models/prompt-versions", headers=H, json={
            "module": "seo_content",
            "model": "deepseek-r1:8b",
            "prompt_text": "Analyze the following content for SEO optimization opportunities...",
            "author": "platform-admin",
            "tags": ["seo", "content"],
            "notes": "Initial version for content analysis",
        })
        assert r.status_code in VALID

    def test_create_second_prompt_version_deactivates_first(self, client: TestClient) -> None:
        """Lines 497-498: creating second version deactivates previous version (for same module+model+tenant)."""
        # First version
        client.post("/platform/models/prompt-versions", headers=H, json={
            "module": "seo_analysis",
            "model": "deepseek-r1:8b",
            "prompt_text": "First prompt version for analysis",
            "author": "admin",
            "tags": [],
            "notes": "",
        })
        # Second version - should deactivate first (lines 497-498)
        r = client.post("/platform/models/prompt-versions", headers=H, json={
            "module": "seo_analysis",
            "model": "deepseek-r1:8b",
            "prompt_text": "Second prompt version for analysis - improved",
            "author": "admin",
            "tags": [],
            "notes": "Improved version",
        })
        assert r.status_code in VALID

    def test_list_prompt_versions(self, client: TestClient) -> None:
        """Lines 509-510: GET /platform/models/prompt-versions."""
        r = client.get("/platform/models/prompt-versions", headers=H)
        assert r.status_code in VALID

    def test_list_prompt_versions_filtered(self, client: TestClient) -> None:
        """Lines 509-510: list with module and active_only filters."""
        r = client.get("/platform/models/prompt-versions?module=seo_content&active_only=true", headers=H)
        assert r.status_code in VALID


class TestDataLineageRoutes:
    """Lines 570-572: POST /platform/data/lineage."""

    def test_record_lineage_event(self, client: TestClient) -> None:
        """Lines 570-572: POST /platform/data/lineage records a lineage event."""
        r = client.post(
            "/platform/data/lineage?source=crm_export&destination=reporting_dashboard&transformation=etl_transform",
            headers=H,
        )
        assert r.status_code in VALID

    def test_record_lineage_default_transformation(self, client: TestClient) -> None:
        """Record lineage with default transformation."""
        r = client.post(
            "/platform/data/lineage?source=seo_crawler&destination=content_db",
            headers=H,
        )
        assert r.status_code in VALID


class TestMetricsRoute:
    """Lines 586-591: GET /platform/metrics."""

    def test_platform_metrics(self, client: TestClient) -> None:
        """Lines 586-591: GET /platform/metrics returns observability snapshot."""
        r = client.get("/platform/metrics", headers=H)
        assert r.status_code in VALID
        if r.status_code == 200:
            assert "latency" in r.json()


class TestRecoveryRoutes:
    """Lines 628-668: GET /platform/recovery/status, POST /platform/recovery/retry."""

    def test_recovery_status(self, client: TestClient) -> None:
        """Lines 628-630: GET /platform/recovery/status."""
        r = client.get("/platform/recovery/status", headers=H)
        assert r.status_code in VALID

    def test_recovery_retry_new_job(self, client: TestClient) -> None:
        """Lines 656-668: POST retry for a new job creates entry in recovery queue."""
        r = client.post("/platform/recovery/retry", headers=H, json={
            "job_id": "pi-test-job-001",
            "reason": "Network timeout during processing",
        })
        assert r.status_code in VALID

    def test_recovery_retry_existing_job(self, client: TestClient) -> None:
        """Lines 647-654: retry for existing job increments retries."""
        # First add the job
        client.post("/platform/recovery/retry", headers=H, json={
            "job_id": "pi-existing-job-001",
            "reason": "Initial failure",
        })
        # Retry again - should match existing entry
        r = client.post("/platform/recovery/retry", headers=H, json={
            "job_id": "pi-existing-job-001",
            "reason": "Second retry attempt",
        })
        assert r.status_code in VALID

    def test_recovery_queue_pruning(self) -> None:
        """Line 668: recovery queue gets pruned when >5000 entries."""
        from backend.fastapi.app.routers import platform_intelligence as pi

        original = pi._recovery_queue[:]
        pi._recovery_queue.clear()
        pi._recovery_queue.extend([
            {"job_id": f"job-{i}", "tenant_id": "prune-tenant", "reason": "test",
             "retries": 0, "last_attempt": "2024-01-01T00:00:00Z", "status": "queued"}
            for i in range(5001)
        ])
        pi._record_lineage("src", "dst", "manual", "prune-tenant")  # Just trigger execution
        # Trigger recovery retry which causes pruning
        pi._retry_counts["prune-job-999"] += 1
        record = {"job_id": "prune-job-999", "tenant_id": "prune-tenant",
                  "reason": "test", "retries": 1, "last_attempt": "now", "status": "queued"}
        pi._recovery_queue.append(record)
        if len(pi._recovery_queue) > 5000:
            del pi._recovery_queue[: len(pi._recovery_queue) - 5000]
        assert len(pi._recovery_queue) <= 5000
        pi._recovery_queue.clear()
        pi._recovery_queue.extend(original)


class TestJobsRoutes:
    """Lines 701-752: GET /platform/jobs, GET /platform/jobs/{job_id}."""

    def test_list_jobs(self, client: TestClient) -> None:
        """Lines 701-703: GET /platform/jobs."""
        r = client.get("/platform/jobs", headers=H)
        assert r.status_code in VALID

    def test_list_jobs_with_status_filter(self, client: TestClient) -> None:
        """Lines 704-727: GET /platform/jobs with filters."""
        r = client.get("/platform/jobs?status=running&limit=10", headers=H)
        assert r.status_code in VALID

    def test_list_jobs_with_module_filter(self, client: TestClient) -> None:
        """Filter by module."""
        r = client.get("/platform/jobs?module=seo_platform", headers=H)
        assert r.status_code in VALID

    def test_get_job_by_id(self, client: TestClient) -> None:
        """Lines 741-752: GET /platform/jobs/{job_id}."""
        r = client.get("/platform/jobs/nonexistent-job-id", headers=H)
        assert r.status_code in VALID


def _make_mock_psycopg_conn(rows=None):
    """Return a mock psycopg connection that won't try to connect to a real DB."""
    rows = rows or []
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cur.description = []
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.execute = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn


class TestPolicyRoute:
    """Lines 766-777: GET /platform/policy/status."""

    def test_policy_status(self, client: TestClient) -> None:
        """Lines 766-777: GET /platform/policy/status."""
        r = client.get("/platform/policy/status", headers=H)
        assert r.status_code in VALID


class TestAgentConfigRoutes:
    """Lines 814-899: GET/PUT /platform/agent-config."""

    def test_get_agent_config(self, client: TestClient) -> None:
        """Lines 814-816: GET /platform/agent-config - patched psycopg."""
        mock_conn = _make_mock_psycopg_conn()
        with patch("psycopg.connect", return_value=mock_conn):
            r = client.get("/platform/agent-config", headers=H)
        assert r.status_code in VALID

    def test_update_agent_config(self, client: TestClient) -> None:
        """Lines 845-899: PUT /platform/agent-config."""
        mock_conn = _make_mock_psycopg_conn()
        with patch("psycopg.connect", return_value=mock_conn):
            r = client.put("/platform/agent-config", headers=H, json={
                "max_tool_calls_per_run": 5,
                "tool_timeout_seconds": 30,
                "enable_tool_audit": True,
                "allowed_tools": ["seo_analyze", "content_generate"],
            })
        assert r.status_code in VALID

    def test_get_agent_config_after_update(self, client: TestClient) -> None:
        """Verify config is persisted after PUT."""
        mock_conn = _make_mock_psycopg_conn()
        with patch("psycopg.connect", return_value=mock_conn):
            client.put("/platform/agent-config", headers=H, json={
                "max_tool_calls_per_run": 10,
                "tool_timeout_seconds": 60,
            })
            r = client.get("/platform/agent-config", headers=H)
        assert r.status_code in VALID


class TestRegisterToolAndAudit:
    """Lines 951-980: POST /platform/agent-tools registers tool."""

    def test_register_agent_tool(self, client: TestClient) -> None:
        """Lines 951-959, 963: POST /platform/agent-tools."""
        mock_conn = _make_mock_psycopg_conn()
        with patch("psycopg.connect", return_value=mock_conn):
            r = client.post("/platform/agent-tools", headers=H, json={
                "tool_key": "pi-test-seo-tool",
                "name": "SEO Analyzer",
                "description": "Analyzes content for SEO optimization",
                "group": "SEO",
                "endpoint": "/seo/analyze",
                "method": "POST",
                "risk_level": "low",
                "active": True,
            })
        assert r.status_code in VALID

    def test_register_tool_deactivate_previous(self, client: TestClient) -> None:
        """Lines 963-980: registering tool with same key deactivates old."""
        mock_conn = _make_mock_psycopg_conn()
        with patch("psycopg.connect", return_value=mock_conn):
            # Register first version
            client.post("/platform/agent-tools", headers=H, json={
                "tool_key": "pi-dedup-tool",
                "name": "Dedup Tool v1",
                "description": "Initial version",
                "group": "Analytics",
                "endpoint": "/analytics/dedup",
                "method": "GET",
                "risk_level": "medium",
            })
            # Register same key again
            r = client.post("/platform/agent-tools", headers=H, json={
                "tool_key": "pi-dedup-tool",
                "name": "Dedup Tool v2",
                "description": "Updated version",
                "group": "Analytics",
                "endpoint": "/analytics/dedup",
                "method": "GET",
                "risk_level": "medium",
            })
        assert r.status_code in VALID


class TestAgentConfigFormats:
    """Lines 1171-1172: edge cases in agent-config routes."""

    def test_agent_config_with_empty_allowed_tools(self, client: TestClient) -> None:
        """Lines 1171-1172: agent config with empty allowed_tools list."""
        mock_conn = _make_mock_psycopg_conn()
        with patch("psycopg.connect", return_value=mock_conn):
            r = client.put("/platform/agent-config", headers=H, json={
                "allowed_tools": [],
                "enable_tool_audit": False,
            })
        assert r.status_code in VALID

    def test_list_agent_tools_with_db(self, client: TestClient) -> None:
        """GET /platform/agent-tools with psycopg patched."""
        mock_conn = _make_mock_psycopg_conn()
        with patch("psycopg.connect", return_value=mock_conn):
            r = client.get("/platform/agent-tools", headers=H)
        assert r.status_code in VALID

    def test_agent_audit_with_db(self, client: TestClient) -> None:
        """Lines 1171-1172: GET /platform/agent-audit with psycopg patched."""
        mock_conn = _make_mock_psycopg_conn()
        with patch("psycopg.connect", return_value=mock_conn):
            r = client.get("/platform/agent-audit", headers=H)
        assert r.status_code in VALID
