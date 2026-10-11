"""Workflow use cases: owner relief plan."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_owner_relief_plan(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:owner-relief-plan:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    owner_stats: dict[str, dict[str, int]] = {}
    action_item_owner: dict[tuple[int, int], str] = {}
    for postmortem in tenant_postmortems:
        postmortem_id = int(postmortem.get("id", 0))
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            stats = owner_stats.setdefault(
                owner, {"open_action_items": 0, "overdue_open_items": 0, "open_escalations": 0}
            )
            stats["open_action_items"] += 1
            if parse_iso(action_item.get("due_at")) < now:
                stats["overdue_open_items"] += 1
            action_item_owner[postmortem_id, int(action_item.get("id", 0))] = owner
    for escalation in open_escalations:
        owner = action_item_owner.get(
            (int(escalation.get("postmortem_id", 0)), int(escalation.get("action_item_id", 0))), "unassigned"
        )
        stats = owner_stats.setdefault(owner, {"open_action_items": 0, "overdue_open_items": 0, "open_escalations": 0})
        stats["open_escalations"] += 1
    plans: list[dict[str, Any]] = []
    for owner, stats in owner_stats.items():
        open_items = int(stats.get("open_action_items", 0))
        overdue_items = int(stats.get("overdue_open_items", 0))
        open_escalation_count = int(stats.get("open_escalations", 0))
        overload = max(0, open_items - max_open_items_per_owner)
        if owner != "unassigned" and overload == 0 and (overdue_items == 0) and (open_escalation_count == 0):
            continue
        relief_actions = overload + overdue_items + open_escalation_count
        if owner == "unassigned":
            priority = "critical"
            recommendation = "Assign owner to unassigned action items and add backup coverage."
        elif overdue_items > 0 or open_escalation_count > 0:
            priority = "high"
            recommendation = "Shift overdue and escalated items to secondary responders."
        elif overload > 0:
            priority = "medium"
            recommendation = "Rebalance low-context tasks across available owners."
        else:
            priority = "low"
            recommendation = "Document fallback owner for continuity."
        plans.append(
            {
                "owner": owner,
                "priority": priority,
                "recommended_relief_actions": max(1, relief_actions),
                "open_action_items": open_items,
                "overdue_open_items": overdue_items,
                "open_escalations": open_escalation_count,
                "recommendation": recommendation,
            }
        )
    plans.sort(
        key=lambda item: (
            0
            if str(item.get("priority")) == "critical"
            else 1
            if str(item.get("priority")) == "high"
            else 2
            if str(item.get("priority")) == "medium"
            else 3,
            -int(item.get("recommended_relief_actions", 0)),
        )
    )
    return {"status": "ok", "max_open_items_per_owner": max_open_items_per_owner, "plans": plans, "count": len(plans)}


def execute_get_postmortem_action_item_escalation_clearance_eta(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-clearance-eta:get", 120, 60
    )
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        open_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    open_action_items = 0
    overdue_open_items = 0
    now = datetime.now(UTC)
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            open_action_items += 1
            if parse_iso(action_item.get("due_at")) < now:
                overdue_open_items += 1
    clearance_load = len(open_escalations) + overdue_open_items
    if clearance_load <= 0:
        clearance_eta_days = 0
    else:
        daily_capacity = max(1, open_action_items // max(1, days_horizon) + 1)
        clearance_eta_days = (clearance_load + daily_capacity - 1) // daily_capacity
    if clearance_eta_days <= 1:
        eta_band = "immediate"
    elif clearance_eta_days <= days_horizon:
        eta_band = "manageable"
    else:
        eta_band = "backlog-risk"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "clearance_eta_days": clearance_eta_days,
        "eta_band": eta_band,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "clearance_load": clearance_load,
    }


def execute_get_postmortem_action_item_mitigation_readiness(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:mitigation-readiness:get", 120, 60
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
    mitigation_readiness_score = 100.0
    mitigation_readiness_score -= overdue_open_items * 9
    mitigation_readiness_score -= unassigned_open_items * 12
    mitigation_readiness_score -= len(open_escalations) * 8
    mitigation_readiness_score -= overloaded_owner_count * 7
    mitigation_readiness_score = round(max(0.0, mitigation_readiness_score), 2)
    if mitigation_readiness_score >= 80:
        readiness_band = "ready"
    elif mitigation_readiness_score >= 55:
        readiness_band = "watch"
    else:
        readiness_band = "at-risk"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "mitigation_readiness_score": mitigation_readiness_score,
        "readiness_band": readiness_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
    }


def execute_get_postmortem_action_item_owner_coverage_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:owner-coverage-forecast:get", 120, 60
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
    active_named_owners = len([owner for owner in owner_open_items if owner != "unassigned"])
    overloaded_owner_count = len(
        [
            owner
            for owner, count in owner_open_items.items()
            if owner != "unassigned" and int(count) > max_open_items_per_owner
        ]
    )
    top_owner_share_pct = round(max(owner_open_items.values()) / total_open_items * 100, 2) if total_open_items else 0.0
    owner_coverage_score = 100.0
    owner_coverage_score -= unassigned_open_items * 10
    owner_coverage_score -= overloaded_owner_count * 8
    owner_coverage_score -= len(open_escalations) * 6
    if top_owner_share_pct >= 80.0:
        owner_coverage_score -= 14
    elif top_owner_share_pct >= 65.0:
        owner_coverage_score -= 7
    owner_coverage_score = round(max(0.0, owner_coverage_score), 2)
    if owner_coverage_score >= 80:
        coverage_band = "strong"
    elif owner_coverage_score >= 55:
        coverage_band = "watch"
    else:
        coverage_band = "fragile"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "owner_coverage_score": owner_coverage_score,
        "coverage_band": coverage_band,
        "active_named_owners": active_named_owners,
        "total_open_action_items": total_open_items,
        "unassigned_open_items": unassigned_open_items,
        "overloaded_owner_count": overloaded_owner_count,
        "open_escalations": len(open_escalations),
        "top_owner_share_pct": top_owner_share_pct,
    }


def execute_get_postmortem_action_item_handoff_pressure(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:handoff-pressure:get", 120, 60
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
    handoff_pressure_score = 100.0
    handoff_pressure_score -= overdue_open_items * 8
    handoff_pressure_score -= due_within_24h * 4
    handoff_pressure_score -= unassigned_open_items * 10
    handoff_pressure_score -= len(open_escalations) * 7
    handoff_pressure_score -= overloaded_owner_count * 6
    if top_owner_share_pct >= 80.0:
        handoff_pressure_score -= 12
    elif top_owner_share_pct >= 65.0:
        handoff_pressure_score -= 6
    handoff_pressure_score = round(max(0.0, handoff_pressure_score), 2)
    if handoff_pressure_score >= 80:
        pressure_band = "steady"
    elif handoff_pressure_score >= 55:
        pressure_band = "elevated"
    else:
        pressure_band = "critical"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "handoff_pressure_score": handoff_pressure_score,
        "pressure_band": pressure_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "top_owner_share_pct": top_owner_share_pct,
    }


def execute_get_postmortem_action_item_remediation_momentum(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-momentum:get", 120, 60
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
    momentum_load = open_action_items + overdue_open_items * 2 + due_within_24h + len(open_escalations) * 2
    target_daily_closures = (momentum_load + days_horizon - 1) // days_horizon if momentum_load > 0 else 0
    remediation_momentum_score = 100.0
    remediation_momentum_score -= overdue_open_items * 9
    remediation_momentum_score -= due_within_24h * 5
    remediation_momentum_score -= len(open_escalations) * 8
    remediation_momentum_score -= target_daily_closures * 3
    remediation_momentum_score = round(max(0.0, remediation_momentum_score), 2)
    if remediation_momentum_score >= 80:
        momentum_band = "on-track"
    elif remediation_momentum_score >= 55:
        momentum_band = "watch"
    else:
        momentum_band = "stalled"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_momentum_score": remediation_momentum_score,
        "momentum_band": momentum_band,
        "target_daily_closures": target_daily_closures,
        "open_action_items": open_action_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "open_escalations": len(open_escalations),
        "momentum_load": momentum_load,
    }
