"""Crm use cases: create api token."""

from ....database import get_db_session
from ....models import Contact
from ....models import Deal
from ....models import Lead
from ....models import Task
from ....models import Ticket
from ..constants import AuthDep
from ..constants import PIPELINE_STAGES
from ..runtime import ContextRuntime
from ..schemas import APITokenCreateRequest
from ..schemas import CRMBackupConfigRequest
from ..schemas import CRMLiveSyncToggleRequest
from .contact_to_dict import helper_contact_to_dict
from .contact_to_dict import helper_deal_to_dict
from .contact_to_dict import helper_lead_to_dict
from .get_live_sync_state import helper_get_live_sync_state
from .get_live_sync_state import helper_is_in_window
from .get_live_sync_state import helper_to_window_days
from .task_to_dict import helper_audit
from .task_to_dict import helper_get_backup_config
from .task_to_dict import helper_next_full_backup_utc
from .task_to_dict import helper_task_to_dict
from .task_to_dict import helper_ticket_to_dict
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any
import hashlib


def execute_create_api_token(runtime: ContextRuntime, payload: APITokenCreateRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:api-tokens:create", 30, 60)
    now = datetime.now(UTC).isoformat()
    duplicate_token: dict[str, Any] | None = None
    created_token: dict[str, Any] | None = None
    normalized_name = payload.name.strip().lower()
    normalized_scopes = sorted({scope.strip().lower() for scope in payload.scopes if scope.strip()})
    with runtime.lock:
        existing = next(
            (
                t
                for t in runtime.api_tokens_memory
                if t.get("tenant_id") == auth.tenant_id
                and str(t.get("name", "")).strip().lower() == normalized_name
                and (
                    sorted({str(scope).strip().lower() for scope in t.get("scopes", []) if str(scope).strip()})
                    == normalized_scopes
                )
            ),
            None,
        )
        if existing is not None:
            duplicate_token = existing.copy()
        else:
            raw = f"{auth.tenant_id}:{payload.name}:{now}:{len(runtime.api_tokens_memory) + 1}"
            token_preview = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            token: dict[str, Any] = {
                "id": len(runtime.api_tokens_memory) + 1,
                "tenant_id": auth.tenant_id,
                "name": payload.name,
                "scopes": payload.scopes,
                "token_prefix": token_preview[:12],
                "created_at": now,
                "last_used_at": None,
                "status": "active",
            }
            runtime.api_tokens_memory.append(token)
            created_token = token
    if duplicate_token is not None:
        helper_audit(runtime, auth.tenant_id, "crm_api_token_reused", int(duplicate_token.get("id", 0)))
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "api_token": duplicate_token,
            "token_hint": str(duplicate_token.get("token_prefix", "")),
            "duplicate": True,
            "created": False,
        }
    if created_token is None:
        raise HTTPException(status_code=500, detail="Failed to create API token.")
    helper_audit(runtime, auth.tenant_id, "crm_api_token_created", int(created_token["id"]))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "api_token": created_token,
        "token_hint": str(created_token.get("token_prefix", "")),
        "duplicate": False,
        "created": True,
    }


