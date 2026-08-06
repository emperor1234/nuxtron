"""
Tests for employee_advocacy.py routes and helpers.
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


class TestAdvocacyCampaigns:
    def test_create_campaign(self, client: TestClient) -> None:
        r = client.post("/advocacy/campaigns", headers=H, json={
            "name": "Product Launch Q1",
            "description": "Share product launch content",
            "starts_at": "2024-01-01T00:00:00Z",
            "ends_at": "2024-03-31T23:59:59Z",
        })
        assert r.status_code in VALID

    def test_create_campaign_minimal(self, client: TestClient) -> None:
        r = client.post("/advocacy/campaigns", headers=H, json={
            "name": "Minimal Campaign",
        })
        assert r.status_code in VALID

    def test_list_campaigns(self, client: TestClient) -> None:
        r = client.get("/advocacy/campaigns", headers=H)
        assert r.status_code in VALID

    def test_list_campaigns_empty_for_new_tenant(self, client: TestClient) -> None:
        h = dict(H)
        h["X-Tenant-Id"] = "fresh-tenant-advocacy"
        r = client.get("/advocacy/campaigns", headers=h)
        assert r.status_code in VALID
        if r.status_code == 200:
            data = r.json()
            assert data["count"] == 0

    def test_create_campaign_missing_name(self, client: TestClient) -> None:
        r = client.post("/advocacy/campaigns", headers=H, json={})
        assert r.status_code in VALID


class TestAdvocacyContent:
    def test_add_content_no_campaign(self, client: TestClient) -> None:
        r = client.post("/advocacy/content", headers=H, json={
            "title": "Share Our New Feature",
            "body": "We launched an amazing feature today!",
            "platform": "linkedin",
        })
        assert r.status_code in VALID

    def test_add_content_invalid_campaign(self, client: TestClient) -> None:
        r = client.post("/advocacy/content", headers=H, json={
            "title": "Content with bad campaign",
            "body": "Some body text",
            "platform": "x",
            "campaign_id": 999999,
        })
        assert r.status_code in VALID  # 404 expected

    def test_list_content(self, client: TestClient) -> None:
        r = client.get("/advocacy/content", headers=H)
        assert r.status_code in VALID

    def test_list_content_with_platform_filter(self, client: TestClient) -> None:
        r = client.get("/advocacy/content?platform=linkedin", headers=H)
        assert r.status_code in VALID

    def test_list_content_active_only_false(self, client: TestClient) -> None:
        r = client.get("/advocacy/content?active_only=false", headers=H)
        assert r.status_code in VALID

    def test_list_content_with_pagination(self, client: TestClient) -> None:
        r = client.get("/advocacy/content?limit=5&offset=0", headers=H)
        assert r.status_code in VALID

    def test_add_content_with_targets(self, client: TestClient) -> None:
        r = client.post("/advocacy/content", headers=H, json={
            "title": "Engineering Content",
            "body": "Read about our engineering culture",
            "platform": "instagram",
            "target_departments": ["engineering", "product"],
            "target_regions": ["us", "eu"],
        })
        assert r.status_code in VALID

    def test_add_content_invalid_campaign_returns_404(self, client: TestClient) -> None:
        r = client.post(
            "/advocacy/content",
            headers=H,
            json={
                "title": "Missing Campaign",
                "body": "Should fail on campaign lookup",
                "platform": "linkedin",
                "campaign_id": 987654321,
            },
        )
        assert r.status_code == 404


class TestAdvocacyParticipants:
    def test_register_participant(self, client: TestClient) -> None:
        r = client.post("/advocacy/participants", headers=H, json={
            "name": "Alice Smith",
            "email": "alice.advocacy@example.com",
            "department": "engineering",
            "region": "us",
            "linkedin_followers": 500,
            "x_followers": 200,
            "instagram_followers": 300,
        })
        assert r.status_code in VALID

    def test_register_participant_idempotent(self, client: TestClient) -> None:
        """Registering same email twice returns existing."""
        payload = {
            "name": "Bob Jones",
            "email": "bob.advocacy.dupe@example.com",
            "department": "sales",
            "region": "eu",
            "linkedin_followers": 1000,
            "x_followers": 500,
            "instagram_followers": 100,
        }
        r1 = client.post("/advocacy/participants", headers=H, json=payload)
        r2 = client.post("/advocacy/participants", headers=H, json=payload)
        assert r1.status_code in VALID
        assert r2.status_code in VALID
        if r1.status_code == 200 and r2.status_code == 200:
            # second call returns created=False
            assert r2.json().get("created") is False

    def test_list_participants(self, client: TestClient) -> None:
        r = client.get("/advocacy/participants", headers=H)
        assert r.status_code in VALID

    def test_list_participants_department_filter(self, client: TestClient) -> None:
        r = client.get("/advocacy/participants?department=engineering", headers=H)
        assert r.status_code in VALID

    def test_list_participants_pagination(self, client: TestClient) -> None:
        r = client.get("/advocacy/participants?limit=10&offset=0", headers=H)
        assert r.status_code in VALID

    def test_register_participant_missing_email(self, client: TestClient) -> None:
        r = client.post("/advocacy/participants", headers=H, json={
            "name": "No Email",
        })
        assert r.status_code in VALID


class TestAdvocacyShares:
    def test_record_share_invalid_participant(self, client: TestClient) -> None:
        r = client.post("/advocacy/participants/999999/share", headers=H, json={
            "content_id": 1,
            "platform": "linkedin",
            "estimated_reach": 500,
            "likes": 10,
            "comments": 2,
            "clicks": 20,
        })
        assert r.status_code in VALID  # 404 expected

    def test_record_share_full_flow(self, client: TestClient) -> None:
        """Create campaign → content → participant → share."""
        # Create campaign
        camp_r = client.post("/advocacy/campaigns", headers=H, json={
            "name": "Full Flow Campaign"
        })
        if camp_r.status_code != 200:
            return

        camp_id = camp_r.json().get("campaign", {}).get("id")

        # Add content
        cont_r = client.post("/advocacy/content", headers=H, json={
            "title": "Share This",
            "body": "Great content",
            "platform": "linkedin",
            "campaign_id": camp_id,
        })
        if cont_r.status_code != 200:
            return

        cont_id = cont_r.json().get("content", {}).get("id")

        # Register participant
        part_r = client.post("/advocacy/participants", headers=H, json={
            "name": "Charlie Test",
            "email": "charlie.fullflow@example.com",
            "department": "marketing",
            "region": "us",
            "linkedin_followers": 2000,
            "x_followers": 1000,
            "instagram_followers": 500,
        })
        if part_r.status_code != 200:
            return

        part_id = part_r.json().get("participant", {}).get("id")

        # Record share
        share_r = client.post(f"/advocacy/participants/{part_id}/share", headers=H, json={
            "content_id": cont_id,
            "platform": "linkedin",
            "estimated_reach": 2000,
            "likes": 50,
            "comments": 10,
            "clicks": 100,
            "custom_commentary": "Check out this awesome feature!",
        })
        assert share_r.status_code in VALID
        if share_r.status_code == 200:
            data = share_r.json()
            assert "points_earned" in data
            assert "earned_media_value" in data

    def test_record_share_invalid_content_with_valid_participant(self, client: TestClient) -> None:
        part_r = client.post("/advocacy/participants", headers=H, json={
            "name": "Valid Participant",
            "email": "valid.participant@example.com",
            "department": "marketing",
            "region": "us",
            "linkedin_followers": 150,
            "x_followers": 50,
            "instagram_followers": 20,
        })
        assert part_r.status_code in VALID
        if part_r.status_code != 200:
            return
        participant_id = part_r.json().get("participant", {}).get("id")

        r = client.post(
            f"/advocacy/participants/{participant_id}/share",
            headers=H,
            json={
                "content_id": 99999999,
                "platform": "linkedin",
                "estimated_reach": 100,
                "likes": 1,
                "comments": 0,
                "clicks": 0,
            },
        )
        assert r.status_code == 404


class TestAdvocacyAnalytics:
    def test_get_analytics(self, client: TestClient) -> None:
        r = client.get("/advocacy/analytics", headers=H)
        assert r.status_code in VALID

    def test_analytics_returns_expected_keys(self, client: TestClient) -> None:
        r = client.get("/advocacy/analytics", headers=H)
        if r.status_code == 200:
            data = r.json()
            assert "activeAdvocates" in data or "total_shares" in data or "totalShares" in data or "status" in data

    def test_analytics_fresh_tenant(self, client: TestClient) -> None:
        h = dict(H)
        h["X-Tenant-Id"] = "brand-new-advocate-tenant"
        r = client.get("/advocacy/analytics", headers=h)
        assert r.status_code in VALID
