"""Workflow use cases: continuity readiness index."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_continuity_readiness_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:continuity-readiness-index:get", 120, 60
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
    continuity_readiness_index = 100.0
    continuity_readiness_index -= overdue_open_items * 8
    continuity_readiness_index -= due_within_24h * 4
    continuity_readiness_index -= unassigned_open_items * 10
    continuity_readiness_index -= len(open_escalations) * 7
    continuity_readiness_index -= overloaded_owner_count * 6
    if top_owner_share_pct >= 80.0:
        continuity_readiness_index -= 12
    elif top_owner_share_pct >= 65.0:
        continuity_readiness_index -= 6
    continuity_readiness_index = round(max(0.0, continuity_readiness_index), 2)
    if continuity_readiness_index >= 80:
        continuity_band = "ready"
    elif continuity_readiness_index >= 55:
        continuity_band = "watch"
    else:
        continuity_band = "fragile"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "continuity_readiness_index": continuity_readiness_index,
        "continuity_band": continuity_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "top_owner_share_pct": top_owner_share_pct,
    }


def execute_get_postmortem_action_item_escalation_drain_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-drain-forecast:get", 120, 60
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
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            open_action_items += 1
            if parse_iso(action_item.get("due_at")) < now:
                overdue_open_items += 1
    drain_load = len(open_escalations) + overdue_open_items
    required_daily_drain = (drain_load + days_horizon - 1) // days_horizon if drain_load > 0 else 0
    drain_confidence_score = round(max(0.0, 100.0 - drain_load * 10 - required_daily_drain * 4), 2)
    if required_daily_drain <= 1:
        drain_band = "light"
    elif required_daily_drain <= 3:
        drain_band = "moderate"
    else:
        drain_band = "heavy"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "required_daily_drain": required_daily_drain,
        "drain_band": drain_band,
        "drain_confidence_score": drain_confidence_score,
        "drain_load": drain_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_remediation_confidence_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-confidence-forecast:get", 120, 60
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
    forecast_load = open_action_items + overdue_open_items * 2 + due_within_24h + len(open_escalations) * 2
    required_daily_throughput = (forecast_load + days_horizon - 1) // days_horizon if forecast_load > 0 else 0
    remediation_confidence_score = 100.0
    remediation_confidence_score -= overdue_open_items * 8
    remediation_confidence_score -= due_within_24h * 4
    remediation_confidence_score -= len(open_escalations) * 8
    remediation_confidence_score -= required_daily_throughput * 3
    remediation_confidence_score = round(max(0.0, remediation_confidence_score), 2)
    if remediation_confidence_score >= 80:
        confidence_band = "high"
    elif remediation_confidence_score >= 55:
        confidence_band = "moderate"
    else:
        confidence_band = "low"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_confidence_score": remediation_confidence_score,
        "confidence_band": confidence_band,
        "required_daily_throughput": required_daily_throughput,
        "forecast_load": forecast_load,
        "open_action_items": open_action_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "open_escalations": len(open_escalations),
    }


def execute_get_postmortem_action_item_escalation_stabilization_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-stabilization-index:get", 120, 60
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
    escalation_stabilization_index = 100.0
    escalation_stabilization_index -= len(open_escalations) * 9
    escalation_stabilization_index -= overdue_open_items * 7
    escalation_stabilization_index -= unassigned_open_items * 9
    escalation_stabilization_index -= overloaded_owner_count * 6
    escalation_stabilization_index = round(max(0.0, escalation_stabilization_index), 2)
    if escalation_stabilization_index >= 80:
        stabilization_band = "stable"
    elif escalation_stabilization_index >= 55:
        stabilization_band = "watch"
    else:
        stabilization_band = "unstable"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_stabilization_index": escalation_stabilization_index,
        "stabilization_band": stabilization_band,
        "total_open_action_items": total_open_items,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "unassigned_open_items": unassigned_open_items,
        "overloaded_owner_count": overloaded_owner_count,
    }


def execute_get_postmortem_action_item_remediation_posture_score(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-posture-score:get", 120, 60
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
    remediation_posture_score = 100.0
    remediation_posture_score -= overdue_open_items * 8
    remediation_posture_score -= due_within_24h * 4
    remediation_posture_score -= unassigned_open_items * 10
    remediation_posture_score -= len(open_escalations) * 7
    remediation_posture_score -= overloaded_owner_count * 6
    if top_owner_share_pct >= 80.0:
        remediation_posture_score -= 12
    elif top_owner_share_pct >= 65.0:
        remediation_posture_score -= 6
    remediation_posture_score = round(max(0.0, remediation_posture_score), 2)
    if remediation_posture_score >= 80:
        posture_band = "strong"
    elif remediation_posture_score >= 55:
        posture_band = "watch"
    else:
        posture_band = "weak"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "remediation_posture_score": remediation_posture_score,
        "posture_band": posture_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "top_owner_share_pct": top_owner_share_pct,
    }


def execute_get_postmortem_action_item_escalation_runway_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-runway-forecast:get", 120, 60
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
    runway_load = len(open_escalations) + overdue_open_items + due_within_24h
    required_daily_runway_actions = (runway_load + days_horizon - 1) // days_horizon if runway_load > 0 else 0
    escalation_runway_score = round(max(0.0, 100.0 - runway_load * 9 - required_daily_runway_actions * 4), 2)
    if required_daily_runway_actions <= 1:
        runway_band = "comfortable"
    elif required_daily_runway_actions <= 3:
        runway_band = "tight"
    else:
        runway_band = "critical"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "required_daily_runway_actions": required_daily_runway_actions,
        "runway_band": runway_band,
        "escalation_runway_score": escalation_runway_score,
        "runway_load": runway_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "open_action_items": open_action_items,
    }
