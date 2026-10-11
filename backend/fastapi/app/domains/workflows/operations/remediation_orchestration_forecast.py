"""Workflow use cases: remediation orchestration forecast."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_remediation_orchestration_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-orchestration-forecast:get",
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
    owner_orchestration_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    orchestration_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
    required_daily_orchestration = (
        (orchestration_load + days_horizon - 1) // days_horizon if orchestration_load > 0 else 0
    )
    remediation_orchestration_score = 100.0
    remediation_orchestration_score -= owner_orchestration_gap * 5
    remediation_orchestration_score -= overdue_open_items * 7
    remediation_orchestration_score -= due_within_24h * 4
    remediation_orchestration_score -= unassigned_open_items * 9
    remediation_orchestration_score -= len(open_escalations) * 6
    remediation_orchestration_score = round(max(0.0, remediation_orchestration_score), 2)
    if remediation_orchestration_score >= 80:
        orchestration_band = "orchestrated"
    elif remediation_orchestration_score >= 55:
        orchestration_band = "watch"
    else:
        orchestration_band = "disjointed"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_orchestration_score": remediation_orchestration_score,
        "orchestration_band": orchestration_band,
        "required_daily_orchestration": required_daily_orchestration,
        "orchestration_load": orchestration_load,
        "owner_orchestration_gap": owner_orchestration_gap,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_orchestration_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-orchestration-index:get", 120, 60
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
    owner_orchestration_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_orchestration_index = 100.0
    escalation_orchestration_index -= owner_orchestration_gap * 5
    escalation_orchestration_index -= overdue_open_items * 7
    escalation_orchestration_index -= due_within_24h * 4
    escalation_orchestration_index -= unassigned_open_items * 9
    escalation_orchestration_index -= len(open_escalations) * 6
    escalation_orchestration_index -= overloaded_owner_count * 8
    escalation_orchestration_index = round(max(0.0, escalation_orchestration_index), 2)
    if escalation_orchestration_index >= 80:
        orchestration_band = "orchestrated"
    elif escalation_orchestration_index >= 55:
        orchestration_band = "watch"
    else:
        orchestration_band = "disjointed"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_orchestration_index": escalation_orchestration_index,
        "orchestration_band": orchestration_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_orchestration_gap": owner_orchestration_gap,
    }


def execute_get_postmortem_action_item_remediation_synchronization_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-synchronization-forecast:get",
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
    owner_synchronization_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    synchronization_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
    required_daily_sync_actions = (
        (synchronization_load + days_horizon - 1) // days_horizon if synchronization_load > 0 else 0
    )
    remediation_synchronization_score = 100.0
    remediation_synchronization_score -= owner_synchronization_gap * 5
    remediation_synchronization_score -= overdue_open_items * 7
    remediation_synchronization_score -= due_within_24h * 4
    remediation_synchronization_score -= unassigned_open_items * 9
    remediation_synchronization_score -= len(open_escalations) * 6
    remediation_synchronization_score = round(max(0.0, remediation_synchronization_score), 2)
    if remediation_synchronization_score >= 80:
        synchronization_band = "synchronized"
    elif remediation_synchronization_score >= 55:
        synchronization_band = "watch"
    else:
        synchronization_band = "desynced"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_synchronization_score": remediation_synchronization_score,
        "synchronization_band": synchronization_band,
        "required_daily_sync_actions": required_daily_sync_actions,
        "synchronization_load": synchronization_load,
        "owner_synchronization_gap": owner_synchronization_gap,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_synchronization_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-synchronization-index:get", 120, 60
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
    owner_synchronization_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_synchronization_index = 100.0
    escalation_synchronization_index -= owner_synchronization_gap * 5
    escalation_synchronization_index -= overdue_open_items * 7
    escalation_synchronization_index -= due_within_24h * 4
    escalation_synchronization_index -= unassigned_open_items * 9
    escalation_synchronization_index -= len(open_escalations) * 6
    escalation_synchronization_index -= overloaded_owner_count * 8
    escalation_synchronization_index = round(max(0.0, escalation_synchronization_index), 2)
    if escalation_synchronization_index >= 80:
        synchronization_band = "synchronized"
    elif escalation_synchronization_index >= 55:
        synchronization_band = "watch"
    else:
        synchronization_band = "desynced"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_synchronization_index": escalation_synchronization_index,
        "synchronization_band": synchronization_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_synchronization_gap": owner_synchronization_gap,
    }


def execute_get_postmortem_action_item_remediation_harmony_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-harmony-forecast:get", 120, 60
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
    owner_harmony_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    harmony_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
    required_daily_harmony_actions = (harmony_load + days_horizon - 1) // days_horizon if harmony_load > 0 else 0
    remediation_harmony_score = 100.0
    remediation_harmony_score -= owner_harmony_gap * 5
    remediation_harmony_score -= overdue_open_items * 7
    remediation_harmony_score -= due_within_24h * 4
    remediation_harmony_score -= unassigned_open_items * 9
    remediation_harmony_score -= len(open_escalations) * 6
    remediation_harmony_score = round(max(0.0, remediation_harmony_score), 2)
    if remediation_harmony_score >= 80:
        harmony_band = "harmonized"
    elif remediation_harmony_score >= 55:
        harmony_band = "watch"
    else:
        harmony_band = "discordant"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_harmony_score": remediation_harmony_score,
        "harmony_band": harmony_band,
        "required_daily_harmony_actions": required_daily_harmony_actions,
        "harmony_load": harmony_load,
        "owner_harmony_gap": owner_harmony_gap,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }
