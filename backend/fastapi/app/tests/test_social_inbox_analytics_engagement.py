"""
Tests for Social Workspace, Smart Inbox, Engagement, and Analytics routers.
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


# ── Social Workspace ──────────────────────────────────────────────────────────

class TestSocialWorkspace:
    def test_list_accounts(self, client: TestClient) -> None:
        r = client.get("/social/accounts", headers=H)
        assert r.status_code == 200

    def test_accounts_catalog(self, client: TestClient) -> None:
        r = client.get("/social/accounts/catalog", headers=H)
        assert r.status_code == 200

    def test_connect_account(self, client: TestClient) -> None:
        r = client.post("/social/accounts/connect", headers=H, json={
            "network": "instagram",
            "account_name": "test_account",
            "access_token": "dummy-token",
        })
        assert r.status_code < 500

    def test_get_brand_profile(self, client: TestClient) -> None:
        r = client.get("/social/brand-profile", headers=H)
        assert r.status_code == 200

    def test_update_brand_profile(self, client: TestClient) -> None:
        r = client.put("/social/brand-profile", headers=H, json={
            "brand_name": "Test Brand",
            "bio": "A test brand description.",
            "website": "https://testbrand.com",
        })
        assert r.status_code < 500

    def test_fetch_brand_from_website(self, client: TestClient) -> None:
        r = client.post("/social/brand-profile/fetch-from-website", headers=H, json={
            "url": "https://example.com",
        })
        assert r.status_code < 500

    def test_update_ugc_template(self, client: TestClient) -> None:
        r = client.put("/social/brand-profile/ugc-template", headers=H, json={
            "template": "Check out our latest post!",
        })
        assert r.status_code < 500

    def test_schedule_post(self, client: TestClient) -> None:
        r = client.post("/social/schedule", headers=H, json={
            "network": "instagram",
            "content": "Test post content",
            "scheduled_at": "2026-06-01T10:00:00Z",
            "format": "image",
        })
        assert r.status_code < 500

    def test_list_scheduled(self, client: TestClient) -> None:
        r = client.get("/social/scheduled", headers=H)
        assert r.status_code == 200

    def test_workspace_overview(self, client: TestClient) -> None:
        r = client.get("/social/workspace/overview", headers=H)
        assert r.status_code == 200

    def test_oauth_providers(self, client: TestClient) -> None:
        r = client.get("/social/oauth/providers", headers=H)
        assert r.status_code == 200

    def test_listening_ingest(self, client: TestClient) -> None:
        r = client.post("/social/listening/ingest", headers=H, json={
            "keyword": "testbrand",
            "network": "instagram",
            "text": "Love this product!",
            "author": "fan123",
        })
        assert r.status_code < 500

    def test_listening_mentions(self, client: TestClient) -> None:
        r = client.get("/social/listening/mentions", headers=H)
        assert r.status_code == 200

    def test_listening_summary(self, client: TestClient) -> None:
        r = client.get("/social/listening/summary", headers=H)
        assert r.status_code == 200

    def test_listening_rules(self, client: TestClient) -> None:
        r = client.post("/social/listening/rules", headers=H, json={
            "keyword": "testbrand",
            "networks": ["instagram", "x"],
        })
        assert r.status_code < 500

    def test_avatar_catalog(self, client: TestClient) -> None:
        r = client.get("/social/avatar/catalog", headers=H)
        assert r.status_code == 200

    def test_voiceover_catalog(self, client: TestClient) -> None:
        r = client.get("/social/voiceover/catalog", headers=H)
        assert r.status_code == 200

    def test_autopilot_preview(self, client: TestClient) -> None:
        r = client.post("/social/autopilot/preview", headers=H, json={
            "network": "instagram",
            "topic": "product launch",
            "tone": "professional",
        })
        assert r.status_code < 500

    def test_autopilot_publish(self, client: TestClient) -> None:
        r = client.post("/social/autopilot/publish", headers=H, json={
            "network": "instagram",
            "content": "Auto published!",
        })
        assert r.status_code < 500

    def test_oauth_connect_all(self, client: TestClient) -> None:
        r = client.post("/social/oauth/connect-all", headers=H, json={})
        assert r.status_code < 500


# ── Smart Inbox ───────────────────────────────────────────────────────────────

class TestSmartInbox:
    def test_list_messages(self, client: TestClient) -> None:
        r = client.get("/inbox/messages", headers=H)
        assert r.status_code == 200

    def test_ingest_message(self, client: TestClient) -> None:
        r = client.post("/inbox/messages", headers=H, json={
            "network": "instagram",
            "source_type": "dm",
            "author_handle": "fan123",
            "text": "Is this product available?",
        })
        assert r.status_code in {200, 201}
        data = r.json()
        assert "id" in data.get("message", data)

    def test_get_message(self, client: TestClient) -> None:
        r = client.post("/inbox/messages", headers=H, json={
            "network": "facebook",
            "source_type": "comment",
            "author_handle": "user456",
            "text": "Great post!",
        })
        mid = (r.json().get("message") or r.json()).get("id", 1)
        r2 = client.get(f"/inbox/messages/{mid}", headers=H)
        assert r2.status_code == 200

    def test_update_message(self, client: TestClient) -> None:
        r = client.post("/inbox/messages", headers=H, json={
            "network": "x",
            "source_type": "mention",
            "author_handle": "tweeter",
            "text": "Love this!",
        })
        mid = (r.json().get("message") or r.json()).get("id", 1)
        r2 = client.patch(f"/inbox/messages/{mid}", headers=H, json={
            "status": "in_progress",
            "assigned_to": "support_agent",
        })
        assert r2.status_code < 500

    def test_lock_message(self, client: TestClient) -> None:
        r = client.post("/inbox/messages", headers=H, json={
            "network": "instagram",
            "source_type": "dm",
            "author_handle": "locker",
            "text": "Need help please.",
        })
        mid = r.json().get("id", 1)
        r2 = client.post(f"/inbox/messages/{mid}/lock", headers=H, json={
            "locked_by": "agent_alice",
        })
        assert r2.status_code < 500

    def test_unlock_message(self, client: TestClient) -> None:
        r = client.post("/inbox/messages", headers=H, json={
            "network": "instagram",
            "source_type": "dm",
            "author_handle": "unlocker",
            "text": "Unlock me.",
        })
        mid = r.json().get("id", 1)
        client.post(f"/inbox/messages/{mid}/lock", headers=H, json={"locked_by": "agent_bob"})
        r2 = client.delete(f"/inbox/messages/{mid}/lock", headers=H)
        assert r2.status_code < 500

    def test_add_internal_note(self, client: TestClient) -> None:
        r = client.post("/inbox/messages", headers=H, json={
            "network": "linkedin",
            "source_type": "comment",
            "author_handle": "biz_contact",
            "text": "Interested in partnership.",
        })
        mid = r.json().get("id", 1)
        r2 = client.post(f"/inbox/messages/{mid}/notes", headers=H, json={
            "author": "agent_carol",
            "note": "Hot lead — follow up ASAP",
        })
        assert r2.status_code < 500

    def test_list_notes(self, client: TestClient) -> None:
        r = client.post("/inbox/messages", headers=H, json={
            "network": "instagram",
            "source_type": "dm",
            "author_handle": "note_getter",
            "text": "List my notes.",
        })
        mid = r.json().get("message", {}).get("id", r.json().get("id", 1))
        r2 = client.get(f"/inbox/messages/{mid}/notes", headers=H)
        assert r2.status_code == 200

    def test_inbox_stats(self, client: TestClient) -> None:
        r = client.get("/inbox/stats", headers=H)
        assert r.status_code == 200

    def test_create_saved_reply(self, client: TestClient) -> None:
        r = client.post("/inbox/saved-replies", headers=H, json={
            "title": "Thank you template",
            "body": "Thank you for reaching out! We'll get back to you shortly.",
            "networks": ["instagram", "facebook"],
        })
        assert r.status_code in {200, 201}

    def test_list_saved_replies(self, client: TestClient) -> None:
        r = client.get("/inbox/saved-replies", headers=H)
        assert r.status_code == 200


# ── Analytics Dashboard ───────────────────────────────────────────────────────

class TestAnalyticsDashboard:
    def test_dashboard(self, client: TestClient) -> None:
        r = client.get("/analytics/dashboard", headers=H)
        assert r.status_code == 200

    def test_metrics(self, client: TestClient) -> None:
        r = client.get("/analytics/metrics", headers=H)
        assert r.status_code == 200

    def test_predictions(self, client: TestClient) -> None:
        r = client.get("/analytics/predictions", headers=H)
        assert r.status_code == 200

    def test_export(self, client: TestClient) -> None:
        r = client.get("/analytics/export", headers=H)
        assert r.status_code == 200

    def test_benchmarks(self, client: TestClient) -> None:
        r = client.get("/analytics/benchmarks", headers=H)
        assert r.status_code == 200

    def test_kpi_insights(self, client: TestClient) -> None:
        r = client.get("/analytics/insights/kpi", headers=H)
        assert r.status_code == 200

    def test_intelligence_insights(self, client: TestClient) -> None:
        r = client.get("/analytics/insights/intelligence", headers=H)
        assert r.status_code == 200

    def test_create_report(self, client: TestClient) -> None:
        r = client.post("/analytics/reports", headers=H, json={
            "name": "Monthly Summary",
            "metrics": ["page_views", "conversions"],
            "date_range": "last_30_days",
        })
        assert r.status_code in {200, 201}

    def test_list_reports(self, client: TestClient) -> None:
        r = client.get("/analytics/reports", headers=H)
        assert r.status_code == 200

    def test_schedule_report(self, client: TestClient) -> None:
        r = client.post("/analytics/reports", headers=H, json={
            "name": "Weekly KPIs",
            "metrics": ["revenue"],
        })
        rid = r.json().get("id", 1)
        r2 = client.post("/analytics/schedule", headers=H, json={
            "report_id": rid,
            "frequency": "weekly",
            "recipients": ["admin@example.com"],
        })
        assert r2.status_code < 500

    def test_trend_insight(self, client: TestClient) -> None:
        r = client.post("/analytics/insights/trend", headers=H, json={
            "metric": "revenue",
            "period": "last_30_days",
        })
        assert r.status_code < 500

    def test_rollup_insight(self, client: TestClient) -> None:
        r = client.post("/analytics/insights/rollup", headers=H, json={
            "modules": ["crm", "social"],
            "label": "Q1 Rollup",
        })
        assert r.status_code < 500

    def test_revenue_attribution_touchpoints(self, client: TestClient) -> None:
        r = client.get("/analytics/revenue-attribution/touchpoints", headers=H)
        assert r.status_code == 200

    def test_revenue_attribution_report(self, client: TestClient) -> None:
        r = client.get("/analytics/revenue-attribution/report", headers=H)
        assert r.status_code == 200

    def test_posthog_capture(self, client: TestClient) -> None:
        r = client.post("/analytics/posthog/capture", headers=H, json={
            "event": "page_view",
            "distinct_id": "user-123",
            "properties": {"page": "/home"},
        })
        assert r.status_code < 500

    def test_plausible_track(self, client: TestClient) -> None:
        r = client.post("/analytics/plausible/track", headers=H, json={
            "name": "pageview",
            "url": "https://example.com/",
        })
        assert r.status_code < 500

    def test_matomo_track(self, client: TestClient) -> None:
        r = client.post("/analytics/matomo/track", headers=H, json={
            "action_name": "Home",
            "url": "https://example.com/",
        })
        assert r.status_code < 500


# ── Engagement ────────────────────────────────────────────────────────────────

class TestEngagement:
    def test_streak(self, client: TestClient) -> None:
        r = client.get("/engagement/streak", headers=H)
        assert r.status_code == 200

    def test_checkin(self, client: TestClient) -> None:
        r = client.post("/engagement/streak/check-in", headers=H)
        assert r.status_code < 500

    def test_streak_recover(self, client: TestClient) -> None:
        r = client.post("/engagement/streak/recover", headers=H)
        assert r.status_code < 500

    def test_referrals(self, client: TestClient) -> None:
        r = client.get("/engagement/referrals", headers=H)
        assert r.status_code == 200

    def test_generate_referral_code(self, client: TestClient) -> None:
        r = client.post("/engagement/referrals/generate-code", headers=H)
        assert r.status_code < 500

    def test_claim_referral(self, client: TestClient) -> None:
        r = client.post("/engagement/referrals/claim", headers=H, json={
            "code": "TESTREF123",
        })
        assert r.status_code < 500

    def test_achievements(self, client: TestClient) -> None:
        r = client.get("/engagement/achievements", headers=H)
        assert r.status_code == 200

    def test_evaluate_achievements(self, client: TestClient) -> None:
        r = client.post("/engagement/achievements/evaluate", headers=H)
        assert r.status_code < 500

    def test_fomo_feed(self, client: TestClient) -> None:
        r = client.get("/engagement/fomo/feed", headers=H)
        assert r.status_code == 200

    def test_create_fomo_rule(self, client: TestClient) -> None:
        r = client.post("/engagement/fomo/rules", headers=H, json={
            "event_type": "new_signup",
            "message_template": "{name} just joined!",
        })
        assert r.status_code < 500

    def test_trigger_fomo(self, client: TestClient) -> None:
        r = client.post("/engagement/fomo/trigger", headers=H, json={
            "event_type": "new_purchase",
            "data": {"product": "Pro Plan"},
        })
        assert r.status_code < 500

    def test_social_proof_events(self, client: TestClient) -> None:
        r = client.post("/engagement/social-proof/events", headers=H, json={
            "event_type": "purchase",
            "actor": "Jane D.",
            "detail": "Pro Plan",
        })
        assert r.status_code < 500

    def test_community_feed(self, client: TestClient) -> None:
        r = client.get("/engagement/community/feed", headers=H)
        assert r.status_code == 200

    def test_community_post(self, client: TestClient) -> None:
        r = client.post("/engagement/community/posts", headers=H, json={
            "content": "Hello community!",
            "post_type": "text",
        })
        assert r.status_code < 500

    def test_ai_best_friend_message(self, client: TestClient) -> None:
        r = client.post("/engagement/ai-best-friend/message", headers=H, json={
            "message": "Hello AI!",
        })
        assert r.status_code < 500

    def test_ai_best_friend_checkin(self, client: TestClient) -> None:
        r = client.post("/engagement/ai-best-friend/check-in", headers=H)
        assert r.status_code < 500
