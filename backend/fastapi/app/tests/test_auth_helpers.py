"""Tests for pure helper functions in auth.py."""
import os
import time

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import patch

import pytest
from backend.fastapi.app.routers.auth import (
    _issue_saml_jwt,
    _resolve_saml_subject,
    _resolve_saml_tenant_id,
    _validate_relay_state,
)
from fastapi import HTTPException

# ─── _validate_relay_state ───────────────────────────────────────────────────

class TestValidateRelayState:
    def test_none_returns_none(self):
        assert _validate_relay_state(None) is None

    def test_empty_returns_none(self):
        assert _validate_relay_state("") is None

    def test_whitespace_returns_none(self):
        assert _validate_relay_state("   ") is None

    def test_relative_path(self):
        assert _validate_relay_state("/dashboard") == "/dashboard"

    def test_protocol_relative_rejected(self):
        assert _validate_relay_state("//evil.com") is None

    def test_http_url_rejected_without_base(self):
        with patch.dict(os.environ, {"SAML_PUBLIC_BASE_URL": ""}):
            result = _validate_relay_state("https://evil.com/steal")
            assert result is None

    def test_matching_base_url_allowed(self):
        with patch.dict(os.environ, {"SAML_PUBLIC_BASE_URL": "https://app.example.com"}):
            result = _validate_relay_state("https://app.example.com/callback")
            assert result == "https://app.example.com/callback"

    def test_different_domain_rejected(self):
        with patch.dict(os.environ, {"SAML_PUBLIC_BASE_URL": "https://app.example.com"}):
            result = _validate_relay_state("https://evil.com/steal")
            assert result is None

    def test_strips_leading_whitespace(self):
        result = _validate_relay_state("  /home")
        assert result == "/home"


# ─── _resolve_saml_tenant_id ─────────────────────────────────────────────────

class TestResolveSamlTenantId:
    def test_resolves_from_attribute(self):
        assertion = {"name_id": "user@example.com", "attributes": {"tenant_id": ["tenant-abc"]}}
        result = _resolve_saml_tenant_id(assertion)
        assert result == "tenant-abc"

    def test_custom_attribute_name(self):
        with patch.dict(os.environ, {"SAML_TENANT_ATTRIBUTE": "org"}):
            assertion = {"attributes": {"org": ["my-org"]}}
            result = _resolve_saml_tenant_id(assertion)
            assert result == "my-org"

    def test_falls_back_to_default_tenant(self):
        with patch.dict(os.environ, {"SAML_DEFAULT_TENANT_ID": "default-tenant", "SAML_TENANT_ATTRIBUTE": "tenant_id"}):
            assertion = {"attributes": {}}
            result = _resolve_saml_tenant_id(assertion)
            assert result == "default-tenant"

    def test_raises_if_no_tenant(self):
        with patch.dict(os.environ, {"SAML_DEFAULT_TENANT_ID": "", "SAML_TENANT_ATTRIBUTE": "tenant_id"}):
            assertion = {"attributes": {}}
            with pytest.raises(HTTPException) as exc:
                _resolve_saml_tenant_id(assertion)
            assert exc.value.status_code == 400

    def test_handles_integer_tenant(self):
        assertion = {"attributes": {"tenant_id": [42]}}
        result = _resolve_saml_tenant_id(assertion)
        assert result == "42"


# ─── _resolve_saml_subject ───────────────────────────────────────────────────

class TestResolveSamlSubject:
    def test_returns_name_id(self):
        assertion = {"name_id": "user@example.com"}
        assert _resolve_saml_subject(assertion) == "user@example.com"

    def test_strips_whitespace(self):
        assertion = {"name_id": "  user@example.com  "}
        assert _resolve_saml_subject(assertion) == "user@example.com"

    def test_missing_name_id_raises(self):
        with pytest.raises(HTTPException) as exc:
            _resolve_saml_subject({})
        assert exc.value.status_code == 400

    def test_empty_name_id_raises(self):
        with pytest.raises(HTTPException) as exc:
            _resolve_saml_subject({"name_id": ""})
        assert exc.value.status_code == 400


# ─── _issue_saml_jwt ─────────────────────────────────────────────────────────

class TestIssueSamlJwt:
    def _mock_signer(self, payload, secret):
        return "signed-jwt-token"

    def test_returns_tuple(self):
        result = _issue_saml_jwt(
            tenant_id="tenant-1",
            subject="user@example.com",
            jwt_sign_hs256=self._mock_signer,
        )
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_token_from_signer(self):
        token, exp, jti = _issue_saml_jwt(
            tenant_id="tenant-1",
            subject="user@example.com",
            jwt_sign_hs256=self._mock_signer,
        )
        assert token == "signed-jwt-token"

    def test_exp_is_future(self):
        _, exp, _ = _issue_saml_jwt(
            tenant_id="tenant-1",
            subject="user@example.com",
            jwt_sign_hs256=self._mock_signer,
        )
        assert exp > int(time.time())

    def test_jti_is_string(self):
        _, _, jti = _issue_saml_jwt(
            tenant_id="tenant-1",
            subject="user@example.com",
            jwt_sign_hs256=self._mock_signer,
        )
        assert isinstance(jti, str)
        assert len(jti) > 0

    def test_custom_session_seconds(self):
        with patch.dict(os.environ, {"SAML_SESSION_SECONDS": "3600"}):
            _, exp, _ = _issue_saml_jwt(
                tenant_id="tenant-1",
                subject="user@example.com",
                jwt_sign_hs256=self._mock_signer,
            )
            now = int(time.time())
            # exp should be approximately now + 3600
            assert abs(exp - now - 3600) < 5
