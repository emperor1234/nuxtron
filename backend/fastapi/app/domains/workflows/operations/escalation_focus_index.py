"""Workflow use cases: escalation focus index."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_escalation_focus_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-focus-index:get", 120, 60
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
    owner_focus_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_focus_index = 100.0
    escalation_focus_index -= overdue_open_items * 8
    escalation_focus_index -= due_within_24h * 4
    escalation_focus_index -= unassigned_open_items * 9
    escalation_focus_index -= len(open_escalations) * 6
    escalation_focus_index -= overloaded_owner_count * 8
    escalation_focus_index -= owner_focus_gap * 4
    escalation_focus_index = round(max(0.0, escalation_focus_index), 2)
    if escalation_focus_index >= 80:
        focus_band = "focused"
    elif escalation_focus_index >= 55:
        focus_band = "watch"
    else:
        focus_band = "diffuse"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_focus_index": escalation_focus_index,
        "focus_band": focus_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_focus_gap": owner_focus_gap,
    }


def execute_get_postmortem_action_item_remediation_attention_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-attention-forecast:get", 120, 60
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
    assigned_open_items = 0
    overdue_open_items = 0
    due_within_24h = 0
    unassigned_open_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            open_action_items += 1
            owner = str(action_item.get("owner", "")).strip()
            if owner:
                assigned_open_items += 1
            else:
                unassigned_open_items += 1
            due_at = parse_iso(action_item.get("due_at"))
            if due_at < now:
                overdue_open_items += 1
            elif due_at <= now + timedelta(hours=24):
                due_within_24h += 1
    attention_backlog = overdue_open_items + due_within_24h + unassigned_open_items * 2 + len(open_escalations)
    required_daily_attention = (attention_backlog + days_horizon - 1) // days_horizon if attention_backlog > 0 else 0
    assigned_coverage_pct = round(assigned_open_items / open_action_items * 100, 2) if open_action_items else 100.0
    remediation_attention_score = 100.0
    remediation_attention_score -= overdue_open_items * 7
    remediation_attention_score -= due_within_24h * 4
    remediation_attention_score -= unassigned_open_items * 10
    remediation_attention_score -= len(open_escalations) * 6
    remediation_attention_score += min(assigned_coverage_pct / 10, 10)
    remediation_attention_score = round(max(0.0, remediation_attention_score), 2)
    if remediation_attention_score >= 80:
        attention_band = "attentive"
    elif remediation_attention_score >= 55:
        attention_band = "watch"
    else:
        attention_band = "fractured"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_attention_score": remediation_attention_score,
        "attention_band": attention_band,
        "required_daily_attention": required_daily_attention,
        "assigned_coverage_pct": assigned_coverage_pct,
        "attention_backlog": attention_backlog,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_attention_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-attention-index:get", 120, 60
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
    owner_attention_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_attention_index = 100.0
    escalation_attention_index -= overdue_open_items * 7
    escalation_attention_index -= due_within_24h * 4
    escalation_attention_index -= unassigned_open_items * 10
    escalation_attention_index -= len(open_escalations) * 7
    escalation_attention_index -= overloaded_owner_count * 8
    escalation_attention_index -= owner_attention_gap * 3
    escalation_attention_index = round(max(0.0, escalation_attention_index), 2)
    if escalation_attention_index >= 80:
        attention_band = "attentive"
    elif escalation_attention_index >= 55:
        attention_band = "watch"
    else:
        attention_band = "distracted"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_attention_index": escalation_attention_index,
        "attention_band": attention_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_attention_gap": owner_attention_gap,
    }


def execute_get_postmortem_action_item_remediation_coordination_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-coordination-forecast:get", 120, 60
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
    owner_coordination_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    coordination_backlog = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
    required_daily_coordination = (
        (coordination_backlog + days_horizon - 1) // days_horizon if coordination_backlog > 0 else 0
    )
    remediation_coordination_score = 100.0
    remediation_coordination_score -= owner_coordination_gap * 6
    remediation_coordination_score -= overdue_open_items * 7
    remediation_coordination_score -= due_within_24h * 4
    remediation_coordination_score -= unassigned_open_items * 9
    remediation_coordination_score -= len(open_escalations) * 6
    remediation_coordination_score = round(max(0.0, remediation_coordination_score), 2)
    if remediation_coordination_score >= 80:
        coordination_band = "coordinated"
    elif remediation_coordination_score >= 55:
        coordination_band = "watch"
    else:
        coordination_band = "fragmented"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_coordination_score": remediation_coordination_score,
        "coordination_band": coordination_band,
        "required_daily_coordination": required_daily_coordination,
        "coordination_backlog": coordination_backlog,
        "owner_coordination_gap": owner_coordination_gap,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_coordination_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-coordination-index:get", 120, 60
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
    owner_coordination_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_coordination_index = 100.0
    escalation_coordination_index -= owner_coordination_gap * 6
    escalation_coordination_index -= overdue_open_items * 7
    escalation_coordination_index -= due_within_24h * 4
    escalation_coordination_index -= unassigned_open_items * 9
    escalation_coordination_index -= len(open_escalations) * 6
    escalation_coordination_index -= overloaded_owner_count * 8
    escalation_coordination_index = round(max(0.0, escalation_coordination_index), 2)
    if escalation_coordination_index >= 80:
        coordination_band = "coordinated"
    elif escalation_coordination_index >= 55:
        coordination_band = "watch"
    else:
        coordination_band = "fragmented"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_coordination_index": escalation_coordination_index,
        "coordination_band": coordination_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_coordination_gap": owner_coordination_gap,
    }
