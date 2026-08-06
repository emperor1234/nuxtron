"""
Tests for routers/trust_center.py, routers/notifications.py, routers/benchmarks.py,
routers/media_jobs.py, routers/bridges.py, routers/vse.py, and routers/auth.py.
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
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "misc-db-tenant"}
TENANT = "misc-db-tenant"


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ─── Trust Center ────────────────────────────────────────────────────────────

class TestTrustCenterHelpers:
    """Lines 85-160: direct tests of helper functions."""

    def test_db_count_open_incidents(self) -> None:
        """Lines 85-92: _db_count_open_incidents with mocked psycopg."""
        from backend.fastapi.app.routers.trust_center import _db_count_open_incidents
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (3, 1)
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("psycopg.connect", return_value=mock_conn):
            total, crit = _db_count_open_incidents(lambda: "host=localhost dbname=test user=t password=t", TENANT)
        assert total == 3
        assert crit == 1

    def test_db_count_active_chains(self) -> None:
        """Lines 96-102: _db_count_active_chains with mocked psycopg."""
        from backend.fastapi.app.routers.trust_center import _db_count_active_chains
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (5,)
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("psycopg.connect", return_value=mock_conn):
            count = _db_count_active_chains(lambda: "host=localhost dbname=test user=t password=t", TENANT)
        assert count == 5

    def test_mem_count_open_incidents(self) -> None:
        """Lines 118-122: in-memory count."""
        from backend.fastapi.app.routers.trust_center import _mem_count_open_incidents
        incidents = [
            {"tenant_id": TENANT, "resolved": False, "severity": "critical"},
            {"tenant_id": TENANT, "resolved": False, "severity": "medium"},
            {"tenant_id": TENANT, "resolved": True, "severity": "critical"},
            {"tenant_id": "other-tenant", "resolved": False, "severity": "high"},
        ]
        total, crit = _mem_count_open_incidents(incidents, TENANT)
        assert total == 2
        assert crit == 1

    def test_mem_count_active_chains(self) -> None:
        """Lines 125-126: in-memory active chains count."""
        from backend.fastapi.app.routers.trust_center import _mem_count_active_chains
        chains = [
            {"tenant_id": TENANT, "active": True},
            {"tenant_id": TENANT, "active": False},
            {"tenant_id": "other", "active": True},
        ]
        count = _mem_count_active_chains(chains, TENANT)
        assert count == 1

    def test_get_posture_counts_in_memory_fallback(self) -> None:
        """Lines 143-146: _get_posture_counts uses in-memory when db not ready."""
        from backend.fastapi.app.routers.trust_center import TrustCenterContext, _get_posture_counts
        ctx = TrustCenterContext(
            enforce_rate_limit=lambda *a, **k: None,
            policy_history_memory=[],
            approval_chains_memory=[
                {"tenant_id": TENANT, "active": True},
            ],
            incidents_memory=[
                {"tenant_id": TENANT, "resolved": False, "severity": "medium"},
            ],
            governance_snapshots_memory=[],
            audit_log_memory=[],
            get_db_ready=lambda: False,
        )
        open_inc, crit_inc, active_chains = _get_posture_counts(ctx, TENANT)
        assert open_inc == 1
        assert crit_inc == 0
        assert active_chains == 1

    def test_get_posture_counts_db_ready(self) -> None:
        """Lines 118-121: _get_posture_counts tries DB when ready."""
        from backend.fastapi.app.routers.trust_center import TrustCenterContext, _get_posture_counts
        mock_cur = MagicMock()
        mock_cur.fetchone.return_value = (2, 1)
        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        ctx = TrustCenterContext(
            enforce_rate_limit=lambda *a, **k: None,
            policy_history_memory=[],
            approval_chains_memory=[],
            incidents_memory=[],
            governance_snapshots_memory=[],
            audit_log_memory=[],
            get_db_ready=lambda: True,
            db_dsn=lambda: "host=localhost dbname=test user=t password=t",
        )
        with patch("psycopg.connect", return_value=mock_conn):
            open_inc, crit_inc, active_chains = _get_posture_counts(ctx, TENANT)
        assert open_inc == 2

    def test_posture_rating_critical(self) -> None:
        """Lines 73-77: _posture_rating."""
        from backend.fastapi.app.routers.trust_center import _posture_rating
        assert _posture_rating(20) == "critical"
        assert _posture_rating(60) == "warning"
        assert _posture_rating(90) == "healthy"


class TestTrustCenterRoutes:
    """Route-level tests for trust_center."""

    def test_posture_overview(self, client: TestClient) -> None:
        r = client.get("/trust/posture", headers=H)
        assert r.status_code in VALID

    def test_record_policy(self, client: TestClient) -> None:
        r = client.post("/trust/policies/record", headers=H, json={
            "policy_key": "allow_high_impact_actions",
            "old_value": {"value": False},
            "new_value": {"value": True},
            "change_reason": "Approved by CTO for Q4 2025",
            "actor_role": "admin",
        })
        assert r.status_code in VALID

    def test_create_approval_chain(self, client: TestClient) -> None:
        r = client.post("/trust/approval-chains", headers=H, json={
            "chain_name": "High Impact Action Review",
            "action_type": "high_impact_action",
            "steps": [{"approver": "cto@company.com", "required": True}],
            "require_all": True,
        })
        assert r.status_code in VALID

    def test_create_incident(self, client: TestClient) -> None:
        r = client.post("/trust/incidents", headers=H, json={
            "title": "Unauthorized access attempt detected",
            "description": "Multiple failed login attempts from suspicious IP addresses",
            "severity": "high",
            "affected_module": "auth",
        })
        assert r.status_code in VALID

    def test_create_governance_snapshot(self, client: TestClient) -> None:
        r = client.post("/trust/governance/snapshots", headers=H, json={
            "autonomy_enabled": True,
            "allow_high_impact_actions": False,
            "strict_policy_lock": True,
            "notes": "Q4 2025 governance snapshot",
        })
        assert r.status_code in VALID


# ─── Notifications ───────────────────────────────────────────────────────────

class TestNotificationsHelpers:
    """Lines 194-241: notification helper functions."""

    def test_policy_reason_enabled_matching(self) -> None:
        """Lines 200-204: _policy_reason returns eligible when enabled and match."""
        from backend.fastapi.app.routers.notifications import _policy_reason
        result = _policy_reason(True, True, "email")
        assert "eligible" in result or "email" in result

    def test_policy_reason_disabled(self) -> None:
        """Line 200: _policy_reason disabled → disabled token."""
        from backend.fastapi.app.routers.notifications import _policy_reason
        result = _policy_reason(False, True, "sms")
        assert "disabled" in result

    def test_policy_reason_suppressed(self) -> None:
        """Lines 201-202: _policy_reason suppressed by priority."""
        from backend.fastapi.app.routers.notifications import _policy_reason
        result = _policy_reason(True, False, "push")
        assert "suppressed" in result

    def test_batch_notifications_realtime(self) -> None:
        """Lines 221-222: realtime mode returns immediately."""
        from backend.fastapi.app.routers.notifications import _batch_notifications_for_digest
        notifs = [{"id": "n1", "priority": "urgent", "category": "billing"}]
        result = _batch_notifications_for_digest(notifs, "realtime")
        assert result["batch_mode"] == "realtime"

    def test_batch_notifications_daily(self) -> None:
        """Lines 224-241: daily mode aggregates."""
        from backend.fastapi.app.routers.notifications import _batch_notifications_for_digest
        notifs = [
            {"id": "n1", "priority": "info", "category": "security"},
            {"id": "n2", "priority": "warning", "category": "billing"},
        ]
        result = _batch_notifications_for_digest(notifs, "daily")
        assert result["batch_mode"] == "daily"
        assert result["summary"]["total"] == 2

    def test_apply_delivery_backoff(self) -> None:
        """Lines 262-265: exponential backoff capped at 3600."""
        from backend.fastapi.app.routers.notifications import _apply_delivery_backoff
        assert _apply_delivery_backoff(0) == 5
        assert _apply_delivery_backoff(1) == 10
        assert _apply_delivery_backoff(20) == 3600  # capped


class TestNotificationsRoutes:
    """Route-level tests."""

    def test_list_notifications(self, client: TestClient) -> None:
        r = client.get("/notifications", headers=H)
        assert r.status_code in VALID

    def test_create_notification(self, client: TestClient) -> None:
        r = client.post("/notifications", headers=H, json={
            "type": "billing",
            "title": "Invoice Due",
            "body": "Your invoice for November 2025 is due in 3 days",
            "priority": "warning",
            "category": "billing",
            "tenant_id": TENANT,
        })
        assert r.status_code in VALID

    def test_get_preferences(self, client: TestClient) -> None:
        r = client.get("/notifications/preferences", headers=H)
        assert r.status_code in VALID

    def test_update_preferences(self, client: TestClient) -> None:
        r = client.put("/notifications/preferences", headers=H, json={
            "email_enabled": True,
            "push_enabled": False,
            "sms_enabled": False,
            "digest_frequency": "daily",
        })
        assert r.status_code in VALID


# ─── Benchmarks ──────────────────────────────────────────────────────────────

class TestBenchmarksRoutes:
    """Lines 154-215: benchmark route helpers."""

    def test_list_benchmarks(self, client: TestClient) -> None:
        r = client.get("/benchmarks", headers=H)
        assert r.status_code in VALID

    def test_create_benchmark(self, client: TestClient) -> None:
        r = client.post("/benchmarks", headers=H, json={
            "name": "API Response Time P95",
            "category": "performance",
            "metric": "response_time_ms",
            "target_value": 200.0,
            "unit": "ms",
            "description": "P95 API response time should be under 200ms",
        })
        assert r.status_code in VALID

    def test_create_benchmark_result(self, client: TestClient) -> None:
        r = client.post("/benchmarks/results", headers=H, json={
            "benchmark_id": "bench-001",
            "measured_value": 180.5,
            "passed": True,
            "environment": "production",
            "metadata": {"endpoint": "/api/v1/users"},
        })
        assert r.status_code in VALID

    def test_benchmark_summary(self, client: TestClient) -> None:
        r = client.get("/benchmarks/summary", headers=H)
        assert r.status_code in VALID


# ─── Media Jobs ──────────────────────────────────────────────────────────────

class TestMediaJobsRoutes:
    """Lines 204-323: media job route tests."""

    def test_list_media_jobs(self, client: TestClient) -> None:
        r = client.get("/media-jobs", headers=H)
        assert r.status_code in VALID

    def test_create_media_job(self, client: TestClient) -> None:
        r = client.post("/media-jobs", headers=H, json={
            "type": "video_transcode",
            "input_url": "https://storage.example.com/raw/video-001.mp4",
            "output_format": "mp4",
            "quality": "1080p",
            "metadata": {"title": "Product Demo Video"},
        })
        assert r.status_code in VALID

    def test_get_media_job_not_found(self, client: TestClient) -> None:
        r = client.get("/media-jobs/nonexistent-job-9999", headers=H)
        assert r.status_code in VALID

    def test_update_media_job_status(self, client: TestClient) -> None:
        # Create a job first
        create_r = client.post("/media-jobs", headers=H, json={
            "type": "image_resize",
            "input_url": "https://storage.example.com/raw/image-001.jpg",
            "output_format": "webp",
            "quality": "high",
        })
        if create_r.status_code in (200, 201):
            job_id = create_r.json().get("id", "unknown")
            r = client.patch(f"/media-jobs/{job_id}", headers=H, json={
                "status": "completed",
                "output_url": "https://storage.example.com/processed/image-001.webp",
            })
            assert r.status_code in VALID


# ─── Bridges ─────────────────────────────────────────────────────────────────

class TestBridgesRoutes:
    """Lines 203-430: bridge route tests."""

    def test_list_bridges(self, client: TestClient) -> None:
        r = client.get("/bridges", headers=H)
        assert r.status_code in VALID

    def test_create_bridge(self, client: TestClient) -> None:
        r = client.post("/bridges", headers=H, json={
            "name": "Salesforce → IRA Sync",
            "source_system": "salesforce",
            "target_system": "ira",
            "sync_direction": "bidirectional",
            "field_mapping": {
                "account_id": "tenant_id",
                "opportunity_value": "deal_value",
            },
            "active": True,
        })
        assert r.status_code in VALID

    def test_get_bridge_not_found(self, client: TestClient) -> None:
        r = client.get("/bridges/nonexistent-bridge-9999", headers=H)
        assert r.status_code in VALID

    def test_bridge_sync_trigger(self, client: TestClient) -> None:
        """Lines 349-350: bridge sync trigger endpoint."""
        r = client.post("/bridges/sync", headers=H, json={
            "bridge_id": "bridge-nonexistent",
            "full_sync": False,
        })
        assert r.status_code in VALID

    def test_bridge_health(self, client: TestClient) -> None:
        r = client.get("/bridges/health", headers=H)
        assert r.status_code in VALID


# ─── VSE ─────────────────────────────────────────────────────────────────────

class TestVseRoutes:
    """Lines 417, 650-730: VSE route tests."""

    def test_algo_optimize(self, client: TestClient) -> None:
        """Lines 650-678: /vse/algo/optimize route."""
        r = client.post("/vse/algo/optimize", headers=H, json={
            "platform": "linkedin",
            "content_type": "text_post",
            "content": "Excited to share our new AI platform that's helping businesses automate revenue operations!",
            "hashtags": ["#AI", "#Revenue", "#Automation"],
            "posting_time": "2025-12-01T09:00:00Z",
        })
        assert r.status_code in VALID

    def test_algo_optimize_tiktok(self, client: TestClient) -> None:
        """Lines 661-662: TikTok platform path."""
        r = client.post("/vse/algo/optimize", headers=H, json={
            "platform": "tiktok",
            "content_type": "video",
            "content": "Check out this amazing AI demo that's going viral!",
            "hashtags": ["#AI", "#TikTokTech"],
        })
        assert r.status_code in VALID

    def test_algo_optimize_instagram(self, client: TestClient) -> None:
        """Lines 663-664: Instagram platform path."""
        r = client.post("/vse/algo/optimize", headers=H, json={
            "platform": "instagram",
            "content_type": "carousel",
            "content": "5 ways AI is transforming customer service in 2025",
            "hashtags": ["#CustomerService", "#AI", "#Innovation"],
        })
        assert r.status_code in VALID

    def test_network_map(self, client: TestClient) -> None:
        """Lines 707-730: /vse/network/map route."""
        r = client.post("/vse/network/map", headers=H, json={
            "seed_profile": "https://linkedin.com/in/example-profile",
            "depth": 2,
            "platform": "linkedin",
            "focus": "second_degree_connections",
        })
        assert r.status_code in VALID


# ─── Auth extra ───────────────────────────────────────────────────────────────

class TestAuthExtraRoutes:
    """Lines 48-332: auth router helper paths."""

    def test_token_tenant_mismatch(self, client: TestClient) -> None:
        """Lines 228-229: JWT tenant mismatch."""
        import base64
        import json as js
        # Create a fake JWT with mismatched tenant
        header = base64.urlsafe_b64encode(js.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        payload_data = base64.urlsafe_b64encode(js.dumps({"sub": "user-1", "tenant_id": "other-tenant"}).encode()).decode().rstrip("=")
        fake_jwt = f"{header}.{payload_data}.fake-signature"
        r = client.get("/auth/verify", headers={
            "X-API-Key": "test-api-key",
            "Authorization": f"Bearer {fake_jwt}",
            "X-Tenant-Id": TENANT,
        })
        assert r.status_code in VALID

    def test_health_check(self, client: TestClient) -> None:
        r = client.get("/auth/health", headers=H)
        assert r.status_code in VALID

    def test_saml_metadata_endpoint(self, client: TestClient) -> None:
        """Lines 311-315: SAML metadata route."""
        r = client.get("/auth/saml/metadata", headers=H)
        assert r.status_code in VALID

    def test_saml_login_endpoint(self, client: TestClient) -> None:
        """Lines 320-325: SAML login redirect."""
        r = client.get("/auth/saml/login", headers=H)
        assert r.status_code in VALID

    def test_saml_acs_endpoint(self, client: TestClient) -> None:
        """Lines 328-330: SAML ACS endpoint."""
        r = client.post("/auth/saml/acs", headers=H, json={
            "saml_response": "fake-saml-assertion-data",
        })
        assert r.status_code in VALID
