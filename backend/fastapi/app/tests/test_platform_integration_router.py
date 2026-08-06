from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "platform-integration-test-tenant"}
FUTURE_SCHEDULE_AT = (datetime.now(UTC) + timedelta(days=30)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class DummyMetrics:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, Any]:
        return self._payload


class DummyPlatformClient:
    async def close(self) -> None:
        return None

    async def create_tweet(self, request: Any) -> dict[str, Any]:
        return {"data": {"id": "tweet-1", "text": request.text}}

    async def schedule_tweet(self, request: Any) -> dict[str, Any]:
        return {"data": {"id": "tweet-scheduled", "scheduled_at": request.scheduled_at.isoformat()}}

    async def create_page_post(self, request: Any) -> dict[str, Any]:
        return {"id": "facebook-1", "message": request.message}

    async def schedule_page_post(self, request: Any) -> dict[str, Any]:
        return {"id": "facebook-scheduled", "scheduled_publish_time": request.scheduled_publish_time.isoformat()}

    async def publish_carousel(self, request: Any) -> dict[str, Any]:
        return {"id": "instagram-carousel", "media_urls": request.media_urls}

    async def publish_reel(self, request: Any) -> dict[str, Any]:
        return {"id": "instagram-reel", "video_url": request.video_url}

    async def publish_story(self, request: Any) -> dict[str, Any]:
        return {"id": "instagram-story", "media_url": request.media_url}

    async def schedule_post(self, request: Any) -> dict[str, Any]:
        # Router reuses schedule_post for both Instagram and LinkedIn clients.
        scheduled_dt = getattr(request, "scheduled_timestamp", None) or getattr(request, "scheduled_time", None)
        return {
            "id": "scheduled-1",
            "scheduled_time": scheduled_dt.isoformat() if scheduled_dt is not None else None,
        }

    async def create_post(self, request: Any) -> dict[str, Any]:
        return {"id": "linkedin-1", "text": request.text}

    async def schedule_video(self, request: Any) -> dict[str, Any]:
        return {"video_id": "tiktok-scheduled", "publish_time": request.scheduled_time.isoformat()}

    async def upload_video(self, request: Any) -> dict[str, Any]:
        return {"video_id": "tiktok-1", "video_url": request.video_url}

    async def get_tweet_metrics(self, post_id: str) -> DummyMetrics:
        return DummyMetrics({"tweet_id": post_id, "public_metrics": {"like_count": 1}})

    async def get_page_insights(self, post_id: str) -> DummyMetrics:
        return DummyMetrics({"post_id": post_id, "page_impressions": 99})

    async def get_post_insights(self, post_id: str) -> DummyMetrics:
        return DummyMetrics({"post_id": post_id, "impressions": 77})

    async def get_post_metrics(self, post_id: str) -> DummyMetrics:
        return DummyMetrics({"post_id": post_id, "likes": 12})

    async def get_video_metrics(self, post_id: str) -> DummyMetrics:
        return DummyMetrics({"video_id": post_id, "views": 321})


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> TestClient:
    monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
    monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
    monkeypatch.setenv("PLATFORM_SCHEDULE_STORE_PATH", str(tmp_path / "scheduled_posts.json"))

    from backend.fastapi.app.integrations.vendor_manager import (
        VendorCredentials,
        VendorType,
        get_vendor_manager,
    )
    from backend.fastapi.app.routers import platform_integration as platform_router

    vendor_manager = get_vendor_manager()
    vendor_manager.store_credentials(
        "twitter_api",
        VendorCredentials(
            vendor_type=VendorType.SOCIAL_MEDIA,
            platform="twitter",
            api_key="twitter-key",
            access_token="twitter-token",
            refresh_token="twitter-refresh-token",
            additional_config={},
        ),
    )
    vendor_manager.store_credentials(
        "meta_graph_api",
        VendorCredentials(
            vendor_type=VendorType.SOCIAL_MEDIA,
            platform="facebook",
            api_key="meta-key",
            access_token="meta-token",
            additional_config={"page_id": "page-1", "instagram_account_id": "ig-1"},
        ),
    )
    vendor_manager.store_credentials(
        "linkedin_api",
        VendorCredentials(
            vendor_type=VendorType.SOCIAL_MEDIA,
            platform="linkedin",
            api_key="linkedin-key",
            access_token="linkedin-token",
            additional_config={"actor_urn": "urn:li:person:123"},
        ),
    )
    vendor_manager.store_credentials(
        "tiktok_api",
        VendorCredentials(
            vendor_type=VendorType.SOCIAL_MEDIA,
            platform="tiktok",
            api_key="tiktok-key",
            access_token="tiktok-token",
            additional_config={"advertiser_id": "adv-1"},
        ),
    )

    monkeypatch.setattr(platform_router, "_build_platform_client", lambda platform, credentials: DummyPlatformClient())
    platform_router._scheduled_posts.clear()
    platform_router._inbox_messages.clear()

    app = FastAPI()
    app.include_router(platform_router.create_platform_integration_router(enforce_rate_limit=lambda *_: None))
    return TestClient(app, raise_server_exceptions=False)


def test_list_accounts_reports_connected_platforms(client: TestClient) -> None:
    response = client.get("/platforms/accounts", headers=H)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert {item["platform"] for item in body["accounts"]} >= {"twitter", "facebook", "instagram", "linkedin", "tiktok"}


