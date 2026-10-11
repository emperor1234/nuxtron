"""Marketing/Ads use cases: get calendar."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import SUPPORTED_PLATFORMS
from ..constants import _BEST_TIME_TABLE
from ..constants import _DEFAULT_BEST_TIME
from ..runtime import ContextRuntime
from ..schemas import ApprovalDecisionModel
from ..schemas import ApprovalRequestModel
from ..schemas import AssetAutoResizeRequest
from ..schemas import CalendarRescheduleRequest
from ..schemas import CampaignDuplicateRequest
from ..services.now_iso import _now_iso
from .append_notification import helper_append_notification
from .append_notification import helper_ensure_connector
from .append_notification import helper_get_campaign
from .append_notification import helper_log_audit
from .append_notification import helper_tenant_campaigns
from fastapi import HTTPException
from fastapi import Query
from typing import Any
import uuid


async def execute_get_calendar(runtime: ContextRuntime, auth: AuthDep):
    campaigns = helper_tenant_campaigns(runtime, auth.tenant_id)
    events: list[dict[str, Any]] = []
    for campaign in campaigns:
        schedule = dict(campaign.get("schedule") or {})
        for date_value in schedule.get("posting_dates", []) or []:
            events.append(
                {
                    "campaign_id": campaign.get("id"),
                    "campaign_name": campaign.get("campaign_name"),
                    "platform": campaign.get("platform"),
                    "date": date_value,
                    "timezone": schedule.get("timezone", "UTC"),
                    "auto_post": bool(schedule.get("auto_post", True)),
                }
            )
    events.sort(key=lambda item: str(item.get("date", "")))
    return {"status": "ok", "tenant_id": auth.tenant_id, "events": events}


async def execute_drag_reschedule(runtime: ContextRuntime, payload: CalendarRescheduleRequest, auth: AuthDep):
    campaign = helper_get_campaign(runtime, auth.tenant_id, payload.campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    with runtime.lock:
        schedule = dict(campaign.get("schedule") or {})
        dates = [str(item) for item in schedule.get("posting_dates", []) or []]
        if payload.from_date in dates:
            dates = [payload.to_date if item == payload.from_date else item for item in dates]
        else:
            dates.append(payload.to_date)
        dates = sorted(set(dates))
        schedule["posting_dates"] = dates
        schedule["auto_select_window_days"] = payload.auto_select_window_days
        campaign["schedule"] = schedule
        campaign["updated_at"] = _now_iso()
    helper_append_notification(
        runtime,
        auth.tenant_id,
        "Calendar updated",
        f"{campaign.get('campaign_name', 'Campaign')} moved to {payload.to_date}.",
    )
    helper_log_audit(
        runtime, auth.tenant_id, "ads_calendar_rescheduled", {"campaign_id": payload.campaign_id, "to": payload.to_date}
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}


async def execute_auto_resize_asset(runtime: ContextRuntime, payload: AssetAutoResizeRequest, auth: AuthDep):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:assets:resize", limit=50, window_seconds=60)
    profile_map = {
        "google_ads": [(1200, 628), (1080, 1080), (960, 1200)],
        "amazon_ads": [(1200, 628), (1024, 512)],
        "microsoft_ads": [(1200, 628), (1080, 1080)],
        "apple_search_ads": [(1200, 628), (640, 1136)],
        "youtube_ads": [(1920, 1080), (1080, 1920)],
    }
    generated: list[dict[str, Any]] = []
    for platform in payload.platforms:
        if platform not in SUPPORTED_PLATFORMS:
            continue
        for width, height in profile_map.get(platform, []):
            generated.append(
                {
                    "platform": platform,
                    "width": width,
                    "height": height,
                    "output_url": f"{payload.asset_url}?platform={platform}&w={width}&h={height}",
                }
            )
    helper_log_audit(
        runtime, auth.tenant_id, "ads_asset_auto_resize", {"asset": payload.asset_url, "variants": len(generated)}
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "variants": generated}


async def execute_get_kpis(runtime: ContextRuntime, auth: AuthDep):
    campaigns = helper_tenant_campaigns(runtime, auth.tenant_id)
    total_budget_daily = sum((float(item.get("budget_daily", 0.0) or 0.0) for item in campaigns))
    total_budget_total = sum((float(item.get("budget_total", 0.0) or 0.0) for item in campaigns))
    spend = 0.0
    revenue = 0.0
    clicks = 0
    conversions = 0
    impressions = 0
    likes = 0
    shares = 0
    comments = 0
    active = 0
    for campaign in campaigns:
        if str(campaign.get("status")) == "active":
            active += 1
        metrics = dict(campaign.get("metrics") or {})
        spend += float(metrics.get("spend", 0.0) or 0.0)
        revenue += float(metrics.get("revenue", 0.0) or 0.0)
        clicks += int(metrics.get("clicks", 0) or 0)
        conversions += int(metrics.get("conversions", 0) or 0)
        impressions += int(metrics.get("impressions", 0) or 0)
        likes += int(metrics.get("likes", 0) or 0)
        shares += int(metrics.get("shares", 0) or 0)
        comments += int(metrics.get("comments", 0) or 0)
    ctr = clicks / impressions * 100.0 if impressions > 0 else 0.0
    cpc = spend / clicks if clicks > 0 else 0.0
    cpa = spend / conversions if conversions > 0 else 0.0
    roi = (revenue - spend) / spend * 100.0 if spend > 0 else 0.0
    success_ratio = conversions / clicks * 100.0 if clicks > 0 else 0.0
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "summary": {
            "campaigns_total": len(campaigns),
            "campaigns_active": active,
            "budget_daily": round(total_budget_daily, 2),
            "budget_total": round(total_budget_total, 2),
            "spend": round(spend, 2),
            "revenue": round(revenue, 2),
            "roi_pct": round(roi, 2),
            "success_ratio_pct": round(success_ratio, 2),
            "ctr_pct": round(ctr, 2),
            "cpc": round(cpc, 2),
            "cpa": round(cpa, 2),
        },
        "engagement": {
            "likes": likes,
            "shares": shares,
            "comments": comments,
            "clicks": clicks,
            "impressions": impressions,
            "conversions": conversions,
        },
    }


async def execute_get_forecast(runtime: ContextRuntime, auth: AuthDep, days: int = Query(default=30, ge=1, le=365)):
    campaigns = helper_tenant_campaigns(runtime, auth.tenant_id)
    active = [item for item in campaigns if str(item.get("status")) in {"active", "draft"}]
    daily_budget = sum((float(item.get("budget_daily", 0.0) or 0.0) for item in active))
    projected_spend = daily_budget * days
    baseline_click_rate = 0.021
    baseline_conv_rate = 0.073
    projected_clicks = (
        int(projected_spend * 1.0 / max(0.01, 1.85) / max(0.001, baseline_click_rate)) if projected_spend > 0 else 0
    )
    projected_conversions = int(projected_clicks * baseline_conv_rate)
    projected_revenue = projected_conversions * 48.0
    projected_roi_pct = (projected_revenue - projected_spend) / projected_spend * 100.0 if projected_spend > 0 else 0.0
    with runtime.lock:
        runtime._forecasts.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": auth.tenant_id,
                "horizon_days": days,
                "projected_spend": round(projected_spend, 2),
                "projected_clicks": projected_clicks,
                "projected_conversions": projected_conversions,
                "projected_roi_pct": round(projected_roi_pct, 2),
                "created_at": _now_iso(),
            }
        )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "horizon_days": days,
        "projected_spend": round(projected_spend, 2),
        "projected_clicks": projected_clicks,
        "projected_conversions": projected_conversions,
        "projected_roi_pct": round(projected_roi_pct, 2),
    }


async def execute_list_ads_notifications(
    runtime: ContextRuntime, auth: AuthDep, limit: int = Query(default=50, ge=1, le=200)
):
    items = [
        item
        for item in runtime.notifications_memory
        if item.get("tenant_id") == auth.tenant_id and str(item.get("category", "")).lower() == "ads_control_tower"
    ]
    items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "total": len(items), "notifications": items[:limit]}


async def execute_get_best_time(
    runtime: ContextRuntime,
    auth: AuthDep,
    platform: str = Query(default="google_ads"),
    objective: str = Query(default="conversions"),
):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:best-time", limit=60, window_seconds=60)
    platform_key = platform.strip().lower()
    objective_key = objective.strip().lower()
    data = _BEST_TIME_TABLE.get(platform_key, {}).get(objective_key) or _DEFAULT_BEST_TIME
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "platform": platform_key,
        "objective": objective_key,
        "best_days": data["best_days"],
        "heatmap": data["heatmap"],
        "peak_hour": data["peak_hour"],
        "avoid_hours": data["avoid_hours"],
        "human_review_window": data["human_review_window"],
        "rationale": data["rationale"],
        "all_platforms_peak": {
            "google_ads": 10,
            "microsoft_ads": 10,
            "amazon_ads": 20,
            "apple_search_ads": 9,
            "youtube_ads": 20,
        },
    }


async def execute_request_approval(
    runtime: ContextRuntime, campaign_id: str, payload: ApprovalRequestModel, auth: AuthDep
):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:approval:request", limit=30, window_seconds=60)
    campaign = helper_get_campaign(runtime, auth.tenant_id, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    with runtime.lock:
        campaign["approval_status"] = "pending_approval"
        campaign["approval_requested_at"] = _now_iso()
        campaign["reviewer_email"] = payload.reviewer_email
        campaign["approval_message"] = payload.message
        campaign["auto_publish_on_approve"] = payload.auto_publish_on_approve
        campaign["updated_at"] = _now_iso()
    helper_append_notification(
        runtime,
        auth.tenant_id,
        "Approval requested",
        f"{campaign.get('campaign_name', 'Campaign')} awaiting review by {payload.reviewer_email}.",
        "info",
    )
    helper_log_audit(
        runtime,
        auth.tenant_id,
        "ads_approval_requested",
        {"campaign_id": campaign_id, "reviewer": payload.reviewer_email},
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}


async def execute_decide_campaign_approval(
    runtime: ContextRuntime, campaign_id: str, payload: ApprovalDecisionModel, auth: AuthDep
):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:approval:decide", limit=30, window_seconds=60)
    campaign = helper_get_campaign(runtime, auth.tenant_id, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    with runtime.lock:
        campaign["approval_status"] = payload.decision
        campaign["approval_decided_at"] = _now_iso()
        campaign["approval_reason"] = payload.reason
        campaign["approver_name"] = payload.reviewer_name
        campaign["updated_at"] = _now_iso()
        if payload.decision == "approved" and bool(campaign.get("auto_publish_on_approve", True)):
            platform = str(campaign.get("platform"))
            connector = helper_ensure_connector(runtime, auth.tenant_id, platform)
            if connector.get("connected"):
                campaign["status"] = "active"
                campaign["published_at"] = _now_iso()
    priority = "success" if payload.decision == "approved" else "warning"
    helper_append_notification(
        runtime,
        auth.tenant_id,
        f"Campaign {payload.decision}",
        f"{campaign.get('campaign_name', 'Campaign')} was {payload.decision} by {payload.reviewer_name}.",
        priority,
    )
    helper_log_audit(
        runtime,
        auth.tenant_id,
        f"ads_campaign_{payload.decision}",
        {"campaign_id": campaign_id, "reviewer": payload.reviewer_name},
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": campaign}


async def execute_duplicate_campaign(
    runtime: ContextRuntime, campaign_id: str, payload: CampaignDuplicateRequest, auth: AuthDep
):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:campaigns:duplicate", limit=30, window_seconds=60)
    import copy

    source = helper_get_campaign(runtime, auth.tenant_id, campaign_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    new_id = str(uuid.uuid4())
    created_at = _now_iso()
    new_campaign = copy.deepcopy(source)
    new_campaign.update(
        {
            "id": new_id,
            "campaign_name": payload.new_name,
            "status": payload.status,
            "created_at": created_at,
            "updated_at": created_at,
            "published_at": None,
            "approval_status": None,
            "approval_requested_at": None,
            "metrics": {
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
            },
        }
    )
    with runtime.lock:
        runtime._campaigns.append(new_campaign)
    helper_append_notification(
        runtime,
        auth.tenant_id,
        "Campaign duplicated",
        f"'{payload.new_name}' cloned from '{source.get('campaign_name')}'.",
        "info",
    )
    helper_log_audit(runtime, auth.tenant_id, "ads_campaign_duplicated", {"source_id": campaign_id, "new_id": new_id})
    return {"status": "ok", "tenant_id": auth.tenant_id, "campaign": new_campaign}


async def execute_ab_test_suggestions(runtime: ContextRuntime, campaign_id: str, auth: AuthDep):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:ab-test", limit=30, window_seconds=60)
    campaign = helper_get_campaign(runtime, auth.tenant_id, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    creative = dict(campaign.get("creative") or {})
    title = str(creative.get("title", "Your Product"))
    description = str(creative.get("description", "Discover what makes us different."))
    cta = str(creative.get("cta", "Learn More"))
    cta_variants: dict[str, list[str]] = {
        "Learn More": ["Get Started", "See How It Works", "Explore Now"],
        "Shop Now": ["Buy Today", "Order Now", "Claim Your Discount"],
        "Sign Up": ["Join Free", "Start Today", "Create Account"],
        "Get Started": ["Try for Free", "Start Now", "Begin Today"],
        "Contact Us": ["Talk to an Expert", "Request a Demo", "Get in Touch"],
    }
    alt_ctas = cta_variants.get(cta, ["Try Now", "Discover More", "Act Now"])
    first_word = title.split()[0] if title.split() else "Us"
    suggestions = [
        {
            "variant": "A",
            "label": "Urgency headline",
            "title": f"Last Chance: {title}",
            "description": description,
            "cta": cta,
            "predicted_ctr_lift_pct": 14,
            "rationale": "Urgency framing increases CTR by 12–18% on average.",
        },
        {
            "variant": "B",
            "label": "Question hook",
            "title": f"Is {title} Right for You?",
            "description": f"See why thousands choose {first_word}. {description}",
            "cta": alt_ctas[0],
            "predicted_ctr_lift_pct": 9,
            "rationale": "Question headlines engage curiosity and drive 9% higher click rates.",
        },
        {
            "variant": "C",
            "label": "Social proof",
            "title": f"{title} — Trusted by 10,000+",
            "description": f"Join thousands of satisfied customers. {description}",
            "cta": alt_ctas[1],
            "predicted_ctr_lift_pct": 18,
            "rationale": "Social proof reduces friction and lifts conversions by 15–22%.",
        },
        {
            "variant": "D",
            "label": "Benefit-first",
            "title": f"Save Time & Money with {first_word}",
            "description": description,
            "cta": alt_ctas[2] if len(alt_ctas) > 2 else alt_ctas[0],
            "predicted_ctr_lift_pct": 11,
            "rationale": "Leading with direct benefits resonates with high-intent audiences.",
        },
    ]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "campaign_id": campaign_id,
        "original": {"title": title, "description": description, "cta": cta},
        "suggestions": suggestions,
    }


async def execute_audience_insights(runtime: ContextRuntime, auth: AuthDep):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ads:audience-insights", limit=30, window_seconds=60)
    campaigns = helper_tenant_campaigns(runtime, auth.tenant_id)
    platforms_used = list({str(c.get("platform")) for c in campaigns})
    keywords_used: list[str] = []
    for c in campaigns:
        for kw in c.get("keywords", []) or []:
            kw_word = str(kw.get("keyword", "")) if isinstance(kw, dict) else ""
            if kw_word and kw_word not in keywords_used:
                keywords_used.append(kw_word)
    overlap_pct = min(85, max(0, len(platforms_used) * 12 + len(keywords_used) * 3))
    saturation_score = min(100, max(0, len(keywords_used) * 4 + len(campaigns) * 2))
    platform_reach: dict[str, int] = {
        "google_ads": 4200000000,
        "microsoft_ads": 540000000,
        "amazon_ads": 310000000,
        "apple_search_ads": 650000000,
        "youtube_ads": 2700000000,
    }
    reach_estimate = sum((platform_reach.get(p, 100000000) for p in platforms_used))
    recommendations: list[str] = []
    if overlap_pct > 60:
        recommendations.append("High audience overlap — consider platform-specific creative to reduce ad fatigue.")
    if saturation_score > 70:
        recommendations.append("Keyword pool may be saturating — broaden match types or add long-tail variants.")
    if len(platforms_used) < 3:
        recommendations.append("Expand to 3+ platforms for diversified reach and reduced channel dependency.")
    if not recommendations:
        recommendations.append("Audience distribution looks healthy. Monitor frequency caps weekly.")
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "platforms_active": platforms_used,
        "keywords_indexed": len(keywords_used),
        "audience_overlap_pct": overlap_pct,
        "keyword_saturation_score": saturation_score,
        "estimated_reach": reach_estimate,
        "recommendations": recommendations,
        "top_keywords": keywords_used[:10],
        "frequency_cap_suggestion": 3 if saturation_score > 60 else 5,
    }
