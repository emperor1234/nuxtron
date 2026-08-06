# pyright: reportUnusedFunction=false
"""
Platform Integration Router — Unified social media API v1.

Endpoints for multi-platform publishing, scheduling, analytics, and messaging.

Published Endpoints:
─────────────────────

### Account Management
POST   /platforms/oauth/authorize/{platform}       – Get OAuth authorization URL
POST   /platforms/oauth/{platform}/callback        – OAuth callback handler
GET    /platforms/accounts                         – List connected accounts
POST   /platforms/accounts/{id}/disconnect         – Disconnect platform account
POST   /platforms/accounts/{id}/refresh-token      – Manually refresh token

### Publishing (Immediate & Scheduled)
POST   /platforms/{platform}/publish               – Publish post immediately
POST   /platforms/{platform}/schedule              – Schedule post for future
GET    /platforms/scheduled-posts                  – List scheduled posts
POST   /platforms/scheduled-posts/{id}/publish-now – Force immediate publish
POST   /platforms/scheduled-posts/{id}/cancel      – Cancel scheduled post

### Analytics & Metrics
GET    /platforms/posts/{post_id}/metrics          – Get post performance metrics
GET    /platforms/analytics/dashboard              – Multi-platform analytics overview
GET    /platforms/{platform}/analytics/summary     – Platform-specific summary
POST   /platforms/analytics/compare                – Compare performance across posts

### Messages & Engagement
GET    /platforms/messages/inbox                   – Unified multi-platform inbox
GET    /platforms/messages/{id}                    – Get specific message
POST   /platforms/messages/{id}/reply              – Reply to message (threaded)
POST   /platforms/messages/{id}/assign             – Assign to team member
POST   /platforms/messages/{id}/tag                – Add tags/labels

### Health & Status
GET    /platforms/accounts/verify                  – Verify all token validity
GET    /platforms/health                           – Connection health status
"""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth
from ..integrations.vendor_manager import VendorCredentials, VendorType, get_vendor_manager
from ..platform_clients.facebook_client import FacebookGraphClient, PagePostCreateRequest, PagePostScheduleRequest
from ..platform_clients.instagram_client import (
    CarouselPublishRequest,
    InstagramGraphClient,
    ReelPublishRequest,
    StoryPublishRequest,
)
from ..platform_clients.instagram_client import PostScheduleRequest as InstagramPostScheduleRequest
from ..platform_clients.linkedin_client import LinkedInGraphClient, PostRequest
from ..platform_clients.linkedin_client import PostScheduleRequest as LinkedInPostScheduleRequest
from ..platform_clients.tiktok_client import TikTokBusinessClient, VideoScheduleRequest, VideoUploadRequest
from ..platform_clients.twitter_client import TweetCreateRequest, TweetScheduleRequest, TwitterV2Client

logger = logging.getLogger(__name__)
AuthDep = Annotated[AuthContext, Depends(require_auth)]

# ─────────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────────

