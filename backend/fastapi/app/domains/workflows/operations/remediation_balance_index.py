"""Workflow use cases: remediation balance index."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_remediation_balance_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-balance-index:get", 120, 60
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
    named_owner_counts = [count for owner, count in owner_open_items.items() if owner != "unassigned"]
    overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
    top_owner_share_pct = (
        round(max(named_owner_counts) / total_open_items * 100, 2) if named_owner_counts and total_open_items else 0.0
    )
    remediation_balance_index = 100.0
    remediation_balance_index -= overdue_open_items * 7
    remediation_balance_index -= unassigned_open_items * 10
    remediation_balance_index -= len(open_escalations) * 7
    remediation_balance_index -= overloaded_owner_count * 8
    if top_owner_share_pct >= 80.0:
        remediation_balance_index -= 14
    elif top_owner_share_pct >= 60.0:
        remediation_balance_index -= 7
    remediation_balance_index = round(max(0.0, remediation_balance_index), 2)
    if remediation_balance_index >= 80:
        balance_band = "balanced"
    elif remediation_balance_index >= 55:
        balance_band = "watch"
    else:
        balance_band = "imbalanced"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "remediation_balance_index": remediation_balance_index,
        "balance_band": balance_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "top_owner_share_pct": top_owner_share_pct,
    }


def execute_get_postmortem_action_item_escalation_pressure_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-pressure-forecast:get", 120, 60
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
    forecast_pressure_units = (
        len(open_escalations) * 2 + overdue_open_items * 2 + due_within_24h + unassigned_open_items
    )
    required_daily_pressure_actions = (
        (forecast_pressure_units + days_horizon - 1) // days_horizon if forecast_pressure_units > 0 else 0
    )
    escalation_pressure_score = round(
        max(0.0, 100.0 - forecast_pressure_units * 8 - required_daily_pressure_actions * 4), 2
    )
    if escalation_pressure_score >= 80:
        pressure_band = "contained"
    elif escalation_pressure_score >= 55:
        pressure_band = "elevated"
    else:
        pressure_band = "critical"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "escalation_pressure_score": escalation_pressure_score,
        "pressure_band": pressure_band,
        "required_daily_pressure_actions": required_daily_pressure_actions,
        "forecast_pressure_units": forecast_pressure_units,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_remediation_concentration_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-concentration-forecast:get",
        120,
        60,
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
    named_owner_counts = [count for owner, count in owner_open_items.items() if owner != "unassigned"]
    top_owner_open_items = max(named_owner_counts) if named_owner_counts else 0
    concentration_share_pct = round(top_owner_open_items / total_open_items * 100, 2) if total_open_items else 0.0
    overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
    remediation_concentration_score = 100.0
    remediation_concentration_score -= overdue_open_items * 7
    remediation_concentration_score -= unassigned_open_items * 9
    remediation_concentration_score -= len(open_escalations) * 6
    remediation_concentration_score -= overloaded_owner_count * 8
    if concentration_share_pct >= 80.0:
        remediation_concentration_score -= 15
    elif concentration_share_pct >= 60.0:
        remediation_concentration_score -= 8
    remediation_concentration_score = round(max(0.0, remediation_concentration_score), 2)
    if remediation_concentration_score >= 80:
        concentration_band = "distributed"
    elif remediation_concentration_score >= 55:
        concentration_band = "watch"
    else:
        concentration_band = "concentrated"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "remediation_concentration_score": remediation_concentration_score,
        "concentration_band": concentration_band,
        "concentration_share_pct": concentration_share_pct,
        "top_owner_open_items": top_owner_open_items,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
    }


def execute_get_postmortem_action_item_escalation_containment_index(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-containment-index:get", 120, 60
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
    containment_load = len(open_escalations) * 2 + overdue_open_items + due_within_24h + unassigned_open_items
    required_daily_containment_actions = (
        (containment_load + days_horizon - 1) // days_horizon if containment_load > 0 else 0
    )
    escalation_containment_index = round(
        max(0.0, 100.0 - containment_load * 8 - required_daily_containment_actions * 4), 2
    )
    if escalation_containment_index >= 80:
        containment_band = "contained"
    elif escalation_containment_index >= 55:
        containment_band = "watch"
    else:
        containment_band = "breach-risk"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "escalation_containment_index": escalation_containment_index,
        "containment_band": containment_band,
        "required_daily_containment_actions": required_daily_containment_actions,
        "containment_load": containment_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_remediation_readiness_balance(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-readiness-balance:get", 120, 60
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
    owner_distribution_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    remediation_readiness_balance = 100.0
    remediation_readiness_balance -= overdue_open_items * 7
    remediation_readiness_balance -= due_within_24h * 4
    remediation_readiness_balance -= unassigned_open_items * 9
    remediation_readiness_balance -= len(open_escalations) * 6
    remediation_readiness_balance -= overloaded_owner_count * 8
    remediation_readiness_balance -= owner_distribution_gap * 4
    remediation_readiness_balance = round(max(0.0, remediation_readiness_balance), 2)
    if remediation_readiness_balance >= 80:
        readiness_band = "balanced"
    elif remediation_readiness_balance >= 55:
        readiness_band = "watch"
    else:
        readiness_band = "strained"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "remediation_readiness_balance": remediation_readiness_balance,
        "readiness_band": readiness_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_distribution_gap": owner_distribution_gap,
    }


def execute_get_postmortem_action_item_escalation_load_shedding_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-load-shedding-forecast:get", 120, 60
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
    load_shedding_units = len(open_escalations) * 2 + overdue_open_items * 2 + due_within_24h + unassigned_open_items
    required_daily_load_shedding = (
        (load_shedding_units + days_horizon - 1) // days_horizon if load_shedding_units > 0 else 0
    )
    escalation_load_shedding_score = round(
        max(0.0, 100.0 - load_shedding_units * 8 - required_daily_load_shedding * 4), 2
    )
    if required_daily_load_shedding <= 1:
        shedding_band = "light"
    elif required_daily_load_shedding <= 3:
        shedding_band = "moderate"
    else:
        shedding_band = "heavy"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "escalation_load_shedding_score": escalation_load_shedding_score,
        "shedding_band": shedding_band,
        "required_daily_load_shedding": required_daily_load_shedding,
        "load_shedding_units": load_shedding_units,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }
