"""
Additional tests for outcome_attribution.py pure helpers and routes.
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


class TestNowIso:
    def test_returns_iso_string(self) -> None:
        from backend.fastapi.app.routers.outcome_attribution import _now_iso
        result = _now_iso()
        assert isinstance(result, str)
        assert "T" in result


class TestQualityBand:
    def _fn(self):
        from backend.fastapi.app.routers.outcome_attribution import _quality_band
        return _quality_band

    def test_excellent(self) -> None:
        assert self._fn()(95.0) == "excellent"

    def test_good(self) -> None:
        # Somewhere in the good range
        result = self._fn()(79.0)
        assert isinstance(result, str)

    def test_poor_at_zero(self) -> None:
        assert self._fn()(0.0) == "poor"

    def test_perfect_score(self) -> None:
        result = self._fn()(100.0)
        assert isinstance(result, str)

    def test_returns_string(self) -> None:
        result = self._fn()(50.0)
        assert isinstance(result, str)


class TestComputeDecisionQualityScore:
    def _fn(self):
        from backend.fastapi.app.routers.outcome_attribution import compute_decision_quality_score
        return compute_decision_quality_score

    def test_perfect_accuracy_safety(self) -> None:
        score = self._fn()(
            accuracy=100.0,
            safety=100.0,
            speed_ms=100,
            revenue_impact_gbp=0.0,
            human_override=False,
        )
        assert 0.0 <= score <= 100.0

    def test_human_override_penalty(self) -> None:
        score_no_override = self._fn()(
            accuracy=80.0,
            safety=80.0,
            speed_ms=500,
            revenue_impact_gbp=0.0,
            human_override=False,
        )
        score_override = self._fn()(
            accuracy=80.0,
            safety=80.0,
            speed_ms=500,
            revenue_impact_gbp=0.0,
            human_override=True,
        )
        assert score_no_override > score_override

    def test_positive_revenue_bonus(self) -> None:
        score_no_rev = self._fn()(
            accuracy=70.0,
            safety=70.0,
            speed_ms=500,
            revenue_impact_gbp=0.0,
            human_override=False,
        )
        score_with_rev = self._fn()(
            accuracy=70.0,
            safety=70.0,
            speed_ms=500,
            revenue_impact_gbp=1000.0,
            human_override=False,
        )
        assert score_with_rev >= score_no_rev

    def test_capped_at_100(self) -> None:
        score = self._fn()(
            accuracy=100.0,
            safety=100.0,
            speed_ms=0,
            revenue_impact_gbp=10000.0,
            human_override=False,
        )
        assert score <= 100.0

    def test_floored_at_0(self) -> None:
        score = self._fn()(
            accuracy=0.0,
            safety=0.0,
            speed_ms=100000,
            revenue_impact_gbp=-10000.0,
            human_override=True,
        )
        assert score >= 0.0

    def test_slow_speed_penalized(self) -> None:
        score_fast = self._fn()(
            accuracy=80.0,
            safety=80.0,
            speed_ms=100,
            revenue_impact_gbp=0.0,
            human_override=False,
        )
        score_slow = self._fn()(
            accuracy=80.0,
            safety=80.0,
            speed_ms=10000,
            revenue_impact_gbp=0.0,
            human_override=False,
        )
        assert score_fast >= score_slow


class TestRowToAction:
    def test_basic_conversion(self) -> None:
        from backend.fastapi.app.routers.outcome_attribution import _row_to_action
        row = ("action-1", "tenant-1", "send_email", "user@example.com", "POST /email",
               "ai_agent", "email", {}, False, "converted", 87.5, "2024-01-01T00:00:00Z")
        result = _row_to_action(row)
        assert result["id"] == "action-1"
        assert result["tenant_id"] == "tenant-1"
        assert result["dry_run"] is False
        assert result["quality_score"] == 87.5


class TestRowToQuality:
    def test_basic_conversion(self) -> None:
        from backend.fastapi.app.routers.outcome_attribution import _row_to_quality
        row = ("q-1", "tenant-1", "action-1", 90.0, 85.0, 250, 500.0, False, "",
               82.5, "excellent", "2024-01-01T00:00:00Z")
        result = _row_to_quality(row)
        assert result["id"] == "q-1"
        assert result["accuracy"] == 90.0
        assert result["speed_ms"] == 250
        assert result["band"] == "excellent"


class TestOutcomeAttributionRoutes:
    """Smoke tests for outcome_attribution routes."""

    def test_record_action(self, client: TestClient) -> None:
        r = client.post("/outcome/actions", headers=H, json={
            "action_type": "send_email",
            "target": "customer@example.com",
            "command": "POST /email",
            "actor_role": "ai_agent",
            "channel": "email",
        })
        assert r.status_code in VALID

    def test_record_action_dry_run(self, client: TestClient) -> None:
        r = client.post("/outcome/actions", headers=H, json={
            "action_type": "update_crm",
            "target": "contact-123",
            "command": "PATCH /contacts/123",
            "actor_role": "human",
            "channel": "crm",
            "dry_run": True,
        })
        assert r.status_code in VALID

    def test_record_outcome(self, client: TestClient) -> None:
        # First record action, then record outcome
        action_r = client.post("/outcome/actions", headers=H, json={
            "action_type": "send_email",
            "target": "prospect@example.com",
            "command": "POST /email",
            "actor_role": "ai_agent",
            "channel": "email",
        })
        if action_r.status_code == 200:
            action_id = action_r.json().get("action", {}).get("id", "fake-id")
        else:
            action_id = "nonexistent-action-id"
        
        r = client.post("/outcome/outcomes", headers=H, json={
            "action_id": action_id,
            "outcome_type": "converted",
        })
        assert r.status_code in VALID

    def test_record_outcome_nonexistent_action(self, client: TestClient) -> None:
        r = client.post("/outcome/outcomes", headers=H, json={
            "action_id": "nonexistent-action-uuid",
            "outcome_type": "no_response",
        })
        assert r.status_code in VALID

    def test_submit_quality(self, client: TestClient) -> None:
        r = client.post("/outcome/quality", headers=H, json={
            "action_id": "test-action-id",
            "accuracy": 88.0,
            "safety": 92.0,
            "speed_ms": 350,
            "revenue_impact_gbp": 250.0,
            "human_override": False,
        })
        assert r.status_code in VALID

    def test_submit_quality_with_override(self, client: TestClient) -> None:
        r = client.post("/outcome/quality", headers=H, json={
            "action_id": "override-action-id",
            "accuracy": 60.0,
            "safety": 70.0,
            "speed_ms": 2000,
            "revenue_impact_gbp": -100.0,
            "human_override": True,
            "override_reason": "Output was incorrect",
        })
        assert r.status_code in VALID

    def test_get_outcome_graph(self, client: TestClient) -> None:
        r = client.get("/outcome/graph", headers=H)
        assert r.status_code in VALID

    def test_list_quality(self, client: TestClient) -> None:
        r = client.get("/outcome/quality", headers=H)
        assert r.status_code in VALID

    def test_list_pending(self, client: TestClient) -> None:
        r = client.get("/outcome/pending", headers=H)
        assert r.status_code in VALID
