"""Automation/Workforce use cases: list capabilities."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import MissionStatus
from ..constants import PROVIDER_CATALOG
from ..runtime import ContextRuntime
from ..schemas import IntegrationConnectRequest
from ..schemas import MissionCreateRequest
from ..schemas import MissionDecisionRequest
from ..schemas import WorkforceProfileRequest
from ..services.mission_execution import _ai_gateway_url
from .now_iso import helper_audit
from .now_iso import helper_db_enabled
from .now_iso import helper_execute_mission
from .now_iso import helper_get_mission_memory
from .now_iso import helper_mask_secret
from .now_iso import helper_now_iso
from .now_iso import helper_persisted_mission_as_memory
from .now_iso import helper_queue_mission_execution
from .now_iso import helper_run_db
from .now_iso import helper_run_db_async
from .now_iso import helper_use_celery
from .now_iso import helper_verify_provider_live
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any
import hashlib
import uuid


def execute_list_capabilities(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:capabilities", 180, 60)
    capabilities = [
        {
            "role": "social_media",
            "name": "Social Media Specialist",
            "includes": ["trend analysis", "publishing", "engagement"],
        },
        {
            "role": "seo",
            "name": "SEO Specialist",
            "includes": ["technical audits", "content optimization", "serp monitoring"],
        },
        {
            "role": "geo",
            "name": "GEO Specialist",
            "includes": ["answer engine optimization", "crawler readiness", "schema coverage"],
        },
        {
            "role": "ads",
            "name": "Ads Specialist",
            "includes": ["creative testing", "budget optimization", "audience targeting"],
        },
        {
            "role": "growth_metrics",
            "name": "Growth Metrics Analyst",
            "includes": ["funnel analysis", "dashboarding", "anomaly alerts"],
        },
        {
            "role": "competitor_strategy",
            "name": "Competitor Strategist",
            "includes": ["gap analysis", "campaign tracking", "market shifts"],
        },
        {
            "role": "social_listening",
            "name": "Social Listening Analyst",
            "includes": ["brand mentions", "sentiment", "crisis alerts"],
        },
        {
            "role": "industry_news",
            "name": "Industry News Researcher",
            "includes": ["daily brief", "signal extraction", "priority tagging"],
        },
        {
            "role": "event_outreach",
            "name": "Event Outreach Specialist",
            "includes": ["prospect events", "invites", "follow-ups"],
        },
        {
            "role": "media_outreach",
            "name": "Media Outreach Specialist",
            "includes": ["press targeting", "pitch drafts", "coverage tracking"],
        },
        {
            "role": "cvr_optimization",
            "name": "CVR Optimization Specialist",
            "includes": ["hypothesis backlog", "tests", "landing optimization"],
        },
    ]
    return {"status": "ok", "capabilities": capabilities}


def execute_list_vendors(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:vendors", 120, 60)
    vendors = [
        {
            "component": "AI generation",
            "vendors": ["openai", "anthropic", "google_vertex"],
            "endpoint": _ai_gateway_url(),
            "required_env": ["FASTAPI_API_KEY", "FASTAPI_URL or NEXT_PUBLIC_FASTAPI_URL"],
        },
        {
            "component": "Slack delivery",
            "vendors": ["slack"],
            "endpoint": PROVIDER_CATALOG["slack"]["action_url"],
            "required_integration_metadata": ["channel (optional, defaults to #general)"],
        },
        {
            "component": "X publishing",
            "vendors": ["x"],
            "endpoint": PROVIDER_CATALOG["x"]["action_url"],
            "required_integration_metadata": [],
        },
    ]
    return {"status": "ok", "vendors": vendors}


def execute_upsert_profile(runtime: ContextRuntime, payload: WorkforceProfileRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:profile:upsert", 60, 60)
    now = helper_now_iso()
    with runtime._lock:
        existing = next((p for p in runtime.profiles_memory if p.get("tenant_id") == auth.tenant_id), None)
        if existing:
            existing.update(payload.model_dump())
            existing["updated_at"] = now
            profile = existing
        else:
            profile = {
                "id": str(uuid.uuid4()),
                "tenant_id": auth.tenant_id,
                **payload.model_dump(),
                "created_at": now,
                "updated_at": now,
            }
            runtime.profiles_memory.append(profile)
    persisted = (
        helper_run_db(
            runtime,
            runtime._db.upsert_profile(
                auth.tenant_id,
                payload.company_name,
                payload.website,
                payload.target_markets,
                payload.preferred_channels,
                payload.brand_tone,
                payload.goals,
            ),
        )
        if helper_db_enabled(runtime)
        else None
    )
    if isinstance(persisted, dict) and persisted:
        profile = persisted
    helper_audit(runtime, auth.tenant_id, "workforce_profile_upserted", payload.company_name)
    return {"status": "ok", "profile": profile}


def execute_get_profile(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:profile:get", 120, 60)
    with runtime._lock:
        profile = next((p.copy() for p in runtime.profiles_memory if p.get("tenant_id") == auth.tenant_id), None)
    if profile is None and helper_db_enabled(runtime):
        persisted = helper_run_db(runtime, runtime._db.get_profile(auth.tenant_id))
        if isinstance(persisted, dict) and persisted:
            profile = persisted
    if profile is None:
        raise HTTPException(status_code=404, detail="Workforce profile not found.")
    return {"status": "ok", "profile": profile}


def execute_integration_catalog(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:integrations:catalog", 180, 60)
    with runtime._lock:
        connected = {
            str(c.get("provider"))
            for c in runtime.integrations_memory
            if c.get("tenant_id") == auth.tenant_id and c.get("status") == "connected"
        }
    rows = []
    for key, entry in PROVIDER_CATALOG.items():
        rows.append(
            {
                "provider": key,
                "name": entry["name"],
                "kind": entry["kind"],
                "auth_type": entry["auth_type"],
                "connected": key in connected,
                "test_url": entry["test_url"],
            }
        )
    return {"status": "ok", "providers": rows}


async def execute_connect_integration(
    runtime: ContextRuntime, payload: IntegrationConnectRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:integrations:connect", 60, 60)
    provider = payload.provider.strip().lower()
    if provider not in PROVIDER_CATALOG:
        raise HTTPException(status_code=422, detail="Unsupported provider.")
    if "action_url" in payload.metadata:
        raise HTTPException(
            status_code=422,
            detail="Custom action endpoints require a separately scoped webhook integration.",
        )
    if not payload.access_token and (not payload.secret_ref):
        raise HTTPException(status_code=422, detail="Either access_token or secret_ref is required.")
    verify_ok = False
    verify_status = 0
    verify_payload: dict[str, Any] = {}
    if payload.access_token:
        verify_ok, verify_status, verify_payload = await helper_verify_provider_live(provider, payload.access_token)
        if not verify_ok:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Provider verification failed.",
                    "provider": provider,
                    "status_code": verify_status,
                    "response": verify_payload,
                },
            )
    now = helper_now_iso()
    token_hash = hashlib.sha256((payload.access_token or "").encode()).hexdigest() if payload.access_token else ""
    with runtime._lock:
        existing = next(
            (
                i
                for i in runtime.integrations_memory
                if i.get("tenant_id") == auth.tenant_id and i.get("provider") == provider
            ),
            None,
        )
        record = {
            "id": existing.get("id") if existing else str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "provider": provider,
            "provider_name": PROVIDER_CATALOG[provider]["name"],
            "status": "connected",
            "token_hash": token_hash,
            "token_preview": helper_mask_secret(payload.access_token) if payload.access_token else None,
            "secret_ref": payload.secret_ref,
            "account_id": payload.account_id,
            "metadata": payload.metadata,
            "last_verified_at": now,
            "last_verified_status": verify_status,
            "last_verified_response": verify_payload,
            "last_verified_token": payload.access_token or existing.get("last_verified_token", "")
            if existing
            else payload.access_token or "",
            "updated_at": now,
            "created_at": existing.get("created_at", now) if existing else now,
        }
        if existing:
            existing.update(record)
        else:
            runtime.integrations_memory.append(record)
    if helper_db_enabled(runtime):
        await helper_run_db_async(
            runtime,
            runtime._db.upsert_integration(
                auth.tenant_id,
                provider,
                "connected",
                token_hash,
                record.get("token_preview"),
                payload.secret_ref,
                payload.account_id,
                payload.metadata,
                verify_status,
                verify_payload,
            ),
        )
    helper_audit(runtime, auth.tenant_id, "workforce_integration_connected", provider)
    return {"status": "ok", "integration": record, "verified": verify_ok}


def execute_list_integrations(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:integrations:list", 120, 60)
    with runtime._lock:
        rows = [r.copy() for r in runtime.integrations_memory if r.get("tenant_id") == auth.tenant_id]
    if not rows and helper_db_enabled(runtime):
        persisted = helper_run_db(runtime, runtime._db.list_integrations(auth.tenant_id))
        if isinstance(persisted, list):
            rows = persisted
    for row in rows:
        row.pop("last_verified_token", None)
    return {"status": "ok", "integrations": rows, "total": len(rows)}


def execute_create_mission(runtime: ContextRuntime, payload: MissionCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:missions:create", 60, 60)
    now = helper_now_iso()
    mission_status: MissionStatus = "pending_approval" if payload.requires_approval else "approved"
    mission = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "title": payload.title,
        "description": payload.description,
        "role": payload.role,
        "objective": payload.objective,
        "providers": [p.strip().lower() for p in payload.providers if p.strip()],
        "requires_approval": payload.requires_approval,
        "status": mission_status,
        "input_context": payload.input_context,
        "created_at": now,
        "updated_at": now,
        "approved_at": None,
        "executed_at": None,
    }
    feed_item = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "mission_id": mission["id"],
        "type": "mission_created",
        "status": mission_status,
        "title": payload.title,
        "summary": payload.objective,
        "created_at": now,
    }
    with runtime._lock:
        runtime.missions_memory.append(mission)
        runtime.feed_memory.append(feed_item)
    persisted = (
        helper_run_db(
            runtime,
            runtime._db.create_mission(
                auth.tenant_id,
                payload.title,
                payload.description,
                payload.role,
                payload.objective,
                payload.requires_approval,
                mission.get("providers", []),
                payload.input_context,
            ),
        )
        if helper_db_enabled(runtime)
        else None
    )
    if isinstance(persisted, dict) and persisted:
        mission.update(persisted)
    helper_audit(runtime, auth.tenant_id, "workforce_mission_created", payload.title)
    return {"status": "ok", "mission": mission, "feed_item": feed_item}


def execute_list_missions(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:missions:list", 120, 60)
    with runtime._lock:
        rows = [
            m.copy()
            for m in runtime.missions_memory
            if m.get("tenant_id") == auth.tenant_id and (not status or m.get("status") == status)
        ]
    if helper_db_enabled(runtime):
        persisted = helper_run_db(runtime, runtime._db.list_missions(auth.tenant_id, status=status, limit=limit))
        if isinstance(persisted, list) and persisted:
            rows = persisted
    return {"status": "ok", "missions": rows[-limit:], "total": len(rows)}


async def execute_approve_mission(
    runtime: ContextRuntime, mission_id: str, payload: MissionDecisionRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:missions:approve", 60, 60)
    mission = helper_get_mission_memory(runtime, auth.tenant_id, mission_id)
    if mission is None and helper_db_enabled(runtime):
        mission = helper_persisted_mission_as_memory(runtime, auth.tenant_id, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found.")
    if mission.get("status") in {"completed", "failed", "rejected"}:
        raise HTTPException(status_code=409, detail="Mission is already finalized.")
    with runtime._lock:
        mission["status"] = "approved"
        mission["approved_at"] = helper_now_iso()
        mission["updated_at"] = helper_now_iso()
        runtime.feed_memory.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": auth.tenant_id,
                "mission_id": mission_id,
                "type": "mission_approved",
                "status": "approved",
                "title": mission.get("title"),
                "summary": payload.note or "Approved for execution",
                "created_at": helper_now_iso(),
            }
        )
        mission["status"] = "running"
    use_celery = helper_use_celery()
    if use_celery:
        outcome = helper_queue_mission_execution(runtime, auth.tenant_id, mission, "approval_celery")
    else:
        outcome = await helper_execute_mission(runtime, auth.tenant_id, mission)
    if helper_db_enabled(runtime):
        await helper_run_db_async(
            runtime, runtime._db.approve_mission(auth.tenant_id, mission_id, auth.tenant_id, payload.note or "")
        )
        await helper_run_db_async(
            runtime,
            runtime._db.create_outcome(
                auth.tenant_id,
                mission_id,
                str(outcome.get("status", "queued" if use_celery else "failed")),
                int(outcome.get("success_count", 0)),
                int(outcome.get("failed_count", 0)),
                outcome.get("provider_results", []),
                outcome.get("artifact", {}),
                "celery_queue" if use_celery else "manual_approval",
            ),
        )
    with runtime._lock:
        runtime.feed_memory.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": auth.tenant_id,
                "mission_id": mission_id,
                "type": "mission_result",
                "status": mission.get("status"),
                "title": mission.get("title"),
                "summary": f"success={outcome['success_count']} failed={outcome['failed_count']}",
                "created_at": helper_now_iso(),
            }
        )
    helper_audit(runtime, auth.tenant_id, "workforce_mission_approved", mission_id)
    return {"status": "ok", "mission": mission, "outcome": outcome}


def execute_live_feed(
    runtime: ContextRuntime, auth: AuthDep, limit: Annotated[int, Query(ge=1, le=1000)] = 100
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:feed", 180, 60)
    with runtime._lock:
        rows = [f.copy() for f in runtime.feed_memory if f.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "items": rows[-limit:], "total": len(rows)}


def execute_list_schedules(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:schedules:list", 120, 60)
    with runtime._lock:
        rows = [s.copy() for s in runtime.schedules_memory if s.get("tenant_id") == auth.tenant_id]
    if helper_db_enabled(runtime):
        persisted = helper_run_db(runtime, runtime._db.list_schedules(auth.tenant_id))
        if isinstance(persisted, list) and persisted:
            rows = persisted
    return {"status": "ok", "schedules": rows, "total": len(rows)}
