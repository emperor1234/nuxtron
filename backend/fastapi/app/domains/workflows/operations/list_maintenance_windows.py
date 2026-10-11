"""Workflow use cases: list maintenance windows."""

from ..constants import AuthDep
from ..graph import coerce_int as _coerce_int
from ..reliability import compute_reliability_snapshot
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorEscalationAcknowledgeRequest
from ..schemas import WorkflowConnectorEscalationRuleRequest
from ..schemas import WorkflowConnectorRunbookRequest
from ..service import append_audit
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_list_maintenance_windows(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:maintenance:list", 120, 60)
    with runtime.lock:
        windows = [w.copy() for w in runtime.connector_maintenance_windows if w.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "windows": windows, "total": len(windows)}


def execute_create_escalation_rule(
    runtime: WorkflowRuntime, payload: WorkflowConnectorEscalationRuleRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:escalation-rules:create", 60, 60)
    with runtime.lock:
        rule = {
            "id": len(runtime.connector_escalation_rules) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name,
            "min_breach_count": payload.min_breach_count,
            "channels": payload.channels,
            "notify_recipients": payload.notify_recipients,
            "enabled": payload.enabled,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.connector_escalation_rules.append(rule)
    append_audit(runtime, auth.tenant_id, "workflow_connector_escalation_rule_created", _coerce_int(rule.get("id")))
    return {"status": "ok", "rule": rule}


def execute_list_escalation_rules(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:escalation-rules:list", 120, 60)
    with runtime.lock:
        rules = [r.copy() for r in runtime.connector_escalation_rules if r.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "rules": rules, "total": len(rules)}


def execute_list_escalation_events(
    runtime: WorkflowRuntime, auth: AuthDep, limit: Annotated[int, Query(ge=1, le=200)] = 100
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:escalation-events:list", 120, 60)
    with runtime.lock:
        events = [e.copy() for e in runtime.connector_escalation_events if e.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "events": events[:limit], "total": len(events)}


def execute_acknowledge_escalation_event(
    runtime: WorkflowRuntime, event_id: int, payload: WorkflowConnectorEscalationAcknowledgeRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:escalation-events:ack", 120, 60)
    with runtime.lock:
        event = next(
            (
                e
                for e in runtime.connector_escalation_events
                if int(e.get("id", 0)) == event_id and e.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if event is None:
            raise HTTPException(status_code=404, detail="Escalation event not found.")
        event["status"] = "acknowledged"
        event["acknowledged_by"] = payload.acknowledged_by
        event["acknowledged_note"] = payload.note
        event["acknowledged_at"] = datetime.now(UTC).isoformat()
    append_audit(runtime, auth.tenant_id, "workflow_connector_escalation_event_acknowledged", event_id)
    return {"status": "ok", "event": event}


def execute_auto_resolve_escalations(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:escalation-events:auto-resolve", 60, 60)
    resolved_alert_ids: list[int] = []
    resolved_event_ids: list[int] = []
    now = datetime.now(UTC).isoformat()
    with runtime.lock:
        for alert in runtime.connector_sla_alerts:
            if alert.get("tenant_id") != auth.tenant_id or alert.get("status") != "open":
                continue
            connector_id = int(alert.get("connector_id", 0))
            connector = next(
                (
                    c
                    for c in runtime.connectors
                    if int(c.get("id", 0)) == connector_id and c.get("tenant_id") == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                continue
            reliability = compute_reliability_snapshot(connector)
            recovered = not bool(reliability.get("availability_breached")) and (
                not bool(reliability.get("latency_breached"))
            )
            if not recovered:
                continue
            alert["status"] = "resolved"
            alert["resolved_at"] = now
            resolved_alert_ids.append(int(alert.get("id", 0)))
            for event in runtime.connector_escalation_events:
                if (
                    event.get("tenant_id") == auth.tenant_id
                    and int(event.get("alert_id", 0)) == int(alert.get("id", 0))
                    and (event.get("status") in {"triggered", "acknowledged"})
                ):
                    event["status"] = "resolved"
                    event["resolved_at"] = now
                    resolved_event_ids.append(int(event.get("id", 0)))
        for event in runtime.connector_escalation_events:
            if event.get("tenant_id") != auth.tenant_id or event.get("status") not in {"triggered", "acknowledged"}:
                continue
            alert_id = int(event.get("alert_id", 0))
            linked_alert = next(
                (
                    a
                    for a in runtime.connector_sla_alerts
                    if int(a.get("id", 0)) == alert_id and a.get("tenant_id") == auth.tenant_id
                ),
                None,
            )
            if linked_alert is not None and linked_alert.get("status") == "open":
                continue
            event["status"] = "resolved"
            event["resolved_at"] = now
            event_id = int(event.get("id", 0))
            if event_id not in resolved_event_ids:
                resolved_event_ids.append(event_id)
    append_audit(runtime, auth.tenant_id, "workflow_connector_escalations_auto_resolved", len(resolved_event_ids))
    return {
        "status": "ok",
        "resolved_alert_ids": resolved_alert_ids,
        "resolved_event_ids": resolved_event_ids,
        "alerts_resolved": len(resolved_alert_ids),
        "events_resolved": len(resolved_event_ids),
    }


def execute_create_connector_runbook(
    runtime: WorkflowRuntime, payload: WorkflowConnectorRunbookRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:runbooks:create", 60, 60)
    with runtime.lock:
        runbook = {
            "id": len(runtime.connector_runbooks) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name,
            "description": payload.description,
            "connector_ids": payload.connector_ids,
            "steps": payload.steps,
            "enabled": payload.enabled,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.connector_runbooks.append(runbook)
    append_audit(runtime, auth.tenant_id, "workflow_connector_runbook_created", _coerce_int(runbook.get("id")))
    return {"status": "ok", "runbook": runbook}


def execute_list_connector_runbooks(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:runbooks:list", 120, 60)
    with runtime.lock:
        runbooks = [r.copy() for r in runtime.connector_runbooks if r.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "runbooks": runbooks, "total": len(runbooks)}
