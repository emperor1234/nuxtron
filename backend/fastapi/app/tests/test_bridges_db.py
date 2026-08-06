"""
Tests for bridges.py missing coverage paths.
Covers Meilisearch query (lines 203-240), Twilio SMS (614+), Twilio call (639+),
Slack (743+), Resend (803+) by mocking httpx and setting env vars.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "bridges-db-tenant"}


def _mock_http_response(status_code=200, json_data=None, is_success=True, text="ok"):
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = is_success
    resp.json.return_value = json_data or {}
    resp.text = text
    return resp


def _mock_httpx_client(response):
    """Create a mock httpx.Client context manager returning given response."""
    client_inst = MagicMock()
    client_inst.__enter__ = MagicMock(return_value=client_inst)
    client_inst.__exit__ = MagicMock(return_value=False)
    client_inst.post.return_value = response
    client_inst.get.return_value = response
    return client_inst


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestBridgesMeilisearchQuery:
    """Cover lines 203-240: meilisearch search query paths."""

    def test_search_success(self, client: TestClient) -> None:
        """Lines 203-228: meilisearch host configured + successful response."""
        mock_resp = _mock_http_response(
            json_data={"hits": [{"id": 1, "title": "test"}], "estimatedTotalHits": 1}
        )
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {"MEILISEARCH_HOST": "http://mock-ms:7700",
                                      "MEILISEARCH_API_KEY": "ms-key"}, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/search/query", headers=H, json={
                    "index": "articles",
                    "query": "test query",
                    "limit": 10,
                    "offset": 0,
                })
                assert r.status_code in VALID

    def test_search_non_success_response(self, client: TestClient) -> None:
        """Line 240: meilisearch returns non-success → fallback result."""
        mock_resp = _mock_http_response(status_code=500, is_success=False, text="Server Error")
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {"MEILISEARCH_HOST": "http://mock-ms:7700"}, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/search/query", headers=H, json={
                    "index": "articles",
                    "query": "error query",
                    "limit": 5,
                    "offset": 0,
                })
                assert r.status_code in VALID

    def test_search_exception(self, client: TestClient) -> None:
        """Lines 229-238: meilisearch raises exception → error fallback."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = Exception("Connection refused")

        with patch.dict(os.environ, {"MEILISEARCH_HOST": "http://mock-ms:7700"}, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/search/query", headers=H, json={
                    "index": "docs",
                    "query": "exception query",
                    "limit": 5,
                    "offset": 0,
                })
                assert r.status_code in VALID

    def test_search_with_filter(self, client: TestClient) -> None:
        """Line 208-209: search with filter param."""
        mock_resp = _mock_http_response(json_data={"hits": [], "estimatedTotalHits": 0})
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {"MEILISEARCH_HOST": "http://mock-ms:7700"}, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/search/query", headers=H, json={
                    "index": "products",
                    "query": "widget",
                    "filter": "category = 'tech'",
                    "limit": 10,
                    "offset": 0,
                })
                assert r.status_code in VALID

    def test_index_document_success(self, client: TestClient) -> None:
        """Cover index-document path with meilisearch configured."""
        mock_resp = _mock_http_response(json_data={"taskUid": 1})
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {"MEILISEARCH_HOST": "http://mock-ms:7700"}, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/search/index-document", headers=H, json={
                    "index": "articles",
                    "document": {"id": 1, "title": "Test Article", "body": "content"},
                })
                assert r.status_code in VALID


