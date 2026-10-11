"""Workflow use cases: decide postmortem closure request."""

from ..constants import AuthDep
from ..graph import parse_iso
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorEscalationAcknowledgeAdminRequest
from ..schemas import WorkflowConnectorEscalationCadencePolicyRequest
from ..schemas import WorkflowConnectorEscalationRoutingPolicyRequest
from ..schemas import WorkflowConnectorOverdueEscalationProcessRequest
from ..schemas import WorkflowConnectorPostmortemClosureDecisionRequest
from ..service import append_audit
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_decide_postmortem_closure_request(
    runtime: WorkflowRuntime,
    connector_id: int,
    postmortem_id: int,
    request_id: int,
    payload: WorkflowConnectorPostmortemClosureDecisionRequest,
    auth: AuthDep,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:closure-requests:decision", 120, 60)
    decision = payload.decision.strip().lower()
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail="Invalid decision.")
    with runtime.lock:
        closure_request = next(
            (
                r
                for r in runtime.connector_postmortem_closure_requests
                if int(r.get("id", 0)) == request_id
                and int(r.get("connector_id", 0)) == connector_id
                and (int(r.get("postmortem_id", 0)) == postmortem_id)
                and (r.get("tenant_id") == auth.tenant_id)
            ),
            None,
        )
        if closure_request is None:
            raise HTTPException(status_code=404, detail="Closure request not found.")
        if closure_request.get("status") not in {"pending", "approved"}:
            raise HTTPException(status_code=409, detail="Closure request is not active.")
        if decision == "approve":
            approved_by = closure_request.setdefault("approved_by", [])
            if payload.reviewer not in approved_by:
                approved_by.append(payload.reviewer)
            required_approvals = int(closure_request.get("required_approvals", 1))
            closure_request["status"] = "approved" if len(approved_by) >= required_approvals else "pending"
        else:
            rejected_by = closure_request.setdefault("rejected_by", [])
            if payload.reviewer not in rejected_by:
                rejected_by.append(payload.reviewer)
            closure_request["status"] = "rejected"
        closure_request["last_decision"] = {
            "decision": decision,
            "reviewer": payload.reviewer,
            "note": payload.note,
            "decided_at": datetime.now(UTC).isoformat(),
        }
        closure_request["updated_at"] = datetime.now(UTC).isoformat()
    append_audit(runtime, auth.tenant_id, "workflow_connector_postmortem_closure_request_decided", request_id)
    return {"status": "ok", "closure_request": closure_request}


