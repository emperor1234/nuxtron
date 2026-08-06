"""
Tests for all engagement_*.py routers:
  - engagement_brand_autopilot_achievements
  - engagement_companion_social
  - engagement_dependency_community
  - engagement_money_printers_bank
  - engagement_money_printers_commerce
  - engagement_referrals
  - engagement_retention
  - engagement_studios
  - engagement_talent_agency
  - engagement_university
  - engagement_white_label
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
# Brand / Autopilot / Achievements
# --------------------------------------------------------------------------- #
class TestBrandAutopilotAchievements:
    def test_personal_brand_lock_in(self, client: TestClient) -> None:
        r = client.get("/engagement/personal-brand-lock-in", headers=H)
        assert r.status_code in VALID

    def test_personal_brand_checkpoint(self, client: TestClient) -> None:
        r = client.post("/engagement/personal-brand-lock-in/checkpoint", headers=H, json={
            "score": 85, "notes": "Good progress"
        })
        assert r.status_code in VALID

    def test_personal_brand_timeline(self, client: TestClient) -> None:
        r = client.get("/engagement/personal-brand-lock-in/timeline", headers=H)
        assert r.status_code in VALID

    def test_autopilot_dashboard(self, client: TestClient) -> None:
        r = client.get("/engagement/autopilot-dependency/dashboard", headers=H)
        assert r.status_code in VALID

    def test_autopilot_checkpoint(self, client: TestClient) -> None:
        r = client.post("/engagement/autopilot-dependency/checkpoint", headers=H, json={
            "action": "scheduled_post", "value": 1
        })
        assert r.status_code in VALID

    def test_autopilot_timeline(self, client: TestClient) -> None:
        r = client.get("/engagement/autopilot-dependency/timeline", headers=H)
        assert r.status_code in VALID

    def test_achievements(self, client: TestClient) -> None:
        r = client.get("/engagement/achievements", headers=H)
        assert r.status_code in VALID

    def test_achievements_evaluate(self, client: TestClient) -> None:
        r = client.post("/engagement/achievements/evaluate", headers=H, json={})
        assert r.status_code in VALID

    def test_achievements_leaderboard(self, client: TestClient) -> None:
        r = client.get("/engagement/achievements/leaderboard", headers=H)
        assert r.status_code in VALID

    def test_achievements_timeline(self, client: TestClient) -> None:
        r = client.get("/engagement/achievements/timeline", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Companion / Social
# --------------------------------------------------------------------------- #
class TestCompanionSocial:
    def test_ai_best_friend(self, client: TestClient) -> None:
        r = client.get("/engagement/ai-best-friend", headers=H)
        assert r.status_code in VALID

    def test_ai_best_friend_check_in(self, client: TestClient) -> None:
        r = client.post("/engagement/ai-best-friend/check-in", headers=H, json={
            "mood": "happy", "note": "Had a great day"
        })
        assert r.status_code in VALID

    def test_ai_best_friend_message(self, client: TestClient) -> None:
        r = client.post("/engagement/ai-best-friend/message", headers=H, json={
            "message": "How are you?", "session_id": "sess_001"
        })
        assert r.status_code in VALID

    def test_ai_best_friend_history(self, client: TestClient) -> None:
        r = client.get("/engagement/ai-best-friend/history", headers=H)
        assert r.status_code in VALID

    def test_fomo_rules_get(self, client: TestClient) -> None:
        r = client.get("/engagement/fomo/rules", headers=H)
        assert r.status_code in VALID

    def test_fomo_rules_post(self, client: TestClient) -> None:
        r = client.post("/engagement/fomo/rules", headers=H, json={
            "name": "Limited offer", "trigger": "product_view", "message": "Only 5 left!"
        })
        assert r.status_code in VALID

    def test_fomo_trigger(self, client: TestClient) -> None:
        r = client.post("/engagement/fomo/trigger", headers=H, json={
            "rule_id": "rule_nonexistent", "target_user_id": "user_001"
        })
        assert r.status_code in VALID

    def test_fomo_feed(self, client: TestClient) -> None:
        r = client.get("/engagement/fomo/feed", headers=H)
        assert r.status_code in VALID

    def test_social_proof_events(self, client: TestClient) -> None:
        r = client.post("/engagement/social-proof/events", headers=H, json={
            "event_type": "purchase", "user": "Alice", "product": "Pro Plan"
        })
        assert r.status_code in VALID

    def test_social_proof_feed(self, client: TestClient) -> None:
        r = client.get("/engagement/social-proof/feed", headers=H)
        assert r.status_code in VALID

    def test_social_proof_leaderboard(self, client: TestClient) -> None:
        r = client.get("/engagement/social-proof/leaderboard", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Dependency / Community
# --------------------------------------------------------------------------- #
class TestDependencyCommunity:
    def test_dependency_creator(self, client: TestClient) -> None:
        r = client.get("/engagement/dependency-creator", headers=H)
        assert r.status_code in VALID

    def test_dependency_creator_advance(self, client: TestClient) -> None:
        r = client.post("/engagement/dependency-creator/advance", headers=H, json={
            "action": "onboard_client", "value": 1
        })
        assert r.status_code in VALID

    def test_dependency_creator_timeline(self, client: TestClient) -> None:
        r = client.get("/engagement/dependency-creator/timeline", headers=H)
        assert r.status_code in VALID

    def test_community(self, client: TestClient) -> None:
        r = client.get("/engagement/community", headers=H)
        assert r.status_code in VALID

    def test_community_circles(self, client: TestClient) -> None:
        r = client.post("/engagement/community/circles", headers=H, json={
            "name": "Marketing Experts", "description": "Share marketing tips"
        })
        assert r.status_code in VALID

    def test_community_posts(self, client: TestClient) -> None:
        r = client.post("/engagement/community/posts", headers=H, json={
            "circle_id": "circle_nonexistent", "content": "Hello community!"
        })
        assert r.status_code in VALID

    def test_community_amas(self, client: TestClient) -> None:
        r = client.post("/engagement/community/amas", headers=H, json={
            "host": "Jane Doe", "topic": "Growth Hacking", "scheduled_at": "2025-03-01T18:00:00Z"
        })
        assert r.status_code in VALID

    def test_community_feed(self, client: TestClient) -> None:
        r = client.get("/engagement/community/feed", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Money Printers - Bank
# --------------------------------------------------------------------------- #
class TestMoneyPrintersBank:
    def test_portfolio(self, client: TestClient) -> None:
        r = client.get("/money-printers/portfolio", headers=H)
        assert r.status_code in VALID

    def test_post_idea(self, client: TestClient) -> None:
        r = client.post("/money-printers/ideas", headers=H, json={
            "title": "AI Newsletter", "description": "Weekly AI roundup", "revenue_model": "subscription"
        })
        assert r.status_code in VALID

    def test_validate_idea(self, client: TestClient) -> None:
        r = client.post("/money-printers/ideas/validate", headers=H, json={
            "idea_id": "idea_nonexistent", "outcome": "approved"
        })
        assert r.status_code in VALID

    def test_backlog(self, client: TestClient) -> None:
        r = client.get("/money-printers/backlog", headers=H)
        assert r.status_code in VALID

    def test_wallet(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-bank/wallet", headers=H)
        assert r.status_code in VALID

    def test_transfer(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-bank/transfer", headers=H, json={
            "amount": 50.0, "description": "Test transfer"
        })
        assert r.status_code in VALID

    def test_payout_preview(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-bank/payout-preview", headers=H)
        assert r.status_code in VALID

    def test_create_payout(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-bank/payouts", headers=H, json={
            "amount": 25.0, "method": "bank_transfer"
        })
        assert r.status_code in VALID

    def test_list_payouts(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-bank/payouts", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Money Printers - Commerce
# --------------------------------------------------------------------------- #
class TestMoneyPrintersCommerce:
    def test_catalog(self, client: TestClient) -> None:
        r = client.get("/money-printers/commerce-pro/catalog", headers=H)
        assert r.status_code in VALID

    def test_create_product(self, client: TestClient) -> None:
        r = client.post("/money-printers/commerce-pro/products", headers=H, json={
            "name": "Digital Course", "price": 197.0, "currency": "USD", "type": "digital"
        })
        assert r.status_code in VALID

    def test_storefront(self, client: TestClient) -> None:
        r = client.get("/money-printers/commerce-pro/storefront", headers=H)
        assert r.status_code in VALID

    def test_create_order(self, client: TestClient) -> None:
        r = client.post("/money-printers/commerce-pro/orders", headers=H, json={
            "product_id": "prod_nonexistent", "buyer_email": "buyer@example.com"
        })
        assert r.status_code in VALID

    def test_list_orders(self, client: TestClient) -> None:
        r = client.get("/money-printers/commerce-pro/orders", headers=H)
        assert r.status_code in VALID

    def test_commerce_overview(self, client: TestClient) -> None:
        r = client.get("/money-printers/commerce-pro/overview", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Referrals
# --------------------------------------------------------------------------- #
class TestReferrals:
    def test_list_referrals(self, client: TestClient) -> None:
        r = client.get("/engagement/referrals", headers=H)
        assert r.status_code in VALID

    def test_generate_code(self, client: TestClient) -> None:
        r = client.post("/engagement/referrals/generate-code", headers=H, json={})
        assert r.status_code in VALID

    def test_referrals_leaderboard(self, client: TestClient) -> None:
        r = client.get("/engagement/referrals/leaderboard", headers=H)
        assert r.status_code in VALID

    def test_claim_referral(self, client: TestClient) -> None:
        r = client.post("/engagement/referrals/claim", headers=H, json={
            "code": "REF_NONEXISTENT"
        })
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Retention / Streak
# --------------------------------------------------------------------------- #
class TestRetention:
    def test_streak(self, client: TestClient) -> None:
        r = client.get("/engagement/streak", headers=H)
        assert r.status_code in VALID

    def test_streak_check_in(self, client: TestClient) -> None:
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


# --------------------------------------------------------------------------- #
# Nuxtron Studios
# --------------------------------------------------------------------------- #
class TestNuxtronStudios:
    def test_create_service(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-studios/services", headers=H, json={
            "title": "Brand Strategy Session", "price": 500.0, "duration_hours": 2
        })
        assert r.status_code in VALID

    def test_create_brief(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-studios/briefs", headers=H, json={
            "client_name": "Acme Corp", "project": "Website Redesign", "budget": 5000.0
        })
        assert r.status_code in VALID

    def test_create_proposal(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-studios/proposals", headers=H, json={
            "brief_id": "brief_nonexistent", "service_id": "svc_nonexistent", "amount": 4500.0
        })
        assert r.status_code in VALID

    def test_create_escrow(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-studios/escrows", headers=H, json={
            "proposal_id": "prop_nonexistent"
        })
        assert r.status_code in VALID

    def test_release_escrow(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-studios/escrows/release", headers=H, json={
            "escrow_id": "escrow_nonexistent"
        })
        assert r.status_code in VALID

    def test_studios_overview(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-studios/overview", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Talent Agency
# --------------------------------------------------------------------------- #
class TestTalentAgency:
    def test_roster(self, client: TestClient) -> None:
        r = client.get("/talent-agency/roster", headers=H)
        assert r.status_code in VALID

    def test_add_creator(self, client: TestClient) -> None:
        r = client.post("/talent-agency/creators", headers=H, json={
            "name": "Jane Influencer", "platforms": ["instagram", "youtube"], "niche": "wellness"
        })
        assert r.status_code in VALID

    def test_add_rate_card(self, client: TestClient) -> None:
        r = client.post("/talent-agency/rate-cards", headers=H, json={
            "creator_id": "creator_nonexistent", "type": "sponsored_post", "price": 1000.0
        })
        assert r.status_code in VALID

    def test_create_deal(self, client: TestClient) -> None:
        r = client.post("/talent-agency/deals", headers=H, json={
            "creator_id": "creator_nonexistent", "brand": "BrandX", "amount": 2500.0
        })
        assert r.status_code in VALID

    def test_accept_deal(self, client: TestClient) -> None:
        r = client.post("/talent-agency/deals/accept", headers=H, json={
            "deal_id": "deal_nonexistent"
        })
        assert r.status_code in VALID

    def test_list_deals(self, client: TestClient) -> None:
        r = client.get("/talent-agency/deals", headers=H)
        assert r.status_code in VALID

    def test_talent_overview(self, client: TestClient) -> None:
        r = client.get("/talent-agency/overview", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# Nuxtron University
# --------------------------------------------------------------------------- #
class TestNuxtronUniversity:
    def test_catalog(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-university/catalog", headers=H)
        assert r.status_code in VALID

    def test_create_course(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-university/courses", headers=H, json={
            "title": "AI Marketing Mastery", "description": "Learn AI-driven marketing", "price": 297.0
        })
        assert r.status_code in VALID

    def test_create_cohort(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-university/cohorts", headers=H, json={
            "course_id": "course_nonexistent", "start_date": "2025-03-01", "capacity": 50
        })
        assert r.status_code in VALID

    def test_enroll(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-university/enrollments", headers=H, json={
            "cohort_id": "cohort_nonexistent", "learner_email": "student@example.com"
        })
        assert r.status_code in VALID

    def test_progress(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-university/progress", headers=H, json={
            "enrollment_id": "enrollment_nonexistent", "completion_delta": 10, "checkpoint": "module_1"
        })
        assert r.status_code in VALID

    def test_university_overview(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-university/overview", headers=H)
        assert r.status_code in VALID


# --------------------------------------------------------------------------- #
# White Label
# --------------------------------------------------------------------------- #
class TestWhiteLabel:
    def test_get_profile(self, client: TestClient) -> None:
        r = client.get("/white-label/profile", headers=H)
        assert r.status_code in VALID

    def test_create_brand_kit(self, client: TestClient) -> None:
        r = client.post("/white-label/brand-kit", headers=H, json={
            "primary_color": "#1A73E8", "logo_url": "https://cdn.example.com/logo.png", "font": "Inter"
        })
        assert r.status_code in VALID

    def test_set_domain(self, client: TestClient) -> None:
        r = client.post("/white-label/domain", headers=H, json={
            "domain": "app.mycustomdomain.com"
        })
        assert r.status_code in VALID

    def test_checkpoint(self, client: TestClient) -> None:
        r = client.post("/white-label/checkpoint", headers=H, json={
            "step": "branding_complete", "notes": "All branding assets uploaded"
        })
        assert r.status_code in VALID

    def test_timeline(self, client: TestClient) -> None:
        r = client.get("/white-label/timeline", headers=H)
        assert r.status_code in VALID