def test_publish_twitter_uses_provider_client(client: TestClient) -> None:
    response = client.post(
        "/platforms/twitter/publish",
        headers=H,
        json={"content": "hello world", "media_urls": [], "hashtags": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "published"
    assert body["platform"] == "twitter"
    assert body["post_id"] == "tweet-1"


def test_schedule_multi_platform_uses_provider_clients(client: TestClient) -> None:
    response = client.post(
        "/platforms/schedule",
        headers=H,
        json={
            "content": "scheduled post",
            "media_urls": ["https://example.com/image.jpg"],
            "platforms": ["twitter", "facebook"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scheduled"
    assert len(body["results"]) == 2


def test_metrics_require_platform_and_use_provider_client(client: TestClient) -> None:
    response = client.get(
        "/platforms/posts/post-123/metrics",
        headers=H,
        params={"platform": "twitter"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["platform"] == "twitter"
    assert body["tweet_id"] == "post-123"


def test_cancel_scheduled_post_updates_status(client: TestClient) -> None:
    schedule_response = client.post(
        "/platforms/schedule",
        headers=H,
        json={
            "content": "scheduled cancel test",
            "media_urls": ["https://example.com/image.jpg"],
            "platforms": ["twitter"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )
    assert schedule_response.status_code == 200

    list_response = client.get("/platforms/scheduled-posts", headers=H)
    assert list_response.status_code == 200
    scheduled_posts = list_response.json()["posts"]
    assert scheduled_posts
    target_post_id = scheduled_posts[0]["id"]

    cancel_response = client.post(f"/platforms/scheduled-posts/{target_post_id}/cancel", headers=H)
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    list_after_cancel = client.get("/platforms/scheduled-posts", headers=H)
    assert list_after_cancel.status_code == 200
    updated_posts = list_after_cancel.json()["posts"]
    cancelled_post = next(post for post in updated_posts if post["id"] == target_post_id)
    assert cancelled_post["status"] == "cancelled"


def test_schedule_fails_closed_in_production_when_persistence_unavailable(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(platform_router, "_persist_scheduled_posts_store", lambda: False)

    response = client.post(
        "/platforms/schedule",
        headers=H,
        json={
            "content": "scheduled persistence fail-closed test",
            "media_urls": ["https://example.com/image.jpg"],
            "platforms": ["twitter"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Scheduled post persistence is unavailable in production."

    list_response = client.get("/platforms/scheduled-posts", headers=H)
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0


def test_force_publish_rejects_cancelled_post(client: TestClient) -> None:
    schedule_response = client.post(
        "/platforms/schedule",
        headers=H,
        json={
            "content": "scheduled then cancelled",
            "media_urls": ["https://example.com/image.jpg"],
            "platforms": ["twitter"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )
    assert schedule_response.status_code == 200

    list_response = client.get("/platforms/scheduled-posts", headers=H)
    post_id = list_response.json()["posts"][0]["id"]

    cancel_response = client.post(f"/platforms/scheduled-posts/{post_id}/cancel", headers=H)
    assert cancel_response.status_code == 200

    publish_now_response = client.post(f"/platforms/scheduled-posts/{post_id}/publish-now", headers=H)
    assert publish_now_response.status_code == 409
    assert publish_now_response.json()["detail"] == "Cancelled posts cannot be published"


def test_schedule_rejects_past_timestamp_without_creating_records(client: TestClient) -> None:
    response = client.post(
        "/platforms/schedule",
        headers=H,
        json={
            "content": "past schedule test",
            "media_urls": ["https://example.com/image.jpg"],
            "platforms": ["twitter"],
            "scheduled_at": "2020-01-01T00:00:00Z",
            "hashtags": ["nuxtron"],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "scheduled_at must be in the future"

    list_response = client.get("/platforms/scheduled-posts", headers=H)
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0


def test_schedule_rejects_instagram_without_media_before_side_effects(client: TestClient) -> None:
    response = client.post(
        "/platforms/schedule",
        headers=H,
        json={
            "content": "instagram missing media",
            "platforms": ["instagram", "twitter"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Instagram scheduling requires media_urls."

    list_response = client.get("/platforms/scheduled-posts", headers=H)
    assert list_response.status_code == 200
    assert list_response.json()["count"] == 0


def test_schedule_single_platform_endpoint_succeeds(client: TestClient) -> None:
    response = client.post(
        "/platforms/twitter/schedule",
        headers=H,
        json={
            "content": "single platform schedule test",
            "media_urls": ["https://example.com/image.jpg"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["platforms"] == ["twitter"]
    assert len(body["results"]) == 1
    assert body["results"][0]["platform"] == "twitter"


def test_accounts_verify_reports_status(client: TestClient) -> None:
    response = client.get("/platforms/accounts/verify", headers=H)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    platforms = {item["platform"] for item in body["accounts"]}
    assert platforms >= {"twitter", "facebook", "instagram", "linkedin", "tiktok"}


def test_platform_analytics_summary_and_compare(client: TestClient) -> None:
    schedule_response = client.post(
        "/platforms/twitter/schedule",
        headers=H,
        json={
            "content": "analytics compare test",
            "media_urls": ["https://example.com/image.jpg"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )
    assert schedule_response.status_code == 200

    list_response = client.get("/platforms/scheduled-posts", headers=H)
    assert list_response.status_code == 200
    post_id = list_response.json()["posts"][0]["id"]

    summary_response = client.get("/platforms/twitter/analytics/summary", headers=H)
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["status"] == "ok"
    assert summary["platform"] == "twitter"
    assert summary["total_posts"] >= 1

    compare_response = client.post(
        "/platforms/analytics/compare",
        headers=H,
        json=[post_id],
    )
    assert compare_response.status_code == 200
    compare = compare_response.json()
    assert compare["status"] == "ok"
    assert compare["requested"] == 1
    assert compare["found"] == 1
    assert compare["comparison"][0]["post_id"] == post_id


def test_message_get_reply_assign_and_tag(client: TestClient) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    message_id = "msg-1"
    platform_router._inbox_messages[H["X-Tenant-Id"]] = [
        {
            "id": message_id,
            "platform": "twitter",
            "text": "hello",
            "tags": [],
        }
    ]

    get_response = client.get(f"/platforms/messages/{message_id}", headers=H)
    assert get_response.status_code == 200
    assert get_response.json()["message"]["id"] == message_id

    reply_response = client.post(
        f"/platforms/messages/{message_id}/reply",
        headers=H,
        json={"reply_text": "Thanks for reaching out"},
    )
    assert reply_response.status_code == 200
    reply_body = reply_response.json()
    assert reply_body["status"] == "sent"
    assert reply_body["message_id"] == message_id
    assert reply_body["thread_size"] == 1
    assert reply_body["reply"]["text"] == "Thanks for reaching out"

    after_reply = client.get(f"/platforms/messages/{message_id}", headers=H)
    assert after_reply.status_code == 200
    assert after_reply.json()["message"]["status"] == "replied"
    assert len(after_reply.json()["message"].get("thread", [])) == 1

    assign_response = client.post(
        f"/platforms/messages/{message_id}/assign",
        headers=H,
        json={"assignee_id": "agent-1"},
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["status"] == "assigned"
    assert assign_response.json()["assigned_at"]

    tag_response = client.post(
        f"/platforms/messages/{message_id}/tag",
        headers=H,
        json={"tags": ["priority", "social"]},
    )
    assert tag_response.status_code == 200
    assert tag_response.json()["status"] == "tagged"
    assert set(tag_response.json()["tags"]) == {"priority", "social"}


def test_oauth_callback_persists_credentials(client: TestClient) -> None:
    response = client.post(
        "/platforms/oauth/twitter/callback",
        headers=H,
        json={
            "access_token": "new-twitter-token",
            "refresh_token": "new-twitter-refresh",
            "additional_config": {"client_id": "abc"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "connected"
    assert body["platform"] == "twitter"
    assert body["has_refresh_token"] is True


def test_disconnect_account_revokes_credentials(client: TestClient) -> None:
    response = client.post("/platforms/accounts/twitter/disconnect", headers=H)
    assert response.status_code == 200
    assert response.json()["status"] == "disconnected"

    list_response = client.get("/platforms/accounts", headers=H)
    assert list_response.status_code == 200
    platforms = {item["platform"] for item in list_response.json()["accounts"]}
    assert "twitter" not in platforms


def test_refresh_token_endpoint_updates_expiry(client: TestClient) -> None:
    response = client.post("/platforms/accounts/twitter/refresh-token", headers=H)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "refreshed"
    assert body["account_id"] == "twitter"
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert expires_at > datetime.now(UTC)


def test_refresh_token_endpoint_rejects_accounts_without_refresh_flow(client: TestClient) -> None:
    response = client.post("/platforms/accounts/facebook/refresh-token", headers=H)
    assert response.status_code == 409
    assert response.json()["detail"] == "Account does not support refresh-token flow"


@pytest.mark.parametrize(
    ("platform", "payload", "expected_post_id"),
    [
        ("facebook", {"content": "fb post"}, "facebook-1"),
        (
            "instagram",
            {"content": "ig story", "media_urls": ["https://example.com/story.jpg"]},
            "instagram-story",
        ),
        (
            "instagram",
            {"content": "ig reel", "media_urls": ["https://example.com/reel.mp4"]},
            "instagram-reel",
        ),
        (
            "instagram",
            {
                "content": "ig carousel",
                "media_urls": [
                    "https://example.com/a.jpg",
                    "https://example.com/b.jpg",
                ],
            },
            "instagram-carousel",
        ),
        ("linkedin", {"content": "linkedin post"}, "linkedin-1"),
        (
            "tiktok",
            {"content": "tiktok post", "media_urls": ["https://example.com/video.mp4"]},
            "tiktok-1",
        ),
    ],
)
def test_publish_supported_platform_variants(
    client: TestClient,
    platform: str,
    payload: dict[str, Any],
    expected_post_id: str,
) -> None:
    response = client.post(f"/platforms/{platform}/publish", headers=H, json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "published"
    assert body["platform"] == platform
    assert body["post_id"] == expected_post_id


def test_publish_rejects_unsupported_platform(client: TestClient) -> None:
    response = client.post(
        "/platforms/myspace/publish",
        headers=H,
        json={"content": "unsupported"},
    )
    assert response.status_code == 400


def test_publish_rejects_tiktok_without_video(client: TestClient) -> None:
    response = client.post(
        "/platforms/tiktok/publish",
        headers=H,
        json={"content": "missing media"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "TikTok publishing requires a video URL."


def test_oauth_authorize_supports_valid_platform_and_rejects_invalid(client: TestClient) -> None:
    ok_response = client.post(
        "/platforms/oauth/authorize/twitter",
        headers=H,
        params={"redirect_uri": "https://example.com/callback"},
    )
    assert ok_response.status_code == 200
    assert ok_response.json()["platform"] == "twitter"
    assert "authorization_url" in ok_response.json()

    invalid_response = client.post(
        "/platforms/oauth/authorize/unknown",
        headers=H,
        params={"redirect_uri": "https://example.com/callback"},
    )
    assert invalid_response.status_code == 400


@pytest.mark.parametrize("platform", ["twitter", "facebook", "instagram", "linkedin", "tiktok"])
def test_metrics_supported_platforms(client: TestClient, platform: str) -> None:
    response = client.get(
        "/platforms/posts/post-xyz/metrics",
        headers=H,
        params={"platform": platform},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["platform"] == platform


def test_metrics_rejects_unsupported_platform(client: TestClient) -> None:
    response = client.get(
        "/platforms/posts/post-xyz/metrics",
        headers=H,
        params={"platform": "unknown"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Unsupported platform requested."


def test_dashboard_and_health_report_platform_connectivity(client: TestClient) -> None:
    dashboard_response = client.get("/platforms/analytics/dashboard", headers=H)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["status"] == "ok"
    assert set(dashboard["platforms"].keys()) == {"twitter", "facebook", "instagram", "linkedin", "tiktok"}
    assert dashboard["platforms"]["twitter"]["connected"] is True

    health_response = client.get("/platforms/health", headers=H)
    assert health_response.status_code == 200
    health = health_response.json()
    assert health["status"] == "ok"
    assert health["platforms"]["twitter"]["connected"] is True


def test_inbox_filter_limit_and_not_found_paths(client: TestClient) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    platform_router._inbox_messages[H["X-Tenant-Id"]] = [
        {"id": "m1", "platform": "twitter", "text": "t1", "tags": []},
        {"id": "m2", "platform": "facebook", "text": "f1", "tags": []},
        {"id": "m3", "platform": "twitter", "text": "t2", "tags": []},
    ]

    response = client.get(
        "/platforms/messages/inbox",
        headers=H,
        params={"platform": "twitter", "limit": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert len(body["messages"]) == 1
    assert body["messages"][0]["platform"] == "twitter"

    missing_message_response = client.get("/platforms/messages/missing", headers=H)
    assert missing_message_response.status_code == 404


def test_assign_tag_and_disconnect_negative_paths(client: TestClient) -> None:
    assign_response = client.post(
        "/platforms/messages/does-not-exist/assign",
        headers=H,
        json={"assignee_id": "agent-1"},
    )
    assert assign_response.status_code == 404

    tag_response = client.post(
        "/platforms/messages/does-not-exist/tag",
        headers=H,
        json={"tags": ["priority"]},
    )
    assert tag_response.status_code == 404

    unknown_account_response = client.post("/platforms/accounts/unknown/disconnect", headers=H)
    assert unknown_account_response.status_code == 404


def test_force_publish_success_and_then_cancel_rejected_for_published(client: TestClient) -> None:
    schedule_response = client.post(
        "/platforms/twitter/schedule",
        headers=H,
        json={
            "content": "publish now success test",
            "media_urls": ["https://example.com/image.jpg"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )
    assert schedule_response.status_code == 200

    list_response = client.get("/platforms/scheduled-posts", headers=H)
    post_id = list_response.json()["posts"][0]["id"]

    publish_now_response = client.post(f"/platforms/scheduled-posts/{post_id}/publish-now", headers=H)
    assert publish_now_response.status_code == 200
    assert publish_now_response.json()["status"] == "published"

    cancel_response = client.post(f"/platforms/scheduled-posts/{post_id}/cancel", headers=H)
    assert cancel_response.status_code == 409
    assert cancel_response.json()["detail"] == "Published posts cannot be cancelled"


def test_schedule_rejects_unsupported_platform(client: TestClient) -> None:
    response = client.post(
        "/platforms/schedule",
        headers=H,
        json={
            "content": "unsupported schedule",
            "platforms": ["unknown"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Unsupported platform requested."


@pytest.mark.parametrize(
    ("platform", "media_urls"),
    [
        ("instagram", ["https://example.com/image.jpg"]),
        ("linkedin", ["https://example.com/image.jpg"]),
        ("tiktok", ["https://example.com/video.mp4"]),
    ],
)
def test_schedule_multi_platform_additional_provider_paths(
    client: TestClient,
    platform: str,
    media_urls: list[str],
) -> None:
    response = client.post(
        "/platforms/schedule",
        headers=H,
        json={
            "content": f"schedule for {platform}",
            "media_urls": media_urls,
            "platforms": [platform],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )
    assert response.status_code == 200
    assert response.json()["results"][0]["platform"] == platform


def test_reply_compare_and_summary_negative_paths(client: TestClient) -> None:
    reply_response = client.post(
        "/platforms/messages/msg-1/reply",
        headers=H,
        json={"reply_text": "Thanks for reaching out"},
    )
    assert reply_response.status_code == 404
    assert reply_response.json()["detail"] == "Message not found"

    compare_response = client.post("/platforms/analytics/compare", headers=H, json=[])
    assert compare_response.status_code == 422
    assert compare_response.json()["detail"] == "post_ids cannot be empty"

    summary_response = client.get("/platforms/unknown/analytics/summary", headers=H)
    assert summary_response.status_code == 422
    assert summary_response.json()["detail"] == "Unsupported platform requested."


def test_verify_reports_expired_token_reason(client: TestClient) -> None:
    from backend.fastapi.app.integrations.vendor_manager import get_vendor_manager

    vendor_manager = get_vendor_manager()
    creds = vendor_manager.get_credentials("twitter_api")
    assert creds is not None
    creds.expires_at = datetime.now(UTC) - timedelta(hours=1)
    vendor_manager.store_credentials("twitter_api", creds)

    response = client.get("/platforms/accounts/verify", headers=H)
    assert response.status_code == 200
    twitter_entry = next(item for item in response.json()["accounts"] if item["platform"] == "twitter")
    assert twitter_entry["valid"] is False
    assert twitter_entry["reason"] == "expired_token"


def test_oauth_callback_validation_and_disconnect_not_connected(client: TestClient) -> None:
    missing_token = client.post(
        "/platforms/oauth/twitter/callback",
        headers=H,
        json={},
    )
    assert missing_token.status_code == 422
    assert "access_token is required" in missing_token.json()["detail"]

    unsupported = client.post(
        "/platforms/oauth/unknown/callback",
        headers=H,
        json={"access_token": "x"},
    )
    assert unsupported.status_code == 422
    assert unsupported.json()["detail"] == "Unsupported platform requested."

    disconnect_once = client.post("/platforms/accounts/twitter/disconnect", headers=H)
    assert disconnect_once.status_code == 200
    disconnect_twice = client.post("/platforms/accounts/twitter/disconnect", headers=H)
    assert disconnect_twice.status_code == 404
    assert disconnect_twice.json()["detail"] == "Account not connected"


def test_refresh_token_not_connected_and_unknown_account(client: TestClient) -> None:
    disconnect = client.post("/platforms/accounts/twitter/disconnect", headers=H)
    assert disconnect.status_code == 200

    not_connected = client.post("/platforms/accounts/twitter/refresh-token", headers=H)
    assert not_connected.status_code == 404
    assert not_connected.json()["detail"] == "Account not connected"

    unknown = client.post("/platforms/accounts/unknown/refresh-token", headers=H)
    assert unknown.status_code == 404
    assert unknown.json()["detail"] == "Account not found"


def test_schedule_and_inbox_store_helper_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    monkeypatch.delenv("PLATFORM_SCHEDULE_STORE_PATH", raising=False)
    default_path = platform_router._schedule_store_path()
    assert str(default_path).endswith("storage\\platform\\scheduled_posts.json") or str(default_path).endswith("storage/platform/scheduled_posts.json")

    custom_path = tmp_path / "custom" / "store.json"
    monkeypatch.setenv("PLATFORM_SCHEDULE_STORE_PATH", str(custom_path))
    assert platform_router._schedule_store_path() == custom_path

    # Invalid JSON should load as empty dict.
    custom_path.parent.mkdir(parents=True, exist_ok=True)
    custom_path.write_text("not-json", encoding="utf-8")
    loaded = platform_router._load_scheduled_posts_store()
    assert loaded == {}

    monkeypatch.delenv("PLATFORM_INBOX_STORE_PATH", raising=False)
    default_inbox_path = platform_router._inbox_store_path()
    assert str(default_inbox_path).endswith("storage\\platform\\inbox_messages.json") or str(default_inbox_path).endswith("storage/platform/inbox_messages.json")

    custom_inbox_path = tmp_path / "custom" / "inbox-store.json"
    monkeypatch.setenv("PLATFORM_INBOX_STORE_PATH", str(custom_inbox_path))
    assert platform_router._inbox_store_path() == custom_inbox_path

    custom_inbox_path.parent.mkdir(parents=True, exist_ok=True)
    custom_inbox_path.write_text("not-json", encoding="utf-8")
    loaded_inbox = platform_router._load_inbox_messages_store()
    assert loaded_inbox == {}


def test_persist_store_helper_and_fail_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router
    from fastapi import HTTPException

    schedule_path = tmp_path / "persist" / "scheduled_posts.json"
    monkeypatch.setenv("PLATFORM_SCHEDULE_STORE_PATH", str(schedule_path))

    platform_router._scheduled_posts.clear()
    platform_router._scheduled_posts[H["X-Tenant-Id"]] = [{"id": "1", "status": "scheduled"}]
    assert platform_router._persist_scheduled_posts_store() is True
    assert schedule_path.exists()

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(platform_router, "_persist_scheduled_posts_store", lambda: False)
    with pytest.raises(HTTPException) as exc:
        platform_router._persist_scheduled_posts_or_raise()
    assert exc.value.status_code == 503


def test_platform_vendor_mapping_and_build_client_validation() -> None:
    from backend.fastapi.app.integrations.vendor_manager import VendorCredentials, VendorType
    from backend.fastapi.app.routers import platform_integration as platform_router

    assert platform_router._platform_vendor_id("twitter") == "twitter_api"
    assert platform_router._platform_vendor_id("facebook") == "meta_graph_api"
    assert platform_router._platform_vendor_id("unknown") == "unknown_api"

    missing_token_credentials = VendorCredentials(
        vendor_type=VendorType.SOCIAL_MEDIA,
        platform="twitter",
        api_key="",
        access_token="",
    )
    with pytest.raises(HTTPException):
        platform_router._build_platform_client("twitter", missing_token_credentials)

    invalid_fb_credentials = VendorCredentials(
        vendor_type=VendorType.SOCIAL_MEDIA,
        platform="facebook",
        api_key="k",
        access_token="t",
        additional_config={},
    )
    with pytest.raises(HTTPException):
        platform_router._build_platform_client("facebook", invalid_fb_credentials)


def test_load_store_normalizes_shape_and_filters_records(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    schedule_path = tmp_path / "normalize" / "scheduled_posts.json"
    schedule_path.parent.mkdir(parents=True, exist_ok=True)
    schedule_path.write_text("{}", encoding="utf-8")

    monkeypatch.setenv("PLATFORM_SCHEDULE_STORE_PATH", str(schedule_path))
    monkeypatch.setattr(
        platform_router.json,
        "loads",
        lambda *_: {
            "tenant-a": [{"id": "1"}, "skip", 3],
            "tenant-b": "not-a-list",
        },
    )

    loaded = platform_router._load_scheduled_posts_store()
    assert loaded == {"tenant-a": [{"id": "1"}]}


def test_persist_or_raise_is_noop_when_not_production(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setattr(platform_router, "_persist_scheduled_posts_store", lambda: False)

    # In non-production, persistence failure should not block request handling.
    platform_router._persist_scheduled_posts_or_raise()


def test_build_client_validation_for_instagram_linkedin_tiktok_and_unsupported() -> None:
    from backend.fastapi.app.integrations.vendor_manager import VendorCredentials, VendorType
    from backend.fastapi.app.routers import platform_integration as platform_router
    from fastapi import HTTPException

    invalid_instagram = VendorCredentials(
        vendor_type=VendorType.SOCIAL_MEDIA,
        platform="instagram",
        api_key="k",
        access_token="t",
        additional_config={},
    )
    with pytest.raises(HTTPException):
        platform_router._build_platform_client("instagram", invalid_instagram)

    invalid_linkedin = VendorCredentials(
        vendor_type=VendorType.SOCIAL_MEDIA,
        platform="linkedin",
        api_key="k",
        access_token="t",
        additional_config={},
    )
    with pytest.raises(HTTPException):
        platform_router._build_platform_client("linkedin", invalid_linkedin)

    valid_linkedin_with_user_id = VendorCredentials(
        vendor_type=VendorType.SOCIAL_MEDIA,
        platform="linkedin",
        api_key="k",
        access_token="t",
        additional_config={"user_id": "12345"},
    )
    client = platform_router._build_platform_client("linkedin", valid_linkedin_with_user_id)
    assert client is not None

    invalid_tiktok = VendorCredentials(
        vendor_type=VendorType.SOCIAL_MEDIA,
        platform="tiktok",
        api_key="k",
        access_token="t",
        additional_config={},
    )
    with pytest.raises(HTTPException):
        platform_router._build_platform_client("tiktok", invalid_tiktok)

    with pytest.raises(HTTPException):
        platform_router._build_platform_client(
            "unknown",
            VendorCredentials(
                vendor_type=VendorType.SOCIAL_MEDIA,
                platform="unknown",
                api_key="k",
                access_token="t",
            ),
        )


def test_close_client_handles_awaitable_and_raised_close(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from backend.fastapi.app.routers import platform_integration as platform_router

    def _fake_create_task(coro: Any) -> None:
        coro.close()
        return None

    monkeypatch.setattr(asyncio, "create_task", _fake_create_task)

    class AwaitableClose:
        def close(self) -> Any:
            async def _cleanup() -> None:
                return None

            return _cleanup()

    class RaisingClose:
        def close(self) -> None:
            raise RuntimeError("boom")

    class NoClose:
        pass

    platform_router._close_client(AwaitableClose())
    platform_router._close_client(RaisingClose())
    platform_router._close_client(NoClose())


def test_load_store_returns_empty_for_non_dict_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    schedule_path = tmp_path / "nondict" / "scheduled_posts.json"
    schedule_path.parent.mkdir(parents=True, exist_ok=True)
    schedule_path.write_text("[]", encoding="utf-8")

    monkeypatch.setenv("PLATFORM_SCHEDULE_STORE_PATH", str(schedule_path))
    loaded = platform_router._load_scheduled_posts_store()
    assert loaded == {}


def test_persist_store_returns_false_when_write_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    schedule_path = tmp_path / "write-fail" / "scheduled_posts.json"
    monkeypatch.setenv("PLATFORM_SCHEDULE_STORE_PATH", str(schedule_path))

    def _boom(*_args: Any, **_kwargs: Any) -> str:
        raise OSError("write failed")

    monkeypatch.setattr(Path, "write_text", _boom)
    assert platform_router._persist_scheduled_posts_store() is False
    assert platform_router._persist_inbox_messages_store() is False


def test_build_client_valid_branch_coverage() -> None:
    from backend.fastapi.app.integrations.vendor_manager import VendorCredentials, VendorType
    from backend.fastapi.app.routers import platform_integration as platform_router

    twitter_client = platform_router._build_platform_client(
        "twitter",
        VendorCredentials(
            vendor_type=VendorType.SOCIAL_MEDIA,
            platform="twitter",
            api_key="k",
            access_token="t",
            additional_config={"client_id": "id", "client_secret": "secret"},
        ),
    )
    assert twitter_client is not None

    facebook_client = platform_router._build_platform_client(
        "facebook",
        VendorCredentials(
            vendor_type=VendorType.SOCIAL_MEDIA,
            platform="facebook",
            api_key="k",
            access_token="t",
            additional_config={"page_id": "p1"},
        ),
    )
    assert facebook_client is not None

    instagram_client = platform_router._build_platform_client(
        "instagram",
        VendorCredentials(
            vendor_type=VendorType.SOCIAL_MEDIA,
            platform="instagram",
            api_key="k",
            access_token="t",
            additional_config={"ig_user_id": "ig-1"},
        ),
    )
    assert instagram_client is not None

    linkedin_client = platform_router._build_platform_client(
        "linkedin",
        VendorCredentials(
            vendor_type=VendorType.SOCIAL_MEDIA,
            platform="linkedin",
            api_key="k",
            access_token="t",
            additional_config={"actor_urn": "urn:li:person:123"},
        ),
    )
    assert linkedin_client is not None

    tiktok_client = platform_router._build_platform_client(
        "tiktok",
        VendorCredentials(
            vendor_type=VendorType.SOCIAL_MEDIA,
            platform="tiktok",
            api_key="k",
            access_token="t",
            additional_config={"advertiser_id": "adv-1"},
        ),
    )
    assert tiktok_client is not None


def test_oauth_callback_merges_existing_additional_config(client: TestClient) -> None:
    response = client.post(
        "/platforms/oauth/linkedin/callback",
        headers=H,
        json={
            "access_token": "linkedin-updated-token",
            "additional_config": {"region": "us"},
        },
    )
    assert response.status_code == 200


def test_publish_future_timestamp_routes_to_schedule_flow(client: TestClient) -> None:
    response = client.post(
        "/platforms/twitter/publish",
        headers=H,
        json={
            "content": "future schedule from publish",
            "media_urls": ["https://example.com/image.jpg"],
            "hashtags": ["nuxtron"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "scheduled"


def test_publish_instagram_requires_media(client: TestClient) -> None:
    response = client.post(
        "/platforms/instagram/publish",
        headers=H,
        json={"content": "no media"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Instagram publishing requires at least one media URL."


def test_schedule_single_platform_rejects_unsupported_platform(client: TestClient) -> None:
    response = client.post(
        "/platforms/unknown/schedule",
        headers=H,
        json={
            "content": "unsupported",
            "scheduled_at": FUTURE_SCHEDULE_AT,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Unsupported platform requested."


def test_force_publish_not_found_and_skip_empty_platform_entry(client: TestClient) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    not_found = client.post("/platforms/scheduled-posts/missing/publish-now", headers=H)
    assert not_found.status_code == 404

    platform_router._scheduled_posts[H["X-Tenant-Id"]] = [
        {
            "id": "post-empty-platform",
            "tenant_id": H["X-Tenant-Id"],
            "platform": "twitter",
            "platforms": ["twitter", ""],
            "content": "with empty platform entry",
            "media_urls": ["https://example.com/image.jpg"],
            "hashtags": [],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "status": "scheduled",
        }
    ]
    response = client.post("/platforms/scheduled-posts/post-empty-platform/publish-now", headers=H)
    assert response.status_code == 200
    assert response.json()["status"] == "published"


def test_force_publish_rolls_back_when_persist_fails(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router
    from fastapi import HTTPException

    schedule_response = client.post(
        "/platforms/twitter/schedule",
        headers=H,
        json={
            "content": "rollback publish-now",
            "media_urls": ["https://example.com/image.jpg"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )
    assert schedule_response.status_code == 200
    post_id = client.get("/platforms/scheduled-posts", headers=H).json()["posts"][0]["id"]

    def _raise_http() -> None:
        raise HTTPException(status_code=503, detail="persist down")

    monkeypatch.setattr(platform_router, "_persist_scheduled_posts_or_raise", _raise_http)
    response = client.post(f"/platforms/scheduled-posts/{post_id}/publish-now", headers=H)
    assert response.status_code == 503

    post = next(p for p in platform_router._scheduled_posts[H["X-Tenant-Id"]] if p["id"] == post_id)
    assert post["status"] == "scheduled"
    assert "published_at" not in post
    assert "published_results" not in post


def test_cancel_not_found_and_rollback_when_persist_fails(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router
    from fastapi import HTTPException

    not_found = client.post("/platforms/scheduled-posts/missing/cancel", headers=H)
    assert not_found.status_code == 404

    schedule_response = client.post(
        "/platforms/twitter/schedule",
        headers=H,
        json={
            "content": "rollback cancel",
            "media_urls": ["https://example.com/image.jpg"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "hashtags": ["nuxtron"],
        },
    )
    assert schedule_response.status_code == 200
    post_id = client.get("/platforms/scheduled-posts", headers=H).json()["posts"][0]["id"]

    def _raise_http() -> None:
        raise HTTPException(status_code=503, detail="persist down")

    monkeypatch.setattr(platform_router, "_persist_scheduled_posts_or_raise", _raise_http)
    response = client.post(f"/platforms/scheduled-posts/{post_id}/cancel", headers=H)
    assert response.status_code == 503

    post = next(p for p in platform_router._scheduled_posts[H["X-Tenant-Id"]] if p["id"] == post_id)
    assert post["status"] == "scheduled"
    assert "cancelled_at" not in post


def test_metrics_uses_dict_payload_branch_when_model_dump_absent(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    class DictMetricsClient(DummyPlatformClient):
        async def get_tweet_metrics(self, post_id: str) -> dict[str, Any]:
            return {"tweet_id": post_id, "likes": 3}

    monkeypatch.setattr(platform_router, "_build_platform_client", lambda *_: DictMetricsClient())
    response = client.get(
        "/platforms/posts/post-dict/metrics",
        headers=H,
        params={"platform": "twitter"},
    )
    assert response.status_code == 200
    assert response.json()["tweet_id"] == "post-dict"


def test_tag_requires_non_empty_tag_and_verify_reports_missing_credentials(client: TestClient) -> None:
    missing_tag_response = client.post(
        "/platforms/messages/msg-1/tag",
        headers=H,
        json={"tags": ["   ", ""]},
    )
    assert missing_tag_response.status_code == 422
    assert missing_tag_response.json()["detail"] == "At least one non-empty tag is required"

    disconnect = client.post("/platforms/accounts/twitter/disconnect", headers=H)
    assert disconnect.status_code == 200
    verify = client.get("/platforms/accounts/verify", headers=H)
    assert verify.status_code == 200
    twitter_entry = next(item for item in verify.json()["accounts"] if item["platform"] == "twitter")
    assert twitter_entry["reason"] == "missing_credentials"


def test_schedule_rejects_tiktok_without_video(client: TestClient) -> None:
    response = client.post(
        "/platforms/schedule",
        headers=H,
        json={
            "content": "tiktok schedule missing media",
            "platforms": ["tiktok"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "TikTok scheduling requires a video URL."


def test_publish_returns_503_when_platform_credentials_missing(client: TestClient) -> None:
    disconnect = client.post("/platforms/accounts/twitter/disconnect", headers=H)
    assert disconnect.status_code == 200

    response = client.post(
        "/platforms/twitter/publish",
        headers=H,
        json={"content": "credential missing test"},
    )
    assert response.status_code == 503
    assert "twitter credentials are not configured" in response.json()["detail"]


def test_force_publish_rollback_restores_existing_published_fields(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router
    from fastapi import HTTPException

    post_id = "post-with-prior-published-fields"
    platform_router._scheduled_posts[H["X-Tenant-Id"]] = [
        {
            "id": post_id,
            "tenant_id": H["X-Tenant-Id"],
            "platform": "twitter",
            "platforms": ["twitter"],
            "content": "rollback with previous published fields",
            "media_urls": ["https://example.com/image.jpg"],
            "hashtags": [],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "status": "scheduled",
            "published_at": "2026-05-19T12:00:00+00:00",
            "published_results": [{"platform": "twitter", "result": {"id": "old"}}],
        }
    ]

    def _raise_http() -> None:
        raise HTTPException(status_code=503, detail="persist down")

    monkeypatch.setattr(platform_router, "_persist_scheduled_posts_or_raise", _raise_http)
    response = client.post(f"/platforms/scheduled-posts/{post_id}/publish-now", headers=H)
    assert response.status_code == 503

    post = platform_router._scheduled_posts[H["X-Tenant-Id"]][0]
    assert post["published_at"] == "2026-05-19T12:00:00+00:00"
    assert post["published_results"] == [{"platform": "twitter", "result": {"id": "old"}}]


def test_cancel_rollback_restores_existing_cancelled_at(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router
    from fastapi import HTTPException

    post_id = "post-with-prior-cancelled-at"
    platform_router._scheduled_posts[H["X-Tenant-Id"]] = [
        {
            "id": post_id,
            "tenant_id": H["X-Tenant-Id"],
            "platform": "twitter",
            "content": "rollback cancel with previous timestamp",
            "media_urls": ["https://example.com/image.jpg"],
            "hashtags": [],
            "scheduled_at": FUTURE_SCHEDULE_AT,
            "status": "scheduled",
            "cancelled_at": "2026-05-18T12:00:00+00:00",
        }
    ]

    def _raise_http() -> None:
        raise HTTPException(status_code=503, detail="persist down")

    monkeypatch.setattr(platform_router, "_persist_scheduled_posts_or_raise", _raise_http)
    response = client.post(f"/platforms/scheduled-posts/{post_id}/cancel", headers=H)
    assert response.status_code == 503

    post = platform_router._scheduled_posts[H["X-Tenant-Id"]][0]
    assert post["cancelled_at"] == "2026-05-18T12:00:00+00:00"


def test_controlled_unreachable_else_branches_for_publish_schedule_and_metrics(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app.routers import platform_integration as platform_router

    monkeypatch.setattr(platform_router, "_SUPPORTED_PLATFORMS", (*platform_router._SUPPORTED_PLATFORMS, "other"))
    monkeypatch.setattr(platform_router, "_build_platform_client", lambda *_: DummyPlatformClient())
    monkeypatch.setattr(platform_router, "_require_platform_credentials", lambda *_: object())

    publish_response = client.post(
        "/platforms/other/publish",
        headers=H,
        json={"content": "other publish"},
    )
    assert publish_response.status_code == 422
    assert publish_response.json()["detail"] == "Unsupported platform: other"

    schedule_response = client.post(
        "/platforms/schedule",
        headers=H,
        json={
            "content": "other schedule",
            "platforms": ["other"],
            "scheduled_at": FUTURE_SCHEDULE_AT,
        },
    )
    assert schedule_response.status_code == 422
    assert schedule_response.json()["detail"] == "Unsupported platform: other"

    metrics_response = client.get(
        "/platforms/posts/post-123/metrics",
        headers=H,
        params={"platform": "other"},
    )
    assert metrics_response.status_code == 422
    assert metrics_response.json()["detail"] == "Unsupported platform: other"

