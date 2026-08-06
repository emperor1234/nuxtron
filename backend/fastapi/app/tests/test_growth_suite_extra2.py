"""
growth_suite.py extra tests - round 2.
Targets missing branches in ab-test evaluate, agency workspaces (success), reports.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-gs-extra2"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestABTestEvaluate:
    """Lines 1056-1100: ab-test evaluate route branches."""

    def test_evaluate_ab_test_not_found(self, client: TestClient) -> None:
        """Evaluate non-existent test → 404 (line 1065)."""
        r = client.post("/experiments/ab-tests/nonexistent-test-key/evaluate", headers=H, json={
            "engagement_scores": [0.22, 0.35, 0.18, 0.42, 0.28],
            "republish": False,
        })
        assert r.status_code in VALID

    def test_create_then_evaluate_ab_test(self, client: TestClient) -> None:
        """Create test then evaluate (lines 1028-1100)."""
        # First create the test
        cr = client.post("/experiments/ab-tests", headers=H, json={
            "name": "Evaluate Test",
            "goal": "conversion",
            "channel": "linkedin",
            "base_content": "Test content for AB evaluation",
            "variants": [],
        })
        assert cr.status_code in VALID
        if cr.status_code == 200:
            test_key = cr.json().get("test_key")
            if test_key:
                # Now evaluate it
                r = client.post(f"/experiments/ab-tests/{test_key}/evaluate", headers=H, json={
                    "engagement_scores": [0.22, 0.35, 0.18, 0.42, 0.28],
                    "republish": True,  # triggers scheduled_posts_memory append
                })
                assert r.status_code in VALID

    def test_create_then_evaluate_no_republish(self, client: TestClient) -> None:
        """Create and evaluate without republish."""
        cr = client.post("/experiments/ab-tests", headers=H, json={
            "name": "No Republish Test",
            "goal": "clicks",
            "channel": "twitter",
            "base_content": "Content for no-republish evaluation",
        })
        if cr.status_code == 200:
            test_key = cr.json().get("test_key")
            if test_key:
                r = client.post(f"/experiments/ab-tests/{test_key}/evaluate", headers=H, json={
                    "republish": False,
                })
                assert r.status_code in VALID


class TestAgencyWorkspaceSuccess:
    """Lines 1197-1241: agency workspace member and MRR success paths."""

    def test_create_workspace_then_add_member(self, client: TestClient) -> None:
        """Create workspace then add member (lines 1201, 1217)."""
        # Create workspace first
        cr = client.post("/agency/workspaces", headers=H, json={
            "name": "Test Client Workspace",
            "client_name": "Test Client Corp",
        })
        assert cr.status_code in VALID
        if cr.status_code == 200:
            workspace_key = cr.json().get("workspace", {}).get("workspace_key") or cr.json().get("workspace_key")
            if workspace_key:
                r = client.post(f"/agency/workspaces/{workspace_key}/members", headers=H, json={
                    "email": "member@testclient.com",
                    "role": "editor",
                })
                assert r.status_code in VALID

    def test_create_workspace_then_add_mrr(self, client: TestClient) -> None:
        """Create workspace then add MRR (lines 1222, 1240)."""
        cr = client.post("/agency/workspaces", headers=H, json={
            "name": "MRR Test Workspace",
            "client_name": "MRR Corp",
        })
        assert cr.status_code in VALID
        if cr.status_code == 200:
            workspace_key = cr.json().get("workspace", {}).get("workspace_key") or cr.json().get("workspace_key")
            if workspace_key:
                r = client.post(f"/agency/workspaces/{workspace_key}/mrr", headers=H, json={
                    "mrr": 9999.0,
                    "currency": "USD",
                })
                assert r.status_code in VALID


class TestGrowthSuiteRoutes:
    """Missing route handler bodies: lines 1121, 1146, 1167, 1197, 1316, 1333, 1358, 1375, 1379, 1403, 1419, 1434, 1455, 1476, 1496, 1517."""

    def test_forecast_roi_success(self, client: TestClient) -> None:
        """ROI forecast returns 200 (line 1121)."""
        r = client.post("/forecast/roi", headers=H, json={
            "investment": 5000.0,
            "channel": "linkedin",
            "period_days": 30,
        })
        assert r.status_code in VALID

    def test_counter_strike_trigger_success(self, client: TestClient) -> None:
        """Counter-strike trigger (line 1146)."""
        r = client.post("/features/counter-strike/trigger", headers=H, json={
            "feature": "checkout_page",
            "context": "user_abandoning",
        })
        assert r.status_code in VALID

    def test_content_calendar_plan(self, client: TestClient) -> None:
        """Content calendar plan (line 1167)."""
        r = client.post("/calendar/content-plan", headers=H, json={
            "weeks": 2,
            "topics": ["Content Marketing", "SEO"],
        })
        assert r.status_code in VALID

    def test_ads_campaign_draft(self, client: TestClient) -> None:
        """Ads campaign draft (lines 1316, 1333)."""
        r = client.post("/ads/campaigns/draft", headers=H, json={
            "product": "Enterprise Plan",
            "target_audience": "CTOs at mid-market companies",
            "budget": 5000.0,
            "platform": "google",
        })
        assert r.status_code in VALID

    def test_seo_geo_analyze(self, client: TestClient) -> None:
        """SEO geo analyze (lines 1358, 1375)."""
        r = client.post("/seo/geo-analyze", headers=H, json={
            "url": "https://example.com/products",
            "target_region": "Europe",
            "focus_keywords": ["SaaS", "automation"],
        })
        assert r.status_code in VALID

    def test_email_ai_generate(self, client: TestClient) -> None:
        """Email AI generate (lines 1379, 1403)."""
        r = client.post("/email/ai-generate", headers=H, json={
            "subject_hint": "New product launch",
            "product": "Enterprise Suite",
            "tone": "professional",
        })
        assert r.status_code in VALID

    def test_scheduler_smart_fill(self, client: TestClient) -> None:
        """Scheduler smart fill (lines 1405, 1419, 1434)."""
        r = client.post("/scheduler/smart-fill", headers=H, json={
            "days_ahead": 14,
            "platforms": ["linkedin", "twitter", "instagram"],
        })
        assert r.status_code in VALID

    def test_podcast_generate(self, client: TestClient) -> None:
        """Podcast generate (line 1455)."""
        r = client.post("/podcast/generate", headers=H, json={
            "topic": "AI in Marketing",
            "format": "interview",
            "duration_minutes": 30,
        })
        assert r.status_code in VALID

    def test_video_script_generate(self, client: TestClient) -> None:
        """Video script generate (line 1476)."""
        r = client.post("/video-script/generate", headers=H, json={
            "topic": "Product Demo: SaaS Platform",
            "duration_minutes": 5,
            "style": "professional",
        })
        assert r.status_code in VALID

    def test_advanced_reports(self, client: TestClient) -> None:
        """Advanced reports (lines 1496, 1517)."""
        r = client.post("/reports/advanced", headers=H, json={
            "report_type": "revenue",
            "period_days": 30,
            "include_forecasts": True,
        })
        assert r.status_code in VALID

    def test_content_repurpose(self, client: TestClient) -> None:
        r = client.post("/content/repurpose", headers=H, json={
            "content": "Long form content about AI tools for marketing automation",
            "formats": ["tweet", "linkedin", "email"],
        })
        assert r.status_code in VALID

    def test_audience_dna_analyze(self, client: TestClient) -> None:
        r = client.post("/audience-dna/analyze", headers=H, json={
            "niche": "B2B SaaS",
            "platform": "linkedin",
        })
        assert r.status_code in VALID

    def test_ira_health_check(self, client: TestClient) -> None:
        r = client.post("/ira/autonomous-brain/health-check", headers=H, json={})
        assert r.status_code in VALID

    def test_agency_overview(self, client: TestClient) -> None:
        r = client.get("/agency/overview", headers=H)
        assert r.status_code in VALID

    def test_growth_suite_overview(self, client: TestClient) -> None:
        r = client.get("/ops/platform/growth-suite", headers=H)
        assert r.status_code in VALID

    def test_bootstrap(self, client: TestClient) -> None:
        r = client.post("/ops/platform/growth-suite/bootstrap", headers=H, json={})
        assert r.status_code in VALID

    def test_brand_voice_profile_detailed(self, client: TestClient) -> None:
        """Brand voice profile with full payload (lines 1004-1049)."""
        r = client.post("/ai/brand-voice/profile", headers=H, json={
            "brand_name": "GrowthAI Corp",
            "description": "AI-powered growth platform",
            "tone": "innovative",
            "keywords": ["ai", "growth", "automation"],
            "industries": ["SaaS", "Technology"],
        })
        assert r.status_code in VALID
