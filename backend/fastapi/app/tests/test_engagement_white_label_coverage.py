"""
Coverage tests for engagement_white_label.py router.

All 5 endpoints: GET /white-label/profile, POST /white-label/brand-kit,
POST /white-label/domain, POST /white-label/checkpoint, GET /white-label/timeline.

Includes the progressed=True branch in checkpoint (credits_awarded=45).

Stages: ['foundation'(0), 'branded'(1), 'client_ready'(2), 'agency_grade'(3)]
Score thresholds: branded>=30, client_ready>=60, agency_grade>=85.
"""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

TENANT = "white-label-coverage-tenant"
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": TENANT}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestWhiteLabelCoverage:
    def test_get_white_label_profile_initial(self, client: TestClient) -> None:
        """GET /white-label/profile — fresh tenant, stage=foundation, score=0."""
        r = client.get("/white-label/profile", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["tenant_id"] == TENANT
        wl = data["white_label"]
        assert "profile" in wl
        assert "stages" in wl
        assert "signals" in wl
        assert wl["profile"]["stage"] == "foundation"
        assert wl["profile"]["white_label_score"] == 0

    def test_checkpoint_no_progression(self, client: TestClient) -> None:
        """POST /white-label/checkpoint with 1 point — stays in foundation, progressed=False."""
        r = client.post(
            "/white-label/checkpoint",
            headers=H,
            json={"action": "manual_checkpoint", "points": 1, "note": "small test"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["progressed"] is False
        assert data["credits_awarded"] == 0
        assert "event" in data
        assert data["event"]["from_stage"] == "foundation"

    def test_set_brand_kit(self, client: TestClient) -> None:
        """POST /white-label/brand-kit — sets brand signals (has_brand_name+20, has_logo+10)."""
        r = client.post(
            "/white-label/brand-kit",
            headers=H,
            json={
                "brand_name": "Acme Corp",
                "primary_color": "#FF5733",
                "accent_color": "#33FF57",
                "logo_url": "https://acme.example.com/logo.png",
                "support_email": "support@acme.example.com",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["profile"]["brand_name"] == "Acme Corp"
        assert data["profile"]["logo_url"] == "https://acme.example.com/logo.png"

    def test_set_domain(self, client: TestClient) -> None:
        """POST /white-label/domain — sets has_custom_domain+20, ssl_enabled+10."""
        r = client.post(
            "/white-label/domain",
            headers=H,
            json={"custom_domain": "acme.example.com", "ssl_enabled": True},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "acme.example.com" in data["profile"]["custom_domain"]
        assert data["profile"]["ssl_enabled"] is True

    def test_checkpoint_with_progression(self, client: TestClient) -> None:
        """POST /white-label/checkpoint with 29 more points — total manual=30.
        Signals now: has_brand_name(20)+has_logo(10)+has_custom_domain(20)+ssl(10)=60.
        Score = 60+30 = 90 → agency_grade (>=85). Progressed from foundation → True.
        Credits awarded = 45."""
        r = client.post(
            "/white-label/checkpoint",
            headers=H,
            json={"action": "stage_advance_test", "points": 29, "note": "advance stage"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["progressed"] is True
        assert data["credits_awarded"] == 45
        assert data["event"]["from_stage"] == "foundation"
        assert data["event"]["to_stage"] == "agency_grade"
        assert data["profile"]["white_label_score"] >= 85

    def test_get_timeline(self, client: TestClient) -> None:
        """GET /white-label/timeline — should contain 2 events (from both checkpoints)."""
        r = client.get("/white-label/timeline", headers=H)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["tenant_id"] == TENANT
        assert data["count"] >= 2
        assert isinstance(data["timeline"], list)
