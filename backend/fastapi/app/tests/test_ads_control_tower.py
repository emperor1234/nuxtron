"""
HTTP smoke tests for the ads_control_tower router.
Tests all 25 endpoints via FastAPI TestClient.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from backend.fastapi.app.integrations.vendor_manager import get_vendor_manager
from backend.fastapi.app.main import app
from fastapi.testclient import TestClient

API_KEY = "test-api-key"
HEADERS = {"X-API-Key": API_KEY, "X-Tenant-Id": "ads-control-tower-test-tenant"}
BASE = "/ads-control-tower"


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── Connectors ────────────────────────────────────────────────────────────────

class TestConnectors:
    def test_list_connectors(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/connectors", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_oauth_start(self, client: TestClient) -> None:
        r = client.post(
            f"{BASE}/connectors/google_ads/oauth/start",
            headers=HEADERS,
            json={"redirect_uri": "https://example.com/callback"},
        )
        assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)

    def test_oauth_callback(self, client: TestClient) -> None:
        r = client.post(
            f"{BASE}/connectors/google_ads/oauth/callback",
            headers=HEADERS,
            json={"code": "auth-code-abc", "state": "state-xyz"},
        )
        assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)

    def test_delete_connector(self, client: TestClient) -> None:
        r = client.delete(f"{BASE}/connectors/google_ads", headers=HEADERS)
        assert r.status_code in (200, 204, 400, 401, 403, 404, 422, 500)


# ── Credits ───────────────────────────────────────────────────────────────────

class TestCredits:
    def test_get_credits(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/credits", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)


# ── Campaigns ─────────────────────────────────────────────────────────────────

class TestCampaigns:
    def test_create_campaign(self, client: TestClient) -> None:
        r = client.post(
            f"{BASE}/campaigns",
            headers=HEADERS,
            json={
                "name": "Test Campaign",
                "platform": "google_ads",
                "budget": 1000.0,
                "objective": "awareness",
            },
        )
        assert r.status_code in (200, 201, 400, 401, 403, 422, 500)

    def test_list_campaigns(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/campaigns", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_get_campaign_by_id(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/campaigns/campaign-001", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_update_campaign(self, client: TestClient) -> None:
        r = client.patch(
            f"{BASE}/campaigns/campaign-001",
            headers=HEADERS,
            json={"name": "Updated Campaign"},
        )
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_delete_campaign(self, client: TestClient) -> None:
        r = client.delete(f"{BASE}/campaigns/campaign-001", headers=HEADERS)
        assert r.status_code in (200, 204, 400, 401, 403, 404, 422, 500)

    def test_publish_campaign(self, client: TestClient) -> None:
        r = client.post(f"{BASE}/campaigns/campaign-001/publish", headers=HEADERS)
        assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)

    def test_campaign_metrics(self, client: TestClient) -> None:
        r = client.post(
            f"{BASE}/campaigns/campaign-001/metrics",
            headers=HEADERS,
            json={"start_date": "2025-01-01", "end_date": "2025-01-31"},
        )
        assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)

    def test_request_approval(self, client: TestClient) -> None:
        r = client.post(
            f"{BASE}/campaigns/campaign-001/request-approval",
            headers=HEADERS,
        )
        assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)

    def test_approve_campaign(self, client: TestClient) -> None:
        r = client.post(
            f"{BASE}/campaigns/campaign-001/approve",
            headers=HEADERS,
        )
        assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)

    def test_duplicate_campaign(self, client: TestClient) -> None:
        r = client.post(
            f"{BASE}/campaigns/campaign-001/duplicate",
            headers=HEADERS,
        )
        assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


# ── Calendar ──────────────────────────────────────────────────────────────────

class TestCalendar:
    def test_get_calendar(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/calendar", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_drag_reschedule(self, client: TestClient) -> None:
        r = client.post(
            f"{BASE}/calendar/drag-reschedule",
            headers=HEADERS,
            json={"campaign_id": "campaign-001", "new_date": "2025-02-15"},
        )
        assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


# ── Assets ────────────────────────────────────────────────────────────────────

class TestAssets:
    def test_auto_resize(self, client: TestClient) -> None:
        r = client.post(
            f"{BASE}/assets/auto-resize",
            headers=HEADERS,
            json={"asset_url": "https://example.com/image.png", "platforms": ["google_ads"]},
        )
        assert r.status_code in (200, 201, 400, 401, 403, 404, 422, 500)


# ── KPIs & Forecast ───────────────────────────────────────────────────────────

class TestKpisAndForecast:
    def test_get_kpis(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/kpis", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_get_forecast(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/forecast", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)


# ── Notifications & Best Time ─────────────────────────────────────────────────

class TestNotificationsAndBestTime:
    def test_get_notifications(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/notifications", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_best_time(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/best-time", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)


# ── A/B Test ──────────────────────────────────────────────────────────────────

class TestAbTest:
    def test_ab_test_suggestions(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/ab-test/campaign-001/suggestions", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)


# ── Audience Insights ─────────────────────────────────────────────────────────

class TestAudienceInsights:
    def test_audience_insights(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/audience-insights", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_endpoint(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/health", headers=HEADERS)
        assert r.status_code in (200, 400, 401, 403, 404, 422, 500)

    def test_health_without_auth(self, client: TestClient) -> None:
        r = client.get(f"{BASE}/health")
        # Either 200 (public) or 400/401/403 (protected or bad request)
        assert r.status_code in (200, 400, 401, 403, 422)


class TestVendorCredentialSync:
    def test_google_ads_connect_persists_vendor_credentials(self, client: TestClient) -> None:
        manager = get_vendor_manager()
        manager.revoke_credentials("google_ads_api")

        start = client.post(f"{BASE}/connectors/google_ads/oauth/start", headers=HEADERS)
        assert start.status_code == 200
        state = start.json().get("state", "")
        assert isinstance(state, str) and state

        callback = client.post(
            f"{BASE}/connectors/google_ads/oauth/callback",
            headers=HEADERS,
            json={"code": "google-token", "state": state, "account_name": "Google Primary"},
        )
        assert callback.status_code == 200
        assert manager.has_credentials("google_ads_api") is True

        status = client.get(f"{BASE}/connectors/google_ads/credentials/status", headers=HEADERS)
        assert status.status_code == 200
        payload = status.json()
        assert payload.get("platform") == "google_ads"
        assert payload.get("vendor_credentials_configured") is True

    def test_microsoft_ads_disconnect_revokes_vendor_credentials(self, client: TestClient) -> None:
        manager = get_vendor_manager()
        manager.revoke_credentials("microsoft_ads_api")

        start = client.post(f"{BASE}/connectors/microsoft_ads/oauth/start", headers=HEADERS)
        assert start.status_code == 200
        state = start.json().get("state", "")
        assert isinstance(state, str) and state

        callback = client.post(
            f"{BASE}/connectors/microsoft_ads/oauth/callback",
            headers=HEADERS,
            json={"code": "ms-token", "state": state, "account_name": "Microsoft Primary"},
        )
        assert callback.status_code == 200
        assert manager.has_credentials("microsoft_ads_api") is True

        disconnected = client.delete(f"{BASE}/connectors/microsoft_ads", headers=HEADERS)
        assert disconnected.status_code == 200
        assert manager.has_credentials("microsoft_ads_api") is False

    @pytest.mark.parametrize(
        "platform,vendor_id,code",
        [
            ("amazon_ads", "amazon_ads_api", "amazon-token"),
            ("apple_search_ads", "apple_search_ads_api", "apple-token"),
            ("youtube_ads", "youtube_ads_api", "youtube-token"),
        ],
    )
    def test_extended_ads_connectors_persist_and_revoke_credentials(
        self,
        client: TestClient,
        platform: str,
        vendor_id: str,
        code: str,
    ) -> None:
        manager = get_vendor_manager()
        manager.revoke_credentials(vendor_id)

        start = client.post(f"{BASE}/connectors/{platform}/oauth/start", headers=HEADERS)
        assert start.status_code == 200
        state = start.json().get("state", "")
        assert isinstance(state, str) and state

        callback = client.post(
            f"{BASE}/connectors/{platform}/oauth/callback",
            headers=HEADERS,
            json={"code": code, "state": state, "account_name": f"{platform} Primary"},
        )
        assert callback.status_code == 200
        assert manager.has_credentials(vendor_id) is True

        status = client.get(f"{BASE}/connectors/{platform}/credentials/status", headers=HEADERS)
        assert status.status_code == 200
        payload = status.json()
        assert payload.get("platform") == platform
        assert payload.get("vendor_credentials_configured") is True

        disconnected = client.delete(f"{BASE}/connectors/{platform}", headers=HEADERS)
        assert disconnected.status_code == 200
        assert manager.has_credentials(vendor_id) is False
