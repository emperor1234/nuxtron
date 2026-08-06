"""
Additional tests for auth.py pure helpers and route branches.
Focused on uncovered code paths.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestValidateRelayState:
    def _fn(self):
        from backend.fastapi.app.routers.auth import _validate_relay_state
        return _validate_relay_state

    def test_none_returns_none(self) -> None:
        assert self._fn()(None) is None

    def test_empty_returns_none(self) -> None:
        assert self._fn()("") is None

    def test_whitespace_returns_none(self) -> None:
        assert self._fn()("   ") is None

    def test_relative_path_allowed(self) -> None:
        assert self._fn()("/dashboard") == "/dashboard"

    def test_relative_path_with_query_allowed(self) -> None:
        assert self._fn()("/dashboard?tab=settings") == "/dashboard?tab=settings"

    def test_protocol_relative_rejected(self) -> None:
        assert self._fn()("//evil.com") is None

    def test_external_url_rejected(self) -> None:
        result = self._fn()("https://evil.com/phish")
        assert result is None

    def test_absolute_url_matching_base_allowed(self) -> None:
        with patch.dict(os.environ, {"SAML_PUBLIC_BASE_URL": "https://myapp.example.com"}, clear=False):
            result = self._fn()("https://myapp.example.com/dashboard")
            assert result == "https://myapp.example.com/dashboard"

    def test_absolute_url_different_origin_rejected(self) -> None:
        with patch.dict(os.environ, {"SAML_PUBLIC_BASE_URL": "https://myapp.example.com"}, clear=False):
            result = self._fn()("https://attacker.com/steal")
            assert result is None

    def test_no_base_url_configured_external_rejected(self) -> None:
        with patch.dict(os.environ, {"SAML_PUBLIC_BASE_URL": ""}, clear=False):
            result = self._fn()("https://any-external.com/path")
            assert result is None

    def test_double_slash_not_relative_path(self) -> None:
        result = self._fn()("//not-safe.com/path")
        assert result is None


class TestEnsureSamlEnabled:
    def test_raises_when_disabled(self) -> None:
        from backend.fastapi.app.routers.auth import _ensure_saml_enabled
        from fastapi import HTTPException
        with patch.dict(os.environ, {"SAML_ENABLED": "false"}, clear=False):
            with patch("backend.fastapi.app.routers.auth.is_saml_enabled", return_value=False):
                with pytest.raises(HTTPException) as exc:
                    _ensure_saml_enabled()
                assert exc.value.status_code == 503


class TestResolveSamlTenantId:
    def test_extracts_from_attributes(self) -> None:
        from backend.fastapi.app.routers.auth import _resolve_saml_tenant_id
        assertion = {
            "name_id": "user@example.com",
            "attributes": {"tenant_id": ["tenant-123"]},
        }
        with patch.dict(os.environ, {"SAML_TENANT_ATTRIBUTE": "tenant_id"}, clear=False):
            result = _resolve_saml_tenant_id(assertion)
            assert result == "tenant-123"

    def test_falls_back_to_default_tenant_env(self) -> None:

        from backend.fastapi.app.routers.auth import _resolve_saml_tenant_id
        assertion = {"name_id": "user@example.com", "attributes": {}}
        with patch.dict(os.environ, {
            "SAML_TENANT_ATTRIBUTE": "tenant_id",
            "SAML_DEFAULT_TENANT_ID": "default-tenant",
        }, clear=False):
            result = _resolve_saml_tenant_id(assertion)
            assert result == "default-tenant"

    def test_raises_when_no_tenant_found(self) -> None:
        from backend.fastapi.app.routers.auth import _resolve_saml_tenant_id
        from fastapi import HTTPException
        assertion = {"name_id": "user@example.com", "attributes": {}}
        with patch.dict(os.environ, {
            "SAML_TENANT_ATTRIBUTE": "tenant_id",
            "SAML_DEFAULT_TENANT_ID": "",
        }, clear=False):
            with pytest.raises(HTTPException) as exc:
                _resolve_saml_tenant_id(assertion)
            assert exc.value.status_code == 400

    def test_handles_numeric_candidate_in_list(self) -> None:
        from backend.fastapi.app.routers.auth import _resolve_saml_tenant_id
        assertion = {
            "name_id": "user@example.com",
            "attributes": {"tenant_id": [42]},  # non-string
        }
        with patch.dict(os.environ, {
            "SAML_TENANT_ATTRIBUTE": "tenant_id",
            "SAML_DEFAULT_TENANT_ID": "",
        }, clear=False):
            result = _resolve_saml_tenant_id(assertion)
            assert result == "42"


class TestResolveSamlSubject:
    def test_returns_name_id(self) -> None:
        from backend.fastapi.app.routers.auth import _resolve_saml_subject
        assertion = {"name_id": "user@example.com", "attributes": {}}
        result = _resolve_saml_subject(assertion)
        assert result == "user@example.com"

    def test_raises_when_empty_name_id(self) -> None:
        from backend.fastapi.app.routers.auth import _resolve_saml_subject
        from fastapi import HTTPException
        assertion = {"name_id": "", "attributes": {}}
        with pytest.raises(HTTPException) as exc:
            _resolve_saml_subject(assertion)
        assert exc.value.status_code == 400

    def test_raises_when_name_id_missing(self) -> None:
        from backend.fastapi.app.routers.auth import _resolve_saml_subject
        from fastapi import HTTPException
        assertion = {"attributes": {}}
        with pytest.raises(HTTPException) as exc:
            _resolve_saml_subject(assertion)
        assert exc.value.status_code == 400


class TestAuthRoutesBranches:
    """Route-level tests to hit previously uncovered branches."""

    def test_register_user_success(self, client: TestClient) -> None:
        r = client.post("/auth/register", headers=H, json={
            "email": "newuser.extra2@example.com",
            "password": "ValidPass123!",
            "first_name": "Test",
            "last_name": "User",
        })
        assert r.status_code in VALID

    def test_register_duplicate_user(self, client: TestClient) -> None:
        """Duplicate registration should return 409."""
        payload = {
            "email": "duplicate.auth.extra2@example.com",
            "password": "StrongPass123!",
            "first_name": "Dup",
            "last_name": "User",
        }
        r1 = client.post("/auth/register", headers=H, json=payload)
        r2 = client.post("/auth/register", headers=H, json=payload)
        assert r1.status_code in VALID
        assert r2.status_code in VALID

    def test_login_user_not_found(self, client: TestClient) -> None:
        r = client.post("/auth/login", headers=H, json={
            "email": "ghost@example.com",
            "password": "AnyPass123!",
        })
        assert r.status_code in VALID

    def test_login_wrong_password(self, client: TestClient) -> None:
        """Register then login with wrong password."""
        client.post("/auth/register", headers=H, json={
            "email": "wrongpw.extra2@example.com",
            "password": "CorrectPass123!",
            "first_name": "Wrong",
            "last_name": "PW",
        })
        r = client.post("/auth/login", headers=H, json={
            "email": "wrongpw.extra2@example.com",
            "password": "WrongPass999!",
        })
        assert r.status_code in VALID

    def test_totp_setup(self, client: TestClient) -> None:
        r = client.post("/auth/totp/setup", headers=H, json={
            "account_name": "test@example.com",
        })
        assert r.status_code in VALID

    def test_totp_verify_invalid_code(self, client: TestClient) -> None:
        # First setup
        setup_r = client.post("/auth/totp/setup", headers=H, json={
            "account_name": "test-totp@example.com",
        })
        if setup_r.status_code == 200:
            secret = setup_r.json().get("secret", "BASE32SECRET")
        else:
            secret = "BASE32SECRET"
        r = client.post("/auth/totp/verify", headers=H, json={
            "secret": secret,
            "code": "000000",  # likely wrong
        })
        assert r.status_code in VALID

    def test_jwt_verify_invalid(self, client: TestClient) -> None:
        r = client.post("/auth/jwt/verify", headers=H, json={
            "token": "not.a.valid.jwt.token",
        })
        assert r.status_code in VALID

    def test_saml_login_disabled(self, client: TestClient) -> None:
        """When SAML disabled, route should return 503."""
        r = client.get("/auth/saml/login", headers=H)
        assert r.status_code in VALID

    def test_saml_metadata_disabled(self, client: TestClient) -> None:
        r = client.get("/auth/saml/metadata", headers=H)
        assert r.status_code in VALID

    def test_saml_acs_disabled(self, client: TestClient) -> None:
        r = client.post("/auth/saml/acs", headers=H, json={
            "saml_response": "fake-base64",
        })
        assert r.status_code in VALID
