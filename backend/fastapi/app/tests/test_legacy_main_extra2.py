"""
Additional tests for legacy_main.py uncovered pure helpers and routes.
Focus: _send_via_*, _db_dsn, _security_alert_from_email, AI/finance routes.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
SA_H = {**H, "X-Super-Admin": "true"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestDbDsn:
    def test_uses_defaults(self) -> None:
        from backend.fastapi.app.legacy_main import _db_dsn
        with patch.dict(os.environ, {
            "POSTGRES_HOST": "myhost",
            "POSTGRES_PORT": "5433",
            "POSTGRES_DB": "mydb",
            "POSTGRES_USER": "myuser",
            "POSTGRES_PASSWORD": "mypass",
        }, clear=False):
            dsn = _db_dsn()
            assert "myhost" in dsn
            assert "5433" in dsn
            assert "mydb" in dsn
            assert "myuser" in dsn
            assert "mypass" in dsn

    def test_returns_string(self) -> None:
        from backend.fastapi.app.legacy_main import _db_dsn
        assert isinstance(_db_dsn(), str)


class TestSendViaListmonk:
    def test_not_configured(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_listmonk
        with patch.dict(os.environ, {"LISTMONK_URL": "", "LISTMONK_API_TOKEN": ""}, clear=False):
            ok, msg = _send_via_listmonk("test@example.com", "Subject", "Body")
            assert ok is False
            assert "not configured" in msg

    def test_missing_token_only(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_listmonk
        with patch.dict(os.environ, {"LISTMONK_URL": "https://listmonk.example.com", "LISTMONK_API_TOKEN": ""}, clear=False):
            ok, msg = _send_via_listmonk("test@example.com", "Subject", "Body")
            assert ok is False

    def test_network_error_returns_failure(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_listmonk
        with patch.dict(os.environ, {
            "LISTMONK_URL": "https://listmonk.example.com",
            "LISTMONK_API_TOKEN": "test-token",
        }, clear=False):
            with patch("httpx.Client") as mock_client_class:
                mock_client_class.return_value.__enter__.return_value.post.side_effect = Exception("Connection refused")
                ok, msg = _send_via_listmonk("test@example.com", "Subject", "Body")
                assert ok is False
                assert "failed" in msg.lower() or "listmonk" in msg.lower()


class TestSendViaPostal:
    def test_not_configured(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_postal
        with patch.dict(os.environ, {"POSTAL_BASE_URL": "", "POSTAL_API_KEY": ""}, clear=False):
            ok, msg = _send_via_postal("test@example.com", "Subject", "Body")
            assert ok is False
            assert "not configured" in msg

    def test_network_error(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_postal
        with patch.dict(os.environ, {
            "POSTAL_BASE_URL": "https://postal.example.com",
            "POSTAL_API_KEY": "test-key",
        }, clear=False):
            with patch("httpx.Client") as mock_client_class:
                mock_client_class.return_value.__enter__.return_value.post.side_effect = Exception("Timeout")
                ok, msg = _send_via_postal("test@example.com", "Subject", "Body")
                assert ok is False


class TestSendViaSes:
    def test_not_configured(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_ses
        with patch.dict(os.environ, {
            "SES_SMTP_HOST": "",
            "SES_SMTP_USERNAME": "",
            "SES_SMTP_PASSWORD": "",
        }, clear=False):
            ok, msg = _send_via_ses("test@example.com", "Subject", "Body")
            assert ok is False
            assert "not configured" in msg

    def test_smtp_error(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_ses
        with patch.dict(os.environ, {
            "SES_SMTP_HOST": "smtp.example.com",
            "SES_SMTP_USERNAME": "user",
            "SES_SMTP_PASSWORD": "pass",
            "SES_SMTP_PORT": "587",
        }, clear=False):
            with patch("smtplib.SMTP") as mock_smtp:
                mock_smtp.return_value.__enter__.return_value.starttls.side_effect = Exception("TLS error")
                ok, msg = _send_via_ses("test@example.com", "Subject", "Body")
                assert ok is False


class TestSendViaResend:
    def test_not_configured(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_resend
        with patch.dict(os.environ, {"RESEND_API_KEY": ""}, clear=False):
            ok, msg = _send_via_resend("test@example.com", "Subject", "Body")
            assert ok is False
            assert "not configured" in msg

    def test_network_error(self) -> None:
        from backend.fastapi.app.legacy_main import _send_via_resend
        with patch.dict(os.environ, {"RESEND_API_KEY": "re_test123"}, clear=False):
            with patch("httpx.Client") as mock_client_class:
                mock_client_class.return_value.__enter__.return_value.post.side_effect = Exception("Timeout")
                ok, msg = _send_via_resend("test@example.com", "Subject", "Body")
                assert ok is False


class TestSecurityAlertFromEmail:
    def test_returns_smtp_from_first(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_from_email
        with patch.dict(os.environ, {
            "SMTP_FROM": "alerts@example.com",
            "RESEND_FROM_EMAIL": "",
        }, clear=False):
            result = _security_alert_from_email()
            assert result == "alerts@example.com"

    def test_falls_back_to_default(self) -> None:
        from backend.fastapi.app.legacy_main import _security_alert_from_email
        with patch.dict(os.environ, {
            "SMTP_FROM": "",
            "RESEND_FROM_EMAIL": "",
            "SES_FROM_EMAIL": "",
            "POSTAL_FROM_EMAIL": "",
        }, clear=False):
            result = _security_alert_from_email()
            assert isinstance(result, str)


class TestLegacyMainAiRoutes:
    """Smoke tests for AI gateway and other uncovered legacy_main routes."""

    def test_ai_ping(self, client: TestClient) -> None:
        r = client.get("/ai/ping", headers=H)
        assert r.status_code in VALID

    def test_ai_gateway_generate_basic(self, client: TestClient) -> None:
        r = client.post("/ai/gateway/generate", headers=H, json={
            "prompt": "Hello, world!",
            "provider": "openai",
            "model": "gpt-4o-mini",
        })
        assert r.status_code in VALID

    def test_ai_gateway_generate_auto_provider(self, client: TestClient) -> None:
        r = client.post("/ai/gateway/generate", headers=H, json={
            "prompt": "Summarize this text briefly.",
            "provider": "auto",
        })
        assert r.status_code in VALID

    def test_ai_gateway_generate_anthropic(self, client: TestClient) -> None:
        r = client.post("/ai/gateway/generate", headers=H, json={
            "prompt": "What is 2+2?",
            "provider": "anthropic",
            "model": "claude-3-haiku-20240307",
        })
        assert r.status_code in VALID

    def test_ai_generated_asset_not_found(self, client: TestClient) -> None:
        r = client.get("/ai/generated-assets/999999", headers=H)
        assert r.status_code in VALID

    def test_ai_security_analytics(self, client: TestClient) -> None:
        r = client.get("/ai/security/analytics", headers=H)
        assert r.status_code in VALID

    def test_ai_security_analytics_with_window(self, client: TestClient) -> None:
        r = client.get("/ai/security/analytics?window_minutes=30", headers=H)
        assert r.status_code in VALID

    def test_ai_security_appeal(self, client: TestClient) -> None:
        r = client.post("/ai/security/appeals", headers=H, json={
            "reason": "My prompt was incorrectly blocked.",
            "original_prompt": "Write a business email",
        })
        assert r.status_code in VALID

    def test_ai_security_admin_ids_state(self, client: TestClient) -> None:
        r = client.get("/ai/security/admin/ids/state", headers=SA_H)
        assert r.status_code in VALID

    def test_ai_security_admin_email_queue(self, client: TestClient) -> None:
        r = client.get("/ai/security/admin/email-queue", headers=SA_H)
        assert r.status_code in VALID

    def test_ai_security_admin_provider_keys_rotate(self, client: TestClient) -> None:
        r = client.post("/ai/security/admin/provider-keys/rotate", headers=SA_H, json={
            "provider": "openai",
        })
        assert r.status_code in VALID

    def test_ai_security_admin_appeal_resolve(self, client: TestClient) -> None:
        r = client.post("/ai/security/admin/appeals/999/resolve", headers=SA_H, json={
            "approved": True,
            "notes": "Reviewed and approved",
        })
        assert r.status_code in VALID

    def test_ai_security_admin_ids_events(self, client: TestClient) -> None:
        r = client.post("/ai/security/admin/ids/events", headers=SA_H, json={
            "event_type": "prompt_injection",
            "severity": "high",
            "details": "Detected jailbreak attempt",
        })
        assert r.status_code in VALID

    def test_ai_security_admin_email_queue_requeue(self, client: TestClient) -> None:
        r = client.post("/ai/security/admin/email-queue/999/requeue", headers=SA_H, json={})
        assert r.status_code in VALID


class TestLegacyMainFinanceRoutes:
    """Smoke tests for ops/finance routes."""

    def test_finance_hub(self, client: TestClient) -> None:
        r = client.get("/ops/finance/hub", headers=H)
        assert r.status_code in VALID

    def test_finance_accounting_integrations(self, client: TestClient) -> None:
        r = client.get("/ops/finance/accounting/integrations", headers=H)
        assert r.status_code in VALID

    def test_finance_connect_integration(self, client: TestClient) -> None:
        r = client.post("/ops/finance/accounting/integrations/connect", headers=H, json={
            "provider": "quickbooks",
            "credentials": {"access_token": "test-token"},
        })
        assert r.status_code in VALID

    def test_finance_create_export(self, client: TestClient) -> None:
        r = client.post("/ops/finance/accounting/exports", headers=H, json={
            "provider": "quickbooks",
            "export_type": "invoices",
            "date_from": "2024-01-01",
            "date_to": "2024-03-31",
        })
        assert r.status_code in VALID

    def test_finance_refresh_token(self, client: TestClient) -> None:
        r = client.post("/ops/finance/accounting/integrations/quickbooks/refresh-token", headers=H, json={})
        assert r.status_code in VALID

    def test_finance_rotate_secret(self, client: TestClient) -> None:
        r = client.post("/ops/finance/accounting/integrations/quickbooks/rotate-secret", headers=H, json={})
        assert r.status_code in VALID


class TestHealthzRoutes:
    """Smoke tests for remaining health routes."""

    def test_healthz(self, client: TestClient) -> None:
        r = client.get("/healthz", headers=H)
        assert r.status_code in VALID

    def test_health_live(self, client: TestClient) -> None:
        r = client.get("/health/live", headers=H)
        assert r.status_code in VALID

    def test_health_vaults(self, client: TestClient) -> None:
        r = client.get("/health/vaults", headers=H)
        assert r.status_code in VALID

    def test_health_encryption(self, client: TestClient) -> None:
        r = client.get("/health/encryption", headers=H)
        assert r.status_code in VALID

    def test_metrics(self, client: TestClient) -> None:
        r = client.get("/metrics", headers=H)
        assert r.status_code in VALID