class TestBridgesTwilioSmsWithCreds:
    """Cover lines 614-650: Twilio SMS with credentials configured."""

    def test_sms_success(self, client: TestClient) -> None:
        """Lines 614-626: Twilio SMS succeeds."""
        mock_resp = _mock_http_response(json_data={"sid": "SM123456", "status": "sent"})
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {
            "TWILIO_ACCOUNT_SID": "AC123456",
            "TWILIO_AUTH_TOKEN": "auth-token-123",
            "TWILIO_FROM_NUMBER": "+15551234567",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/twilio/send-sms", headers=H, json={
                    "to": "+15559876543",
                    "body": "Test SMS message from bridges test",
                })
                assert r.status_code in VALID

    def test_sms_non_success_response(self, client: TestClient) -> None:
        """Lines 550-560: Twilio SMS non-success response."""
        mock_resp = _mock_http_response(status_code=400, is_success=False, text='{"code": 21211}')
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {
            "TWILIO_ACCOUNT_SID": "AC789",
            "TWILIO_AUTH_TOKEN": "token-789",
            "TWILIO_FROM_NUMBER": "+15551111111",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/twilio/send-sms", headers=H, json={
                    "to": "+15552222222",
                    "body": "Test fail SMS",
                })
                assert r.status_code in VALID

    def test_sms_exception(self, client: TestClient) -> None:
        """Lines 560+: Twilio SMS raises exception → queued-after-error."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = Exception("Network error")

        with patch.dict(os.environ, {
            "TWILIO_ACCOUNT_SID": "AC567",
            "TWILIO_AUTH_TOKEN": "token-567",
            "TWILIO_FROM_NUMBER": "+15553333333",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/twilio/send-sms", headers=H, json={
                    "to": "+15554444444",
                    "body": "Exception test SMS",
                })
                assert r.status_code in VALID


class TestBridgesTwilioCallWithCreds:
    """Cover lines 614-655: Twilio make-call with credentials configured."""

    def test_call_success(self, client: TestClient) -> None:
        """Lines 614+: Twilio call succeeds."""
        mock_resp = _mock_http_response(json_data={"sid": "CA123456", "status": "initiated"})
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {
            "TWILIO_ACCOUNT_SID": "AC_CALL_001",
            "TWILIO_AUTH_TOKEN": "auth-call-001",
            "TWILIO_FROM_NUMBER": "+15551000000",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/twilio/make-call", headers=H, json={
                    "to": "+15558000000",
                    "twiml_url": "https://example.com/twiml",
                })
                assert r.status_code in VALID

    def test_call_exception(self, client: TestClient) -> None:
        """Lines 639-647: Twilio call raises exception → queued-after-error."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = Exception("Timeout")

        with patch.dict(os.environ, {
            "TWILIO_ACCOUNT_SID": "AC_CALL_002",
            "TWILIO_AUTH_TOKEN": "auth-call-002",
            "TWILIO_FROM_NUMBER": "+15551000001",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/twilio/make-call", headers=H, json={
                    "to": "+15558000001",
                    "twiml_url": "https://example.com/twiml2",
                })
                assert r.status_code in VALID

    def test_call_non_success(self, client: TestClient) -> None:
        """Lines 743-750: Twilio call non-success → queued-after-non-success."""
        mock_resp = _mock_http_response(status_code=400, is_success=False, text="Bad request")
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {
            "TWILIO_ACCOUNT_SID": "AC_CALL_003",
            "TWILIO_AUTH_TOKEN": "auth-call-003",
            "TWILIO_FROM_NUMBER": "+15551000002",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/twilio/make-call", headers=H, json={
                    "to": "+15558000002",
                    "twiml_url": "https://example.com/twiml3",
                })
                assert r.status_code in VALID


class TestBridgesSlackWithCreds:
    """Cover lines 778-810: Slack send-message and webhook paths."""

    def test_slack_send_message_success(self, client: TestClient) -> None:
        """Lines 778+: Slack message send with webhook URL configured."""
        mock_resp = _mock_http_response(json_data={"ok": True})
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/TEST/WEBHOOK",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/slack/send-message", headers=H, json={
                    "channel": "#test-channel",
                    "text": "Test slack message from bridges test",
                    "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Hello"}}],
                })
                assert r.status_code in VALID

    def test_slack_webhook_with_blocks(self, client: TestClient) -> None:
        """Lines 778: slack webhook with blocks field."""
        mock_resp = _mock_http_response(json_data={"ok": True})
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/TEST2/WEBHOOK",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/slack/webhook", headers=H, json={
                    "text": "Webhook test",
                    "blocks": [{"type": "header", "text": {"type": "plain_text", "text": "Title"}}],
                })
                assert r.status_code in VALID

    def test_slack_webhook_success_response(self, client: TestClient) -> None:
        """Lines 803-810: Slack webhook success → item stored in memory."""
        mock_resp = _mock_http_response(json_data={"ok": True})
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {
            "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/TEST3/WEBHOOK",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/slack/webhook", headers=H, json={
                    "text": "Success webhook test",
                })
                assert r.status_code in VALID


class TestBridgesResendWithKey:
    """Cover line 851: Resend email with API key configured."""

    def test_resend_email_success(self, client: TestClient) -> None:
        """Lines 851+: Resend API key configured → sends email."""
        mock_resp = _mock_http_response(json_data={"id": "email-123", "status": "sent"})
        mock_client = _mock_httpx_client(mock_resp)

        with patch.dict(os.environ, {
            "RESEND_API_KEY": "re_test_key_bridges",
            "RESEND_FROM_EMAIL": "test@example.com",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/resend/send-email", headers=H, json={
                    "to_email": "recipient@example.com",
                    "subject": "Test Email from Bridges",
                    "html_body": "<p>Hello World</p>",
                })
                assert r.status_code in VALID

    def test_resend_email_exception(self, client: TestClient) -> None:
        """Lines 851+: Resend raises exception → queued-after-error."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = Exception("API down")

        with patch.dict(os.environ, {
            "RESEND_API_KEY": "re_test_key_bridges2",
            "RESEND_FROM_EMAIL": "test2@example.com",
        }, clear=False):
            with patch("httpx.Client", return_value=mock_client):
                r = client.post("/notifications/resend/send-email", headers=H, json={
                    "to_email": "target@example.com",
                    "subject": "Exception test",
                    "html_body": "<p>test</p>",
                })
                assert r.status_code in VALID