class OAuthAuthorizeRequest(BaseModel):
    """Request OAuth authorization."""
    platform: str = Field(..., pattern=r"^(twitter|facebook|instagram|linkedin|tiktok)$")
    redirect_uri: str = Field(..., description="Callback URI after authorization")
    scopes: list[str] | None = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback payload for credential persistence."""
    code: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    additional_config: dict[str, Any] | None = None


class PublishRequest(BaseModel):
    """Request to publish content."""
    content: str = Field(..., max_length=5000)
    media_urls: list[str] | None = None
    hashtags: list[str] | None = None
    scheduled_at: datetime | None = None  # If None, publish immediately


class SchedulePostRequest(BaseModel):
    """Request to schedule post."""
    content: str
    media_urls: list[str] | None = None
    platforms: list[str] = Field(default=..., min_length=1)
    scheduled_at: datetime
    hashtags: list[str] | None = None


class PlatformScheduleRequest(BaseModel):
    """Request to schedule post for a single platform."""
    content: str
    media_urls: list[str] | None = None
    scheduled_at: datetime
    hashtags: list[str] | None = None


class MessageReplyRequest(BaseModel):
    """Request to reply to message."""
    reply_text: str = Field(..., max_length=2000)
    is_internal: bool = Field(default=False, description="Internal note only?")


class MessageAssignRequest(BaseModel):
    """Request to assign a message to a team member."""
    assignee_id: str = Field(..., min_length=1, max_length=160)


class MessageTagRequest(BaseModel):
    """Request to add labels to a message."""
    tags: list[str] = Field(..., min_length=1)


# ─────────────────────────────────────────────────────────────────────────────────
# In-Memory Stores (Production: use Postgres)
# ─────────────────────────────────────────────────────────────────────────────────

_lock = threading.Lock()

# { tenant_id: { platform: client_instance } }
_platform_clients: dict[str, dict[str, Any]] = {}

# { tenant_id: [scheduled_post, ...] }
_scheduled_posts: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [message, ...] }
_inbox_messages: dict[str, list[dict[str, Any]]] = {}

_SUPPORTED_PLATFORMS = ("twitter", "facebook", "instagram", "linkedin", "tiktok")
_vendor_manager = get_vendor_manager()


def _is_production_env() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"


def _schedule_store_path() -> Path:
    configured = os.getenv("PLATFORM_SCHEDULE_STORE_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path("storage") / "platform" / "scheduled_posts.json"


def _inbox_store_path() -> Path:
    configured = os.getenv("PLATFORM_INBOX_STORE_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path("storage") / "platform" / "inbox_messages.json"


def _load_json_store(path: Path, *, warning_label: str) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.warning("Unable to load %s from %s", warning_label, path)
        return {}
    if not isinstance(payload, dict):
        return {}
    normalized: dict[str, list[dict[str, Any]]] = {}
    for tenant_id, records in payload.items():
        if not isinstance(tenant_id, str) or not isinstance(records, list):
            continue
        normalized[tenant_id] = [record for record in records if isinstance(record, dict)]
    return normalized


def _load_scheduled_posts_store() -> dict[str, list[dict[str, Any]]]:
    return _load_json_store(_schedule_store_path(), warning_label="platform scheduled-post store")


def _load_inbox_messages_store() -> dict[str, list[dict[str, Any]]]:
    return _load_json_store(_inbox_store_path(), warning_label="platform inbox store")


def _persist_json_store(path: Path, payload: dict[str, list[dict[str, Any]]], *, error_label: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
        return True
    except Exception:
        logger.exception("Unable to persist %s to %s", error_label, path)
        return False


def _persist_scheduled_posts_store() -> bool:
    return _persist_json_store(
        _schedule_store_path(),
        _scheduled_posts,
        error_label="platform scheduled-post store",
    )


def _persist_inbox_messages_store() -> bool:
    return _persist_json_store(
        _inbox_store_path(),
        _inbox_messages,
        error_label="platform inbox store",
    )


def _persist_scheduled_posts_or_raise() -> None:
    if _persist_scheduled_posts_store():
        return
    if _is_production_env():
        raise HTTPException(
            status_code=503,
            detail="Scheduled post persistence is unavailable in production.",
        )


def _persist_inbox_messages_or_raise() -> None:
    if _persist_inbox_messages_store():
        return
    if _is_production_env():
        raise HTTPException(
            status_code=503,
            detail="Inbox state persistence is unavailable in production.",
        )


def _validate_schedule_request(request: SchedulePostRequest, platforms: list[str]) -> None:
    if request.scheduled_at <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="scheduled_at must be in the future")

    for platform in platforms:
        # Validate provider credentials before any API side effects occur.
        _require_platform_credentials(platform)

        if platform == "instagram" and not request.media_urls:
            raise HTTPException(status_code=422, detail="Instagram scheduling requires media_urls.")
        if platform == "tiktok" and not request.media_urls:
            raise HTTPException(status_code=422, detail="TikTok scheduling requires a video URL.")


_scheduled_posts = _load_scheduled_posts_store()
_inbox_messages = _load_inbox_messages_store()


def _platform_vendor_id(platform: str) -> str:
    normalized = platform.strip().lower()
    return {
        "twitter": "twitter_api",
        "facebook": "meta_graph_api",
        "instagram": "meta_graph_api",
        "linkedin": "linkedin_api",
        "tiktok": "tiktok_api",
    }.get(normalized, f"{normalized}_api")


def _require_platform_credentials(platform: str) -> VendorCredentials:
    vendor_id = _platform_vendor_id(platform)
    credentials = _vendor_manager.get_credentials(vendor_id)
    if credentials is None:
        raise HTTPException(
            status_code=503,
            detail=f"{platform} credentials are not configured for this tenant.",
        )
    return credentials


def _build_platform_client(platform: str, credentials: VendorCredentials) -> Any:
    normalized = platform.strip().lower()
    access_token = credentials.access_token or credentials.api_key
    if not access_token:
        raise HTTPException(status_code=503, detail=f"{platform} access token is missing.")

    if normalized == "twitter":
        return TwitterV2Client(
            access_token=access_token,
            refresh_token=credentials.refresh_token,
            expires_at=credentials.expires_at,
            client_id=(credentials.additional_config or {}).get("client_id"),
            client_secret=(credentials.additional_config or {}).get("client_secret"),
        )
    if normalized == "facebook":
        page_id = (credentials.additional_config or {}).get("page_id")
        if not page_id:
            raise HTTPException(status_code=503, detail="facebook page_id is not configured.")
        return FacebookGraphClient(access_token=access_token, page_id=page_id)
    if normalized == "instagram":
        ig_user_id = (credentials.additional_config or {}).get("instagram_account_id") or (credentials.additional_config or {}).get("ig_user_id")
        if not ig_user_id:
            raise HTTPException(status_code=503, detail="instagram account id is not configured.")
        return InstagramGraphClient(access_token=access_token, ig_user_id=ig_user_id)
    if normalized == "linkedin":
        actor_urn = (credentials.additional_config or {}).get("actor_urn") or (credentials.additional_config or {}).get("user_urn")
        if not actor_urn:
            user_id = (credentials.additional_config or {}).get("user_id")
            if user_id:
                actor_urn = f"urn:li:person:{user_id}"
        if not actor_urn:
            raise HTTPException(status_code=503, detail="linkedin actor URN is not configured.")
        return LinkedInGraphClient(access_token=access_token, actor_urn=actor_urn)
    if normalized == "tiktok":
        advertiser_id = (credentials.additional_config or {}).get("advertiser_id") or (credentials.additional_config or {}).get("account_id")
        if not advertiser_id:
            raise HTTPException(status_code=503, detail="tiktok advertiser_id is not configured.")
        return TikTokBusinessClient(access_token=access_token, advertiser_id=advertiser_id)

    raise HTTPException(status_code=422, detail=f"Unsupported platform: {platform}")


def _close_client(client: Any) -> None:
    close = getattr(client, "close", None)
    if close is None:
        return
    try:
        result = close()
        if hasattr(result, "__await__"):
            # Best-effort cleanup if the caller created an async client.
            import asyncio

            asyncio.create_task(result)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────────

def create_platform_integration_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
) -> APIRouter:
    """Create platform integration router."""

    router = APIRouter(prefix="/platforms", tags=["Social Media Platforms"])

    # ─────────────────────────────────────────────────────────────────────────────
    # OAuth & Account Management
    # ─────────────────────────────────────────────────────────────────────────────

    @router.post("/oauth/authorize/{platform}")
    def get_oauth_url(
        platform: str,
        redirect_uri: str = Query(...),
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """
        Get OAuth authorization URL for platform.

        Returns: authorization_url to redirect user to
        """
        enforce_rate_limit(f"{auth.tenant_id}:oauth:authorize", 100, 60)

        if platform not in ("twitter", "facebook", "instagram", "linkedin", "tiktok"):
            raise HTTPException(400, "Unsupported platform")

        # Build OAuth URLs per platform
        oauth_urls = {
            "twitter": (
                f"https://twitter.com/i/oauth2/authorize"
                f"?client_id={os.getenv('TWITTER_CLIENT_ID')}"
                f"&redirect_uri={redirect_uri}"
                f"&response_type=code&scope=tweet.read%20tweet.write%20users.read"
            ),
            "facebook": (
                f"https://www.facebook.com/v18.0/dialog/oauth"
                f"?client_id={os.getenv('FACEBOOK_APP_ID')}"
                f"&redirect_uri={redirect_uri}"
                f"&scope=pages_manage_posts,pages_manage_metadata,pages_read_engagement"
            ),
            "instagram": (
                f"https://www.facebook.com/v18.0/dialog/oauth"
                f"?client_id={os.getenv('FACEBOOK_APP_ID')}"
                f"&redirect_uri={redirect_uri}"
                f"&scope=instagram_business_basic,instagram_business_content_publish"
            ),
            "linkedin": (
                f"https://www.linkedin.com/oauth/v2/authorization"
                f"?client_id={os.getenv('LINKEDIN_CLIENT_ID')}"
                f"&redirect_uri={redirect_uri}"
                f"&response_type=code&scope=w_member_social"
            ),
            "tiktok": (
                f"https://open.tiktok.com/auth/authorize"
                f"?client_key={os.getenv('TIKTOK_CLIENT_ID')}"
                f"&redirect_uri={redirect_uri}"
                f"&scope=video.list,video.upload"
            ),
        }

        return {
            "platform": platform,
            "authorization_url": oauth_urls.get(platform, ""),
            "scopes_required": {
                "twitter": ["tweet.read", "tweet.write", "users.read"],
                "facebook": ["pages_manage_posts"],
                "instagram": ["instagram_business_content_publish"],
                "linkedin": ["w_member_social"],
                "tiktok": ["video.list", "video.upload"],
            }.get(platform, []),
        }

    @router.get("/accounts")
    def list_accounts(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        """List connected platform accounts."""
        enforce_rate_limit(f"{auth.tenant_id}:accounts:list", 300, 60)
        accounts = []
        for platform in _SUPPORTED_PLATFORMS:
            vendor_id = _platform_vendor_id(platform)
            credentials = _vendor_manager.get_credentials(vendor_id)
            if credentials is not None:
                accounts.append(
                    {
                        "id": platform,
                        "platform": platform,
                        "connected": True,
                        "vendor_id": vendor_id,
                        "has_refresh_token": bool(credentials.refresh_token),
                    }
                )

        return {
            "status": "ok",
            "accounts": accounts,
        }

    @router.post("/oauth/{platform}/callback")
    def oauth_callback(
        platform: str,
        payload: OAuthCallbackRequest,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Persist OAuth callback tokens for a platform account."""
        enforce_rate_limit(f"{auth.tenant_id}:oauth:callback", 100, 60)

        normalized = platform.strip().lower()
        if normalized not in _SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=422, detail="Unsupported platform requested.")

        # This endpoint persists credential material provided by a trusted callback handler.
        access_token = (payload.access_token or "").strip()
        if not access_token:
            raise HTTPException(
                status_code=422,
                detail="access_token is required to persist platform credentials.",
            )

        vendor_id = _platform_vendor_id(normalized)
        existing = _vendor_manager.get_credentials(vendor_id)
        merged_config: dict[str, Any] = {}
        if existing and existing.additional_config:
            merged_config.update(existing.additional_config)
        if payload.additional_config:
            merged_config.update(payload.additional_config)

        credentials = VendorCredentials(
            vendor_type=VendorType.SOCIAL_MEDIA,
            platform=normalized,
            api_key=access_token,
            access_token=access_token,
            refresh_token=payload.refresh_token or (existing.refresh_token if existing else None),
            expires_at=payload.expires_at or (existing.expires_at if existing else None),
            additional_config=merged_config,
        )
        _vendor_manager.store_credentials(vendor_id, credentials)

        return {
            "status": "connected",
            "platform": normalized,
            "vendor_id": vendor_id,
            "has_refresh_token": bool(credentials.refresh_token),
        }

    @router.post("/accounts/{account_id}/disconnect")
    def disconnect_account(
        account_id: str,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Disconnect a platform account by platform id."""
        enforce_rate_limit(f"{auth.tenant_id}:accounts:disconnect", 100, 60)

        platform = account_id.strip().lower()
        if platform not in _SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=404, detail="Account not found")

        vendor_id = _platform_vendor_id(platform)
        disconnected = _vendor_manager.revoke_credentials(vendor_id)
        if not disconnected:
            raise HTTPException(status_code=404, detail="Account not connected")

        return {
            "status": "disconnected",
            "account_id": platform,
            "vendor_id": vendor_id,
        }

    @router.post("/accounts/{account_id}/refresh-token")
    def refresh_account_token(
        account_id: str,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Refresh account token metadata when a refresh token is available."""
        enforce_rate_limit(f"{auth.tenant_id}:accounts:refresh", 100, 60)

        platform = account_id.strip().lower()
        if platform not in _SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=404, detail="Account not found")

        vendor_id = _platform_vendor_id(platform)
        credentials = _vendor_manager.get_credentials(vendor_id)
        if credentials is None:
            raise HTTPException(status_code=404, detail="Account not connected")
        if not credentials.refresh_token:
            raise HTTPException(status_code=409, detail="Account does not support refresh-token flow")

        refreshed_credentials = VendorCredentials(
            vendor_type=credentials.vendor_type,
            platform=credentials.platform,
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
            access_token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            expires_at=(datetime.now(UTC) + timedelta(hours=2)).replace(microsecond=0),
            endpoint_url=credentials.endpoint_url,
            additional_config=credentials.additional_config,
        )
        _vendor_manager.store_credentials(vendor_id, refreshed_credentials)

        return {
            "status": "refreshed",
            "account_id": platform,
            "vendor_id": vendor_id,
            "expires_at": refreshed_credentials.expires_at.isoformat() if refreshed_credentials.expires_at else None,
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # Publishing
    # ─────────────────────────────────────────────────────────────────────────────

    @router.post("/{platform}/publish")
    async def publish_post(
        platform: str,
        request: PublishRequest,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """
        Publish content to platform immediately.

        Platforms: twitter, facebook, instagram, linkedin, tiktok
        """
        enforce_rate_limit(f"{auth.tenant_id}:publish", 600, 60)

        if platform not in _SUPPORTED_PLATFORMS:
            raise HTTPException(400, "Unsupported platform")

        if request.scheduled_at and request.scheduled_at > datetime.now(UTC):
            return await schedule_post(
                SchedulePostRequest(
                    content=request.content,
                    media_urls=request.media_urls,
                    platforms=[platform],
                    scheduled_at=request.scheduled_at,
                    hashtags=request.hashtags,
                ),
                auth,
            )

        credentials = _require_platform_credentials(platform)
        client = _build_platform_client(platform, credentials)
        try:
            if platform == "twitter":
                result = await client.create_tweet(
                    TweetCreateRequest(
                        text=request.content,
                        media_ids=None,
                        in_reply_to_tweet_id=None,
                    )
                )
                post_id = result.get("data", {}).get("id") or result.get("id")
                return {
                    "status": "published",
                    "platform": platform,
                    "post_id": post_id,
                    "provider_response": result,
                    "published_at": datetime.now(UTC).isoformat(),
                }

            if platform == "facebook":
                result = await client.create_page_post(
                    PagePostCreateRequest(
                        message=request.content,
                        link=None,
                        picture=request.media_urls[0] if request.media_urls else None,
                    )
                )
                return {
                    "status": "published",
                    "platform": platform,
                    "post_id": result.get("id"),
                    "provider_response": result,
                    "published_at": datetime.now(UTC).isoformat(),
                }

            if platform == "instagram":
                if not request.media_urls:
                    raise HTTPException(status_code=422, detail="Instagram publishing requires at least one media URL.")
                if len(request.media_urls) > 1:
                    result = await client.publish_carousel(
                        CarouselPublishRequest(
                            media_urls=request.media_urls,
                            captions=None,
                            main_caption=request.content,
                        )
                    )
                elif request.media_urls[0].lower().endswith((".mp4", ".mov", ".avi", ".webm")):
                    result = await client.publish_reel(
                        ReelPublishRequest(video_url=request.media_urls[0], caption=request.content)
                    )
                else:
                    result = await client.publish_story(
                        StoryPublishRequest(
                            media_url=request.media_urls[0],
                            media_type="IMAGE",
                            sticker_type=None,
                        )
                    )
                return {
                    "status": "published",
                    "platform": platform,
                    "post_id": result.get("id") or result.get("post_id"),
                    "provider_response": result,
                    "published_at": datetime.now(UTC).isoformat(),
                }

            if platform == "linkedin":
                result = await client.create_post(
                    PostRequest(text=request.content)
                )
                return {
                    "status": "published",
                    "platform": platform,
                    "post_id": result.get("id") or result.get("urn"),
                    "provider_response": result,
                    "published_at": datetime.now(UTC).isoformat(),
                }

            if platform == "tiktok":
                if not request.media_urls:
                    raise HTTPException(status_code=422, detail="TikTok publishing requires a video URL.")
                result = await client.upload_video(
                    VideoUploadRequest(
                        video_url=request.media_urls[0],
                        title=request.content[:150],
                        description=request.content,
                        hashtags=request.hashtags or [],
                    )
                )
                return {
                    "status": "published",
                    "platform": platform,
                    "post_id": result.get("video_id") or result.get("post_id"),
                    "provider_response": result,
                    "published_at": datetime.now(UTC).isoformat(),
                }

            raise HTTPException(status_code=422, detail=f"Unsupported platform: {platform}")
        finally:
            await client.close()

    @router.post("/schedule")
    async def schedule_post(
        request: SchedulePostRequest,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Schedule post across multiple platforms."""
        enforce_rate_limit(f"{auth.tenant_id}:schedule", 300, 60)

        platforms = [platform.strip().lower() for platform in request.platforms]
        if not platforms or any(platform not in _SUPPORTED_PLATFORMS for platform in platforms):
            raise HTTPException(status_code=422, detail="Unsupported platform requested.")

        # Pre-validate all platform prerequisites before external calls.
        _validate_schedule_request(request, list(dict.fromkeys(platforms)))

        scheduled_results: list[dict[str, Any]] = []
        scheduled_records: list[dict[str, Any]] = []
        for platform in dict.fromkeys(platforms):
            credentials = _require_platform_credentials(platform)
            client = _build_platform_client(platform, credentials)
            try:
                if platform == "twitter":
                    result = await client.schedule_tweet(
                        TweetScheduleRequest(
                            text=request.content,
                            media_ids=None,
                            scheduled_at=request.scheduled_at,
                        )
                    )
                elif platform == "facebook":
                    result = await client.schedule_page_post(
                        PagePostScheduleRequest(
                            message=request.content,
                            scheduled_publish_time=request.scheduled_at,
                        )
                    )
                elif platform == "instagram":
                    result = await client.schedule_post(
                        InstagramPostScheduleRequest(
                            media_type="CAROUSEL" if len(request.media_urls) > 1 else "SINGLE_IMAGE",
                            media_urls=request.media_urls,
                            caption=request.content,
                            scheduled_timestamp=request.scheduled_at,
                        )
                    )
                elif platform == "linkedin":
                    result = await client.schedule_post(
                        LinkedInPostScheduleRequest(
                            text=request.content,
                            scheduled_time=request.scheduled_at,
                        )
                    )
                elif platform == "tiktok":
                    if not request.media_urls:
                        raise HTTPException(status_code=422, detail="TikTok scheduling requires a video URL.")
                    result = await client.schedule_video(
                        VideoScheduleRequest(
                            video_url=request.media_urls[0],
                            title=request.content[:150],
                            description=request.content,
                            scheduled_time=request.scheduled_at,
                        )
                    )
                else:
                    raise HTTPException(status_code=422, detail=f"Unsupported platform: {platform}")

                scheduled_results.append(
                    {
                        "platform": platform,
                        "result": result,
                    }
                )
                scheduled_records.append(
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": auth.tenant_id,
                        "platform": platform,
                        "content": request.content,
                        "media_urls": request.media_urls or [],
                        "hashtags": request.hashtags or [],
                        "scheduled_at": request.scheduled_at.isoformat(),
                        "status": "scheduled",
                        "provider_response": result,
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                )
            finally:
                await client.close()

        with _lock:
            if auth.tenant_id not in _scheduled_posts:
                _scheduled_posts[auth.tenant_id] = []
            tenant_posts = _scheduled_posts[auth.tenant_id]
            original_count = len(tenant_posts)
            tenant_posts.extend(scheduled_records)
            try:
                _persist_scheduled_posts_or_raise()
            except HTTPException:
                del tenant_posts[original_count:]
                raise

        return {
            "status": "scheduled",
            "scheduled_at": request.scheduled_at.isoformat(),
            "platforms": platforms,
            "results": scheduled_results,
        }

    @router.post("/{platform}/schedule")
    async def schedule_single_platform_post(
        platform: str,
        request: PlatformScheduleRequest,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Schedule content for a single platform."""
        normalized_platform = platform.strip().lower()
        if normalized_platform not in _SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=422, detail="Unsupported platform requested.")

        return await schedule_post(
            SchedulePostRequest(
                content=request.content,
                media_urls=request.media_urls,
                platforms=[normalized_platform],
                scheduled_at=request.scheduled_at,
                hashtags=request.hashtags,
            ),
            auth,
        )

    @router.get("/scheduled-posts")
    def list_scheduled_posts(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        """List all scheduled posts."""
        enforce_rate_limit(f"{auth.tenant_id}:scheduled:list", 300, 60)

        with _lock:
            posts = _scheduled_posts.get(auth.tenant_id, [])

        return {
            "status": "ok",
            "count": len(posts),
            "posts": posts[:20],  # Limit to 20
        }

    @router.post("/scheduled-posts/{post_id}/publish-now")
    async def force_publish(
        post_id: str,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Force immediate publication of scheduled post."""
        enforce_rate_limit(f"{auth.tenant_id}:publish:force", 100, 60)

        with _lock:
            posts = _scheduled_posts.get(auth.tenant_id, [])
            post = next((p for p in posts if p["id"] == post_id), None)

            if not post:
                raise HTTPException(404, "Post not found")
            if post.get("status") == "cancelled":
                raise HTTPException(status_code=409, detail="Cancelled posts cannot be published")

        publish_results: list[dict[str, Any]] = []
        for platform in post.get("platforms", [post.get("platform")]):
            if not platform:
                continue
            result = await publish_post(
                platform,
                PublishRequest(
                    content=str(post.get("content", "")),
                    media_urls=list(post.get("media_urls") or []) or None,
                    hashtags=list(post.get("hashtags") or []) or None,
                ),
                auth,
            )
            publish_results.append({"platform": platform, "result": result})

        with _lock:
            previous_status = post.get("status")
            previous_published_at = post.get("published_at")
            previous_results = post.get("published_results")
            post["status"] = "published"
            post["published_at"] = datetime.now(UTC).isoformat()
            post["published_results"] = publish_results
            try:
                _persist_scheduled_posts_or_raise()
            except HTTPException:
                post["status"] = previous_status
                if previous_published_at is None:
                    post.pop("published_at", None)
                else:
                    post["published_at"] = previous_published_at
                if previous_results is None:
                    post.pop("published_results", None)
                else:
                    post["published_results"] = previous_results
                raise

        return {"status": "published", "post_id": post_id, "results": publish_results}

    @router.post("/scheduled-posts/{post_id}/cancel")
    def cancel_scheduled_post(
        post_id: str,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Cancel a scheduled post that has not been published yet."""
        enforce_rate_limit(f"{auth.tenant_id}:schedule:cancel", 200, 60)

        with _lock:
            posts = _scheduled_posts.get(auth.tenant_id, [])
            post = next((p for p in posts if p["id"] == post_id), None)
            if post is None:
                raise HTTPException(status_code=404, detail="Post not found")

            if post.get("status") == "published":
                raise HTTPException(status_code=409, detail="Published posts cannot be cancelled")

            previous_status = post.get("status")
            previous_cancelled_at = post.get("cancelled_at")
            post["status"] = "cancelled"
            post["cancelled_at"] = datetime.now(UTC).isoformat()
            try:
                _persist_scheduled_posts_or_raise()
            except HTTPException:
                post["status"] = previous_status
                if previous_cancelled_at is None:
                    post.pop("cancelled_at", None)
                else:
                    post["cancelled_at"] = previous_cancelled_at
                raise

        return {"status": "cancelled", "post_id": post_id}

    # ─────────────────────────────────────────────────────────────────────────────
    # Analytics
    # ─────────────────────────────────────────────────────────────────────────────

    @router.get("/posts/{post_id}/metrics")
    async def get_post_metrics(
        post_id: str,
        platform: str = Query(...),
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Get performance metrics for a post."""
        enforce_rate_limit(f"{auth.tenant_id}:metrics", 600, 60)

        normalized = platform.strip().lower()
        if normalized not in _SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=422, detail="Unsupported platform requested.")

        credentials = _require_platform_credentials(normalized)
        client = _build_platform_client(normalized, credentials)
        try:
            if normalized == "twitter":
                metrics = await client.get_tweet_metrics(post_id)
            elif normalized == "facebook":
                metrics = await client.get_page_insights(post_id)
            elif normalized == "instagram":
                metrics = await client.get_post_insights(post_id)
            elif normalized == "linkedin":
                metrics = await client.get_post_metrics(post_id)
            elif normalized == "tiktok":
                metrics = await client.get_video_metrics(post_id)
            else:
                raise HTTPException(status_code=422, detail=f"Unsupported platform: {normalized}")

            if hasattr(metrics, "model_dump"):
                payload = metrics.model_dump()
            else:
                payload = dict(metrics)
            payload["platform"] = normalized
            return payload
        finally:
            await client.close()

    @router.get("/analytics/dashboard")
    def analytics_dashboard(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        """Multi-platform analytics overview."""
        enforce_rate_limit(f"{auth.tenant_id}:analytics:dashboard", 300, 60)

        return {
            "status": "ok",
            "platforms": {
                platform: {
                    "connected": _vendor_manager.has_credentials(_platform_vendor_id(platform)),
                    "vendor_id": _platform_vendor_id(platform),
                }
                for platform in _SUPPORTED_PLATFORMS
            },
            "summary": "Use /platforms/posts/{post_id}/metrics?platform=<platform> for real platform metrics.",
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # Messages & Engagement
    # ─────────────────────────────────────────────────────────────────────────────

    @router.get("/messages/inbox")
    def get_inbox(
        auth: AuthContext = Depends(require_auth),
        platform: str | None = None,
        limit: int = Query(20, ge=1, le=100),
    ) -> dict[str, Any]:
        """Get unified inbox across platforms."""
        enforce_rate_limit(f"{auth.tenant_id}:inbox:list", 600, 60)

        with _lock:
            messages = _inbox_messages.get(auth.tenant_id, [])

            if platform:
                messages = [m for m in messages if m["platform"] == platform]

        return {
            "status": "ok",
            "count": len(messages),
            "messages": messages[:limit],
        }

    @router.get("/messages/{message_id}")
    def get_message(
        message_id: str,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Get a specific message from unified inbox."""
        enforce_rate_limit(f"{auth.tenant_id}:inbox:get", 600, 60)

        with _lock:
            messages = _inbox_messages.get(auth.tenant_id, [])
            message = next((m for m in messages if m.get("id") == message_id), None)

        if message is None:
            raise HTTPException(status_code=404, detail="Message not found")

        return {
            "status": "ok",
            "message": message,
        }

    @router.post("/messages/{message_id}/reply")
    async def reply_to_message(
        message_id: str,
        request: MessageReplyRequest,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Reply to a message and persist thread history."""
        enforce_rate_limit(f"{auth.tenant_id}:messages:reply", 600, 60)

        sent_at = datetime.now(UTC).isoformat()
        reply = {
            "id": f"r_{uuid.uuid4().hex[:16]}",
            "text": request.reply_text,
            "is_internal": request.is_internal,
            "author_id": auth.tenant_id,
            "sent_at": sent_at,
        }

        with _lock:
            messages = _inbox_messages.get(auth.tenant_id, [])
            message = next((m for m in messages if m.get("id") == message_id), None)
            if message is None:
                raise HTTPException(status_code=404, detail="Message not found")

            thread = [item for item in message.get("thread", []) if isinstance(item, dict)]
            thread.append(reply)
            message["thread"] = thread
            message["last_replied_at"] = sent_at
            message["status"] = "internal_note" if request.is_internal else "replied"
            _persist_inbox_messages_or_raise()

        return {
            "status": "sent",
            "message_id": message_id,
            "reply": reply,
            "thread_size": len(thread),
        }

    @router.post("/messages/{message_id}/assign")
    def assign_message(
        message_id: str,
        request: MessageAssignRequest,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Assign a message to a team member."""
        enforce_rate_limit(f"{auth.tenant_id}:messages:assign", 600, 60)

        assigned_at = datetime.now(UTC).isoformat()
        with _lock:
            messages = _inbox_messages.get(auth.tenant_id, [])
            message = next((m for m in messages if m.get("id") == message_id), None)
            if message is None:
                raise HTTPException(status_code=404, detail="Message not found")
            message["assignee_id"] = request.assignee_id
            message["assigned_at"] = assigned_at
            _persist_inbox_messages_or_raise()

        return {
            "status": "assigned",
            "message_id": message_id,
            "assignee_id": request.assignee_id,
            "assigned_at": assigned_at,
        }

    @router.post("/messages/{message_id}/tag")
    def tag_message(
        message_id: str,
        request: MessageTagRequest,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Add tags/labels to a message."""
        enforce_rate_limit(f"{auth.tenant_id}:messages:tag", 600, 60)

        normalized_tags = [tag.strip() for tag in request.tags if tag.strip()]
        if not normalized_tags:
            raise HTTPException(status_code=422, detail="At least one non-empty tag is required")

        with _lock:
            messages = _inbox_messages.get(auth.tenant_id, [])
            message = next((m for m in messages if m.get("id") == message_id), None)
            if message is None:
                raise HTTPException(status_code=404, detail="Message not found")
            existing_tags = [str(tag) for tag in message.get("tags", [])]
            merged_tags = list(dict.fromkeys(existing_tags + normalized_tags))
            message["tags"] = merged_tags
            _persist_inbox_messages_or_raise()

        return {
            "status": "tagged",
            "message_id": message_id,
            "tags": merged_tags,
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # Health & Status
    # ─────────────────────────────────────────────────────────────────────────────

    @router.get("/health")
    def platform_health(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        """Check connection health for all platforms."""
        enforce_rate_limit(f"{auth.tenant_id}:health", 300, 60)

        return {
            "status": "ok",
            "platforms": {
                platform: {
                    "connected": _vendor_manager.has_credentials(_platform_vendor_id(platform)),
                    "last_checked": datetime.now(UTC).isoformat(),
                }
                for platform in _SUPPORTED_PLATFORMS
            },
        }

    @router.get("/accounts/verify")
    def verify_accounts(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        """Verify configured platform credentials are present and not expired."""
        enforce_rate_limit(f"{auth.tenant_id}:accounts:verify", 300, 60)

        verification: list[dict[str, Any]] = []
        now = datetime.now(UTC)
        for platform in _SUPPORTED_PLATFORMS:
            credentials = _vendor_manager.get_credentials(_platform_vendor_id(platform))
            if credentials is None:
                verification.append({"platform": platform, "connected": False, "valid": False, "reason": "missing_credentials"})
                continue

            expired = bool(credentials.expires_at and credentials.expires_at <= now)
            verification.append(
                {
                    "platform": platform,
                    "connected": True,
                    "valid": not expired,
                    "has_refresh_token": bool(credentials.refresh_token),
                    "expires_at": credentials.expires_at.isoformat() if credentials.expires_at else None,
                    "reason": "expired_token" if expired else "ok",
                }
            )

        return {
            "status": "ok",
            "accounts": verification,
        }

    @router.get("/{platform}/analytics/summary")
    async def platform_analytics_summary(
        platform: str,
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Return a platform-level summary from locally tracked scheduled posts."""
        enforce_rate_limit(f"{auth.tenant_id}:analytics:summary", 300, 60)

        normalized = platform.strip().lower()
        if normalized not in _SUPPORTED_PLATFORMS:
            raise HTTPException(status_code=422, detail="Unsupported platform requested.")

        with _lock:
            posts = _scheduled_posts.get(auth.tenant_id, [])
            platform_posts = [post for post in posts if post.get("platform") == normalized]

        status_counts: dict[str, int] = {}
        for post in platform_posts:
            status = str(post.get("status", "unknown"))
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "status": "ok",
            "platform": normalized,
            "total_posts": len(platform_posts),
            "status_breakdown": status_counts,
        }

    @router.post("/analytics/compare")
    def compare_analytics(
        post_ids: list[str],
        auth: AuthContext = Depends(require_auth),
    ) -> dict[str, Any]:
        """Compare locally tracked scheduled-post states across selected post IDs."""
        enforce_rate_limit(f"{auth.tenant_id}:analytics:compare", 300, 60)

        if not post_ids:
            raise HTTPException(status_code=422, detail="post_ids cannot be empty")

        with _lock:
            posts = _scheduled_posts.get(auth.tenant_id, [])
            selected = [post for post in posts if str(post.get("id")) in set(post_ids)]

        comparison = [
            {
                "post_id": str(post.get("id")),
                "platform": post.get("platform"),
                "status": post.get("status"),
                "scheduled_at": post.get("scheduled_at"),
                "published_at": post.get("published_at"),
            }
            for post in selected
        ]

        return {
            "status": "ok",
            "requested": len(post_ids),
            "found": len(selected),
            "comparison": comparison,
        }

    # ─────────────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────────────

    return router


# ─────────────────────────────────────────────────────────────────────────────────
# Integration with main app
# ─────────────────────────────────────────────────────────────────────────────────

# In app/__init__.py or main router file, add:
# from .routers.platform_integration import create_platform_integration_router
# platform_router = create_platform_integration_router(enforce_rate_limit=...)
# app.include_router(platform_router)
