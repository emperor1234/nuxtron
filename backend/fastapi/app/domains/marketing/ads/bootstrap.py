"""Fail-closed compatibility router for the retired Ads Control Tower API."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any, NoReturn
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from ....deps import AuthContext, require_auth

AdsAuth = Annotated[AuthContext, Depends(require_auth)]
ADS_CONTROL_TOWER_UNAVAILABLE_MESSAGE = (
    "Ads Control Tower is unavailable until real provider OAuth exchange, "
    "tenant-scoped durable campaign storage, and verified provider reporting are implemented."
)
ADS_CONTROL_TOWER_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": ADS_CONTROL_TOWER_UNAVAILABLE_MESSAGE,
}
ADS_CONTROL_TOWER_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
ADS_CONTROL_TOWER_RESPONSES = {
    501: {
        "description": ADS_CONTROL_TOWER_UNAVAILABLE_MESSAGE,
        "content": {"application/json": {"example": {"detail": ADS_CONTROL_TOWER_UNAVAILABLE_DETAIL}}},
    }
}


def _platform_oauth_url(platform: str) -> str:
    """Return the documented provider authorization endpoint, never a token."""
    urls = {
        "google_ads": "https://accounts.google.com/o/oauth2/v2/auth",
        "microsoft_ads": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        "amazon_ads": "https://www.amazon.com/ap/oa",
        "apple_search_ads": "https://appleid.apple.com/auth/authorize",
        "youtube_ads": "https://accounts.google.com/o/oauth2/v2/auth",
    }
    return urls.get(platform, "https://example.com/oauth")


def _seed_connector(tenant_id: str, platform: str) -> dict[str, Any]:
    """Build a disconnected UI projection; no provider credential is fabricated."""
    now = datetime.now(UTC).isoformat()
    return {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "platform": platform,
        "platform_description": "",
        "platform_accent": "#3b82f6",
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
        "created_at": now,
        "updated_at": now,
    }


def create_ads_control_tower_router(
    *,
    enforce_rate_limit: Callable[..., None],
    notifications_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
    connectors_memory: list[dict[str, Any]] | None = None,
    campaigns_memory: list[dict[str, Any]] | None = None,
    scheduler_memory: list[dict[str, Any]] | None = None,
    forecast_memory: list[dict[str, Any]] | None = None,
) -> APIRouter:
    """Keep old paths authenticated, but never return simulated business success."""
    # The parameters remain for composition-root compatibility only. None of these
    # in-memory stores or provider callbacks can support a trustworthy customer API.
    _ = (
        enforce_rate_limit,
        notifications_memory,
        audit_log_memory,
        connectors_memory,
        campaigns_memory,
        scheduler_memory,
        forecast_memory,
    )
    router = APIRouter(prefix="/ads-control-tower", tags=["ads-control-tower"])

    def unavailable(legacy_path: str, _auth: AdsAuth) -> NoReturn:
        """Fail closed before any fake OAuth, campaign mutation, or metric path."""
        _ = legacy_path
        raise HTTPException(
            status_code=501,
            detail=ADS_CONTROL_TOWER_UNAVAILABLE_DETAIL,
            headers={"Cache-Control": "no-store"},
        )

    for method in ADS_CONTROL_TOWER_METHODS:
        router.add_api_route(
            "/{legacy_path:path}",
            unavailable,
            methods=[method],
            name=f"ads_control_tower_unavailable_{method.lower()}",
            operation_id=f"ads_control_tower_unavailable_{method.lower()}",
            status_code=501,
            response_model=None,
            responses=ADS_CONTROL_TOWER_RESPONSES,
        )

    return router
