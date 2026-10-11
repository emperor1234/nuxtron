"""Workflow use cases: readiness forecast."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_readiness_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:readiness-forecast:get", 120, 60
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
    readiness_forecast_score = 100.0
    readiness_forecast_score -= overdue_open_items * 10
    readiness_forecast_score -= due_within_24h * 4
    readiness_forecast_score -= unassigned_open_items * 12
    readiness_forecast_score -= len(open_escalations) * 7
    readiness_forecast_score -= overloaded_owner_count * 9
    if top_owner_share_pct >= 80.0:
        readiness_forecast_score -= 15
    elif top_owner_share_pct >= 65.0:
        readiness_forecast_score -= 8
    readiness_forecast_score = round(max(0.0, readiness_forecast_score), 2)
    if readiness_forecast_score >= 80:
        forecast_band = "ready"
    elif readiness_forecast_score >= 55:
        forecast_band = "watch"
    else:
        forecast_band = "risk"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "readiness_forecast_score": readiness_forecast_score,
        "forecast_band": forecast_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
    }


def execute_get_postmortem_action_item_remediation_throughput(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-throughput:get", 120, 60
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
    risk_load_units = (
        total_open_items
        + overdue_open_items * 2
        + len(open_escalations) * 3
        + unassigned_open_items * 2
        + overloaded_owner_count * 2
    )
    required_daily_remediations = (risk_load_units + days_horizon - 1) // days_horizon if risk_load_units > 0 else 0
    if required_daily_remediations <= 2:
        throughput_band = "sustainable"
    elif required_daily_remediations <= 5:
        throughput_band = "stretched"
    else:
        throughput_band = "critical"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "days_horizon": days_horizon,
        "required_daily_remediations": required_daily_remediations,
        "throughput_band": throughput_band,
        "risk_load_units": risk_load_units,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
    }


def execute_get_postmortem_action_item_risk_burndown(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:risk-burndown:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    open_items = 0
    overdue_open_items = 0
    unassigned_open_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            open_items += 1
            if parse_iso(action_item.get("due_at")) < now:
                overdue_open_items += 1
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            if owner == "unassigned":
                unassigned_open_items += 1
    critical_backlog = overdue_open_items + len(open_escalations)
    high_backlog = max(0, open_items - critical_backlog)
    recommended_daily_critical_closures = (
        (critical_backlog + days_horizon - 1) // days_horizon if critical_backlog > 0 else 0
    )
    recommended_daily_high_closures = (high_backlog + days_horizon - 1) // days_horizon if high_backlog > 0 else 0
    recommended_daily_owner_assignments = (
        (unassigned_open_items + days_horizon - 1) // days_horizon if unassigned_open_items > 0 else 0
    )
    risk_burndown_index = 100.0
    risk_burndown_index -= critical_backlog * 12
    risk_burndown_index -= high_backlog * 4
    risk_burndown_index -= unassigned_open_items * 10
    risk_burndown_index = round(max(0.0, risk_burndown_index), 2)
    if risk_burndown_index >= 80:
        burndown_band = "on-track"
    elif risk_burndown_index >= 55:
        burndown_band = "needs-focus"
    else:
        burndown_band = "off-track"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "risk_burndown_index": risk_burndown_index,
        "burndown_band": burndown_band,
        "recommended_daily_critical_closures": recommended_daily_critical_closures,
        "recommended_daily_high_closures": recommended_daily_high_closures,
        "recommended_daily_owner_assignments": recommended_daily_owner_assignments,
        "critical_backlog": critical_backlog,
        "high_backlog": high_backlog,
        "unassigned_open_items": unassigned_open_items,
    }


def execute_get_postmortem_action_item_capacity_scenarios(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:capacity-scenarios:get", 120, 60
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
    risk_load_units = (
        total_open_items
        + overdue_open_items * 2
        + len(open_escalations) * 3
        + unassigned_open_items * 2
        + overloaded_owner_count * 2
    )
    scenarios = [
        {"name": "stabilize", "risk_units_per_day": 1.0},
        {"name": "accelerate", "risk_units_per_day": 1.35},
        {"name": "constrained", "risk_units_per_day": 0.75},
    ]
    scenario_rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        units_per_day = float(scenario["risk_units_per_day"])
        required_daily_actions = (
            int((risk_load_units / max(units_per_day, 0.1) + days_horizon - 1) // days_horizon)
            if risk_load_units > 0
            else 0
        )
        if required_daily_actions <= 2:
            capacity_band = "comfortable"
        elif required_daily_actions <= 5:
            capacity_band = "tight"
        else:
            capacity_band = "overloaded"
        scenario_rows.append(
            {
                "scenario": scenario["name"],
                "required_daily_actions": required_daily_actions,
                "capacity_band": capacity_band,
            }
        )
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "max_open_items_per_owner": max_open_items_per_owner,
        "risk_load_units": risk_load_units,
        "scenarios": scenario_rows,
        "count": len(scenario_rows),
    }


def execute_get_postmortem_action_item_remediation_sla(
    runtime: WorkflowRuntime, auth: AuthDep, sla_hours: Annotated[int, Query(ge=1, le=168)] = 24
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-sla:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    total_open_items = 0
    within_sla_count = 0
    overdue_count = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            total_open_items += 1
            due_at = parse_iso(action_item.get("due_at"))
            hours_to_due = (due_at - now).total_seconds() / 3600
            if hours_to_due >= 0:
                within_sla_count += 1
            else:
                overdue_count += 1
    sla_adherence_pct = round(within_sla_count / total_open_items * 100, 2) if total_open_items else 100.0
    remediation_sla_score = round(max(0.0, sla_adherence_pct - len(open_escalations) * 4), 2)
    if remediation_sla_score >= 85:
        sla_band = "healthy"
    elif remediation_sla_score >= 60:
        sla_band = "watch"
    else:
        sla_band = "breach"
    return {
        "status": "ok",
        "sla_hours": sla_hours,
        "remediation_sla_score": remediation_sla_score,
        "sla_band": sla_band,
        "sla_adherence_pct": sla_adherence_pct,
        "total_open_action_items": total_open_items,
        "within_sla_count": within_sla_count,
        "overdue_count": overdue_count,
        "open_escalations": len(open_escalations),
    }
