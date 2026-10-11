from __future__ import annotations

"Tenant credentials, scheduling validation, and social provider clients."
from .....integrations.vendor_manager import VendorCredentials
from .....platform_clients.facebook_client import FacebookGraphClient
from .....platform_clients.instagram_client import InstagramGraphClient
from .....platform_clients.linkedin_client import LinkedInGraphClient
from .....platform_clients.tiktok_client import TikTokBusinessClient
from .....platform_clients.twitter_client import TwitterV2Client
from ..constants import _vendor_manager
from ..schemas import SchedulePostRequest
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from typing import Any
from ..configuration import _is_production_env


def _platform_vendor_id(platform: str, tenant_id: str | None = None) -> str:
    normalized = platform.strip().lower()
    vendor_id = {
        "twitter": "twitter_api",
        "facebook": "meta_graph_api",
        "instagram": "meta_graph_api",
        "linkedin": "linkedin_api",
        "tiktok": "tiktok_api",
    }.get(normalized, f"{normalized}_api")
    if not tenant_id:
        return vendor_id
    if not _is_production_env():
        return vendor_id
    return _vendor_manager.ensure_tenant_vendor(tenant_id, vendor_id)


def _require_platform_credentials(platform: str, tenant_id: str) -> VendorCredentials:
    vendor_id = _platform_vendor_id(platform, tenant_id)
    credentials = _vendor_manager.get_credentials(vendor_id)
    if credentials is None:
        raise HTTPException(status_code=503, detail=f"{platform} credentials are not configured for this tenant.")
    return credentials


def _validate_schedule_request(request: SchedulePostRequest, platforms: list[str], tenant_id: str) -> None:
    if request.scheduled_at <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="scheduled_at must be in the future")
    for platform in platforms:
        _require_platform_credentials(platform, tenant_id)
        if platform == "instagram" and (not request.media_urls):
            raise HTTPException(status_code=422, detail="Instagram scheduling requires media_urls.")
        if platform == "tiktok" and (not request.media_urls):
            raise HTTPException(status_code=422, detail="TikTok scheduling requires a video URL.")


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
        ig_user_id = (credentials.additional_config or {}).get("instagram_account_id") or (
            credentials.additional_config or {}
        ).get("ig_user_id")
        if not ig_user_id:
            raise HTTPException(status_code=503, detail="instagram account id is not configured.")
        return InstagramGraphClient(access_token=access_token, ig_user_id=ig_user_id)
    if normalized == "linkedin":
        actor_urn = (credentials.additional_config or {}).get("actor_urn") or (credentials.additional_config or {}).get(
            "user_urn"
        )
        if not actor_urn:
            user_id = (credentials.additional_config or {}).get("user_id")
            if user_id:
                actor_urn = f"urn:li:person:{user_id}"
        if not actor_urn:
            raise HTTPException(status_code=503, detail="linkedin actor URN is not configured.")
        return LinkedInGraphClient(access_token=access_token, actor_urn=actor_urn)
    if normalized == "tiktok":
        advertiser_id = (credentials.additional_config or {}).get("advertiser_id") or (
            credentials.additional_config or {}
        ).get("account_id")
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
            import asyncio

            asyncio.create_task(result)
    except Exception:
        pass
