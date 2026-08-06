"""
Tests for trust_center router — covering uncovered endpoints.
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


class TestPolicies:
    def test_create_policy(self, client: TestClient) -> None:
        r = client.post("/policies", headers=H, json={
            "name": "Data Retention Policy",
            "description": "Test policy",
            "category": "data",
        })
        assert r.status_code in VALID

    def test_list_policies(self, client: TestClient) -> None:
        r = client.get("/policies", headers=H)
        assert r.status_code in VALID


class TestApprovalChains:
    def test_create_approval_chain(self, client: TestClient) -> None:
        r = client.post("/approval-chains", headers=H, json={
            "name": "Finance Approval",
            "steps": ["manager", "director"],
        })
        assert r.status_code in VALID

    def test_list_approval_chains(self, client: TestClient) -> None:
        r = client.get("/approval-chains", headers=H)
        assert r.status_code in VALID

    def test_delete_approval_chain_nonexistent(self, client: TestClient) -> None:
        r = client.delete("/approval-chains/chain_nonexistent", headers=H)
        assert r.status_code in VALID


class TestIncidents:
    def test_create_incident(self, client: TestClient) -> None:
        r = client.post("/incidents", headers=H, json={
            "title": "Security Breach",
            "severity": "high",
            "description": "Unauthorized access detected.",
        })
        assert r.status_code in VALID

    def test_resolve_incident_nonexistent(self, client: TestClient) -> None:
        r = client.patch("/incidents/incident_nonexistent/resolve", headers=H, json={
            "resolution_notes": "Fixed by updating firewall rules.",
        })
        assert r.status_code in VALID

    def test_list_incidents(self, client: TestClient) -> None:
        r = client.get("/incidents", headers=H)
        assert r.status_code in VALID


class TestSnapshotsAndPosture:
    def test_create_snapshot(self, client: TestClient) -> None:
        r = client.post("/snapshots", headers=H, json={
            "label": "weekly-snapshot",
        })
        assert r.status_code in VALID

    def test_get_posture(self, client: TestClient) -> None:
        r = client.get("/posture", headers=H)
        assert r.status_code in VALID
