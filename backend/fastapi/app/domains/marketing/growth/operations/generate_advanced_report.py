"""Marketing/Growth use cases: generate advanced report."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import _SLUG_PATTERN
from ..runtime import ContextRuntime
from ..schemas import AdvancedReportRequest
from ..schemas import BrandHierarchyRequest
from ..schemas import BrandVoiceFeedbackRequest
from ..schemas import KeywordTrackRequest
from ..services.now_iso import _now_iso
from .ensure_tables import helper_load_records
from .ensure_tables import helper_store_record
from fastapi import HTTPException
from typing import Any
import uuid


def execute_generate_advanced_report(
    runtime: ContextRuntime, payload: AdvancedReportRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:reports", 20, 60)
    tracked_revenue = round(
        sum(
            (
                float(item.get("amount") or 0.0)
                for item in runtime.revenue_conversions_memory
                if item.get("tenant_id") == auth.tenant_id
            )
        ),
        2,
    )
    attributed_posts = sum(
        (1 for item in runtime.revenue_touchpoints_memory if item.get("tenant_id") == auth.tenant_id)
    )
    report = {
        "client_name": payload.client_name,
        "window_days": payload.reporting_window_days,
        "executive_summary": "Top content themes are compounding into measurable revenue, with clear winners for redistribution.",
        "platform_breakdown": [
            {"platform": "linkedin", "pipeline_share_pct": 46},
            {"platform": "instagram", "pipeline_share_pct": 31},
            {"platform": "email", "pipeline_share_pct": 23},
        ],
        "tracked_revenue": tracked_revenue,
        "attributed_posts": attributed_posts,
        "csv_export_path": "/analytics/export",
    }
    runtime.analytics_reports_memory.append(
        {
            "id": len(runtime.analytics_reports_memory) + 1,
            "tenant_id": auth.tenant_id,
            "name": f"{payload.client_name} advanced report",
            "status": "ready",
        }
    )
    helper_store_record(
        runtime,
        auth.tenant_id,
        "advanced_reports",
        "report",
        _SLUG_PATTERN.sub("_", payload.client_name.lower()).strip("_") or "client",
        {
            "status": "ready",
            "headline": "White-label advanced report generated with executive summary and export path.",
            "metrics": [
                {"label": "Tracked revenue", "value": tracked_revenue},
                {"label": "Attributed posts", "value": attributed_posts},
            ],
            "report": report,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "report": report}


def execute_brand_voice_feedback(
    runtime: ContextRuntime, profile_key: str, payload: BrandVoiceFeedbackRequest, auth: AuthDep
) -> dict[str, Any]:
    """Record thumbs-up/down feedback to improve the AI writing model."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:brand-voice:feedback", 120, 60)
    records = helper_load_records(runtime, auth.tenant_id)
    record = next(
        (
            row
            for row in records
            if row.get("feature_key") == "brand_voice_dna" and row.get("resource_key") == profile_key
        ),
        None,
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Brand voice profile not found.")
    content = record.get("payload", {}) if isinstance(record.get("payload"), dict) else {}
    thumbs_up = int(content.get("thumbs_up", 0))
    thumbs_down = int(content.get("thumbs_down", 0))
    if payload.signal == "thumbs_up":
        thumbs_up += 1
    else:
        thumbs_down += 1
    if payload.edited_output:
        bv = content.get("brand_voice", {}) if isinstance(content.get("brand_voice"), dict) else {}
        bv["rewrite"] = payload.edited_output
        content["brand_voice"] = bv
    content["thumbs_up"] = thumbs_up
    content["thumbs_down"] = thumbs_down
    bv = content.get("brand_voice", {}) if isinstance(content.get("brand_voice"), dict) else {}
    base_score = int(bv.get("voice_score", 70))
    net_signal = thumbs_up - thumbs_down
    adjusted = min(99, max(40, base_score + net_signal))
    bv["voice_score"] = adjusted
    content["brand_voice"] = bv
    content["headline"] = f"Voice model adapting: score {adjusted}/100, {thumbs_up} positive signals."
    helper_store_record(runtime, auth.tenant_id, "brand_voice_dna", "profile", profile_key, content)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "profile_key": profile_key,
        "voice_score": adjusted,
        "thumbs_up": thumbs_up,
        "thumbs_down": thumbs_down,
    }


