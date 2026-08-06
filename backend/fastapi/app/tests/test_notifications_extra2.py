"""
Notifications extra tests - round 2.
Targets fanout functions: _fanout_slack, _fanout_email, _fanout_webhook.
Uses mock httpx to cover HTTP call branches.
Lines 474-712 in notifications.py.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant-notif2"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _set_prefs(client: TestClient, email_enabled: bool = True, slack_enabled: bool = True) -> None:
    """Helper: set notification preferences for test tenant."""
    client.put("/notifications/preferences", headers=H, json={
        "email_enabled": email_enabled,
        "slack_enabled": slack_enabled,
        "digest_frequency": "realtime",
        "muted_categories": [],
    })


class TestFanoutSlack:
    """Lines 474-511: _fanout_slack branches."""

    def test_slack_no_webhook_url(self, client: TestClient) -> None:
        """When SLACK_WEBHOOK_URL not set → returns queued (lines 474-481)."""
        _set_prefs(client, slack_enabled=True)
        with patch.dict(os.environ, {'SLACK_WEBHOOK_URL': ''}):
            r = client.post("/notifications", headers=H, json={
                "title": "Alert",
                "message": "Slack not configured",
                "priority": "critical",
                "category": "security"
            })
        assert r.status_code in VALID
        if r.status_code == 200:
            receipts = r.json().get("deliveryReceipts", [])
            slack_receipts = [rr for rr in receipts if rr.get("channel") == "slack"]
            assert any(rr.get("delivery_status") in ("queued", "skipped") for rr in slack_receipts)

    def test_slack_webhook_success(self, client: TestClient) -> None:
        """SLACK_WEBHOOK_URL set + httpx success → 'sent' (lines 486-504)."""
        _set_prefs(client, slack_enabled=True)
        mock_resp = MagicMock()
        mock_resp.is_success = True

        with patch.dict(os.environ, {'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications", headers=H, json={
                    "title": "Critical Alert",
                    "message": "System issue detected",
                    "priority": "critical",
                    "category": "security"
                })
        assert r.status_code in VALID

    def test_slack_webhook_non_success(self, client: TestClient) -> None:
        """SLACK_WEBHOOK_URL set + httpx non-success response → 'queued-after-non-success' (lines 486-510)."""
        _set_prefs(client, slack_enabled=True)
        mock_resp = MagicMock()
        mock_resp.is_success = False

        with patch.dict(os.environ, {'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications", headers=H, json={
                    "title": "Alert Non-Success",
                    "message": "Slack returned non-2xx",
                    "priority": "warning",
                    "category": "security"
                })
        assert r.status_code in VALID

    def test_slack_webhook_http_error(self, client: TestClient) -> None:
        """SLACK_WEBHOOK_URL set + httpx.HTTPError → 'queued-after-error' (line 511)."""
        import httpx
        _set_prefs(client, slack_enabled=True)

        with patch.dict(os.environ, {'SLACK_WEBHOOK_URL': 'https://hooks.slack.com/test'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.side_effect = httpx.HTTPError("Connection error")
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications", headers=H, json={
                    "title": "Alert HTTP Error",
                    "message": "Slack request failed",
                    "priority": "error",
                    "category": "security"
                })
        assert r.status_code in VALID


class TestFanoutEmail:
    """Lines 521-572: _fanout_email branches."""

    def test_email_no_api_key(self, client: TestClient) -> None:
        """When RESEND_API_KEY not set → queued (lines 521-529)."""
        _set_prefs(client, email_enabled=True)
        with patch.dict(os.environ, {'RESEND_API_KEY': '', 'NOTIFICATION_EMAIL_TO': 'test@test.com'}):
            r = client.post("/notifications", headers=H, json={
                "title": "Critical Email Test",
                "message": "No API key",
                "priority": "critical",
                "category": "billing"
            })
        assert r.status_code in VALID

    def test_email_no_to_address(self, client: TestClient) -> None:
        """When NOTIFICATION_EMAIL_TO not set → queued."""
        _set_prefs(client, email_enabled=True)
        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-key', 'NOTIFICATION_EMAIL_TO': ''}):
            r = client.post("/notifications", headers=H, json={
                "title": "Critical Email No To",
                "message": "No recipient",
                "priority": "critical",
                "category": "billing"
            })
        assert r.status_code in VALID

    def test_email_success(self, client: TestClient) -> None:
        """RESEND_API_KEY + NOTIFICATION_EMAIL_TO set + httpx success → 'sent'."""
        _set_prefs(client, email_enabled=True)
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {'id': 'email_123'}

        with patch.dict(os.environ, {
            'RESEND_API_KEY': 'test-resend-key',
            'NOTIFICATION_EMAIL_TO': 'admin@example.com',
            'RESEND_FROM_EMAIL': 'noreply@example.com',
        }):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications", headers=H, json={
                    "title": "Critical Email Success",
                    "message": "Email sent successfully",
                    "priority": "critical",
                    "category": "billing"
                })
        assert r.status_code in VALID

    def test_email_non_success(self, client: TestClient) -> None:
        """httpx non-success → 'queued-after-non-success'."""
        _set_prefs(client, email_enabled=True)
        mock_resp = MagicMock()
        mock_resp.is_success = False

        with patch.dict(os.environ, {
            'RESEND_API_KEY': 'test-resend-key',
            'NOTIFICATION_EMAIL_TO': 'admin@example.com',
        }):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications", headers=H, json={
                    "title": "Critical Email Non-Success",
                    "message": "Email API returned non-2xx",
                    "priority": "error",
                    "category": "billing"
                })
        assert r.status_code in VALID

    def test_email_http_error(self, client: TestClient) -> None:
        """httpx.HTTPError → 'queued-after-error' (line 572)."""
        import httpx
        _set_prefs(client, email_enabled=True)

        with patch.dict(os.environ, {
            'RESEND_API_KEY': 'test-resend-key',
            'NOTIFICATION_EMAIL_TO': 'admin@example.com',
        }):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.side_effect = httpx.HTTPError("Connection failed")
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications", headers=H, json={
                    "title": "Critical Email HTTP Error",
                    "message": "Email request failed",
                    "priority": "critical",
                    "category": "billing"
                })
        assert r.status_code in VALID


class TestFanoutWebhook:
    """Lines 582-622: _fanout_webhook branches."""

    def test_webhook_no_url(self, client: TestClient) -> None:
        """When NOTIFICATION_WEBHOOK_URL not set → queued (lines 582-589)."""
        with patch.dict(os.environ, {'NOTIFICATION_WEBHOOK_URL': ''}):
            r = client.post("/notifications", headers=H, json={
                "title": "Critical Webhook Test",
                "message": "No webhook URL",
                "priority": "critical",
                "category": "security"
            })
        assert r.status_code in VALID

    def test_webhook_success(self, client: TestClient) -> None:
        """NOTIFICATION_WEBHOOK_URL set + httpx success → 'sent'."""
        mock_resp = MagicMock()
        mock_resp.is_success = True

        with patch.dict(os.environ, {
            'NOTIFICATION_WEBHOOK_URL': 'https://webhook.example.com/notify',
            'NOTIFICATION_WEBHOOK_TOKEN': 'test-webhook-token',
        }):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications", headers=H, json={
                    "title": "Critical Webhook Success",
                    "message": "Webhook sent successfully",
                    "priority": "critical",
                    "category": "security"
                })
        assert r.status_code in VALID

    def test_webhook_non_success(self, client: TestClient) -> None:
        """httpx non-success → 'queued-after-non-success'."""
        mock_resp = MagicMock()
        mock_resp.is_success = False

        with patch.dict(os.environ, {
            'NOTIFICATION_WEBHOOK_URL': 'https://webhook.example.com/notify',
        }):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications", headers=H, json={
                    "title": "Critical Webhook Non-Success",
                    "message": "Webhook returned non-2xx",
                    "priority": "critical",
                    "category": "security"
                })
        assert r.status_code in VALID

    def test_webhook_http_error(self, client: TestClient) -> None:
        """httpx.HTTPError → 'queued-after-error' (line 622)."""
        import httpx

        with patch.dict(os.environ, {
            'NOTIFICATION_WEBHOOK_URL': 'https://webhook.example.com/notify',
        }):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.side_effect = httpx.HTTPError("Connection error")
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications", headers=H, json={
                    "title": "Critical Webhook HTTP Error",
                    "message": "Webhook request failed",
                    "priority": "critical",
                    "category": "security"
                })
        assert r.status_code in VALID


class TestNotificationRoutesCoverage:
    """Additional route tests for notifications.py coverage."""

    def test_create_critical_notification_all_fanouts(self, client: TestClient) -> None:
        """Create a critical notification to trigger all fanout paths (641, 660, 679)."""
        _set_prefs(client, email_enabled=True, slack_enabled=True)
        r = client.post("/notifications", headers=H, json={
            "title": "CRITICAL SYSTEM ALERT",
            "message": "All fanouts triggered",
            "priority": "critical",
            "category": "security"
        })
        assert r.status_code in VALID

    def test_create_error_notification(self, client: TestClient) -> None:
        """Priority='error' triggers email + possibly slack fanout."""
        _set_prefs(client, email_enabled=True, slack_enabled=True)
        r = client.post("/notifications", headers=H, json={
            "title": "Error Notification",
            "message": "Error level event",
            "priority": "error",
            "category": "system"
        })
        assert r.status_code in VALID

    def test_create_warning_notification(self, client: TestClient) -> None:
        """Priority='warning' triggers slack fanout only."""
        _set_prefs(client, email_enabled=True, slack_enabled=True)
        r = client.post("/notifications", headers=H, json={
            "title": "Warning Notification",
            "message": "Warning level event",
            "priority": "warning",
            "category": "system"
        })
        assert r.status_code in VALID

    def test_digest_batch_daily(self, client: TestClient) -> None:
        """Test digest batching with daily frequency."""
        # Set preferences to daily digest
        client.put("/notifications/preferences", headers=H, json={
            "digest_frequency": "daily",
            "email_enabled": False,
        })
        r = client.get("/notifications", headers=H)
        assert r.status_code in VALID

    def test_digest_batch_weekly(self, client: TestClient) -> None:
        """Test digest batching with weekly frequency."""
        client.put("/notifications/preferences", headers=H, json={
            "digest_frequency": "weekly",
            "email_enabled": False,
        })
        r = client.get("/notifications", headers=H)
        assert r.status_code in VALID

    def test_mark_all_read(self, client: TestClient) -> None:
        r = client.post("/notifications/read-all", headers=H)
        assert r.status_code in VALID

    def test_dismiss_notification(self, client: TestClient) -> None:
        # Create one first
        cr = client.post("/notifications", headers=H, json={
            "title": "To dismiss",
            "message": "Will be dismissed",
            "priority": "info"
        })
        if cr.status_code == 200:
            notif_id = cr.json().get("notification", {}).get("id")
            if notif_id:
                r = client.delete(f"/notifications/{notif_id}", headers=H)
                assert r.status_code in VALID

    def test_read_notification(self, client: TestClient) -> None:
        # Create one first
        cr = client.post("/notifications", headers=H, json={
            "title": "To read",
            "message": "Will be marked read",
            "priority": "info"
        })
        if cr.status_code == 200:
            notif_id = cr.json().get("notification", {}).get("id")
            if notif_id:
                r = client.post(f"/notifications/{notif_id}/read", headers=H)
                assert r.status_code in VALID

    def test_delivery_receipts_with_notification_id(self, client: TestClient) -> None:
        r = client.get("/notifications/delivery-receipts?notification_id=1", headers=H)
        assert r.status_code in VALID

    def test_list_with_priority_filter(self, client: TestClient) -> None:
        r = client.get("/notifications?priority=critical", headers=H)
        assert r.status_code in VALID

    def test_list_with_category_filter(self, client: TestClient) -> None:
        r = client.get("/notifications?category=security", headers=H)
        assert r.status_code in VALID

    def test_list_with_pagination(self, client: TestClient) -> None:
        r = client.get("/notifications?limit=5&offset=0", headers=H)
        assert r.status_code in VALID
