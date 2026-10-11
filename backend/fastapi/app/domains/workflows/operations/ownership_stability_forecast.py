"""Workflow use cases: ownership stability forecast."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_ownership_stability_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:ownership-stability-forecast:get", 120, 60
    )
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    owner_open_items: dict[str, int] = {}
    total_open_items = 0
    unassigned_open_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
            total_open_items += 1
            if owner == "unassigned":
                unassigned_open_items += 1
    overloaded_owner_count = len(
        [
            owner
            for owner, count in owner_open_items.items()
            if owner != "unassigned" and int(count) > max_open_items_per_owner
        ]
    )
    top_owner_share_pct = round(max(owner_open_items.values()) / total_open_items * 100, 2) if total_open_items else 0.0
    active_named_owners = len([owner for owner in owner_open_items if owner != "unassigned"])
    ownership_stability_score = 100.0
    ownership_stability_score -= unassigned_open_items * 10
    ownership_stability_score -= overloaded_owner_count * 8
    ownership_stability_score -= len(open_escalations) * 6
    if top_owner_share_pct >= 80.0:
        ownership_stability_score -= 14
    elif top_owner_share_pct >= 65.0:
        ownership_stability_score -= 7
    if active_named_owners <= 1 and total_open_items > 0:
        ownership_stability_score -= 12
    ownership_stability_score = round(max(0.0, ownership_stability_score), 2)
    if ownership_stability_score >= 80:
        stability_band = "stable"
    elif ownership_stability_score >= 55:
        stability_band = "watch"
    else:
        stability_band = "fragile"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "ownership_stability_score": ownership_stability_score,
        "stability_band": stability_band,
        "active_named_owners": active_named_owners,
        "total_open_action_items": total_open_items,
        "unassigned_open_items": unassigned_open_items,
        "overloaded_owner_count": overloaded_owner_count,
        "open_escalations": len(open_escalations),
        "top_owner_share_pct": top_owner_share_pct,
    }


def execute_get_postmortem_action_item_escalation_burn_rate(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-burn-rate:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    overdue_open_items = 0
    open_action_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            open_action_items += 1
            if parse_iso(action_item.get("due_at")) < now:
                overdue_open_items += 1
    burn_load = len(open_escalations) + overdue_open_items
    target_daily_burn = (burn_load + days_horizon - 1) // days_horizon if burn_load > 0 else 0
    escalation_pressure_index = round(max(0.0, 100.0 - burn_load * 10 - target_daily_burn * 4), 2)
    if target_daily_burn <= 1:
        burn_band = "low"
    elif target_daily_burn <= 3:
        burn_band = "managed"
    else:
        burn_band = "high"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "target_daily_burn": target_daily_burn,
        "burn_band": burn_band,
        "escalation_pressure_index": escalation_pressure_index,
        "burn_load": burn_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_handoff_resilience_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:handoff-resilience-forecast:get", 120, 60
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
    unassigned_open_items = 0
    due_within_24h = 0
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
    overloaded_owner_count = len(
        [
            owner
            for owner, count in owner_open_items.items()
            if owner != "unassigned" and int(count) > max_open_items_per_owner
        ]
    )
    top_owner_share_pct = round(max(owner_open_items.values()) / total_open_items * 100, 2) if total_open_items else 0.0
    handoff_resilience_score = 100.0
    handoff_resilience_score -= overdue_open_items * 9
    handoff_resilience_score -= due_within_24h * 4
    handoff_resilience_score -= unassigned_open_items * 11
    handoff_resilience_score -= len(open_escalations) * 7
    handoff_resilience_score -= overloaded_owner_count * 6
    if top_owner_share_pct >= 80.0:
        handoff_resilience_score -= 12
    elif top_owner_share_pct >= 65.0:
        handoff_resilience_score -= 6
    handoff_resilience_score = round(max(0.0, handoff_resilience_score), 2)
    if handoff_resilience_score >= 80:
        resilience_band = "resilient"
    elif handoff_resilience_score >= 55:
        resilience_band = "watch"
    else:
        resilience_band = "fragile"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "handoff_resilience_score": handoff_resilience_score,
        "resilience_band": resilience_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "top_owner_share_pct": top_owner_share_pct,
    }


def execute_get_postmortem_action_item_backlog_clearance_confidence(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:backlog-clearance-confidence:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    open_action_items = 0
    overdue_open_items = 0
    due_within_24h = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            open_action_items += 1
            due_at = parse_iso(action_item.get("due_at"))
            if due_at < now:
                overdue_open_items += 1
            elif due_at <= now + timedelta(hours=24):
                due_within_24h += 1
    clearance_load = open_action_items + overdue_open_items * 2 + due_within_24h + len(open_escalations) * 2
    required_daily_closures = (clearance_load + days_horizon - 1) // days_horizon if clearance_load > 0 else 0
    backlog_clearance_confidence = 100.0
    backlog_clearance_confidence -= overdue_open_items * 9
    backlog_clearance_confidence -= due_within_24h * 4
    backlog_clearance_confidence -= len(open_escalations) * 8
    backlog_clearance_confidence -= required_daily_closures * 3
    backlog_clearance_confidence = round(max(0.0, backlog_clearance_confidence), 2)
    if backlog_clearance_confidence >= 80:
        confidence_band = "high"
    elif backlog_clearance_confidence >= 55:
        confidence_band = "moderate"
    else:
        confidence_band = "low"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "backlog_clearance_confidence": backlog_clearance_confidence,
        "confidence_band": confidence_band,
        "required_daily_closures": required_daily_closures,
        "clearance_load": clearance_load,
        "open_action_items": open_action_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "open_escalations": len(open_escalations),
    }


def execute_get_postmortem_action_item_remediation_velocity_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-velocity-forecast:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    open_action_items = 0
    overdue_open_items = 0
    due_within_24h = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            open_action_items += 1
            due_at = parse_iso(action_item.get("due_at"))
            if due_at < now:
                overdue_open_items += 1
            elif due_at <= now + timedelta(hours=24):
                due_within_24h += 1
    velocity_load = open_action_items + overdue_open_items * 2 + due_within_24h + len(open_escalations) * 2
    target_daily_velocity = (velocity_load + days_horizon - 1) // days_horizon if velocity_load > 0 else 0
    remediation_velocity_score = 100.0
    remediation_velocity_score -= overdue_open_items * 8
    remediation_velocity_score -= due_within_24h * 4
    remediation_velocity_score -= len(open_escalations) * 7
    remediation_velocity_score -= target_daily_velocity * 3
    remediation_velocity_score = round(max(0.0, remediation_velocity_score), 2)
    if remediation_velocity_score >= 80:
        velocity_band = "fast"
    elif remediation_velocity_score >= 55:
        velocity_band = "steady"
    else:
        velocity_band = "lagging"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_velocity_score": remediation_velocity_score,
        "velocity_band": velocity_band,
        "target_daily_velocity": target_daily_velocity,
        "velocity_load": velocity_load,
        "open_action_items": open_action_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "open_escalations": len(open_escalations),
    }


def execute_get_postmortem_action_item_escalation_recovery_readiness(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-recovery-readiness:get", 120, 60
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
    unassigned_open_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
            total_open_items += 1
            if parse_iso(action_item.get("due_at")) < now:
                overdue_open_items += 1
            if owner == "unassigned":
                unassigned_open_items += 1
    overloaded_owner_count = len(
        [
            owner
            for owner, count in owner_open_items.items()
            if owner != "unassigned" and int(count) > max_open_items_per_owner
        ]
    )
    escalation_recovery_score = 100.0
    escalation_recovery_score -= len(open_escalations) * 9
    escalation_recovery_score -= overdue_open_items * 7
    escalation_recovery_score -= unassigned_open_items * 10
    escalation_recovery_score -= overloaded_owner_count * 6
    escalation_recovery_score = round(max(0.0, escalation_recovery_score), 2)
    if escalation_recovery_score >= 80:
        recovery_band = "ready"
    elif escalation_recovery_score >= 55:
        recovery_band = "watch"
    else:
        recovery_band = "risk"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_recovery_score": escalation_recovery_score,
        "recovery_band": recovery_band,
        "total_open_action_items": total_open_items,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "unassigned_open_items": unassigned_open_items,
        "overloaded_owner_count": overloaded_owner_count,
    }
