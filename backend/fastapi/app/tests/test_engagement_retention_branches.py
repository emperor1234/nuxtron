"""Additional branch coverage for engagement_retention.py milestone and recovery paths."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

import pytest
from backend.fastapi.app.memory_stores import engagement_streaks
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H_MILESTONE = {"X-API-Key": "test-api-key", "X-Tenant-Id": "retention-milestone-tenant"}
H_RECOVERY = {"X-API-Key": "test-api-key", "X-Tenant-Id": "retention-recovery-tenant"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def _record_for(tenant_id: str) -> dict:
    rec = next((item for item in engagement_streaks if item.get("tenant_id") == tenant_id), None)
    if rec is None:
        rec = {
            "tenant_id": tenant_id,
            "current_streak": 0,
            "longest_streak": 0,
            "last_check_in_date": None,
            "last_recovery_date": None,
            "recoverable_streak": 0,
            "recoverable_until": None,
            "milestones_unlocked": [],
            "badge": "unranked",
            "updated_at": datetime.now(UTC).isoformat(),
        }
        engagement_streaks.append(rec)
    return rec


class TestEngagementRetentionBranches:
    def test_check_in_unlocks_day7_milestone_once(self, client: TestClient) -> None:
        rec = _record_for(H_MILESTONE["X-Tenant-Id"])
        rec["current_streak"] = 6
        rec["longest_streak"] = 6
        rec["last_check_in_date"] = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
        rec["recoverable_streak"] = 0
        rec["recoverable_until"] = None
        rec["milestones_unlocked"] = []

        r = client.post("/engagement/streak/check-in", headers=H_MILESTONE)
        assert r.status_code == 200
        data = r.json()
        assert data["already_checked_in"] is False
        assert data["milestone_unlocked"] == 7
        assert data["credits_awarded"] > 0

        # Repeat same-day check-in should be idempotent.
        r2 = client.post("/engagement/streak/check-in", headers=H_MILESTONE)
        assert r2.status_code == 200
        second = r2.json()
        assert second["already_checked_in"] is True
        assert second["credits_awarded"] == 0

    def test_recover_streak_success_then_cooldown_422(self, client: TestClient) -> None:
        today = datetime.now(UTC).date()
        rec = _record_for(H_RECOVERY["X-Tenant-Id"])
        rec["recoverable_streak"] = 5
        rec["recoverable_until"] = today.isoformat()
        rec["last_recovery_date"] = (today - timedelta(days=31)).isoformat()
        rec["current_streak"] = 0

        ok = client.post("/engagement/streak/recover", headers=H_RECOVERY)
        assert ok.status_code == 200
        ok_data = ok.json()
        assert ok_data["recovered"] is True
        assert ok_data["streak"]["current_streak"] == 5

        rec["recoverable_streak"] = 4
        rec["recoverable_until"] = today.isoformat()
        rec["last_recovery_date"] = today.isoformat()
        rec["current_streak"] = 0

        limited = client.post("/engagement/streak/recover", headers=H_RECOVERY)
        assert limited.status_code == 422
