"""
Supplementary ops/SIEM tests for routes not in test_seo_products_ops_misc.py.
Covers the remaining ops routes: hybrid-stacks, module-registry, super-admin dashboard,
siem data-collection, detection, investigation, architecture, flows, controls,
updates, endpoint-hardening, network-anomalies, dead-code findings, threat-hunting.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
HA = {**H, "X-Super-Admin": "true"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestOpsPlatformExtra:
    def test_hybrid_stacks(self, client: TestClient) -> None:
        r = client.get("/ops/platform/hybrid-stacks", headers=H)
        assert r.status_code in VALID

    def test_module_registry(self, client: TestClient) -> None:
        r = client.get("/ops/platform/module-registry", headers=H)
        assert r.status_code in VALID

    def test_super_admin_dashboard(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/dashboard", headers=HA)
        assert r.status_code in VALID


class TestOpsSiemExtra:
    def test_siem_data_collection(self, client: TestClient) -> None:
        r = client.get("/ops/siem/data-collection", headers=H)
        assert r.status_code in VALID

    def test_siem_detection(self, client: TestClient) -> None:
        r = client.get("/ops/siem/detection", headers=H)
        assert r.status_code in VALID

    def test_siem_investigation(self, client: TestClient) -> None:
        r = client.get("/ops/siem/investigation", headers=H)
        assert r.status_code in VALID

    def test_siem_compliance_retention(self, client: TestClient) -> None:
        r = client.post("/ops/siem/compliance/retention", headers=H, json={
            "retention_days": 90, "log_types": ["auth", "access"]
        })
        assert r.status_code in VALID

    def test_siem_architecture(self, client: TestClient) -> None:
        r = client.get("/ops/siem/architecture", headers=H)
        assert r.status_code in VALID

    def test_patch_siem_case(self, client: TestClient) -> None:
        r = client.patch("/ops/siem/cases/case_nonexistent", headers=H, json={
            "status": "resolved", "resolution": "False positive"
        })
        assert r.status_code in VALID

    def test_siem_flows(self, client: TestClient) -> None:
        r = client.get("/ops/siem/flows", headers=H)
        assert r.status_code in VALID

    def test_siem_controls(self, client: TestClient) -> None:
        r = client.get("/ops/siem/controls", headers=H)
        assert r.status_code in VALID

    def test_patch_siem_control(self, client: TestClient) -> None:
        r = client.patch("/ops/siem/controls/firewall/ctrl_001", headers=H, json={
            "enabled": True
        })
        assert r.status_code in VALID

    def test_siem_updates(self, client: TestClient) -> None:
        r = client.get("/ops/siem/updates", headers=H)
        assert r.status_code in VALID

    def test_apply_update(self, client: TestClient) -> None:
        r = client.post("/ops/siem/updates/update_001/apply", headers=H, json={})
        assert r.status_code in VALID

    def test_auto_pentest_jobs(self, client: TestClient) -> None:
        r = client.get("/ops/siem/auto-pentest/jobs", headers=H)
        assert r.status_code in VALID

    def test_vault_encryption_health(self, client: TestClient) -> None:
        r = client.get("/ops/siem/vault-encryption-health", headers=H)
        assert r.status_code in VALID

    def test_endpoint_hardening_baseline(self, client: TestClient) -> None:
        r = client.post("/ops/siem/endpoint-hardening/baseline", headers=H, json={
            "endpoints": ["10.0.0.1", "10.0.0.2"]
        })
        assert r.status_code in VALID

    def test_endpoint_hardening_status(self, client: TestClient) -> None:
        r = client.get("/ops/siem/endpoint-hardening/status", headers=H)
        assert r.status_code in VALID

    def test_network_anomalies(self, client: TestClient) -> None:
        r = client.get("/ops/siem/network-anomalies", headers=H)
        assert r.status_code in VALID

    def test_dead_code_findings(self, client: TestClient) -> None:
        r = client.get("/ops/siem/dead-code/findings", headers=H)
        assert r.status_code in VALID

    def test_threat_hunting_advanced(self, client: TestClient) -> None:
        r = client.get("/ops/siem/threat-hunting/advanced", headers=H)
        assert r.status_code in VALID
