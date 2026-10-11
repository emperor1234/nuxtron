"""Workflow use cases: process postmortem escalation cadence."""

from ..constants import AuthDep
from ..graph import coerce_int as _coerce_int
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorEscalationCadenceProcessRequest
from ..schemas import WorkflowConnectorEscalationSuppressionProcessRequest
from ..service import append_audit
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_process_postmortem_escalation_cadence(
    runtime: WorkflowRuntime, payload: WorkflowConnectorEscalationCadenceProcessRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:escalation-cadence:process", 60, 60)
    now = datetime.now(UTC)
    processed: list[dict[str, Any]] = []
    with runtime.lock:
        policy = next(
            (
                p
                for p in runtime.connector_postmortem_escalation_cadence_policies
                if p.get("tenant_id") == auth.tenant_id and bool(p.get("enabled", False))
            ),
            None,
        )
        if policy is None:
            return {"status": "ok", "processed": [], "count": 0}
        l2_after = int(policy.get("l2_after_minutes", 30))
        l3_after = int(policy.get("l3_after_minutes", 90))
        repage_interval = int(policy.get("repage_interval_minutes", 30))
        max_repages = int(policy.get("max_repages", 8))
        suppression_ttl_minutes = int(policy.get("suppression_ttl_minutes", 240))
        l1_recipients = list(policy.get("l1_recipients", []))
        l2_recipients = list(policy.get("l2_recipients", []))
        l3_recipients = list(policy.get("l3_recipients", []))
        for escalation in runtime.connector_postmortem_action_item_escalations:
            if escalation.get("tenant_id") != auth.tenant_id or escalation.get("status") != "open":
                continue
            next_repage_at = parse_iso(escalation.get("next_repage_at"))
            if next_repage_at > now:
                continue
            created_at = parse_iso(escalation.get("created_at"))
            elapsed_minutes = max(0, int((now - created_at).total_seconds() // 60))
            current_tier = str(escalation.get("tier", "l1")).lower()
            target_tier = current_tier
            if elapsed_minutes >= l3_after:
                target_tier = "l3"
            elif elapsed_minutes >= l2_after and current_tier == "l1":
                target_tier = "l2"
            if target_tier == "l1":
                recipients = l1_recipients
            elif target_tier == "l2":
                recipients = l2_recipients
            else:
                recipients = l3_recipients
            repage_count = int(escalation.get("repage_count", 0)) + 1
            escalation["tier"] = target_tier
            escalation["notify_recipients"] = recipients
            escalation["repage_count"] = repage_count
            escalation["last_paged_at"] = now.isoformat()
            escalation["next_repage_at"] = (now + timedelta(minutes=repage_interval)).isoformat()
            if repage_count >= max_repages:
                escalation["status"] = "suppressed"
                escalation["suppressed_at"] = now.isoformat()
                escalation["suppressed_until"] = (now + timedelta(minutes=suppression_ttl_minutes)).isoformat()
            processed.append(escalation.copy())
            if len(processed) >= payload.limit:
                break
    append_audit(runtime, auth.tenant_id, "workflow_connector_postmortem_escalation_cadence_processed", len(processed))
    return {"status": "ok", "processed": processed, "count": len(processed)}


def execute_process_postmortem_escalation_suppression(
    runtime: WorkflowRuntime, payload: WorkflowConnectorEscalationSuppressionProcessRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:escalation-suppression:process", 60, 60
    )
    now = datetime.now(UTC)
    reopened: list[dict[str, Any]] = []
    with runtime.lock:
        policy = next(
            (
                p
                for p in runtime.connector_postmortem_escalation_cadence_policies
                if p.get("tenant_id") == auth.tenant_id and bool(p.get("enabled", False))
            ),
            None,
        )
        if policy is None or not bool(policy.get("reopen_on_reoverdue", True)):
            return {"status": "ok", "reopened": [], "count": 0}
        for escalation in runtime.connector_postmortem_action_item_escalations:
            if escalation.get("tenant_id") != auth.tenant_id or escalation.get("status") != "suppressed":
                continue
            suppressed_until = parse_iso(escalation.get("suppressed_until"))
            if suppressed_until > now:
                continue
            postmortem = next(
                (
                    p
                    for p in runtime.connector_postmortems
                    if int(p.get("id", 0)) == int(escalation.get("postmortem_id", 0))
                    and p.get("tenant_id") == auth.tenant_id
                ),
                None,
            )
            if postmortem is None:
                continue
            action_item = next(
                (
                    item
                    for item in postmortem.get("action_items_detailed") or []
                    if int(item.get("id", 0)) == int(escalation.get("action_item_id", 0))
                ),
                None,
            )
            if action_item is None:
                continue
            if str(action_item.get("status", "")).lower() == "done":
                escalation["status"] = "closed"
                escalation["closed_at"] = now.isoformat()
                continue
            escalation["status"] = "open"
            escalation["tier"] = "l1"
            escalation["reopened_at"] = now.isoformat()
            escalation["next_repage_at"] = now.isoformat()
            reopened.append(escalation.copy())
            if len(reopened) >= payload.limit:
                break
    append_audit(
        runtime, auth.tenant_id, "workflow_connector_postmortem_escalation_suppression_processed", len(reopened)
    )
    return {"status": "ok", "reopened": reopened, "count": len(reopened)}


def execute_get_postmortem_escalation_aging_dashboard(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    ack_slo_minutes: Annotated[int, Query(ge=5, le=2880)] = 60,
    lookback_hours: Annotated[int, Query(ge=1, le=720)] = 168,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:escalation-aging:get", 120, 60)
    now = datetime.now(UTC)
    lookback_start = now - timedelta(hours=lookback_hours)
    with runtime.lock:
        escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id and parse_iso(item.get("created_at")) >= lookback_start
        ]
    open_escalations = [item for item in escalations if item.get("status") == "open"]
    acknowledged_escalations = [
        item for item in escalations if item.get("status") in {"acknowledged", "closed"} and item.get("acknowledged_at")
    ]
    ack_within_slo = 0
    for item in acknowledged_escalations:
        created_at = parse_iso(item.get("created_at"))
        acknowledged_at = parse_iso(item.get("acknowledged_at"))
        ack_minutes = int((acknowledged_at - created_at).total_seconds() // 60)
        if ack_minutes <= ack_slo_minutes:
            ack_within_slo += 1
    age_0_30 = 0
    age_31_120 = 0
    age_121_plus = 0
    for item in open_escalations:
        age_minutes = int((now - parse_iso(item.get("created_at"))).total_seconds() // 60)
        if age_minutes <= 30:
            age_0_30 += 1
        elif age_minutes <= 120:
            age_31_120 += 1
        else:
            age_121_plus += 1
    ack_slo_compliance_pct = (
        round(ack_within_slo / len(acknowledged_escalations) * 100, 2) if acknowledged_escalations else 100.0
    )
    return {
        "status": "ok",
        "ack_slo_minutes": ack_slo_minutes,
        "lookback_hours": lookback_hours,
        "total_escalations": len(escalations),
        "open_escalations": len(open_escalations),
        "acknowledged_escalations": len(acknowledged_escalations),
        "ack_slo_compliance_pct": ack_slo_compliance_pct,
        "age_buckets": {"0_30_minutes": age_0_30, "31_120_minutes": age_31_120, "121_plus_minutes": age_121_plus},
    }


def execute_get_postmortem_action_item_breach_forecast(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    window_hours: Annotated[int, Query(ge=1, le=168)] = 24,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:breach-forecast:get", 120, 60
    )
    now = datetime.now(UTC)
    window_end = now + timedelta(hours=window_hours)
    at_risk_items: list[dict[str, Any]] = []
    with runtime.lock:
        tenant_postmortems = [p.copy() for p in runtime.connector_postmortems if p.get("tenant_id") == auth.tenant_id]
        escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id
        ]
    escalation_by_action_item: dict[tuple[int, int], dict[str, Any]] = {}
    for escalation in escalations:
        key = (int(escalation.get("postmortem_id", 0)), int(escalation.get("action_item_id", 0)))
        existing = escalation_by_action_item.get(key)
        if existing is None or parse_iso(escalation.get("created_at")) > parse_iso(existing.get("created_at")):
            escalation_by_action_item[key] = escalation
    for postmortem in tenant_postmortems:
        if str(postmortem.get("status", "")).lower() == "closed":
            continue
        connector_id = int(postmortem.get("connector_id", 0))
        for action_item in postmortem.get("action_items_detailed") or []:
            action_status = str(action_item.get("status", "")).lower()
            if action_status == "done":
                continue
            due_at = parse_iso(action_item.get("due_at"))
            if due_at > window_end and due_at >= now:
                continue
            minutes_to_due = int((due_at - now).total_seconds() // 60)
            if due_at < now:
                risk_level = "breached"
            elif minutes_to_due <= 60:
                risk_level = "critical_soon"
            elif minutes_to_due <= 240:
                risk_level = "high_soon"
            else:
                risk_level = "due_soon"
            escalation: dict[str, Any] | None = escalation_by_action_item.get(
                (_coerce_int(postmortem.get("id", 0)), _coerce_int(action_item.get("id", 0)))
            )
            at_risk_items.append(
                {
                    "connector_id": connector_id,
                    "postmortem_id": int(postmortem.get("id", 0)),
                    "action_item_id": int(action_item.get("id", 0)),
                    "action_item_title": action_item.get("title", ""),
                    "action_item_status": action_item.get("status", ""),
                    "owner": action_item.get("owner", ""),
                    "due_at": due_at.isoformat(),
                    "minutes_to_due": minutes_to_due,
                    "risk_level": risk_level,
                    "escalation_status": escalation.get("status") if escalation else None,
                    "escalation_tier": escalation.get("tier") if escalation else None,
                }
            )
    risk_order = {"breached": 0, "critical_soon": 1, "high_soon": 2, "due_soon": 3}
    at_risk_items.sort(
        key=lambda item: (
            risk_order.get(str(item.get("risk_level", "due_soon")), 9),
            int(item.get("minutes_to_due", 0)),
        )
    )
    trimmed = at_risk_items[:limit]
    breached_count = len([item for item in trimmed if item.get("risk_level") == "breached"])
    return {
        "status": "ok",
        "window_hours": window_hours,
        "total_candidates": len(at_risk_items),
        "at_risk_total": len(trimmed),
        "breached_count": breached_count,
        "items": trimmed,
    }


def execute_get_postmortem_escalation_priority_queue(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    include_suppressed: bool = True,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalations:priority-queue:get", 120, 60
    )
    now = datetime.now(UTC)
    with runtime.lock:
        candidates = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id
            and str(item.get("status", ""))
            in ({"open", "acknowledged", "suppressed"} if include_suppressed else {"open", "acknowledged"})
        ]
    severity_weights = {"critical": 4, "high": 3, "medium": 2}
    tier_boost = {"l3": 25, "l2": 15, "l1": 5}
    queue_items: list[dict[str, Any]] = []
    for escalation in candidates:
        created_at = parse_iso(escalation.get("created_at"))
        age_minutes = max(0, int((now - created_at).total_seconds() // 60))
        severity = str(escalation.get("severity", "medium")).lower()
        tier = str(escalation.get("tier", "l1")).lower()
        repage_count = int(escalation.get("repage_count", 0))
        status = str(escalation.get("status", "open")).lower()
        status_penalty = 10 if status == "acknowledged" else 0
        suppression_boost = 30 if status == "suppressed" else 0
        priority_score = (
            severity_weights.get(severity, 1) * 100
            + tier_boost.get(tier, 0)
            + min(age_minutes, 720)
            + repage_count * 5
            + suppression_boost
            - status_penalty
        )
        if status == "suppressed":
            recommended_action = "process_suppression"
        elif tier == "l3":
            recommended_action = "exec_page"
        elif repage_count >= 3:
            recommended_action = "incident_command_review"
        elif status == "acknowledged":
            recommended_action = "follow_up_owner"
        else:
            recommended_action = "repage_or_ack"
        queue_items.append(
            {
                **escalation,
                "age_minutes": age_minutes,
                "priority_score": priority_score,
                "recommended_action": recommended_action,
            }
        )
    queue_items.sort(key=lambda item: int(item.get("priority_score", 0)), reverse=True)
    ranked = []
    for idx, item in enumerate(queue_items[:limit], start=1):
        item_with_rank = item.copy()
        item_with_rank["rank"] = idx
        ranked.append(item_with_rank)
    return {
        "status": "ok",
        "include_suppressed": include_suppressed,
        "total_candidates": len(queue_items),
        "queue": ranked,
        "count": len(ranked),
    }
