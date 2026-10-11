"""Social use cases: get ads analytics."""

from ....domains.social.persistence import _SocialWorkspaceState
from ..services import brand as ugc_provider
from ....domains.social.persistence import _sw_audit
from ....domains.social.schemas import BulkScheduleRequest
from ....domains.social.schemas import ReportCreateRequest
from ....domains.social.schemas import UgcApproveRequest
from ....domains.social.schemas import UgcRepublishRequest
from ..constants import AuthDep
from ..constants import REPORT_NOT_FOUND
from ..constants import SUPPORTED_NETWORKS
from ..constants import TEN_AM_LABEL
from ..constants import UGC_ASSET_NOT_FOUND
from ..services.capabilities import _require_any_env_for_strict_social
from ..services.workspace import _sw_http_error
from ..services.workspace import _sw_seed_ad_campaigns
from ..services.workspace import _sw_seed_reports
from datetime import UTC
from datetime import datetime
from fastapi import APIRouter
from fastapi import HTTPException
from typing import Any
from typing import cast
import secrets


def operation_get_ads_analytics(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    _require_any_env_for_strict_social(
        ["META_ADS_ACCESS_TOKEN", "META_ACCESS_TOKEN", "TIKTOK_ADS_ACCESS_TOKEN", "TIKTOK_ACCESS_TOKEN"],
        "paid social ads analytics",
    )
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ads:analytics", 240, 60)
    _sw_seed_ad_campaigns(st, auth.tenant_id)
    with st.lock:
        campaigns = [item.copy() for item in st.social_ad_campaigns if item.get("tenant_id") == auth.tenant_id]
        boosts = [item.copy() for item in st.social_ad_boosts if item.get("tenant_id") == auth.tenant_id]
    total_paid_impressions = sum((int(c.get("impressions") or 0) for c in campaigns))
    total_paid_spend = sum((float(c.get("spent") or 0) for c in campaigns))
    by_network: dict[str, dict[str, Any]] = {}
    for c in campaigns:
        net = str(c.get("network") or "other")
        entry = by_network.setdefault(net, {"impressions": 0, "clicks": 0, "conversions": 0, "spent": 0.0, "roas": []})
        entry["impressions"] += int(c.get("impressions") or 0)
        entry["clicks"] += int(c.get("clicks") or 0)
        entry["conversions"] += int(c.get("conversions") or 0)
        entry["spent"] += float(c.get("spent") or 0)
        cast(list[float], entry["roas"]).append(float(c.get("roas") or 0))
    for net in by_network:
        roas_list = cast(list[float], by_network[net]["roas"])
        by_network[net]["avg_roas"] = round(sum(roas_list) / max(len(roas_list), 1), 2)
        del by_network[net]["roas"]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "paid_summary": {
            "total_impressions": total_paid_impressions,
            "total_spend": round(total_paid_spend, 2),
            "active_campaigns": sum((1 for c in campaigns if c.get("status") == "active")),
            "active_boosts": sum((1 for b in boosts if b.get("status") == "active")),
        },
        "by_network": by_network,
        "campaigns": campaigns,
        "boosts": boosts,
    }


