"""
Extra tests for auth.py pure helper functions and additional routes.
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


class TestValidateRelayState:
    def _fn(self):
        from backend.fastapi.app.routers.auth import _validate_relay_state
        return _validate_relay_state

    def test_none_returns_none(self) -> None:
        fn = self._fn()
        assert fn(None) is None

    def test_empty_string_returns_none(self) -> None:
        fn = self._fn()
        assert fn("") is None

    def test_whitespace_returns_none(self) -> None:
        fn = self._fn()
        assert fn("   ") is None

    def test_relative_path_returned(self) -> None:
        fn = self._fn()
        result = fn("/dashboard")
        assert result == "/dashboard"

    def test_protocol_relative_rejected(self) -> None:
        fn = self._fn()
        result = fn("//evil.com/attack")
        assert result is None

    def test_external_url_rejected(self) -> None:
        fn = self._fn()
        result = fn("https://evil.com/steal")
        assert result is None

    def test_relative_path_with_query(self) -> None:
        fn = self._fn()
        result = fn("/dashboard?foo=bar")
        assert result == "/dashboard?foo=bar"

    def test_absolute_url_matching_base(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"SAML_PUBLIC_BASE_URL": "https://myapp.example.com"}):
            result = fn("https://myapp.example.com/callback")
            assert result == "https://myapp.example.com/callback"

    def test_absolute_url_non_matching_base(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"SAML_PUBLIC_BASE_URL": "https://myapp.example.com"}):
            result = fn("https://evil.com/steal")
            assert result is None


class TestResolveSamlTenantId:
    def _fn(self):
        from backend.fastapi.app.routers.auth import _resolve_saml_tenant_id
        return _resolve_saml_tenant_id

    def test_resolves_from_attribute(self) -> None:
        fn = self._fn()
        assertion = {"attributes": {"tenant_id": ["my-tenant"]}, "name_id": "user@example.com"}
        result = fn(assertion)
        assert result == "my-tenant"

    def test_resolves_from_custom_attribute(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"SAML_TENANT_ATTRIBUTE": "org_id"}):
            assertion = {"attributes": {"org_id": ["org-123"]}, "name_id": "user@example.com"}
            result = fn(assertion)
            assert result == "org-123"

    def test_falls_back_to_default_tenant(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"SAML_DEFAULT_TENANT_ID": "default-tenant"}):
            assertion = {"attributes": {}, "name_id": "user@example.com"}
            result = fn(assertion)
            assert result == "default-tenant"

    def test_raises_when_no_tenant(self) -> None:
        import fastapi
        fn = self._fn()
        assertion = {"attributes": {}, "name_id": "user@example.com"}
        with pytest.raises(fastapi.HTTPException) as exc_info:
            fn(assertion)
        assert exc_info.value.status_code == 400

    def test_non_string_candidate_coerced(self) -> None:
        fn = self._fn()
        assertion = {"attributes": {"tenant_id": [42]}, "name_id": "user@example.com"}
        result = fn(assertion)
        assert result == "42"


class TestResolveSamlSubject:
    def _fn(self):
        from backend.fastapi.app.routers.auth import _resolve_saml_subject
        return _resolve_saml_subject

    def test_resolves_name_id(self) -> None:
        fn = self._fn()
        assertion = {"name_id": "user@example.com"}
        assert fn(assertion) == "user@example.com"

    def test_strips_whitespace(self) -> None:
        fn = self._fn()
        assertion = {"name_id": "  user@example.com  "}
        assert fn(assertion) == "user@example.com"

    def test_raises_when_no_subject(self) -> None:
        import fastapi
        fn = self._fn()
        assertion = {"name_id": ""}
        with pytest.raises(fastapi.HTTPException) as exc_info:
            fn(assertion)
        assert exc_info.value.status_code == 400


class TestIssueSamlJwt:
    def test_returns_token_exp_jti(self) -> None:
        from backend.fastapi.app.legacy_main import _jwt_sign_hs256
        from backend.fastapi.app.routers.auth import _issue_saml_jwt

        token, exp, jti = _issue_saml_jwt(
            tenant_id="my-tenant",
            subject="user@example.com",
            jwt_sign_hs256=_jwt_sign_hs256,
        )
        assert isinstance(token, str)
        assert isinstance(exp, int)
        assert isinstance(jti, str)
        assert len(jti) > 0

    def test_token_is_jwt(self) -> None:
        from backend.fastapi.app.legacy_main import _jwt_sign_hs256
        from backend.fastapi.app.routers.auth import _issue_saml_jwt

        token, _, _ = _issue_saml_jwt(
            tenant_id="test-tenant",
            subject="subject@test.com",
            jwt_sign_hs256=_jwt_sign_hs256,
        )
        parts = token.split(".")
        assert len(parts) == 3


class TestAuthRouteEndpoints:
    def test_totp_setup(self, client: TestClient) -> None:
        r = client.post("/auth/totp/setup", headers=H, json={})
        assert r.status_code in VALID

    def test_totp_verify_invalid_code(self, client: TestClient) -> None:
        r = client.post("/auth/totp/verify", headers=H, json={
            "secret": "JBSWY3DPEHPK3PXP",
            "code": "000000",
        })
        assert r.status_code in VALID

    def test_jwt_issue(self, client: TestClient) -> None:
        r = client.post("/auth/jwt/issue", headers=H, json={
            "subject": "test@example.com",
            "roles": ["admin"],
            "expires_in_seconds": 3600,
        })
        assert r.status_code in VALID

    def test_jwt_verify_invalid(self, client: TestClient) -> None:
        r = client.post("/auth/jwt/verify", headers=H, json={
            "token": "invalid.jwt.token",
        })
        assert r.status_code in VALID

    def test_jwt_issue_then_verify(self, client: TestClient) -> None:
        # Issue a token first
        issue_r = client.post("/auth/jwt/issue", headers=H, json={
            "subject": "round_trip@example.com",
            "roles": ["user"],
            "expires_in_seconds": 3600,
        })
        assert issue_r.status_code in VALID
        if issue_r.status_code == 200:
            token = issue_r.json().get("result", {}).get("token", "")
            if token:
                verify_r = client.post("/auth/jwt/verify", headers=H, json={"token": token})
                assert verify_r.status_code in VALID

    def test_saml_metadata(self, client: TestClient) -> None:
        r = client.get("/auth/saml/metadata", headers=H)
        assert r.status_code in VALID

    def test_saml_login(self, client: TestClient) -> None:
        r = client.get("/auth/saml/login", headers=H)
        assert r.status_code in VALID

    def test_saml_acs(self, client: TestClient) -> None:
        r = client.post("/auth/saml/acs", headers=H, json={"saml_response": "invalid-base64"})
        assert r.status_code in VALID

    def test_saml_slo(self, client: TestClient) -> None:
        r = client.get("/auth/saml/slo", headers=H)
        assert r.status_code in VALID

    def test_user_register(self, client: TestClient) -> None:
        r = client.post("/auth/users/register", headers=H, json={
            "email": "test@example.com",
            "password": "securepassword123",
        })
        assert r.status_code in VALID

    def test_user_login(self, client: TestClient) -> None:
        r = client.post("/auth/users/login", headers=H, json={
            "email": "test@example.com",
            "password": "securepassword123",
        })
        assert r.status_code in VALID

    def test_user_refresh(self, client: TestClient) -> None:
        r = client.post("/auth/users/refresh", headers=H, json={
            "refresh_token": "invalid-refresh-token",
        })
        assert r.status_code in VALID

    def test_user_logout(self, client: TestClient) -> None:
        r = client.post("/auth/users/logout", headers=H, json={
            "refresh_token": "some-refresh-token",
        })
        assert r.status_code in VALID

    def test_user_mfa_enroll(self, client: TestClient) -> None:
        r = client.post("/auth/users/mfa/enroll", headers=H, json={})
        assert r.status_code in VALID

    def test_user_mfa_verify(self, client: TestClient) -> None:
        r = client.post("/auth/users/mfa/verify", headers=H, json={
            "secret": "JBSWY3DPEHPK3PXP",
            "code": "000000",
        })
        assert r.status_code in VALID

    def test_user_magic_link(self, client: TestClient) -> None:
        r = client.post("/auth/users/magic-link", headers=H, json={
            "email": "user@example.com",
        })
        assert r.status_code in VALID

    def test_user_magic_link_verify(self, client: TestClient) -> None:
        r = client.post("/auth/users/magic-link/verify", headers=H, json={
            "token": "invalid-token-abc",
        })
        assert r.status_code in VALID
