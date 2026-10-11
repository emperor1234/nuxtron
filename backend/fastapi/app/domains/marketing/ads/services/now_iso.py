"""Marketing/Ads service: now iso."""

from __future__ import annotations
from ..constants import PLATFORM_META
from datetime import UTC
from datetime import datetime
from typing import Any
import uuid


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _platform_oauth_url(platform: str) -> str:
    urls = {
        "google_ads": "https://accounts.google.com/o/oauth2/v2/auth",
        "microsoft_ads": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "amazon_ads": "https://www.amazon.com/ap/oa",
        "apple_search_ads": "https://appleid.apple.com/auth/authorize",
        "youtube_ads": "https://accounts.google.com/o/oauth2/v2/auth",
    }
    return urls.get(platform, "https://example.com/oauth")


def _platform_vendor_id(platform: str) -> str | None:
    mapping = {
        "google_ads": "google_ads_api",
        "microsoft_ads": "microsoft_ads_api",
        "amazon_ads": "amazon_ads_api",
        "apple_search_ads": "apple_search_ads_api",
        "youtube_ads": "youtube_ads_api",
    }
    return mapping.get(platform)


def _seed_connector(tenant_id: str, platform: str) -> dict[str, Any]:
    meta = PLATFORM_META.get(platform, {})
    return {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "platform": platform,
        "platform_description": meta.get("description", ""),
        "platform_accent": meta.get("accent", "#3b82f6"),
        "status": "disconnected",
        "connected": False,
        "account_name": "",
        "account_id": "",
        "scopes": [],
        "token_fingerprint": None,
        "refresh_token_present": False,
        "credit_currency": "USD",
        "credit_total": 0.0,
        "credit_remaining": 0.0,
        "last_sync_at": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
