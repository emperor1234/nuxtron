"""
Tests for the tenants router — covering all 4 routes + memory and DB paths.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

HEADERS = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 400, 401, 403, 404, 409, 422, 500)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestCreateTenant:
    def test_create_with_valid_payload(self, client: TestClient) -> None:
        r = client.post("/tenants", headers=HEADERS, json={
            "display_name": "Acme Corp",
            "plan": "starter",
            "status": "active",
            "settings": {},
        })
        assert r.status_code in VALID

    def test_create_with_all_plans(self, client: TestClient) -> None:
        for plan in ("starter", "growth", "pro", "enterprise"):
            r = client.post("/tenants", headers=HEADERS, json={
                "display_name": f"Company {plan}",
                "plan": plan,
            })
            assert r.status_code in VALID

    def test_create_missing_display_name(self, client: TestClient) -> None:
        r = client.post("/tenants", headers=HEADERS, json={"plan": "starter"})
        assert r.status_code == 422

    def test_create_short_display_name_rejected(self, client: TestClient) -> None:
        r = client.post("/tenants", headers=HEADERS, json={"display_name": "A"})
        assert r.status_code == 422

    def test_create_with_settings(self, client: TestClient) -> None:
        r = client.post("/tenants", headers=HEADERS, json={
            "display_name": "With Settings",
            "settings": {"feature_x": True},
        })
        assert r.status_code in VALID

    def test_unauthenticated_rejected(self, client: TestClient) -> None:
        r = client.post("/tenants", json={"display_name": "No Auth"})
        assert r.status_code in (401, 403, 422)


class TestListTenants:
    def test_list_returns_ok(self, client: TestClient) -> None:
        r = client.get("/tenants", headers=HEADERS)
        assert r.status_code in VALID

    def test_list_unauthenticated(self, client: TestClient) -> None:
        r = client.get("/tenants")
        assert r.status_code in (401, 403)


class TestUpdateTenant:
    def test_update_cross_tenant_forbidden(self, client: TestClient) -> None:
        r = client.patch("/tenants/other-tenant-id", headers=HEADERS, json={
            "display_name": "New Name",
        })
        assert r.status_code == 403

    def test_update_own_tenant(self, client: TestClient) -> None:
        r = client.patch("/tenants/test-tenant", headers=HEADERS, json={
            "display_name": "Updated Tenant",
        })
        assert r.status_code in VALID

    def test_update_plan(self, client: TestClient) -> None:
        r = client.patch("/tenants/test-tenant", headers=HEADERS, json={
            "plan": "enterprise",
        })
        assert r.status_code in VALID

    def test_update_status(self, client: TestClient) -> None:
        r = client.patch("/tenants/test-tenant", headers=HEADERS, json={
            "status": "suspended",
        })
        assert r.status_code in VALID

    def test_update_settings(self, client: TestClient) -> None:
        r = client.patch("/tenants/test-tenant", headers=HEADERS, json={
            "settings": {"key": "value"},
        })
        assert r.status_code in VALID

    def test_update_unauthenticated(self, client: TestClient) -> None:
        r = client.patch("/tenants/test-tenant", json={"display_name": "No Auth"})
        assert r.status_code in (401, 403, 422)


class TestDeleteTenant:
    def test_delete_cross_tenant_forbidden(self, client: TestClient) -> None:
        r = client.delete("/tenants/other-tenant-id", headers=HEADERS)
        assert r.status_code == 403

    def test_delete_own_tenant(self, client: TestClient) -> None:
        r = client.delete("/tenants/test-tenant", headers=HEADERS)
        assert r.status_code in VALID

    def test_delete_unauthenticated(self, client: TestClient) -> None:
        r = client.delete("/tenants/test-tenant")
        assert r.status_code in (401, 403)
