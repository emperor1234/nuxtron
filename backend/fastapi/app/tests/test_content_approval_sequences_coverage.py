"""Coverage for content_approval.py and sequences.py happy paths and edge cases."""
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


class TestContentApprovalCoverage:
    """Cover configure, get config, submit, list, decide (approve/reject), comments."""

    def test_get_config_before_setup(self, client: TestClient) -> None:
        # Config not set yet — should return status ok with config=None
        H2 = {"X-API-Key": "test-api-key", "X-Tenant-Id": "approval-empty-tenant"}
        r = client.get("/content/approval/config", headers=H2)
        assert r.status_code == 200
        assert r.json()["config"] is None

    def test_configure_approval_chain(self, client: TestClient) -> None:
        r = client.put(
            "/content/approval/config",
            headers=H,
            json={"levels": ["editor", "legal", "manager"], "require_all_levels": True, "expiry_hours": 72},
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["config"]["levels"] == ["editor", "legal", "manager"]
        assert data["config"]["expiry_hours"] == 72

    def test_update_existing_config(self, client: TestClient) -> None:
        # Update the config (already exists, covers the update branch)
        r = client.put(
            "/content/approval/config",
            headers=H,
            json={"levels": ["editor", "manager"], "require_all_levels": False, "expiry_hours": 24},
        )
        assert r.status_code in (200, 201)
        assert r.json()["config"]["expiry_hours"] == 24

    def test_get_config_after_setup(self, client: TestClient) -> None:
        r = client.get("/content/approval/config", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["config"] is not None
        assert "levels" in data["config"]

    def test_submit_for_approval(self, client: TestClient) -> None:
        r = client.post(
            "/content/approval/requests",
            headers=H,
            json={
                "scheduled_post_id": 101,
                "platform": "linkedin",
                "content_preview": "Our Q2 results are in!",
                "requested_by": "marketer@example.com",
                "campaign_tag": "q2-results",
                "due_at": "2026-05-20T12:00:00Z",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["request"]["status"] == "pending"
        assert data["request"]["platform"] == "linkedin"

    def test_submit_duplicate_rejected(self, client: TestClient) -> None:
        # Submitting again for the same scheduled_post_id should return 400
        r = client.post(
            "/content/approval/requests",
            headers=H,
            json={
                "scheduled_post_id": 101,
                "platform": "linkedin",
                "content_preview": "Duplicate submission",
                "requested_by": "marketer@example.com",
            },
        )
        assert r.status_code == 400

    def test_list_approval_requests(self, client: TestClient) -> None:
        r = client.get("/content/approval/requests", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["count"] >= 1
        assert len(data["requests"]) >= 1

    def test_list_with_status_filter(self, client: TestClient) -> None:
        r = client.get("/content/approval/requests?approval_status=pending", headers=H)
        assert r.status_code == 200

    def test_approve_request_single_level(self, client: TestClient) -> None:
        # With require_all_levels=False (set above), first approval should finalize
        r = client.post(
            "/content/approval/requests",
            headers=H,
            json={
                "scheduled_post_id": 200,
                "platform": "twitter",
                "content_preview": "Tweet content for approval",
                "requested_by": "creator@example.com",
            },
        )
        assert r.status_code in (200, 201)
        rid = r.json()["request"]["id"]

        r2 = client.post(
            f"/content/approval/requests/{rid}/decision",
            headers=H,
            json={"decision": "approved", "reviewer_role": "editor", "comment": "Looks great!"},
        )
        assert r2.status_code in (200, 201)
        data = r2.json()
        assert data["decision"] == "approved"
        # With require_all_levels=False, one approval is enough
        assert data["request"]["status"] == "approved"

    def test_reject_request(self, client: TestClient) -> None:
        r = client.post(
            "/content/approval/requests",
            headers=H,
            json={
                "scheduled_post_id": 201,
                "platform": "facebook",
                "content_preview": "Content for rejection test",
                "requested_by": "creator@example.com",
            },
        )
        assert r.status_code in (200, 201)
        rid = r.json()["request"]["id"]

        r2 = client.post(
            f"/content/approval/requests/{rid}/decision",
            headers=H,
            json={"decision": "rejected", "reviewer_role": "manager", "comment": "Not brand compliant"},
        )
        assert r2.status_code in (200, 201)
        data = r2.json()
        assert data["request"]["status"] == "rejected"

    def test_decide_on_non_pending(self, client: TestClient) -> None:
        # Get the approved request from previous test, try to decide again
        r = client.get("/content/approval/requests?approval_status=approved", headers=H)
        if r.json()["count"] > 0:
            rid = r.json()["requests"][0]["id"]
            r2 = client.post(
                f"/content/approval/requests/{rid}/decision",
                headers=H,
                json={"decision": "approved", "reviewer_role": "editor"},
            )
            assert r2.status_code == 400

    def test_decide_missing_request(self, client: TestClient) -> None:
        r = client.post(
            "/content/approval/requests/9999/decision",
            headers=H,
            json={"decision": "approved", "reviewer_role": "editor"},
        )
        assert r.status_code == 404

    def test_decide_invalid_role(self, client: TestClient) -> None:
        # Submit a new request
        r = client.post(
            "/content/approval/requests",
            headers=H,
            json={
                "scheduled_post_id": 202,
                "platform": "instagram",
                "content_preview": "Testing invalid role",
                "requested_by": "creator@example.com",
            },
        )
        assert r.status_code in (200, 201)
        rid = r.json()["request"]["id"]

        r2 = client.post(
            f"/content/approval/requests/{rid}/decision",
            headers=H,
            json={"decision": "approved", "reviewer_role": "cfo"},  # not in levels
        )
        assert r2.status_code == 422

    def test_list_comments_on_request(self, client: TestClient) -> None:
        # Create a request and approve with comment
        r = client.post(
            "/content/approval/requests",
            headers=H,
            json={
                "scheduled_post_id": 203,
                "platform": "linkedin",
                "content_preview": "Comment test content",
                "requested_by": "user@example.com",
            },
        )
        rid = r.json()["request"]["id"]
        client.post(
            f"/content/approval/requests/{rid}/decision",
            headers=H,
            json={"decision": "approved", "reviewer_role": "editor", "comment": "Nice post!"},
        )

        r2 = client.get(f"/content/approval/requests/{rid}/comments", headers=H)
        assert r2.status_code == 200
        assert r2.json()["count"] >= 1

    def test_list_comments_missing_request(self, client: TestClient) -> None:
        r = client.get("/content/approval/requests/9999/comments", headers=H)
        assert r.status_code == 404

    def test_approve_with_require_all_levels(self, client: TestClient) -> None:
        """Cover the require_all_levels=True path: partial approval doesn't finalize."""
        H3 = {"X-API-Key": "test-api-key", "X-Tenant-Id": "approval-all-levels-tenant"}
        # Set up config requiring all levels
        client.put(
            "/content/approval/config",
            headers=H3,
            json={"levels": ["editor", "legal"], "require_all_levels": True, "expiry_hours": 48},
        )

        r = client.post(
            "/content/approval/requests",
            headers=H3,
            json={
                "scheduled_post_id": 301,
                "platform": "linkedin",
                "content_preview": "Multi-level approval test",
                "requested_by": "creator@example.com",
            },
        )
        rid = r.json()["request"]["id"]

        # First level approval
        r2 = client.post(
            f"/content/approval/requests/{rid}/decision",
            headers=H3,
            json={"decision": "approved", "reviewer_role": "editor"},
        )
        assert r2.status_code in (200, 201)
        # Not fully approved yet
        assert r2.json()["request"]["status"] == "pending"

        # Second level approval - now fully approved
        r3 = client.post(
            f"/content/approval/requests/{rid}/decision",
            headers=H3,
            json={"decision": "approved", "reviewer_role": "legal"},
        )
        assert r3.status_code in (200, 201)
        assert r3.json()["request"]["status"] == "approved"


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
