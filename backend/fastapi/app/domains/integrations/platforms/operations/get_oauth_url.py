"""Integrations/Platforms use cases: get oauth url."""

from __future__ import annotations
from ..services import clients as provider_clients
from .....deps import AuthContext
from .....deps import require_auth
from .....integrations.vendor_manager import VendorCredentials
from .....integrations.vendor_manager import VendorType
from .....platform_clients.facebook_client import PagePostCreateRequest
from .....platform_clients.instagram_client import CarouselPublishRequest
from .....platform_clients.instagram_client import ReelPublishRequest
from .....platform_clients.instagram_client import StoryPublishRequest
from .....platform_clients.linkedin_client import PostRequest
from .....platform_clients.tiktok_client import VideoUploadRequest
from .....platform_clients.twitter_client import TweetCreateRequest
from ..constants import _SUPPORTED_PLATFORMS
from ..constants import _vendor_manager
from ..runtime import ContextRuntime
from ..schemas import OAuthCallbackRequest
from ..schemas import PublishRequest
from ..schemas import SchedulePostRequest
from ..services.oauth import _decode_oauth_state
from ..services.oauth import _encode_oauth_state
from ..services.oauth import _exchange_oauth_code
from ..configuration import _is_production_env
from ..services.oauth import _oauth_state_secret
from ..services.clients import _platform_vendor_id
from ..services.clients import _require_platform_credentials
from .schedule_post import execute_schedule_post
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from typing import Any
from urllib.parse import urlencode
import base64
import hashlib
import os
import secrets
import time


def execute_get_oauth_url(
    runtime: ContextRuntime, platform: str, redirect_uri: str = Query(...), auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """
    Get OAuth authorization URL for platform.

    Returns: authorization_url to redirect user to
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:oauth:authorize", 100, 60)
    if platform not in ("twitter", "facebook", "instagram", "linkedin", "tiktok"):
        raise HTTPException(400, "Unsupported platform")
    if _is_production_env() and (not _oauth_state_secret()):
        raise HTTPException(status_code=503, detail="OAuth state signing is not configured.")
    code_verifier = secrets.token_urlsafe(48)
    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).rstrip(b"=").decode()
    state = _encode_oauth_state(
        tenant_id=auth.tenant_id,
        platform=platform,
        redirect_uri=redirect_uri,
        expires_at=int(time.time()) + 600,
        code_verifier=code_verifier,
    )
    oauth_urls = {
        "twitter": f"https://twitter.com/i/oauth2/authorize?client_id={os.getenv('TWITTER_CLIENT_ID')}&{urlencode({'redirect_uri': redirect_uri, 'state': state, 'code_challenge': code_challenge, 'code_challenge_method': 'S256'})}&response_type=code&scope=tweet.read%20tweet.write%20users.read",
        "facebook": f"https://www.facebook.com/v18.0/dialog/oauth?client_id={os.getenv('FACEBOOK_APP_ID')}&{urlencode({'redirect_uri': redirect_uri, 'state': state})}&scope=pages_manage_posts,pages_manage_metadata,pages_read_engagement",
        "instagram": f"https://www.facebook.com/v18.0/dialog/oauth?client_id={os.getenv('FACEBOOK_APP_ID')}&{urlencode({'redirect_uri': redirect_uri, 'state': state})}&scope=instagram_business_basic,instagram_business_content_publish",
        "linkedin": f"https://www.linkedin.com/oauth/v2/authorization?client_id={os.getenv('LINKEDIN_CLIENT_ID')}&{urlencode({'redirect_uri': redirect_uri, 'state': state})}&response_type=code&scope=w_member_social",
        "tiktok": f"https://open.tiktok.com/auth/authorize?client_key={os.getenv('TIKTOK_CLIENT_ID')}&{urlencode({'redirect_uri': redirect_uri, 'state': state})}&scope=video.list,video.upload",
    }
    return {
        "platform": platform,
        "authorization_url": oauth_urls.get(platform, ""),
        "state": state,
        "scopes_required": {
            "twitter": ["tweet.read", "tweet.write", "users.read"],
            "facebook": ["pages_manage_posts"],
            "instagram": ["instagram_business_content_publish"],
            "linkedin": ["w_member_social"],
            "tiktok": ["video.list", "video.upload"],
        }.get(platform, []),
    }


def execute_list_accounts(runtime: ContextRuntime, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """List connected platform accounts."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:accounts:list", 300, 60)
    accounts = []
    for platform in _SUPPORTED_PLATFORMS:
        vendor_id = _platform_vendor_id(platform, auth.tenant_id)
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
    return {"status": "ok", "accounts": accounts}


