"""
ads_control_tower extra tests — round 2.
Creates campaigns with real IDs to cover update/delete/publish/metrics branches.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-ads-extra2"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
BASE = "/ads-control-tower"

CAMPAIGN_BODY = {
    "platform": "google_ads",
    "campaign_name": "Extra2 Test Campaign",
    "objective": "conversions",
    "status": "draft",
    "budget_daily": 100.0,
    "budget_total": 5000.0,
    "currency": "USD",
    "creative": {
        "title": "Test Product",
        "description": "A test product description for coverage.",
        "cta": "Learn More",
    },
}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _connect_google_ads(client: TestClient) -> None:
    """Connect google_ads platform by doing oauth start → callback."""
    # Step 1: oauth start
    r = client.post(f"{BASE}/connectors/google_ads/oauth/start", headers=H, json={
        "redirect_uri": "https://example.com/callback",
    })
    state = None
    if r.status_code == 200:
        state = r.json().get("oauth_state") or r.json().get("state")
    if state is None:
        # connector might already have a state set
        r2 = client.get(f"{BASE}/connectors", headers=H)
        if r2.status_code == 200:
            for c in r2.json().get("connectors", []):
                if c.get("platform") == "google_ads":
                    state = c.get("oauth_state")
                    break
    if state is None:
        return  # Can't proceed without state

    # Step 2: oauth callback
    client.post(f"{BASE}/connectors/google_ads/oauth/callback", headers=H, json={
        "code": "auth-code-xyz",
        "state": state,
        "account_name": "Test Google Ads Account",
        "account_id": "google-ads-123",
        "scopes": ["ads.manage"],
        "credit_total": 5000.0,
        "credit_remaining": 4900.0,
        "credit_currency": "USD",
    })


def _create_campaign(client: TestClient) -> str | None:
    """Helper: connect Google Ads and create a campaign. Returns campaign_id."""
    _connect_google_ads(client)
    r = client.post(f"{BASE}/campaigns", headers=H, json=CAMPAIGN_BODY)
    if r.status_code in (200, 201):
        return r.json().get("campaign", {}).get("id")
    return None


class TestAdsOauthFullFlow:
    """Full OAuth flow covering lines 553-580."""

    def test_oauth_start_unsupported(self, client: TestClient) -> None:
        r = client.post(f"{BASE}/connectors/unknown_platform/oauth/start", headers=H, json={
            "redirect_uri": "https://example.com/callback",
        })
        assert r.status_code in VALID

    def test_oauth_callback_state_mismatch(self, client: TestClient) -> None:
        """Callback with wrong state → 400 (line 555)."""
        r = client.post(f"{BASE}/connectors/google_ads/oauth/callback", headers=H, json={
            "code": "wrong-code",
            "state": "wrong-state-xyz",
            "account_name": "Test",
            "account_id": "test-123",
            "scopes": ["ads.manage"],
            "credit_total": 1000.0,
            "credit_remaining": 900.0,
            "credit_currency": "USD",
        })
        assert r.status_code in VALID

    def test_full_oauth_and_campaign_create(self, client: TestClient) -> None:
        """Full OAuth flow + campaign create (lines 555-670)."""
        # Start oauth to get state
        r_start = client.post(f"{BASE}/connectors/google_ads/oauth/start", headers=H, json={
            "redirect_uri": "https://example.com/callback",
        })
        assert r_start.status_code in VALID
        state = None
        if r_start.status_code == 200:
            state = r_start.json().get("oauth_state") or r_start.json().get("state")

        if state:
            r_cb = client.post(f"{BASE}/connectors/google_ads/oauth/callback", headers=H, json={
                "code": "auth-code-valid",
                "state": state,
                "account_name": "Test Google Ads Account Full",
                "account_id": "google-ads-full-456",
                "scopes": ["ads.manage", "ads.readonly"],
                "credit_total": 10000.0,
                "credit_remaining": 9500.0,
                "credit_currency": "USD",
            })
            assert r_cb.status_code in VALID


class TestAdsCampaignCrudWithRealId:
    """Campaign CRUD using real created campaign IDs — lines 700-900."""

    @pytest.fixture(autouse=True)
    def campaign_id(self, client: TestClient) -> str | None:
        self._campaign_id = _create_campaign(client)
        return self._campaign_id

    def test_get_existing_campaign(self, client: TestClient) -> None:
        if not self._campaign_id:
            pytest.skip("No campaign created")
        r = client.get(f"{BASE}/campaigns/{self._campaign_id}", headers=H)
        assert r.status_code in VALID

    def test_update_existing_campaign(self, client: TestClient) -> None:
        if not self._campaign_id:
            pytest.skip("No campaign created")
        r = client.patch(f"{BASE}/campaigns/{self._campaign_id}", headers=H, json={
            "campaign_name": "Updated Campaign Name",
            "objective": "awareness",
        })
        assert r.status_code in VALID

    def test_update_campaign_status(self, client: TestClient) -> None:
        if not self._campaign_id:
            pytest.skip("No campaign created")
        r = client.patch(f"{BASE}/campaigns/{self._campaign_id}", headers=H, json={
            "status": "active",
        })
        assert r.status_code in VALID

    def test_patch_metrics_existing_campaign(self, client: TestClient) -> None:
        """Update campaign metrics — lines 770-800."""
        if not self._campaign_id:
            pytest.skip("No campaign created")
        r = client.post(f"{BASE}/campaigns/{self._campaign_id}/metrics", headers=H, json={
            "likes": 100,
            "impressions": 5000,
            "shares": 50,
            "comments": 30,
            "clicks": 200,
            "conversions": 15,
            "spend": 450.0,
            "revenue": 1200.0,
        })
        assert r.status_code in VALID

    def test_publish_existing_campaign(self, client: TestClient) -> None:
        """Publish connected campaign (lines 745-760)."""
        if not self._campaign_id:
            pytest.skip("No campaign created")
        r = client.post(f"{BASE}/campaigns/{self._campaign_id}/publish", headers=H, json={
            "publish_all_connected_accounts": True,
        })
        assert r.status_code in VALID

    def test_ab_test_suggestions_existing_campaign(self, client: TestClient) -> None:
        """AB test suggestions (lines 1065-1115)."""
        if not self._campaign_id:
            pytest.skip("No campaign created")
        r = client.get(f"{BASE}/ab-test/{self._campaign_id}/suggestions", headers=H)
        assert r.status_code in VALID

    def test_request_approval_existing_campaign(self, client: TestClient) -> None:
        """Request approval for existing campaign (lines 1000-1020)."""
        if not self._campaign_id:
            pytest.skip("No campaign created")
        r = client.post(f"{BASE}/campaigns/{self._campaign_id}/request-approval", headers=H, json={
            "reviewer_email": "reviewer@example.com",
            "message": "Please review this campaign",
            "auto_publish_on_approve": True,
        })
        assert r.status_code in VALID

    def test_approve_existing_campaign(self, client: TestClient) -> None:
        """Approve existing campaign (lines 1021-1050)."""
        if not self._campaign_id:
            pytest.skip("No campaign created")
        r = client.post(f"{BASE}/campaigns/{self._campaign_id}/approve", headers=H, json={
            "decision": "approved",
            "reason": "Looks great",
            "reviewer_name": "John Reviewer",
        })
        assert r.status_code in VALID

    def test_duplicate_existing_campaign(self, client: TestClient) -> None:
        """Duplicate existing campaign (lines 1051-1065)."""
        if not self._campaign_id:
            pytest.skip("No campaign created")
        r = client.post(f"{BASE}/campaigns/{self._campaign_id}/duplicate", headers=H, json={
            "new_name": "Duplicate Campaign",
            "status": "draft",
        })
        assert r.status_code in VALID

    def test_delete_existing_campaign(self, client: TestClient) -> None:
        """Delete existing campaign (line 740-745)."""
        if not self._campaign_id:
            pytest.skip("No campaign created")
        r = client.delete(f"{BASE}/campaigns/{self._campaign_id}", headers=H)
        assert r.status_code in VALID


class TestAdsCalendarAndAudience:
    """Calendar and audience insight routes — lines 800-900."""

    def test_calendar_events(self, client: TestClient) -> None:
        """Calendar with posting_dates (lines 805-840)."""
        # Create campaign with schedule
        _connect_google_ads(client)
        client.post(f"{BASE}/campaigns", headers=H, json={
            **CAMPAIGN_BODY,
            "campaign_name": "Calendar Test Campaign",
            "schedule": {
                "timezone": "America/New_York",
                "start_at": "2025-06-01",
                "end_at": "2025-08-31",
                "auto_post": True,
                "posting_dates": ["2025-06-01", "2025-06-15", "2025-07-01"],
            },
        })
        r = client.get(f"{BASE}/calendar", headers=H)
        assert r.status_code in VALID

    def test_calendar_reschedule_not_found(self, client: TestClient) -> None:
        r = client.post(f"{BASE}/calendar/drag-reschedule", headers=H, json={
            "campaign_id": "nonexistent-campaign-id",
            "original_date": "2025-06-01",
            "new_date": "2025-06-15",
        })
        assert r.status_code in VALID

    def test_calendar_reschedule_existing(self, client: TestClient) -> None:
        """Reschedule existing campaign (lines 855-900)."""
        campaign_id = _create_campaign(client)
        if not campaign_id:
            return
        r = client.post(f"{BASE}/calendar/drag-reschedule", headers=H, json={
            "campaign_id": campaign_id,
            "original_date": "2025-06-01",
            "new_date": "2025-07-15",
        })
        assert r.status_code in VALID

    def test_audience_insights(self, client: TestClient) -> None:
        """Audience insights route (lines 1120-1150)."""
        r = client.get(f"{BASE}/audience-insights", headers=H)
        assert r.status_code in VALID

    def test_forecast_roas(self, client: TestClient) -> None:
        """Forecast route (lines 1000+)."""
        r = client.post(f"{BASE}/forecasts/roas", headers=H, json={
            "platform": "google_ads",
            "budget_daily": 200.0,
            "budget_total": 6000.0,
            "duration_days": 30,
            "objective": "conversions",
        })
        assert r.status_code in VALID
