"""Workflow use cases: escalation harmony index."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_escalation_harmony_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-harmony-index:get", 120, 60
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
    owner_harmony_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_harmony_index = 100.0
    escalation_harmony_index -= owner_harmony_gap * 5
    escalation_harmony_index -= overdue_open_items * 7
    escalation_harmony_index -= due_within_24h * 4
    escalation_harmony_index -= unassigned_open_items * 9
    escalation_harmony_index -= len(open_escalations) * 6
    escalation_harmony_index -= overloaded_owner_count * 8
    escalation_harmony_index = round(max(0.0, escalation_harmony_index), 2)
    if escalation_harmony_index >= 80:
        harmony_band = "harmonized"
    elif escalation_harmony_index >= 55:
        harmony_band = "watch"
    else:
        harmony_band = "discordant"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_harmony_index": escalation_harmony_index,
        "harmony_band": harmony_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_harmony_gap": owner_harmony_gap,
    }


def execute_get_postmortem_action_item_remediation_rhythm_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-rhythm-forecast:get", 120, 60
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
    owner_rhythm_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    rhythm_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
    required_daily_rhythm_actions = (rhythm_load + days_horizon - 1) // days_horizon if rhythm_load > 0 else 0
    remediation_rhythm_score = 100.0
    remediation_rhythm_score -= owner_rhythm_gap * 5
    remediation_rhythm_score -= overdue_open_items * 7
    remediation_rhythm_score -= due_within_24h * 4
    remediation_rhythm_score -= unassigned_open_items * 9
    remediation_rhythm_score -= len(open_escalations) * 6
    remediation_rhythm_score = round(max(0.0, remediation_rhythm_score), 2)
    if remediation_rhythm_score >= 80:
        rhythm_band = "steady"
    elif remediation_rhythm_score >= 55:
        rhythm_band = "watch"
    else:
        rhythm_band = "erratic"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_rhythm_score": remediation_rhythm_score,
        "rhythm_band": rhythm_band,
        "required_daily_rhythm_actions": required_daily_rhythm_actions,
        "rhythm_load": rhythm_load,
        "owner_rhythm_gap": owner_rhythm_gap,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_rhythm_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-rhythm-index:get", 120, 60
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
    owner_rhythm_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_rhythm_index = 100.0
    escalation_rhythm_index -= owner_rhythm_gap * 5
    escalation_rhythm_index -= overdue_open_items * 7
    escalation_rhythm_index -= due_within_24h * 4
    escalation_rhythm_index -= unassigned_open_items * 9
    escalation_rhythm_index -= len(open_escalations) * 6
    escalation_rhythm_index -= overloaded_owner_count * 8
    escalation_rhythm_index = round(max(0.0, escalation_rhythm_index), 2)
    if escalation_rhythm_index >= 80:
        rhythm_band = "steady"
    elif escalation_rhythm_index >= 55:
        rhythm_band = "watch"
    else:
        rhythm_band = "erratic"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_rhythm_index": escalation_rhythm_index,
        "rhythm_band": rhythm_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_rhythm_gap": owner_rhythm_gap,
    }


def execute_get_postmortem_action_item_remediation_tempo_forecast(
    runtime: WorkflowRuntime, auth: AuthDep, days_horizon: Annotated[int, Query(ge=1, le=30)] = 7
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-tempo-forecast:get", 120, 60
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
    owner_tempo_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    tempo_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
    required_daily_tempo_actions = (tempo_load + days_horizon - 1) // days_horizon if tempo_load > 0 else 0
    remediation_tempo_score = 100.0
    remediation_tempo_score -= owner_tempo_gap * 5
    remediation_tempo_score -= overdue_open_items * 7
    remediation_tempo_score -= due_within_24h * 4
    remediation_tempo_score -= unassigned_open_items * 9
    remediation_tempo_score -= len(open_escalations) * 6
    remediation_tempo_score = round(max(0.0, remediation_tempo_score), 2)
    if remediation_tempo_score >= 80:
        tempo_band = "steady"
    elif remediation_tempo_score >= 55:
        tempo_band = "watch"
    else:
        tempo_band = "rushing"
    return {
        "status": "ok",
        "days_horizon": days_horizon,
        "remediation_tempo_score": remediation_tempo_score,
        "tempo_band": tempo_band,
        "required_daily_tempo_actions": required_daily_tempo_actions,
        "tempo_load": tempo_load,
        "owner_tempo_gap": owner_tempo_gap,
        "open_escalations": len(open_escalations),
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_action_items": open_action_items,
    }


def execute_get_postmortem_action_item_escalation_tempo_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-tempo-index:get", 120, 60
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
    owner_tempo_gap = (
        max(named_owner_counts) - min(named_owner_counts)
        if len(named_owner_counts) >= 2
        else named_owner_counts[0]
        if named_owner_counts
        else 0
    )
    escalation_tempo_index = 100.0
    escalation_tempo_index -= owner_tempo_gap * 5
    escalation_tempo_index -= overdue_open_items * 7
    escalation_tempo_index -= due_within_24h * 4
    escalation_tempo_index -= unassigned_open_items * 9
    escalation_tempo_index -= len(open_escalations) * 6
    escalation_tempo_index -= overloaded_owner_count * 8
    escalation_tempo_index = round(max(0.0, escalation_tempo_index), 2)
    if escalation_tempo_index >= 80:
        tempo_band = "steady"
    elif escalation_tempo_index >= 55:
        tempo_band = "watch"
    else:
        tempo_band = "rushing"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "escalation_tempo_index": escalation_tempo_index,
        "tempo_band": tempo_band,
        "total_open_action_items": total_open_items,
        "overdue_open_items": overdue_open_items,
        "due_within_24h": due_within_24h,
        "unassigned_open_items": unassigned_open_items,
        "open_escalations": len(open_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "owner_tempo_gap": owner_tempo_gap,
    }