def execute_oauth_callback(
    runtime: ContextRuntime, platform: str, payload: OAuthCallbackRequest, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Persist OAuth callback tokens for a platform account."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:oauth:callback", 100, 60)
    normalized = platform.strip().lower()
    if normalized not in _SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=422, detail="Unsupported platform requested.")
    redirect_uri = (payload.redirect_uri or "").strip()
    refresh_token = payload.refresh_token
    expires_at = payload.expires_at
    if _is_production_env():
        if not payload.code or not payload.state or (not redirect_uri):
            raise HTTPException(
                status_code=400, detail="Production OAuth callbacks require code, state, and redirect_uri."
            )
        state_claims = _decode_oauth_state(
            payload.state, tenant_id=auth.tenant_id, platform=normalized, redirect_uri=redirect_uri
        )
        token_data = _exchange_oauth_code(
            normalized, payload.code.strip(), redirect_uri, str(state_claims.get("code_verifier", ""))
        )
        access_token = str(token_data.get("access_token", "")).strip()
        refresh_token = str(token_data.get("refresh_token", "") or refresh_token or "").strip() or None
        expires_in = int(token_data.get("expires_in", 3600) or 3600)
        expires_at = expires_at or (datetime.now(UTC) + timedelta(seconds=max(60, expires_in))).replace(microsecond=0)
    else:
        access_token = (payload.access_token or "").strip()
    if not access_token:
        raise HTTPException(status_code=422, detail="access_token is required to persist platform credentials.")
    vendor_id = _platform_vendor_id(normalized, auth.tenant_id)
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
        refresh_token=refresh_token or (existing.refresh_token if existing else None),
        expires_at=expires_at or (existing.expires_at if existing else None),
        additional_config=merged_config,
    )
    _vendor_manager.store_credentials(vendor_id, credentials)
    return {
        "status": "connected",
        "platform": normalized,
        "vendor_id": vendor_id,
        "has_refresh_token": bool(credentials.refresh_token),
    }


def execute_disconnect_account(
    runtime: ContextRuntime, account_id: str, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Disconnect a platform account by platform id."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:accounts:disconnect", 100, 60)
    platform = account_id.strip().lower()
    if platform not in _SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=404, detail="Account not found")
    vendor_id = _platform_vendor_id(platform, auth.tenant_id)
    disconnected = _vendor_manager.revoke_credentials(vendor_id)
    if not disconnected:
        raise HTTPException(status_code=404, detail="Account not connected")
    return {"status": "disconnected", "account_id": platform, "vendor_id": vendor_id}


def execute_refresh_account_token(
    runtime: ContextRuntime, account_id: str, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """Refresh account token metadata when a refresh token is available."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:accounts:refresh", 100, 60)
    platform = account_id.strip().lower()
    if platform not in _SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=404, detail="Account not found")
    vendor_id = _platform_vendor_id(platform, auth.tenant_id)
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


async def execute_publish_post(
    runtime: ContextRuntime, platform: str, request: PublishRequest, auth: AuthContext = Depends(require_auth)
) -> dict[str, Any]:
    """
    Publish content to platform immediately.

    Platforms: twitter, facebook, instagram, linkedin, tiktok
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:publish", 600, 60)
    if platform not in _SUPPORTED_PLATFORMS:
        raise HTTPException(400, "Unsupported platform")
    if request.scheduled_at and request.scheduled_at > datetime.now(UTC):
        return await execute_schedule_post(
            runtime,
            SchedulePostRequest(
                content=request.content,
                media_urls=request.media_urls,
                platforms=[platform],
                scheduled_at=request.scheduled_at,
                hashtags=request.hashtags,
            ),
            auth,
        )
    credentials = _require_platform_credentials(platform, auth.tenant_id)
    client = provider_clients._build_platform_client(platform, credentials)
    try:
        if platform == "twitter":
            result = await client.create_tweet(
                TweetCreateRequest(text=request.content, media_ids=None, in_reply_to_tweet_id=None)
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
                    message=request.content, link=None, picture=request.media_urls[0] if request.media_urls else None
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
                    CarouselPublishRequest(media_urls=request.media_urls, captions=None, main_caption=request.content)
                )
            elif request.media_urls[0].lower().endswith((".mp4", ".mov", ".avi", ".webm")):
                result = await client.publish_reel(
                    ReelPublishRequest(video_url=request.media_urls[0], caption=request.content)
                )
            else:
                result = await client.publish_story(
                    StoryPublishRequest(media_url=request.media_urls[0], media_type="IMAGE", sticker_type=None)
                )
            return {
                "status": "published",
                "platform": platform,
                "post_id": result.get("id") or result.get("post_id"),
                "provider_response": result,
                "published_at": datetime.now(UTC).isoformat(),
            }
        if platform == "linkedin":
            result = await client.create_post(PostRequest(text=request.content))
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
