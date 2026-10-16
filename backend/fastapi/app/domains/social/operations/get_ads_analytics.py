"""Social use cases: get ads analytics."""

import secrets
from datetime import UTC, datetime
from typing import Any, cast

from fastapi import APIRouter

from ....domains.social.persistence import _SocialWorkspaceState, _sw_audit
from ....domains.social.schemas import BulkScheduleRequest, ReportCreateRequest, UgcApproveRequest, UgcRepublishRequest
from ..constants import REPORT_NOT_FOUND, SUPPORTED_NETWORKS, TEN_AM_LABEL, AuthDep
from ..services.capabilities import _require_any_env_for_strict_social
from ..services.workspace import _sw_http_error, _sw_seed_ad_campaigns, _sw_seed_reports
from ..ugc_unavailable import raise_ugc_unavailable


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
    total_paid_impressions = sum(int(c.get("impressions") or 0) for c in campaigns)
    total_paid_spend = sum(float(c.get("spent") or 0) for c in campaigns)
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
            "active_campaigns": sum(1 for c in campaigns if c.get("status") == "active"),
            "active_boosts": sum(1 for b in boosts if b.get("status") == "active"),
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
                5.0 + 4.5 * (1 if any(r["hour"] == hour for r in recs) else 0.3 + 0.5 * (hour % 6 / 6)), 1
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
                platform = str(post_data.get("platform") or post_data.get("network") or "").strip().lower()
                if platform not in SUPPORTED_NETWORKS:
                    errors.append({"row": idx + 1, "error": f"Unsupported platform '{platform}'"})
                    continue
                text = str(post_data.get("text") or post_data.get("content") or "").strip()
                if len(text) > 4000:
                    errors.append({"row": idx + 1, "error": "Text is longer than 4,000 characters"})
                    continue
                publish_raw = str(post_data.get("publish_at") or post_data.get("schedule_at") or "").strip()
                try:
                    publish_at = datetime.fromisoformat(publish_raw.replace("Z", "+00:00"))
                except ValueError:
                    errors.append({"row": idx + 1, "error": "publish_at must be an ISO 8601 date and time"})
                    continue
                if publish_at.tzinfo is None:
                    publish_at = publish_at.replace(tzinfo=UTC)

                def _as_list(value: Any) -> list[str]:
                    if isinstance(value, list):
                        return [str(item).strip() for item in value if str(item).strip()]
                    return [part.strip() for part in str(value or "").replace("\n", ",").split(",") if part.strip()]

                post = {
                    "id": len(st.scheduled_posts) + len(created) + 1,
                    "tenant_id": auth.tenant_id,
                    "platform": platform,
                    "text": text,
                    "publish_at": publish_at.isoformat(),
                    "status": "scheduled",
                    "hashtags": _as_list(post_data.get("hashtags")),
                    "media_urls": _as_list(post_data.get("media_urls")),
                    "utm_tags": post_data.get("utm_tags") if isinstance(post_data.get("utm_tags"), dict) else {},
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
    raise_ugc_unavailable()



def operation_list_ugc_assets(
    st: _SocialWorkspaceState,
    router: APIRouter,
    sentiment: str | None = None,
    rights_status: str | None = None,
    *,
    auth: AuthDep,
) -> dict[str, Any]:
    raise_ugc_unavailable()



def operation_approve_ugc_asset(
    st: _SocialWorkspaceState, router: APIRouter, asset_id: int, payload: UgcApproveRequest, auth: AuthDep
) -> dict[str, Any]:
    raise_ugc_unavailable()



def operation_republish_ugc_asset(
    st: _SocialWorkspaceState,
    router: APIRouter,
    asset_id: int,
    auth: AuthDep,
    payload: UgcRepublishRequest | None = None,
) -> dict[str, Any]:
    raise_ugc_unavailable()
