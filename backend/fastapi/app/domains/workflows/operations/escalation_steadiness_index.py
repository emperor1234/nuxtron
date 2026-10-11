"""Workflow use cases: escalation steadiness index."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_escalation_steadiness_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-steadiness-index:get", 120, 60
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
    owner_steadiness_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_steadiness_index = 100.0
    escalation_steadiness_index -= overdue_open_items * 8
    escalation_steadiness_index -= due_within_24h * 4
    escalation_steadiness_index -= unassigned_open_items * 9
    escalation_steadiness_index -= len(open_escalations) * 6
    escalation_steadiness_index -= overloaded_owner_count * 8
    escalation_steadiness_index -= owner_steadiness_gap * 4
    escalation_steadiness_index = round(max(0.0, escalation_steadiness_index), 2)
    if escalation_steadiness_index >= 80:
        steadiness_band = "stable"
    elif escalation_steadiness_index >= 55:
        steadiness_band = "watch"
    else:
        steadiness_band = "unstable"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_steadiness_index": escalation_steadiness_index,
        "steadiness_band": steadiness_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_steadiness_gap": owner_steadiness_gap,
    }


def execute_get_postmortem_action_item_remediation_durability_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-durability-forecast:get", 120, 60
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
    durability_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
    required_daily_durability_actions = (
        (durability_load + days_horizon - 1) // days_horizon if durability_load > 0 else 0
    )
    remediation_durability_score = round(
        max(0.0, 100.0 - durability_load * 8 - required_daily_durability_actions * 4), 2
    )
    if remediation_durability_score >= 80:
        durability_band = "durable"
    elif remediation_durability_score >= 55:
        durability_band = "watch"
    else:
        durability_band = "brittle"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_durability_score": remediation_durability_score,
        "durability_band": durability_band,
        "required_daily_durability_actions": required_daily_durability_actions,
        "durability_load": durability_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_durability_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-durability-index:get", 120, 60
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
    owner_durability_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_durability_index = 100.0
    escalation_durability_index -= overdue_open_items * 8
    escalation_durability_index -= due_within_24h * 4
    escalation_durability_index -= unassigned_open_items * 9
    escalation_durability_index -= len(open_escalations) * 6
    escalation_durability_index -= overloaded_owner_count * 8
    escalation_durability_index -= owner_durability_gap * 4
    escalation_durability_index = round(max(0.0, escalation_durability_index), 2)
    if escalation_durability_index >= 80:
        durability_band = "durable"
    elif escalation_durability_index >= 55:
        durability_band = "watch"
    else:
        durability_band = "fragile"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_durability_index": escalation_durability_index,
        "durability_band": durability_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_durability_gap": owner_durability_gap,
    }


def execute_get_postmortem_action_item_remediation_consistency_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-consistency-forecast:get", 120, 60
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
    consistency_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
    required_daily_consistency_actions = (
        (consistency_load + days_horizon - 1) // days_horizon if consistency_load > 0 else 0
    )
    remediation_consistency_score = round(
        max(0.0, 100.0 - consistency_load * 8 - required_daily_consistency_actions * 4), 2
    )
    if remediation_consistency_score >= 80:
        consistency_band = "consistent"
    elif remediation_consistency_score >= 55:
        consistency_band = "watch"
    else:
        consistency_band = "inconsistent"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_consistency_score": remediation_consistency_score,
        "consistency_band": consistency_band,
        "required_daily_consistency_actions": required_daily_consistency_actions,
        "consistency_load": consistency_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_consistency_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-consistency-index:get", 120, 60
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
    owner_consistency_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_consistency_index = 100.0
    escalation_consistency_index -= overdue_open_items * 8
    escalation_consistency_index -= due_within_24h * 4
    escalation_consistency_index -= unassigned_open_items * 9
    escalation_consistency_index -= len(open_escalations) * 6
    escalation_consistency_index -= overloaded_owner_count * 8
    escalation_consistency_index -= owner_consistency_gap * 4
    escalation_consistency_index = round(max(0.0, escalation_consistency_index), 2)
    if escalation_consistency_index >= 80:
        consistency_band = "consistent"
    elif escalation_consistency_index >= 55:
        consistency_band = "watch"
    else:
        consistency_band = "volatile"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_consistency_index": escalation_consistency_index,
        "consistency_band": consistency_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_consistency_gap": owner_consistency_gap,
    }


def execute_get_postmortem_action_item_remediation_alignment_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-alignment-forecast:get", 120, 60
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
    alignment_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
    required_daily_alignment_actions = (alignment_load + days_horizon - 1) // days_horizon if alignment_load > 0 else 0
    remediation_alignment_score = round(max(0.0, 100.0 - alignment_load * 8 - required_daily_alignment_actions * 4), 2)
    if remediation_alignment_score >= 80:
        alignment_band = "aligned"
    elif remediation_alignment_score >= 55:
        alignment_band = "watch"
    else:
        alignment_band = "misaligned"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_alignment_score": remediation_alignment_score,
        "alignment_band": alignment_band,
        "required_daily_alignment_actions": required_daily_alignment_actions,
        "alignment_load": alignment_load,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }
