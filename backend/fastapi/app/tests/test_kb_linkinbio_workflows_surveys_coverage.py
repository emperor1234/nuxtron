"""Coverage for knowledge_base.py, linkinbio.py, workflows.py, and surveys.py."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {
    "X-API-Key": os.getenv("FASTAPI_API_KEY", "test-api-key"),
    "X-Tenant-Id": "kb-lnk-wf-sv-coverage-tenant",
}


def _create_linkinbio_page(client: TestClient, title: str = "Seed Page") -> int:
    response = client.post(
        "/linkinbio/pages",
        headers=H,
        json={
            "title": title,
            "bio": "Seed bio",
            "theme": "minimal",
            "custom_domain": "",
            "profile_image_url": "",
        },
    )
    assert response.status_code in (200, 201)
    return int(response.json()["page"]["id"])


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


# ────────────────────────────────────────────────────────────────────────────
# Knowledge Base
# ────────────────────────────────────────────────────────────────────────────

class TestKnowledgeBaseCoverage:
    """Cover create/list/get/update/delete articles + categories + search + feedback + analytics."""

    def test_create_category(self, client: TestClient) -> None:
        r = client.post(
            "/kb/categories",
            headers=H,
            json={"name": "Getting Started", "description": "Onboarding guides", "sort_order": 1, "icon": "book"},
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["category"]["name"] == "Getting Started"

    def test_create_subcategory(self, client: TestClient) -> None:
        r = client.post(
            "/kb/categories",
            headers=H,
            json={"name": "Advanced Topics", "parent_category_id": 1, "sort_order": 2},
        )
        assert r.status_code in (200, 201)

    def test_list_categories(self, client: TestClient) -> None:
        r = client.get("/kb/categories", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_create_published_article(self, client: TestClient) -> None:
        r = client.post(
            "/kb/articles",
            headers=H,
            json={
                "title": "How to set up your account",
                "body": "Follow these steps to get started with your account quickly and easily.",
                "category_id": 1,
                "tags": ["setup", "onboarding"],
                "status": "published",
                "seo_title": "Account Setup Guide",
                "seo_description": "Learn how to set up your account step by step.",
                "featured": True,
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["article"]["status"] == "published"
        assert data["article"]["published_at"] is not None

    def test_create_draft_article(self, client: TestClient) -> None:
        r = client.post(
            "/kb/articles",
            headers=H,
            json={
                "title": "Draft Article",
                "body": "This is a draft that hasn't been published yet.",
                "status": "draft",
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["article"]["status"] == "draft"

    def test_create_article_invalid_status_defaults(self, client: TestClient) -> None:
        r = client.post(
            "/kb/articles",
            headers=H,
            json={
                "title": "Status Default Test",
                "body": "This should default to draft status.",
                "status": "invalid_st",
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["article"]["status"] == "draft"

    def test_list_articles(self, client: TestClient) -> None:
        r = client.get("/kb/articles", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_list_articles_by_status(self, client: TestClient) -> None:
        r = client.get("/kb/articles?status=published", headers=H)
        assert r.status_code == 200
        for a in r.json()["articles"]:
            assert a["status"] == "published"

    def test_list_articles_by_category(self, client: TestClient) -> None:
        r = client.get("/kb/articles?category_id=1", headers=H)
        assert r.status_code == 200

    def test_list_articles_featured(self, client: TestClient) -> None:
        r = client.get("/kb/articles?featured=true", headers=H)
        assert r.status_code == 200
        for a in r.json()["articles"]:
            assert a["featured"] is True

    def test_get_article_increments_views(self, client: TestClient) -> None:
        list_r = client.get("/kb/articles", headers=H)
        art_id = list_r.json()["articles"][0]["id"]

        r = client.get(f"/kb/articles/{art_id}", headers=H)
        assert r.status_code == 200
        assert r.json()["article"]["view_count"] >= 1

    def test_get_article_missing(self, client: TestClient) -> None:
        r = client.get("/kb/articles/9999", headers=H)
        assert r.status_code == 404

    def test_update_article_publish(self, client: TestClient) -> None:
        # Get the draft article
        list_r = client.get("/kb/articles?status=draft", headers=H)
        art_id = list_r.json()["articles"][0]["id"]

        r = client.patch(
            f"/kb/articles/{art_id}",
            headers=H,
            json={
                "title": "Updated Draft Title",
                "status": "published",
                "seo_title": "SEO Title for Draft",
                "seo_description": "SEO description here.",
                "featured": True,
                "tags": ["updated", "published"],
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["article"]["status"] == "published"
        assert data["article"]["published_at"] is not None

    def test_update_article_missing(self, client: TestClient) -> None:
        r = client.patch("/kb/articles/9999", headers=H, json={"title": "Ghost"})
        assert r.status_code == 404

    def test_submit_helpful_feedback(self, client: TestClient) -> None:
        list_r = client.get("/kb/articles", headers=H)
        art_id = list_r.json()["articles"][0]["id"]

        r = client.post(
            f"/kb/articles/{art_id}/feedback",
            headers=H,
            json={"helpful": True, "comment": "Very clear and easy to follow!"},
        )
        assert r.status_code in (200, 201)
        assert r.json()["feedback"]["helpful"] is True

    def test_submit_not_helpful_feedback(self, client: TestClient) -> None:
        list_r = client.get("/kb/articles", headers=H)
        art_id = list_r.json()["articles"][0]["id"]

        r = client.post(
            f"/kb/articles/{art_id}/feedback",
            headers=H,
            json={"helpful": False, "comment": "Needs more detail."},
        )
        assert r.status_code in (200, 201)
        assert r.json()["feedback"]["helpful"] is False

    def test_submit_feedback_missing_article(self, client: TestClient) -> None:
        r = client.post("/kb/articles/9999/feedback", headers=H, json={"helpful": True})
        assert r.status_code == 404

    def test_search_articles(self, client: TestClient) -> None:
        r = client.get("/kb/search?q=account", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_search_articles_no_results(self, client: TestClient) -> None:
        r = client.get("/kb/search?q=xyznotfoundkeyword", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] == 0

    def test_kb_analytics(self, client: TestClient) -> None:
        r = client.get("/kb/analytics/summary", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "total_articles" in data
        assert "helpfulness_rate" in data
        assert "top_articles" in data

    def test_delete_article(self, client: TestClient) -> None:
        r = client.post(
            "/kb/articles",
            headers=H,
            json={"title": "Delete Me Article", "body": "This will be deleted."},
        )
        art_id = r.json()["article"]["id"]

        r2 = client.delete(f"/kb/articles/{art_id}", headers=H)
        assert r2.status_code in (200, 201)
        assert r2.json()["deleted"] is True

    def test_delete_article_missing(self, client: TestClient) -> None:
        r = client.delete("/kb/articles/9999", headers=H)
        assert r.status_code == 404

    def test_create_article_updates_category_count(self, client: TestClient) -> None:
        cat_r = client.post(
            "/kb/categories",
            headers=H,
            json={"name": "Counted Category", "description": "for count test"},
        )
        assert cat_r.status_code in (200, 201)
        category_id = cat_r.json()["category"]["id"]

        art_r = client.post(
            "/kb/articles",
            headers=H,
            json={
                "title": "Counted Article",
                "body": "category count increment",
                "category_id": category_id,
                "status": "draft",
            },
        )
        assert art_r.status_code in (200, 201)

        list_cat_r = client.get("/kb/categories", headers=H)
        assert list_cat_r.status_code == 200
        category = next(c for c in list_cat_r.json()["categories"] if c["id"] == category_id)
        assert category["article_count"] >= 1

    def test_update_article_body_and_category(self, client: TestClient) -> None:
        cat_r = client.post(
            "/kb/categories",
            headers=H,
            json={"name": "Update Category", "description": "for article update"},
        )
        assert cat_r.status_code in (200, 201)
        new_category_id = cat_r.json()["category"]["id"]

        art_r = client.post(
            "/kb/articles",
            headers=H,
            json={"title": "Update Me", "body": "old body", "status": "draft"},
        )
        assert art_r.status_code in (200, 201)
        article_id = art_r.json()["article"]["id"]

        upd_r = client.patch(
            f"/kb/articles/{article_id}",
            headers=H,
            json={"body": "new body", "category_id": new_category_id},
        )
        assert upd_r.status_code in (200, 201)
        updated = upd_r.json()["article"]
        assert updated["body"] == "new body"
        assert updated["category_id"] == new_category_id


# ────────────────────────────────────────────────────────────────────────────
# Link-in-Bio
# ────────────────────────────────────────────────────────────────────────────

class TestLinkinbioCoverage:
    """Cover create page, list, update, add links, analytics."""

    def test_create_page(self, client: TestClient) -> None:
        r = client.post(
            "/linkinbio/pages",
            headers=H,
            json={
                "title": "My Brand Page",
                "bio": "We make great products",
                "theme": "dark",
                "custom_domain": "links.mybrand.com",
                "profile_image_url": "https://example.com/avatar.png",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["page"]["title"] == "My Brand Page"
        assert data["page"]["published"] is True

    def test_list_pages(self, client: TestClient) -> None:
        _create_linkinbio_page(client, title="List Seed")
        r = client.get("/linkinbio/pages", headers=H)
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_update_page(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="Update Seed")

        r = client.patch(
            f"/linkinbio/pages/{page_id}",
            headers=H,
            json={"title": "Updated Page Title", "bio": "Updated bio text", "theme": "gradient"},
        )
        assert r.status_code in (200, 201)
        assert r.json()["page"]["title"] == "Updated Page Title"

    def test_update_page_missing(self, client: TestClient) -> None:
        r = client.patch("/linkinbio/pages/9999", headers=H, json={"title": "Ghost"})
        assert r.status_code == 404

    def test_update_page_custom_domain(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="Domain Seed")

        r = client.patch(
            f"/linkinbio/pages/{page_id}",
            headers=H,
            json={"custom_domain": "updated.links.mybrand.com"},
        )
        assert r.status_code in (200, 201)
        assert r.json()["page"]["custom_domain"] == "updated.links.mybrand.com"

    def test_add_link(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="Add Link Seed")

        r = client.post(
            f"/linkinbio/pages/{page_id}/links",
            headers=H,
            json={
                "label": "Shop Now",
                "url": "https://shop.mybrand.com",
                "emoji": "🛍️",
                "is_product": True,
                "product_price": 29.99,
                "product_currency": "USD",
                "active": True,
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["link"]["label"] == "Shop Now"
        assert data["link"]["is_product"] is True

    def test_add_link_missing_page(self, client: TestClient) -> None:
        r = client.post(
            "/linkinbio/pages/9999/links",
            headers=H,
            json={"label": "Ghost Link", "url": "https://example.com"},
        )
        assert r.status_code == 404

    def test_page_analytics(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="Analytics Seed")

        r = client.get(f"/linkinbio/pages/{page_id}/analytics", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "analytics" in data
        assert data["analytics"]["total_links"] >= 1

    def test_page_analytics_missing(self, client: TestClient) -> None:
        r = client.get("/linkinbio/pages/9999/analytics", headers=H)
        assert r.status_code == 404

    def test_list_links(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="List Links Seed")

        create_r = client.post(
            f"/linkinbio/pages/{page_id}/links",
            headers=H,
            json={"label": "Creator Kit", "url": "https://example.com/kit", "emoji": "🧰"},
        )
        assert create_r.status_code in (200, 201)

        r = client.get(f"/linkinbio/pages/{page_id}/links", headers=H)
        assert r.status_code == 200
        assert r.json()["count"] >= 1

    def test_update_link_and_toggle(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="Update Link Seed")

        create_r = client.post(
            f"/linkinbio/pages/{page_id}/links",
            headers=H,
            json={"label": "Old Label", "url": "https://example.com/old", "emoji": "🔗"},
        )
        assert create_r.status_code in (200, 201)
        link_id = create_r.json()["link"]["id"]

        upd_r = client.patch(
            f"/linkinbio/pages/{page_id}/links/{link_id}",
            headers=H,
            json={"label": "New Label", "active": False},
        )
        assert upd_r.status_code in (200, 201)
        assert upd_r.json()["link"]["label"] == "New Label"
        assert upd_r.json()["link"]["active"] is False

    def test_record_link_click(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="Click Seed")

        create_r = client.post(
            f"/linkinbio/pages/{page_id}/links",
            headers=H,
            json={"label": "Click Me", "url": "https://example.com/click", "emoji": "🖱️"},
        )
        assert create_r.status_code in (200, 201)
        link_id = create_r.json()["link"]["id"]

        click_r = client.post(f"/linkinbio/pages/{page_id}/links/{link_id}/click", headers=H)
        assert click_r.status_code in (200, 201)
        assert click_r.json()["link"]["clicks"] >= 1

    def test_delete_link(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="Delete Link Seed")

        create_r = client.post(
            f"/linkinbio/pages/{page_id}/links",
            headers=H,
            json={"label": "Delete Link", "url": "https://example.com/delete", "emoji": "🗑️"},
        )
        assert create_r.status_code in (200, 201)
        link_id = create_r.json()["link"]["id"]

        delete_r = client.delete(f"/linkinbio/pages/{page_id}/links/{link_id}", headers=H)
        assert delete_r.status_code in (200, 201)

    def test_link_endpoints_missing(self, client: TestClient) -> None:
        r1 = client.get("/linkinbio/pages/9999/links", headers=H)
        assert r1.status_code == 404

        r2 = client.patch(
            "/linkinbio/pages/9999/links/9999",
            headers=H,
            json={"label": "Ghost"},
        )
        assert r2.status_code == 404

        r3 = client.delete("/linkinbio/pages/9999/links/9999", headers=H)
        assert r3.status_code == 404

        r4 = client.post("/linkinbio/pages/9999/links/9999/click", headers=H)
        assert r4.status_code == 404

    def test_record_page_view(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="View Seed")

        r = client.post(f"/linkinbio/pages/{page_id}/view", headers=H)
        assert r.status_code in (200, 201)
        assert r.json()["page"]["total_views"] >= 1

    def test_timeseries_analytics(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="Timeseries Seed")

        r = client.get(f"/linkinbio/pages/{page_id}/analytics/timeseries?days=14", headers=H)
        assert r.status_code == 200
        payload = r.json()["timeseries"]
        assert payload["days"] == 14
        assert len(payload["series"]) == 14
        assert "views" in payload["totals"]
        assert "clicks" in payload["totals"]
        assert "per_link" in payload

    def test_timeseries_per_link_clicks(self, client: TestClient) -> None:
        page_id = _create_linkinbio_page(client, title="Timeseries Link Seed")

        create_r = client.post(
            f"/linkinbio/pages/{page_id}/links",
            headers=H,
            json={"label": "Timeseries Link", "url": "https://example.com/ts", "emoji": "📈"},
        )
        assert create_r.status_code in (200, 201)
        link_id = create_r.json()["link"]["id"]

        click_r = client.post(f"/linkinbio/pages/{page_id}/links/{link_id}/click", headers=H)
        assert click_r.status_code in (200, 201)

        series_r = client.get(f"/linkinbio/pages/{page_id}/analytics/timeseries?days=7", headers=H)
        assert series_r.status_code == 200
        per_link = series_r.json()["timeseries"].get("per_link", [])
        target = next((item for item in per_link if item.get("link_id") == link_id), None)
        assert target is not None
        assert target["total_clicks"] >= 1

    def test_timeseries_analytics_missing_page(self, client: TestClient) -> None:
        r = client.get("/linkinbio/pages/9999/analytics/timeseries?days=14", headers=H)
        assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# Workflows
# ────────────────────────────────────────────────────────────────────────────

class TestWorkflowsCoverage:
    """Cover create/list/get/toggle/enroll/executions/analytics/delete."""

    def test_create_workflow(self, client: TestClient) -> None:
        r = client.post(
            "/workflows",
            headers=H,
            json={
                "name": "New Lead Welcome Sequence",
                "description": "Auto-send welcome email when a new contact is created",
                "trigger": {
                    "trigger_type": "contact_created",
                    "conditions": [{"field": "source", "op": "eq", "value": "website"}],
                },
                "steps": [
                    {"step_id": "step1", "action_type": "send_email", "config": {"template": "welcome_email"}, "next_step_id": "step2"},
                    {"step_id": "step2", "action_type": "delay", "delay_hours": 24, "next_step_id": "step3"},
                    {"step_id": "step3", "action_type": "add_tag", "config": {"tag": "welcomed"}},
                ],
                "re_enrollment": False,
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["workflow"]["name"] == "New Lead Welcome Sequence"
        assert data["workflow"]["step_count"] == 3

    def test_create_workflow_invalid_trigger_defaults(self, client: TestClient) -> None:
        r = client.post(
            "/workflows",
            headers=H,
            json={
                "name": "Default Trigger Workflow",
                "trigger": {"trigger_type": "not_a_real_trigger"},
                "steps": [],
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["workflow"]["trigger"]["trigger_type"] == "manual"

    def test_list_workflows(self, client: TestClient) -> None:
        r = client.get("/workflows", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_list_workflows_trigger_filter(self, client: TestClient) -> None:
        r = client.get("/workflows?trigger_type=contact_created", headers=H)
        assert r.status_code == 200
        for w in r.json()["workflows"]:
            assert w["trigger"]["trigger_type"] == "contact_created"

    def test_get_workflow(self, client: TestClient) -> None:
        list_r = client.get("/workflows", headers=H)
        wf_id = list_r.json()["workflows"][0]["id"]

        r = client.get(f"/workflows/{wf_id}", headers=H)
        assert r.status_code == 200
        assert r.json()["workflow"]["id"] == wf_id

    def test_get_workflow_missing(self, client: TestClient) -> None:
        r = client.get("/workflows/9999", headers=H)
        assert r.status_code == 404

    def test_toggle_workflow_pause(self, client: TestClient) -> None:
        list_r = client.get("/workflows", headers=H)
        wf_id = list_r.json()["workflows"][0]["id"]

        r = client.patch(f"/workflows/{wf_id}/toggle?active=false", headers=H)
        assert r.status_code in (200, 201)
        assert r.json()["workflow"]["status"] == "paused"

    def test_toggle_workflow_activate(self, client: TestClient) -> None:
        list_r = client.get("/workflows", headers=H)
        wf_id = list_r.json()["workflows"][0]["id"]

        r = client.patch(f"/workflows/{wf_id}/toggle?active=true", headers=H)
        assert r.status_code in (200, 201)
        assert r.json()["workflow"]["status"] == "active"

    def test_toggle_workflow_missing(self, client: TestClient) -> None:
        r = client.patch("/workflows/9999/toggle?active=true", headers=H)
        assert r.status_code == 404

    def test_enroll_contact(self, client: TestClient) -> None:
        list_r = client.get("/workflows", headers=H)
        wf_id = list_r.json()["workflows"][0]["id"]

        r = client.post(
            f"/workflows/{wf_id}/enroll",
            headers=H,
            json={"contact_id": "contact-abc-123", "contact_email": "lead@example.com"},
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["execution"]["contact_id"] == "contact-abc-123"
        assert data["execution"]["status"] == "completed"

    def test_enroll_contact_paused_workflow(self, client: TestClient) -> None:
        # Create a workflow and immediately pause it
        r_create = client.post(
            "/workflows",
            headers=H,
            json={"name": "Paused Workflow", "trigger": {"trigger_type": "manual"}, "steps": []},
        )
        wf_id = r_create.json()["workflow"]["id"]
        client.patch(f"/workflows/{wf_id}/toggle?active=false", headers=H)

        r = client.post(f"/workflows/{wf_id}/enroll", headers=H, json={"contact_id": "contact-x"})
        assert r.status_code == 409

    def test_enroll_missing_workflow(self, client: TestClient) -> None:
        r = client.post("/workflows/9999/enroll", headers=H, json={"contact_id": "contact-x"})
        assert r.status_code == 404

    def test_list_executions(self, client: TestClient) -> None:
        created = client.post(
            "/workflows",
            headers=H,
            json={"name": "Execution Seed Workflow", "trigger": {"trigger_type": "manual"}, "steps": []},
        )
        assert created.status_code in (200, 201)
        wf_id = created.json()["workflow"]["id"]

        # Ensure at least one execution exists for deterministic assertions.
        enroll = client.post(
            f"/workflows/{wf_id}/enroll",
            headers=H,
            json={"contact_id": "exec-check-001", "contact_email": "exec@example.com"},
        )
        assert enroll.status_code in (200, 201)

        r = client.get(f"/workflows/{wf_id}/executions", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_executions_missing_workflow(self, client: TestClient) -> None:
        r = client.get("/workflows/9999/executions", headers=H)
        assert r.status_code == 404

    def test_workflow_analytics(self, client: TestClient) -> None:
        list_r = client.get("/workflows", headers=H)
        wf_id = list_r.json()["workflows"][0]["id"]

        r = client.get(f"/workflows/{wf_id}/analytics", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "total_enrollments" in data
        assert "completion_rate" in data
        assert "avg_steps_executed" in data

    def test_workflow_analytics_missing(self, client: TestClient) -> None:
        r = client.get("/workflows/9999/analytics", headers=H)
        assert r.status_code == 404

    def test_delete_workflow(self, client: TestClient) -> None:
        r_create = client.post(
            "/workflows",
            headers=H,
            json={"name": "Delete Me Workflow", "trigger": {"trigger_type": "manual"}, "steps": []},
        )
        wf_id = r_create.json()["workflow"]["id"]

        r = client.delete(f"/workflows/{wf_id}", headers=H)
        assert r.status_code in (200, 201)
        assert r.json()["deleted"] is True

    def test_delete_workflow_missing(self, client: TestClient) -> None:
        r = client.delete("/workflows/9999", headers=H)
        assert r.status_code == 404


# ────────────────────────────────────────────────────────────────────────────
# Surveys
# ────────────────────────────────────────────────────────────────────────────

class TestSurveysCoverage:
    """Cover create NPS/CSAT/CES/custom, list, get, respond, list responses, analytics."""

    def test_create_nps_survey_auto_questions(self, client: TestClient) -> None:
        r = client.post(
            "/surveys",
            headers=H,
            json={
                "name": "Product NPS Survey",
                "survey_type": "nps",
                "description": "How likely are you to recommend us?",
                "trigger_event": "deal_closed",
                "trigger_delay_hours": 48,
                "follow_up_threshold": 6,
                "send_via": "email",
                "questions": [],  # should auto-generate NPS questions
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["survey"]["survey_type"] == "nps"
        assert len(data["survey"]["questions"]) >= 1

    def test_create_csat_survey_auto_questions(self, client: TestClient) -> None:
        r = client.post(
            "/surveys",
            headers=H,
            json={
                "name": "Support CSAT Survey",
                "survey_type": "csat",
                "trigger_event": "ticket_resolved",
                "questions": [],  # should auto-generate CSAT questions
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["survey"]["survey_type"] == "csat"

    def test_create_ces_survey_auto_questions(self, client: TestClient) -> None:
        r = client.post(
            "/surveys",
            headers=H,
            json={
                "name": "Onboarding CES Survey",
                "survey_type": "ces",
                "trigger_event": "onboarding_complete",
                "questions": [],  # should auto-generate CES questions
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["survey"]["survey_type"] == "ces"

    def test_create_custom_survey_with_questions(self, client: TestClient) -> None:
        r = client.post(
            "/surveys",
            headers=H,
            json={
                "name": "Product Feedback Survey",
                "survey_type": "custom",
                "trigger_event": "manual",
                "questions": [
                    {
                        "question_id": "q1",
                        "question_text": "How would you rate our product?",
                        "question_type": "scale",
                        "scale_min": 1,
                        "scale_max": 5,
                        "required": True,
                        "options": [],
                    },
                ],
            },
        )
        assert r.status_code in (200, 201)
        assert len(r.json()["survey"]["questions"]) == 1

    def test_create_survey_invalid_type_defaults(self, client: TestClient) -> None:
        r = client.post(
            "/surveys",
            headers=H,
            json={"name": "Bad Type Survey", "survey_type": "not_a_type", "trigger_event": "not_a_trigger"},
        )
        assert r.status_code in (200, 201)
        assert r.json()["survey"]["survey_type"] == "custom"
        assert r.json()["survey"]["trigger_event"] == "manual"

    def test_list_surveys(self, client: TestClient) -> None:
        r = client.get("/surveys", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 4

    def test_list_surveys_type_filter(self, client: TestClient) -> None:
        r = client.get("/surveys?survey_type=nps", headers=H)
        assert r.status_code == 200
        for s in r.json()["surveys"]:
            assert s["survey_type"] == "nps"

    def test_get_survey(self, client: TestClient) -> None:
        list_r = client.get("/surveys", headers=H)
        sv_id = list_r.json()["surveys"][0]["id"]

        r = client.get(f"/surveys/{sv_id}", headers=H)
        assert r.status_code == 200
        assert r.json()["survey"]["id"] == sv_id

    def test_get_survey_missing(self, client: TestClient) -> None:
        r = client.get("/surveys/9999", headers=H)
        assert r.status_code == 404

    def test_submit_nps_response_promoter(self, client: TestClient) -> None:
        # Get NPS survey id
        list_r = client.get("/surveys?survey_type=nps", headers=H)
        sv_id = list_r.json()["surveys"][0]["id"]

        r = client.post(
            f"/surveys/{sv_id}/respond",
            headers=H,
            json={
                "survey_id": sv_id,
                "respondent_email": "promoter@example.com",
                "respondent_name": "Happy Customer",
                "primary_score": 9,
                "verbatim": "Love your product! Definitely recommending to everyone.",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["response"]["nps_category"] == "promoter"
        assert data["response"]["requires_follow_up"] is False

    def test_submit_nps_response_detractor(self, client: TestClient) -> None:
        list_r = client.get("/surveys?survey_type=nps", headers=H)
        sv_id = list_r.json()["surveys"][0]["id"]

        r = client.post(
            f"/surveys/{sv_id}/respond",
            headers=H,
            json={
                "survey_id": sv_id,
                "respondent_email": "detractor@example.com",
                "primary_score": 3,
                "verbatim": "Product doesn't work as expected.",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["response"]["nps_category"] == "detractor"
        assert data["response"]["requires_follow_up"] is True

    def test_submit_nps_response_passive(self, client: TestClient) -> None:
        list_r = client.get("/surveys?survey_type=nps", headers=H)
        sv_id = list_r.json()["surveys"][0]["id"]

        r = client.post(
            f"/surveys/{sv_id}/respond",
            headers=H,
            json={
                "survey_id": sv_id,
                "respondent_email": "passive@example.com",
                "primary_score": 7,
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["response"]["nps_category"] == "passive"

    def test_submit_response_missing_survey(self, client: TestClient) -> None:
        r = client.post(
            "/surveys/9999/respond",
            headers=H,
            json={
                "survey_id": 9999,
                "respondent_email": "ghost@example.com",
                "primary_score": 5,
            },
        )
        assert r.status_code == 404

    def test_list_responses(self, client: TestClient) -> None:
        list_r = client.get("/surveys?survey_type=nps", headers=H)
        sv_id = list_r.json()["surveys"][0]["id"]

        r = client.get(f"/surveys/{sv_id}/responses", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 2

    def test_list_responses_missing_survey(self, client: TestClient) -> None:
        r = client.get("/surveys/9999/responses", headers=H)
        assert r.status_code == 404

    def test_survey_analytics_nps(self, client: TestClient) -> None:
        list_r = client.get("/surveys?survey_type=nps", headers=H)
        sv_id = list_r.json()["surveys"][0]["id"]

        r = client.get(f"/surveys/{sv_id}/analytics", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["survey_type"] == "nps"
        assert "nps_score" in data
        assert "promoters" in data
        assert "detractors" in data
        assert "follow_up_pending" in data

    def test_survey_analytics_missing(self, client: TestClient) -> None:
        r = client.get("/surveys/9999/analytics", headers=H)
        assert r.status_code == 404
