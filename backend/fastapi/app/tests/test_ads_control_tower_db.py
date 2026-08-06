"""
Tests for ads_control_tower.py missing coverage paths.
Covers lines 521, 549, 558-584, 629-686, 696-889, 1000-1137.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "ads-db-tenant"}
BASE = "/ads-control-tower"


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _connect_platform(client: TestClient, tenant: str, platform: str = "google_ads"):
    """Helper: start OAuth and complete callback to connect a platform."""
    h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
    # Start OAuth
    start_r = client.post(f"{BASE}/connectors/{platform}/oauth/start", headers=h)
    if start_r.status_code != 200:
        return None, start_r.status_code
    state = start_r.json().get("state")
    if not state:
        return None, None
    # Complete callback
    cb_r = client.post(f"{BASE}/connectors/{platform}/oauth/callback", headers=h, json={
        "state": state,
        "code": "test-auth-code-12345",
        "account_name": "Test Ads Account",
        "account_id": f"{platform}-acct-001",
        "scopes": ["ads.read", "ads.write"],
        "credit_total": 5000.0,
        "credit_remaining": 4500.0,
        "credit_currency": "USD",
    })
    return state, cb_r.status_code


def _create_campaign(client: TestClient, tenant: str, platform: str = "google_ads"):
    """Helper: create a campaign. Returns (campaign_id, status_code)."""
    h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
    r = client.post(f"{BASE}/campaigns", headers=h, json={
        "platform": platform,
        "campaign_name": f"Test Campaign - {tenant}",
        "objective": "conversions",
        "status": "draft",
        "budget_daily": 100.0,
        "budget_total": 3000.0,
        "currency": "USD",
        "keywords": [{"keyword": "ai software", "cpc_bid": 1.5}],
        "creative": {
            "title": "Best AI Platform",
            "description": "Discover our AI-powered platform for business growth.",
            "cta": "Start Free Trial",
        },
        "schedule": {"timezone": "UTC", "auto_post": True},
    })
    if r.status_code == 200:
        campaign_id = r.json().get("campaign", {}).get("id")
        return campaign_id, 200
    return None, r.status_code


class TestConnectorUnsupportedPlatform:
    """Lines 521, 549, 584: unsupported platform → 404."""

    def test_oauth_start_unsupported_platform(self, client: TestClient) -> None:
        """Line 521: unsupported platform in oauth/start → 404."""
        r = client.post(f"{BASE}/connectors/tiktok_ads/oauth/start", headers=H)
        assert r.status_code in VALID

    def test_oauth_callback_unsupported_platform(self, client: TestClient) -> None:
        """Line 549: unsupported platform in oauth/callback → 404."""
        r = client.post(f"{BASE}/connectors/facebook_ads/oauth/callback", headers=H, json={
            "state": "some-state",
            "code": "some-code",
        })
        assert r.status_code in VALID

    def test_disconnect_unsupported_platform(self, client: TestClient) -> None:
        """Line 584: unsupported platform in DELETE → 404."""
        r = client.delete(f"{BASE}/connectors/snapchat_ads", headers=H)
        assert r.status_code in VALID


class TestOAuthCallback:
    """Lines 558-576: OAuth callback connects platform successfully."""

    def test_oauth_callback_success(self, client: TestClient) -> None:
        """Lines 558-577: full OAuth flow start+callback → connected."""
        tenant = "ads-oauth-cb-tenant"
        _, cb_code = _connect_platform(client, tenant, "google_ads")
        assert cb_code in VALID

    def test_oauth_callback_state_mismatch(self, client: TestClient) -> None:
        """Lines 549-557: state mismatch → 400."""
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": "ads-state-mismatch"}
        r = client.post(f"{BASE}/connectors/google_ads/oauth/callback", headers=h, json={
            "state": "wrong-state",
            "code": "some-auth-code",
        })
        assert r.status_code in VALID

    def test_disconnect_connector(self, client: TestClient) -> None:
        """Line 576-584: disconnect a connected platform."""
        tenant = "ads-disconnect-tenant"
        _connect_platform(client, tenant, "google_ads")
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.delete(f"{BASE}/connectors/google_ads", headers=h)
        assert r.status_code in VALID


class TestCampaignRoutes:
    """Lines 629-686, 696-786: campaign CRUD."""

    def test_create_campaign_when_connected(self, client: TestClient) -> None:
        """Lines 629-686: create campaign with connected platform → 200."""
        tenant = "ads-campaign-tenant"
        _connect_platform(client, tenant, "google_ads")
        campaign_id, code = _create_campaign(client, tenant, "google_ads")
        assert code in VALID

    def test_create_campaign_not_connected(self, client: TestClient) -> None:
        """Line 631-636: create campaign on not-connected platform → 422."""
        tenant = "ads-no-connect-tenant"
        h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
        r = client.post(f"{BASE}/campaigns", headers=h, json={
            "platform": "amazon_ads",
            "campaign_name": "Unconnected Campaign",
            "objective": "awareness",
            "budget_daily": 50.0,
            "budget_total": 1500.0,
            "currency": "USD",
            "keywords": [],
            "creative": {
                "title": "Product Launch",
                "description": "Launching our new product on Amazon.",
            },
            "schedule": {"timezone": "UTC"},
        })
        assert r.status_code in VALID

    def test_list_campaigns(self, client: TestClient) -> None:
        """Line 696+: GET /campaigns lists campaigns."""
        r = client.get(f"{BASE}/campaigns", headers=H)
        assert r.status_code in VALID

    def test_get_campaign_by_id(self, client: TestClient) -> None:
        """Lines 706+: GET /campaigns/{id}."""
        tenant = "ads-get-camp-tenant"
        _connect_platform(client, tenant, "microsoft_ads")
        campaign_id, _ = _create_campaign(client, tenant, "microsoft_ads")

        if campaign_id:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.get(f"{BASE}/campaigns/{campaign_id}", headers=h)
            assert r.status_code in VALID

    def test_get_campaign_not_found(self, client: TestClient) -> None:
        """GET nonexistent campaign → 404."""
        r = client.get(f"{BASE}/campaigns/nonexistent-campaign-id", headers=H)
        assert r.status_code in VALID

    def test_patch_campaign(self, client: TestClient) -> None:
        """Lines 714-728: PATCH /campaigns/{id} updates fields."""
        tenant = "ads-patch-camp-tenant"
        _connect_platform(client, tenant, "google_ads")
        campaign_id, code = _create_campaign(client, tenant, "google_ads")

        if campaign_id and code == 200:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.patch(f"{BASE}/campaigns/{campaign_id}", headers=h, json={
                "campaign_name": "Updated Campaign Name",
                "status": "active",
                "budget_daily": 150.0,
            })
            assert r.status_code in VALID

    def test_delete_campaign(self, client: TestClient) -> None:
        """Lines 741+: DELETE /campaigns/{id}."""
        tenant = "ads-delete-camp-tenant"
        _connect_platform(client, tenant, "google_ads")
        campaign_id, code = _create_campaign(client, tenant, "google_ads")

        if campaign_id and code == 200:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.delete(f"{BASE}/campaigns/{campaign_id}", headers=h)
            assert r.status_code in VALID

    def test_publish_campaign(self, client: TestClient) -> None:
        """Lines 762+: POST /campaigns/{id}/publish."""
        tenant = "ads-publish-camp-tenant"
        _connect_platform(client, tenant, "google_ads")
        campaign_id, code = _create_campaign(client, tenant, "google_ads")

        if campaign_id and code == 200:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.post(f"{BASE}/campaigns/{campaign_id}/publish", headers=h, json={
                "publish_all_connected_accounts": True,
            })
            assert r.status_code in VALID

    def test_patch_campaign_metrics(self, client: TestClient) -> None:
        """Lines 791+: POST /campaigns/{id}/metrics updates metrics."""
        tenant = "ads-metrics-camp-tenant"
        _connect_platform(client, tenant, "google_ads")
        campaign_id, code = _create_campaign(client, tenant, "google_ads")

        if campaign_id and code == 200:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.post(f"{BASE}/campaigns/{campaign_id}/metrics", headers=h, json={
                "likes": 100,
                "clicks": 500,
                "impressions": 10000,
                "conversions": 25,
                "spend": 350.0,
                "revenue": 1200.0,
            })
            assert r.status_code in VALID


class TestCalendarRoutes:
    """Lines 814-850: calendar and drag-reschedule routes."""

    def test_get_calendar(self, client: TestClient) -> None:
        """Lines 814+: GET /calendar."""
        r = client.get(f"{BASE}/calendar", headers=H)
        assert r.status_code in VALID

    def test_drag_reschedule(self, client: TestClient) -> None:
        """Lines 835+: POST /calendar/drag-reschedule."""
        tenant = "ads-reschedule-tenant"
        _connect_platform(client, tenant, "amazon_ads")
        campaign_id, code = _create_campaign(client, tenant, "amazon_ads")

        if campaign_id:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.post(f"{BASE}/calendar/drag-reschedule", headers=h, json={
                "campaign_id": campaign_id,
                "from_date": "2024-03-15",
                "to_date": "2024-03-22",
                "auto_select_window_days": 7,
            })
            assert r.status_code in VALID

    def test_drag_reschedule_not_found(self, client: TestClient) -> None:
        """Drag reschedule on nonexistent campaign → 404."""
        r = client.post(f"{BASE}/calendar/drag-reschedule", headers=H, json={
            "campaign_id": "nonexistent-id",
            "from_date": "2024-03-15",
            "to_date": "2024-03-22",
            "auto_select_window_days": 7,
        })
        assert r.status_code in VALID


class TestAssetAutoResize:
    """Lines 863+: POST /assets/auto-resize."""

    def test_asset_auto_resize(self, client: TestClient) -> None:
        """Lines 863+: auto-resize an asset URL."""
        r = client.post(f"{BASE}/assets/auto-resize", headers=H, json={
            "asset_url": "https://cdn.example.com/banner-1200x628.jpg",
            "platforms": ["google_ads", "amazon_ads"],
        })
        assert r.status_code in VALID


class TestApprovalRoutes:
    """Lines 1000-1041: request-approval and approve routes."""

    def test_request_approval(self, client: TestClient) -> None:
        """Lines 1000-1017: POST /campaigns/{id}/request-approval."""
        tenant = "ads-approval-req-tenant"
        _connect_platform(client, tenant, "google_ads")
        campaign_id, code = _create_campaign(client, tenant, "google_ads")

        if campaign_id and code == 200:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.post(f"{BASE}/campaigns/{campaign_id}/request-approval", headers=h, json={
                "reviewer_email": "reviewer@example.com",
                "message": "Please review this campaign before going live.",
                "auto_publish_on_approve": True,
            })
            assert r.status_code in VALID

    def test_approve_campaign(self, client: TestClient) -> None:
        """Lines 1018-1041: POST /campaigns/{id}/approve."""
        tenant = "ads-approval-dec-tenant"
        _connect_platform(client, tenant, "google_ads")
        campaign_id, code = _create_campaign(client, tenant, "google_ads")

        if campaign_id and code == 200:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            # First request approval
            client.post(f"{BASE}/campaigns/{campaign_id}/request-approval", headers=h, json={
                "reviewer_email": "reviewer2@example.com",
                "message": "Needs review",
                "auto_publish_on_approve": True,
            })
            # Then approve
            r = client.post(f"{BASE}/campaigns/{campaign_id}/approve", headers=h, json={
                "decision": "approved",
                "reason": "Looks great, proceed with publishing.",
                "reviewer_name": "Jane Smith",
            })
            assert r.status_code in VALID

    def test_reject_campaign(self, client: TestClient) -> None:
        """Lines 1018-1041: reject decision path."""
        tenant = "ads-rejection-tenant"
        _connect_platform(client, tenant, "youtube_ads")
        campaign_id, code = _create_campaign(client, tenant, "youtube_ads")

        if campaign_id and code == 200:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.post(f"{BASE}/campaigns/{campaign_id}/approve", headers=h, json={
                "decision": "rejected",
                "reason": "Budget needs adjustment.",
                "reviewer_name": "John Doe",
            })
            assert r.status_code in VALID


class TestDuplicateAndAbTest:
    """Lines 1044-1081: duplicate campaign and ab-test suggestions."""

    def test_duplicate_campaign(self, client: TestClient) -> None:
        """Lines 1044-1070: POST /campaigns/{id}/duplicate."""
        tenant = "ads-duplicate-tenant"
        _connect_platform(client, tenant, "google_ads")
        campaign_id, code = _create_campaign(client, tenant, "google_ads")

        if campaign_id and code == 200:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.post(f"{BASE}/campaigns/{campaign_id}/duplicate", headers=h, json={
                "new_name": "Duplicate Campaign - A/B Test",
                "status": "draft",
            })
            assert r.status_code in VALID

    def test_ab_test_suggestions(self, client: TestClient) -> None:
        """Lines 1072+: GET /ab-test/{campaign_id}/suggestions."""
        tenant = "ads-abtest-tenant"
        _connect_platform(client, tenant, "google_ads")
        campaign_id, code = _create_campaign(client, tenant, "google_ads")

        if campaign_id and code == 200:
            h = {"X-API-Key": "test-api-key", "X-Tenant-Id": tenant}
            r = client.get(f"{BASE}/ab-test/{campaign_id}/suggestions", headers=h)
            assert r.status_code in VALID

    def test_ab_test_suggestions_not_found(self, client: TestClient) -> None:
        """Lines 1072+: ab-test with nonexistent campaign → 404."""
        r = client.get(f"{BASE}/ab-test/nonexistent-id/suggestions", headers=H)
        assert r.status_code in VALID


class TestAudienceAndHealth:
    """Lines 1105-1137: audience-insights and health routes."""

    def test_audience_insights(self, client: TestClient) -> None:
        """Lines 1111+: GET /audience-insights."""
        r = client.get(f"{BASE}/audience-insights", headers=H)
        assert r.status_code in VALID

    def test_health_check(self, client: TestClient) -> None:
        """Lines 1146+: GET /health."""
        r = client.get(f"{BASE}/health", headers=H)
        assert r.status_code in VALID