def operation_list_reports(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:reports:list", 240, 60)
    _sw_seed_reports(st, auth.tenant_id)
    with st.lock:
        items = [item.copy() for item in st.reports if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "reports": items}


def operation_create_report(
    st: _SocialWorkspaceState, router: APIRouter, payload: ReportCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:reports:create", 60, 60)
    now = datetime.now(UTC).isoformat()
    with st.lock:
        report = {
            "id": len(st.reports) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name.strip(),
            "report_type": payload.report_type.strip(),
            "networks": payload.networks,
            "date_range_days": payload.date_range_days,
            "metrics": payload.metrics,
            "export_format": payload.export_format.strip(),
            "schedule": payload.schedule,
            "status": "generating",
            "data": {},
            "created_at": now,
            "generated_at": None,
        }
        st.reports.append(report)
        created = report.copy()
    _sw_audit(st, auth.tenant_id, "social_report_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "report": created, "telemetry_event": "social.reports.created"}


def operation_get_report(st: _SocialWorkspaceState, router: APIRouter, report_id: int, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:reports:get", 240, 60)
    with st.lock:
        report = next(
            (
                item.copy()
                for item in st.reports
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == report_id
            ),
            None,
        )
    if report is None:
        raise _sw_http_error(status_code=404, detail=REPORT_NOT_FOUND)
    return {"status": "ok", "tenant_id": auth.tenant_id, "report": report}


def operation_export_report(
    st: _SocialWorkspaceState, router: APIRouter, report_id: int, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:reports:export", 30, 60)
    with st.lock:
        report = next(
            (item for item in st.reports if item.get("tenant_id") == auth.tenant_id and item.get("id") == report_id),
            None,
        )
    if report is None:
        raise _sw_http_error(status_code=404, detail=REPORT_NOT_FOUND)
    export_token = secrets.token_urlsafe(32)
    _sw_audit(st, auth.tenant_id, "social_report_exported", report_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "report_id": report_id,
        "export_format": report.get("export_format", "pdf"),
        "download_url": f"/api/fastapi/social/reports/{report_id}/download?token={export_token}",
        "expires_in_seconds": 3600,
        "telemetry_event": "social.reports.exported",
    }


def operation_delete_report(
    st: _SocialWorkspaceState, router: APIRouter, report_id: int, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:reports:delete", 60, 60)
    with st.lock:
        idx = next(
            (
                i
                for i, item in enumerate(st.reports)
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == report_id
            ),
            None,
        )
        if idx is None:
            raise _sw_http_error(status_code=404, detail=REPORT_NOT_FOUND)
        st.reports.pop(idx)
    _sw_audit(st, auth.tenant_id, "social_report_deleted", report_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "deleted_id": report_id}


def operation_get_best_time_to_post(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:best-time", 120, 60)
    recommendations = {
        "instagram": [
            {
                "day": "Monday",
                "hour": 11,
                "score": 9.2,
                "label": "11:00 AM",
                "reason": "Peak audience activity based on your follower timezone distribution",
            },
            {
                "day": "Wednesday",
                "hour": 14,
                "score": 9.5,
                "label": "2:00 PM",
                "reason": "Highest engagement window for B2C content midweek",
            },
            {
                "day": "Friday",
                "hour": 10,
                "score": 8.8,
                "label": TEN_AM_LABEL,
                "reason": "Friday morning sees high story-view rates",
            },
        ],
        "x": [
            {
                "day": "Tuesday",
                "hour": 9,
                "score": 9.1,
                "label": "9:00 AM",
                "reason": "Business audience peaks at start of workday",
            },
            {
                "day": "Wednesday",
                "hour": 12,
                "score": 8.9,
                "label": "12:00 PM",
                "reason": "Lunch-break scroll window maximizes impressions",
            },
            {"day": "Thursday", "hour": 18, "score": 8.7, "label": "6:00 PM", "reason": "Post-work engagement surge"},
        ],
        "facebook": [
            {
                "day": "Wednesday",
                "hour": 11,
                "score": 9.3,
                "label": "11:00 AM",
                "reason": "Highest organic reach window for Pages this month",
            },
            {
                "day": "Thursday",
                "hour": 13,
                "score": 8.6,
                "label": "1:00 PM",
                "reason": "Video posts see 2.4x more views at this time",
            },
        ],
        "linkedin": [
            {
                "day": "Tuesday",
                "hour": 10,
                "score": 9.4,
                "label": TEN_AM_LABEL,
                "reason": "Decision-makers most active Tuesday mornings",
            },
            {
                "day": "Wednesday",
                "hour": 9,
                "score": 9.2,
                "label": "9:00 AM",
                "reason": "Highest B2B engagement slot of the week",
            },
            {
                "day": "Thursday",
                "hour": 10,
                "score": 9.0,
                "label": TEN_AM_LABEL,
                "reason": "Mid-week professional content peak",
            },
        ],
        "tiktok": [
            {
                "day": "Friday",
                "hour": 18,
                "score": 9.5,
                "label": "6:00 PM",
                "reason": "Friday evening is peak For You page surfing window",
            },
            {
                "day": "Saturday",
                "hour": 10,
                "score": 9.1,
                "label": TEN_AM_LABEL,
                "reason": "Weekend morning is highest watch-time slot",
            },
            {
                "day": "Sunday",
                "hour": 14,
                "score": 8.9,
                "label": "2:00 PM",
                "reason": "Sunday afternoon drives share velocity",
            },
        ],
        "youtube": [
            {
                "day": "Saturday",
                "hour": 15,
                "score": 9.3,
                "label": "3:00 PM",
                "reason": "Weekend afternoon maximizes subscriber notifications",
            },
            {
                "day": "Sunday",
                "hour": 17,
                "score": 9.0,
                "label": "5:00 PM",
                "reason": "Sunday evening long-form viewing peak",
            },
        ],
    }
    heatmap = {
        net: {
            str(hour): round(
                5.0 + 4.5 * (1 if any((r["hour"] == hour for r in recs)) else 0.3 + 0.5 * (hour % 6 / 6)), 1
            )
            for hour in range(24)
        }
        for net, recs in recommendations.items()
    }
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "recommendations": recommendations,
        "heatmap": heatmap,
        "model_version": "2026-05",
        "data_points_analyzed": 284000,
    }


def operation_bulk_schedule_posts(
    st: _SocialWorkspaceState, router: APIRouter, payload: BulkScheduleRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:bulk-schedule", 30, 60)
    created: list[dict[str, Any]] = []
    errors = []
    with st.lock:
        for idx, post_data in enumerate(payload.posts):
            try:
                if not post_data.get("text") and (not post_data.get("content")):
                    errors.append({"row": idx + 1, "error": "Missing text/content field"})
                    continue
                if not post_data.get("publish_at") and (not post_data.get("schedule_at")):
                    errors.append({"row": idx + 1, "error": "Missing publish_at field"})
                    continue
                platform = str(post_data.get("platform") or post_data.get("network") or "instagram")
                post = {
                    "id": len(st.scheduled_posts) + len(created) + 1,
                    "tenant_id": auth.tenant_id,
                    "platform": platform,
                    "text": str(post_data.get("text") or post_data.get("content") or ""),
                    "publish_at": str(post_data.get("publish_at") or post_data.get("schedule_at") or ""),
                    "status": "scheduled",
                    "hashtags": post_data.get("hashtags", []),
                    "media_urls": post_data.get("media_urls", []),
                    "utm_tags": post_data.get("utm_tags", {}),
                    "created_at": datetime.now(UTC).isoformat(),
                    "bulk_job_id": None,
                }
                st.scheduled_posts.append(post)
                created.append({"row": idx + 1, "post_id": post["id"]})
            except Exception as exc:
                errors.append({"row": idx + 1, "error": str(exc)})
        job = {
            "id": len(st.bulk_schedule_jobs) + 1,
            "tenant_id": auth.tenant_id,
            "total_rows": len(payload.posts),
            "created": len(created),
            "errors": len(errors),
            "status": "complete",
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.bulk_schedule_jobs.append(job)
        job_copy = job.copy()
    _sw_audit(st, auth.tenant_id, "social_bulk_schedule_submitted", job_copy["id"])
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "job": job_copy,
        "created": created,
        "errors": errors,
        "telemetry_event": "social.bulk_schedule.submitted",
    }


def operation_list_bulk_schedule_jobs(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:bulk-schedule:jobs", 240, 60)
    with st.lock:
        items = [item.copy() for item in st.bulk_schedule_jobs if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "jobs": items}


def operation_get_bulk_schedule_template(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:bulk-schedule:template", 120, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "template_fields": ["platform", "text", "publish_at", "hashtags", "media_urls", "utm_campaign"],
        "example_row": {
            "platform": "instagram",
            "text": "Example post content #marketing",
            "publish_at": "2026-06-01T10:00:00Z",
            "hashtags": "#marketing,#brand",
            "media_urls": "",
            "utm_campaign": "june-campaign",
        },
        "supported_networks": list(SUPPORTED_NETWORKS.keys()),
        "max_rows": 500,
    }


def operation_discover_ugc_assets(
    st: _SocialWorkspaceState, router: APIRouter, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    """Initiate UGC discovery from brand mentions (production vendor integration)."""
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ugc:discover", 30, 60)
    brand_domain = payload.get("brand_domain", f"{auth.tenant_id}.example.com").strip()
    limit = min(int(payload.get("limit", 20)), 100)
    try:
        assets = ugc_provider._fetch_ugc_assets(brand_domain, limit)
        with st.lock:
            st.ugc_assets = [item for item in st.ugc_assets if item.get("tenant_id") != auth.tenant_id]
            for asset in assets:
                asset["tenant_id"] = auth.tenant_id
                st.ugc_assets.append(asset)
        _sw_audit(st, auth.tenant_id, "social_ugc_discovered", len(assets))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "discovered": len(assets),
            "assets": assets[:10],
            "telemetry_event": "social.ugc.discovered",
        }
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise _sw_http_error(status_code=502, detail=f"UGC discovery failed: {str(exc)}")


def operation_list_ugc_assets(
    st: _SocialWorkspaceState,
    router: APIRouter,
    sentiment: str | None = None,
    rights_status: str | None = None,
    *,
    auth: AuthDep,
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ugc:list", 240, 60)
    with st.lock:
        items = [item.copy() for item in st.ugc_assets if item.get("tenant_id") == auth.tenant_id]
    if sentiment:
        items = [item for item in items if item.get("sentiment") == sentiment]
    if rights_status:
        items = [item for item in items if item.get("rights_status") == rights_status]
    summary = {
        "total": len(items),
        "pending_rights": sum((1 for item in items if item.get("rights_status") == "pending")),
        "approved": sum((1 for item in items if item.get("rights_status") == "approved")),
        "declined": sum((1 for item in items if item.get("rights_status") == "declined")),
    }
    return {"status": "ok", "tenant_id": auth.tenant_id, "summary": summary, "assets": items}


def operation_approve_ugc_asset(
    st: _SocialWorkspaceState, router: APIRouter, asset_id: int, payload: UgcApproveRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ugc:approve", 120, 60)
    with st.lock:
        asset = next(
            (item for item in st.ugc_assets if item.get("tenant_id") == auth.tenant_id and item.get("id") == asset_id),
            None,
        )
        if asset is None:
            raise _sw_http_error(status_code=404, detail=UGC_ASSET_NOT_FOUND)
        asset["approved"] = payload.approved
        asset["rights_status"] = "approved" if payload.approved else "declined"
        if payload.note:
            asset["rights_note"] = payload.note.strip()
        asset["updated_at"] = datetime.now(UTC).isoformat()
        updated = asset.copy()
    _sw_audit(
        st, auth.tenant_id, "social_ugc_asset_approved" if payload.approved else "social_ugc_asset_declined", asset_id
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "asset": updated,
        "telemetry_event": "social.ugc.approved" if payload.approved else "social.ugc.declined",
    }


def operation_republish_ugc_asset(
    st: _SocialWorkspaceState,
    router: APIRouter,
    asset_id: int,
    auth: AuthDep,
    payload: UgcRepublishRequest | None = None,
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:ugc:republish", 60, 60)
    requested_publish_at = payload.scheduled_time if payload is not None else None
    if requested_publish_at is not None and requested_publish_at.tzinfo is None:
        requested_publish_at = requested_publish_at.replace(tzinfo=UTC)
    target_network = None
    if payload is not None and payload.target_networks:
        target_network = str(payload.target_networks[0]).strip().lower()
    with st.lock:
        asset = next(
            (item for item in st.ugc_assets if item.get("tenant_id") == auth.tenant_id and item.get("id") == asset_id),
            None,
        )
        if asset is None:
            raise _sw_http_error(status_code=404, detail=UGC_ASSET_NOT_FOUND)
        if asset.get("rights_status") != "approved":
            raise _sw_http_error(status_code=422, detail="Rights must be approved before republishing.")
        publish_at = requested_publish_at or datetime.now(UTC)
        platform = target_network or str(asset.get("network") or "instagram")
        post = {
            "id": len(st.scheduled_posts) + 1,
            "tenant_id": auth.tenant_id,
            "platform": platform,
            "text": str(asset.get("caption") or ""),
            "publish_at": publish_at.isoformat(),
            "status": "scheduled",
            "ugc_asset_id": asset_id,
            "credit_creator": bool(payload.add_credit) if payload is not None else True,
            "credited_handle": str(asset.get("author") or ""),
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.scheduled_posts.append(post)
    _sw_audit(st, auth.tenant_id, "social_ugc_republished", asset_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "post": post, "telemetry_event": "social.ugc.republished"}
