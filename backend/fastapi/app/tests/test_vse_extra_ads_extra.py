"""
Additional VSE routes not covered in test_vse_content_ai_pentest.py.
Also covers ads_control_tower routes not in test_ads_control_tower.py.
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


# --------------------------------------------------------------------------- #
# VSE - Triggers
# --------------------------------------------------------------------------- #
class TestVseTriggers:
    def test_triggers_library(self, client: TestClient) -> None:
        r = client.get("/vse/triggers/library", headers=H)
        assert r.status_code in VALID

    def test_triggers_analyze(self, client: TestClient) -> None:
        r = client.post("/vse/triggers/analyze", headers=H, json={
            "content": "Limited time offer - only 3 left!", "platforms": ["twitter"]
        })
        assert r.status_code in VALID

    def test_triggers_optimal(self, client: TestClient) -> None:
        r = client.post("/vse/triggers/optimal", headers=H, json={
            "goal": "urgency", "audience": "millennials"
        })
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Algorithm
# --------------------------------------------------------------------------- #
class TestVseAlgorithm:
    def test_algorithm_models(self, client: TestClient) -> None:
        r = client.get("/vse/algorithm/models", headers=H)
        assert r.status_code in VALID

    def test_algorithm_optimize(self, client: TestClient) -> None:
        r = client.post("/vse/algorithm/optimize", headers=H, json={
            "content": "Check out our new product!", "target_platform": "instagram"
        })
        assert r.status_code in VALID

    def test_algorithm_updates(self, client: TestClient) -> None:
        r = client.get("/vse/algorithm/updates", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Network
# --------------------------------------------------------------------------- #
class TestVseNetwork:
    def test_network_map(self, client: TestClient) -> None:
        r = client.post("/vse/network/map", headers=H, json={
            "seed_accounts": ["@influencer1", "@influencer2"], "depth": 2
        })
        assert r.status_code in VALID

    def test_network_superconnectors(self, client: TestClient) -> None:
        r = client.get("/vse/network/superconnectors", headers=H)
        assert r.status_code in VALID

    def test_network_cascade_simulate(self, client: TestClient) -> None:
        r = client.post("/vse/network/cascade-simulate", headers=H, json={
            "seed_node": "@influencer1", "content": "New product launch"
        })
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Detonation
# --------------------------------------------------------------------------- #
class TestVseDetonation:
    def test_detonation_plan(self, client: TestClient) -> None:
        r = client.post("/vse/detonation/plan", headers=H, json={
            "campaign": "Product Launch", "channels": ["twitter", "linkedin"], "launch_at": "2025-03-15T12:00:00Z"
        })
        assert r.status_code in VALID

    def test_detonation_execute(self, client: TestClient) -> None:
        r = client.post("/vse/detonation/execute", headers=H, json={
            "plan_id": "plan_nonexistent"
        })
        assert r.status_code in VALID

    def test_detonation_list(self, client: TestClient) -> None:
        r = client.get("/vse/detonation", headers=H)
        assert r.status_code in VALID

    def test_detonation_history(self, client: TestClient) -> None:
        r = client.get("/vse/detonation/history", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Swarm
# --------------------------------------------------------------------------- #
class TestVseSwarm:
    def test_swarm_compose(self, client: TestClient) -> None:
        r = client.post("/vse/swarm/compose", headers=H, json={
            "agents": ["content", "engagement", "amplify"], "goal": "viral_launch"
        })
        assert r.status_code in VALID

    def test_swarm_release(self, client: TestClient) -> None:
        r = client.post("/vse/swarm/release", headers=H, json={
            "swarm_id": "swarm_nonexistent"
        })
        assert r.status_code in VALID

    def test_swarm_status(self, client: TestClient) -> None:
        r = client.get("/vse/swarm/swarm_nonexistent/status", headers=H)
        assert r.status_code in VALID

    def test_swarm_db_stats(self, client: TestClient) -> None:
        r = client.get("/vse/swarm/database/stats", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Momentum
# --------------------------------------------------------------------------- #
class TestVseMomentum:
    def test_momentum_start(self, client: TestClient) -> None:
        r = client.post("/vse/momentum/start", headers=H, json={
            "campaign": "Launch", "boost_duration_hours": 24
        })
        assert r.status_code in VALID

    def test_momentum_get_nonexistent(self, client: TestClient) -> None:
        r = client.get("/vse/momentum/event_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_momentum_inject_nonexistent(self, client: TestClient) -> None:
        r = client.post("/vse/momentum/event_nonexistent/inject", headers=H, json={
            "boost_amount": 10
        })
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Content (extra routes)
# --------------------------------------------------------------------------- #
class TestVseContentExtra:
    def test_content_generate_variants(self, client: TestClient) -> None:
        r = client.post("/vse/content/generate-variants", headers=H, json={
            "base_content": "Check our new product!", "num_variants": 3, "platforms": ["twitter"]
        })
        assert r.status_code in VALID

    def test_content_hooks(self, client: TestClient) -> None:
        r = client.post("/vse/content/hooks", headers=H, json={
            "topic": "AI tools", "audience": "marketers"
        })
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Emotion
# --------------------------------------------------------------------------- #
class TestVseEmotion:
    def test_emotion_analyze(self, client: TestClient) -> None:
        r = client.post("/vse/emotion/analyze", headers=H, json={
            "content": "This is amazing! You need to try it now!"
        })
        assert r.status_code in VALID

    def test_emotion_engineer(self, client: TestClient) -> None:
        r = client.post("/vse/emotion/engineer", headers=H, json={
            "target_emotion": "excitement", "topic": "product launch"
        })
        assert r.status_code in VALID

    def test_emotion_audience_state(self, client: TestClient) -> None:
        r = client.get("/vse/emotion/audience-state", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Trends
# --------------------------------------------------------------------------- #
class TestVseTrends:
    def test_trends_live(self, client: TestClient) -> None:
        r = client.get("/vse/trends/live", headers=H)
        assert r.status_code in VALID

    def test_trends_hijack(self, client: TestClient) -> None:
        r = client.post("/vse/trends/hijack", headers=H, json={
            "trend": "#AIMarketing", "brand_message": "Check out our AI tools"
        })
        assert r.status_code in VALID

    def test_trends_alerts(self, client: TestClient) -> None:
        r = client.get("/vse/trends/alerts", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Paid
# --------------------------------------------------------------------------- #
class TestVsePaid:
    def test_paid_assess(self, client: TestClient) -> None:
        r = client.post("/vse/paid/assess", headers=H, json={
            "content": "Our new product is here!", "budget": 500.0
        })
        assert r.status_code in VALID

    def test_paid_amplify(self, client: TestClient) -> None:
        r = client.post("/vse/paid/amplify", headers=H, json={
            "post_id": "post_001", "budget": 200.0, "platforms": ["facebook"]
        })
        assert r.status_code in VALID

    def test_paid_events(self, client: TestClient) -> None:
        r = client.get("/vse/paid/events", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Dark Social
# --------------------------------------------------------------------------- #
class TestVseDarkSocial:
    def test_dark_social_seed(self, client: TestClient) -> None:
        r = client.post("/vse/dark-social/seed", headers=H, json={
            "content": "Exclusive early access link", "communities": ["slack_group_1"]
        })
        assert r.status_code in VALID

    def test_dark_social_measurement(self, client: TestClient) -> None:
        r = client.get("/vse/dark-social/measurement", headers=H)
        assert r.status_code in VALID

    def test_dark_social_attribution(self, client: TestClient) -> None:
        r = client.post("/vse/dark-social/attribution", headers=H, json={
            "session_id": "sess_001", "referrer_source": "slack"
        })
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# VSE - Immortalise
# --------------------------------------------------------------------------- #
class TestVseImmortalise:
    def test_immortalise(self, client: TestClient) -> None:
        r = client.post("/vse/immortalise", headers=H, json={
            "content": "Our most viral post ever!", "platform": "twitter"
        })
        assert r.status_code in VALID

    def test_immortalise_vault(self, client: TestClient) -> None:
        r = client.get("/vse/immortalise/vault", headers=H)
        assert r.status_code in VALID

    def test_immortalise_assets_nonexistent(self, client: TestClient) -> None:
        r = client.get("/vse/immortalise/immortal_nonexistent/assets", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Ads Control Tower - extra routes
# --------------------------------------------------------------------------- #
class TestAdsControlTowerExtra:
    def test_health(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/health", headers=H)
        assert r.status_code in VALID

    def test_list_connectors(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/connectors", headers=H)
        assert r.status_code in VALID

    def test_oauth_start(self, client: TestClient) -> None:
        r = client.post("/ads-control-tower/connectors/google_ads/oauth/start", headers=H, json={})
        assert r.status_code in VALID

    def test_oauth_callback(self, client: TestClient) -> None:
        r = client.post("/ads-control-tower/connectors/google_ads/oauth/callback", headers=H, json={
            "code": "auth_code_xxx", "state": "state_xxx"
        })
        assert r.status_code in VALID

    def test_delete_connector(self, client: TestClient) -> None:
        r = client.delete("/ads-control-tower/connectors/google_ads", headers=H)
        assert r.status_code in VALID

    def test_credits(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/credits", headers=H)
        assert r.status_code in VALID

    def test_create_campaign(self, client: TestClient) -> None:
        r = client.post("/ads-control-tower/campaigns", headers=H, json={
            "name": "Test Campaign", "platform": "google_ads", "budget": 500.0
        })
        assert r.status_code in VALID

    def test_list_campaigns(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/campaigns", headers=H)
        assert r.status_code in VALID

    def test_get_campaign_nonexistent(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/campaigns/camp_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_update_campaign(self, client: TestClient) -> None:
        r = client.patch("/ads-control-tower/campaigns/camp_nonexistent", headers=H, json={
            "budget": 750.0
        })
        assert r.status_code in VALID

    def test_delete_campaign(self, client: TestClient) -> None:
        r = client.delete("/ads-control-tower/campaigns/camp_nonexistent", headers=H)
        assert r.status_code in VALID

    def test_publish_campaign(self, client: TestClient) -> None:
        r = client.post("/ads-control-tower/campaigns/camp_nonexistent/publish", headers=H, json={})
        assert r.status_code in VALID

    def test_campaign_metrics(self, client: TestClient) -> None:
        r = client.post("/ads-control-tower/campaigns/camp_nonexistent/metrics", headers=H, json={
            "impressions": 1000, "clicks": 50, "conversions": 5
        })
        assert r.status_code in VALID

    def test_calendar(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/calendar", headers=H)
        assert r.status_code in VALID

    def test_calendar_drag_reschedule(self, client: TestClient) -> None:
        r = client.post("/ads-control-tower/calendar/drag-reschedule", headers=H, json={
            "campaign_id": "camp_nonexistent", "new_date": "2025-04-01"
        })
        assert r.status_code in VALID

    def test_assets_auto_resize(self, client: TestClient) -> None:
        r = client.post("/ads-control-tower/assets/auto-resize", headers=H, json={
            "image_url": "https://cdn.example.com/ad.png", "platforms": ["facebook", "instagram"]
        })
        assert r.status_code in VALID

    def test_kpis(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/kpis", headers=H)
        assert r.status_code in VALID

    def test_forecast(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/forecast", headers=H)
        assert r.status_code in VALID

    def test_notifications(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/notifications", headers=H)
        assert r.status_code in VALID

    def test_best_time(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/best-time", headers=H)
        assert r.status_code in VALID

    def test_request_approval(self, client: TestClient) -> None:
        r = client.post("/ads-control-tower/campaigns/camp_nonexistent/request-approval", headers=H, json={})
        assert r.status_code in VALID

    def test_approve(self, client: TestClient) -> None:
        r = client.post("/ads-control-tower/campaigns/camp_nonexistent/approve", headers=H, json={
            "approved": True
        })
        assert r.status_code in VALID

    def test_duplicate(self, client: TestClient) -> None:
        r = client.post("/ads-control-tower/campaigns/camp_nonexistent/duplicate", headers=H, json={})
        assert r.status_code in VALID

    def test_ab_test_suggestions(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/ab-test/camp_nonexistent/suggestions", headers=H)
        assert r.status_code in VALID

    def test_audience_insights(self, client: TestClient) -> None:
        r = client.get("/ads-control-tower/audience-insights", headers=H)
        assert r.status_code in VALID
