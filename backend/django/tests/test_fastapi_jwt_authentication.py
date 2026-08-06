"""Tests for platform_api.authentication.FastAPIJWTAuthentication.

Verifies that a bearer JWT shaped exactly like the ones FastAPI's
routers/auth.py issues (iss='nuxtron-fastapi', tenant_id/sub/roles claims,
HS256 signed with the shared JWT_SIGNING_KEY) is accepted by Django, and that
tokens missing the FastAPI marker, using the wrong secret, or expired, are
rejected (or passed through, for the "not my token" case).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from platform_api.authentication import FastAPIJWTAuthentication

SHARED_SECRET = "test-shared-jwt-signing-key"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _make_token(*, secret: str = SHARED_SECRET, iss: str = "nuxtron-fastapi", tenant_id: str = "tenant-1",
                 sub: str = "user-1", roles: list[str] | None = None, exp_in: int = 3600) -> str:
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": sub,
        "tenant_id": tenant_id,
        "roles": roles or [],
        "iat": now,
        "exp": now + exp_in,
        "iss": iss,
        "jti": "test-jti-123",
    }
    head = _b64url(json.dumps(header, separators=(",", ":")).encode())
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode("utf-8"), f"{head}.{body}".encode("ascii"), hashlib.sha256).digest()
    return f"{head}.{body}.{_b64url(sig)}"


@pytest.fixture(autouse=True)
def _shared_secret(monkeypatch):
    monkeypatch.setenv("JWT_SIGNING_KEY", SHARED_SECRET)


class TestFastAPIJWTAuthentication:
    def _request_with_token(self, token: str):
        factory = APIRequestFactory()
        request = factory.get("/api/whatever", HTTP_AUTHORIZATION=f"Bearer {token}")
        return request

    def test_accepts_valid_fastapi_token(self) -> None:
        token = _make_token(tenant_id="acme", sub="alice", roles=["admin"])
        request = self._request_with_token(token)
        result = FastAPIJWTAuthentication().authenticate(request)
        assert result is not None
        principal, returned_token = result
        assert principal.tenant_id == "acme"
        assert principal.subject == "alice"
        assert principal.roles == ["admin"]
        assert principal.is_authenticated is True
        assert returned_token == token

    def test_rejects_wrong_secret(self) -> None:
        token = _make_token(secret="wrong-secret")
        request = self._request_with_token(token)
        # Wrong secret means signature verification fails -> _verify_hs256
        # returns None -> authenticate() returns None (not raises), since a
        # not-FastAPI-shaped or invalid token should fall through to the next
        # authenticator rather than hard-failing the whole auth chain.
        result = FastAPIJWTAuthentication().authenticate(request)
        assert result is None

    def test_ignores_non_fastapi_issuer(self) -> None:
        """A Django-issued (simplejwt) token must pass through untouched so
        the next authenticator in the chain gets a chance at it."""
        token = _make_token(iss="some-other-issuer")
        request = self._request_with_token(token)
        result = FastAPIJWTAuthentication().authenticate(request)
        assert result is None

    def test_rejects_expired_token(self) -> None:
        token = _make_token(exp_in=-100)
        request = self._request_with_token(token)
        result = FastAPIJWTAuthentication().authenticate(request)
        assert result is None

    def test_rejects_missing_tenant_claim(self) -> None:
        token = _make_token(tenant_id="")
        request = self._request_with_token(token)
        with pytest.raises(AuthenticationFailed):
            FastAPIJWTAuthentication().authenticate(request)

    def test_no_authorization_header_returns_none(self) -> None:
        factory = APIRequestFactory()
        request = factory.get("/api/whatever")
        result = FastAPIJWTAuthentication().authenticate(request)
        assert result is None

    def test_non_bearer_scheme_returns_none(self) -> None:
        factory = APIRequestFactory()
        request = factory.get("/api/whatever", HTTP_AUTHORIZATION="Basic abc123")
        result = FastAPIJWTAuthentication().authenticate(request)
        assert result is None