def execute_process_overdue_postmortem_action_items(
    runtime: WorkflowRuntime, payload: WorkflowConnectorOverdueEscalationProcessRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:overdue:process", 60, 60
    )
    processed: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    with runtime.lock:
        for postmortem in runtime.connector_postmortems:
            if postmortem.get("tenant_id") != auth.tenant_id:
                continue
            connector_id = int(postmortem.get("connector_id", 0))
            if payload.connector_id is not None and connector_id != payload.connector_id:
                continue
            if postmortem.get("status") == "closed":
                continue
            for action_item in postmortem.get("action_items_detailed") or []:
                if str(action_item.get("status", "")).lower() == "done":
                    continue
                due_at = parse_iso(action_item.get("due_at"))
                if due_at > now and (not payload.include_not_due):
                    continue
                overdue_hours = max(0, int((now - due_at).total_seconds() // 3600))
                policy = next(
                    (
                        p
                        for p in runtime.connector_postmortem_escalation_routing_policies
                        if p.get("tenant_id") == auth.tenant_id and bool(p.get("enabled", True))
                    ),
                    None,
                )
                if policy is None:
                    policy = {
                        "medium_threshold_hours": 1,
                        "high_threshold_hours": 24,
                        "critical_threshold_hours": 72,
                        "paging_start_hour_utc": 8,
                        "paging_end_hour_utc": 20,
                        "in_window_channel": "pagerduty",
                        "off_window_channel": "email",
                        "medium_recipients": [],
                        "high_recipients": [],
                        "critical_recipients": [],
                    }
                medium_threshold = int(policy.get("medium_threshold_hours", 1))
                high_threshold = int(policy.get("high_threshold_hours", 24))
                critical_threshold = int(policy.get("critical_threshold_hours", 72))
                if overdue_hours >= critical_threshold:
                    severity = "critical"
                elif overdue_hours >= high_threshold:
                    severity = "high"
                elif overdue_hours >= medium_threshold:
                    severity = "medium"
                else:
                    severity = "medium"
                start_hour = int(policy.get("paging_start_hour_utc", 8))
                end_hour = int(policy.get("paging_end_hour_utc", 20))
                hour = now.hour
                if start_hour == end_hour:
                    in_window = True
                elif start_hour < end_hour:
                    in_window = start_hour <= hour < end_hour
                else:
                    in_window = hour >= start_hour or hour < end_hour
                channel = (
                    str(policy.get("in_window_channel", "pagerduty"))
                    if in_window
                    else str(policy.get("off_window_channel", "email"))
                )
                recipients = list(policy.get(f"{severity}_recipients", []))
                already_escalated = any(
                    (
                        int(escalation.get("postmortem_id", 0)) == int(postmortem.get("id", 0))
                        and int(escalation.get("action_item_id", 0)) == int(action_item.get("id", 0))
                        and (escalation.get("status") == "open")
                        for escalation in runtime.connector_postmortem_action_item_escalations
                        if escalation.get("tenant_id") == auth.tenant_id
                    )
                )
                if already_escalated:
                    continue
                escalation = {
                    "id": len(runtime.connector_postmortem_action_item_escalations) + 1,
                    "tenant_id": auth.tenant_id,
                    "connector_id": connector_id,
                    "postmortem_id": int(postmortem.get("id", 0)),
                    "action_item_id": int(action_item.get("id", 0)),
                    "owner": action_item.get("owner", ""),
                    "status": "open",
                    "reason": "action_item_overdue",
                    "severity": severity,
                    "channel": channel,
                    "in_paging_window": in_window,
                    "notify_recipients": recipients,
                    "overdue_hours": overdue_hours,
                    "tier": "l1",
                    "repage_count": 0,
                    "first_paged_at": now.isoformat(),
                    "last_paged_at": now.isoformat(),
                    "next_repage_at": now.isoformat(),
                    "created_at": now.isoformat(),
                }
                runtime.connector_postmortem_action_item_escalations.append(escalation)
                action_item["status"] = "blocked"
                action_item["updated_at"] = now.isoformat()
                processed.append(escalation)
                if len(processed) >= payload.limit:
                    break
            if len(processed) >= payload.limit:
                break
    append_audit(
        runtime, auth.tenant_id, "workflow_connector_postmortem_overdue_action_items_processed", len(processed)
    )
    return {"status": "ok", "processed": processed, "count": len(processed)}


def execute_list_postmortem_action_item_escalations(
    runtime: WorkflowRuntime, auth: AuthDep, limit: Annotated[int, Query(ge=1, le=500)] = 100
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:overdue:list", 120, 60)
    with runtime.lock:
        escalations = [
            item.copy()
            for item in runtime.connector_postmortem_action_item_escalations
            if item.get("tenant_id") == auth.tenant_id
        ]
    escalations.sort(key=lambda item: parse_iso(item.get("created_at")), reverse=True)
    return {"status": "ok", "escalations": escalations[:limit], "total": len(escalations)}


def execute_acknowledge_action_item_escalation(
    runtime: WorkflowRuntime,
    escalation_id: int,
    payload: WorkflowConnectorEscalationAcknowledgeAdminRequest,
    auth: AuthDep,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(
        f"{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalations:ack", 120, 60
    )
    with runtime.lock:
        escalation = next(
            (
                item
                for item in runtime.connector_postmortem_action_item_escalations
                if int(item.get("id", 0)) == escalation_id and item.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if escalation is None:
            raise HTTPException(status_code=404, detail="Escalation not found.")
        escalation["status"] = "acknowledged"
        escalation["acknowledged_by"] = payload.acknowledged_by
        escalation["acknowledged_note"] = payload.note
        escalation["acknowledged_at"] = datetime.now(UTC).isoformat()
    append_audit(
        runtime, auth.tenant_id, "workflow_connector_postmortem_action_item_escalation_acknowledged", escalation_id
    )
    return {"status": "ok", "escalation": escalation}


def execute_upsert_postmortem_escalation_routing_policy(
    runtime: WorkflowRuntime, payload: WorkflowConnectorEscalationRoutingPolicyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:escalation-routing:upsert", 60, 60)
    with runtime.lock:
        policy = next(
            (
                p
                for p in runtime.connector_postmortem_escalation_routing_policies
                if p.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if policy is None:
            policy = {
                "id": len(runtime.connector_postmortem_escalation_routing_policies) + 1,
                "tenant_id": auth.tenant_id,
                "created_at": datetime.now(UTC).isoformat(),
            }
            runtime.connector_postmortem_escalation_routing_policies.append(policy)
        policy.update(
            {
                "enabled": payload.enabled,
                "paging_start_hour_utc": payload.paging_start_hour_utc,
                "paging_end_hour_utc": payload.paging_end_hour_utc,
                "in_window_channel": payload.in_window_channel,
                "off_window_channel": payload.off_window_channel,
                "medium_threshold_hours": payload.medium_threshold_hours,
                "high_threshold_hours": payload.high_threshold_hours,
                "critical_threshold_hours": payload.critical_threshold_hours,
                "medium_recipients": payload.medium_recipients,
                "high_recipients": payload.high_recipients,
                "critical_recipients": payload.critical_recipients,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
    append_audit(
        runtime, auth.tenant_id, "workflow_connector_postmortem_escalation_routing_policy_upserted", int(policy["id"])
    )
    return {"status": "ok", "policy": policy}


def execute_get_postmortem_escalation_routing_policy(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:escalation-routing:get", 120, 60)
    with runtime.lock:
        policy = next(
            (
                p.copy()
                for p in runtime.connector_postmortem_escalation_routing_policies
                if p.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
    if policy is None:
        return {
            "status": "ok",
            "policy": {
                "enabled": False,
                "paging_start_hour_utc": 8,
                "paging_end_hour_utc": 20,
                "in_window_channel": "pagerduty",
                "off_window_channel": "email",
                "medium_threshold_hours": 1,
                "high_threshold_hours": 24,
                "critical_threshold_hours": 72,
                "medium_recipients": [],
                "high_recipients": [],
                "critical_recipients": [],
            },
        }
    return {"status": "ok", "policy": policy}


def execute_upsert_postmortem_escalation_cadence_policy(
    runtime: WorkflowRuntime, payload: WorkflowConnectorEscalationCadencePolicyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:escalation-cadence:upsert", 60, 60)
    with runtime.lock:
        policy = next(
            (
                p
                for p in runtime.connector_postmortem_escalation_cadence_policies
                if p.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if policy is None:
            policy = {
                "id": len(runtime.connector_postmortem_escalation_cadence_policies) + 1,
                "tenant_id": auth.tenant_id,
                "created_at": datetime.now(UTC).isoformat(),
            }
            runtime.connector_postmortem_escalation_cadence_policies.append(policy)
        policy.update(
            {
                "enabled": payload.enabled,
                "l2_after_minutes": payload.l2_after_minutes,
                "l3_after_minutes": payload.l3_after_minutes,
                "repage_interval_minutes": payload.repage_interval_minutes,
                "max_repages": payload.max_repages,
                "suppression_ttl_minutes": payload.suppression_ttl_minutes,
                "reopen_on_reoverdue": payload.reopen_on_reoverdue,
                "l1_recipients": payload.l1_recipients,
                "l2_recipients": payload.l2_recipients,
                "l3_recipients": payload.l3_recipients,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
    append_audit(
        runtime, auth.tenant_id, "workflow_connector_postmortem_escalation_cadence_policy_upserted", int(policy["id"])
    )
    return {"status": "ok", "policy": policy}


def execute_get_postmortem_escalation_cadence_policy(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:escalation-cadence:get", 120, 60)
    with runtime.lock:
        policy = next(
            (
                p.copy()
                for p in runtime.connector_postmortem_escalation_cadence_policies
                if p.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
    if policy is None:
        return {
            "status": "ok",
            "policy": {
                "enabled": False,
                "l2_after_minutes": 30,
                "l3_after_minutes": 90,
                "repage_interval_minutes": 30,
                "max_repages": 8,
                "suppression_ttl_minutes": 240,
                "reopen_on_reoverdue": True,
                "l1_recipients": [],
                "l2_recipients": [],
                "l3_recipients": [],
            },
        }
    return {"status": "ok", "policy": policy}
