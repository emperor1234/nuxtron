"""Marketing/Ads use cases: append notification."""

from __future__ import annotations
from .....integrations.vendor_manager import VendorCredentials
from .....integrations.vendor_manager import VendorType
from ..constants import AuthDep
from ..constants import SUPPORTED_PLATFORMS
from ..runtime import ContextRuntime
from ..schemas import CampaignCreateRequest
from ..schemas import CampaignMetricsPatchRequest
from ..schemas import CampaignPublishRequest
from ..schemas import CampaignUpdateRequest
from ..schemas import ConnectorCallbackRequest
from ..services.now_iso import _now_iso
from ..services.now_iso import _platform_oauth_url
from ..services.now_iso import _platform_vendor_id
from ..services.now_iso import _seed_connector
from fastapi import HTTPException
from fastapi import Query
from typing import Any
import hashlib
import secrets
import uuid


def helper_append_notification(
    runtime: ContextRuntime, tenant_id: str, title: str, message: str, priority: str = "info"
) -> None:
    with runtime.lock:
        runtime.notifications_memory.append(
            {
                "id": len(runtime.notifications_memory) + 1,
                "tenant_id": tenant_id,
                "title": title,
                "message": message,
                "category": "ads_control_tower",
                "priority": priority,
                "is_read": False,
                "source": "ads-control-tower",
                "created_at": _now_iso(),
            }
        )


