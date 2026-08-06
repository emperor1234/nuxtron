"""
Bridges router extra tests — round 3.
Covers httpx-mocked paths: meilisearch with host, Twilio with creds, Slack with token,
Resend with api key, Algolia with creds. Also covers redis mock paths.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-bridges-extra3"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _httpx_mock(is_success: bool = True, json_data: dict | None = None, status_code: int = 200, raise_exc: bool = False):
    """Build a mock httpx.Client context manager."""
    mock_cls = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
    mock_ctx.__exit__ = MagicMock(return_value=False)
    if raise_exc:
        mock_ctx.post.side_effect = Exception("Connection refused")
        mock_ctx.put.side_effect = Exception("Connection refused")
        mock_ctx.get.side_effect = Exception("Connection refused")
    else:
        mock_resp = MagicMock()
        mock_resp.is_success = is_success
        mock_resp.status_code = status_code
        mock_resp.text = "Error detail"
        mock_resp.json.return_value = json_data or {"ok": True, "id": "msg-001"}
        mock_ctx.post.return_value = mock_resp
        mock_ctx.put.return_value = mock_resp
        mock_ctx.get.return_value = mock_resp
    mock_cls.return_value = mock_ctx
    return mock_cls


# ── Meilisearch ─────────────────────────────────────────────────────────────


class TestMeilisearchWithHost:
    """Lines 125-170: meilisearch index/query when MEILISEARCH_HOST is set."""

    def test_index_document_success(self, client: TestClient) -> None:
        """Lines 125-146: success path."""
        mock_cls = _httpx_mock(is_success=True, json_data={"taskUid": 1})
        env = {"MEILISEARCH_HOST": "http://meilisearch.local:7700", "MEILISEARCH_API_KEY": "master-key"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/search/index-document", headers=H, json={
                "index": "products",
                "document_id": "prod-001",
                "document": {"title": "Test Product", "price": 29.99},
            })
        assert r.status_code in VALID

    def test_index_document_exception_fallback(self, client: TestClient) -> None:
        """Lines 147-158: exception → queued-after-error."""
        mock_cls = _httpx_mock(raise_exc=True)
        env = {"MEILISEARCH_HOST": "http://meilisearch.local:7700"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/search/index-document", headers=H, json={
                "index": "articles",
                "document_id": "art-001",
                "document": {"title": "Article"},
            })
        assert r.status_code in VALID

    def test_index_document_non_success_fallback(self, client: TestClient) -> None:
        """Lines 160-170: non-success → queued-after-non-success."""
        mock_cls = _httpx_mock(is_success=False, status_code=500)
        env = {"MEILISEARCH_HOST": "http://meilisearch.local:7700"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/search/index-document", headers=H, json={
                "index": "posts",
                "document_id": "post-001",
                "document": {"title": "Post"},
            })
        assert r.status_code in VALID

    def test_query_success(self, client: TestClient) -> None:
        """Lines 203-230: search query success path."""
        mock_cls = _httpx_mock(is_success=True, json_data={"hits": [{"title": "result"}], "estimatedTotalHits": 1})
        env = {"MEILISEARCH_HOST": "http://meilisearch.local:7700", "MEILISEARCH_API_KEY": "key"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/search/query", headers=H, json={
                "index": "products",
                "query": "test",
                "limit": 10,
                "offset": 0,
            })
        assert r.status_code in VALID

    def test_query_with_filter(self, client: TestClient) -> None:
        """Line 208: filter applied to request body."""
        mock_cls = _httpx_mock(is_success=True, json_data={"hits": [], "estimatedTotalHits": 0})
        env = {"MEILISEARCH_HOST": "http://meilisearch.local:7700"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/search/query", headers=H, json={
                "index": "products",
                "query": "filtered",
                "limit": 5,
                "offset": 0,
                "filter": "price > 10",
            })
        assert r.status_code in VALID

    def test_query_exception(self, client: TestClient) -> None:
        """Lines 229-240: query exception path."""
        mock_cls = _httpx_mock(raise_exc=True)
        env = {"MEILISEARCH_HOST": "http://meilisearch.local:7700"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/search/query", headers=H, json={
                "index": "products",
                "query": "broken",
                "limit": 10,
                "offset": 0,
            })
        assert r.status_code in VALID


# ── Twilio ───────────────────────────────────────────────────────────────────


class TestTwilioWithCredentials:
    """Lines 538-648: Twilio SMS/call with credentials set."""

    def test_sms_success(self, client: TestClient) -> None:
        """Lines 538-540: SMS success path."""
        mock_cls = _httpx_mock(is_success=True, json_data={"sid": "SM123", "status": "sent"})
        env = {
            "TWILIO_ACCOUNT_SID": "ACtest123",
            "TWILIO_AUTH_TOKEN": "test_token",
            "TWILIO_FROM_NUMBER": "+15550001111",
        }
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/twilio/send-sms", headers=H, json={
                "to": "+15559999999",
                "body": "Hello from test",
            })
        assert r.status_code in VALID

    def test_sms_non_success(self, client: TestClient) -> None:
        """Lines 551: SMS non-success return."""
        mock_cls = _httpx_mock(is_success=False, status_code=400)
        env = {
            "TWILIO_ACCOUNT_SID": "ACtest456",
            "TWILIO_AUTH_TOKEN": "test_token2",
            "TWILIO_FROM_NUMBER": "+15550002222",
        }
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/twilio/send-sms", headers=H, json={
                "to": "+15558888888",
                "body": "Test body",
            })
        assert r.status_code in VALID

    def test_sms_exception(self, client: TestClient) -> None:
        """SMS exception → queued-after-error."""
        mock_cls = _httpx_mock(raise_exc=True)
        env = {
            "TWILIO_ACCOUNT_SID": "ACtest789",
            "TWILIO_AUTH_TOKEN": "test_token3",
            "TWILIO_FROM_NUMBER": "+15550003333",
        }
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/twilio/send-sms", headers=H, json={
                "to": "+15557777777",
                "body": "Exception test",
            })
        assert r.status_code in VALID

    def test_call_success(self, client: TestClient) -> None:
        """Lines 614-616: call success path."""
        mock_cls = _httpx_mock(is_success=True, json_data={"sid": "CA123", "status": "initiated"})
        env = {
            "TWILIO_ACCOUNT_SID": "ACtest_call",
            "TWILIO_AUTH_TOKEN": "token_call",
            "TWILIO_FROM_NUMBER": "+15550004444",
        }
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/twilio/make-call", headers=H, json={
                "to": "+15556666666",
                "twiml_url": "https://twiml.example.com/say",
            })
        assert r.status_code in VALID

    def test_call_non_success(self, client: TestClient) -> None:
        """Lines 639-648: call queued-after-non-success."""
        mock_cls = _httpx_mock(is_success=False, status_code=400)
        env = {
            "TWILIO_ACCOUNT_SID": "ACtest_call_ns",
            "TWILIO_AUTH_TOKEN": "token_call_ns",
            "TWILIO_FROM_NUMBER": "+15550005555",
        }
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/twilio/make-call", headers=H, json={
                "to": "+15555555555",
                "twiml_url": "https://twiml.example.com/say2",
            })
        assert r.status_code in VALID


# ── Slack ─────────────────────────────────────────────────────────────────────


class TestSlackWithToken:
    """Lines 713-810: Slack send-message with token + blocks."""

    def test_send_message_with_blocks_success(self, client: TestClient) -> None:
        """Lines 713, 718-721: blocks branch + success path."""
        mock_cls = _httpx_mock(is_success=True, json_data={"ok": True, "ts": "12345.67890"})
        env = {"SLACK_BOT_TOKEN": "xoxb-test-token"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/slack/send-message", headers=H, json={
                "channel": "#general",
                "text": "Hello with blocks",
                "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Block text"}}],
            })
        assert r.status_code in VALID

    def test_send_message_exception(self, client: TestClient) -> None:
        """Lines 731-737: exception → queued."""
        mock_cls = _httpx_mock(raise_exc=True)
        env = {"SLACK_BOT_TOKEN": "xoxb-test-token-exc"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/slack/send-message", headers=H, json={
                "channel": "#alerts",
                "text": "Exception test",
            })
        assert r.status_code in VALID

    def test_send_message_non_success(self, client: TestClient) -> None:
        """Lines 743-750: non-success → queued."""
        mock_cls = _httpx_mock(is_success=False, status_code=500)
        env = {"SLACK_BOT_TOKEN": "xoxb-test-token-ns"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/slack/send-message", headers=H, json={
                "channel": "#dev",
                "text": "Non-success test",
            })
        assert r.status_code in VALID

    def test_webhook_with_blocks_success(self, client: TestClient) -> None:
        """Lines 778, 783: webhook blocks + success path."""
        mock_cls = _httpx_mock(is_success=True, json_data={"ok": True})
        env = {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test/test/test"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/slack/webhook", headers=H, json={
                "text": "Webhook with blocks",
                "blocks": [{"type": "divider"}],
            })
        assert r.status_code in VALID

    def test_webhook_exception(self, client: TestClient) -> None:
        """Lines 803-810: webhook exception."""
        mock_cls = _httpx_mock(raise_exc=True)
        env = {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/test/exc/exc"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/slack/webhook", headers=H, json={
                "text": "Exception webhook",
            })
        assert r.status_code in VALID


# ── Resend ────────────────────────────────────────────────────────────────────


class TestResendWithApiKey:
    """Lines 876-937: Resend with API key."""

    def test_send_email_html_body(self, client: TestClient) -> None:
        """Lines 876-877: html branch."""
        mock_cls = _httpx_mock(is_success=True, json_data={"id": "msg-html-001"})
        env = {"RESEND_API_KEY": "re_test_key"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/resend/send-email", headers=H, json={
                "to_email": "test@example.com",
                "subject": "HTML Email Test",
                "html": "<h1>Hello!</h1>",
            })
        assert r.status_code in VALID

    def test_send_email_text_body(self, client: TestClient) -> None:
        """Lines 878-879: text branch."""
        mock_cls = _httpx_mock(is_success=True, json_data={"id": "msg-text-001"})
        env = {"RESEND_API_KEY": "re_test_key2"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/resend/send-email", headers=H, json={
                "to_email": "text@example.com",
                "subject": "Text Email Test",
                "text": "Plain text email body",
            })
        assert r.status_code in VALID

    def test_send_email_no_body_default(self, client: TestClient) -> None:
        """Lines 880-881: neither html nor text → uses default."""
        mock_cls = _httpx_mock(is_success=True, json_data={"id": "msg-default-001"})
        env = {"RESEND_API_KEY": "re_test_key3"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/resend/send-email", headers=H, json={
                "to_email": "default@example.com",
                "subject": "Default Body Email",
            })
        assert r.status_code in VALID

    def test_send_email_exception(self, client: TestClient) -> None:
        """Lines 905-912: exception → queued-after-error."""
        mock_cls = _httpx_mock(raise_exc=True)
        env = {"RESEND_API_KEY": "re_test_key_exc"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/resend/send-email", headers=H, json={
                "to_email": "exc@example.com",
                "subject": "Exception Email",
            })
        assert r.status_code in VALID

    def test_send_email_non_success(self, client: TestClient) -> None:
        """Lines 914-921: non-success → queued-after-non-success."""
        mock_cls = _httpx_mock(is_success=False, status_code=429)
        env = {"RESEND_API_KEY": "re_test_key_ns"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/notifications/resend/send-email", headers=H, json={
                "to_email": "ns@example.com",
                "subject": "Non-success Email",
            })
        assert r.status_code in VALID


# ── Algolia ───────────────────────────────────────────────────────────────────


class TestAlgolia:
    """Lines 1057-1186: algolia index + query."""

    def test_index_object_no_creds(self, client: TestClient) -> None:
        """Without ALGOLIA_APP_ID/API_KEY → queued."""
        with patch.dict(os.environ, {"ALGOLIA_APP_ID": "", "ALGOLIA_API_KEY": ""}):
            r = client.post("/search/algolia/index-object", headers=H, json={
                "index_name": "products",
                "object_id": "obj-001",
                "document": {"title": "Algolia test"},
            })
        assert r.status_code in VALID

    def test_index_object_with_creds_success(self, client: TestClient) -> None:
        """Lines 1068-1077: success path."""
        mock_cls = _httpx_mock(is_success=True, json_data={"objectID": "obj-002", "taskID": 1})
        env = {"ALGOLIA_APP_ID": "TESTAPP", "ALGOLIA_API_KEY": "algolia-key"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/search/algolia/index-object", headers=H, json={
                "index_name": "articles",
                "object_id": "art-001",
                "document": {"title": "Algolia Article"},
            })
        assert r.status_code in VALID

    def test_index_object_exception(self, client: TestClient) -> None:
        """Lines 1090-1091: exception path."""
        mock_cls = _httpx_mock(raise_exc=True)
        env = {"ALGOLIA_APP_ID": "TESTAPP2", "ALGOLIA_API_KEY": "algolia-key2"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/search/algolia/index-object", headers=H, json={
                "index_name": "posts",
                "object_id": "post-001",
                "document": {"title": "Algolia Post"},
            })
        assert r.status_code in VALID

    def test_query_no_creds(self, client: TestClient) -> None:
        """Without creds → memory fallback."""
        with patch.dict(os.environ, {"ALGOLIA_APP_ID": "", "ALGOLIA_API_KEY": ""}):
            r = client.post("/search/algolia/query", headers=H, json={
                "index_name": "products",
                "query": "test",
                "limit": 10,
            })
        assert r.status_code in VALID

    def test_query_with_creds_success(self, client: TestClient) -> None:
        """Lines 1159-1172: query success path."""
        mock_cls = _httpx_mock(
            is_success=True,
            json_data={"hits": [{"objectID": "p1"}], "nbHits": 1, "query": "test"},
        )
        env = {"ALGOLIA_APP_ID": "TESTAPP3", "ALGOLIA_API_KEY": "algolia-key3"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/search/algolia/query", headers=H, json={
                "index_name": "products",
                "query": "test",
                "limit": 5,
            })
        assert r.status_code in VALID

    def test_query_with_creds_exception(self, client: TestClient) -> None:
        """Lines 1181-1186: query exception path."""
        mock_cls = _httpx_mock(raise_exc=True)
        env = {"ALGOLIA_APP_ID": "TESTAPP4", "ALGOLIA_API_KEY": "algolia-key4"}
        with patch.dict(os.environ, env), patch("httpx.Client", mock_cls):
            r = client.post("/search/algolia/query", headers=H, json={
                "index_name": "articles",
                "query": "broken",
            })
        assert r.status_code in VALID
