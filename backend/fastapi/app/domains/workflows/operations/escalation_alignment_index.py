"""Workflow use cases: escalation alignment index."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_escalation_alignment_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-alignment-index:get", 120, 60
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
    owner_alignment_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_alignment_index = 100.0
    escalation_alignment_index -= overdue_open_items * 8
    escalation_alignment_index -= due_within_24h * 4
    escalation_alignment_index -= unassigned_open_items * 9
    escalation_alignment_index -= len(open_escalations) * 6
    escalation_alignment_index -= overloaded_owner_count * 8
    escalation_alignment_index -= owner_alignment_gap * 4
    escalation_alignment_index = round(max(0.0, escalation_alignment_index), 2)
    if escalation_alignment_index >= 80:
        alignment_band = "aligned"
    elif escalation_alignment_index >= 55:
        alignment_band = "watch"
    else:
        alignment_band = "misaligned"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_alignment_index": escalation_alignment_index,
        "alignment_band": alignment_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_alignment_gap": owner_alignment_gap,
    }


def execute_get_postmortem_action_item_remediation_clarity_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-clarity-forecast:get", 120, 60
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
    clarity_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
    required_daily_clarity_actions = (clarity_load + days_horizon - 1) // days_horizon if clarity_load > 0 else 0
    remediation_clarity_score = round(max(0.0, 100.0 - clarity_load * 8 - required_daily_clarity_actions * 4), 2)
    if remediation_clarity_score >= 80:
        clarity_band = "clear"
    elif remediation_clarity_score >= 55:
        clarity_band = "watch"
    else:
        clarity_band = "unclear"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_clarity_score": remediation_clarity_score,
        "clarity_band": clarity_band,
        "required_daily_clarity_actions": required_daily_clarity_actions,
        "clarity_load": clarity_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_clarity_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-clarity-index:get", 120, 60
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
    owner_clarity_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_clarity_index = 100.0
    escalation_clarity_index -= overdue_open_items * 8
    escalation_clarity_index -= due_within_24h * 4
    escalation_clarity_index -= unassigned_open_items * 9
    escalation_clarity_index -= len(open_escalations) * 6
    escalation_clarity_index -= overloaded_owner_count * 8
    escalation_clarity_index -= owner_clarity_gap * 4
    escalation_clarity_index = round(max(0.0, escalation_clarity_index), 2)
    if escalation_clarity_index >= 80:
        clarity_band = "clear"
    elif escalation_clarity_index >= 55:
        clarity_band = "watch"
    else:
        clarity_band = "unclear"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_clarity_index": escalation_clarity_index,
        "clarity_band": clarity_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_clarity_gap": owner_clarity_gap,
    }


def execute_get_postmortem_action_item_remediation_composure_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-composure-forecast:get", 120, 60
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
    composure_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
    required_daily_composure_actions = (composure_load + days_horizon - 1) // days_horizon if composure_load > 0 else 0
    remediation_composure_score = round(max(0.0, 100.0 - composure_load * 8 - required_daily_composure_actions * 4), 2)
    if remediation_composure_score >= 80:
        composure_band = "composed"
    elif remediation_composure_score >= 55:
        composure_band = "watch"
    else:
        composure_band = "strained"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_composure_score": remediation_composure_score,
        "composure_band": composure_band,
        "required_daily_composure_actions": required_daily_composure_actions,
        "composure_load": composure_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_composure_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-composure-index:get", 120, 60
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
    owner_composure_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_composure_index = 100.0
    escalation_composure_index -= overdue_open_items * 8
    escalation_composure_index -= due_within_24h * 4
    escalation_composure_index -= unassigned_open_items * 9
    escalation_composure_index -= len(open_escalations) * 6
    escalation_composure_index -= overloaded_owner_count * 8
    escalation_composure_index -= owner_composure_gap * 4
    escalation_composure_index = round(max(0.0, escalation_composure_index), 2)
    if escalation_composure_index >= 80:
        composure_band = "composed"
    elif escalation_composure_index >= 55:
        composure_band = "watch"
    else:
        composure_band = "strained"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_composure_index": escalation_composure_index,
        "composure_band": composure_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_composure_gap": owner_composure_gap,
    }


def execute_get_postmortem_action_item_remediation_focus_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-focus-forecast:get", 120, 60
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
    focus_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
    required_daily_focus_actions = (focus_load + days_horizon - 1) // days_horizon if focus_load > 0 else 0
    remediation_focus_score = round(max(0.0, 100.0 - focus_load * 8 - required_daily_focus_actions * 4), 2)
    if remediation_focus_score >= 80:
        focus_band = "focused"
    elif remediation_focus_score >= 55:
        focus_band = "watch"
    else:
        focus_band = "scattered"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_focus_score": remediation_focus_score,
        "focus_band": focus_band,
        "required_daily_focus_actions": required_daily_focus_actions,
        "focus_load": focus_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }
