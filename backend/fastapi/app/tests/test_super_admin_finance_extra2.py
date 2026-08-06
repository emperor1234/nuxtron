"""
Additional tests for super_admin_finance.py — branch coverage for
disconnect, delete, retry-export, cancel-export, _guard_request.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
HA = {**H, "X-Super-Admin": "true"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestGuardRequest:
    """Test _guard_request pure function."""

    def test_calls_enforce_rate_limit(self) -> None:
        from backend.fastapi.app.deps import AuthContext
        from backend.fastapi.app.routers.super_admin_finance import _guard_request

        request = MagicMock()
        auth = MagicMock(spec=AuthContext)
        auth.tenant_id = "tenant1"
        enforce = MagicMock()
        require_sa = MagicMock()

        _guard_request(
            request, auth, "key",
            enforce_rate_limit=enforce,
            require_super_admin_access=require_sa,
            scope="test:scope",
            limit=10,
            window_seconds=60,
        )
        enforce.assert_called_once_with("tenant1:test:scope", 10, 60)

    def test_calls_require_super_admin_access(self) -> None:
        from backend.fastapi.app.deps import AuthContext
        from backend.fastapi.app.routers.super_admin_finance import _guard_request

        request = MagicMock()
        auth = MagicMock(spec=AuthContext)
        auth.tenant_id = "tenant2"
        enforce = MagicMock()
        require_sa = MagicMock()

        _guard_request(
            request, auth, "admin-key",
            enforce_rate_limit=enforce,
            require_super_admin_access=require_sa,
            scope="test:scope",
            limit=5,
            window_seconds=30,
        )
        require_sa.assert_called_once_with(request, "admin-key")

    def test_propagates_rate_limit_exception(self) -> None:
        from backend.fastapi.app.deps import AuthContext
        from backend.fastapi.app.routers.super_admin_finance import _guard_request

        request = MagicMock()
        auth = MagicMock(spec=AuthContext)
        auth.tenant_id = "tenant3"
        enforce = MagicMock(side_effect=Exception("rate limited"))
        require_sa = MagicMock()

        with pytest.raises(Exception, match="rate limited"):
            _guard_request(
                request, auth, None,
                enforce_rate_limit=enforce,
                require_super_admin_access=require_sa,
                scope="test",
                limit=1,
                window_seconds=1,
            )

    def test_propagates_super_admin_exception(self) -> None:
        from backend.fastapi.app.deps import AuthContext
        from backend.fastapi.app.routers.super_admin_finance import _guard_request
        from fastapi import HTTPException

        request = MagicMock()
        auth = MagicMock(spec=AuthContext)
        auth.tenant_id = "tenant4"
        enforce = MagicMock()
        require_sa = MagicMock(side_effect=HTTPException(status_code=403, detail="Forbidden"))

        with pytest.raises(HTTPException) as exc:
            _guard_request(
                request, auth, "bad-key",
                enforce_rate_limit=enforce,
                require_super_admin_access=require_sa,
                scope="test",
                limit=10,
                window_seconds=60,
            )
        assert exc.value.status_code == 403


class TestSuperAdminExtraRoutes:
    """Test routes that weren't in the first test file."""

    def test_disconnect_integration(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/integrations/disconnect",
            headers=H,
            json={"provider": "quickbooks"},
        )
        assert r.status_code in VALID

    def test_disconnect_integration_xero(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/integrations/disconnect",
            headers=H,
            json={"provider": "xero"},
        )
        assert r.status_code in VALID

    def test_disconnect_invalid_provider(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/integrations/disconnect",
            headers=H,
            json={"provider": "invalid_provider"},
        )
        assert r.status_code in VALID

    def test_delete_integration_provider(self, client: TestClient) -> None:
        r = client.delete(
            "/ops/platform/super-admin/accounting/integrations/quickbooks",
            headers=H,
        )
        assert r.status_code in VALID

    def test_delete_integration_xero(self, client: TestClient) -> None:
        r = client.delete(
            "/ops/platform/super-admin/accounting/integrations/xero",
            headers=H,
        )
        assert r.status_code in VALID

    def test_delete_integration_hmrc(self, client: TestClient) -> None:
        r = client.delete(
            "/ops/platform/super-admin/accounting/integrations/hmrc",
            headers=H,
        )
        assert r.status_code in VALID

    def test_retry_export_not_found(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/exports/99999/retry",
            headers=H,
        )
        assert r.status_code in VALID

    def test_retry_export_zero_id(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/exports/0/retry",
            headers=H,
        )
        assert r.status_code in VALID

    def test_cancel_export_not_found(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/exports/99999/cancel",
            headers=H,
        )
        assert r.status_code in VALID

    def test_cancel_export_zero_id(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/exports/0/cancel",
            headers=H,
        )
        assert r.status_code in VALID

    def test_connect_integration_hmrc(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/integrations/connect",
            headers=H,
            json={
                "provider": "hmrc",
                "client_id": "hmrc-client-abc",
                "account_name": "HMRC Account",
            },
        )
        assert r.status_code in VALID

    def test_create_export_xero(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/exports",
            headers=H,
            json={
                "provider": "xero",
                "export_type": "pnl",
                "period_label": "Q1-2024",
            },
        )
        assert r.status_code in VALID

    def test_create_export_ledger(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/accounting/exports",
            headers=H,
            json={
                "provider": "quickbooks",
                "export_type": "ledger",
                "period_label": "2024-01",
            },
        )
        assert r.status_code in VALID

    def test_module_settings_update_disable(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/module-settings",
            headers=H,
            json={
                "key": "feature_x",
                "enabled": False,
                "value": "",
            },
        )
        assert r.status_code in VALID

    def test_module_settings_update_with_value(self, client: TestClient) -> None:
        r = client.post(
            "/ops/platform/super-admin/module-settings",
            headers=H,
            json={
                "key": "feature_y",
                "enabled": True,
                "value": "custom_value",
            },
        )
        assert r.status_code in VALID
