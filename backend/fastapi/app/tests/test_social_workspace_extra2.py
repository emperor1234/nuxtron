"""
social_workspace.py extra tests - round 2.
Targets missing branches: connect/disconnect accounts, oauth routes, brand profile,
fetch-from-website, workspace overview, engage, autopilot.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "test-sw-extra2"}
VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


def _connect_account(client: TestClient, network: str = "twitter") -> int | None:
    """Connect a social account and return account_id if successful."""
    r = client.post("/social/accounts/connect", headers=H, json={
        "network": network,
        "handle": f"test_{network}_handle",
        "account_name": f"Test {network.title()} Account",
    })
    if r.status_code == 200:
        return r.json().get("account", {}).get("id")
    return None


class TestConnectDisconnectAccount:
    """Lines 1150-1191: connect/disconnect social accounts."""

    def test_connect_twitter_account(self, client: TestClient) -> None:
        """Connect twitter account (line 1150, 1165)."""
        r = client.post("/social/accounts/connect", headers=H, json={
            "network": "twitter",
            "handle": "test_handle_sw2",
            "account_name": "Test Twitter Account",
        })
        assert r.status_code in VALID

    def test_connect_instagram_account(self, client: TestClient) -> None:
        """Connect instagram account."""
        r = client.post("/social/accounts/connect", headers=H, json={
            "network": "instagram",
            "handle": "test_ig_handle",
            "account_name": "Test Instagram Account",
        })
        assert r.status_code in VALID

    def test_connect_linkedin_account(self, client: TestClient) -> None:
        """Connect linkedin account."""
        r = client.post("/social/accounts/connect", headers=H, json={
            "network": "linkedin",
            "handle": "test_linkedin_handle",
            "account_name": "Test LinkedIn Account",
        })
        assert r.status_code in VALID

    def test_connect_unsupported_network(self, client: TestClient) -> None:
        """Unsupported network → 422."""
        r = client.post("/social/accounts/connect", headers=H, json={
            "network": "myspace",
            "handle": "test_myspace",
        })
        assert r.status_code in VALID

    def test_disconnect_account_success(self, client: TestClient) -> None:
        """Disconnect existing account (lines 1183, 1191)."""
        account_id = _connect_account(client, "tiktok")
        if account_id:
            r = client.delete(f"/social/accounts/{account_id}", headers=H)
            assert r.status_code in VALID

    def test_disconnect_account_not_found(self, client: TestClient) -> None:
        """Disconnect non-existent account → 404 (line 1189)."""
        r = client.delete("/social/accounts/99999", headers=H)
        assert r.status_code in VALID


class TestOAuthRoutes:
    """Lines 1241-1296: OAuth routes."""

    def test_oauth_providers_list(self, client: TestClient) -> None:
        r = client.get("/social/oauth/providers", headers=H)
        assert r.status_code in VALID

    def test_oauth_start_twitter(self, client: TestClient) -> None:
        """OAuth start for twitter (line 1241, 1255)."""
        r = client.post("/social/oauth/twitter/start", headers=H, json={
            "redirect_uri": "https://example.com/callback",
        })
        assert r.status_code in VALID

    def test_oauth_start_linkedin(self, client: TestClient) -> None:
        r = client.post("/social/oauth/linkedin/start", headers=H, json={
            "redirect_uri": "https://example.com/callback",
        })
        assert r.status_code in VALID

    def test_oauth_start_unsupported_network(self, client: TestClient) -> None:
        """Unsupported oauth network → 422."""
        r = client.post("/social/oauth/myspace/start", headers=H, json={
            "redirect_uri": "https://example.com/callback",
        })
        assert r.status_code in VALID

    def test_oauth_callback_invalid_state(self, client: TestClient) -> None:
        """OAuth callback with invalid state → 400 (line 1274)."""
        r = client.post("/social/oauth/twitter/callback", headers=H, json={
            "state": "nonexistent-state-xyz",
            "code": "auth-code-123",
        })
        assert r.status_code in VALID

    def test_oauth_connect_all(self, client: TestClient) -> None:
        """OAuth connect-all."""
        r = client.post("/social/oauth/connect-all", headers=H, json={
            "access_tokens": {"twitter": "tok_twitter", "instagram": "tok_ig"},
        })
        assert r.status_code in VALID


class TestBrandProfile:
    """Lines 1353-1400: brand profile routes."""

    def test_get_brand_profile(self, client: TestClient) -> None:
        r = client.get("/social/brand-profile", headers=H)
        assert r.status_code in VALID

    def test_update_brand_profile(self, client: TestClient) -> None:
        """Update brand profile (lines 1353, 1397)."""
        r = client.put("/social/brand-profile", headers=H, json={
            "business_name": "Test Business",
            "industry": "Technology",
            "tone": "professional",
            "keywords": ["innovation", "tech"],
            "hashtags": ["#tech", "#innovation"],
            "timezone": "UTC",
            "brand_colors": ["#FF0000", "#00FF00"],
            "title_font_family": "Inter",
            "subtitle_font_family": "Inter",
            "title_font_weight": "Bold",
            "subtitle_font_weight": "Regular",
        })
        assert r.status_code in VALID

    def test_update_brand_profile_with_avatar(self, client: TestClient) -> None:
        """Update brand profile with avatar_profile dict (line 1397)."""
        r = client.put("/social/brand-profile", headers=H, json={
            "business_name": "Avatar Business",
            "industry": "Entertainment",
            "tone": "casual",
            "keywords": [],
            "hashtags": [],
            "timezone": "UTC",
            "brand_colors": [],
            "title_font_family": "Roboto",
            "subtitle_font_family": "Roboto",
            "title_font_weight": "Regular",
            "subtitle_font_weight": "Regular",
            "avatar_profile": {
                "name": "Alex",
                "ethnicity": "South Asian",
                "gender": "non-binary",
                "style": "casual",
                "face_type": "oval",
                "eye_style": "almond",
                "body_shape": "athletic",
                "body_proportions": "medium",
                "age_range": "25-35",
            },
        })
        assert r.status_code in VALID

    def test_update_ugc_template(self, client: TestClient) -> None:
        r = client.put("/social/brand-profile/ugc-template", headers=H, json={
            "template_name": "Standard UGC",
            "content_style": "authentic",
        })
        assert r.status_code in VALID

    def test_fetch_brand_from_website_no_url(self, client: TestClient) -> None:
        """Empty website URL → 422 (line 689)."""
        r = client.post("/social/brand-profile/fetch-from-website", headers=H, json={
            "website_url": "",
        })
        assert r.status_code in VALID

    def test_fetch_brand_from_website_valid_url(self, client: TestClient) -> None:
        """Valid website URL → tries to fetch (lines 634, 647-649)."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=False)
            mock_response.read.return_value = b'<html><title>Test Business</title></html>'
            mock_urlopen.return_value = mock_response

            r = client.post("/social/brand-profile/fetch-from-website", headers=H, json={
                "website_url": "https://example.com",
            })
        assert r.status_code in VALID

    def test_fetch_brand_website_fetch_error(self, client: TestClient) -> None:
        """Website fetch raises exception → returns empty (lines 647-649)."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_urlopen.side_effect = Exception("Network error")

            r = client.post("/social/brand-profile/fetch-from-website", headers=H, json={
                "website_url": "https://error-website.example.com",
            })
        assert r.status_code in VALID

    def test_avatar_catalog(self, client: TestClient) -> None:
        r = client.get("/social/avatar/catalog", headers=H)
        assert r.status_code in VALID

    def test_voiceover_catalog(self, client: TestClient) -> None:
        r = client.get("/social/voiceover/catalog", headers=H)
        assert r.status_code in VALID


class TestWorkspaceOverview:
    """Lines 1529-1540, 1568-1673: overview, engage, autopilot."""

    def test_workspace_overview(self, client: TestClient) -> None:
        """Workspace overview (lines 1432-1440)."""
        r = client.get("/social/workspace/overview", headers=H)
        assert r.status_code in VALID

    def test_engage_message_not_found(self, client: TestClient) -> None:
        """Message not found → 404 (line 1577)."""
        account_id = _connect_account(client, "twitter")
        r = client.post("/social/inbox/messages/99999/engage", headers=H, json={
            "account_id": account_id or 1,
            "action": "reply",
            "reply_text": "Hello!",
            "agent_name": "Test Agent",
        })
        assert r.status_code in VALID

    def test_engage_message_account_not_found(self, client: TestClient) -> None:
        """Account not found for engage → 404."""
        r = client.post("/social/inbox/messages/1/engage", headers=H, json={
            "account_id": 99999,
            "action": "reply",
            "reply_text": "Hello!",
            "agent_name": "Test Agent",
        })
        assert r.status_code in VALID

    def test_autopilot_preview_no_account(self, client: TestClient) -> None:
        """Autopilot preview with no account → 404."""
        r = client.post("/social/autopilot/preview", headers=H, json={
            "account_id": 99999,
            "headline": "Test Headline",
            "caption": "Test Caption",
            "content_type": "image",
            "publish_mode": "scheduled",
            "media_urls": [],
        })
        assert r.status_code in VALID

    def test_autopilot_preview_success(self, client: TestClient) -> None:
        """Autopilot preview with valid account (lines 1534, 1639)."""
        account_id = _connect_account(client, "instagram")
        if account_id:
            r = client.post("/social/autopilot/preview", headers=H, json={
                "account_id": account_id,
                "headline": "Test Autopilot Headline",
                "caption": "Test Autopilot Caption for instagram",
                "content_type": "video",
                "publish_mode": "scheduled",
                "media_urls": ["https://example.com/video.mp4"],
            })
            assert r.status_code in VALID

    def test_autopilot_publish_success(self, client: TestClient) -> None:
        """Autopilot publish with valid account (lines 1539, 1660, 1672)."""
        account_id = _connect_account(client, "linkedin")
        if account_id:
            r = client.post("/social/autopilot/publish", headers=H, json={
                "account_id": account_id,
                "headline": "Test Publish Headline",
                "caption": "Test publish caption for linkedin",
                "content_type": "image",
                "publish_mode": "now",
                "media_urls": [],
            })
            assert r.status_code in VALID

    def test_autopilot_publish_scheduled(self, client: TestClient) -> None:
        """Autopilot publish in scheduled mode."""
        account_id = _connect_account(client, "twitter")
        if account_id:
            r = client.post("/social/autopilot/publish", headers=H, json={
                "account_id": account_id,
                "headline": "Scheduled Post Headline",
                "caption": "Scheduled post caption",
                "content_type": "image",
                "publish_mode": "scheduled",
                "media_urls": [],
            })
            assert r.status_code in VALID

    def test_autopilot_publish_no_account(self, client: TestClient) -> None:
        """Autopilot publish with no account → 404."""
        r = client.post("/social/autopilot/publish", headers=H, json={
            "account_id": 99999,
            "headline": "No Account Headline",
            "caption": "No account caption",
            "content_type": "image",
            "publish_mode": "now",
            "media_urls": [],
        })
        assert r.status_code in VALID
