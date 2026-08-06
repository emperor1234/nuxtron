"""
Tests for Tickets, Knowledge Base, Surveys, Workflows, and Sequences routers.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


# ── Standalone Tickets ────────────────────────────────────────────────────────

class TestTicketsRouter:
    def test_list_tickets(self, client: TestClient) -> None:
        r = client.get("/tickets", headers=H)
        assert r.status_code == 200

    def test_create_ticket(self, client: TestClient) -> None:
        r = client.post("/tickets", headers=H, json={
            "subject": "Cannot login",
            "customer_email": "user@example.com",
            "priority": "high",
            "channel": "email",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert "id" in data.get("ticket", data)

    def test_get_ticket(self, client: TestClient) -> None:
        r = client.post("/tickets", headers=H, json={
            "subject": "Fetch test",
            "customer_email": "test@example.com",
        })
        tid = r.json().get("ticket", r.json()).get("id", 1)
        r2 = client.get(f"/tickets/{tid}", headers=H)
        assert r2.status_code == 200

    def test_update_ticket(self, client: TestClient) -> None:
        r = client.post("/tickets", headers=H, json={
            "subject": "Update test",
            "customer_email": "patch@example.com",
        })
        tid = r.json().get("ticket", r.json()).get("id", 1)
        r2 = client.patch(f"/tickets/{tid}", headers=H, json={"status": "in_progress"})
        assert r2.status_code < 500

    def test_add_comment(self, client: TestClient) -> None:
        r = client.post("/tickets", headers=H, json={
            "subject": "Comment test",
            "customer_email": "cmt@example.com",
        })
        tid = r.json().get("ticket", r.json()).get("id", 1)
        r2 = client.post(f"/tickets/{tid}/comments", headers=H, json={
            "body": "Looking into this issue now.",
            "is_internal": False,
        })
        assert r2.status_code in {200, 201}

    def test_get_comments(self, client: TestClient) -> None:
        r = client.post("/tickets", headers=H, json={
            "subject": "Get comments test",
            "customer_email": "gc@example.com",
        })
        tid = r.json().get("ticket", r.json()).get("id", 1)
        r2 = client.get(f"/tickets/{tid}/comments", headers=H)
        assert r2.status_code == 200

    def test_csat_response(self, client: TestClient) -> None:
        r = client.post("/tickets", headers=H, json={
            "subject": "CSAT test",
            "customer_email": "csat@example.com",
        })
        tid = r.json().get("ticket", r.json()).get("id", 1)
        r2 = client.post(f"/tickets/{tid}/csat", headers=H, json={
            "score": 5,
            "comment": "Great support!",
        })
        assert r2.status_code < 500

    def test_sla_config(self, client: TestClient) -> None:
        r = client.put("/tickets/sla-config", headers=H, json={
            "priority": "urgent",
            "first_response_hours": 1,
            "resolution_hours": 8,
        })
        assert r.status_code < 500

    def test_tickets_analytics(self, client: TestClient) -> None:
        r = client.get("/tickets/analytics/summary", headers=H)
        assert r.status_code == 200


# ── Knowledge Base ────────────────────────────────────────────────────────────

class TestKnowledgeBase:
    def test_list_categories(self, client: TestClient) -> None:
        r = client.get("/kb/categories", headers=H)
        assert r.status_code == 200

    def test_create_category(self, client: TestClient) -> None:
        r = client.post("/kb/categories", headers=H, json={
            "name": "Getting Started",
            "description": "Beginner guides",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert "id" in data.get("category", data)

    def test_list_articles(self, client: TestClient) -> None:
        r = client.get("/kb/articles", headers=H)
        assert r.status_code == 200

    def test_create_article(self, client: TestClient) -> None:
        r = client.post("/kb/articles", headers=H, json={
            "title": "How to get started",
            "body": "Welcome to our platform. Here is everything you need to know...",
            "status": "published",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert "id" in data.get("article", data)

    def test_get_article(self, client: TestClient) -> None:
        r = client.post("/kb/articles", headers=H, json={
            "title": "Fetch me",
            "body": "Content here for fetching.",
        })
        aid = r.json().get("article", {}).get("id", r.json().get("id", 1))
        r2 = client.get(f"/kb/articles/{aid}", headers=H)
        assert r2.status_code == 200

    def test_update_article(self, client: TestClient) -> None:
        r = client.post("/kb/articles", headers=H, json={
            "title": "Update me",
            "body": "Original content.",
        })
        aid = r.json().get("article", {}).get("id", r.json().get("id", 1))
        r2 = client.patch(f"/kb/articles/{aid}", headers=H, json={
            "title": "Updated Title",
            "status": "published",
        })
        assert r2.status_code < 500

    def test_delete_article(self, client: TestClient) -> None:
        r = client.post("/kb/articles", headers=H, json={
            "title": "Delete me",
            "body": "To be deleted.",
        })
        aid = r.json().get("article", {}).get("id", r.json().get("id", 1))
        r2 = client.delete(f"/kb/articles/{aid}", headers=H)
        assert r2.status_code in {200, 204}

    def test_article_feedback(self, client: TestClient) -> None:
        r = client.post("/kb/articles", headers=H, json={
            "title": "Feedback test",
            "body": "Rate this article.",
        })
        aid = r.json().get("article", {}).get("id", r.json().get("id", 1))
        r2 = client.post(f"/kb/articles/{aid}/feedback", headers=H, json={
            "helpful": True,
            "comment": "Very helpful!",
        })
        assert r2.status_code < 500

    def test_search(self, client: TestClient) -> None:
        r = client.get("/kb/search?q=started", headers=H)
        assert r.status_code == 200

    def test_analytics_summary(self, client: TestClient) -> None:
        r = client.get("/kb/analytics/summary", headers=H)
        assert r.status_code == 200


# ── Surveys ───────────────────────────────────────────────────────────────────

class TestSurveys:
    def test_list_surveys(self, client: TestClient) -> None:
        r = client.get("/surveys", headers=H)
        assert r.status_code == 200

    def test_create_survey(self, client: TestClient) -> None:
        r = client.post("/surveys", headers=H, json={
            "name": "Customer NPS Q1",
            "survey_type": "nps",
            "questions": [],
            "trigger_event": "manual",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert "id" in data.get("survey", data)

    def test_get_survey(self, client: TestClient) -> None:
        r = client.post("/surveys", headers=H, json={"name": "Fetch Survey"})
        sid = r.json().get("survey", {}).get("id", r.json().get("id", 1))
        r2 = client.get(f"/surveys/{sid}", headers=H)
        assert r2.status_code == 200

    def test_survey_analytics(self, client: TestClient) -> None:
        r = client.post("/surveys", headers=H, json={"name": "Analytics Survey"})
        sid = r.json().get("survey", {}).get("id", r.json().get("id", 1))
        r2 = client.get(f"/surveys/{sid}/analytics", headers=H)
        assert r2.status_code == 200

    def test_submit_response(self, client: TestClient) -> None:
        r = client.post("/surveys", headers=H, json={"name": "Response Survey", "survey_type": "nps"})
        sid = r.json().get("survey", {}).get("id", r.json().get("id", 1))
        r2 = client.post(f"/surveys/{sid}/respond", headers=H, json={
            "survey_id": sid,
            "respondent_email": "responder@example.com",
            "answers": [],
            "primary_score": 9,
        })
        assert r2.status_code < 500

    def test_get_responses(self, client: TestClient) -> None:
        r = client.post("/surveys", headers=H, json={"name": "Responses Survey"})
        sid = r.json().get("survey", {}).get("id", r.json().get("id", 1))
        r2 = client.get(f"/surveys/{sid}/responses", headers=H)
        assert r2.status_code == 200


# ── Workflows ─────────────────────────────────────────────────────────────────

class TestWorkflows:
    def test_list_workflows(self, client: TestClient) -> None:
        r = client.get("/workflows", headers=H)
        assert r.status_code == 200

    def test_create_workflow(self, client: TestClient) -> None:
        r = client.post("/workflows", headers=H, json={
            "name": "Welcome Workflow",
            "trigger": {
                "trigger_type": "contact_created",
                "conditions": [],
            },
            "steps": [],
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert "id" in data.get("workflow", data)

    def test_get_workflow(self, client: TestClient) -> None:
        r = client.post("/workflows", headers=H, json={
            "name": "Fetch Workflow",
            "trigger": {"trigger_type": "manual"},
        })
        wid = r.json().get("workflow", {}).get("id", r.json().get("id", 1))
        r2 = client.get(f"/workflows/{wid}", headers=H)
        assert r2.status_code == 200

    def test_delete_workflow(self, client: TestClient) -> None:
        r = client.post("/workflows", headers=H, json={
            "name": "Delete Workflow",
            "trigger": {"trigger_type": "manual"},
        })
        wid = r.json().get("workflow", {}).get("id", r.json().get("id", 1))
        r2 = client.delete(f"/workflows/{wid}", headers=H)
        assert r2.status_code in {200, 204}

    def test_workflow_toggle(self, client: TestClient) -> None:
        r = client.post("/workflows", headers=H, json={
            "name": "Toggle Workflow",
            "trigger": {"trigger_type": "manual"},
        })
        wid = r.json().get("workflow", {}).get("id", r.json().get("id", 1))
        r2 = client.patch(f"/workflows/{wid}/toggle", headers=H)
        assert r2.status_code < 500

    def test_enroll_workflow(self, client: TestClient) -> None:
        r = client.post("/workflows", headers=H, json={
            "name": "Enroll Workflow",
            "trigger": {"trigger_type": "manual"},
        })
        wid = r.json().get("id", 1)
        r2 = client.post(f"/workflows/{wid}/enroll", headers=H, json={
            "contact_id": "contact-123",
            "contact_email": "enroll@example.com",
        })
        assert r2.status_code < 500

    def test_workflow_analytics(self, client: TestClient) -> None:
        r = client.post("/workflows", headers=H, json={
            "name": "Analytics Workflow",
            "trigger": {"trigger_type": "manual"},
        })
        wid = r.json().get("id", 1)
        r2 = client.get(f"/workflows/{wid}/analytics", headers=H)
        assert r2.status_code < 500

    def test_workflow_executions(self, client: TestClient) -> None:
        r = client.post("/workflows", headers=H, json={
            "name": "Executions Workflow",
            "trigger": {"trigger_type": "manual"},
        })
        wid = r.json().get("id", 1)
        r2 = client.get(f"/workflows/{wid}/executions", headers=H)
        assert r2.status_code < 500


# ── Sequences ─────────────────────────────────────────────────────────────────

class TestSequences:
    def test_list_sequences(self, client: TestClient) -> None:
        r = client.get("/sequences", headers=H)
        assert r.status_code == 200

    def test_create_sequence(self, client: TestClient) -> None:
        r = client.post("/sequences", headers=H, json={
            "name": "Welcome Cadence",
            "description": "5-touch welcome sequence",
            "steps": [
                {"step_type": "email", "delay_days": 0, "subject": "Welcome!", "body": "Hi there"},
                {"step_type": "email", "delay_days": 3, "subject": "Check-in", "body": "How are things?"},
            ],
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert "id" in data.get("sequence", data)

    def test_get_sequence(self, client: TestClient) -> None:
        r = client.post("/sequences", headers=H, json={"name": "Fetch Sequence"})
        sid = (r.json().get("sequence") or r.json()).get("id", 1)
        r2 = client.get(f"/sequences/{sid}", headers=H)
        assert r2.status_code == 200

    def test_delete_sequence(self, client: TestClient) -> None:
        r = client.post("/sequences", headers=H, json={"name": "Delete Sequence"})
        sid = (r.json().get("sequence") or r.json()).get("id", 1)
        r2 = client.delete(f"/sequences/{sid}", headers=H)
        assert r2.status_code in {200, 204}

    def test_enroll_contact(self, client: TestClient) -> None:
        r = client.post("/sequences", headers=H, json={"name": "Enroll Sequence"})
        sid = r.json().get("id", 1)
        r2 = client.post(f"/sequences/{sid}/enroll", headers=H, json={
            "sequence_id": sid,
            "contact_id": "c-001",
            "contact_email": "enroll@example.com",
        })
        assert r2.status_code < 500

    def test_sequence_analytics(self, client: TestClient) -> None:
        r = client.post("/sequences", headers=H, json={"name": "Analytics Sequence"})
        sid = r.json().get("id", 1)
        r2 = client.get(f"/sequences/{sid}/analytics", headers=H)
        assert r2.status_code < 500

    def test_sequence_enrollments(self, client: TestClient) -> None:
        r = client.post("/sequences", headers=H, json={"name": "Enrollments Sequence"})
        sid = r.json().get("id", 1)
        r2 = client.get(f"/sequences/{sid}/enrollments", headers=H)
        assert r2.status_code < 500
