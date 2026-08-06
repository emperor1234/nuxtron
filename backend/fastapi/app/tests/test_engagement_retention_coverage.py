"""Coverage tests for engagement_retention.py — streak, check-in, recover, leaderboard, withdrawal-preview, earnings-ticker."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "retention-coverage-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


class TestEngagementRetentionCoverage:
    def test_get_streak_initial(self, client: TestClient) -> None:
        r = client.get("/engagement/streak", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "streak" in data
        assert "milestone_rewards" in data
        streak = data["streak"]
        assert "current_streak" in streak
        assert "longest_streak" in streak
        assert "badge" in streak

    def test_check_in_first_time(self, client: TestClient) -> None:
        r = client.post("/engagement/streak/check-in", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["already_checked_in"] is False
        assert data["streak"]["current_streak"] >= 1

    def test_check_in_already_checked_in_today(self, client: TestClient) -> None:
        # Second check-in on same day should be idempotent
        r = client.post("/engagement/streak/check-in", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["already_checked_in"] is True
        assert data["credits_awarded"] == 0

    def test_recover_streak_no_recoverable_returns_422(self, client: TestClient) -> None:
        """No recoverable streak should return 422."""
        r = client.post("/engagement/streak/recover", headers=H)
        assert r.status_code == 422

    def test_streak_leaderboard(self, client: TestClient) -> None:
        r = client.get("/engagement/streak/leaderboard", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "leaderboard" in data
        assert isinstance(data["leaderboard"], list)

    def test_withdrawal_preview(self, client: TestClient) -> None:
        r = client.get("/engagement/withdrawal-preview", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "withdrawal_preview" in data
        wp = data["withdrawal_preview"]
        assert "dependency_score" in wp
        assert "what_you_will_lose" in wp
        assert isinstance(wp["what_you_will_lose"], list)
        assert len(wp["what_you_will_lose"]) == 8

    def test_earnings_ticker_default_limit(self, client: TestClient) -> None:
        r = client.get("/engagement/earnings-ticker", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert "events" in data or "ticker" in data or "status" in data

    def test_earnings_ticker_custom_limit(self, client: TestClient) -> None:
        r = client.get("/engagement/earnings-ticker", headers=H, params={"limit": 5})
        assert r.status_code == 200
