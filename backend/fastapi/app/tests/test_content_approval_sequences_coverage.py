"""Coverage for sequences.py happy paths and edge cases.

Content approval coverage lives in test_content_approval_durable.py.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "approval-seq-coverage-tenant"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestSequencesCoverage:
    """Cover create, list, get, enroll, step outcomes, analytics, delete."""

    def test_create_sequence(self, client: TestClient) -> None:
        r = client.post(
            "/sequences",
            headers=H,
            json={
                "name": "Cold Outreach Sequence",
                "description": "5-touch cold outreach for SaaS prospects",
                "steps": [
                    {"step_type": "email", "delay_days": 0, "delay_hours": 0, "subject": "Intro", "body": "Hi there"},
                    {"step_type": "linkedin", "delay_days": 2, "delay_hours": 0, "task_description": "Connect on LinkedIn"},
                    {"step_type": "call", "delay_days": 5, "delay_hours": 0, "task_description": "Discovery call"},
                    {"step_type": "invalid_type", "delay_days": 7, "delay_hours": 0},  # should default to email
                ],
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["sequence"]["step_count"] == 4
        # invalid_type step should be mapped to 'email'
        assert data["sequence"]["steps"][3]["step_type"] == "email"

    def test_list_sequences(self, client: TestClient) -> None:
        r = client.get("/sequences", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "sequences" in data
        assert data["total"] >= 1

    def test_list_sequences_pagination(self, client: TestClient) -> None:
        r = client.get("/sequences?limit=5&offset=0", headers=H)
        assert r.status_code == 200

    def test_get_sequence(self, client: TestClient) -> None:
        # Get the first sequence
        list_r = client.get("/sequences", headers=H)
        seq_id = list_r.json()["sequences"][0]["id"]

        r = client.get(f"/sequences/{seq_id}", headers=H)
        assert r.status_code == 200
        assert r.json()["sequence"]["id"] == seq_id

    def test_get_sequence_missing(self, client: TestClient) -> None:
        r = client.get("/sequences/9999", headers=H)
        assert r.status_code == 404

    def test_enroll_contact(self, client: TestClient) -> None:
        list_r = client.get("/sequences", headers=H)
        seq_id = list_r.json()["sequences"][0]["id"]

        r = client.post(
            f"/sequences/{seq_id}/enroll",
            headers=H,
            json={
                "sequence_id": seq_id,
                "contact_id": "contact-001",
                "contact_email": "john.doe@example.com",
                "contact_name": "John Doe",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["enrollment"]["contact_id"] == "contact-001"
        assert data["enrollment"]["status"] == "active"

    def test_enroll_already_enrolled(self, client: TestClient) -> None:
        # Enroll same contact again - should return already_enrolled
        list_r = client.get("/sequences", headers=H)
        seq_id = list_r.json()["sequences"][0]["id"]

        r = client.post(
            f"/sequences/{seq_id}/enroll",
            headers=H,
            json={
                "sequence_id": seq_id,
                "contact_id": "contact-001",
                "contact_email": "john.doe@example.com",
                "contact_name": "John Doe",
            },
        )
        assert r.status_code in (200, 201)
        assert r.json()["status"] == "already_enrolled"

    def test_enroll_missing_sequence(self, client: TestClient) -> None:
        r = client.post(
            "/sequences/9999/enroll",
            headers=H,
            json={
                "sequence_id": 9999,
                "contact_id": "contact-x",
                "contact_email": "x@example.com",
            },
        )
        assert r.status_code == 404

    def test_list_enrollments(self, client: TestClient) -> None:
        list_r = client.get("/sequences", headers=H)
        seq_id = list_r.json()["sequences"][0]["id"]

        r = client.get(f"/sequences/{seq_id}/enrollments", headers=H)
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_list_enrollments_with_status_filter(self, client: TestClient) -> None:
        list_r = client.get("/sequences", headers=H)
        seq_id = list_r.json()["sequences"][0]["id"]
        r = client.get(f"/sequences/{seq_id}/enrollments?status=active", headers=H)
        assert r.status_code == 200

    def test_list_enrollments_missing_sequence(self, client: TestClient) -> None:
        r = client.get("/sequences/9999/enrollments", headers=H)
        assert r.status_code == 404

    def test_record_step_outcome_replied(self, client: TestClient) -> None:
        # Get enrollment id
        list_r = client.get("/sequences", headers=H)
        seq_id = list_r.json()["sequences"][0]["id"]
        enr_r = client.get(f"/sequences/{seq_id}/enrollments", headers=H)
        enr_id = enr_r.json()["enrollments"][0]["id"]

        # Record "replied" outcome — should pause the sequence
        r = client.post(
            f"/sequences/enrollments/{enr_id}/step-outcome",
            headers=H,
            json={"outcome": "replied", "notes": "Prospect replied interested"},
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["enrollment"]["status"] == "replied"
        assert data["enrollment"]["reply_received"] is True

    def test_record_step_outcome_missing_enrollment(self, client: TestClient) -> None:
        r = client.post(
            "/sequences/enrollments/9999/step-outcome",
            headers=H,
            json={"outcome": "called", "notes": "Voicemail"},
        )
        assert r.status_code == 404

    def test_record_step_outcome_progress(self, client: TestClient) -> None:
        # Create a fresh enrollment and advance steps
        list_r = client.get("/sequences", headers=H)
        seq_id = list_r.json()["sequences"][0]["id"]
        enr_r = client.post(
            f"/sequences/{seq_id}/enroll",
            headers=H,
            json={
                "sequence_id": seq_id,
                "contact_id": "contact-002",
                "contact_email": "jane@example.com",
                "contact_name": "Jane Smith",
            },
        )
        enr_id = enr_r.json()["enrollment"]["id"]

        # Record 'called' outcome (advances step)
        r = client.post(
            f"/sequences/enrollments/{enr_id}/step-outcome",
            headers=H,
            json={"outcome": "called", "notes": "Called and left voicemail"},
        )
        assert r.status_code in (200, 201)
        assert r.json()["enrollment"]["current_step"] >= 2

    def test_sequence_analytics(self, client: TestClient) -> None:
        list_r = client.get("/sequences", headers=H)
        seq_id = list_r.json()["sequences"][0]["id"]

        r = client.get(f"/sequences/{seq_id}/analytics", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "total_enrollments" in data
        assert "reply_rate" in data

    def test_sequence_analytics_missing(self, client: TestClient) -> None:
        r = client.get("/sequences/9999/analytics", headers=H)
        assert r.status_code == 404

    def test_record_step_outcome_completed_sets_completed_status(self, client: TestClient) -> None:
        # Create a single-step sequence so completed outcome can finish enrollment.
        seq_r = client.post(
            "/sequences",
            headers=H,
            json={
                "name": "Single Step Sequence",
                "description": "completion branch",
                "steps": [{"step_type": "email", "delay_days": 0, "delay_hours": 0}],
            },
        )
        assert seq_r.status_code in (200, 201)
        seq_id = seq_r.json()["sequence"]["id"]

        enr_r = client.post(
            f"/sequences/{seq_id}/enroll",
            headers=H,
            json={
                "sequence_id": seq_id,
                "contact_id": "contact-completed",
                "contact_email": "completed@example.com",
            },
        )
        assert enr_r.status_code in (200, 201)
        enr_id = enr_r.json()["enrollment"]["id"]

        out_r = client.post(
            f"/sequences/enrollments/{enr_id}/step-outcome",
            headers=H,
            json={"outcome": "completed", "notes": "Final step done"},
        )
        assert out_r.status_code in (200, 201)
        assert out_r.json()["enrollment"]["status"] == "completed"

    def test_delete_sequence(self, client: TestClient) -> None:
        # Create a fresh sequence to delete
        r = client.post(
            "/sequences",
            headers=H,
            json={"name": "Delete Me Sequence", "description": "Will be deleted", "steps": []},
        )
        seq_id = r.json()["sequence"]["id"]

        # Enroll someone (to test pause on delete)
        client.post(
            f"/sequences/{seq_id}/enroll",
            headers=H,
            json={
                "sequence_id": seq_id,
                "contact_id": "delete-contact",
                "contact_email": "del@example.com",
            },
        )

        r2 = client.delete(f"/sequences/{seq_id}", headers=H)
        assert r2.status_code in (200, 201)
        assert r2.json()["deleted"] is True

    def test_delete_missing_sequence(self, client: TestClient) -> None:
        r = client.delete("/sequences/9999", headers=H)
        assert r.status_code == 404
