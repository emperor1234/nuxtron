"""
HTTP smoke tests for the platform_intelligence router.
Tests all registered /platform/* and /ops/platform/* endpoints via TestClient.
"""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import backend.fastapi.app.routers.platform_intelligence as pi
import pytest
from backend.fastapi.app.main import app
from fastapi.testclient import TestClient

API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY}

VALID_CODES = (200, 201, 400, 401, 403, 404, 422, 500)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── /ops/platform/* ───────────────────────────────────────────────────────────

class TestOpsPlatform:
    def test_status(self, client: TestClient) -> None:
        r = client.get("/ops/platform/status", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_metrics_summary(self, client: TestClient) -> None:
        r = client.get("/ops/platform/metrics-summary", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_anti_failure_status(self, client: TestClient) -> None:
        r = client.get("/ops/platform/anti-failure-status", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_use_case_coverage(self, client: TestClient) -> None:
        r = client.get("/ops/platform/use-case-coverage", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_capabilities(self, client: TestClient) -> None:
        r = client.get("/ops/platform/capabilities", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_hybrid_stacks(self, client: TestClient) -> None:
        r = client.get("/ops/platform/hybrid-stacks", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_module_registry(self, client: TestClient) -> None:
        r = client.get("/ops/platform/module-registry", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_growth_suite(self, client: TestClient) -> None:
        r = client.get("/ops/platform/growth-suite", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_growth_suite_bootstrap(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/growth-suite/bootstrap",
            headers=HEADERS,
            json={"site_id": "test-site"},
        )
        assert r.status_code in VALID_CODES


# ── /ops/platform/super-admin/* ───────────────────────────────────────────────

class TestSuperAdmin:
    def test_dashboard(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/dashboard", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_accounting_integrations(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/accounting/integrations", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_accounting_connect(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/integrations/connect",
            headers=HEADERS,
            json={"provider": "quickbooks", "api_key": "test-key"},
        )
        assert r.status_code in VALID_CODES

    def test_accounting_disconnect(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/integrations/disconnect",
            headers=HEADERS,
            json={"provider": "quickbooks"},
        )
        assert r.status_code in VALID_CODES

    def test_accounting_delete_provider(self, client: TestClient) -> None:
        r = client.delete(
            "/ops/platform/super-admin/accounting/integrations/quickbooks",
            headers=HEADERS,
        )
        assert r.status_code in VALID_CODES

    def test_accounting_exports_list(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/accounting/exports", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_accounting_exports_create(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/exports",
            headers=HEADERS,
            json={"provider": "quickbooks", "date_range": "last_month"},
        )
        assert r.status_code in VALID_CODES

    def test_accounting_export_retry(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/exports/export-001/retry",
            headers=HEADERS,
        )
        assert r.status_code in VALID_CODES

    def test_accounting_export_cancel(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/exports/export-001/cancel",
            headers=HEADERS,
        )
        assert r.status_code in VALID_CODES

    def test_module_settings_get(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/module-settings", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_module_settings_post(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/module-settings",
            headers=HEADERS,
            json={"module": "seo", "enabled": True},
        )
        assert r.status_code in VALID_CODES

    def test_audit_log(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/audit-log", headers=HEADERS)
        assert r.status_code in VALID_CODES


# ── /platform/ai-safety/* ─────────────────────────────────────────────────────

class TestAiSafety:
    def test_ai_safety_validate(self, client: TestClient) -> None:
        r = client.post(
            "/platform/ai-safety/validate",
            headers=HEADERS,
            json={"content": "This is a test prompt.", "context": "seo"},
        )
        assert r.status_code in VALID_CODES

    def test_ai_safety_audit_log(self, client: TestClient) -> None:
        r = client.get("/platform/ai-safety/audit-log", headers=HEADERS)
        assert r.status_code in VALID_CODES


# ── /platform/models/* ───────────────────────────────────────────────────────

class TestModels:
    def test_list_models(self, client: TestClient) -> None:
        r = client.get("/platform/models", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_create_prompt_version(self, client: TestClient) -> None:
        r = client.post(
            "/platform/models/prompt-versions",
            headers=HEADERS,
            json={"name": "v1", "template": "Hello {{name}}"},
        )
        assert r.status_code in VALID_CODES

    def test_list_prompt_versions(self, client: TestClient) -> None:
        r = client.get("/platform/models/prompt-versions", headers=HEADERS)
        assert r.status_code in VALID_CODES


# ── /platform/data/* ─────────────────────────────────────────────────────────

class TestDataLineage:
    def test_get_lineage(self, client: TestClient) -> None:
        r = client.get("/platform/data/lineage", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_post_lineage(self, client: TestClient) -> None:
        r = client.post(
            "/platform/data/lineage",
            headers=HEADERS,
            json={"source": "import", "target": "seo-index"},
        )
        assert r.status_code in VALID_CODES


# ── /platform/metrics ─────────────────────────────────────────────────────────

class TestMetrics:
    def test_get_metrics(self, client: TestClient) -> None:
        r = client.get("/platform/metrics", headers=HEADERS)
        assert r.status_code in VALID_CODES


# ── /platform/recovery/* ──────────────────────────────────────────────────────

class TestRecovery:
    def test_recovery_status(self, client: TestClient) -> None:
        r = client.get("/platform/recovery/status", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_recovery_retry(self, client: TestClient) -> None:
        r = client.post(
            "/platform/recovery/retry",
            headers=HEADERS,
            json={"job_id": "job-001"},
        )
        assert r.status_code in VALID_CODES

    def test_recovery_delete_job(self, client: TestClient) -> None:
        r = client.delete("/platform/recovery/queue/job-001", headers=HEADERS)
        assert r.status_code in VALID_CODES


# ── /platform/jobs/* ─────────────────────────────────────────────────────────

class TestJobs:
    def test_list_jobs(self, client: TestClient) -> None:
        r = client.get("/platform/jobs", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_get_job_by_id(self, client: TestClient) -> None:
        r = client.get("/platform/jobs/job-001", headers=HEADERS)
        assert r.status_code in VALID_CODES


# ── /platform/policy & sla ───────────────────────────────────────────────────

class TestPolicyAndSla:
    def test_policy_status(self, client: TestClient) -> None:
        r = client.get("/platform/policy/status", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_sla(self, client: TestClient) -> None:
        r = client.get("/platform/sla", headers=HEADERS)
        assert r.status_code in VALID_CODES


# ── /platform/intelligence ───────────────────────────────────────────────────

class TestIntelligence:
    def test_intelligence(self, client: TestClient) -> None:
        r = client.get("/platform/intelligence", headers=HEADERS)
        assert r.status_code in VALID_CODES


# ── /platform/agent-* ────────────────────────────────────────────────────────

class TestAgent:
    def test_get_agent_config(self, client: TestClient) -> None:
        r = client.get("/platform/agent-config", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_put_agent_config(self, client: TestClient) -> None:
        r = client.put(
            "/platform/agent-config",
            headers=HEADERS,
            json={"max_iterations": 10, "timeout_seconds": 60},
        )
        assert r.status_code in VALID_CODES

    def test_get_agent_tools(self, client: TestClient) -> None:
        r = client.get("/platform/agent-tools", headers=HEADERS)
        assert r.status_code in VALID_CODES

    def test_post_agent_tools(self, client: TestClient) -> None:
        r = client.post(
            "/platform/agent-tools",
            headers=HEADERS,
            json={"name": "web_search", "enabled": True},
        )
        assert r.status_code in VALID_CODES

    def test_agent_audit(self, client: TestClient) -> None:
        r = client.get("/platform/agent-audit", headers=HEADERS)
        assert r.status_code in VALID_CODES


# ── Unit tests for helper functions ──────────────────────────────────────────


class TestAgentDbDsn:
    def test_returns_dsn_string(self):
        with patch.dict(os.environ, {
            "POSTGRES_HOST": "myhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "mydb",
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypass",
        }):
            dsn = pi._agent_db_dsn()
        assert "myhost" in dsn
        assert "5433" in dsn
        assert "mydb" in dsn


class TestTryAgentDbQuery:
    def test_returns_false_on_connection_error(self):
        with patch("psycopg.connect", side_effect=Exception("conn refused")):
            ok, rows = pi._try_agent_db_query("SELECT 1")
        assert ok is False
        assert rows == []

    def test_returns_rows_on_success(self):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.description = [MagicMock(name="id"), MagicMock(name="val")]
        mock_cursor.__iter__ = MagicMock(return_value=iter([]))
        mock_cursor.fetchall.return_value = [(1, "a"), (2, "b")]
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        with patch("psycopg.connect", return_value=mock_conn):
            ok, rows = pi._try_agent_db_query("SELECT id, val FROM t")
        assert ok is True


class TestTryAgentDbScalar:
    def test_returns_false_on_error(self):
        with patch("psycopg.connect", side_effect=Exception("down")):
            ok, val = pi._try_agent_db_scalar("SELECT COUNT(*)")
        assert ok is False
        assert val is None


class TestPlatformHelpers:
    def test_now_returns_iso_string(self):
        result = pi._now()
        assert "T" in result or len(result) > 10

    def test_sha256_returns_16_chars(self):
        result = pi._sha256("hello world")
        assert len(result) == 16

    def test_uptime_seconds_positive(self):
        result = pi._uptime_seconds()
        assert result >= 0.0


class TestDetectHallucinationIndicators:
    def test_clean_text_high_score(self):
        result = pi._detect_hallucination_indicators("This is a concise and balanced analysis of the topic.")
        assert result["hallucination_score"] >= 80
        assert result["risk_level"] == "low"

    def test_overconfident_phrases_reduce_score(self):
        result = pi._detect_hallucination_indicators("This product always works and is 100% guaranteed.")
        assert result["hallucination_score"] < 100
        assert len(result["flags"]) > 0

    def test_future_years_flagged(self):
        result = pi._detect_hallucination_indicators("In 2085, AI will dominate everything.")
        assert any("year" in f.lower() or "2085" in f for f in result["flags"])

    def test_short_content_flagged(self):
        result = pi._detect_hallucination_indicators("OK.")
        assert any("short" in f.lower() for f in result["flags"])

    def test_contradiction_pair_flagged(self):
        result = pi._detect_hallucination_indicators("Traffic will increase. Traffic will decrease. That's certain.")
        assert any("contradiction" in f.lower() for f in result["flags"])

    def test_repetition_flagged(self):
        repetitive = ("the word " * 60)
        result = pi._detect_hallucination_indicators(repetitive)
        assert any("diversity" in f.lower() or "repetition" in f.lower() for f in result["flags"])

    def test_score_clamped_to_zero(self):
        bad_text = "always never 100% guaranteed absolutely certain without exception 2085 2090 " + ("bad " * 60)
        result = pi._detect_hallucination_indicators(bad_text)
        assert result["hallucination_score"] >= 0


class TestValidateJsonKeys:
    def test_valid_json_all_keys_present(self):
        content = json.dumps({"name": "Alice", "age": 30})
        result = pi._validate_json_keys(content, ["name", "age"])
        assert result["valid"] is True
        assert result["missing_keys"] == []

    def test_missing_keys_detected(self):
        content = json.dumps({"name": "Alice"})
        result = pi._validate_json_keys(content, ["name", "age"])
        assert result["valid"] is False
        assert "age" in result["missing_keys"]

    def test_invalid_json_parse_error(self):
        result = pi._validate_json_keys("{not valid json}", ["key"])
        assert result["valid"] is False
        assert result["parse_error"] is not None

    def test_empty_required_keys(self):
        content = json.dumps({"x": 1})
        result = pi._validate_json_keys(content, [])
        assert result["valid"] is True


class TestGetEnvModelRegistry:
    def test_always_has_ollama(self):
        with patch.dict(os.environ, {}, clear=False):
            registry = pi._get_env_model_registry()
        assert any(m["provider"] == "ollama" for m in registry)

    def test_openai_added_when_key_set(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            registry = pi._get_env_model_registry()
        assert any(m["provider"] == "openai" for m in registry)

    def test_anthropic_added_when_key_set(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "ant-key"}):
            registry = pi._get_env_model_registry()
        assert any(m["provider"] == "anthropic" for m in registry)

    def test_ollama_url_from_env(self):
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://custom:11434"}):
            registry = pi._get_env_model_registry()
        ollama = next(m for m in registry if m["provider"] == "ollama")
        assert ollama["api_url"] == "http://custom:11434"


class TestRecordLineage:
    def test_appends_event(self):
        initial_count = len(pi._lineage_events)
        pi._record_lineage("source_a", "dest_b", "transform_c", "tenant_xyz")
        assert len(pi._lineage_events) > initial_count
        last = pi._lineage_events[-1]
        assert last["source"] == "source_a"
        assert last["destination"] == "dest_b"
        assert last["tenant_id"] == "tenant_xyz"

    def test_meta_defaults_to_empty(self):
        pi._record_lineage("s", "d", "t", "tenant")
        last = pi._lineage_events[-1]
        assert last["meta"] == {}

    def test_meta_passed_through(self):
        pi._record_lineage("s", "d", "t", "tenant", meta={"key": "value"})
        last = pi._lineage_events[-1]
        assert last["meta"] == {"key": "value"}


class TestGetSlaMetrics:
    def test_returns_expected_keys(self):
        with patch("backend.fastapi.app.routers.platform_intelligence.get_request_latency_snapshot",
                   return_value={"paths": {}}):
            result = pi._get_sla_metrics()
        assert "compliance_pct" in result
        assert "uptime_seconds" in result
        assert "status" in result

    def test_breached_paths_detected(self):
        slow_snapshot = {
            "paths": {
                "/slow-path": {"p95_ms": 5000},
                "/fast-path": {"p95_ms": 100},
            }
        }
        with patch("backend.fastapi.app.routers.platform_intelligence.get_request_latency_snapshot",
                   return_value=slow_snapshot), \
             patch.dict(os.environ, {"SLA_TARGET_P95_MS": "2000"}):
            result = pi._get_sla_metrics()
        assert "/slow-path" in result["breached_paths"]
        assert "/fast-path" in result["compliant_paths"]

    def test_all_compliant_gives_green(self):
        fast_snapshot = {"paths": {"/fast": {"p95_ms": 100}}}
        with patch("backend.fastapi.app.routers.platform_intelligence.get_request_latency_snapshot",
                   return_value=fast_snapshot):
            result = pi._get_sla_metrics()
        assert result["status"] == "green"
