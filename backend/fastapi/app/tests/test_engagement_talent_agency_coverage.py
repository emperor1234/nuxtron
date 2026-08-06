"""Focused coverage tests for engagement_talent_agency.py missing branches."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "talent-agency-coverage-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestTalentAgencyCoverage:
    def test_rate_card_success_updates_creator_rate(self, client: TestClient) -> None:
        r_creator = client.post(
            "/talent-agency/creators",
            headers=H,
            json={
                "name": "Casey Creator",
                "niche": "tech",
                "platform": "youtube",
                "followers": 120000,
                "rate_card_usd": 250.0,
            },
        )
        assert r_creator.status_code in (200, 201)
        creator_id = r_creator.json()["creator"]["id"]

        r_rate = client.post(
            "/talent-agency/rate-cards",
            headers=H,
            json={
                "creator_id": creator_id,
                "post_rate_usd": 300,
                "story_rate_usd": 150,
                "reel_rate_usd": 450,
                "package_rate_usd": 500,
                "currency": "usd",
            },
        )
        assert r_rate.status_code in (200, 201)
        data = r_rate.json()
        assert data["rate_card"]["currency"] == "USD"

        r_roster = client.get("/talent-agency/roster", headers=H)
        assert r_roster.status_code == 200
        creators = r_roster.json()["creators"]
        c = next(item for item in creators if item["id"] == creator_id)
        assert c["rate_card_usd"] == 500

    def test_propose_deal_creator_not_found(self, client: TestClient) -> None:
        r = client.post(
            "/talent-agency/deals",
            headers=H,
            json={
                "creator_id": 999999,
                "brand_name": "Ghost Brand",
                "deliverables": ["1 post"],
                "budget_usd": 500,
            },
        )
        assert r.status_code == 404

    def test_propose_deal_success_with_string_deliverables(self, client: TestClient) -> None:
        r_roster = client.get("/talent-agency/roster", headers=H)
        creator_id = r_roster.json()["creators"][0]["id"]

        r = client.post(
            "/talent-agency/deals",
            headers=H,
            json={
                "creator_id": creator_id,
                "brand_name": "Acme",
                "deliverables": "1 reel + 2 stories,1 post",
                "budget_usd": 1400,
                "currency": "usd",
                "note": "initial offer",
            },
        )
        assert r.status_code in (200, 201)
        deal = r.json()["deal"]
        assert deal["status"] == "proposed"
        assert deal["currency"] == "USD"
        assert len(deal["deliverables"]) >= 3

    def test_propose_deal_success_with_list_deliverables(self, client: TestClient) -> None:
        r_roster = client.get("/talent-agency/roster", headers=H)
        creator_id = r_roster.json()["creators"][0]["id"]

        r = client.post(
            "/talent-agency/deals",
            headers=H,
            json={
                "creator_id": creator_id,
                "brand_name": "List Brand",
                "deliverables": [" 1 post ", "", "2 stories"],
                "budget_usd": 600,
            },
        )
        assert r.status_code in (200, 201)
        deal = r.json()["deal"]
        assert deal["deliverables"] == ["1 post", "2 stories"]

    def test_accept_deal_with_counter_rate_and_reject(self, client: TestClient) -> None:
        r_deals = client.get("/talent-agency/deals", headers=H)
        deal_id = r_deals.json()["deals"][0]["id"]

        r = client.post(
            "/talent-agency/deals/accept",
            headers=H,
            json={
                "deal_id": deal_id,
                "accepted": False,
                "counter_rate_usd": 2200,
                "note": "counter submitted",
            },
        )
        assert r.status_code in (200, 201)
        deal = r.json()["deal"]
        assert deal["accepted"] is False
        assert deal["budget_usd"] == 2200
        assert deal["status"] == "proposed"
        assert deal["note"] == "counter submitted"
        assert "updated_at" in deal

    def test_accept_deal_stage_thresholds(self, client: TestClient) -> None:
        r_deals = client.get("/talent-agency/deals", headers=H)
        deal_id = r_deals.json()["deals"][0]["id"]

        r_enterprise = client.post(
            "/talent-agency/deals/accept",
            headers=H,
            json={"deal_id": deal_id, "accepted": True, "counter_rate_usd": 6000},
        )
        assert r_enterprise.status_code in (200, 201)
        assert r_enterprise.json()["deal"]["status"] == "enterprise_deal"

        r_mid = client.post(
            "/talent-agency/deals/accept",
            headers=H,
            json={"deal_id": deal_id, "accepted": True, "counter_rate_usd": 1500},
        )
        assert r_mid.status_code in (200, 201)
        assert r_mid.json()["deal"]["status"] == "mid_market_deal"

        r_micro = client.post(
            "/talent-agency/deals/accept",
            headers=H,
            json={"deal_id": deal_id, "accepted": True, "counter_rate_usd": 500},
        )
        assert r_micro.status_code in (200, 201)
        assert r_micro.json()["deal"]["status"] == "micro_deal"

    def test_accept_deal_not_found(self, client: TestClient) -> None:
        r = client.post(
            "/talent-agency/deals/accept",
            headers=H,
            json={"deal_id": 987654, "accepted": True},
        )
        assert r.status_code == 404

    def test_overview_after_acceptance(self, client: TestClient) -> None:
        r = client.get("/talent-agency/overview", headers=H)
        assert r.status_code == 200
        ta = r.json()["talent_agency"]
        assert ta["accepted_deals"] >= 1
        assert ta["marketplace_stage"] == "active"
