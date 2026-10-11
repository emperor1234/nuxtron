"""Workflow use cases: remediation cadence forecast."""

from ..constants import AuthDep
from ..graph import coerce_int as _coerce_int
from ..graph import parse_iso
from ..reliability import default_reliability_policy
from ..reliability import ensure_reliability_fields
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorUpsertRequest
from ..service import append_audit
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_remediation_cadence_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-cadence-forecast:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    owner_open_items: dict[str, int] = {}
    open_action_items = 0
    overdue_open_items = 0
    due_within_24h = 0
    unassigned_open_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
            open_action_items += 1
            due_at = parse_iso(action_item.get("due_at"))
            if due_at < now:
                overdue_open_items += 1
            elif due_at <= now + timedelta(hours=24):
                due_within_24h += 1
            if owner == "unassigned":
                unassigned_open_items += 1
    named_owner_counts = [count for owner, count in owner_open_items.items() if owner != "unassigned"]
    owner_cadence_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    cadence_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
    required_daily_cadence_actions = (cadence_load + days_horizon - 1) // days_horizon if cadence_load > 0 else 0
    remediation_cadence_score = 100.0
    remediation_cadence_score -= owner_cadence_gap * 5
    remediation_cadence_score -= overdue_open_items * 7
    remediation_cadence_score -= due_within_24h * 4
    remediation_cadence_score -= unassigned_open_items * 9
    remediation_cadence_score -= len(open_escalations) * 6
    remediation_cadence_score = round(max(0.0, remediation_cadence_score), 2)
    if remediation_cadence_score >= 80:
        cadence_band = "steady"
    elif remediation_cadence_score >= 55:
        cadence_band = "watch"
    else:
        cadence_band = "choppy"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_cadence_score": remediation_cadence_score,
        "cadence_band": cadence_band,
        "required_daily_cadence_actions": required_daily_cadence_actions,
        "cadence_load": cadence_load,
        "owner_cadence_gap": owner_cadence_gap,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_cadence_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-cadence-index:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    owner_open_items: dict[str, int] = {}
    total_open_items = 0
    overdue_open_items = 0
    due_within_24h = 0
    unassigned_open_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
            total_open_items += 1
            due_at = parse_iso(action_item.get("due_at"))
            if due_at < now:
                overdue_open_items += 1
            elif due_at <= now + timedelta(hours=24):
                due_within_24h += 1
            if owner == "unassigned":
                unassigned_open_items += 1
    named_owner_counts = [count for owner, count in owner_open_items.items() if owner != "unassigned"]
    overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
    owner_cadence_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_cadence_index = 100.0
    escalation_cadence_index -= owner_cadence_gap * 5
    escalation_cadence_index -= overdue_open_items * 7
    escalation_cadence_index -= due_within_24h * 4
    escalation_cadence_index -= unassigned_open_items * 9
    escalation_cadence_index -= len(open_escalations) * 6
    escalation_cadence_index -= overloaded_owner_count * 8
    escalation_cadence_index = round(max(0.0, escalation_cadence_index), 2)
    if escalation_cadence_index >= 80:
        cadence_band = "steady"
    elif escalation_cadence_index >= 55:
        cadence_band = "watch"
    else:
        cadence_band = "choppy"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_cadence_index": escalation_cadence_index,
        "cadence_band": cadence_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_cadence_gap": owner_cadence_gap,
    }


def execute_get_postmortem_action_item_remediation_stability_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-stability-forecast:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    owner_open_items: dict[str, int] = {}
    open_action_items = 0
    overdue_open_items = 0
    due_within_24h = 0
    unassigned_open_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
            open_action_items += 1
            due_at = parse_iso(action_item.get("due_at"))
            if due_at < now:
                overdue_open_items += 1
            elif due_at <= now + timedelta(hours=24):
                due_within_24h += 1
            if owner == "unassigned":
                unassigned_open_items += 1
    named_owner_counts = [count for owner, count in owner_open_items.items() if owner != "unassigned"]
    owner_stability_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    stability_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
    required_daily_stability_actions = (stability_load + days_horizon - 1) // days_horizon if stability_load > 0 else 0
    remediation_stability_score = 100.0
    remediation_stability_score -= owner_stability_gap * 5
    remediation_stability_score -= overdue_open_items * 7
    remediation_stability_score -= due_within_24h * 4
    remediation_stability_score -= unassigned_open_items * 9
    remediation_stability_score -= len(open_escalations) * 6
    remediation_stability_score = round(max(0.0, remediation_stability_score), 2)
    if remediation_stability_score >= 80:
        stability_band = "stable"
    elif remediation_stability_score >= 55:
        stability_band = "watch"
    else:
        stability_band = "volatile"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_stability_score": remediation_stability_score,
        "stability_band": stability_band,
        "required_daily_stability_actions": required_daily_stability_actions,
        "stability_load": stability_load,
        "owner_stability_gap": owner_stability_gap,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_stability_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-stability-index:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    owner_open_items: dict[str, int] = {}
    total_open_items = 0
    overdue_open_items = 0
    due_within_24h = 0
    unassigned_open_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
            total_open_items += 1
            due_at = parse_iso(action_item.get("due_at"))
            if due_at < now:
                overdue_open_items += 1
            elif due_at <= now + timedelta(hours=24):
                due_within_24h += 1
            if owner == "unassigned":
                unassigned_open_items += 1
    named_owner_counts = [count for owner, count in owner_open_items.items() if owner != "unassigned"]
    overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
    owner_stability_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_stability_index = 100.0
    escalation_stability_index -= owner_stability_gap * 5
    escalation_stability_index -= overdue_open_items * 7
    escalation_stability_index -= due_within_24h * 4
    escalation_stability_index -= unassigned_open_items * 9
    escalation_stability_index -= len(open_escalations) * 6
    escalation_stability_index -= overloaded_owner_count * 8
    escalation_stability_index = round(max(0.0, escalation_stability_index), 2)
    if escalation_stability_index >= 80:
        stability_band = "stable"
    elif escalation_stability_index >= 55:
        stability_band = "watch"
    else:
        stability_band = "volatile"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_stability_index": escalation_stability_index,
        "stability_band": stability_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_stability_gap": owner_stability_gap,
    }


