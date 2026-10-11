"""Social use cases: request ugc rights."""

from ....domains.social.persistence import _SocialWorkspaceState
from ..services import brand as ugc_provider
from ....domains.social.persistence import _sw_audit
from ..constants import AuthDep
from ..constants import JSON_CONTENT_TYPE
from ..constants import UGC_ASSET_NOT_FOUND
from ..services.workspace import _sw_http_error
from datetime import UTC
from datetime import datetime
from fastapi import APIRouter
from fastapi import HTTPException
from typing import Any
import os


def operation_request_ugc_rights(
    st: _SocialWorkspaceState, router: APIRouter, asset_id: int, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    """Request rights from UGC creator (production vendor integration)."""
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ugc:request-rights", 120, 60)
    with st.lock:
        asset = next(
            (item for item in st.ugc_assets if item.get("tenant_id") == auth.tenant_id and item.get("id") == asset_id),
            None,
        )
        if asset is None:
            raise _sw_http_error(status_code=404, detail=UGC_ASSET_NOT_FOUND)
        ugc_rights_endpoint = os.getenv("UGC_RIGHTS_REQUEST_ENDPOINT", "").strip()
        ugc_api_key = os.getenv("UGC_DISCOVERY_API_KEY", "").strip()
        if not ugc_rights_endpoint or not ugc_api_key:
            raise _sw_http_error(status_code=503, detail="UGC rights request service not configured")
        try:
            headers = {"Authorization": f"Bearer {ugc_api_key}", "Content-Type": JSON_CONTENT_TYPE}
            request_payload = {
                "author_handle": asset.get("author"),
                "platform": asset.get("network"),
                "media_id": asset.get("id"),
                "request_message": payload.get("message", "We would like to use your content in our marketing"),
            }
            result = ugc_provider._ugc_http_json_request("POST", ugc_rights_endpoint, headers, request_payload)
            asset["rights_request_sent"] = True
            asset["rights_request_sent_at"] = datetime.now(UTC).isoformat()
            asset["rights_status"] = "pending"
            sent_at = asset["rights_request_sent_at"]
        except HTTPException:
            raise
        except Exception as exc:
            raise _sw_http_error(status_code=502, detail=f"Rights request failed: {str(exc)}")
    _sw_audit(st, auth.tenant_id, "social_ugc_rights_requested", asset_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "asset_id": asset_id,
        "request_id": result.get("request_id"),
        "sent_at": sent_at,
        "telemetry_event": "social.ugc.rights_requested",
    }


def operation_batch_approve_ugc(
    st: _SocialWorkspaceState, router: APIRouter, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    """Batch approve multiple UGC assets."""
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ugc:batch-approve", 60, 60)
    asset_ids = payload.get("asset_ids", [])
    if not asset_ids or len(asset_ids) > 50:
        raise _sw_http_error(status_code=422, detail="Provide 1-50 asset IDs")
    approved_count = 0
    with st.lock:
        for asset_id in asset_ids:
            asset = next(
                (
                    item
                    for item in st.ugc_assets
                    if item.get("tenant_id") == auth.tenant_id and item.get("id") == asset_id
                ),
                None,
            )
            if asset:
                asset["approved"] = True
                asset["rights_status"] = "approved"
                asset["updated_at"] = datetime.now(UTC).isoformat()
                approved_count += 1
    _sw_audit(st, auth.tenant_id, "social_ugc_batch_approved", approved_count)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "approved": approved_count,
        "total": len(asset_ids),
        "telemetry_event": "social.ugc.batch_approved",
    }


def operation_get_ugc_performance(
    st: _SocialWorkspaceState, router: APIRouter, asset_id: int | None = None, *, auth: AuthDep
) -> dict[str, Any]:
    """Get performance metrics for republished UGC (production vendor integration)."""
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ugc:performance", 240, 60)
    perf_endpoint = os.getenv("UGC_PERFORMANCE_ENDPOINT", "").strip()
    perf_api_key = os.getenv("UGC_DISCOVERY_API_KEY", "").strip()
    if not perf_endpoint or not perf_api_key:
        with st.lock:
            posts = [p for p in st.scheduled_posts if p.get("tenant_id") == auth.tenant_id and p.get("ugc_asset_id")]
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "total_ugc_posts": len(posts),
            "performance": [
                {
                    "post_id": p["id"],
                    "asset_id": p.get("ugc_asset_id"),
                    "platform": p["platform"],
                    "engagement": 0,
                    "impressions": 0,
                    "clicks": 0,
                }
                for p in posts[:10]
            ],
        }
    try:
        headers = {"Authorization": f"Bearer {perf_api_key}", "Content-Type": JSON_CONTENT_TYPE}
        result = ugc_provider._ugc_http_json_request("GET", f"{perf_endpoint}?tenant={auth.tenant_id}", headers)
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "performance": result.get("performance", []),
            "summary": result.get("summary", {}),
            "telemetry_event": "social.ugc.performance_fetched",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _sw_http_error(status_code=502, detail=f"Performance fetch failed: {str(exc)}")
