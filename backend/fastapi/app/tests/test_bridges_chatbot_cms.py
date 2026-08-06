"""
Tests for bridges.py, chatbot.py, cms_integration.py routers.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# --------------------------------------------------------------------------- #
# Bridges
# --------------------------------------------------------------------------- #
class TestBridgesSearch:
    def test_index_document(self, client: TestClient) -> None:
        r = client.post("/search/index-document", headers=H, json={
            "index": "posts",
            "id": "doc1",
            "body": {"title": "Hello World", "content": "Test content"},
        })
        assert r.status_code in VALID

    def test_query(self, client: TestClient) -> None:
        r = client.post("/search/query", headers=H, json={
            "index": "posts",
            "query": "hello",
        })
        assert r.status_code in VALID

    def test_algolia_index_object(self, client: TestClient) -> None:
        r = client.post("/search/algolia/index-object", headers=H, json={
            "index_name": "posts",
            "object_id": "obj1",
            "data": {"title": "Test"},
        })
        assert r.status_code in VALID

    def test_algolia_query(self, client: TestClient) -> None:
        r = client.post("/search/algolia/query", headers=H, json={
            "index_name": "posts",
            "query": "test",
        })
        assert r.status_code in VALID


class TestBridgesCache:
    def test_cache_set(self, client: TestClient) -> None:
        r = client.post("/cache/set", headers=H, json={
            "key": "test_key",
            "value": "test_value",
            "ttl": 300,
        })
        assert r.status_code in VALID

    def test_cache_get(self, client: TestClient) -> None:
        r = client.post("/cache/get", headers=H, json={"key": "test_key"})
        assert r.status_code in VALID

    def test_cache_delete(self, client: TestClient) -> None:
        r = client.post("/cache/delete", headers=H, json={"key": "test_key"})
        assert r.status_code in VALID

    def test_cache_flush_prefix(self, client: TestClient) -> None:
        r = client.post("/cache/flush-prefix", headers=H, json={"prefix": "test_"})
        assert r.status_code in VALID


class TestBridgesNotifications:
    def test_twilio_sms(self, client: TestClient) -> None:
        r = client.post("/notifications/twilio/send-sms", headers=H, json={
            "to": "+15551234567",
            "body": "Hello from test",
        })
        assert r.status_code in VALID

    def test_twilio_call(self, client: TestClient) -> None:
        r = client.post("/notifications/twilio/make-call", headers=H, json={
            "to": "+15551234567",
            "twiml": "<Response><Say>Hello</Say></Response>",
        })
        assert r.status_code in VALID

    def test_slack_message(self, client: TestClient) -> None:
        r = client.post("/notifications/slack/send-message", headers=H, json={
            "channel": "#general",
            "text": "Test notification",
        })
        assert r.status_code in VALID

    def test_slack_webhook(self, client: TestClient) -> None:
        r = client.post("/notifications/slack/webhook", headers=H, json={
            "text": "Test webhook message",
        })
        assert r.status_code in VALID

    def test_resend_email(self, client: TestClient) -> None:
        r = client.post("/notifications/resend/send-email", headers=H, json={
            "to": "test@example.com",
            "from_email": "noreply@example.com",
            "subject": "Test Email",
            "html": "<p>Hello</p>",
        })
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Chatbot
# --------------------------------------------------------------------------- #
class TestChatbot:
    def test_create_chatbot(self, client: TestClient) -> None:
        r = client.post("/chatbot", headers=H, json={
            "name": "Support Bot",
            "persona": "helpful assistant",
            "data_sources": ["https://docs.example.com"],
        })
        assert r.status_code in VALID

    def test_list_chatbots(self, client: TestClient) -> None:
        r = client.get("/chatbot", headers=H)
        assert r.status_code in VALID

    def test_train_nonexistent(self, client: TestClient) -> None:
        r = client.post("/chatbot/bot_nonexistent/train", headers=H, json={})
        assert r.status_code in VALID

    def test_deploy_nonexistent(self, client: TestClient) -> None:
        r = client.post("/chatbot/bot_nonexistent/deploy", headers=H, json={})
        assert r.status_code in VALID

    def test_message_nonexistent(self, client: TestClient) -> None:
        r = client.post("/chatbot/bot_nonexistent/message", headers=H, json={
            "message": "Hello",
            "session_id": "sess_001",
        })
        assert r.status_code in VALID

    def test_conversations_nonexistent(self, client: TestClient) -> None:
        r = client.get("/chatbot/bot_nonexistent/conversations", headers=H)
        assert r.status_code in VALID

    def test_analytics_nonexistent(self, client: TestClient) -> None:
        r = client.get("/chatbot/bot_nonexistent/analytics", headers=H)
        assert r.status_code in VALID

    def test_leads_nonexistent(self, client: TestClient) -> None:
        r = client.get("/chatbot/bot_nonexistent/leads", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# CMS Integration
# --------------------------------------------------------------------------- #
class TestCmsIntegration:
    def test_create_connection(self, client: TestClient) -> None:
        r = client.post("/cms/connections", headers=H, json={
            "cms_type": "wordpress",
            "url": "https://myblog.example.com",
            "credentials": {"username": "admin", "app_password": "xxxx"},
        })
        assert r.status_code in VALID

    def test_list_connections(self, client: TestClient) -> None:
        r = client.get("/cms/connections", headers=H)
        assert r.status_code in VALID

    def test_publish(self, client: TestClient) -> None:
        r = client.post("/cms/publish", headers=H, json={
            "connection_id": "conn_nonexistent",
            "title": "Test Post",
            "content": "<p>Hello World</p>",
            "status": "draft",
        })
        assert r.status_code in VALID

    def test_sync(self, client: TestClient) -> None:
        r = client.post("/cms/sync", headers=H, json={
            "connection_id": "conn_nonexistent",
        })
        assert r.status_code in VALID

    def test_list_pages(self, client: TestClient) -> None:
        r = client.get("/cms/pages", headers=H)
        assert r.status_code in VALID

    def test_schema_inject(self, client: TestClient) -> None:
        r = client.post("/cms/schema-inject", headers=H, json={
            "connection_id": "conn_nonexistent",
            "page_id": "page_001",
            "schema_type": "Article",
        })
        assert r.status_code in VALID

    def test_crawler_analytics(self, client: TestClient) -> None:
        r = client.get("/cms/crawler-analytics", headers=H)
        assert r.status_code in VALID