def execute_get_postmortem_compliance_rollups(
    runtime: WorkflowRuntime, auth: AuthDep, weeks: Annotated[int, Query(ge=1, le=26)] = 4
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:compliance:rollups", 120, 60)
    now = datetime.now(UTC)
    week_rollups: list[dict[str, Any]] = []
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
    for idx in range(weeks):
        period_end = now - timedelta(days=idx * 7)
        period_start = period_end - timedelta(days=7)
        created = [p for p in tenant_postmortems if period_start <= parse_iso(p.get("created_at")) < period_end]
        closed = [
            p
            for p in tenant_postmortems
            if p.get("status") == "closed" and period_start <= parse_iso(p.get("closed_at")) < period_end
        ]
        closed_within_sla = [p for p in closed if str(p.get("closure_sla_status", "")).lower() == "met"]
        open_overdue_actions = 0
        for p in tenant_postmortems:
            if p.get("status") == "closed":
                continue
            for item in p.get("action_items_detailed") or []:
                if str(item.get("status", "")).lower() == "done":
                    continue
                if parse_iso(item.get("due_at")) < now:
                    open_overdue_actions += 1
        closure_rate_pct = round(len(closed) / len(created) * 100, 2) if created else 100.0
        sla_compliance_pct = round(len(closed_within_sla) / len(closed) * 100, 2) if closed else 100.0
        week_rollups.append(
            {
                "week_start": period_start.isoformat(),
                "week_end": period_end.isoformat(),
                "postmortems_created": len(created),
                "postmortems_closed": len(closed),
                "closed_within_sla": len(closed_within_sla),
                "closure_rate_pct": closure_rate_pct,
                "sla_compliance_pct": sla_compliance_pct,
                "open_overdue_action_items": open_overdue_actions,
            }
        )
    week_rollups.sort(key=lambda item: parse_iso(item.get("week_start")), reverse=True)
    return {"status": "ok", "weeks": weeks, "rollups": week_rollups, "total": len(week_rollups)}


def execute_upsert_connector(
    runtime: WorkflowRuntime, payload: WorkflowConnectorUpsertRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:upsert", 60, 60)
    name_normalized = payload.name.strip().lower()
    now = datetime.now(UTC).isoformat()
    with runtime.lock:
        existing = next(
            (
                c
                for c in runtime.connectors
                if c.get("tenant_id") == auth.tenant_id and str(c.get("name", "")).strip().lower() == name_normalized
            ),
            None,
        )
        if existing is None:
            connector = {
                "id": len(runtime.connectors) + 1,
                "tenant_id": auth.tenant_id,
                "name": payload.name,
                "vendor": payload.vendor,
                "auth_type": payload.auth_type,
                "capabilities": payload.capabilities,
                "rate_limit_per_minute": payload.rate_limit_per_minute,
                "error_budget_pct": payload.error_budget_pct,
                "status": "unknown",
                "last_checked_at": None,
                "reliability_policy": default_reliability_policy(),
                "reliability_stats": {
                    "total_requests": 0,
                    "failed_requests": 0,
                    "retries_attempted": 0,
                    "replay_enqueued": 0,
                    "replay_success": 0,
                    "replay_failed": 0,
                },
                "circuit_breaker": {
                    "state": "closed",
                    "consecutive_failures": 0,
                    "opened_at": None,
                    "cooldown_seconds": 120,
                },
                "created_at": now,
                "updated_at": now,
            }
            runtime.connectors.append(connector)
        else:
            existing["vendor"] = payload.vendor
            existing["auth_type"] = payload.auth_type
            existing["capabilities"] = payload.capabilities
            existing["rate_limit_per_minute"] = payload.rate_limit_per_minute
            existing["error_budget_pct"] = payload.error_budget_pct
            existing["updated_at"] = now
            ensure_reliability_fields(existing)
            connector = existing
    append_audit(runtime, auth.tenant_id, "workflow_connector_upserted", _coerce_int(connector.get("id")))
    return {"status": "ok", "connector": connector}


def execute_list_connectors(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:list", 120, 60)
    with runtime.lock:
        connectors = [c.copy() for c in runtime.connectors if c.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "connectors": connectors, "total": len(connectors)}
