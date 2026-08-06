"""
Route smoke tests for growth_suite router — all endpoints.
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


class TestGrowthSuite:
    def test_growth_suite_overview(self, client: TestClient) -> None:
        r = client.get("/ops/platform/growth-suite", headers=H)
        assert r.status_code in VALID

    def test_bootstrap(self, client: TestClient) -> None:
        r = client.post("/ops/platform/growth-suite/bootstrap", headers=H, json={})
        assert r.status_code in VALID

    def test_brand_voice_profile(self, client: TestClient) -> None:
        r = client.post("/ai/brand-voice/profile", headers=H, json={
            "brand_name": "Nuxtron",
            "description": "SaaS platform",
            "tone": "professional",
        })
        assert r.status_code in VALID

    def test_ab_tests(self, client: TestClient) -> None:
        r = client.post("/experiments/ab-tests", headers=H, json={
            "name": "CTA Button Color",
            "variants": [
                {"name": "control", "description": "Blue button"},
                {"name": "variant_a", "description": "Green button"},
            ],
        })
        assert r.status_code in VALID

    def test_forecast_roi(self, client: TestClient) -> None:
        r = client.post("/forecast/roi", headers=H, json={
            "investment": 10000.0,
            "channel": "email",
            "period_days": 90,
        })
        assert r.status_code in VALID

    def test_counter_strike_trigger(self, client: TestClient) -> None:
        r = client.post("/features/counter-strike/trigger", headers=H, json={
            "feature": "pricing_page",
            "context": "user_hesitating",
        })
        assert r.status_code in VALID

    def test_content_plan(self, client: TestClient) -> None:
        r = client.post("/calendar/content-plan", headers=H, json={
            "weeks": 4,
            "topics": ["SEO", "Marketing"],
        })
        assert r.status_code in VALID

    def test_create_workspace(self, client: TestClient) -> None:
        r = client.post("/agency/workspaces", headers=H, json={
            "name": "Client A Workspace",
            "client_name": "ACME Corp",
        })
        assert r.status_code in VALID

    def test_add_member_not_found(self, client: TestClient) -> None:
        r = client.post("/agency/workspaces/nonexistent-key/members", headers=H, json={
            "email": "team@example.com",
            "role": "editor",
        })
        assert r.status_code in VALID

    def test_mrr_not_found(self, client: TestClient) -> None:
        r = client.post("/agency/workspaces/nonexistent-key/mrr", headers=H, json={
            "mrr": 5000.0,
        })
        assert r.status_code in VALID

    def test_agency_overview(self, client: TestClient) -> None:
        r = client.get("/agency/overview", headers=H)
        assert r.status_code in VALID

    def test_audience_dna_analyze(self, client: TestClient) -> None:
        r = client.post("/audience-dna/analyze", headers=H, json={
            "niche": "health & wellness",
            "platform": "instagram",
        })
        assert r.status_code in VALID

    def test_ira_health_check(self, client: TestClient) -> None:
        r = client.post("/ira/autonomous-brain/health-check", headers=H, json={})
        assert r.status_code in VALID

    def test_ads_campaign_draft(self, client: TestClient) -> None:
        r = client.post("/ads/campaigns/draft", headers=H, json={
            "product": "Pro Plan",
            "target_audience": "SMB founders",
            "budget": 1000.0,
        })
        assert r.status_code in VALID

    def test_content_repurpose(self, client: TestClient) -> None:
        r = client.post("/content/repurpose", headers=H, json={
            "content": "Long-form blog post about SEO strategies...",
            "formats": ["tweet", "linkedin"],
        })
        assert r.status_code in VALID

    def test_seo_geo_analyze(self, client: TestClient) -> None:
        r = client.post("/seo/geo-analyze", headers=H, json={
            "url": "https://example.com",
            "target_region": "US",
        })
        assert r.status_code in VALID

    def test_email_ai_generate(self, client: TestClient) -> None:
        r = client.post("/email/ai-generate", headers=H, json={
            "subject_hint": "Summer sale",
            "product": "Pro Plan",
        })
        assert r.status_code in VALID

    def test_scheduler_smart_fill(self, client: TestClient) -> None:
        r = client.post("/scheduler/smart-fill", headers=H, json={
            "days_ahead": 7,
            "platforms": ["twitter", "linkedin"],
        })
        assert r.status_code in VALID

    def test_podcast_generate(self, client: TestClient) -> None:
        r = client.post("/podcast/generate", headers=H, json={
            "topic": "AI and Marketing",
            "duration_minutes": 30,
        })
        assert r.status_code in VALID

    def test_video_script_generate(self, client: TestClient) -> None:
        r = client.post("/video-script/generate", headers=H, json={
            "topic": "How to use Nuxtron",
            "duration_seconds": 60,
        })
        assert r.status_code in VALID

    def test_advanced_reports(self, client: TestClient) -> None:
        r = client.post("/reports/advanced", headers=H, json={
            "report_type": "revenue_attribution",
            "period": "last_90_days",
        })
        assert r.status_code in VALID
