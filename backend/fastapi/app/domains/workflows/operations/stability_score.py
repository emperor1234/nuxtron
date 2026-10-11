"""Workflow use cases: stability score."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_stability_score(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:stability-score:get", 120, 60
    )
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        tenant_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    owner_open_items: dict[str, int] = {}
    action_item_owner: dict[tuple[int, int], str] = {}
    for postmortem in tenant_postmortems:
        postmortem_id = int(postmortem.get("id", 0))
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
            action_item_owner[postmortem_id, int(action_item.get("id", 0))] = owner
    owner_open_escalations: dict[str, int] = {}
    for escalation in tenant_escalations:
        owner = action_item_owner.get(
            (int(escalation.get("postmortem_id", 0)), int(escalation.get("action_item_id", 0))), "unassigned"
        )
        owner_open_escalations[owner] = int(owner_open_escalations.get(owner, 0)) + 1
    total_open_items = sum(owner_open_items.values())
    unassigned_items = int(owner_open_items.get("unassigned", 0))
    overloaded_owners = [
        owner
        for owner, count in owner_open_items.items()
        if owner != "unassigned" and int(count) > max_open_items_per_owner
    ]
    escalation_concentration = len([owner for owner, count in owner_open_escalations.items() if int(count) >= 2])
    top_owner_share_pct = round(max(owner_open_items.values()) / total_open_items * 100, 2) if total_open_items else 0.0
    score = 100.0
    score -= unassigned_items * 10
    score -= len(overloaded_owners) * 12
    score -= escalation_concentration * 14
    if top_owner_share_pct >= 80.0:
        score -= 20
    elif top_owner_share_pct >= 65.0:
        score -= 10
    stability_score = round(max(0.0, score), 2)
    if stability_score >= 80:
        stability_band = "stable"
    elif stability_score >= 50:
        stability_band = "watch"
    else:
        stability_band = "unstable"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "stability_score": stability_score,
        "stability_band": stability_band,
        "total_open_action_items": total_open_items,
        "unassigned_open_items": unassigned_items,
        "overloaded_owner_count": len(overloaded_owners),
        "escalation_concentration_count": escalation_concentration,
        "top_owner_share_pct": top_owner_share_pct,
    }


def execute_get_postmortem_action_item_handoff_plan(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:handoff-plan:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        tenant_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id
            and str(item.get("status", "open")).lower() in {"open", "acknowledged"}
        ]
    owner_stats: dict[str, dict[str, Any]] = {}
    action_item_owner: dict[tuple[int, int], str] = {}
    for postmortem in tenant_postmortems:
        postmortem_id = int(postmortem.get("id", 0))
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            stats = owner_stats.setdefault(
                owner,
                {
                    "owner": owner,
                    "open_action_items": 0,
                    "overdue_open_items": 0,
                    "open_escalations": 0,
                    "critical_open_escalations": 0,
                },
            )
            stats["open_action_items"] = int(stats["open_action_items"]) + 1
            if parse_iso(action_item.get("due_at")) < now:
                stats["overdue_open_items"] = int(stats["overdue_open_items"]) + 1
            action_item_owner[postmortem_id, int(action_item.get("id", 0))] = owner
    for escalation in tenant_escalations:
        owner = action_item_owner.get(
            (int(escalation.get("postmortem_id", 0)), int(escalation.get("action_item_id", 0))), "unassigned"
        )
        stats = owner_stats.setdefault(
            owner,
            {
                "owner": owner,
                "open_action_items": 0,
                "overdue_open_items": 0,
                "open_escalations": 0,
                "critical_open_escalations": 0,
            },
        )
        if str(escalation.get("status", "open")).lower() == "open":
            stats["open_escalations"] = int(stats["open_escalations"]) + 1
            if str(escalation.get("severity", "")).lower() == "critical":
                stats["critical_open_escalations"] = int(stats["critical_open_escalations"]) + 1
    plans: list[dict[str, Any]] = []
    for stats in owner_stats.values():
        owner = str(stats.get("owner", "unassigned"))
        open_items = int(stats.get("open_action_items", 0))
        overdue_items = int(stats.get("overdue_open_items", 0))
        open_escalations = int(stats.get("open_escalations", 0))
        critical_open = int(stats.get("critical_open_escalations", 0))
        if owner == "unassigned":
            continue
        if open_items <= max_open_items_per_owner and overdue_items == 0 and (open_escalations == 0):
            continue
        if critical_open > 0:
            priority = "critical"
        elif overdue_items > 0 or open_escalations >= 2:
            priority = "high"
        else:
            priority = "medium"
        backup_slots = max(1, open_items - max_open_items_per_owner if open_items > max_open_items_per_owner else 1)
        recommendations: list[str] = []
        if open_items > max_open_items_per_owner:
            recommendations.append("Reassign low-context action items to backup owner.")
        if overdue_items > 0:
            recommendations.append("Transfer overdue items to secondary responder.")
        if open_escalations > 0:
            recommendations.append("Assign co-owner for active escalations.")
        if not recommendations:
            recommendations.append("Add documented backup owner for continuity.")
        plans.append(
            {
                "owner": owner,
                "priority": priority,
                "backup_owner_slots_needed": backup_slots,
                "open_action_items": open_items,
                "overdue_open_items": overdue_items,
                "open_escalations": open_escalations,
                "critical_open_escalations": critical_open,
                "recommendations": recommendations,
            }
        )
    plans.sort(
        key=lambda item: (
            0 if str(item.get("priority")) == "critical" else 1 if str(item.get("priority")) == "high" else 2,
            -int(item.get("open_action_items", 0)),
        )
    )
    return {"status": "ok", "max_open_items_per_owner": max_open_items_per_owner, "plans": plans, "count": len(plans)}


def execute_get_postmortem_action_item_resilience_snapshot(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:resilience-snapshot:get", 120, 60
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
    overloaded_owner_count = len(
        [
            owner
            for owner, count in owner_open_items.items()
            if owner != "unassigned" and int(count) > max_open_items_per_owner
        ]
    )
    top_owner_share_pct = round(max(owner_open_items.values()) / total_open_items * 100, 2) if total_open_items else 0.0
    resilience_score = 100.0
    resilience_score -= unassigned_open_items * 12
    resilience_score -= overloaded_owner_count * 10
    resilience_score -= len(open_escalations) * 8
    if top_owner_share_pct >= 80.0:
        resilience_score -= 18
    elif top_owner_share_pct >= 65.0:
        resilience_score -= 9
    resilience_score = round(max(0.0, resilience_score), 2)
    if resilience_score >= 80:
        resilience_band = "strong"
    elif resilience_score >= 55:
        resilience_band = "watch"
    else:
        resilience_band = "fragile"
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "resilience_score": resilience_score,
        "resilience_band": resilience_band,
        "total_open_action_items": total_open_items,
        "open_escalations": len(open_escalations),
        "unassigned_open_items": unassigned_open_items,
        "overloaded_owner_count": overloaded_owner_count,
        "top_owner_share_pct": top_owner_share_pct,
    }


def execute_get_postmortem_action_item_remediation_queue(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-queue:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        tenant_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    owner_stats: dict[str, dict[str, Any]] = {}
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
            stats["open_action_items"] = int(stats["open_action_items"]) + 1
            if parse_iso(action_item.get("due_at")) < now:
                stats["overdue_open_items"] = int(stats["overdue_open_items"]) + 1
            action_item_owner[postmortem_id, int(action_item.get("id", 0))] = owner
    for escalation in tenant_escalations:
        owner = action_item_owner.get(
            (int(escalation.get("postmortem_id", 0)), int(escalation.get("action_item_id", 0))), "unassigned"
        )
        stats = owner_stats.setdefault(owner, {"open_action_items": 0, "overdue_open_items": 0, "open_escalations": 0})
        stats["open_escalations"] = int(stats["open_escalations"]) + 1
    queue: list[dict[str, Any]] = []
    for owner, stats in owner_stats.items():
        open_items = int(stats.get("open_action_items", 0))
        overdue_items = int(stats.get("overdue_open_items", 0))
        open_escalations = int(stats.get("open_escalations", 0))
        if (
            owner != "unassigned"
            and open_items <= max_open_items_per_owner
            and (overdue_items == 0)
            and (open_escalations == 0)
        ):
            continue
        priority_score = (
            overdue_items * 100
            + open_escalations * 80
            + max(0, open_items - max_open_items_per_owner) * 60
            + (120 if owner == "unassigned" else 0)
        )
        if owner == "unassigned":
            action = "assign_owner"
            reason = "Open action items have no owner."
        elif overdue_items > 0:
            action = "reassign_overdue"
            reason = "Owner has overdue open action items."
        elif open_escalations > 0:
            action = "add_co_owner"
            reason = "Owner has active escalations requiring backup."
        else:
            action = "rebalance_load"
            reason = "Owner exceeds configured open-item capacity."
        queue.append(
            {
                "owner": owner,
                "action": action,
                "reason": reason,
                "priority_score": priority_score,
                "open_action_items": open_items,
                "overdue_open_items": overdue_items,
                "open_escalations": open_escalations,
            }
        )
    queue.sort(key=lambda item: int(item.get("priority_score", 0)), reverse=True)
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "queue": queue[:limit],
        "count": min(len(queue), limit),
        "total_candidates": len(queue),
    }
