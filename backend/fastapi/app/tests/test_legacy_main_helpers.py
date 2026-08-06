"""
Unit tests for pure helper functions in legacy_main.py.
Targets _b64url_encode, _b64url_decode, _jwt_sign_hs256, _jwt_verify_hs256,
_totp_secret, _totp_code, _totp_verify, _is_production, _allow_api_docs,
_enforce_rate_limit, reset_rate_limits_for_tests, RateLimitExceededError,
and dispatch helpers.
"""
from __future__ import annotations

import os
import time
from unittest.mock import patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest


class TestB64urlHelpers:
    def test_encode_decode_roundtrip(self) -> None:
        from backend.fastapi.app.legacy_main import _b64url_decode, _b64url_encode
        data = b"hello world test bytes 12345"
        encoded = _b64url_encode(data)
        decoded = _b64url_decode(encoded)
        assert decoded == data

    def test_no_padding_in_encoded(self) -> None:
        from backend.fastapi.app.legacy_main import _b64url_encode
        encoded = _b64url_encode(b"test")
        assert "=" not in encoded

    def test_empty_bytes_roundtrip(self) -> None:
        from backend.fastapi.app.legacy_main import _b64url_decode, _b64url_encode
        assert _b64url_decode(_b64url_encode(b"")) == b""


class TestJwtSignVerify:
    SECRET = "test_secret_key_12345"

    def test_sign_and_verify_valid_token(self) -> None:
        from backend.fastapi.app.legacy_main import _jwt_sign_hs256, _jwt_verify_hs256
        payload = {"sub": "user123", "role": "admin"}
        token = _jwt_sign_hs256(payload, self.SECRET)
        ok, claims, err = _jwt_verify_hs256(token, self.SECRET)
        assert ok is True
        assert err is None
        assert claims is not None
        assert claims["sub"] == "user123"

    def test_verify_wrong_secret_fails(self) -> None:
        from backend.fastapi.app.legacy_main import _jwt_sign_hs256, _jwt_verify_hs256
        token = _jwt_sign_hs256({"sub": "user"}, self.SECRET)
        ok, claims, err = _jwt_verify_hs256(token, "wrong_secret")
        assert ok is False
        assert err is not None

    def test_verify_malformed_token(self) -> None:
        from backend.fastapi.app.legacy_main import _jwt_verify_hs256
        ok, claims, err = _jwt_verify_hs256("not.a.valid.token.extra", self.SECRET)
        assert ok is False

    def test_verify_expired_token(self) -> None:
        from backend.fastapi.app.legacy_main import _jwt_sign_hs256, _jwt_verify_hs256
        payload = {"sub": "user", "exp": int(time.time()) - 10}
        token = _jwt_sign_hs256(payload, self.SECRET)
        ok, claims, err = _jwt_verify_hs256(token, self.SECRET)
        assert ok is False
        assert err is not None
        assert "expired" in (err or "").lower()

    def test_verify_valid_with_future_exp(self) -> None:
        from backend.fastapi.app.legacy_main import _jwt_sign_hs256, _jwt_verify_hs256
        payload = {"sub": "user", "exp": int(time.time()) + 3600}
        token = _jwt_sign_hs256(payload, self.SECRET)
        ok, claims, err = _jwt_verify_hs256(token, self.SECRET)
        assert ok is True

    def test_token_is_three_parts(self) -> None:
        from backend.fastapi.app.legacy_main import _jwt_sign_hs256
        token = _jwt_sign_hs256({"key": "val"}, self.SECRET)
        assert len(token.split(".")) == 3


class TestTotpFunctions:
    def test_secret_is_base32(self) -> None:
        from backend.fastapi.app.legacy_main import _totp_secret
        secret = _totp_secret()
        import base64
        # Should not raise
        base64.b32decode(secret.upper() + "=" * ((8 - len(secret) % 8) % 8))
        assert len(secret) > 0

    def test_code_is_6_digits(self) -> None:
        from backend.fastapi.app.legacy_main import _totp_code, _totp_secret
        secret = _totp_secret()
        code = _totp_code(secret)
        assert len(code) == 6
        assert code.isdigit()

    def test_verify_current_code(self) -> None:
        from backend.fastapi.app.legacy_main import _totp_code, _totp_secret, _totp_verify
        secret = _totp_secret()
        code = _totp_code(secret)
        assert _totp_verify(secret, code) is True

    def test_verify_wrong_code_fails(self) -> None:
        from backend.fastapi.app.legacy_main import _totp_secret, _totp_verify
        secret = _totp_secret()
        assert _totp_verify(secret, "000000") is False

    def test_code_deterministic_for_fixed_time(self) -> None:
        from backend.fastapi.app.legacy_main import _totp_code, _totp_secret
        secret = _totp_secret()
        t = 1000000
        code1 = _totp_code(secret, for_time=t)
        code2 = _totp_code(secret, for_time=t)
        assert code1 == code2

    def test_different_times_may_differ(self) -> None:
        from backend.fastapi.app.legacy_main import _totp_code, _totp_secret
        secret = _totp_secret()
        # Different time windows should produce different codes
        code1 = _totp_code(secret, for_time=0)
        code2 = _totp_code(secret, for_time=1000000)
        # They CAN be the same by coincidence, but usually differ
        # Just verify both are valid 6-digit strings
        assert len(code1) == 6 and len(code2) == 6


