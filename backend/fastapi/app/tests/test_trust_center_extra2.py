"""
Additional tests for trust_center.py pure helpers.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestNowIso:
    def test_returns_string(self) -> None:
        from backend.fastapi.app.routers.trust_center import _now_iso
        result = _now_iso()
        assert isinstance(result, str)
        assert "T" in result  # ISO format


class TestPostureRating:
    def _fn(self):
        from backend.fastapi.app.routers.trust_center import _posture_rating
        return _posture_rating

    def test_critical_below_40(self) -> None:
        fn = self._fn()
        assert fn(0.0) == "critical"
        assert fn(39.9) == "critical"

    def test_warning_40_to_70(self) -> None:
        fn = self._fn()
        assert fn(40.0) == "warning"
        assert fn(69.9) == "warning"

    def test_healthy_70_plus(self) -> None:
        fn = self._fn()
        assert fn(70.0) == "healthy"
        assert fn(100.0) == "healthy"


class TestMemCountOpenIncidents:
    def _fn(self):
        from backend.fastapi.app.routers.trust_center import _mem_count_open_incidents
        return _mem_count_open_incidents

    def test_empty_list(self) -> None:
        fn = self._fn()
        total, crit = fn([], "tenant-1")
        assert total == 0
        assert crit == 0

    def test_counts_open_incidents(self) -> None:
        fn = self._fn()
        incidents = [
            {"tenant_id": "tenant-1", "resolved": False, "severity": "critical"},
            {"tenant_id": "tenant-1", "resolved": False, "severity": "low"},
            {"tenant_id": "tenant-1", "resolved": True, "severity": "critical"},
            {"tenant_id": "other-tenant", "resolved": False, "severity": "critical"},
        ]
        total, crit = fn(incidents, "tenant-1")
        assert total == 2
        assert crit == 1

    def test_only_counts_correct_tenant(self) -> None:
        fn = self._fn()
        incidents = [
            {"tenant_id": "other", "resolved": False, "severity": "low"},
        ]
        total, crit = fn(incidents, "my-tenant")
        assert total == 0
        assert crit == 0


class TestMemCountActiveChains:
    def _fn(self):
        from backend.fastapi.app.routers.trust_center import _mem_count_active_chains
        return _mem_count_active_chains

    def test_empty_list(self) -> None:
        fn = self._fn()
        assert fn([], "tenant-1") == 0

    def test_counts_active_chains(self) -> None:
        fn = self._fn()
        chains = [
            {"tenant_id": "tenant-1", "active": True},
            {"tenant_id": "tenant-1", "active": False},
            {"tenant_id": "tenant-1", "active": True},
            {"tenant_id": "other", "active": True},
        ]
        assert fn(chains, "tenant-1") == 2

    def test_no_active_for_tenant(self) -> None:
        fn = self._fn()
        chains = [
            {"tenant_id": "tenant-1", "active": False},
        ]
        assert fn(chains, "tenant-1") == 0


class TestTrustCenterRoutes:
    """Smoke tests for trust_center endpoints."""

    def test_get_posture(self, client: TestClient) -> None:
        r = client.get("/trust/posture", headers=H)
        assert r.status_code in VALID

    def test_record_policy(self, client: TestClient) -> None:
        r = client.post("/trust/policies", headers=H, json={
            "policy_type": "gdpr",
            "change_type": "update",
            "description": "Updated GDPR policy",
            "new_value": "Opt-in required",
        })
        assert r.status_code in VALID

    def test_list_policies(self, client: TestClient) -> None:
        r = client.get("/trust/policies", headers=H)
        assert r.status_code in VALID

    def test_create_chain(self, client: TestClient) -> None:
        r = client.post("/trust/approval-chains", headers=H, json={
            "name": "Security Approval Chain",
            "description": "Requires 2 approvals",
            "steps": [
                {"approver_email": "security@example.com", "required": True},
            ],
        })
        assert r.status_code in VALID

    def test_list_chains(self, client: TestClient) -> None:
        r = client.get("/trust/approval-chains", headers=H)
        assert r.status_code in VALID

    def test_create_incident(self, client: TestClient) -> None:
        r = client.post("/trust/incidents", headers=H, json={
            "title": "Data breach detected",
            "severity": "critical",
            "description": "Unauthorized access to user data",
        })
        assert r.status_code in VALID

    def test_list_incidents(self, client: TestClient) -> None:
        r = client.get("/trust/incidents", headers=H)
        assert r.status_code in VALID

    def test_resolve_incident_not_found(self, client: TestClient) -> None:
        r = client.post("/trust/incidents/nonexistent-id/resolve", headers=H, json={
            "resolution_notes": "Patched",
        })
        assert r.status_code in VALID

    def test_deactivate_chain_not_found(self, client: TestClient) -> None:
        r = client.delete("/trust/approval-chains/nonexistent-id", headers=H)
        assert r.status_code in VALID

    def test_capture_snapshot(self, client: TestClient) -> None:
        r = client.post("/trust/snapshots", headers=H, json={
            "snapshot_type": "quarterly",
            "notes": "Q1 2024 compliance snapshot",
        })
        assert r.status_code in VALID
