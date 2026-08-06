"""Focused coverage tests for influencer.py missing branches."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "influencer-coverage-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestInfluencerCoverage:
    def test_profile_success(self, client: TestClient) -> None:
        r = client.get("/influencer/profile/1001", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["influencer"]["id"] == 1001

    def test_profile_not_found(self, client: TestClient) -> None:
        r = client.get("/influencer/profile/999999", headers=H)
        assert r.status_code == 404

    def test_fraud_check_low_risk_branch(self, client: TestClient) -> None:
        r = client.post("/influencer/fraud-check", headers=H, json={"influencer_id": 1001})
        assert r.status_code == 200
        report = r.json()["fraud_report"]
        assert report["overall_risk"] == "low"
        assert report["recommendation"] == "safe_to_proceed"
        assert report["fake_follower_pct"] >= 0
        assert report["bot_activity_score"] >= 0

    def test_fraud_check_medium_risk_branch(self, client: TestClient) -> None:
        r = client.post("/influencer/fraud-check", headers=H, json={"influencer_id": 1004})
        assert r.status_code == 200
        report = r.json()["fraud_report"]
        assert report["overall_risk"] == "medium"
        assert report["recommendation"] == "manual_review_required"

    def test_outreach_not_found(self, client: TestClient) -> None:
        r = client.post(
            "/influencer/outreach",
            headers=H,
            json={
                "influencer_id": 999999,
                "message": "This is a valid length collaboration outreach message.",
                "offer_amount": 500,
            },
        )
        assert r.status_code == 404

    def test_outreach_success(self, client: TestClient) -> None:
        r = client.post(
            "/influencer/outreach",
            headers=H,
            json={
                "influencer_id": 1002,
                "message": "Hello creator, we would love to discuss a sponsored partnership this month.",
                "offer_amount": 1200,
                "currency": "usd",
            },
        )
        assert r.status_code in (200, 201)
        outreach = r.json()["outreach"]
        assert outreach["status"] == "sent"
        assert outreach["handle"] == "@contentqueen_biz"
        assert outreach["currency"] == "usd"

    def test_campaign_then_analytics(self, client: TestClient) -> None:
        c = client.post(
            "/influencer/campaigns",
            headers=H,
            json={
                "name": "Creator Push",
                "objective": "awareness",
                "budget": 2400,
                "currency": "USD",
                "influencer_ids": [1001, 1002],
                "brief": "Launch push for Q2.",
            },
        )
        assert c.status_code in (200, 201)

        a = client.get("/influencer/analytics", headers=H)
        assert a.status_code == 200
        analytics = a.json()["analytics"]
        assert analytics["total_campaigns"] >= 1
        assert analytics["total_outreach_sent"] >= 1
        assert analytics["total_budget_allocated"] >= 2400
