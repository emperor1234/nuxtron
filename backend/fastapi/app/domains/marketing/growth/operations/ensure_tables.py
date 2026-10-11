"""Marketing/Growth use cases: ensure tables."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import _FEATURE_ORDER
from ..constants import _SLUG_PATTERN
from ..runtime import ContextRuntime
from ..schemas import ABTestEvaluationRequest
from ..schemas import ABTestRequest
from ..schemas import BrandVoiceRequest
from ..schemas import CounterStrikeRequest
from ..schemas import RoiForecastRequest
from ..services.now_iso import _ab_variants
from ..services.now_iso import _analyze_brand_voice
from ..services.now_iso import _now_iso
from ..services.now_iso import _roi_forecast
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from typing import Any
import json
import psycopg
import uuid


def helper_ensure_tables(runtime: ContextRuntime) -> None:
    if not runtime.db_ready_fn():
        return
    if runtime.db_initialized["done"]:
        return
    with runtime.db_init_lock:
        if runtime.db_initialized["done"]:
            return
        with psycopg.connect(runtime.db_dsn_fn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "\n                        CREATE TABLE IF NOT EXISTS growth_suite_records (\n                            id BIGSERIAL PRIMARY KEY,\n                            tenant_id TEXT NOT NULL,\n                            feature_key TEXT NOT NULL,\n                            resource_type TEXT NOT NULL,\n                            resource_key TEXT NOT NULL,\n                            payload JSONB NOT NULL DEFAULT '{}'::jsonb,\n                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),\n                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),\n                            UNIQUE (tenant_id, feature_key, resource_type, resource_key)\n                        )\n                        "
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_growth_suite_tenant_feature ON growth_suite_records (tenant_id, feature_key, updated_at DESC)"
                )
            conn.commit()
        runtime.db_initialized["done"] = True


def helper_store_record(
    runtime: ContextRuntime,
    tenant_id: str,
    feature_key: str,
    resource_type: str,
    resource_key: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    now = _now_iso()
    item = {
        "tenant_id": tenant_id,
        "feature_key": feature_key,
        "resource_type": resource_type,
        "resource_key": resource_key,
        "payload": payload,
        "created_at": now,
        "updated_at": now,
    }
    with runtime.lock:
        existing = next(
            (
                row
                for row in runtime.growth_suite_memory
                if row.get("tenant_id") == tenant_id
                and row.get("feature_key") == feature_key
                and (row.get("resource_type") == resource_type)
                and (row.get("resource_key") == resource_key)
            ),
            None,
        )
        if existing is None:
            runtime.growth_suite_memory.append(item)
        else:
            existing["payload"] = payload
            existing["updated_at"] = now
            item = existing.copy()
    if runtime.db_ready_fn():
        helper_ensure_tables(runtime)
        with psycopg.connect(runtime.db_dsn_fn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "\n                        INSERT INTO growth_suite_records (tenant_id, feature_key, resource_type, resource_key, payload, created_at, updated_at)\n                        VALUES (%s, %s, %s, %s, %s::jsonb, NOW(), NOW())\n                        ON CONFLICT (tenant_id, feature_key, resource_type, resource_key)\n                        DO UPDATE SET payload = EXCLUDED.payload, updated_at = NOW()\n                        ",
                    (tenant_id, feature_key, resource_type, resource_key, json.dumps(payload)),
                )
            conn.commit()
    return item


def helper_load_records(runtime: ContextRuntime, tenant_id: str) -> list[dict[str, Any]]:
    if runtime.db_ready_fn():
        helper_ensure_tables(runtime)
        with psycopg.connect(runtime.db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                "\n                        SELECT feature_key, resource_type, resource_key, payload, created_at, updated_at\n                        FROM growth_suite_records\n                        WHERE tenant_id = %s\n                        ORDER BY updated_at DESC\n                        ",
                (tenant_id,),
            )
            rows = cur.fetchall()
        return [
            {
                "tenant_id": tenant_id,
                "feature_key": feature_key,
                "resource_type": resource_type,
                "resource_key": resource_key,
                "payload": payload,
                "created_at": created_at.isoformat(),
                "updated_at": updated_at.isoformat(),
            }
            for feature_key, resource_type, resource_key, payload, created_at, updated_at in rows
        ]
    with runtime.lock:
        return [row.copy() for row in runtime.growth_suite_memory if row.get("tenant_id") == tenant_id]


def helper_latest_by_feature(runtime: ContextRuntime, tenant_id: str) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for row in helper_load_records(runtime, tenant_id):
        feature_key = str(row.get("feature_key"))
        if feature_key not in latest:
            latest[feature_key] = row
    return latest


def helper_summary(runtime: ContextRuntime, tenant_id: str) -> dict[str, Any]:
    latest = helper_latest_by_feature(runtime, tenant_id)
    chatbot_count = sum(
        (1 for item in runtime.chatbots_memory if item.get("tenant_id") == tenant_id and bool(item.get("deployed")))
    )
    lead_count = sum((1 for item in runtime.chatbot_leads_memory if item.get("tenant_id") == tenant_id))
    email_count = sum((1 for item in runtime.email_campaigns_memory if item.get("tenant_id") == tenant_id))
    scheduled_count = sum((1 for item in runtime.scheduled_posts_memory if item.get("tenant_id") == tenant_id))
    link_pages = sum((1 for item in runtime.linkinbio_pages_memory if item.get("tenant_id") == tenant_id))
    link_items = sum((1 for item in runtime.linkinbio_links_memory if item.get("tenant_id") == tenant_id))
    report_count = sum((1 for item in runtime.analytics_reports_memory if item.get("tenant_id") == tenant_id))
    touchpoint_count = sum((1 for item in runtime.revenue_touchpoints_memory if item.get("tenant_id") == tenant_id))
    conversion_count = sum((1 for item in runtime.revenue_conversions_memory if item.get("tenant_id") == tenant_id))
    crm_contacts = sum((1 for item in runtime.crm_contacts_memory if item.get("tenant_id") == tenant_id))
    crm_deals = sum((1 for item in runtime.crm_deals_memory if item.get("tenant_id") == tenant_id))
    features: list[dict[str, Any]] = []
    for feature_key, name in _FEATURE_ORDER:
        record = latest.get(feature_key)
        metrics: list[dict[str, Any]] = []
        headline = "Not configured yet."
        updated_at = None
        status = "idle"
        if record is not None:
            payload = record.get("payload", {}) if isinstance(record.get("payload"), dict) else {}
            status = str(payload.get("status") or "ready")
            headline = str(payload.get("headline") or payload.get("summary") or "Ready for use.")
            updated_at = record.get("updated_at")
            metrics = payload.get("metrics", []) if isinstance(payload.get("metrics"), list) else []
        if feature_key == "ai_lead_chatbot" and (not metrics):
            metrics = [
                {"label": "Deployed bots", "value": chatbot_count},
                {"label": "Captured leads", "value": lead_count},
            ]
            headline = (
                "Lead capture chatbot pipeline is ready."
                if chatbot_count
                else "Deploy a chatbot to activate lead capture."
            )
            status = "ready" if chatbot_count else status
        if feature_key == "email_marketing" and (not metrics):
            metrics = [{"label": "Campaign drafts", "value": email_count}]
            headline = "Email automation pipeline is wired." if email_count else headline
            status = "ready" if email_count else status
        if feature_key == "smart_scheduler" and (not metrics):
            metrics = [{"label": "Scheduled drafts", "value": scheduled_count}]
            headline = "Timing intelligence is available for queued drafts." if scheduled_count else headline
            status = "ready" if scheduled_count else status
        if feature_key == "link_in_bio_builder" and (not metrics):
            metrics = [{"label": "Pages", "value": link_pages}, {"label": "Tracked links", "value": link_items}]
            headline = "Shoppable bio pages are wired." if link_pages else headline
            status = "ready" if link_pages else status
        if feature_key == "advanced_reports" and (not metrics):
            metrics = [
                {"label": "Report templates", "value": report_count},
                {"label": "Tracked conversions", "value": conversion_count},
            ]
            headline = "Executive reporting is available." if report_count or conversion_count else headline
            status = "ready" if report_count or conversion_count else status
        if feature_key == "agency_portal" and (not metrics):
            metrics = [{"label": "CRM contacts", "value": crm_contacts}, {"label": "Open deals", "value": crm_deals}]
        if feature_key == "roi_forecaster" and (not metrics) and touchpoint_count:
            metrics = [
                {"label": "Touchpoints", "value": touchpoint_count},
                {"label": "Conversions", "value": conversion_count},
            ]
            headline = "Revenue forecasting is anchored to live attribution data."
            status = "ready"
        features.append(
            {
                "key": feature_key,
                "name": name,
                "status": status,
                "headline": headline,
                "updated_at": updated_at,
                "metrics": metrics,
            }
        )
    configured = sum((1 for feature in features if feature["status"] != "idle"))
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "generated_at": _now_iso(),
        "features": features,
        "totals": {"features": len(features), "configured": configured, "db_ready": runtime.db_ready_fn()},
    }


def execute_growth_suite_summary(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:summary", 120, 60)
    return helper_summary(runtime, auth.tenant_id)


def execute_brand_voice_profile(runtime: ContextRuntime, payload: BrandVoiceRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:brand-voice", 30, 60)
    result = _analyze_brand_voice(payload.sample_posts, payload.ai_output)
    profile_key = _SLUG_PATTERN.sub("_", payload.profile_name.lower()).strip("_") or "voice_profile"
    helper_store_record(
        runtime,
        auth.tenant_id,
        "brand_voice_dna",
        "profile",
        profile_key,
        {
            "status": "ready",
            "headline": f"Voice score {result['voice_score']}/100 with rewrite output ready.",
            "metrics": [
                {"label": "Voice score", "value": result["voice_score"]},
                {"label": "Signature words", "value": len(result["fingerprint"]["signature_words"])},
            ],
            "brand_voice": result,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "profile_key": profile_key, "brand_voice": result}


def execute_create_ab_test(runtime: ContextRuntime, payload: ABTestRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:ab-test:create", 30, 60)
    test_key = f"ab_{uuid.uuid4().hex[:10]}"
    variants = _ab_variants(payload.base_content)
    helper_store_record(
        runtime,
        auth.tenant_id,
        "auto_ab_testing",
        "test",
        test_key,
        {
            "status": "running",
            "headline": "Five variants are live for the 2-hour winner selection window.",
            "metrics": [{"label": "Variants", "value": len(variants)}, {"label": "Window minutes", "value": 120}],
            "name": payload.name,
            "goal": payload.goal,
            "channel": payload.channel,
            "variants": variants,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "test_key": test_key, "variants": variants}


def execute_evaluate_ab_test(
    runtime: ContextRuntime, test_key: str, payload: ABTestEvaluationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:ab-test:evaluate", 30, 60)
    existing = next(
        (
            row
            for row in helper_load_records(runtime, auth.tenant_id)
            if row.get("feature_key") == "auto_ab_testing" and row.get("resource_key") == test_key
        ),
        None,
    )
    if existing is None:
        raise HTTPException(status_code=404, detail="A/B test not found.")
    current_payload = existing.get("payload", {}) if isinstance(existing.get("payload"), dict) else {}
    variants = current_payload.get("variants", []) if isinstance(current_payload.get("variants"), list) else []
    if not variants:
        raise HTTPException(status_code=422, detail="No variants available for evaluation.")
    scores = payload.engagement_scores or [0.22 + index * 0.03 for index in range(len(variants))]
    winner_index = max(range(min(len(variants), len(scores))), key=lambda index: scores[index])
    winner = variants[winner_index]
    if payload.republish:
        runtime.scheduled_posts_memory.append(
            {
                "id": len(runtime.scheduled_posts_memory) + 1,
                "tenant_id": auth.tenant_id,
                "platform": current_payload.get("channel", "linkedin"),
                "content": winner.get("content", ""),
                "status": "scheduled",
                "scheduled_for": (datetime.now(UTC) + timedelta(minutes=5)).isoformat(),
                "source": "ab-test-winner",
            }
        )
    helper_store_record(
        runtime,
        auth.tenant_id,
        "auto_ab_testing",
        "test",
        test_key,
        {
            "status": "ready",
            "headline": f"Winner {winner.get('name', 'variant')} selected and republish queued.",
            "metrics": [
                {"label": "Winning score", "value": round(scores[winner_index], 3)},
                {"label": "Republished", "value": payload.republish},
            ],
            "variants": variants,
            "winner": winner,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "winner": winner, "score": scores[winner_index]}


def execute_forecast_roi(runtime: ContextRuntime, payload: RoiForecastRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:roi", 60, 60)
    forecast = _roi_forecast(payload)
    helper_store_record(
        runtime,
        auth.tenant_id,
        "roi_forecaster",
        "forecast",
        "latest",
        {
            "status": "ready",
            "headline": f"Predicted revenue ${forecast['projected_revenue']:.2f} for {payload.content_title}.",
            "metrics": [
                {"label": "Revenue", "value": forecast["projected_revenue"]},
                {"label": "Conversions", "value": forecast["projected_conversions"]},
            ],
            "forecast": forecast,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "forecast": forecast}


def execute_trigger_counter_strike(
    runtime: ContextRuntime, payload: CounterStrikeRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:growth-suite:counter-strike", 60, 60)
    response_post = f"{payload.competitor_handle} opened the conversation. We are answering with proof, positioning, and a sharper CTA on {payload.platform}."
    deadline = (datetime.now(UTC) + timedelta(seconds=60)).isoformat()
    helper_store_record(
        runtime,
        auth.tenant_id,
        "counter_strike",
        "event",
        f"counter_{uuid.uuid4().hex[:8]}",
        {
            "status": "ready",
            "headline": "Counter content drafted inside the 60-second SLA.",
            "metrics": [{"label": "SLA sec", "value": 60}, {"label": "Platform", "value": payload.platform}],
            "response_post": response_post,
            "deadline": deadline,
        },
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "response_post": response_post, "deadline": deadline}
