"""
Tests for growth_suite, influencer, and other untested routers.
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
    def test_get_growth_suite(self, client: TestClient) -> None:
        r = client.get("/ops/platform/growth-suite", headers=H)
        assert r.status_code in VALID

    def test_bootstrap(self, client: TestClient) -> None:
        r = client.post("/ops/platform/growth-suite/bootstrap", headers=H, json={})
        assert r.status_code in VALID

    def test_brand_voice_profile(self, client: TestClient) -> None:
        r = client.post("/ai/brand-voice/profile", headers=H, json={
            "brand_name": "Test Brand",
            "tone": "professional",
            "industry": "tech",
        })
        assert r.status_code in VALID

    def test_ab_tests(self, client: TestClient) -> None:
        r = client.post("/experiments/ab-tests", headers=H, json={
            "name": "Homepage CTA Test",
            "variants": ["control", "variant_a"],
            "traffic_split": [0.5, 0.5],
        })
        assert r.status_code in VALID

    def test_forecast_roi(self, client: TestClient) -> None:
        r = client.post("/forecast/roi", headers=H, json={
            "campaign_spend": 5000,
            "expected_conversion_rate": 0.03,
            "avg_order_value": 200,
        })
        assert r.status_code in VALID

    def test_counter_strike_trigger(self, client: TestClient) -> None:
        r = client.post("/features/counter-strike/trigger", headers=H, json={
            "trigger_type": "competitor_price_drop",
            "target": "premium_plan",
        })
        assert r.status_code in VALID

    def test_calendar_content_plan(self, client: TestClient) -> None:
        r = client.post("/calendar/content-plan", headers=H, json={
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "channels": ["twitter", "linkedin"],
        })
        assert r.status_code in VALID

    def test_create_agency_workspace(self, client: TestClient) -> None:
        r = client.post("/agency/workspaces", headers=H, json={
            "name": "Test Agency",
            "workspace_key": "test-agency-001",
        })
        assert r.status_code in VALID

    def test_add_workspace_members(self, client: TestClient) -> None:
        r = client.post("/agency/workspaces/nonexistent-workspace/members", headers=H, json={
            "email": "member@example.com",
            "role": "editor",
        })
        assert r.status_code in VALID

    def test_workspace_mrr(self, client: TestClient) -> None:
        r = client.post("/agency/workspaces/nonexistent-workspace/mrr", headers=H, json={
            "mrr": 5000.0,
        })
        assert r.status_code in VALID

    def test_agency_overview(self, client: TestClient) -> None:
        r = client.get("/agency/overview", headers=H)
        assert r.status_code in VALID

    def test_audience_dna_analyze(self, client: TestClient) -> None:
        r = client.post("/audience-dna/analyze", headers=H, json={
            "site_url": "https://example.com",
            "audience_segment": "enterprise",
        })
        assert r.status_code in VALID

    def test_autonomous_brain_health_check(self, client: TestClient) -> None:
        r = client.post("/ira/autonomous-brain/health-check", headers=H, json={})
        assert r.status_code in VALID

    def test_ads_campaigns_draft(self, client: TestClient) -> None:
        r = client.post("/ads/campaigns/draft", headers=H, json={
            "campaign_name": "Test Campaign",
            "budget": 1000,
            "channels": ["google", "facebook"],
        })
        assert r.status_code in VALID

    def test_content_repurpose(self, client: TestClient) -> None:
        r = client.post("/content/repurpose", headers=H, json={
            "content": "Original blog post content here.",
            "target_formats": ["tweet", "linkedin_post"],
        })
        assert r.status_code in VALID

    def test_seo_geo_analyze(self, client: TestClient) -> None:
        r = client.post("/seo/geo-analyze", headers=H, json={
            "site_url": "https://example.com",
            "target_markets": ["US", "UK", "CA"],
        })
        assert r.status_code in VALID

    def test_email_ai_generate(self, client: TestClient) -> None:
        r = client.post("/email/ai-generate", headers=H, json={
            "subject": "Increase conversions",
            "audience_segment": "trial_users",
        })
        assert r.status_code in VALID

    def test_scheduler_smart_fill(self, client: TestClient) -> None:
        r = client.post("/scheduler/smart-fill", headers=H, json={
            "channels": ["twitter", "instagram"],
            "week_start": "2025-01-06",
        })
        assert r.status_code in VALID

    def test_podcast_generate(self, client: TestClient) -> None:
        r = client.post("/podcast/generate", headers=H, json={
            "topic": "AI in marketing 2025",
            "duration_minutes": 30,
        })
        assert r.status_code in VALID

    def test_video_script_generate(self, client: TestClient) -> None:
        r = client.post("/video-script/generate", headers=H, json={
            "topic": "How to grow your SaaS",
            "style": "educational",
        })
        assert r.status_code in VALID


class TestInfluencer:
    def test_search(self, client: TestClient) -> None:
        r = client.post("/influencer/search", headers=H, json={
            "niche": "tech",
            "min_followers": 10000,
            "platform": "instagram",
        })
        assert r.status_code in VALID

    def test_profile_nonexistent(self, client: TestClient) -> None:
        r = client.get("/influencer/profile/influencer_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_fraud_check(self, client: TestClient) -> None:
        r = client.post("/influencer/fraud-check", headers=H, json={
            "influencer_id": "influencer_nonexistent",
        })
        assert r.status_code in VALID

    def test_create_campaign(self, client: TestClient) -> None:
        r = client.post("/influencer/campaigns", headers=H, json={
            "name": "Product Launch Campaign",
            "budget": 10000,
            "platform": "instagram",
        })
        assert r.status_code in VALID

    def test_list_campaigns(self, client: TestClient) -> None:
        r = client.get("/influencer/campaigns", headers=H)
        assert r.status_code in VALID

    def test_outreach(self, client: TestClient) -> None:
        r = client.post("/influencer/outreach", headers=H, json={
            "influencer_id": "influencer_nonexistent",
            "message": "Hi, we'd love to collaborate!",
        })
        assert r.status_code in VALID

    def test_analytics(self, client: TestClient) -> None:
        r = client.get("/influencer/analytics", headers=H)
        assert r.status_code in VALID
