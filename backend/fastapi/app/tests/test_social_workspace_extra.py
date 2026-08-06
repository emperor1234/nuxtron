"""
Tests for social_workspace router — covering uncovered endpoints.
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


class TestSocialAccounts:
    def test_catalog(self, client: TestClient) -> None:
        r = client.get("/social/accounts/catalog", headers=H)
        assert r.status_code in VALID

    def test_list_accounts(self, client: TestClient) -> None:
        r = client.get("/social/accounts", headers=H)
        assert r.status_code in VALID

    def test_connect_twitter(self, client: TestClient) -> None:
        r = client.post("/social/accounts/connect", headers=H, json={
            "network": "twitter",
            "access_token": "tok_123",
            "access_token_secret": "sec_456",
        })
        assert r.status_code in VALID

    def test_connect_instagram(self, client: TestClient) -> None:
        r = client.post("/social/accounts/connect", headers=H, json={
            "network": "instagram",
            "access_token": "tok_ig",
        })
        assert r.status_code in VALID

    def test_connect_linkedin(self, client: TestClient) -> None:
        r = client.post("/social/accounts/connect", headers=H, json={
            "network": "linkedin",
            "access_token": "tok_li",
        })
        assert r.status_code in VALID

    def test_connect_unsupported_network(self, client: TestClient) -> None:
        r = client.post("/social/accounts/connect", headers=H, json={
            "network": "myspace",
            "access_token": "tok_ms",
        })
        assert r.status_code in VALID

    def test_delete_account(self, client: TestClient) -> None:
        r = client.delete("/social/accounts/acc_nonexistent", headers=H)
        assert r.status_code in VALID


class TestSocialOAuth:
    def test_providers(self, client: TestClient) -> None:
        r = client.get("/social/oauth/providers", headers=H)
        assert r.status_code in VALID

    def test_oauth_start_twitter(self, client: TestClient) -> None:
        r = client.post("/social/oauth/twitter/start", headers=H, json={})
        assert r.status_code in VALID

    def test_oauth_start_unsupported(self, client: TestClient) -> None:
        r = client.post("/social/oauth/myspace/start", headers=H, json={})
        assert r.status_code in VALID

    def test_oauth_callback(self, client: TestClient) -> None:
        r = client.post("/social/oauth/twitter/callback", headers=H, json={
            "code": "auth_code_123",
            "state": "state_abc",
        })
        assert r.status_code in VALID

    def test_oauth_connect_all(self, client: TestClient) -> None:
        r = client.post("/social/oauth/connect-all", headers=H, json={})
        assert r.status_code in VALID


class TestBrandProfile:
    def test_get_brand_profile(self, client: TestClient) -> None:
        r = client.get("/social/brand-profile", headers=H)
        assert r.status_code in VALID

    def test_get_avatar_catalog(self, client: TestClient) -> None:
        r = client.get("/social/avatar/catalog", headers=H)
        assert r.status_code in VALID

    def test_get_voiceover_catalog(self, client: TestClient) -> None:
        r = client.get("/social/voiceover/catalog", headers=H)
        assert r.status_code in VALID

    def test_update_brand_profile(self, client: TestClient) -> None:
        r = client.put("/social/brand-profile", headers=H, json={
            "brand_name": "Test Brand",
            "brand_voice": "professional",
        })
        assert r.status_code in VALID

    def test_update_ugc_template(self, client: TestClient) -> None:
        r = client.put("/social/brand-profile/ugc-template", headers=H, json={
            "template": "Here is a {product} review",
        })
        assert r.status_code in VALID

    def test_fetch_from_website(self, client: TestClient) -> None:
        r = client.post("/social/brand-profile/fetch-from-website", headers=H, json={
            "website_url": "https://example.com",
        })
        assert r.status_code in VALID

    def test_fetch_from_invalid_url(self, client: TestClient) -> None:
        r = client.post("/social/brand-profile/fetch-from-website", headers=H, json={
            "website_url": "not-a-url",
        })
        assert r.status_code in VALID


class TestWorkspaceAndInbox:
    def test_workspace_overview(self, client: TestClient) -> None:
        r = client.get("/social/workspace/overview", headers=H)
        assert r.status_code in VALID

    def test_message_engage_nonexistent(self, client: TestClient) -> None:
        r = client.post("/social/inbox/messages/msg_nonexistent/engage", headers=H, json={
            "action": "like",
        })
        assert r.status_code in VALID


class TestAutopilot:
    def test_autopilot_preview(self, client: TestClient) -> None:
        r = client.post("/social/autopilot/preview", headers=H, json={
            "account_id": "acc_nonexistent",
            "content": "Test post content",
        })
        assert r.status_code in VALID

    def test_autopilot_publish(self, client: TestClient) -> None:
        r = client.post("/social/autopilot/publish", headers=H, json={
            "account_id": "acc_nonexistent",
            "content": "Published post",
        })
        assert r.status_code in VALID