def execute_list_api_tokens(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:api-tokens:list", 120, 60)
    with runtime.lock:
        items = [t.copy() for t in runtime.api_tokens_memory if t.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda t: str(t.get("created_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "api_tokens": items}


def execute_get_forecast(
    runtime: ContextRuntime, auth: AuthDep, days: Annotated[int, Query(ge=7, le=365)] = 30
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:reports:forecast", 120, 60)
    now = datetime.now(UTC)
    window_days = helper_to_window_days(days)
    window_start = now - timedelta(days=window_days)
    with runtime.lock:
        tenant_deals = [d.copy() for d in runtime.deals_memory if d.get("tenant_id") == auth.tenant_id]
        tenant_invoices = [i.copy() for i in runtime.crm_invoices_memory if i.get("tenant_id") == auth.tenant_id]
    tenant_deals = [
        d
        for d in tenant_deals
        if helper_is_in_window(d.get("created_at") or d.get("updated_at") or d.get("close_date"), window_start)
    ]
    tenant_invoices = [
        i
        for i in tenant_invoices
        if helper_is_in_window(i.get("created_at") or i.get("updated_at") or i.get("due_date"), window_start)
    ]
    open_deals = [d for d in tenant_deals if d.get("stage") not in ("closed_won", "closed_lost")]
    won_deals = [d for d in tenant_deals if d.get("stage") == "closed_won"]
    weighted_pipeline = round(
        sum((float(d.get("value", 0)) * float(d.get("probability", 0)) / 100.0 for d in open_deals)), 2
    )
    closed_won_total = round(sum((float(d.get("value", 0)) for d in won_deals)), 2)
    outstanding_invoices = round(
        sum((float(i.get("amount", 0)) for i in tenant_invoices if i.get("status") == "pending")), 2
    )
    paid_invoices = round(sum((float(i.get("amount", 0)) for i in tenant_invoices if i.get("status") == "paid")), 2)
    monthly: dict[str, float] = {}
    for d in open_deals:
        month = str(d.get("close_date", ""))[:7] or "unknown"
        monthly.setdefault(month, 0.0)
        monthly[month] += float(d.get("value", 0)) * float(d.get("probability", 0)) / 100.0
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "window_days": window_days,
        "weighted_pipeline": weighted_pipeline,
        "closed_won_total": closed_won_total,
        "outstanding_invoices": outstanding_invoices,
        "paid_invoices": paid_invoices,
        "monthly_forecast": {k: round(v, 2) for k, v in sorted(monthly.items())},
    }


def execute_get_kpis(
    runtime: ContextRuntime, auth: AuthDep, days: Annotated[int, Query(ge=7, le=365)] = 30
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:reports:kpis", 120, 60)
    now = datetime.now(UTC)
    window_days = helper_to_window_days(days)
    window_start = now - timedelta(days=window_days)
    with runtime.lock:
        tenant_contacts = [c for c in runtime.contacts_memory if c.get("tenant_id") == auth.tenant_id]
        tenant_deals = [d for d in runtime.deals_memory if d.get("tenant_id") == auth.tenant_id]
        tenant_leads = [l for l in runtime.leads_memory if l.get("tenant_id") == auth.tenant_id]
        tenant_tickets = [t for t in runtime.tickets_memory if t.get("tenant_id") == auth.tenant_id]
        tenant_tasks = [t for t in runtime.tasks_memory if t.get("tenant_id") == auth.tenant_id]
    tenant_contacts = [c for c in tenant_contacts if helper_is_in_window(c.get("created_at"), window_start)]
    tenant_deals = [
        d
        for d in tenant_deals
        if helper_is_in_window(d.get("created_at") or d.get("updated_at") or d.get("close_date"), window_start)
    ]
    tenant_leads = [
        l for l in tenant_leads if helper_is_in_window(l.get("created_at") or l.get("updated_at"), window_start)
    ]
    tenant_tickets = [
        t for t in tenant_tickets if helper_is_in_window(t.get("created_at") or t.get("updated_at"), window_start)
    ]
    tenant_tasks = [
        t
        for t in tenant_tasks
        if helper_is_in_window(t.get("created_at") or t.get("updated_at") or t.get("due_date"), window_start)
    ]
    won_deals = [d for d in tenant_deals if d.get("stage") == "closed_won"]
    lost_deals = [d for d in tenant_deals if d.get("stage") == "closed_lost"]
    total_closed = len(won_deals) + len(lost_deals)
    win_rate = round(len(won_deals) / total_closed * 100, 1) if total_closed > 0 else 0.0
    converted_leads = [l for l in tenant_leads if l.get("status") == "converted"]
    lead_conversion_rate = round(len(converted_leads) / len(tenant_leads) * 100, 1) if tenant_leads else 0.0
    open_tickets = [t for t in tenant_tickets if t.get("status") == "open"]
    escalated_tickets = [t for t in tenant_tickets if t.get("escalated")]
    avg_deal_value = (
        round(sum((float(d.get("value", 0)) for d in tenant_deals)) / len(tenant_deals), 2) if tenant_deals else 0.0
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "kpis": {
            "total_contacts": len(tenant_contacts),
            "total_leads": len(tenant_leads),
            "lead_conversion_rate_pct": lead_conversion_rate,
            "total_deals": len(tenant_deals),
            "win_rate_pct": win_rate,
            "avg_deal_value": avg_deal_value,
            "closed_won_value": round(sum((float(d.get("value", 0)) for d in won_deals)), 2),
            "open_tickets": len(open_tickets),
            "escalated_tickets": len(escalated_tickets),
            "open_tasks": len([t for t in tenant_tasks if t.get("status") == "open"]),
            "overdue_tasks": len(
                [
                    t
                    for t in tenant_tasks
                    if t.get("status") == "open" and str(t.get("due_date", "")) < datetime.now(UTC).date().isoformat()
                ]
            ),
        },
        "window_days": window_days,
    }


def execute_get_executive_analytics(
    runtime: ContextRuntime, auth: AuthDep, days: Annotated[int, Query(ge=7, le=365)] = 30
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:reports:executive", 90, 60)
    now = datetime.now(UTC)
    window_days = helper_to_window_days(days)
    window_start = now - timedelta(days=window_days)
    with runtime.lock:
        tenant_contacts = [c.copy() for c in runtime.contacts_memory if c.get("tenant_id") == auth.tenant_id]
        tenant_deals = [d.copy() for d in runtime.deals_memory if d.get("tenant_id") == auth.tenant_id]
        tenant_leads = [l.copy() for l in runtime.leads_memory if l.get("tenant_id") == auth.tenant_id]
        tenant_tickets = [t.copy() for t in runtime.tickets_memory if t.get("tenant_id") == auth.tenant_id]
        tenant_tasks = [t.copy() for t in runtime.tasks_memory if t.get("tenant_id") == auth.tenant_id]
    with get_db_session() as session:
        db_contacts = [
            helper_contact_to_dict(row)
            for row in session.query(Contact).filter(Contact.tenant_id == auth.tenant_id).all()
        ]
        db_deals = [
            helper_deal_to_dict(row) for row in session.query(Deal).filter(Deal.tenant_id == auth.tenant_id).all()
        ]
        db_leads = [
            helper_lead_to_dict(row) for row in session.query(Lead).filter(Lead.tenant_id == auth.tenant_id).all()
        ]
        db_tickets = [
            helper_ticket_to_dict(row) for row in session.query(Ticket).filter(Ticket.tenant_id == auth.tenant_id).all()
        ]
        db_tasks = [
            helper_task_to_dict(row) for row in session.query(Task).filter(Task.tenant_id == auth.tenant_id).all()
        ]

    def _merge_items(mem_rows: list[dict[str, Any]], db_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for row in db_rows:
            merged[f"db:{int(row.get('id', 0))}"] = row
        for row in mem_rows:
            row_id = int(row.get("id", 0))
            key = f"db:{row_id}" if row_id > 0 and f"db:{row_id}" in merged else f"mem:{row_id}:{len(merged)}"
            merged[key] = row
        return list(merged.values())

    tenant_contacts = _merge_items(tenant_contacts, db_contacts)
    tenant_deals = _merge_items(tenant_deals, db_deals)
    tenant_leads = _merge_items(tenant_leads, db_leads)
    tenant_tickets = _merge_items(tenant_tickets, db_tickets)
    tenant_tasks = _merge_items(tenant_tasks, db_tasks)
    tenant_contacts = [c for c in tenant_contacts if helper_is_in_window(c.get("created_at"), window_start)]
    tenant_deals = [
        d
        for d in tenant_deals
        if helper_is_in_window(d.get("created_at") or d.get("updated_at") or d.get("close_date"), window_start)
    ]
    tenant_leads = [
        l for l in tenant_leads if helper_is_in_window(l.get("created_at") or l.get("updated_at"), window_start)
    ]
    tenant_tickets = [
        t for t in tenant_tickets if helper_is_in_window(t.get("created_at") or t.get("updated_at"), window_start)
    ]
    tenant_tasks = [
        t
        for t in tenant_tasks
        if helper_is_in_window(t.get("created_at") or t.get("updated_at") or t.get("due_date"), window_start)
    ]
    stage_counts: dict[str, int] = {stage["stage"]: 0 for stage in PIPELINE_STAGES}
    for deal in tenant_deals:
        stage = str(deal.get("stage", "prospect"))
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    funnel = [
        {"stage": stage["stage"], "display": stage["display"], "count": stage_counts.get(stage["stage"], 0)}
        for stage in PIPELINE_STAGES
    ]
    revenue_trend: dict[str, float] = {}
    for deal in tenant_deals:
        if str(deal.get("stage", "")) != "closed_won":
            continue
        close_date = str(deal.get("close_date") or deal.get("updated_at") or deal.get("created_at") or "")
        month = close_date[:7] if len(close_date) >= 7 else now.strftime("%Y-%m")
        revenue_trend.setdefault(month, 0.0)
        revenue_trend[month] += float(deal.get("value", 0.0))
    sorted_months = sorted(revenue_trend.keys())[-6:]
    monthly_closed_won = [{"month": month, "value": round(revenue_trend[month], 2)} for month in sorted_months]
    lead_source_breakdown: dict[str, int] = {}
    for lead in tenant_leads:
        source = str(lead.get("source", "unknown")).strip().lower() or "unknown"
        lead_source_breakdown[source] = lead_source_breakdown.get(source, 0) + 1
    overdue_tasks = len(
        [
            task
            for task in tenant_tasks
            if str(task.get("status", "")) == "open" and str(task.get("due_date", "")) < now.date().isoformat()
        ]
    )
    escalated_tickets = len([ticket for ticket in tenant_tickets if bool(ticket.get("escalated"))])
    anomalies: list[dict[str, Any]] = []
    if overdue_tasks > 0:
        anomalies.append(
            {"type": "task_overdue", "severity": "medium", "detail": f"{overdue_tasks} overdue open tasks"}
        )
    if tenant_tickets and escalated_tickets / len(tenant_tickets) >= 0.2:
        anomalies.append({"type": "support_risk", "severity": "high", "detail": "Escalation ratio is above 20%"})
    open_stage_total = sum(
        (count for stage, count in stage_counts.items() if stage not in ("closed_won", "closed_lost"))
    )
    negotiation_share = stage_counts.get("negotiation", 0) / open_stage_total if open_stage_total else 0.0
    if negotiation_share >= 0.6:
        anomalies.append(
            {
                "type": "pipeline_congestion",
                "severity": "medium",
                "detail": "Open pipeline is concentrated in negotiation stage",
            }
        )
    total_contacts = len(tenant_contacts)
    converted_leads = len([lead for lead in tenant_leads if str(lead.get("status", "")) == "converted"])
    conversion_rate = round(converted_leads / len(tenant_leads) * 100, 1) if tenant_leads else 0.0
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "generated_at": now.isoformat(),
        "window_days": window_days,
        "overview": {
            "total_contacts": total_contacts,
            "total_deals": len(tenant_deals),
            "total_leads": len(tenant_leads),
            "lead_conversion_rate_pct": conversion_rate,
            "escalated_ticket_ratio_pct": round(escalated_tickets / len(tenant_tickets) * 100, 1)
            if tenant_tickets
            else 0.0,
            "overdue_tasks": overdue_tasks,
        },
        "charts": {
            "pipeline_funnel": funnel,
            "monthly_closed_won": monthly_closed_won,
            "lead_source_breakdown": lead_source_breakdown,
        },
        "anomalies": anomalies,
    }


def execute_get_backup_ops(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:ops:backup:get", 120, 60)
    now = datetime.now(UTC)
    with runtime.lock:
        config = helper_get_backup_config(runtime, auth.tenant_id).copy()
        snapshots = [
            row.copy()
            for row in runtime.backup_snapshots_memory
            if row.get("tenant_id") == auth.tenant_id and row.get("type") == "snapshot"
        ]
    snapshots.sort(key=lambda row: str(row.get("started_at", "")), reverse=True)
    latest_incremental = next((row for row in snapshots if row.get("mode") == "incremental"), None)
    latest_full = next((row for row in snapshots if row.get("mode") == "full"), None)
    next_incremental_at = now + timedelta(minutes=int(config.get("incremental_minutes", 5)))
    next_full_at = helper_next_full_backup_utc(runtime, config, now)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "config": config,
        "latest_incremental": latest_incremental,
        "latest_full": latest_full,
        "snapshot_count": len(snapshots),
        "next_runs": {"incremental_at": next_incremental_at.isoformat(), "full_at": next_full_at.isoformat()},
        "schedule_health": "healthy" if bool(config.get("enabled", True)) else "paused",
    }


def execute_update_backup_config(
    runtime: ContextRuntime, payload: CRMBackupConfigRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:ops:backup:config", 60, 60)
    now_iso = datetime.now(UTC).isoformat()
    with runtime.lock:
        config = helper_get_backup_config(runtime, auth.tenant_id)
        config["incremental_minutes"] = payload.incremental_minutes
        config["full_backup_weekday"] = payload.full_backup_weekday
        config["full_backup_hour_utc"] = payload.full_backup_hour_utc
        config["retention_days"] = payload.retention_days
        config["enabled"] = payload.enabled
        config["updated_at"] = now_iso
        snapshot = config.copy()
    helper_audit(runtime, auth.tenant_id, "crm_backup_config_updated", int(snapshot.get("id", 0)))
    return {"status": "ok", "tenant_id": auth.tenant_id, "config": snapshot}


def execute_toggle_live_sync(
    runtime: ContextRuntime, payload: CRMLiveSyncToggleRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:crm:ops:sync:toggle", 60, 60)
    now_iso = datetime.now(UTC).isoformat()
    with runtime.lock:
        state = helper_get_live_sync_state(runtime, auth.tenant_id)
        state["enabled"] = payload.enabled
        state["interval_seconds"] = payload.interval_seconds
        state["updated_at"] = now_iso
        snapshot = state.copy()
    helper_audit(runtime, auth.tenant_id, "crm_live_sync_toggled", int(snapshot.get("id", 0)))
    return {"status": "ok", "tenant_id": auth.tenant_id, "sync": snapshot}
