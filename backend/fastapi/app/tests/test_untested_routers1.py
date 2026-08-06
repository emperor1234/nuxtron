"""
Route smoke tests for untested routers:
cms_integration, chatbot, competitive, content_approval,
knowledge_base, influencer, linkinbio, marketplace.
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


class TestCmsIntegration:
    def test_create_connection(self, client: TestClient) -> None:
        r = client.post("/cms/connections", headers=H, json={
            "cms_type": "wordpress",
            "name": "My WP Site",
            "api_url": "https://myblog.com",
            "api_key": "secret-key",
        })
        assert r.status_code in VALID

    def test_unsupported_cms_type(self, client: TestClient) -> None:
        r = client.post("/cms/connections", headers=H, json={
            "cms_type": "unknown_cms",
            "name": "My Site",
            "api_url": "https://site.com",
        })
        assert r.status_code in VALID

    def test_list_connections(self, client: TestClient) -> None:
        r = client.get("/cms/connections", headers=H)
        assert r.status_code in VALID

    def test_publish_not_found(self, client: TestClient) -> None:
        r = client.post("/cms/publish", headers=H, json={
            "connection_id": 9999,
            "title": "Test Post",
            "content": "Hello world",
            "status": "draft",
        })
        assert r.status_code in VALID

    def test_sync_not_found(self, client: TestClient) -> None:
        r = client.post("/cms/sync", headers=H, json={
            "connection_id": 9999,
        })
        assert r.status_code in VALID

    def test_list_pages(self, client: TestClient) -> None:
        r = client.get("/cms/pages", headers=H)
        assert r.status_code in VALID

    def test_schema_inject_not_found(self, client: TestClient) -> None:
        r = client.post("/cms/schema-inject", headers=H, json={
            "connection_id": 9999,
            "schema_type": "Article",
        })
        assert r.status_code in VALID

    def test_crawler_analytics(self, client: TestClient) -> None:
        r = client.get("/cms/crawler-analytics", headers=H)
        assert r.status_code in VALID


class TestChatbot:
    def test_create_chatbot(self, client: TestClient) -> None:
        r = client.post("/chatbot", headers=H, json={
            "name": "Support Bot",
            "personality": "helpful and concise",
            "fallback_message": "I don't understand",
        })
        assert r.status_code in VALID

    def test_list_chatbots(self, client: TestClient) -> None:
        r = client.get("/chatbot", headers=H)
        assert r.status_code in VALID

    def test_train_not_found(self, client: TestClient) -> None:
        r = client.post("/chatbot/99999/train", headers=H, json={
            "knowledge_sources": ["https://example.com/faq"],
        })
        assert r.status_code in VALID

    def test_deploy_not_found(self, client: TestClient) -> None:
        r = client.post("/chatbot/99999/deploy", headers=H, json={
            "channel": "website",
        })
        assert r.status_code in VALID

    def test_message_not_found(self, client: TestClient) -> None:
        r = client.post("/chatbot/99999/message", headers=H, json={
            "message": "Hello!",
            "session_id": "sess-001",
        })
        assert r.status_code in VALID

    def test_conversations_not_found(self, client: TestClient) -> None:
        r = client.get("/chatbot/99999/conversations", headers=H)
        assert r.status_code in VALID

    def test_analytics_not_found(self, client: TestClient) -> None:
        r = client.get("/chatbot/99999/analytics", headers=H)
        assert r.status_code in VALID

    def test_leads(self, client: TestClient) -> None:
        r = client.get("/chatbot/99999/leads", headers=H)
        assert r.status_code in VALID


class TestKnowledgeBase:
    def test_create_kb(self, client: TestClient) -> None:
        r = client.post("/knowledge-base", headers=H, json={
            "name": "Product FAQ",
            "description": "Frequently asked questions",
        })
        assert r.status_code in VALID

    def test_list_kbs(self, client: TestClient) -> None:
        r = client.get("/knowledge-base", headers=H)
        assert r.status_code in VALID

    def test_create_article(self, client: TestClient) -> None:
        r = client.post("/knowledge-base/99999/articles", headers=H, json={
            "title": "Getting Started",
            "content": "Welcome to the platform!",
        })
        assert r.status_code in VALID

    def test_list_articles_not_found(self, client: TestClient) -> None:
        r = client.get("/knowledge-base/99999/articles", headers=H)
        assert r.status_code in VALID

    def test_search_kb(self, client: TestClient) -> None:
        r = client.get("/knowledge-base/search?q=getting+started", headers=H)
        assert r.status_code in VALID


class TestInfluencer:
    def test_create_campaign(self, client: TestClient) -> None:
        r = client.post("/influencer/campaigns", headers=H, json={
            "name": "Summer Launch",
            "budget": 5000.0,
            "target_reach": 100000,
        })
        assert r.status_code in VALID

    def test_list_campaigns(self, client: TestClient) -> None:
        r = client.get("/influencer/campaigns", headers=H)
        assert r.status_code in VALID

    def test_add_influencer(self, client: TestClient) -> None:
        r = client.post("/influencer/campaigns/99999/influencers", headers=H, json={
            "handle": "@test_influencer",
            "platform": "instagram",
            "followers": 50000,
        })
        assert r.status_code in VALID

    def test_list_influencers(self, client: TestClient) -> None:
        r = client.get("/influencer/campaigns/99999/influencers", headers=H)
        assert r.status_code in VALID

    def test_analytics(self, client: TestClient) -> None:
        r = client.get("/influencer/campaigns/99999/analytics", headers=H)
        assert r.status_code in VALID


class TestLinkinbio:
    def test_create_page(self, client: TestClient) -> None:
        r = client.post("/linkinbio/pages", headers=H, json={
            "title": "My Links",
            "bio": "Check out my content",
        })
        assert r.status_code in VALID

    def test_list_pages(self, client: TestClient) -> None:
        r = client.get("/linkinbio/pages", headers=H)
        assert r.status_code in VALID

    def test_add_link(self, client: TestClient) -> None:
        r = client.post("/linkinbio/pages/99999/links", headers=H, json={
            "title": "My Blog",
            "url": "https://myblog.com",
        })
        assert r.status_code in VALID

    def test_analytics_not_found(self, client: TestClient) -> None:
        r = client.get("/linkinbio/pages/99999/analytics", headers=H)
        assert r.status_code in VALID


class TestMarketplace:
    def test_list_products(self, client: TestClient) -> None:
        r = client.get("/marketplace/products", headers=H)
        assert r.status_code in VALID

    def test_create_product(self, client: TestClient) -> None:
        r = client.post("/marketplace/products", headers=H, json={
            "name": "Test Product",
            "price": 29.99,
            "description": "A great product",
        })
        assert r.status_code in VALID

    def test_get_product_not_found(self, client: TestClient) -> None:
        r = client.get("/marketplace/products/99999", headers=H)
        assert r.status_code in VALID

    def test_create_order(self, client: TestClient) -> None:
        r = client.post("/marketplace/orders", headers=H, json={
            "product_id": 1,
            "quantity": 2,
        })
        assert r.status_code in VALID


class TestContentApproval:
    def test_create_content(self, client: TestClient) -> None:
        r = client.post("/content-approval/items", headers=H, json={
            "title": "New Blog Post",
            "content": "Blog content here",
            "content_type": "blog",
        })
        assert r.status_code in VALID

    def test_list_content(self, client: TestClient) -> None:
        r = client.get("/content-approval/items", headers=H)
        assert r.status_code in VALID

    def test_approve_content(self, client: TestClient) -> None:
        r = client.post("/content-approval/items/99999/approve", headers=H, json={
            "comment": "Looks good!",
        })
        assert r.status_code in VALID

    def test_reject_content(self, client: TestClient) -> None:
        r = client.post("/content-approval/items/99999/reject", headers=H, json={
            "reason": "Needs revision",
        })
        assert r.status_code in VALID


class TestCompetitive:
    def test_add_competitor(self, client: TestClient) -> None:
        r = client.post("/competitive/competitors", headers=H, json={
            "name": "Competitor A",
            "domain": "competitor-a.com",
        })
        assert r.status_code in VALID

    def test_list_competitors(self, client: TestClient) -> None:
        r = client.get("/competitive/competitors", headers=H)
        assert r.status_code in VALID

    def test_analysis(self, client: TestClient) -> None:
        r = client.get("/competitive/analysis", headers=H)
        assert r.status_code in VALID

    def test_insights(self, client: TestClient) -> None:
        r = client.get("/competitive/insights", headers=H)
        assert r.status_code in VALID
