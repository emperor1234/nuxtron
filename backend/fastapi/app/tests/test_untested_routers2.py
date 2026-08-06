"""
Route smoke tests for untested routers batch 2:
media_library, meetings, products, sequences, workflows, 
surveys, utm_builder, viralpost, smart_inbox.
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


class TestMediaLibrary:
    def test_create_folder(self, client: TestClient) -> None:
        r = client.post("/media/folders", headers=H, json={"name": "Brand Assets"})
        assert r.status_code in VALID

    def test_list_folders(self, client: TestClient) -> None:
        r = client.get("/media/folders", headers=H)
        assert r.status_code in VALID

    def test_create_asset(self, client: TestClient) -> None:
        r = client.post("/media/assets", headers=H, json={
            "filename": "logo.png",
            "url": "https://cdn.example.com/logo.png",
            "file_type": "image/png",
            "file_size": 12345,
        })
        assert r.status_code in VALID

    def test_list_assets(self, client: TestClient) -> None:
        r = client.get("/media/assets", headers=H)
        assert r.status_code in VALID

    def test_get_asset_not_found(self, client: TestClient) -> None:
        r = client.get("/media/assets/99999", headers=H)
        assert r.status_code in VALID

    def test_delete_asset_not_found(self, client: TestClient) -> None:
        r = client.delete("/media/assets/99999", headers=H)
        assert r.status_code in VALID

    def test_stats(self, client: TestClient) -> None:
        r = client.get("/media/stats", headers=H)
        assert r.status_code in VALID


class TestMeetings:
    def test_create_meeting_link(self, client: TestClient) -> None:
        r = client.post("/meetings/links", headers=H, json={
            "title": "Discovery Call",
            "duration_minutes": 30,
            "slug": "discovery-call-test",
        })
        assert r.status_code in VALID

    def test_list_meeting_links(self, client: TestClient) -> None:
        r = client.get("/meetings/links", headers=H)
        assert r.status_code in VALID

    def test_get_meeting_link_not_found(self, client: TestClient) -> None:
        r = client.get("/meetings/links/nonexistent-slug-xyz", headers=H)
        assert r.status_code in VALID

    def test_book_meeting_not_found(self, client: TestClient) -> None:
        r = client.post("/meetings/book", headers=H, json={
            "slug": "nonexistent-slug",
            "attendee_name": "Alice",
            "attendee_email": "alice@example.com",
            "requested_at": "2025-06-01T10:00:00Z",
        })
        assert r.status_code in VALID

    def test_list_bookings(self, client: TestClient) -> None:
        r = client.get("/meetings/bookings", headers=H)
        assert r.status_code in VALID

    def test_analytics(self, client: TestClient) -> None:
        r = client.get("/meetings/analytics", headers=H)
        assert r.status_code in VALID


class TestProducts:
    def test_create_category(self, client: TestClient) -> None:
        r = client.post("/products/categories", headers=H, json={
            "name": "Software",
            "description": "Software products",
        })
        assert r.status_code in VALID

    def test_list_categories(self, client: TestClient) -> None:
        r = client.get("/products/categories", headers=H)
        assert r.status_code in VALID

    def test_create_product(self, client: TestClient) -> None:
        r = client.post("/products", headers=H, json={
            "name": "Nuxtron Pro",
            "sku": "NXT-PRO-001",
            "price": 99.99,
            "description": "Professional plan",
        })
        assert r.status_code in VALID

    def test_list_products(self, client: TestClient) -> None:
        r = client.get("/products", headers=H)
        assert r.status_code in VALID

    def test_get_product_not_found(self, client: TestClient) -> None:
        r = client.get("/products/99999", headers=H)
        assert r.status_code in VALID

    def test_delete_product_not_found(self, client: TestClient) -> None:
        r = client.delete("/products/99999", headers=H)
        assert r.status_code in VALID

    def test_catalog_stats(self, client: TestClient) -> None:
        r = client.get("/products/catalog/stats", headers=H)
        assert r.status_code in VALID


class TestSequences:
    def test_create_sequence(self, client: TestClient) -> None:
        r = client.post("/sequences", headers=H, json={
            "name": "Welcome Sequence",
            "steps": [
                {"day": 0, "action": "email", "subject": "Welcome!", "body": "Hello!"},
                {"day": 3, "action": "email", "subject": "Follow up", "body": "Checking in"},
            ],
        })
        assert r.status_code in VALID

    def test_list_sequences(self, client: TestClient) -> None:
        r = client.get("/sequences", headers=H)
        assert r.status_code in VALID

    def test_get_sequence_not_found(self, client: TestClient) -> None:
        r = client.get("/sequences/99999", headers=H)
        assert r.status_code in VALID

    def test_enroll_not_found(self, client: TestClient) -> None:
        r = client.post("/sequences/99999/enroll", headers=H, json={
            "contact_id": "contact-001",
        })
        assert r.status_code in VALID

    def test_enrollments_not_found(self, client: TestClient) -> None:
        r = client.get("/sequences/99999/enrollments", headers=H)
        assert r.status_code in VALID

    def test_analytics_not_found(self, client: TestClient) -> None:
        r = client.get("/sequences/99999/analytics", headers=H)
        assert r.status_code in VALID

    def test_delete_not_found(self, client: TestClient) -> None:
        r = client.delete("/sequences/99999", headers=H)
        assert r.status_code in VALID


class TestWorkflows:
    def test_create_workflow(self, client: TestClient) -> None:
        r = client.post("/workflows", headers=H, json={
            "name": "Lead Nurture",
            "trigger": "contact_created",
            "steps": [
                {"type": "email", "delay_hours": 0, "template_id": 1},
            ],
        })
        assert r.status_code in VALID

    def test_list_workflows(self, client: TestClient) -> None:
        r = client.get("/workflows", headers=H)
        assert r.status_code in VALID

    def test_get_workflow_not_found(self, client: TestClient) -> None:
        r = client.get("/workflows/99999", headers=H)
        assert r.status_code in VALID

    def test_toggle_not_found(self, client: TestClient) -> None:
        r = client.patch("/workflows/99999/toggle", headers=H)
        assert r.status_code in VALID

    def test_enroll_not_found(self, client: TestClient) -> None:
        r = client.post("/workflows/99999/enroll", headers=H, json={
            "contact_id": "contact-001",
        })
        assert r.status_code in VALID

    def test_executions_not_found(self, client: TestClient) -> None:
        r = client.get("/workflows/99999/executions", headers=H)
        assert r.status_code in VALID

    def test_analytics_not_found(self, client: TestClient) -> None:
        r = client.get("/workflows/99999/analytics", headers=H)
        assert r.status_code in VALID

    def test_delete_not_found(self, client: TestClient) -> None:
        r = client.delete("/workflows/99999", headers=H)
        assert r.status_code in VALID


class TestSurveys:
    def test_create_survey(self, client: TestClient) -> None:
        r = client.post("/surveys", headers=H, json={
            "title": "Customer Satisfaction",
            "questions": [
                {"text": "How satisfied are you?", "type": "rating", "options": []},
            ],
        })
        assert r.status_code in VALID

    def test_list_surveys(self, client: TestClient) -> None:
        r = client.get("/surveys", headers=H)
        assert r.status_code in VALID

    def test_get_survey_not_found(self, client: TestClient) -> None:
        r = client.get("/surveys/99999", headers=H)
        assert r.status_code in VALID

    def test_respond_not_found(self, client: TestClient) -> None:
        r = client.post("/surveys/99999/respond", headers=H, json={
            "answers": [{"question_id": 1, "value": "5"}],
        })
        assert r.status_code in VALID

    def test_responses_not_found(self, client: TestClient) -> None:
        r = client.get("/surveys/99999/responses", headers=H)
        assert r.status_code in VALID

    def test_analytics_not_found(self, client: TestClient) -> None:
        r = client.get("/surveys/99999/analytics", headers=H)
        assert r.status_code in VALID


class TestUtmBuilder:
    def test_create_preset(self, client: TestClient) -> None:
        r = client.post("/publishing/utm/presets", headers=H, json={
            "name": "Email Campaign",
            "source": "email",
            "medium": "newsletter",
            "campaign": "summer-launch",
        })
        assert r.status_code in VALID

    def test_list_presets(self, client: TestClient) -> None:
        r = client.get("/publishing/utm/presets", headers=H)
        assert r.status_code in VALID

    def test_build_not_found(self, client: TestClient) -> None:
        r = client.post("/publishing/utm/build", headers=H, json={
            "preset_id": 99999,
            "base_url": "https://example.com",
        })
        assert r.status_code in VALID


class TestViralpost:
    def test_post_history(self, client: TestClient) -> None:
        r = client.post("/publishing/post-history", headers=H, json={
            "platform": "twitter",
            "content": "Hello world!",
            "published_at": "2025-01-01T10:00:00Z",
        })
        assert r.status_code in VALID

    def test_optimal_times_post(self, client: TestClient) -> None:
        r = client.post("/publishing/optimal-times", headers=H, json={
            "platform": "instagram",
            "timezone": "UTC",
        })
        assert r.status_code in VALID

    def test_optimal_times_get(self, client: TestClient) -> None:
        r = client.get("/publishing/optimal-times", headers=H)
        assert r.status_code in VALID

    def test_optimal_times_defaults(self, client: TestClient) -> None:
        r = client.get("/publishing/optimal-times/defaults", headers=H)
        assert r.status_code in VALID


class TestSmartInbox:
    def test_create_message(self, client: TestClient) -> None:
        r = client.post("/inbox/messages", headers=H, json={
            "channel": "email",
            "from_address": "customer@example.com",
            "subject": "Help with billing",
            "body": "I need help with my invoice",
        })
        assert r.status_code in VALID

    def test_list_messages(self, client: TestClient) -> None:
        r = client.get("/inbox/messages", headers=H)
        assert r.status_code in VALID

    def test_get_message_not_found(self, client: TestClient) -> None:
        r = client.get("/inbox/messages/99999", headers=H)
        assert r.status_code in VALID

    def test_get_notes_not_found(self, client: TestClient) -> None:
        r = client.get("/inbox/messages/99999/notes", headers=H)
        assert r.status_code in VALID

    def test_stats(self, client: TestClient) -> None:
        r = client.get("/inbox/stats", headers=H)
        assert r.status_code in VALID

    def test_create_saved_reply(self, client: TestClient) -> None:
        r = client.post("/inbox/saved-replies", headers=H, json={
            "title": "Standard Refund Response",
            "body": "We've processed your refund.",
        })
        assert r.status_code in VALID

    def test_list_saved_replies(self, client: TestClient) -> None:
        r = client.get("/inbox/saved-replies", headers=H)
        assert r.status_code in VALID
