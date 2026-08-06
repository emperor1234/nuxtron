"""
Route smoke tests for engagement routers:
engagement_referrals, engagement_retention, engagement_studios,
engagement_university, engagement_white_label.
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


class TestEngagementReferrals:
    def test_list_referrals(self, client: TestClient) -> None:
        r = client.get("/engagement/referrals", headers=H)
        assert r.status_code in VALID

    def test_generate_code(self, client: TestClient) -> None:
        r = client.post("/engagement/referrals/generate-code", headers=H, json={})
        assert r.status_code in VALID

    def test_leaderboard(self, client: TestClient) -> None:
        r = client.get("/engagement/referrals/leaderboard", headers=H)
        assert r.status_code in VALID


class TestEngagementRetention:
    def test_get_streak(self, client: TestClient) -> None:
        r = client.get("/engagement/streak", headers=H)
        assert r.status_code in VALID

    def test_check_in(self, client: TestClient) -> None:
        r = client.post("/engagement/streak/check-in", headers=H, json={})
        assert r.status_code in VALID

    def test_streak_recover(self, client: TestClient) -> None:
        r = client.post("/engagement/streak/recover", headers=H, json={})
        assert r.status_code in VALID

    def test_streak_leaderboard(self, client: TestClient) -> None:
        r = client.get("/engagement/streak/leaderboard", headers=H)
        assert r.status_code in VALID

    def test_withdrawal_preview(self, client: TestClient) -> None:
        r = client.get("/engagement/withdrawal-preview", headers=H)
        assert r.status_code in VALID

    def test_earnings_ticker(self, client: TestClient) -> None:
        r = client.get("/engagement/earnings-ticker", headers=H)
        assert r.status_code in VALID


class TestEngagementStudios:
    def test_create_service(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-studios/services", headers=H, json={
            "name": "Logo Design",
            "price": 500.0,
            "description": "Professional logo",
        })
        assert r.status_code in VALID

    def test_create_brief(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-studios/briefs", headers=H, json={
            "title": "Brand Refresh",
            "description": "Need a new brand identity",
        })
        assert r.status_code in VALID

    def test_create_proposal_not_found(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-studios/proposals", headers=H, json={
            "brief_id": 99999,
            "service_id": 99998,
            "price": 500.0,
        })
        assert r.status_code in VALID

    def test_create_escrow_not_found(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-studios/escrows", headers=H, json={
            "proposal_id": 99999,
            "amount": 500.0,
        })
        assert r.status_code in VALID

    def test_overview(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-studios/overview", headers=H)
        assert r.status_code in VALID


class TestEngagementUniversity:
    def test_catalog(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-university/catalog", headers=H)
        assert r.status_code in VALID

    def test_create_course(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-university/courses", headers=H, json={
            "title": "SEO Mastery",
            "description": "Learn advanced SEO",
            "price": 199.0,
        })
        assert r.status_code in VALID

    def test_create_cohort_not_found(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-university/cohorts", headers=H, json={
            "course_id": 99999,
            "name": "Cohort A",
            "starts_at": "2025-07-01T09:00:00Z",
        })
        assert r.status_code in VALID

    def test_overview(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-university/overview", headers=H)
        assert r.status_code in VALID


class TestEngagementWhiteLabel:
    def test_get_profile(self, client: TestClient) -> None:
        r = client.get("/white-label/profile", headers=H)
        assert r.status_code in VALID

    def test_brand_kit(self, client: TestClient) -> None:
        r = client.post("/white-label/brand-kit", headers=H, json={
            "primary_color": "#FF5500",
            "logo_url": "https://cdn.example.com/logo.png",
        })
        assert r.status_code in VALID

    def test_domain(self, client: TestClient) -> None:
        r = client.post("/white-label/domain", headers=H, json={
            "domain": "app.myplatform.com",
        })
        assert r.status_code in VALID

    def test_checkpoint(self, client: TestClient) -> None:
        r = client.post("/white-label/checkpoint", headers=H, json={
            "checkpoint": "branding_complete",
        })
        assert r.status_code in VALID

    def test_timeline(self, client: TestClient) -> None:
        r = client.get("/white-label/timeline", headers=H)
        assert r.status_code in VALID
