"""Crm use cases: list deals."""

from ....database import get_db_session
from ....models import Deal
from ..constants import AuthDep
from ..constants import DEAL_NOT_FOUND
from ..constants import LEAD_NOT_FOUND
from ..constants import PIPELINE_STAGES
from ..runtime import ContextRuntime
from ..schemas import ActivityCreateRequest
from ..schemas import CRMWebhookCreateRequest
from ..schemas import DealUpdateRequest
from ..schemas import LeadCreateRequest
from ..schemas import TaskCreateRequest
from .contact_to_dict import helper_create_db_activity
from .contact_to_dict import helper_create_db_lead
from .contact_to_dict import helper_deal_to_dict
from .contact_to_dict import helper_find_duplicate_db_lead
from .contact_to_dict import helper_get_db_lead
from .contact_to_dict import helper_lead_to_dict
from .contact_to_dict import helper_list_db_activities
from .contact_to_dict import helper_list_db_companies
from .contact_to_dict import helper_list_db_contacts
from .contact_to_dict import helper_list_db_deals
from .contact_to_dict import helper_list_db_leads
from .task_to_dict import helper_audit
from .task_to_dict import helper_create_db_task
from .task_to_dict import helper_find_duplicate_db_task
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_list_deals(
    runtime: ContextRuntime,
    auth: AuthDep,
    q: Annotated[str | None, Query(max_length=180)] = None,
    stage: Annotated[str | None, Query(max_length=60)] = None,
    min_value: Annotated[float, Query(ge=0.0)] = 0.0,
    max_value: Annotated[float | None, Query(ge=0.0)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:deals:list", 240, 60)
    query_text = (q or "").strip().lower()
    stage_filter = (stage or "").strip().lower()
    with get_db_session() as session:
        query = session.query(Deal).filter(Deal.tenant_id == auth.tenant_id)
        if stage_filter:
            query = query.filter(Deal.stage == stage_filter)
        query = query.filter(Deal.value >= min_value)
        if max_value is not None:
            query = query.filter(Deal.value <= max_value)
        if query_text:
            like_query = f"%{query_text}%"
            query = query.filter(Deal.title.ilike(like_query))
        total = query.count()
        deals = query.order_by(Deal.created_at.desc()).offset(offset).limit(limit).all()
        window = [helper_deal_to_dict(deal) for deal in deals]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(window),
        "total": total,
        "limit": limit,
        "offset": offset,
        "deals": window,
    }


def execute_update_deal(
    runtime: ContextRuntime, deal_id: int, payload: DealUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:deals:update", 120, 60)
    with get_db_session() as session:
        item = session.query(Deal).filter_by(id=deal_id, tenant_id=auth.tenant_id).first()
        if item is None:
            raise HTTPException(status_code=404, detail=DEAL_NOT_FOUND)
        data = dict(item.data or {})
        if payload.stage is not None:
            item.stage = payload.stage
            data["probability"] = next(
                (s["probability"] for s in PIPELINE_STAGES if s["stage"] == payload.stage),
                int(data.get("probability", 10)),
            )
        if payload.value is not None:
            item.value = payload.value
        if payload.close_date is not None:
            item.close_date = payload.close_date
        if payload.properties:
            current_properties = data.get("properties", {})
            if not isinstance(current_properties, dict):
                current_properties = {}
            current_properties.update(payload.properties)
            data["properties"] = current_properties
        item.data = data
        session.flush()
        snapshot = helper_deal_to_dict(item)
    helper_audit(runtime, auth.tenant_id, "crm_deal_updated", deal_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "deal": snapshot}


def execute_get_pipeline(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:pipeline", 180, 60)
    tenant_deals = helper_list_db_deals(auth.tenant_id)
    stage_buckets: dict[str, list[dict[str, Any]]] = {s["stage"]: [] for s in PIPELINE_STAGES}
    for deal in tenant_deals:
        stage = str(deal.get("stage", "prospect"))
        if stage not in stage_buckets:
            stage_buckets[stage] = []
        stage_buckets[stage].append(deal)
    pipeline: list[dict[str, Any]] = [
        {
            "stage": s["stage"],
            "display": s["display"],
            "probability": s["probability"],
            "count": len(stage_buckets.get(s["stage"], [])),
            "total_value": round(sum((float(d.get("value", 0)) for d in stage_buckets.get(s["stage"], []))), 2),
        }
        for s in PIPELINE_STAGES
    ]
    total_pipeline_value = round(
        sum((float(d.get("value", 0)) for d in tenant_deals if d.get("stage") not in ("closed_lost",))), 2
    )
    total_closed_won = round(sum((float(d.get("value", 0)) for d in tenant_deals if d.get("stage") == "closed_won")), 2)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "pipeline": pipeline,
        "total_pipeline_value": total_pipeline_value,
        "total_closed_won": total_closed_won,
        "total_deals": len(tenant_deals),
    }


def execute_get_summary(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:summary", 240, 60)
    contacts = helper_list_db_contacts(auth.tenant_id)
    companies = helper_list_db_companies(auth.tenant_id)
    deals = helper_list_db_deals(auth.tenant_id)
    with runtime.lock:
        activities = [a.copy() for a in runtime.activities_memory if a.get("tenant_id") == auth.tenant_id]
    open_deals = [d for d in deals if d.get("stage") not in ("closed_won", "closed_lost")]
    won_deals = [d for d in deals if d.get("stage") == "closed_won"]
    avg_score = round(sum((int(c.get("lead_score", 0)) for c in contacts)) / len(contacts) if contacts else 0, 2)
    forecast_revenue = round(
        sum((float(d.get("value", 0)) * (float(d.get("probability", 0)) / 100.0) for d in open_deals)), 2
    )
    stage_counts: dict[str, int] = {}
    for stage in PIPELINE_STAGES:
        key = stage["stage"]
        stage_counts[key] = sum((1 for d in deals if d.get("stage") == key))
    recent_activities = sorted(activities, key=lambda a: str(a.get("created_at", "")), reverse=True)[:10]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "summary": {
            "contacts": len(contacts),
            "companies": len(companies),
            "deals_total": len(deals),
            "deals_open": len(open_deals),
            "deals_won": len(won_deals),
            "pipeline_value": round(sum((float(d.get("value", 0)) for d in open_deals)), 2),
            "closed_won_value": round(sum((float(d.get("value", 0)) for d in won_deals)), 2),
            "forecast_revenue": forecast_revenue,
            "avg_lead_score": avg_score,
            "activities": len(activities),
            "stage_counts": stage_counts,
        },
        "pipeline_stages": PIPELINE_STAGES,
        "recent_activities": recent_activities,
    }


def execute_create_activity(runtime: ContextRuntime, payload: ActivityCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:activities:create", 180, 60)
    activity = helper_create_db_activity(auth.tenant_id, payload)
    helper_audit(runtime, auth.tenant_id, "crm_activity_created", int(activity["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "activity": activity}


def execute_list_activities(
    runtime: ContextRuntime,
    auth: AuthDep,
    type: Annotated[str | None, Query(max_length=40)] = None,
    contact_id: Annotated[int | None, Query(ge=1)] = None,
    deal_id: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:activities:list", 240, 60)
    items, total = helper_list_db_activities(
        auth.tenant_id,
        type_filter=(type or "").strip().lower() or None,
        contact_id=contact_id,
        deal_id=deal_id,
        limit=limit,
        offset=offset,
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "total": total,
        "limit": limit,
        "offset": offset,
        "activities": items,
    }


def execute_export_crm(
    runtime: ContextRuntime,
    auth: AuthDep,
    resource: Annotated[str, Query(pattern="^(contacts|companies|deals|activities)$")] = "contacts",
    format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:export", 20, 60)
    contact_rows = helper_list_db_contacts(auth.tenant_id) if resource == "contacts" else []
    company_rows = helper_list_db_companies(auth.tenant_id) if resource == "companies" else []
    deal_rows = helper_list_db_deals(auth.tenant_id) if resource == "deals" else []
    with runtime.lock:
        source_map = {
            "contacts": contact_rows,
            "companies": company_rows,
            "deals": deal_rows,
            "activities": [a.copy() for a in runtime.activities_memory if a.get("tenant_id") == auth.tenant_id],
        }
    rows = source_map[resource]
    if format == "json":
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "resource": resource,
            "format": format,
            "count": len(rows),
            "rows": rows,
        }
    if not rows:
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "resource": resource,
            "format": format,
            "count": 0,
            "csv": "",
        }
    headers = sorted({k for row in rows for k in row if k != "tenant_id"})
    lines = [",".join(headers)]
    for row in rows:
        values: list[str] = []
        for key in headers:
            raw = row.get(key, "")
            value = str(raw).replace('"', '""')
            values.append(f'"{value}"')
        lines.append(",".join(values))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "resource": resource,
        "format": format,
        "count": len(rows),
        "csv": "\n".join(lines),
    }


def execute_create_webhook(runtime: ContextRuntime, payload: CRMWebhookCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:webhooks:create", 40, 60)
    now = datetime.now(UTC).isoformat()
    duplicate_webhook: dict[str, Any] | None = None
    created_webhook: dict[str, Any] | None = None
    with runtime.lock:
        existing = next(
            (
                w
                for w in runtime.webhook_subscriptions_memory
                if w.get("tenant_id") == auth.tenant_id
                and str(w.get("event", "")).strip().lower() == payload.event.strip().lower()
                and (str(w.get("target_url", "")).strip().lower() == payload.target_url.strip().lower())
            ),
            None,
        )
        if existing is not None:
            duplicate_webhook = existing.copy()
        else:
            record: dict[str, Any] = {
                "id": len(runtime.webhook_subscriptions_memory) + 1,
                "tenant_id": auth.tenant_id,
                "event": payload.event,
                "target_url": payload.target_url,
                "secret_masked": payload.secret[:2] + "***" if payload.secret else "",
                "status": "active",
                "created_at": now,
                "updated_at": now,
                "last_delivery_status": None,
                "last_delivery_at": None,
            }
            runtime.webhook_subscriptions_memory.append(record)
            created_webhook = record
    if duplicate_webhook is not None:
        helper_audit(runtime, auth.tenant_id, "crm_webhook_reused", int(duplicate_webhook.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "webhook": duplicate_webhook,
            "duplicate": True,
            "created": False,
        }
    if created_webhook is None:
        raise HTTPException(status_code=500, detail="Failed to create webhook.")
    helper_audit(runtime, auth.tenant_id, "crm_webhook_created", int(created_webhook["id"]))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "webhook": created_webhook,
        "duplicate": False,
        "created": True,
    }


def execute_list_webhooks(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:webhooks:list", 120, 60)
    with runtime.lock:
        items = [w.copy() for w in runtime.webhook_subscriptions_memory if w.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda row: str(row.get("created_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "webhooks": items}


def execute_test_webhook(runtime: ContextRuntime, webhook_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:webhooks:test", 60, 60)
    now = datetime.now(UTC).isoformat()
    with runtime.lock:
        row = next(
            (
                w
                for w in runtime.webhook_subscriptions_memory
                if w.get("tenant_id") == auth.tenant_id and int(w.get("id", 0)) == webhook_id
            ),
            None,
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Webhook not found.")
        row["last_delivery_status"] = "delivered"
        row["last_delivery_at"] = now
        row["updated_at"] = now
        snapshot = row.copy()
    helper_audit(runtime, auth.tenant_id, "crm_webhook_tested", webhook_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "webhook": snapshot,
        "delivery": {
            "status": "delivered",
            "tested_at": now,
            "sample_payload": {"event": snapshot.get("event"), "tenant_id": auth.tenant_id},
        },
    }


def execute_create_lead(runtime: ContextRuntime, payload: LeadCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:leads:create", 120, 60)
    duplicate = helper_find_duplicate_db_lead(auth.tenant_id, payload)
    if duplicate is not None:
        helper_audit(runtime, auth.tenant_id, "crm_lead_reused", int(duplicate.get("id", 0)))
        return {"status": "ok", "tenant_id": auth.tenant_id, "lead": duplicate, "duplicate": True, "created": False}
    lead = helper_create_db_lead(auth.tenant_id, payload)
    helper_audit(runtime, auth.tenant_id, "crm_lead_created", int(lead["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "lead": lead, "duplicate": False, "created": True}


def execute_list_leads(
    runtime: ContextRuntime,
    auth: AuthDep,
    q: Annotated[str | None, Query(max_length=160)] = None,
    status: Annotated[str | None, Query(max_length=40)] = None,
    assigned_to: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=250)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:leads:list", 240, 60)
    items, total = helper_list_db_leads(
        auth.tenant_id,
        status=(status or "").strip() or None,
        assigned_to=(assigned_to or "").strip() or None,
        q=(q or "").strip() or None,
        limit=limit,
        offset=offset,
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "total": total,
        "limit": limit,
        "offset": offset,
        "leads": items,
    }


def execute_get_lead(runtime: ContextRuntime, lead_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:leads:get", 300, 60)
    obj = helper_get_db_lead(lead_id, auth.tenant_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=LEAD_NOT_FOUND)
    return {"status": "ok", "tenant_id": auth.tenant_id, "lead": helper_lead_to_dict(obj)}


def execute_create_task(runtime: ContextRuntime, payload: TaskCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:tasks:create", 120, 60)
    duplicate = helper_find_duplicate_db_task(auth.tenant_id, payload)
    if duplicate is not None:
        helper_audit(runtime, auth.tenant_id, "crm_task_reused", int(duplicate.get("id", 0)))
        return {"status": "ok", "tenant_id": auth.tenant_id, "task": duplicate, "duplicate": True, "created": False}
    task = helper_create_db_task(auth.tenant_id, payload)
    helper_audit(runtime, auth.tenant_id, "crm_task_created", int(task["id"]))
    return {"status": "ok", "tenant_id": auth.tenant_id, "task": task, "duplicate": False, "created": True}
