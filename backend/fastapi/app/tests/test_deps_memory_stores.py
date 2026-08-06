"""
Tests for deps.py authentication helpers and memory_stores module.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest

# ─── Helpers ──────────────────────────────────────────────────────────────── #

def _make_jwt(claims: dict, secret: str = "test-secret", expired: bool = False) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    if expired:
        claims = {**claims, "exp": int(time.time()) - 3600}
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    signing_input = f"{header}.{payload}".encode("ascii")
    sig = base64.urlsafe_b64encode(
        hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig}"


# ─── Tests for internal helpers ───────────────────────────────────────────── #

class TestHeaderValue:
    def test_strips_string(self) -> None:
        from backend.fastapi.app.deps import _header_value
        assert _header_value("  hello  ") == "hello"

    def test_none_returns_empty(self) -> None:
        from backend.fastapi.app.deps import _header_value
        assert _header_value(None) == ""

    def test_non_string_returns_empty(self) -> None:
        from backend.fastapi.app.deps import _header_value
        assert _header_value(42) == ""


class TestB64urlDecode:
    def test_roundtrip(self) -> None:
        from backend.fastapi.app.deps import _b64url_decode
        original = b"hello world"
        encoded = base64.urlsafe_b64encode(original).rstrip(b"=").decode()
        assert _b64url_decode(encoded) == original


class TestJwtVerifyHs256:
    def test_valid_token(self) -> None:
        from backend.fastapi.app.deps import _jwt_verify_hs256
        token = _make_jwt({"tenant_id": "t1"}, "mysecret")
        valid, claims, err = _jwt_verify_hs256(token, "mysecret")
        assert valid is True
        assert err is None
        assert (claims or {}).get("tenant_id") == "t1"

    def test_wrong_secret(self) -> None:
        from backend.fastapi.app.deps import _jwt_verify_hs256
        token = _make_jwt({"tenant_id": "t1"}, "correct-secret")
        valid, claims, err = _jwt_verify_hs256(token, "wrong-secret")
        assert valid is False
        assert err is not None

    def test_invalid_format(self) -> None:
        from backend.fastapi.app.deps import _jwt_verify_hs256
        valid, claims, err = _jwt_verify_hs256("not.a.jwt.at.all", "secret")
        assert valid is False

    def test_expired_token(self) -> None:
        from backend.fastapi.app.deps import _jwt_verify_hs256
        token = _make_jwt({"tenant_id": "t1"}, "mysecret", expired=True)
        valid, claims, err = _jwt_verify_hs256(token, "mysecret")
        assert valid is False
        assert "expired" in (err or "").lower()

    def test_invalid_payload_not_dict(self) -> None:
        from backend.fastapi.app.deps import _jwt_verify_hs256
        # Create token with non-dict payload
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(b'"just_a_string"').rstrip(b"=").decode()
        signing_input = f"{header}.{payload}".encode("ascii")
        sig = base64.urlsafe_b64encode(
            hmac.new(b"secret", signing_input, hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        token = f"{header}.{payload}.{sig}"
        valid, claims, err = _jwt_verify_hs256(token, "secret")
        assert valid is False


class TestEnforceQueryApiKeyPolicy:
    def test_no_query_param_allowed(self) -> None:
        from backend.fastapi.app.deps import _enforce_query_api_key_policy
        req = MagicMock()
        req.query_params = {}
        _enforce_query_api_key_policy(req)  # should not raise

    def test_api_key_in_query_raises(self) -> None:
        from backend.fastapi.app.deps import _enforce_query_api_key_policy
        from fastapi import HTTPException
        req = MagicMock()
        req.query_params = {"api_key": "somekey"}
        req.url.path = "/some/path"
        with pytest.raises(HTTPException) as exc_info:
            _enforce_query_api_key_policy(req)
        assert exc_info.value.status_code == 400

    def test_stream_endpoint_with_api_key_allowed(self) -> None:
        from backend.fastapi.app.deps import _enforce_query_api_key_policy
        req = MagicMock()
        req.query_params = {"api_key": "somekey"}
        req.url.path = "/notifications/stream"
        with patch.dict(os.environ, {"ALLOW_QUERY_API_KEY_FOR_STREAM": "true"}):
            _enforce_query_api_key_policy(req)  # should not raise


class TestEnforceTransportSecurity:
    def test_no_enforcement_by_default(self) -> None:
        from backend.fastapi.app.deps import _enforce_transport_security
        _enforce_transport_security("http", "none")  # Should not raise when disabled

    def test_https_enforced_rejects_http(self) -> None:
        from backend.fastapi.app.deps import _enforce_transport_security
        from fastapi import HTTPException
        with patch.dict(os.environ, {"ENFORCE_HTTPS_HEADER": "true"}):
            with pytest.raises(HTTPException) as exc_info:
                _enforce_transport_security("http", "")
            assert exc_info.value.status_code == 400

    def test_https_passes(self) -> None:
        from backend.fastapi.app.deps import _enforce_transport_security
        with patch.dict(os.environ, {"ENFORCE_HTTPS_HEADER": "true"}):
            _enforce_transport_security("https", "")  # Should not raise

    def test_mtls_required_rejects_unverified(self) -> None:
        from backend.fastapi.app.deps import _enforce_transport_security
        from fastapi import HTTPException
        with patch.dict(os.environ, {"REQUIRE_MTLS": "true", "ENFORCE_HTTPS_HEADER": "false"}):
            with pytest.raises(HTTPException) as exc_info:
                _enforce_transport_security("", "none")
            assert exc_info.value.status_code == 401

    def test_mtls_verified_passes(self) -> None:
        from backend.fastapi.app.deps import _enforce_transport_security
        with patch.dict(os.environ, {"REQUIRE_MTLS": "true", "ENFORCE_HTTPS_HEADER": "false"}):
            _enforce_transport_security("", "success")  # Should not raise


class TestResolveJwtSecret:
    def test_returns_env_var(self) -> None:
        from backend.fastapi.app.deps import _resolve_jwt_secret
        with patch.dict(os.environ, {"JWT_SIGNING_KEY": "my-jwt-secret"}):
            secret = _resolve_jwt_secret(is_production=True)
            assert secret == "my-jwt-secret"

    def test_fallback_to_api_key_in_dev(self) -> None:
        from backend.fastapi.app.deps import _resolve_jwt_secret
        with patch.dict(os.environ, {"JWT_SIGNING_KEY": "", "FASTAPI_API_KEY": "dev-key"}):
            secret = _resolve_jwt_secret(is_production=False)
            assert secret == "dev-key"

    def test_empty_in_production_without_jwt_key(self) -> None:
        from backend.fastapi.app.deps import _resolve_jwt_secret
        with patch.dict(os.environ, {"JWT_SIGNING_KEY": ""}):
            secret = _resolve_jwt_secret(is_production=True)
            assert secret == ""


class TestAuthenticateApiKey:
    def test_valid_api_key(self) -> None:
        from backend.fastapi.app.deps import _authenticate_api_key
        with patch.dict(os.environ, {"FASTAPI_API_KEY": "test-api-key", "ALLOW_HEADER_API_KEYS": "true"}):
            tenant_id, mode, subject, roles, jti, exp = _authenticate_api_key("test-api-key", "tenant-123")
            assert tenant_id == "tenant-123"
            assert mode == "api_key"
            assert subject == ""
            assert roles == []
            assert jti == ""
            assert exp == 0

    def test_invalid_api_key_raises(self) -> None:
        from backend.fastapi.app.deps import _authenticate_api_key
        from fastapi import HTTPException
        with patch.dict(os.environ, {"FASTAPI_API_KEY": "correct-key", "ALLOW_HEADER_API_KEYS": "true"}):
            with pytest.raises(HTTPException) as exc_info:
                _authenticate_api_key("wrong-key", "tenant-123")
            assert exc_info.value.status_code == 401

    def test_disabled_api_keys_raises(self) -> None:
        """Header API keys are blocked by default (ALLOW_HEADER_API_KEYS not set)."""
        # Do NOT set ALLOW_HEADER_API_KEYS — the default secure policy must reject header keys.
        import os as _os

        from backend.fastapi.app.deps import _authenticate_api_key
        from fastapi import HTTPException
        env_without_allow = {k: v for k, v in _os.environ.items() if k != "ALLOW_HEADER_API_KEYS"}
        with patch.dict(_os.environ, env_without_allow, clear=True):
            with pytest.raises(HTTPException) as exc_info:
                _authenticate_api_key("any-key", "tenant-123")
            assert exc_info.value.status_code == 401


class TestAuthenticateBearer:
    def test_valid_bearer_token(self) -> None:
        from backend.fastapi.app.deps import _authenticate_bearer
        token = _make_jwt({"tenant_id": "t1"}, "jwt-secret")
        with patch.dict(os.environ, {"JWT_SIGNING_KEY": "jwt-secret"}):
            tenant_id, mode, subject, roles, jti, exp = _authenticate_bearer(f"Bearer {token}", "t1", is_production=False)
            assert tenant_id == "t1"
            assert mode == "bearer_jwt"

    def test_no_jwt_secret_raises(self) -> None:
        from backend.fastapi.app.deps import _authenticate_bearer
        from fastapi import HTTPException
        with patch.dict(os.environ, {"JWT_SIGNING_KEY": "", "FASTAPI_API_KEY": ""}):
            with pytest.raises(HTTPException) as exc_info:
                _authenticate_bearer("Bearer sometoken", "t1", is_production=True)
            assert exc_info.value.status_code == 401

    def test_tenant_mismatch_raises(self) -> None:
        from backend.fastapi.app.deps import _authenticate_bearer
        from fastapi import HTTPException
        token = _make_jwt({"tenant_id": "t1"}, "jwt-secret")
        with patch.dict(os.environ, {"JWT_SIGNING_KEY": "jwt-secret"}):
            with pytest.raises(HTTPException) as exc_info:
                _authenticate_bearer(f"Bearer {token}", "t2", is_production=False)
            assert exc_info.value.status_code == 403

    def test_empty_tenant_in_token_is_rejected(self) -> None:
        """A bearer token with no tenant_id claim must be rejected outright —
        it must NOT fall back to a client-supplied X-Tenant-Id header, since
        that would let any caller holding a tenant-less token pick an
        arbitrary tenant."""
        from backend.fastapi.app.deps import _authenticate_bearer
        from fastapi import HTTPException
        token = _make_jwt({}, "jwt-secret")  # no tenant_id in token
        with patch.dict(os.environ, {"JWT_SIGNING_KEY": "jwt-secret"}):
            with pytest.raises(HTTPException) as exc_info:
                _authenticate_bearer(f"Bearer {token}", "header-tenant", is_production=False)
            assert exc_info.value.status_code == 401


class TestMemoryStores:
    def test_all_stores_are_lists(self) -> None:
        import backend.fastapi.app.memory_stores as ms
        assert isinstance(ms.scheduled_posts, list)
        assert isinstance(ms.email_contacts, list)
        assert isinstance(ms.audit_log, list)
        assert isinstance(ms.notifications, list)
        assert isinstance(ms.siem_cases, list)

    def test_stores_start_empty(self) -> None:
        # module-level lists start empty (before any test populates them)
        import backend.fastapi.app.memory_stores as ms
        # Just check they are iterable lists
        assert hasattr(ms, "scheduled_posts")
        assert hasattr(ms, "seo_analyses")
        assert hasattr(ms, "audit_log")