def helper_log_audit(runtime: ContextRuntime, tenant_id: str, action: str, payload: dict[str, Any]) -> None:
    with runtime.lock:
        runtime.audit_log_memory.append(
            {
                "id": len(runtime.audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "event": action,
                "payload": payload,
                "source": "ads-control-tower",
                "created_at": _now_iso(),
            }
        )


def helper_tenant_connectors(runtime: ContextRuntime, tenant_id: str) -> list[dict[str, Any]]:
    return [item for item in runtime._connectors if item.get("tenant_id") == tenant_id]


def helper_tenant_campaigns(runtime: ContextRuntime, tenant_id: str) -> list[dict[str, Any]]:
    return [item for item in runtime._campaigns if item.get("tenant_id") == tenant_id]


def helper_get_campaign(runtime: ContextRuntime, tenant_id: str, campaign_id: str) -> dict[str, Any] | None:
    return next(
        (item for item in runtime._campaigns if item.get("tenant_id") == tenant_id and item.get("id") == campaign_id),
        None,
    )


def helper_ensure_connector(runtime: ContextRuntime, tenant_id: str, platform: str) -> dict[str, Any]:
    existing = next(
        (
            item
            for item in runtime._connectors
            if item.get("tenant_id") == tenant_id and item.get("platform") == platform
        ),
        None,
    )
    if existing is not None:
        return existing
    seeded = _seed_connector(tenant_id, platform)
    runtime._connectors.append(seeded)
    return seeded


async def execute_list_connectors(runtime: ContextRuntime, auth: AuthDep):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:connectors", limit=80, window_seconds=60)
    with runtime.lock:
        connectors = [
            helper_ensure_connector(runtime, auth.tenant_id, platform) for platform in sorted(SUPPORTED_PLATFORMS)
        ]
    return {"status": "ok", "tenant_id": auth.tenant_id, "connectors": connectors}


async def execute_oauth_start(runtime: ContextRuntime, platform: str, auth: AuthDep):
    platform_key = platform.strip().lower()
    if platform_key not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:{platform_key}:oauth:start", limit=20, window_seconds=60)
    state = secrets.token_urlsafe(24)
    with runtime.lock:
        connector = helper_ensure_connector(runtime, auth.tenant_id, platform_key)
        connector["oauth_state"] = state
        connector["oauth_started_at"] = _now_iso()
        connector["status"] = "auth_pending"
        connector["updated_at"] = _now_iso()
    auth_url = f"{_platform_oauth_url(platform_key)}?client_id=configure-me&response_type=code&redirect_uri=configure-me&scope=ads.read+ads.write&state={state}"
    helper_log_audit(runtime, auth.tenant_id, "ads_oauth_start", {"platform": platform_key})
    return {
        "platform": platform_key,
        "state": state,
        "authorization_url": auth_url,
        "callback_path": f"/ads-control-tower/connectors/{platform_key}/oauth/callback",
    }


async def execute_oauth_callback(runtime: ContextRuntime, platform: str, body: ConnectorCallbackRequest, auth: AuthDep):
    platform_key = platform.strip().lower()
    if platform_key not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:{platform_key}:oauth:callback", limit=30, window_seconds=60)
    with runtime.lock:
        connector = helper_ensure_connector(runtime, auth.tenant_id, platform_key)
        expected_state = str(connector.get("oauth_state", ""))
        if not expected_state or expected_state != body.state:
            raise HTTPException(status_code=400, detail="OAuth state mismatch.")
        token_fingerprint = hashlib.sha256(body.code.encode("utf-8")).hexdigest()[:16]
        connector.update(
            {
                "connected": True,
                "status": "connected",
                "account_name": body.account_name,
                "account_id": body.account_id or f"{platform_key}-acct-{token_fingerprint[:8]}",
                "scopes": body.scopes,
                "token_fingerprint": token_fingerprint,
                "refresh_token_present": True,
                "credit_total": float(body.credit_total),
                "credit_remaining": float(body.credit_remaining),
                "credit_currency": body.credit_currency.upper(),
                "last_sync_at": _now_iso(),
                "updated_at": _now_iso(),
            }
        )
    vendor_id = _platform_vendor_id(platform_key)
    if vendor_id:
        runtime.vendor_manager.store_credentials(
            vendor_id,
            VendorCredentials(
                vendor_type=VendorType.ANALYTICS,
                platform=platform_key,
                api_key=body.code,
                access_token=body.code,
                refresh_token="present",
                additional_config={
                    "tenant_id": auth.tenant_id,
                    "account_id": connector.get("account_id", ""),
                    "account_name": connector.get("account_name", ""),
                    "scopes": list(body.scopes),
                },
            ),
        )
    helper_append_notification(
        runtime, auth.tenant_id, f"{platform_key} connected", f"OAuth connected for {body.account_name}", "success"
    )
    helper_log_audit(
        runtime,
        auth.tenant_id,
        "ads_oauth_connected",
        {"platform": platform_key, "account_id": connector["account_id"]},
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "connector": connector}


async def execute_connector_credentials_status(runtime: ContextRuntime, platform: str, auth: AuthDep):
    platform_key = platform.strip().lower()
    if platform_key not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")
    connector = helper_ensure_connector(runtime, auth.tenant_id, platform_key)
    vendor_id = _platform_vendor_id(platform_key)
    has_credentials = bool(vendor_id and runtime.vendor_manager.has_credentials(vendor_id))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "platform": platform_key,
        "connector_connected": bool(connector.get("connected")),
        "vendor_credentials_configured": has_credentials,
    }


async def execute_disconnect_connector(runtime: ContextRuntime, platform: str, auth: AuthDep):
    platform_key = platform.strip().lower()
    if platform_key not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=404, detail=f"Unsupported platform: {platform}")
    with runtime.lock:
        connector = helper_ensure_connector(runtime, auth.tenant_id, platform_key)
        connector.update(
            {
                "connected": False,
                "status": "disconnected",
                "token_fingerprint": None,
                "refresh_token_present": False,
                "updated_at": _now_iso(),
            }
        )
    vendor_id = _platform_vendor_id(platform_key)
    if vendor_id:
        runtime.vendor_manager.revoke_credentials(vendor_id)
    helper_append_notification(
        runtime, auth.tenant_id, f"{platform_key} disconnected", "Connector disconnected from control tower.", "warning"
    )
    helper_log_audit(runtime, auth.tenant_id, "ads_oauth_disconnected", {"platform": platform_key})
    return {"status": "ok", "tenant_id": auth.tenant_id, "connector": connector}


