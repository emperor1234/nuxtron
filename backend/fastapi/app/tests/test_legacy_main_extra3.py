"""
Tests for missing branches in legacy_main.py:
- _allowed_hosts/_cors_origins production raises
- _jwt_verify_hs256 invalid payload type
- _send_via_listmonk success and API-error paths
- _send_via_postal success and API-error paths
- _send_via_ses port 465 and non-465 paths
- _send_via_resend success and API-error paths
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")


class TestAllowedHostsProductionRaise:
    """Line 343: raise RuntimeError in production when ALLOWED_HOSTS not set."""

    def test_raises_in_production_with_no_hosts(self) -> None:
        import pytest
        from backend.fastapi.app.legacy_main import _allowed_hosts
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "ALLOWED_HOSTS": ""}, clear=False):
            with pytest.raises(RuntimeError, match="ALLOWED_HOSTS"):
                _allowed_hosts()


class TestCorsOriginsProductionRaise:
    """Line 352: raise RuntimeError in production when CORS_ORIGINS not set."""

    def test_raises_in_production_with_no_origins(self) -> None:
        import pytest
        from backend.fastapi.app.legacy_main import _cors_origins
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "CORS_ORIGINS": ""}, clear=False):
            with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
                _cors_origins()


class TestJwtVerifyInvalidPayloadType:
    """Line 406: invalid token payload (JSON but not a dict)."""

    SECRET = "test-jwt-secret"

    def test_verify_invalid_payload_type_array(self) -> None:
        """JWT whose payload is a valid JSON array (not a dict) → invalid payload."""
        import hashlib
        import hmac
        import json

        from backend.fastapi.app.legacy_main import _b64url_encode, _jwt_verify_hs256

        # Build a token with array payload
        header = {"alg": "HS256", "typ": "JWT"}
        head = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        body = _b64url_encode(json.dumps(["item1", "item2"]).encode("utf-8"))  # array!
        signing_input = f"{head}.{body}".encode("ascii")
        signature = hmac.new(self.SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
        sig = _b64url_encode(signature)
        token = f"{head}.{body}.{sig}"

        ok, claims, err = _jwt_verify_hs256(token, self.SECRET)
        assert ok is False
        assert err is not None
        assert "invalid" in (err or "").lower() or "payload" in (err or "").lower()


class TestSendViaListmonkSuccessPath:
    """Lines 460-462: Listmonk success and error response paths."""

    def _make_mock_response(self, is_success: bool, status_code: int = 200) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.is_success = is_success
        mock_resp.status_code = status_code
        return mock_resp

    def test_success_path(self) -> None:
        """Line 460: response.is_success → True, return success tuple."""
        from backend.fastapi.app.legacy_main import _send_via_listmonk
        with patch.dict(os.environ, {
            "LISTMONK_URL": "https://listmonk.example.com",
            "LISTMONK_API_TOKEN": "test-token",
        }, clear=False):
            with patch("httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_client.post.return_value = self._make_mock_response(is_success=True)
                ok, msg = _send_via_listmonk("user@example.com", "Hello", "Body text")
                assert ok is True
                assert "listmonk" in msg.lower() or "delivered" in msg.lower()

    def test_api_error_path(self) -> None:
        """Line 461: response.is_success → False, return error tuple."""
        from backend.fastapi.app.legacy_main import _send_via_listmonk
        with patch.dict(os.environ, {
            "LISTMONK_URL": "https://listmonk.example.com",
            "LISTMONK_API_TOKEN": "test-token",
        }, clear=False):
            with patch("httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_client.post.return_value = self._make_mock_response(is_success=False, status_code=500)
                ok, msg = _send_via_listmonk("user@example.com", "Hello", "Body text")
                assert ok is False
                assert "500" in msg or "error" in msg.lower()


class TestSendViaPostalSuccessPath:
    """Lines 488-490: Postal success and error response paths."""

    def _make_mock_response(self, is_success: bool, status_code: int = 200) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.is_success = is_success
        mock_resp.status_code = status_code
        return mock_resp

    def test_success_path(self) -> None:
        """Line 488: response.is_success → True."""
        from backend.fastapi.app.legacy_main import _send_via_postal
        with patch.dict(os.environ, {
            "POSTAL_BASE_URL": "https://postal.example.com",
            "POSTAL_API_KEY": "postal-key",
            "POSTAL_FROM_EMAIL": "noreply@example.com",
        }, clear=False):
            with patch("httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_client.post.return_value = self._make_mock_response(is_success=True)
                ok, msg = _send_via_postal("user@example.com", "Hello", "Body text")
                assert ok is True
                assert "postal" in msg.lower() or "delivered" in msg.lower()

    def test_api_error_path(self) -> None:
        """Line 489: response.is_success → False."""
        from backend.fastapi.app.legacy_main import _send_via_postal
        with patch.dict(os.environ, {
            "POSTAL_BASE_URL": "https://postal.example.com",
            "POSTAL_API_KEY": "postal-key",
        }, clear=False):
            with patch("httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_client.post.return_value = self._make_mock_response(is_success=False, status_code=503)
                ok, msg = _send_via_postal("user@example.com", "Hello", "Body text")
                assert ok is False
                assert "503" in msg or "error" in msg.lower()


class TestSendViaSesSmtpPaths:
    """Lines 516-524: SES SMTP port 465 (SMTP_SSL) and non-465 paths."""

    def test_port_465_ssl_success(self) -> None:
        """Line 516-518: uses SMTP_SSL for port 465."""
        from backend.fastapi.app.legacy_main import _send_via_ses
        with patch.dict(os.environ, {
            "SES_SMTP_HOST": "smtp.example.com",
            "SES_SMTP_PORT": "465",
            "SES_SMTP_USERNAME": "smtp_user",
            "SES_SMTP_PASSWORD": "smtp_pass",
        }, clear=False):
            with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
                mock_server = MagicMock()
                mock_smtp_ssl.return_value.__enter__.return_value = mock_server
                ok, msg = _send_via_ses("user@example.com", "Subject", "Body")
                assert ok is True
                assert "delivered" in msg.lower() or "ses" in msg.lower()

    def test_port_587_starttls_success(self) -> None:
        """Lines 522-524: uses SMTP + starttls for port 587."""
        from backend.fastapi.app.legacy_main import _send_via_ses
        with patch.dict(os.environ, {
            "SES_SMTP_HOST": "smtp.example.com",
            "SES_SMTP_PORT": "587",
            "SES_SMTP_USERNAME": "smtp_user",
            "SES_SMTP_PASSWORD": "smtp_pass",
        }, clear=False):
            with patch("smtplib.SMTP") as mock_smtp:
                mock_server = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_server
                ok, msg = _send_via_ses("user@example.com", "Subject", "Body")
                assert ok is True
                assert "delivered" in msg.lower() or "ses" in msg.lower()

    def test_port_465_ssl_failure(self) -> None:
        """SMTP_SSL raises an exception."""
        from backend.fastapi.app.legacy_main import _send_via_ses
        with patch.dict(os.environ, {
            "SES_SMTP_HOST": "smtp.example.com",
            "SES_SMTP_PORT": "465",
            "SES_SMTP_USERNAME": "smtp_user",
            "SES_SMTP_PASSWORD": "smtp_pass",
        }, clear=False):
            with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
                mock_smtp_ssl.side_effect = Exception("SSL handshake failed")
                ok, msg = _send_via_ses("user@example.com", "Subject", "Body")
                assert ok is False
                assert "failed" in msg.lower() or "error" in msg.lower()


class TestSendViaResendSuccessPath:
    """Lines 553-555: Resend success and error response paths."""

    def _make_mock_response(self, is_success: bool, status_code: int = 200) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.is_success = is_success
        mock_resp.status_code = status_code
        return mock_resp

    def test_success_path(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_resend
        with patch.dict(os.environ, {
            "RESEND_API_KEY": "re_test_key",
            "RESEND_FROM_EMAIL": "noreply@example.com",
        }, clear=False):
            with patch("httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_client.post.return_value = self._make_mock_response(is_success=True)
                ok, msg = _send_via_resend("user@example.com", "Hello", "Body")
                assert ok is True
                assert "resend" in msg.lower() or "delivered" in msg.lower()

    def test_api_error_path(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_resend
        with patch.dict(os.environ, {
            "RESEND_API_KEY": "re_test_key",
            "RESEND_FROM_EMAIL": "noreply@example.com",
        }, clear=False):
            with patch("httpx.Client") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value.__enter__.return_value = mock_client
                mock_client.post.return_value = self._make_mock_response(is_success=False, status_code=422)
                ok, msg = _send_via_resend("user@example.com", "Hello", "Body")
                assert ok is False
                assert "422" in msg or "error" in msg.lower()
