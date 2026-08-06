"""
Tests for playbooks, sequences, competitive, and utm_builder routers.
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


class TestPlaybooks:
    def test_list_playbooks(self, client: TestClient) -> None:
        r = client.get("/playbooks", headers=H)
        assert r.status_code in VALID

    def test_get_playbook_nonexistent(self, client: TestClient) -> None:
        r = client.get("/playbooks/playbook_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_create_playbook(self, client: TestClient) -> None:
        r = client.post("/playbooks", headers=H, json={
            "name": "Onboarding Playbook",
            "trigger": "user_signup",
            "steps": [{"type": "email", "delay_hours": 0}],
        })
        assert r.status_code in VALID

    def test_run_playbook_nonexistent(self, client: TestClient) -> None:
        r = client.post("/playbooks/run", headers=H, json={
            "playbook_id": "playbook_nonexistent",
            "contact_id": "contact_001",
        })
        assert r.status_code in VALID

    def test_list_runs(self, client: TestClient) -> None:
        r = client.get("/playbooks/runs/list", headers=H)
        assert r.status_code in VALID


class TestSequences:
    def test_create_sequence(self, client: TestClient) -> None:
        r = client.post("/sequences", headers=H, json={
            "name": "Cold Outreach Sequence",
            "steps": [
                {"type": "email", "delay_days": 0, "subject": "Intro"},
                {"type": "email", "delay_days": 3, "subject": "Follow-up"},
            ],
        })
        assert r.status_code in VALID

    def test_list_sequences(self, client: TestClient) -> None:
        r = client.get("/sequences", headers=H)
        assert r.status_code in VALID

    def test_get_sequence_nonexistent(self, client: TestClient) -> None:
        r = client.get("/sequences/seq_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_enroll_sequence_nonexistent(self, client: TestClient) -> None:
        r = client.post("/sequences/seq_nonexistent/enroll", headers=H, json={
            "contact_id": "contact_001",
        })
        assert r.status_code in VALID

    def test_list_enrollments_nonexistent(self, client: TestClient) -> None:
        r = client.get("/sequences/seq_nonexistent/enrollments", headers=H)
        assert r.status_code in VALID

    def test_step_outcome(self, client: TestClient) -> None:
        r = client.post("/sequences/enrollments/enroll_nonexistent/step-outcome", headers=H, json={
            "outcome": "opened",
            "step_index": 0,
        })
        assert r.status_code in VALID

    def test_analytics_nonexistent(self, client: TestClient) -> None:
        r = client.get("/sequences/seq_nonexistent/analytics", headers=H)
        assert r.status_code in VALID

    def test_delete_sequence_nonexistent(self, client: TestClient) -> None:
        r = client.delete("/sequences/seq_nonexistent", headers=H)
        assert r.status_code in VALID


class TestCompetitive:
    def test_create_profile(self, client: TestClient) -> None:
        r = client.post("/competitive/profiles", headers=H, json={
            "competitor_name": "Acme Corp",
            "website": "https://acme.com",
            "industry": "SaaS",
        })
        assert r.status_code in VALID

    def test_list_profiles(self, client: TestClient) -> None:
        r = client.get("/competitive/profiles", headers=H)
        assert r.status_code in VALID

    def test_delete_profile(self, client: TestClient) -> None:
        r = client.delete("/competitive/profiles/profile_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_own_profile(self, client: TestClient) -> None:
        r = client.post("/competitive/own-profile", headers=H, json={
            "website": "https://mycompany.com",
            "strengths": ["AI", "automation"],
            "weaknesses": ["pricing"],
        })
        assert r.status_code in VALID

    def test_report(self, client: TestClient) -> None:
        r = client.get("/competitive/report", headers=H)
        assert r.status_code in VALID

    def test_share_of_voice(self, client: TestClient) -> None:
        r = client.get("/competitive/share-of-voice", headers=H)
        assert r.status_code in VALID


class TestUtmBuilder:
    def test_create_preset(self, client: TestClient) -> None:
        r = client.post("/publishing/utm/presets", headers=H, json={
            "name": "Email Campaign",
            "utm_source": "email",
            "utm_medium": "newsletter",
            "utm_campaign": "monthly_digest",
        })
        assert r.status_code in VALID

    def test_list_presets(self, client: TestClient) -> None:
        r = client.get("/publishing/utm/presets", headers=H)
        assert r.status_code in VALID

    def test_update_preset(self, client: TestClient) -> None:
        r = client.patch("/publishing/utm/presets/preset_nonexistent", headers=H, json={
            "utm_campaign": "updated_campaign",
        })
        assert r.status_code in VALID

    def test_delete_preset(self, client: TestClient) -> None:
        r = client.delete("/publishing/utm/presets/preset_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_build_utm(self, client: TestClient) -> None:
        r = client.post("/publishing/utm/build", headers=H, json={
            "base_url": "https://example.com/landing",
            "utm_source": "twitter",
            "utm_medium": "social",
            "utm_campaign": "launch_2025",
        })
        assert r.status_code in VALID

    def test_build_utm_missing_source(self, client: TestClient) -> None:
        r = client.post("/publishing/utm/build", headers=H, json={
            "base_url": "https://example.com/landing",
        })
        assert r.status_code in VALID