async def execute_get_credit_balances(runtime: ContextRuntime, auth: AuthDep):
    connectors = helper_tenant_connectors(runtime, auth.tenant_id)
    balances = [
        {
            "platform": item.get("platform"),
            "account_name": item.get("account_name"),
            "account_id": item.get("account_id"),
            "currency": item.get("credit_currency", "USD"),
            "credit_total": float(item.get("credit_total", 0.0) or 0.0),
            "credit_remaining": float(item.get("credit_remaining", 0.0) or 0.0),
            "connected": bool(item.get("connected")),
        }
        for item in connectors
    ]
    total = sum((float(item["credit_total"]) for item in balances))
    remaining = sum((float(item["credit_remaining"]) for item in balances))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "accounts": balances,
        "portfolio_credit_total": round(total, 2),
        "portfolio_credit_remaining": round(remaining, 2),
    }


async def execute_create_campaign(runtime: ContextRuntime, payload: CampaignCreateRequest, auth: AuthDep):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:campaigns:create", limit=50, window_seconds=60)
    connector = helper_ensure_connector(runtime, auth.tenant_id, payload.platform)
    if not connector.get("connected"):
        raise HTTPException(status_code=422, detail=f"{payload.platform} is not connected. Complete OAuth first.")
    created_at = _now_iso()
    campaign_id = str(uuid.uuid4())
    metrics = {
        "likes": 0,
        "description_views": 0,
        "shares": 0,
        "comments": 0,
        "clicks": 0,
        "impressions": 0,
        "conversions": 0,
        "spend": 0.0,
        "revenue": 0.0,
        "roi_pct": 0.0,
        "success_ratio_pct": 0.0,
        "updated_at": created_at,
    }
    item = {
        "id": campaign_id,
        "tenant_id": auth.tenant_id,
        "platform": payload.platform,
        "campaign_name": payload.campaign_name,
        "objective": payload.objective,
        "status": payload.status,
        "budget_daily": float(payload.budget_daily),
        "budget_total": float(payload.budget_total),
        "currency": payload.currency.upper(),
        "keywords": [keyword.model_dump() for keyword in payload.keywords],
        "creative": payload.creative.model_dump(),
        "schedule": payload.schedule.model_dump(),
        "connected_accounts": payload.connected_accounts or [str(connector.get("account_id", ""))],
        "metrics": metrics,
        "created_at": created_at,
        "updated_at": created_at,
    }
    with runtime.lock:
        runtime._campaigns.append(item)
        runtime._scheduler.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": auth.tenant_id,
                "campaign_id": campaign_id,
                "action": "initial_schedule",
                "payload": payload.schedule.model_dump(),
                "created_at": created_at,
            }
        )
    helper_append_notification(
        runtime,
        auth.tenant_id,
        "Campaign created",
        f"{payload.campaign_name} created for {payload.platform}.",
        "success",
    )
    helper_log_audit(
        runtime, auth.tenant_id, "ads_campaign_created", {"campaign_id": campaign_id, "platform": payload.platform}
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": item}


async def execute_list_campaigns(
    runtime: ContextRuntime,
    auth: AuthDep,
    platform: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    campaigns = helper_tenant_campaigns(runtime, auth.tenant_id)
    if platform:
        campaigns = [item for item in campaigns if str(item.get("platform")) == platform]
    if status:
        campaigns = [item for item in campaigns if str(item.get("status")) == status]
    return {"status": "ok", "tenant_id": auth.tenant_id, "total": len(campaigns), "campaigns": campaigns}


async def execute_get_campaign(runtime: ContextRuntime, campaign_id: str, auth: AuthDep):
    campaign = helper_get_campaign(runtime, auth.tenant_id, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}


async def execute_update_campaign(
    runtime: ContextRuntime, campaign_id: str, payload: CampaignUpdateRequest, auth: AuthDep
):
    campaign = helper_get_campaign(runtime, auth.tenant_id, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    patch = payload.model_dump(exclude_none=True)
    with runtime.lock:
        if "keywords" in patch and isinstance(patch["keywords"], list):
            patch["keywords"] = [
                item.model_dump() if hasattr(item, "model_dump") else item for item in patch["keywords"]
            ]
        if "creative" in patch and hasattr(patch["creative"], "model_dump"):
            patch["creative"] = patch["creative"].model_dump()
        if "schedule" in patch and hasattr(patch["schedule"], "model_dump"):
            patch["schedule"] = patch["schedule"].model_dump()
        campaign.update(patch)
        campaign["updated_at"] = _now_iso()
    helper_append_notification(
        runtime, auth.tenant_id, "Campaign updated", f"{campaign.get('campaign_name', 'Campaign')} updated."
    )
    helper_log_audit(
        runtime, auth.tenant_id, "ads_campaign_updated", {"campaign_id": campaign_id, "fields": list(patch.keys())}
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}


async def execute_delete_campaign(runtime: ContextRuntime, campaign_id: str, auth: AuthDep):
    with runtime.lock:
        idx = next(
            (
                i
                for i, item in enumerate(runtime._campaigns)
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == campaign_id
            ),
            None,
        )
        if idx is None:
            raise HTTPException(status_code=404, detail="Campaign not found.")
        removed = runtime._campaigns.pop(idx)
    helper_append_notification(
        runtime, auth.tenant_id, "Campaign deleted", f"{removed.get('campaign_name', 'Campaign')} deleted.", "warning"
    )
    helper_log_audit(runtime, auth.tenant_id, "ads_campaign_deleted", {"campaign_id": campaign_id})
    return {"status": "ok", "tenant_id": auth.tenant_id, "deleted": campaign_id}


async def execute_publish_campaign(
    runtime: ContextRuntime, campaign_id: str, payload: CampaignPublishRequest, auth: AuthDep
):
    campaign = helper_get_campaign(runtime, auth.tenant_id, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    platform = str(campaign.get("platform"))
    connector = helper_ensure_connector(runtime, auth.tenant_id, platform)
    if not connector.get("connected"):
        raise HTTPException(status_code=422, detail=f"{platform} is not connected. Complete OAuth first.")
    with runtime.lock:
        campaign["status"] = "active"
        campaign["published_at"] = _now_iso()
        campaign["updated_at"] = _now_iso()
        campaign["publish_mode"] = "all_accounts" if payload.publish_all_connected_accounts else "primary_account"
    helper_append_notification(
        runtime,
        auth.tenant_id,
        "Campaign published",
        f"{campaign.get('campaign_name', 'Campaign')} published to {platform}.",
        "success",
    )
    helper_log_audit(
        runtime, auth.tenant_id, "ads_campaign_published", {"campaign_id": campaign_id, "platform": platform}
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}


async def execute_patch_metrics(
    runtime: ContextRuntime, campaign_id: str, payload: CampaignMetricsPatchRequest, auth: AuthDep
):
    campaign = helper_get_campaign(runtime, auth.tenant_id, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    with runtime.lock:
        metrics = dict(campaign.get("metrics") or {})
        metrics["likes"] = int(payload.likes)
        metrics["description_views"] = int(payload.impressions)
        metrics["shares"] = int(payload.shares)
        metrics["comments"] = int(payload.comments)
        metrics["clicks"] = int(payload.clicks)
        metrics["impressions"] = int(payload.impressions)
        metrics["conversions"] = int(payload.conversions)
        metrics["spend"] = float(payload.spend)
        metrics["revenue"] = float(payload.revenue)
        roi = (metrics["revenue"] - metrics["spend"]) / metrics["spend"] * 100.0 if metrics["spend"] > 0 else 0.0
        success_ratio = metrics["conversions"] / metrics["clicks"] * 100.0 if metrics["clicks"] > 0 else 0.0
        metrics["roi_pct"] = round(roi, 2)
        metrics["success_ratio_pct"] = round(success_ratio, 2)
        metrics["updated_at"] = _now_iso()
        campaign["metrics"] = metrics
        campaign["updated_at"] = _now_iso()
    helper_append_notification(
        runtime,
        auth.tenant_id,
        "Campaign metrics synced",
        f"{campaign.get('campaign_name', 'Campaign')} metrics updated.",
    )
    helper_log_audit(runtime, auth.tenant_id, "ads_metrics_updated", {"campaign_id": campaign_id})
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}
