"""Workflow use cases: remediation pressure index."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_remediation_pressure_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-pressure-index:get", 120, 60
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
    owner_pressure_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    remediation_pressure_index = 100.0
    remediation_pressure_index -= overdue_open_items * 8
    remediation_pressure_index -= due_within_24h * 4
    remediation_pressure_index -= unassigned_open_items * 9
    remediation_pressure_index -= len(open_escalations) * 6
    remediation_pressure_index -= overloaded_owner_count * 8
    remediation_pressure_index -= owner_pressure_gap * 4
    remediation_pressure_index = round(max(0.0, remediation_pressure_index), 2)
    if remediation_pressure_index >= 80:
        pressure_band = "relieved"
    elif remediation_pressure_index >= 55:
        pressure_band = "watch"
    else:
        pressure_band = "pressured"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "remediation_pressure_index": remediation_pressure_index,
        "pressure_band": pressure_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_pressure_gap": owner_pressure_gap,
    }


def execute_get_postmortem_action_item_escalation_relief_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-relief-forecast:get", 120, 60
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
    relief_units = len(open_escalations) + overdue_open_items + due_within_24h
    required_daily_relief_actions = (relief_units + days_horizon - 1) // days_horizon if relief_units > 0 else 0
    escalation_relief_score = round(max(0.0, 100.0 - relief_units * 9 - required_daily_relief_actions * 4), 2)
    if required_daily_relief_actions <= 1:
        relief_band = "relievable"
    elif required_daily_relief_actions <= 3:
        relief_band = "tight"
    else:
        relief_band = "stretched"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "escalation_relief_score": escalation_relief_score,
        "relief_band": relief_band,
        "required_daily_relief_actions": required_daily_relief_actions,
        "relief_units": relief_units,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_remediation_recovery_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-recovery-index:get", 120, 60
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
    owner_recovery_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    remediation_recovery_index = 100.0
    remediation_recovery_index -= overdue_open_items * 8
    remediation_recovery_index -= due_within_24h * 4
    remediation_recovery_index -= unassigned_open_items * 9
    remediation_recovery_index -= len(open_escalations) * 6
    remediation_recovery_index -= overloaded_owner_count * 8
    remediation_recovery_index -= owner_recovery_gap * 4
    remediation_recovery_index = round(max(0.0, remediation_recovery_index), 2)
    if remediation_recovery_index >= 80:
        recovery_band = "recovering"
    elif remediation_recovery_index >= 55:
        recovery_band = "watch"
    else:
        recovery_band = "delayed"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "remediation_recovery_index": remediation_recovery_index,
        "recovery_band": recovery_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_recovery_gap": owner_recovery_gap,
    }


def execute_get_postmortem_action_item_escalation_recovery_index(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-recovery-index:get", 120, 60
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
    recovery_units = len(open_escalations) + overdue_open_items + due_within_24h
    required_daily_recovery_actions = (recovery_units + days_horizon - 1) // days_horizon if recovery_units > 0 else 0
    escalation_recovery_index = round(max(0.0, 100.0 - recovery_units * 9 - required_daily_recovery_actions * 4), 2)
    if required_daily_recovery_actions <= 1:
        recovery_band = "recovered"
    elif required_daily_recovery_actions <= 3:
        recovery_band = "tight"
    else:
        recovery_band = "lagging"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "escalation_recovery_index": escalation_recovery_index,
        "recovery_band": recovery_band,
        "required_daily_recovery_actions": required_daily_recovery_actions,
        "recovery_units": recovery_units,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_remediation_resilience_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-resilience-forecast:get", 120, 60
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
    unassigned_open_items = 0
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
            if not str(action_item.get("owner", "")).strip():
                unassigned_open_items += 1
    resilience_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
    required_daily_resilience_actions = (
        (resilience_load + days_horizon - 1) // days_horizon if resilience_load > 0 else 0
    )
    remediation_resilience_score = round(
        max(0.0, 100.0 - resilience_load * 8 - required_daily_resilience_actions * 4), 2
    )
    if remediation_resilience_score >= 80:
        resilience_band = "resilient"
    elif remediation_resilience_score >= 55:
        resilience_band = "watch"
    else:
        resilience_band = "fragile"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_resilience_score": remediation_resilience_score,
        "resilience_band": resilience_band,
        "required_daily_resilience_actions": required_daily_resilience_actions,
        "resilience_load": resilience_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_remediation_steadiness_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-steadiness-forecast:get", 120, 60
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
    unassigned_open_items = 0
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
            if not str(action_item.get("owner", "")).strip():
                unassigned_open_items += 1
    steadiness_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
    required_daily_steadiness_actions = (
        (steadiness_load + days_horizon - 1) // days_horizon if steadiness_load > 0 else 0
    )
    remediation_steadiness_score = round(
        max(0.0, 100.0 - steadiness_load * 8 - required_daily_steadiness_actions * 4), 2
    )
    if remediation_steadiness_score >= 80:
        steadiness_band = "steady"
    elif remediation_steadiness_score >= 55:
        steadiness_band = "watch"
    else:
        steadiness_band = "shaky"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_steadiness_score": remediation_steadiness_score,
        "steadiness_band": steadiness_band,
        "required_daily_steadiness_actions": required_daily_steadiness_actions,
        "steadiness_load": steadiness_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }
