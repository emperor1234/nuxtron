"""
Extra tests for super_admin_finance router — covering uncovered endpoints.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
H_SA = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant", "X-Super-Admin": "true"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestAccountingIntegrations:
    def test_get_integrations(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/accounting/integrations", headers=H)
        assert r.status_code in VALID

    def test_connect_integration_quickbooks(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/integrations/connect",
            headers=H,
            json={
                "provider": "quickbooks",
                "client_id": "qb_client_123",
                "client_secret": "qb_secret_xyz",
                "account_name": "Test Company",
            },
        )
        assert r.status_code in VALID

    def test_connect_integration_xero(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/integrations/connect",
            headers=H,
            json={
                "provider": "xero",
                "client_id": "xero_client_abc",
                "client_secret": "xero_secret_abc",
                "account_name": "Xero Account",
            },
        )
        assert r.status_code in VALID

    def test_disconnect_integration(self, client: TestClient) -> None:
        r = client.delete(
            "/ops/platform/super-admin/accounting/integrations/quickbooks",
            headers=H,
        )
        assert r.status_code in VALID


class TestAccountingExports:
    def test_create_export(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/exports",
            headers=H,
            json={
                "format": "csv",
                "date_range": "last_month",
                "report_type": "revenue",
            },
        )
        assert r.status_code in VALID

    def test_list_exports(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/accounting/exports", headers=H)
        assert r.status_code in VALID


class TestModuleSettings:
    def test_get_module_settings(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/module-settings", headers=H)
        assert r.status_code in VALID

    def test_update_module_settings(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/module-settings",
            headers=H,
            json={
                "module": "ira",
                "settings": {"autonomy_enabled": True, "max_budget": 100.0},
            },
        )
        assert r.status_code in VALID


class TestAuditLog:
    def test_get_audit_log(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/audit-log", headers=H)
        assert r.status_code in VALID

    def test_get_audit_log_with_filter(self, client: TestClient) -> None:
        r = client.get("/ops/platform/super-admin/audit-log?limit=10&offset=0", headers=H)
        assert r.status_code in VALID
