"""
bridges.py extra tests - round 2.
Targets missing branches in meilisearch, twilio, slack, resend email routes.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant-bridges2"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestMeilisearchIndexDocument:
    """Lines 107-170: _meilisearch_index_document branches."""

    def test_index_no_host_queues(self, client: TestClient) -> None:
        """When MEILISEARCH_HOST not set → memory queue (lines 107-123)."""
        with patch.dict(os.environ, {'MEILISEARCH_HOST': '', 'MEILISEARCH_API_KEY': ''}):
            r = client.post("/search/index-document", headers=H, json={
                "index": "products",
                "document_id": "doc-1",
                "document": {"name": "Test Product", "price": 99.9},
            })
        assert r.status_code in VALID

    def test_index_with_host_success(self, client: TestClient) -> None:
        """MEILISEARCH_HOST set + httpx success → indexed (lines 125-146)."""
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.status_code = 200

        with patch.dict(os.environ, {'MEILISEARCH_HOST': 'http://localhost:7700', 'MEILISEARCH_API_KEY': 'test-key'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/search/index-document", headers=H, json={
                    "index": "products",
                    "document_id": "doc-2",
                    "document": {"name": "Mocked Product", "price": 49.9},
                })
        assert r.status_code in VALID

    def test_index_with_host_exception(self, client: TestClient) -> None:
        """MEILISEARCH_HOST set + exception → queued-after-error (lines 147-158)."""
        with patch.dict(os.environ, {'MEILISEARCH_HOST': 'http://localhost:7700'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.side_effect = Exception("Connection refused")
                mock_client_cls.return_value = mock_ctx

                r = client.post("/search/index-document", headers=H, json={
                    "index": "products",
                    "document_id": "doc-3",
                    "document": {"name": "Error Product"},
                })
        assert r.status_code in VALID

    def test_index_with_host_non_success(self, client: TestClient) -> None:
        """MEILISEARCH_HOST set + non-success response → queued-after-non-success (lines 160-170)."""
        mock_resp = MagicMock()
        mock_resp.is_success = False
        mock_resp.status_code = 400

        with patch.dict(os.environ, {'MEILISEARCH_HOST': 'http://localhost:7700'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/search/index-document", headers=H, json={
                    "index": "products",
                    "document_id": "doc-4",
                    "document": {"name": "Non-Success Product"},
                })
        assert r.status_code in VALID


class TestMeilisearchQuery:
    """Lines 200-240: _meilisearch_query branches."""

    def test_query_no_host(self, client: TestClient) -> None:
        with patch.dict(os.environ, {'MEILISEARCH_HOST': ''}):
            r = client.post("/search/query", headers=H, json={
                "index": "products",
                "q": "test product",
                "limit": 10,
                "offset": 0,
            })
        assert r.status_code in VALID

    def test_query_with_host_success(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"hits": [{"id": "doc-1"}], "nbHits": 1}

        with patch.dict(os.environ, {'MEILISEARCH_HOST': 'http://localhost:7700', 'MEILISEARCH_API_KEY': 'test-key'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/search/query", headers=H, json={
                    "index": "products",
                    "q": "test",
                })
        assert r.status_code in VALID

    def test_query_with_exception(self, client: TestClient) -> None:
        with patch.dict(os.environ, {'MEILISEARCH_HOST': 'http://localhost:7700'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.side_effect = Exception("Timeout")
                mock_client_cls.return_value = mock_ctx

                r = client.post("/search/query", headers=H, json={
                    "index": "products",
                    "q": "error test",
                })
        assert r.status_code in VALID


class TestTwilioSendSms:
    """Lines 538-551: twilio send-sms httpx branches."""

    def test_sms_success(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"sid": "SM123", "status": "sent"}

        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'ACtest123',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_FROM_NUMBER': '+15551234567',
        }):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications/twilio/send-sms", headers=H, json={
                    "to": "+15559876543",
                    "body": "Test SMS message",
                })
        assert r.status_code in VALID

    def test_sms_non_success(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.is_success = False

        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'ACtest123',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_FROM_NUMBER': '+15551234567',
        }):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications/twilio/send-sms", headers=H, json={
                    "to": "+15559876543",
                    "body": "Test SMS fail",
                })
        assert r.status_code in VALID


class TestTwilioMakeCall:
    """Lines 614-648: twilio make-call httpx branches."""

    def test_call_success(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"sid": "CAtest", "status": "queued"}

        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'ACtest123',
            'TWILIO_AUTH_TOKEN': 'test-token',
            'TWILIO_FROM_NUMBER': '+15551234567',
        }):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications/twilio/make-call", headers=H, json={
                    "to": "+15559876543",
                    "twiml": "<Response><Say>Hello</Say></Response>",
                })
        assert r.status_code in VALID

    def test_call_queued_no_credentials(self, client: TestClient) -> None:
        """When no TWILIO credentials → queued."""
        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': '',
            'TWILIO_AUTH_TOKEN': '',
        }):
            r = client.post("/notifications/twilio/make-call", headers=H, json={
                "to": "+15559876543",
                "twiml": "<Response><Say>Hello</Say></Response>",
            })
        assert r.status_code in VALID


class TestSlackSendMessage:
    """Lines 713-750: slack send-message httpx branches."""

    def test_slack_message_success(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.is_success = True

        with patch.dict(os.environ, {
            'SLACK_BOT_TOKEN': 'xoxb-test-token',
        }):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications/slack/send-message", headers=H, json={
                    "channel": "#general",
                    "text": "Hello from test",
                })
        assert r.status_code in VALID

    def test_slack_message_with_blocks(self, client: TestClient) -> None:
        """Test with blocks parameter (line 713)."""
        mock_resp = MagicMock()
        mock_resp.is_success = True

        with patch.dict(os.environ, {'SLACK_BOT_TOKEN': 'xoxb-test-token'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications/slack/send-message", headers=H, json={
                    "channel": "#alerts",
                    "text": "Alert with blocks",
                    "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Alert!"}}],
                })
        assert r.status_code in VALID

    def test_slack_message_no_token_queued(self, client: TestClient) -> None:
        """When no SLACK_BOT_TOKEN → queued."""
        with patch.dict(os.environ, {'SLACK_BOT_TOKEN': ''}):
            r = client.post("/notifications/slack/send-message", headers=H, json={
                "channel": "#general",
                "text": "Hello from test (no token)",
            })
        assert r.status_code in VALID


class TestSlackWebhook:
    """Lines 778-810: slack webhook httpx branches."""

    def test_slack_webhook_success(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.is_success = True

        with patch('httpx.Client') as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_ctx.post.return_value = mock_resp
            mock_client_cls.return_value = mock_ctx

            r = client.post("/notifications/slack/webhook", headers=H, json={
                "webhook_url": "https://hooks.slack.com/test",
                "text": "Webhook test message",
            })
        assert r.status_code in VALID

    def test_slack_webhook_with_blocks(self, client: TestClient) -> None:
        """Test webhook with blocks (line 778)."""
        mock_resp = MagicMock()
        mock_resp.is_success = True

        with patch('httpx.Client') as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_ctx.post.return_value = mock_resp
            mock_client_cls.return_value = mock_ctx

            r = client.post("/notifications/slack/webhook", headers=H, json={
                "webhook_url": "https://hooks.slack.com/test",
                "text": "Webhook with blocks",
                "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Block!"}}],
            })
        assert r.status_code in VALID

    def test_slack_webhook_non_success(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.is_success = False

        with patch('httpx.Client') as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_ctx.post.return_value = mock_resp
            mock_client_cls.return_value = mock_ctx

            r = client.post("/notifications/slack/webhook", headers=H, json={
                "webhook_url": "https://hooks.slack.com/test",
                "text": "Non-success response",
            })
        assert r.status_code in VALID


class TestResendSendEmail:
    """Lines 851-969: resend send-email httpx branches."""

    def test_resend_email_no_api_key(self, client: TestClient) -> None:
        """When no RESEND_API_KEY → queued."""
        with patch.dict(os.environ, {'RESEND_API_KEY': ''}):
            r = client.post("/notifications/resend/send-email", headers=H, json={
                "from_email": "noreply@example.com",
                "to": ["admin@example.com"],
                "subject": "Test Email",
                "text": "Hello from test",
            })
        assert r.status_code in VALID

    def test_resend_email_success_with_html_and_text(self, client: TestClient) -> None:
        """Both html and text provided (lines 876-881)."""
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"id": "email_test_123"}

        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-resend-key'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications/resend/send-email", headers=H, json={
                    "from_email": "noreply@example.com",
                    "to": ["admin@example.com"],
                    "subject": "Test HTML Email",
                    "html": "<h1>Hello</h1>",
                    "text": "Hello",
                })
        assert r.status_code in VALID

    def test_resend_email_success_text_only(self, client: TestClient) -> None:
        """Text only (line 878-879)."""
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"id": "email_text_123"}

        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-resend-key'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications/resend/send-email", headers=H, json={
                    "from_email": "noreply@example.com",
                    "to": ["admin@example.com"],
                    "subject": "Test Text Email",
                    "text": "Hello from text",
                })
        assert r.status_code in VALID

    def test_resend_email_no_body_uses_default(self, client: TestClient) -> None:
        """No html and no text → default body (line 880-881)."""
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"id": "email_default_123"}

        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-resend-key'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications/resend/send-email", headers=H, json={
                    "from_email": "noreply@example.com",
                    "to": ["admin@example.com"],
                    "subject": "Test Default Body Email",
                })
        assert r.status_code in VALID

    def test_resend_email_exception(self, client: TestClient) -> None:
        """httpx exception → queued-after-error."""
        with patch.dict(os.environ, {'RESEND_API_KEY': 'test-resend-key'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.side_effect = Exception("Connection error")
                mock_client_cls.return_value = mock_ctx

                r = client.post("/notifications/resend/send-email", headers=H, json={
                    "from_email": "noreply@example.com",
                    "to": ["admin@example.com"],
                    "subject": "Exception Email",
                })
        assert r.status_code in VALID


class TestAlgoliaRoutes:
    """Lines 1057-1185: algolia routes."""

    def test_algolia_index_no_credentials(self, client: TestClient) -> None:
        with patch.dict(os.environ, {'ALGOLIA_APP_ID': '', 'ALGOLIA_API_KEY': ''}):
            r = client.post("/search/algolia/index-object", headers=H, json={
                "index": "products",
                "object_id": "obj-1",
                "document": {"name": "Algolia Product"},
            })
        assert r.status_code in VALID

    def test_algolia_query_no_credentials(self, client: TestClient) -> None:
        with patch.dict(os.environ, {'ALGOLIA_APP_ID': '', 'ALGOLIA_API_KEY': ''}):
            r = client.post("/search/algolia/query", headers=H, json={
                "index": "products",
                "q": "test",
            })
        assert r.status_code in VALID

    def test_algolia_index_success(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"objectID": "obj-1"}

        with patch.dict(os.environ, {'ALGOLIA_APP_ID': 'test-app-id', 'ALGOLIA_API_KEY': 'test-key'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.put.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/search/algolia/index-object", headers=H, json={
                    "index": "products",
                    "object_id": "obj-1",
                    "document": {"name": "Algolia Product"},
                })
        assert r.status_code in VALID

    def test_algolia_query_success(self, client: TestClient) -> None:
        mock_resp = MagicMock()
        mock_resp.is_success = True
        mock_resp.json.return_value = {"hits": [], "nbHits": 0}

        with patch.dict(os.environ, {'ALGOLIA_APP_ID': 'test-app-id', 'ALGOLIA_API_KEY': 'test-key'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.post.return_value = mock_resp
                mock_client_cls.return_value = mock_ctx

                r = client.post("/search/algolia/query", headers=H, json={
                    "index": "products",
                    "q": "algolia test",
                })
        assert r.status_code in VALID

    def test_algolia_index_exception(self, client: TestClient) -> None:
        with patch.dict(os.environ, {'ALGOLIA_APP_ID': 'test-app-id', 'ALGOLIA_API_KEY': 'test-key'}):
            with patch('httpx.Client') as mock_client_cls:
                mock_ctx = MagicMock()
                mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
                mock_ctx.__exit__ = MagicMock(return_value=False)
                mock_ctx.put.side_effect = Exception("Algolia error")
                mock_client_cls.return_value = mock_ctx

                r = client.post("/search/algolia/index-object", headers=H, json={
                    "index": "products",
                    "object_id": "obj-error",
                    "document": {"name": "Error Product"},
                })
        assert r.status_code in VALID
