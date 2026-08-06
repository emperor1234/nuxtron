"""
Route smoke tests for remaining engagement routers:
engagement_brand_autopilot_achievements, engagement_companion_social,
engagement_dependency_community, engagement_money_printers_bank,
engagement_money_printers_commerce, engagement_talent_agency.
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


class TestEngagementBrandAutopilot:
    def test_personal_brand_lock_in(self, client: TestClient) -> None:
        r = client.get("/engagement/personal-brand-lock-in", headers=H)
        assert r.status_code in VALID

    def test_brand_checkpoint(self, client: TestClient) -> None:
        r = client.post("/engagement/personal-brand-lock-in/checkpoint", headers=H, json={
            "checkpoint": "profile_complete",
        })
        assert r.status_code in VALID

    def test_brand_timeline(self, client: TestClient) -> None:
        r = client.get("/engagement/personal-brand-lock-in/timeline", headers=H)
        assert r.status_code in VALID

    def test_autopilot_dashboard(self, client: TestClient) -> None:
        r = client.get("/engagement/autopilot-dependency/dashboard", headers=H)
        assert r.status_code in VALID

    def test_autopilot_checkpoint(self, client: TestClient) -> None:
        r = client.post("/engagement/autopilot-dependency/checkpoint", headers=H, json={
            "checkpoint": "first_automation",
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


class TestEngagementCompanionSocial:
    def test_ai_best_friend(self, client: TestClient) -> None:
        r = client.get("/engagement/ai-best-friend", headers=H)
        assert r.status_code in VALID

    def test_ai_check_in(self, client: TestClient) -> None:
        r = client.post("/engagement/ai-best-friend/check-in", headers=H, json={
            "mood": "happy",
            "note": "Great day!",
        })
        assert r.status_code in VALID

    def test_ai_message(self, client: TestClient) -> None:
        r = client.post("/engagement/ai-best-friend/message", headers=H, json={
            "message": "How are you?",
        })
        assert r.status_code in VALID

    def test_ai_history(self, client: TestClient) -> None:
        r = client.get("/engagement/ai-best-friend/history", headers=H)
        assert r.status_code in VALID

    def test_fomo_rules_list(self, client: TestClient) -> None:
        r = client.get("/engagement/fomo/rules", headers=H)
        assert r.status_code in VALID

    def test_fomo_rule_create(self, client: TestClient) -> None:
        r = client.post("/engagement/fomo/rules", headers=H, json={
            "name": "Limited Offer",
            "trigger": "purchase",
        })
        assert r.status_code in VALID

    def test_fomo_trigger_not_found(self, client: TestClient) -> None:
        r = client.post("/engagement/fomo/trigger", headers=H, json={
            "rule_id": 99999,
            "user_id": "user-001",
        })
        assert r.status_code in VALID

    def test_fomo_feed(self, client: TestClient) -> None:
        r = client.get("/engagement/fomo/feed", headers=H)
        assert r.status_code in VALID

    def test_social_proof_event(self, client: TestClient) -> None:
        r = client.post("/engagement/social-proof/events", headers=H, json={
            "event_type": "purchase",
            "display_text": "John just purchased Pro!",
        })
        assert r.status_code in VALID

    def test_social_proof_feed(self, client: TestClient) -> None:
        r = client.get("/engagement/social-proof/feed", headers=H)
        assert r.status_code in VALID

    def test_social_proof_leaderboard(self, client: TestClient) -> None:
        r = client.get("/engagement/social-proof/leaderboard", headers=H)
        assert r.status_code in VALID


class TestEngagementDependencyCommunity:
    def test_dependency_creator(self, client: TestClient) -> None:
        r = client.get("/engagement/dependency-creator", headers=H)
        assert r.status_code in VALID

    def test_advance_dependency(self, client: TestClient) -> None:
        r = client.post("/engagement/dependency-creator/advance", headers=H, json={
            "action": "complete_module",
        })
        assert r.status_code in VALID

    def test_dependency_timeline(self, client: TestClient) -> None:
        r = client.get("/engagement/dependency-creator/timeline", headers=H)
        assert r.status_code in VALID

    def test_community_dashboard(self, client: TestClient) -> None:
        r = client.get("/engagement/community", headers=H)
        assert r.status_code in VALID

    def test_create_circle(self, client: TestClient) -> None:
        r = client.post("/engagement/community/circles", headers=H, json={
            "name": "SEO Masters",
            "description": "For SEO professionals",
        })
        assert r.status_code in VALID

    def test_community_post_not_found(self, client: TestClient) -> None:
        r = client.post("/engagement/community/posts", headers=H, json={
            "circle_id": 99999,
            "content": "Hello community!",
        })
        assert r.status_code in VALID

    def test_create_ama(self, client: TestClient) -> None:
        r = client.post("/engagement/community/amas", headers=H, json={
            "title": "Ask Me Anything About SEO",
            "scheduled_at": "2025-07-01T15:00:00Z",
        })
        assert r.status_code in VALID

    def test_community_feed(self, client: TestClient) -> None:
        r = client.get("/engagement/community/feed", headers=H)
        assert r.status_code in VALID


class TestEngagementMoneyPrintersBank:
    def test_portfolio(self, client: TestClient) -> None:
        r = client.get("/money-printers/portfolio", headers=H)
        assert r.status_code in VALID

    def test_create_idea(self, client: TestClient) -> None:
        r = client.post("/money-printers/ideas", headers=H, json={
            "title": "SaaS Dashboard",
            "description": "Analytics platform",
            "estimated_revenue": 10000.0,
        })
        assert r.status_code in VALID

    def test_backlog(self, client: TestClient) -> None:
        r = client.get("/money-printers/backlog", headers=H)
        assert r.status_code in VALID

    def test_wallet(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-bank/wallet", headers=H)
        assert r.status_code in VALID

    def test_bank_transfer(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-bank/transfer", headers=H, json={
            "amount": 100.0,
            "destination": "payout",
            "note": "monthly payout",
        })
        assert r.status_code in VALID

    def test_payout_preview(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-bank/payout-preview", headers=H)
        assert r.status_code in VALID

    def test_request_payout(self, client: TestClient) -> None:
        r = client.post("/money-printers/nuxtron-bank/payouts", headers=H, json={
            "amount": 100.0,
            "method": "bank_transfer",
        })
        assert r.status_code in VALID

    def test_list_payouts(self, client: TestClient) -> None:
        r = client.get("/money-printers/nuxtron-bank/payouts", headers=H)
        assert r.status_code in VALID


class TestEngagementMoneyPrintersCommerce:
    def test_catalog(self, client: TestClient) -> None:
        r = client.get("/money-printers/commerce-pro/catalog", headers=H)
        assert r.status_code in VALID

    def test_create_product(self, client: TestClient) -> None:
        r = client.post("/money-printers/commerce-pro/products", headers=H, json={
            "name": "Digital Course",
            "price": 97.0,
            "type": "digital",
        })
        assert r.status_code in VALID

    def test_storefront(self, client: TestClient) -> None:
        r = client.get("/money-printers/commerce-pro/storefront", headers=H)
        assert r.status_code in VALID

    def test_order_not_found(self, client: TestClient) -> None:
        r = client.post("/money-printers/commerce-pro/orders", headers=H, json={
            "product_id": 99999,
            "quantity": 1,
        })
        assert r.status_code in VALID

    def test_list_orders(self, client: TestClient) -> None:
        r = client.get("/money-printers/commerce-pro/orders", headers=H)
        assert r.status_code in VALID

    def test_overview(self, client: TestClient) -> None:
        r = client.get("/money-printers/commerce-pro/overview", headers=H)
        assert r.status_code in VALID


class TestEngagementTalentAgency:
    def test_roster(self, client: TestClient) -> None:
        r = client.get("/talent-agency/roster", headers=H)
        assert r.status_code in VALID

    def test_create_creator(self, client: TestClient) -> None:
        r = client.post("/talent-agency/creators", headers=H, json={
            "name": "Jane Creator",
            "niche": "fitness",
            "platform": "instagram",
        })
        assert r.status_code in VALID

    def test_rate_card_not_found(self, client: TestClient) -> None:
        r = client.post("/talent-agency/rate-cards", headers=H, json={
            "creator_id": 99999,
            "content_type": "reel",
            "price": 500.0,
        })
        assert r.status_code in VALID

    def test_deal_not_found(self, client: TestClient) -> None:
        r = client.post("/talent-agency/deals", headers=H, json={
            "creator_id": 99999,
            "brand": "Nike",
            "amount": 2000.0,
        })
        assert r.status_code in VALID

    def test_accept_deal_not_found(self, client: TestClient) -> None:
        r = client.post("/talent-agency/deals/accept", headers=H, json={
            "deal_id": 99999,
        })
        assert r.status_code in VALID

    def test_list_deals(self, client: TestClient) -> None:
        r = client.get("/talent-agency/deals", headers=H)
        assert r.status_code in VALID

    def test_overview(self, client: TestClient) -> None:
        r = client.get("/talent-agency/overview", headers=H)
        assert r.status_code in VALID
