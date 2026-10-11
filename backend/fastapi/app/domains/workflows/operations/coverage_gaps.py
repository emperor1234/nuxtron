"""Workflow use cases: coverage gaps."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from datetime import UTC
from datetime import datetime
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_get_postmortem_action_item_coverage_gaps(
    runtime: WorkflowRuntime, auth: AuthDep, max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:coverage-gaps:get", 120, 60
    )
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
    owner_open_counts: dict[str, int] = {}
    total_open_items = 0
    for postmortem in tenant_postmortems:
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_open_counts[owner] = int(owner_open_counts.get(owner, 0)) + 1
            total_open_items += 1
    unassigned_open_items = int(owner_open_counts.get("unassigned", 0))
    overloaded_owners = [
        {"owner": owner, "open_action_items": count}
        for owner, count in owner_open_counts.items()
        if owner != "unassigned" and count > max_open_items_per_owner
    ]
    overload_count = len(overloaded_owners)
    max_owner_share_pct = (
        round(max(owner_open_counts.values()) / total_open_items * 100, 2) if total_open_items else 0.0
    )
    gaps: list[dict[str, Any]] = []
    if unassigned_open_items > 0:
        gaps.append(
            {
                "code": "unassigned_items",
                "severity": "high" if unassigned_open_items >= 2 else "medium",
                "count": unassigned_open_items,
                "message": "Open action items are unassigned.",
            }
        )
    if overload_count > 0:
        gaps.append(
            {
                "code": "overloaded_owner",
                "severity": "high" if overload_count >= 2 else "medium",
                "count": overload_count,
                "message": "One or more owners exceed open-item capacity threshold.",
            }
        )
    if max_owner_share_pct >= 70.0 and total_open_items >= 3:
        gaps.append(
            {
                "code": "single_owner_concentration",
                "severity": "high",
                "count": 1,
                "message": "A single owner carries most open action items.",
            }
        )
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "total_open_action_items": total_open_items,
        "unassigned_open_items": unassigned_open_items,
        "overloaded_owners": overloaded_owners,
        "max_owner_share_pct": max_owner_share_pct,
        "gaps": gaps,
        "count": len(gaps),
    }


def execute_get_postmortem_action_item_handoff_readiness(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    critical_open_escalations_threshold: Annotated[int, Query(ge=1, le=20)] = 1,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:handoff-readiness:get", 120, 60
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
            stats = owner_stats.setdefault(
                owner,
                {
                    "owner": owner,
                    "open_action_items": 0,
                    "overdue_open_items": 0,
                    "open_escalations": 0,
                    "critical_open_escalations": 0,
                    "acknowledged_escalations": 0,
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
                "acknowledged_escalations": 0,
            },
        )
        escalation_status = str(escalation.get("status", "open")).lower()
        if escalation_status == "open":
            stats["open_escalations"] = int(stats["open_escalations"]) + 1
            if str(escalation.get("severity", "")).lower() == "critical":
                stats["critical_open_escalations"] = int(stats["critical_open_escalations"]) + 1
        elif escalation_status == "acknowledged":
            stats["acknowledged_escalations"] = int(stats["acknowledged_escalations"]) + 1
    readiness: list[dict[str, Any]] = []
    for stats in owner_stats.values():
        open_items = int(stats.get("open_action_items", 0))
        overdue_items = int(stats.get("overdue_open_items", 0))
        critical_open_escalations = int(stats.get("critical_open_escalations", 0))
        open_escalations = int(stats.get("open_escalations", 0))
        if critical_open_escalations >= critical_open_escalations_threshold:
            readiness_status = "blocked"
        elif open_items > max_open_items_per_owner or overdue_items > 0 or open_escalations > 0:
            readiness_status = "at_risk"
        else:
            readiness_status = "ready"
        handoff_score = max(
            0, 100 - open_items * 12 - overdue_items * 15 - open_escalations * 20 - critical_open_escalations * 25
        )
        readiness.append(
            {
                **stats,
                "handoff_readiness_status": readiness_status,
                "handoff_readiness_score": handoff_score,
                "backup_recommended": readiness_status != "ready",
            }
        )
    readiness.sort(
        key=lambda item: (
            0
            if str(item.get("handoff_readiness_status")) == "blocked"
            else 1
            if str(item.get("handoff_readiness_status")) == "at_risk"
            else 2,
            int(item.get("handoff_readiness_score", 0)),
        )
    )
    return {
        "status": "ok",
        "max_open_items_per_owner": max_open_items_per_owner,
        "critical_open_escalations_threshold": critical_open_escalations_threshold,
        "owners": readiness,
        "count": len(readiness),
    }


def execute_get_postmortem_action_item_continuity_risks(
    runtime: WorkflowRuntime, auth: AuthDep, min_single_owner_items: Annotated[int, Query(ge=1, le=100)] = 2
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:continuity-risks:get", 120, 60
    )
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        tenant_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and str(item.get("status", "open")).lower() == "open"
        ]
    connector_owner_counts: dict[int, dict[str, int]] = {}
    connector_totals: dict[int, int] = {}
    action_item_owner: dict[tuple[int, int], str] = {}
    postmortem_connector: dict[int, int] = {}
    for postmortem in tenant_postmortems:
        postmortem_id = int(postmortem.get("id", 0))
        connector_id = int(postmortem.get("connector_id", 0))
        postmortem_connector[postmortem_id] = connector_id
        owner_counts = connector_owner_counts.setdefault(connector_id, {})
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_counts[owner] = int(owner_counts.get(owner, 0)) + 1
            connector_totals[connector_id] = int(connector_totals.get(connector_id, 0)) + 1
            action_item_owner[postmortem_id, int(action_item.get("id", 0))] = owner
    owner_open_escalations: dict[str, int] = {}
    for escalation in tenant_escalations:
        owner = action_item_owner.get(
            (int(escalation.get("postmortem_id", 0)), int(escalation.get("action_item_id", 0))), "unassigned"
        )
        owner_open_escalations[owner] = int(owner_open_escalations.get(owner, 0)) + 1
    risks: list[dict[str, Any]] = []
    for connector_id, owner_counts in connector_owner_counts.items():
        total = int(connector_totals.get(connector_id, 0))
        if total <= 0:
            continue
        dominant_owner, dominant_count = max(owner_counts.items(), key=lambda item: int(item[1]))
        dominant_share = round(int(dominant_count) / total * 100, 2)
        if int(dominant_count) >= min_single_owner_items and dominant_share >= 70.0:
            severity = "critical" if dominant_share >= 85.0 else "high"
            risks.append(
                {
                    "code": "single_owner_connector_dependency",
                    "severity": severity,
                    "connector_id": connector_id,
                    "owner": dominant_owner,
                    "owner_open_items": int(dominant_count),
                    "owner_share_pct": dominant_share,
                    "message": "Connector incident actions are heavily concentrated on one owner.",
                }
            )
    for owner, open_escalations in owner_open_escalations.items():
        if open_escalations < 2:
            continue
        risks.append(
            {
                "code": "escalation_concentration",
                "severity": "high" if open_escalations < 4 else "critical",
                "owner": owner,
                "open_escalations": int(open_escalations),
                "message": "Owner has concentrated open escalations requiring continuity planning.",
            }
        )
    risks.sort(
        key=lambda item: (
            0 if str(item.get("severity")) == "critical" else 1,
            -int(item.get("owner_open_items", item.get("open_escalations", 0))),
        )
    )
    return {"status": "ok", "min_single_owner_items": min_single_owner_items, "risks": risks, "count": len(risks)}


def execute_get_postmortem_action_item_ownership_churn(
    runtime: WorkflowRuntime, auth: AuthDep, min_owner_switch_risk_items: Annotated[int, Query(ge=1, le=100)] = 2
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:ownership-churn:get", 120, 60
    )
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        tenant_escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id
            and str(item.get("status", "open")).lower() in {"open", "acknowledged"}
        ]
    connector_owner_counts: dict[int, dict[str, int]] = {}
    connector_open_item_totals: dict[int, int] = {}
    action_item_owner: dict[tuple[int, int], str] = {}
    postmortem_connector: dict[int, int] = {}
    for postmortem in tenant_postmortems:
        connector_id = int(postmortem.get("connector_id", 0))
        postmortem_id = int(postmortem.get("id", 0))
        postmortem_connector[postmortem_id] = connector_id
        owner_counts = connector_owner_counts.setdefault(connector_id, {})
        for action_item in postmortem.get("action_items_detailed") or []:
            if str(action_item.get("status", "open")).lower() == "done":
                continue
            owner = str(action_item.get("owner", "")).strip() or "unassigned"
            owner_counts[owner] = int(owner_counts.get(owner, 0)) + 1
            connector_open_item_totals[connector_id] = int(connector_open_item_totals.get(connector_id, 0)) + 1
            action_item_owner[postmortem_id, int(action_item.get("id", 0))] = owner
    connector_open_escalation_owners: dict[int, set[str]] = {}
    for escalation in tenant_escalations:
        postmortem_id = int(escalation.get("postmortem_id", 0))
        connector_id = int(postmortem_connector.get(postmortem_id, 0))
        owner = action_item_owner.get((postmortem_id, int(escalation.get("action_item_id", 0))), "unassigned")
        connector_open_escalation_owners.setdefault(connector_id, set()).add(owner)
    churn_rows: list[dict[str, Any]] = []
    for connector_id, owner_counts in connector_owner_counts.items():
        total_items = int(connector_open_item_totals.get(connector_id, 0))
        if total_items <= 0:
            continue
        distinct_owners = len(owner_counts)
        unassigned_items = int(owner_counts.get("unassigned", 0))
        top_owner_count = max(owner_counts.values()) if owner_counts else 0
        top_owner_share_pct = round(int(top_owner_count) / total_items * 100, 2)
        escalation_owners = connector_open_escalation_owners.get(connector_id, set())
        owner_switch_risk_items = sum((1 for count in owner_counts.values() if int(count) == 1))
        churn_index = round(
            min(
                100.0,
                distinct_owners * 12
                + len(escalation_owners) * 14
                + unassigned_items * 18
                + (40.0 if 35.0 <= top_owner_share_pct <= 75.0 else 0.0),
            ),
            2,
        )
        if churn_index >= 70.0:
            severity = "high"
        elif churn_index >= 40.0:
            severity = "medium"
        else:
            severity = "low"
        churn_rows.append(
            {
                "connector_id": connector_id,
                "open_action_items": total_items,
                "distinct_active_owners": distinct_owners,
                "unassigned_open_items": unassigned_items,
                "top_owner_share_pct": top_owner_share_pct,
                "open_escalation_owners": len(escalation_owners),
                "owner_switch_risk_items": owner_switch_risk_items,
                "churn_index": churn_index,
                "severity": severity,
                "needs_assignment_normalization": owner_switch_risk_items >= min_owner_switch_risk_items,
            }
        )
    churn_rows.sort(key=lambda item: float(item.get("churn_index", 0.0)), reverse=True)
    return {
        "status": "ok",
        "min_owner_switch_risk_items": min_owner_switch_risk_items,
        "connectors": churn_rows,
        "count": len(churn_rows),
    }