class TestIsProduction:
    def test_development_environment(self) -> None:
        from backend.fastapi.app.legacy_main import _is_production
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert _is_production() is False

    def test_production_environment(self) -> None:
        from backend.fastapi.app.legacy_main import _is_production
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            assert _is_production() is True

    def test_case_insensitive(self) -> None:
        from backend.fastapi.app.legacy_main import _is_production
        with patch.dict(os.environ, {"ENVIRONMENT": "PRODUCTION"}):
            assert _is_production() is True


class TestAllowApiDocs:
    def test_development_always_allowed(self) -> None:
        from backend.fastapi.app.legacy_main import _allow_api_docs
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            assert _allow_api_docs() is True

    def test_production_blocked_by_default(self) -> None:
        from backend.fastapi.app.legacy_main import _allow_api_docs
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ENABLE_API_DOCS": "0"}):
            assert _allow_api_docs() is False

    def test_production_enabled_by_env(self) -> None:
        from backend.fastapi.app.legacy_main import _allow_api_docs
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ENABLE_API_DOCS": "true"}):
            assert _allow_api_docs() is True


class TestEnforceRateLimit:
    def test_under_limit_does_not_raise(self) -> None:
        from backend.fastapi.app.legacy_main import _enforce_rate_limit, reset_rate_limits_for_tests
        reset_rate_limits_for_tests()
        # Should not raise for first 5 requests
        for _ in range(5):
            _enforce_rate_limit("test_key_under", 10, 60)

    def test_over_limit_raises(self) -> None:
        from backend.fastapi.app.legacy_main import (
            RateLimitExceededError,
            _enforce_rate_limit,
            reset_rate_limits_for_tests,
        )
        reset_rate_limits_for_tests()
        for _ in range(3):
            _enforce_rate_limit("test_key_over", 3, 60)
        with pytest.raises(RateLimitExceededError):
            _enforce_rate_limit("test_key_over", 3, 60)

    def test_reset_clears_limits(self) -> None:
        from backend.fastapi.app.legacy_main import (
            RateLimitExceededError,
            _enforce_rate_limit,
            reset_rate_limits_for_tests,
        )
        reset_rate_limits_for_tests()
        for _ in range(2):
            _enforce_rate_limit("test_key_reset", 2, 60)
        # Should raise now
        with pytest.raises(RateLimitExceededError):
            _enforce_rate_limit("test_key_reset", 2, 60)
        # After reset, should not raise
        reset_rate_limits_for_tests()
        _enforce_rate_limit("test_key_reset", 2, 60)

    def test_different_keys_independent(self) -> None:
        from backend.fastapi.app.legacy_main import _enforce_rate_limit, reset_rate_limits_for_tests
        reset_rate_limits_for_tests()
        for _ in range(3):
            _enforce_rate_limit("key_a_indep", 3, 60)
        # key_b should be unaffected
        _enforce_rate_limit("key_b_indep", 3, 60)


class TestRateLimitExceededError:
    def test_has_detail_attribute(self) -> None:
        from backend.fastapi.app.legacy_main import RateLimitExceededError
        err = RateLimitExceededError("Too many requests")
        assert err.detail == "Too many requests"
        assert str(err) == "Too many requests"


class TestSendViaProviders:
    """Tests for email provider helpers when not configured."""

    def test_listmonk_not_configured(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_listmonk
        with patch.dict(os.environ, {"LISTMONK_URL": "", "LISTMONK_API_TOKEN": ""}):
            ok, msg = _send_via_listmonk("test@example.com", "Subject", "Body")
            assert ok is False
            assert "not configured" in msg.lower()

    def test_postal_not_configured(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_postal
        with patch.dict(os.environ, {"POSTAL_BASE_URL": "", "POSTAL_API_KEY": ""}):
            ok, msg = _send_via_postal("test@example.com", "Subject", "Body")
            assert ok is False
            assert "not configured" in msg.lower()

    def test_ses_not_configured(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_ses
        with patch.dict(os.environ, {"SES_SMTP_HOST": "", "SES_SMTP_USERNAME": ""}):
            ok, msg = _send_via_ses("test@example.com", "Subject", "Body")
            assert ok is False
            assert "not configured" in msg.lower()

    def test_resend_not_configured(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_resend
        with patch.dict(os.environ, {"RESEND_API_KEY": ""}):
            ok, msg = _send_via_resend("test@example.com", "Subject", "Body")
            assert ok is False
            assert "not configured" in msg.lower()
