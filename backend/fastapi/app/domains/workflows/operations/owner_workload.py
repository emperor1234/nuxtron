"""Workflow use cases: owner workload."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorActionItemRebalanceRequest
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_owner_workload(
    runtime: WorkflowRuntime, auth: AuthDep, include_done: bool = False
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:owner-workload:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        tenant_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id
        ]
    action_item_owner: dict[tuple[int, int], str] = {}
    owner_stats: dict[str, dict[str, Any]] = {}
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            status = str(action_item.get("status", "open")).lower()
            if not include_done and status == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            stats = owner_stats.setdefault(
                owner,
                {
                    "owner": owner,
                    "open_action_items": 0,
                    "blocked_action_items": 0,
                    "overdue_open_items": 0,
                    "open_escalations": 0,
                    "acknowledged_escalations": 0,
                    "suppressed_escalations": 0,
                },
            )
            if status in {"open", "blocked"}:
                stats["open_action_items"] = int(stats["open_action_items"]) + 1
            if status == "blocked":
                stats["blocked_action_items"] = int(stats["blocked_action_items"]) + 1
            if status != "done" and parse_iso(action_item.get("due_at")) < now:
                stats["overdue_open_items"] = int(stats["overdue_open_items"]) + 1
            action_item_owner[int(postmortem.get("id", 0)), int(action_item.get("id", 0))] = owner
    for escalation in tenant_escalations:
        owner = action_item_owner.get(
            (int(escalation.get("postmortem_id", 0)), int(escalation.get("action_item_id", 0))), "unassigned"
        )
        stats = owner_stats.setdefault(
            owner,
            {
                "owner": owner,
                "open_action_items": 0,
                "blocked_action_items": 0,
                "overdue_open_items": 0,
                "open_escalations": 0,
                "acknowledged_escalations": 0,
                "suppressed_escalations": 0,
            },
        )
        escalation_status = str(escalation.get("status", "open")).lower()
        if escalation_status == "open":
            stats["open_escalations"] = int(stats["open_escalations"]) + 1
        elif escalation_status == "acknowledged":
            stats["acknowledged_escalations"] = int(stats["acknowledged_escalations"]) + 1
        elif escalation_status == "suppressed":
            stats["suppressed_escalations"] = int(stats["suppressed_escalations"]) + 1
    owners: list[dict[str, Any]] = []
    for stats in owner_stats.values():
        workload_score = (
            int(stats.get("open_action_items", 0)) * 3
            + int(stats.get("overdue_open_items", 0)) * 5
            + int(stats.get("open_escalations", 0)) * 8
            + int(stats.get("suppressed_escalations", 0)) * 4
        )
        row = stats.copy()
        row["workload_score"] = workload_score
        owners.append(row)
    owners.sort(key=lambda item: int(item.get("workload_score", 0)), reverse=True)
    total_open_items = sum((int(item.get("open_action_items", 0)) for item in owners))
    total_open_escalations = sum((int(item.get("open_escalations", 0)) for item in owners))
    return {
        "status": "ok",
        "include_done": include_done,
        "owners": owners,
        "total_owners": len(owners),
        "total_open_action_items": total_open_items,
        "total_open_escalations": total_open_escalations,
    }


def execute_get_postmortem_action_item_rebalance_suggestions(
    runtime: WorkflowRuntime, payload: WorkflowConnectorActionItemRebalanceRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:rebalance-suggestions:get", 60, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
    owner_open_counts: dict[str, int] = {}
    candidate_items: list[dict[str, Any]] = []
    for postmortem in tenant_postmortems:
        postmortem_id = int(postmortem.get("id", 0))
        connector_id = int(postmortem.get("connector_id", 0))
        for action_item in postmortem.get("action_items_detailed") or []:
            status = str(action_item.get("status", "open")).lower()
            if status == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_open_counts[owner] = int(owner_open_counts.get(owner, 0)) + 1
            due_at = parse_iso(action_item.get("due_at"))
            candidate_items.append(
                {
                    "connector_id": connector_id,
                    "postmortem_id": postmortem_id,
                    "action_item_id": int(action_item.get("id", 0)),
                    "action_item_title": action_item.get("title", ""),
                    "from_owner": owner,
                    "due_at": due_at.isoformat(),
                    "minutes_overdue": max(0, int((now - due_at).total_seconds() // 60)),
                }
            )
    max_open = int(payload.max_open_items_per_owner)
    overloaded = [
        owner
        for owner, count in owner_open_counts.items()
        if count > max_open and (payload.include_unassigned or owner != "unassigned")
    ]
    underloaded = [owner for owner, count in owner_open_counts.items() if owner != "unassigned" and count < max_open]
    if not underloaded:
        return {
            "status": "ok",
            "max_open_items_per_owner": max_open,
            "suggestions": [],
            "count": 0,
            "reason": "No underloaded owners available for reassignment.",
        }
    candidate_items.sort(
        key=lambda item: (0 if int(item.get("minutes_overdue", 0)) > 0 else 1, -int(item.get("minutes_overdue", 0)))
    )
    suggestions: list[dict[str, Any]] = []
    for item in candidate_items:
        from_owner = str(item.get("from_owner", "unassigned"))
        if from_owner not in overloaded:
            continue
        underloaded.sort(key=lambda owner: int(owner_open_counts.get(owner, 0)))
        to_owner = underloaded[0]
        if from_owner == to_owner:
            continue
        suggestions.append({**item, "to_owner": to_owner, "reason": "source_owner_over_capacity"})
        owner_open_counts[from_owner] = int(owner_open_counts.get(from_owner, 0)) - 1
        owner_open_counts[to_owner] = int(owner_open_counts.get(to_owner, 0)) + 1
        if owner_open_counts[from_owner] <= max_open and from_owner in overloaded:
            overloaded.remove(from_owner)
        if owner_open_counts[to_owner] >= max_open and to_owner in underloaded:
            underloaded.remove(to_owner)
        if len(suggestions) >= payload.limit or not overloaded or (not underloaded):
            break
    return {"status": "ok", "max_open_items_per_owner": max_open, "suggestions": suggestions, "count": len(suggestions)}


def execute_get_postmortem_action_item_workload_hotspots(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    max_overdue_items_per_owner: Annotated[int, Query(ge=0, le=100)] = 1,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:workload-hotspots:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        tenant_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id
        ]
    owner_stats: dict[str, dict[str, Any]] = {}
    action_item_owner: dict[tuple[int, int], str] = {}
    for postmortem in tenant_postmortems:
        postmortem_id = int(postmortem.get("id", 0))
        for action_item in postmortem.get("action_items_detailed") or []:
            status = str(action_item.get("status", "open")).lower()
            if status == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            due_at = parse_iso(action_item.get("due_at"))
            stats = owner_stats.setdefault(
                owner, {"owner": owner, "open_action_items": 0, "overdue_open_items": 0, "open_escalations": 0}
            )
            stats["open_action_items"] = int(stats["open_action_items"]) + 1
            if due_at < now:
                stats["overdue_open_items"] = int(stats["overdue_open_items"]) + 1
            action_item_owner[postmortem_id, int(action_item.get("id", 0))] = owner
    for escalation in tenant_escalations:
        if str(escalation.get("status", "open")).lower() != "open":
            continue
        owner = action_item_owner.get(
            (int(escalation.get("postmortem_id", 0)), int(escalation.get("action_item_id", 0))), "unassigned"
        )
        stats = owner_stats.setdefault(
            owner, {"owner": owner, "open_action_items": 0, "overdue_open_items": 0, "open_escalations": 0}
        )
        stats["open_escalations"] = int(stats["open_escalations"]) + 1
    hotspots: list[dict[str, Any]] = []
    for stats in owner_stats.values():
        open_items = int(stats.get("open_action_items", 0))
        overdue_items = int(stats.get("overdue_open_items", 0))
        open_escalations = int(stats.get("open_escalations", 0))
        overloaded = open_items > max_open_items_per_owner
        overdue_breached = overdue_items > max_overdue_items_per_owner
        if not overloaded and (not overdue_breached) and (open_escalations == 0):
            continue
        severity = "critical" if overdue_breached or open_escalations >= 2 else "high"
        hotspots.append(
            {**stats, "over_capacity": overloaded, "overdue_threshold_breached": overdue_breached, "severity": severity}
        )
    hotspots.sort(
        key=lambda item: (
            0 if str(item.get("severity")) == "critical" else 1,
            -(int(item.get("overdue_open_items", 0)) + int(item.get("open_escalations", 0))),
            -int(item.get("open_action_items", 0)),
        )
    )
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "max_overdue_items_per_owner": max_overdue_items_per_owner,
        "hotspots": hotspots,
        "count": len(hotspots),
    }


def execute_get_postmortem_action_item_surge_alerts(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    lookback_hours: Annotated[int, Query(ge=1, le=720)] = 24,
    min_new_open_escalations: Annotated[int, Query(ge=1, le=50)] = 1,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:surge-alerts:get", 120, 60
    )
    now = datetime.now(UTC)
    lookback_start = now - timedelta(hours=lookback_hours)
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and parse_iso(item.get("created_at")) >= lookback_start
        ]
    action_item_owner: dict[tuple[int, int], str] = {}
    action_item_due: dict[tuple[int, int], datetime] = {}
    for postmortem in tenant_postmortems:
        postmortem_id = int(postmortem.get("id", 0))
        for action_item in postmortem.get("action_items_detailed") or []:
            item_id = int(action_item.get("id", 0))
            action_item_owner[postmortem_id, item_id] = str(action_item.get("owner", "")).strip() or "unassigned"
            action_item_due[postmortem_id, item_id] = parse_iso(action_item.get("due_at"))
    owner_alerts: dict[str, dict[str, Any]] = {}
    for escalation in escalations:
        if str(escalation.get("status", "open")).lower() != "open":
            continue
        key = (int(escalation.get("postmortem_id", 0)), int(escalation.get("action_item_id", 0)))
        owner = action_item_owner.get(key, "unassigned")
        alert = owner_alerts.setdefault(
            owner,
            {
                "owner": owner,
                "new_open_escalations": 0,
                "new_critical_escalations": 0,
                "new_overdue_items": 0,
                "lookback_hours": lookback_hours,
            },
        )
        alert["new_open_escalations"] = int(alert["new_open_escalations"]) + 1
        if str(escalation.get("severity", "")).lower() == "critical":
            alert["new_critical_escalations"] = int(alert["new_critical_escalations"]) + 1
        due_at = action_item_due.get(key)
        if due_at is not None and due_at < now:
            alert["new_overdue_items"] = int(alert["new_overdue_items"]) + 1
    alerts: list[dict[str, Any]] = []
    for alert in owner_alerts.values():
        if int(alert.get("new_open_escalations", 0)) < min_new_open_escalations:
            continue
        critical = int(alert.get("new_critical_escalations", 0))
        if critical >= 1:
            severity = "critical"
        elif int(alert.get("new_open_escalations", 0)) >= 2:
            severity = "high"
        else:
            severity = "medium"
        alerts.append({**alert, "severity": severity})
    alerts.sort(
        key=lambda item: (
            0 if str(item.get("severity")) == "critical" else 1 if str(item.get("severity")) == "high" else 2,
            -int(item.get("new_open_escalations", 0)),
        )
    )
    return {
        "status": "ok",
        "lookback_hours": lookback_hours,
        "min_new_open_escalations": min_new_open_escalations,
        "alerts": alerts,
        "count": len(alerts),
    }


def execute_get_postmortem_action_item_balance_index(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:balance-index:get", 120, 60
    )
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        tenant_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    owner_open_counts: dict[str, int] = {}
    total_open_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_open_counts[owner] = int(owner_open_counts.get(owner, 0)) + 1
            total_open_items += 1
    owner_counts_sorted = sorted(owner_open_counts.values(), reverse=True)
    top_owner_count = owner_counts_sorted[0] if owner_counts_sorted else 0
    top_two_count = sum(owner_counts_sorted[:2]) if owner_counts_sorted else 0
    max_owner_share_pct = round(top_owner_count / total_open_items * 100, 2) if total_open_items else 0.0
    top_two_share_pct = round(top_two_count / total_open_items * 100, 2) if total_open_items else 0.0
    overloaded_owner_count = len([count for count in owner_counts_sorted if count > max_open_items_per_owner])
    balance_index = round(max(0.0, 100.0 - max_owner_share_pct), 2)
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "total_open_action_items": total_open_items,
        "owners_with_open_items": len(owner_open_counts),
        "open_escalations": len(tenant_escalations),
        "overloaded_owner_count": overloaded_owner_count,
        "max_owner_share_pct": max_owner_share_pct,
        "top_two_owner_share_pct": top_two_share_pct,
        "balance_index": balance_index,
    }