def execute_list_ab_tests(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """List all A/B tests for the tenant with their status and winner data."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:ab-test:list", 120, 60)
    records = [
        row for row in helper_load_records(runtime, auth.tenant_id) if row.get("feature_key") == "auto_ab_testing"
    ]
    tests = []
    for row in records:
        payload = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
        tests.append(
            {
                "test_key": row.get("resource_key"),
                "name": payload.get("name", row.get("resource_key")),
                "status": payload.get("status", "unknown"),
                "headline": payload.get("headline", ""),
                "variants_count": len(payload.get("variants", [])) if isinstance(payload.get("variants"), list) else 0,
                "winner": payload.get("winner"),
                "channel": payload.get("channel", "linkedin"),
                "goal": payload.get("goal", "engagement"),
                "updated_at": row.get("updated_at"),
            }
        )
    return {"status": "ok", "tenant_id": auth.tenant_id, "tests": tests, "count": len(tests)}


def execute_keyword_top_insights(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Return keyword performance data for word cloud and engagement insights."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:keywords:top", 120, 60)
    tracked = [
        row for row in helper_load_records(runtime, auth.tenant_id) if row.get("feature_key") == "keyword_tracking"
    ]
    voice_records = [
        row for row in helper_load_records(runtime, auth.tenant_id) if row.get("feature_key") == "brand_voice_dna"
    ]
    keyword_map: dict[str, dict[str, Any]] = {}
    for row in tracked:
        p = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
        kw = str(p.get("keyword", ""))
        if not kw:
            continue
        if kw not in keyword_map:
            keyword_map[kw] = {"keyword": kw, "impressions": 0, "engagement": 0, "platforms": []}
        keyword_map[kw]["impressions"] += int(p.get("impressions", 0))
        keyword_map[kw]["engagement"] += int(p.get("engagement", 0))
        platform = p.get("platform", "")
        if platform and platform not in keyword_map[kw]["platforms"]:
            keyword_map[kw]["platforms"].append(platform)
    for vrow in voice_records:
        vp = vrow.get("payload", {}) if isinstance(vrow.get("payload"), dict) else {}
        bv = vp.get("brand_voice", {}) if isinstance(vp.get("brand_voice"), dict) else {}
        fp = bv.get("fingerprint", {}) if isinstance(bv.get("fingerprint"), dict) else {}
        sig_words = fp.get("signature_words", []) if isinstance(fp.get("signature_words"), list) else []
        for idx, word in enumerate(sig_words):
            if word not in keyword_map:
                keyword_map[word] = {
                    "keyword": word,
                    "impressions": 2400 - idx * 200,
                    "engagement": 180 - idx * 12,
                    "platforms": ["linkedin"],
                }
    keywords = sorted(keyword_map.values(), key=lambda x: int(x.get("impressions", 0)), reverse=True)
    for kw in keywords:
        imp = int(kw.get("impressions", 0))
        eng = int(kw.get("engagement", 0))
        kw["engagement_rate"] = round(eng / max(1, imp), 4)
        kw["weight"] = min(100, max(10, round(imp / 25)))
    return {"status": "ok", "tenant_id": auth.tenant_id, "keywords": keywords[:40], "count": len(keywords)}


def execute_track_keyword(runtime: ContextRuntime, payload: KeywordTrackRequest, auth: AuthDep) -> dict[str, Any]:
    """Record impressions and engagement for a keyword to build the word cloud."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:keywords:track", 120, 60)
    slug = _SLUG_PATTERN.sub("_", payload.keyword.lower()).strip("_") or "keyword"
    helper_store_record(
        runtime,
        auth.tenant_id,
        "keyword_tracking",
        "keyword",
        slug,
        {
            "keyword": payload.keyword,
            "impressions": payload.impressions,
            "engagement": payload.engagement,
            "platform": payload.platform,
            "updated_at": _now_iso(),
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "keyword": payload.keyword, "tracked": True}


def execute_list_brand_hierarchy(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Return the parent-child brand hierarchy for enterprise/franchise accounts."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:brand-hierarchy:list", 120, 60)
    records = [
        row for row in helper_load_records(runtime, auth.tenant_id) if row.get("feature_key") == "brand_hierarchy"
    ]
    brands = []
    for row in records:
        p = row.get("payload", {}) if isinstance(row.get("payload"), dict) else {}
        brands.append(
            {
                "brand_key": row.get("resource_key"),
                "brand_name": p.get("brand_name", ""),
                "parent_brand_key": p.get("parent_brand_key", "root"),
                "region": p.get("region"),
                "industry": p.get("industry"),
                "voice_profile_key": p.get("voice_profile_key"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
            }
        )
    return {"status": "ok", "tenant_id": auth.tenant_id, "brands": brands, "count": len(brands)}


def execute_create_child_brand(
    runtime: ContextRuntime, payload: BrandHierarchyRequest, auth: AuthDep
) -> dict[str, Any]:
    """Add a child brand under the parent-child brand hierarchy."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:brand-hierarchy:create", 30, 60)
    brand_key = f"brand_{_SLUG_PATTERN.sub('_', payload.child_brand_name.lower()).strip('_')}_{uuid.uuid4().hex[:6]}"
    helper_store_record(
        runtime,
        auth.tenant_id,
        "brand_hierarchy",
        "brand",
        brand_key,
        {
            "brand_name": payload.child_brand_name,
            "parent_brand_key": payload.parent_brand_key,
            "region": payload.region,
            "industry": payload.industry,
            "voice_profile_key": payload.voice_profile_key,
            "created_at": _now_iso(),
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "brand_key": brand_key, "brand_name": payload.child_brand_name}


def execute_export_analytics_csv(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Return a CSV-formatted analytics export for all channels."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:export", 20, 60)
    rows: list[dict[str, Any]] = []
    for item in runtime.scheduled_posts_memory:
        if item.get("tenant_id") != auth.tenant_id:
            continue
        rows.append(
            {
                "type": "scheduled_post",
                "platform": item.get("platform", ""),
                "content": str(item.get("content", ""))[:80],
                "status": item.get("status", ""),
                "scheduled_for": item.get("scheduled_for", ""),
                "impressions": 0,
                "engagement": 0,
            }
        )
    csv_lines = ["type,platform,content,status,scheduled_for,impressions,engagement"]
    for row in rows[:500]:
        safe_content = str(row.get("content", "")).replace('"', "'").replace(",", ";")
        csv_lines.append(
            f'''{row["type"]},{row["platform"]},"{safe_content}",{row["status"]},{row["scheduled_for"]},{row["impressions"]},{row["engagement"]}'''
        )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "export_format": "csv",
        "row_count": len(rows),
        "csv": "\n".join(csv_lines),
        "generated_at": _now_iso(),
    }
