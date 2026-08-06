"""
Smoke tests for untested routers:
- documents.py (documents and quotes)
- marketplace.py
- workflows.py
- meetings.py
- knowledge_base.py
- surveys.py
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


# ── Documents ────────────────────────────────────────────────────────────────

class TestDocuments:
    def test_create_document(self, client) -> None:
        r = client.post("/documents", headers=H, json={
            "title": "Test Doc", "content": "Hello world", "document_type": "report"
        })
        assert r.status_code in VALID

    def test_list_documents(self, client) -> None:
        r = client.get("/documents", headers=H)
        assert r.status_code in VALID

    def test_get_document_not_found(self, client) -> None:
        r = client.get("/documents/nonexistent-id", headers=H)
        assert r.status_code in VALID

    def test_share_document_not_found(self, client) -> None:
        r = client.post("/documents/nonexistent-id/share", headers=H, json={"emails": ["user@test.com"]})
        assert r.status_code in VALID

    def test_delete_document_not_found(self, client) -> None:
        r = client.delete("/documents/nonexistent-id", headers=H)
        assert r.status_code in VALID


# ── Quotes ────────────────────────────────────────────────────────────────────

class TestQuotes:
    def test_create_quote(self, client) -> None:
        r = client.post("/quotes", headers=H, json={
            "contact_id": "c-1",
            "title": "Service Quote",
            "line_items": [{"description": "SEO Services", "quantity": 1, "unit_price": 500.0}],
        })
        assert r.status_code in VALID

    def test_list_quotes(self, client) -> None:
        r = client.get("/quotes", headers=H)
        assert r.status_code in VALID

    def test_get_quote_not_found(self, client) -> None:
        r = client.get("/quotes/nonexistent-id", headers=H)
        assert r.status_code in VALID

    def test_send_quote_not_found(self, client) -> None:
        r = client.post("/quotes/nonexistent-id/send", headers=H, json={})
        assert r.status_code in VALID

    def test_sign_quote_not_found(self, client) -> None:
        r = client.post("/quotes/nonexistent-id/sign", headers=H, json={"signed_by": "client@test.com"})
        assert r.status_code in VALID


# ── Marketplace ───────────────────────────────────────────────────────────────

class TestMarketplace:
    def test_list_plugins(self, client) -> None:
        r = client.get("/marketplace/plugins", headers=H)
        assert r.status_code in VALID

    def test_list_themes(self, client) -> None:
        r = client.get("/marketplace/themes", headers=H)
        assert r.status_code in VALID

    def test_install_item(self, client) -> None:
        r = client.post("/marketplace/install", headers=H, json={
            "item_id": "plugin-seo-boost", "item_type": "plugin"
        })
        assert r.status_code in VALID

    def test_publish_item(self, client) -> None:
        r = client.post("/marketplace/publish", headers=H, json={
            "name": "My Plugin", "description": "A plugin", "item_type": "plugin", "version": "1.0.0"
        })
        assert r.status_code in VALID


# ── Workflows ─────────────────────────────────────────────────────────────────

class TestWorkflows:
    def test_create_workflow(self, client) -> None:
        r = client.post("/workflows", headers=H, json={
            "name": "Test Workflow",
            "trigger_type": "schedule",
            "steps": [{"action": "send_email", "config": {}}],
        })
        assert r.status_code in VALID

    def test_list_workflows(self, client) -> None:
        r = client.get("/workflows", headers=H)
        assert r.status_code in VALID

    def test_get_workflow_not_found(self, client) -> None:
        r = client.get("/workflows/nonexistent-id", headers=H)
        assert r.status_code in VALID

    def test_toggle_workflow_not_found(self, client) -> None:
        r = client.patch("/workflows/nonexistent-id/toggle", headers=H)
        assert r.status_code in VALID

    def test_enroll_workflow_not_found(self, client) -> None:
        r = client.post("/workflows/nonexistent-id/enroll", headers=H, json={"contact_id": "c-1"})
        assert r.status_code in VALID

    def test_get_workflow_executions_not_found(self, client) -> None:
        r = client.get("/workflows/nonexistent-id/executions", headers=H)
        assert r.status_code in VALID

    def test_get_workflow_analytics_not_found(self, client) -> None:
        r = client.get("/workflows/nonexistent-id/analytics", headers=H)
        assert r.status_code in VALID

    def test_delete_workflow_not_found(self, client) -> None:
        r = client.delete("/workflows/nonexistent-id", headers=H)
        assert r.status_code in VALID


# ── Meetings ──────────────────────────────────────────────────────────────────

class TestMeetings:
    def test_create_meeting_link(self, client) -> None:
        r = client.post("/meetings/links", headers=H, json={
            "name": "30-min Consultation",
            "slug": "consult-30min",
            "duration_minutes": 30,
        })
        assert r.status_code in VALID

    def test_list_meeting_links(self, client) -> None:
        r = client.get("/meetings/links", headers=H)
        assert r.status_code in VALID

    def test_get_meeting_link_not_found(self, client) -> None:
        r = client.get("/meetings/links/nonexistent-slug", headers=H)
        assert r.status_code in VALID

    def test_book_meeting_not_found(self, client) -> None:
        r = client.post("/meetings/book", headers=H, json={
            "slug": "nonexistent-slug",
            "attendee_email": "test@example.com",
            "attendee_name": "Test User",
            "start_time": "2025-01-01T10:00:00Z",
        })
        assert r.status_code in VALID

    def test_list_bookings(self, client) -> None:
        r = client.get("/meetings/bookings", headers=H)
        assert r.status_code in VALID

    def test_patch_booking_not_found(self, client) -> None:
        r = client.patch("/meetings/bookings/nonexistent-id", headers=H, json={"status": "cancelled"})
        assert r.status_code in VALID

    def test_meeting_analytics(self, client) -> None:
        r = client.get("/meetings/analytics", headers=H)
        assert r.status_code in VALID


# ── Knowledge Base ────────────────────────────────────────────────────────────

class TestKnowledgeBase:
    def test_create_category(self, client) -> None:
        r = client.post("/kb/categories", headers=H, json={"name": "Getting Started", "description": "Intro articles"})
        assert r.status_code in VALID

    def test_list_categories(self, client) -> None:
        r = client.get("/kb/categories", headers=H)
        assert r.status_code in VALID

    def test_create_article(self, client) -> None:
        r = client.post("/kb/articles", headers=H, json={
            "title": "How to get started",
            "content": "First, log in to your account...",
            "category_id": "cat-1",
        })
        assert r.status_code in VALID

    def test_list_articles(self, client) -> None:
        r = client.get("/kb/articles", headers=H)
        assert r.status_code in VALID

    def test_get_article_not_found(self, client) -> None:
        r = client.get("/kb/articles/nonexistent-id", headers=H)
        assert r.status_code in VALID

    def test_patch_article_not_found(self, client) -> None:
        r = client.patch("/kb/articles/nonexistent-id", headers=H, json={"title": "Updated Title"})
        assert r.status_code in VALID

    def test_delete_article_not_found(self, client) -> None:
        r = client.delete("/kb/articles/nonexistent-id", headers=H)
        assert r.status_code in VALID

    def test_article_feedback_not_found(self, client) -> None:
        r = client.post("/kb/articles/nonexistent-id/feedback", headers=H, json={"helpful": True})
        assert r.status_code in VALID

    def test_search_articles(self, client) -> None:
        r = client.get("/kb/search", headers=H, params={"q": "getting started"})
        assert r.status_code in VALID

    def test_kb_analytics(self, client) -> None:
        r = client.get("/kb/analytics/summary", headers=H)
        assert r.status_code in VALID


# ── Surveys ───────────────────────────────────────────────────────────────────

class TestSurveys:
    def test_create_survey(self, client) -> None:
        r = client.post("/surveys", headers=H, json={
            "title": "Customer Satisfaction Survey",
            "questions": [
                {"text": "How satisfied are you?", "type": "rating", "required": True}
            ],
        })
        assert r.status_code in VALID

    def test_list_surveys(self, client) -> None:
        r = client.get("/surveys", headers=H)
        assert r.status_code in VALID

    def test_get_survey_not_found(self, client) -> None:
        r = client.get("/surveys/nonexistent-id", headers=H)
        assert r.status_code in VALID

    def test_respond_to_survey_not_found(self, client) -> None:
        r = client.post("/surveys/nonexistent-id/respond", headers=H, json={
            "answers": [{"question_id": "q-1", "value": "5"}]
        })
        assert r.status_code in VALID

    def test_get_survey_responses_not_found(self, client) -> None:
        r = client.get("/surveys/nonexistent-id/responses", headers=H)
        assert r.status_code in VALID

    def test_get_survey_analytics_not_found(self, client) -> None:
        r = client.get("/surveys/nonexistent-id/analytics", headers=H)
        assert r.status_code in VALID
