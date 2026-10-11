"""Workflow use cases: assign runbook operator."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..graph import coerce_int as _coerce_int
from ..graph import parse_iso
from ..incidents import build_incident_timeline
from ..reliability import compute_reliability_snapshot
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorPostmortemRequest
from ..schemas import WorkflowConnectorPostmortemTemplateApplyRequest
from ..schemas import WorkflowConnectorPostmortemTemplateRequest
from ..schemas import WorkflowConnectorRunbookAssignmentRequest
from ..service import append_audit
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_assign_runbook_operator(
    runtime: WorkflowRuntime, runbook_id: int, payload: WorkflowConnectorRunbookAssignmentRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:runbooks:assign", 120, 60)
    with runtime.lock:
        runbook = next(
            (
                r
                for r in runtime.connector_runbooks
                if int(r.get("id", 0)) == runbook_id and r.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if runbook is None:
            raise HTTPException(status_code=404, detail="Runbook not found.")
        assignment = {
            "id": len(runtime.connector_runbook_assignments) + 1,
            "tenant_id": auth.tenant_id,
            "runbook_id": runbook_id,
            "runbook_name": runbook.get("name"),
            "operator": payload.operator,
            "role": payload.role,
            "note": payload.note,
            "status": "assigned",
            "created_at": datetime.now(UTC).isoformat(),
        }
        runtime.connector_runbook_assignments.append(assignment)
    append_audit(runtime, auth.tenant_id, "workflow_connector_runbook_operator_assigned", int(assignment["id"]))
    return {"status": "ok", "assignment": assignment}


def execute_list_runbook_assignments(runtime: WorkflowRuntime, runbook_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:runbooks:assignments:list", 120, 60)
    with runtime.lock:
        assignments = [
            a.copy()
            for a in runtime.connector_runbook_assignments
            if a.get("tenant_id") == auth.tenant_id and int(a.get("runbook_id", 0)) == runbook_id
        ]
    return {"status": "ok", "assignments": assignments, "total": len(assignments)}


def execute_get_connector_incident_timeline(
    runtime: WorkflowRuntime, connector_id: int, auth: AuthDep, limit: Annotated[int, Query(ge=1, le=300)] = 100
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:incident-timeline:list", 120, 60)
    with runtime.lock:
        connector = next(
            (
                c
                for c in runtime.connectors
                if int(c.get("id", 0)) == connector_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if connector is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        timeline = build_incident_timeline(runtime, tenant_id=auth.tenant_id, connector_id=connector_id, limit=limit)
    return {"status": "ok", "connector_id": connector_id, "timeline": timeline, "total": len(timeline)}


def execute_get_connector_sli_trends(
    runtime: WorkflowRuntime, connector_id: int, auth: AuthDep, buckets: Annotated[int, Query(ge=4, le=72)] = 12
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:sli-trends:list", 120, 60)
    with runtime.lock:
        connector = next(
            (
                c
                for c in runtime.connectors
                if int(c.get("id", 0)) == connector_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if connector is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        reliability = compute_reliability_snapshot(connector)
        open_alerts = len(
            [
                alert
                for alert in runtime.connector_sla_alerts
                if alert.get("tenant_id") == auth.tenant_id
                and int(alert.get("connector_id", 0)) == connector_id
                and (alert.get("status") == "open")
            ]
        )
        pending_replay = len(
            [
                item
                for item in runtime.connector_replay_queue
                if item.get("tenant_id") == auth.tenant_id
                and int(item.get("connector_id", 0)) == connector_id
                and (item.get("status") == "pending")
            ]
        )
    now = datetime.now(UTC)
    points: list[dict[str, Any]] = []
    base_availability = float(reliability.get("availability_pct_rolling", 100.0))
    base_latency = int(reliability.get("latency_p95_ms", 120))
    pressure = min(10.0, open_alerts * 0.8 + pending_replay * 0.3)
    for idx in range(buckets):
        hours_ago = buckets - idx - 1
        drift = hours_ago % 3 * 0.09
        availability = max(50.0, min(100.0, base_availability - pressure + drift))
        latency = max(50, base_latency + int(open_alerts * 9 + pending_replay * 4 + hours_ago % 5 * 5))
        points.append(
            {
                "bucket_start": (now - timedelta(hours=hours_ago)).isoformat(),
                "availability_pct": round(availability, 2),
                "latency_p95_ms": latency,
            }
        )
    return {
        "status": "ok",
        "connector_id": connector_id,
        "buckets": buckets,
        "points": points,
        "targets": {
            "availability_target_pct": float(reliability.get("availability_target_pct", 99.9)),
            "latency_target_p95_ms": int(reliability.get("latency_target_p95_ms", 500)),
        },
    }


def execute_create_postmortem_template(
    runtime: WorkflowRuntime, payload: WorkflowConnectorPostmortemTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:templates:create", 60, 60)
    with runtime.lock:
        template = {
            "id": len(runtime.connector_postmortem_templates) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name,
            "summary_template": payload.summary_template,
            "default_action_items": payload.default_action_items,
            "closure_sla_hours": payload.closure_sla_hours,
            "enabled": payload.enabled,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.connector_postmortem_templates.append(template)
    append_audit(
        runtime, auth.tenant_id, "workflow_connector_postmortem_template_created", _coerce_int(template.get("id"))
    )
    return {"status": "ok", "template": template}


def execute_list_postmortem_templates(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:templates:list", 120, 60)
    with runtime.lock:
        templates = [
            template.copy()
            for template in runtime.connector_postmortem_templates
            if template.get("tenant_id") == auth.tenant_id
        ]
    templates.sort(key=lambda item: parse_iso(item.get("created_at")), reverse=True)
    return {"status": "ok", "templates": templates, "total": len(templates)}


def execute_apply_postmortem_template(
    runtime: WorkflowRuntime, template_id: int, payload: WorkflowConnectorPostmortemTemplateApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:templates:apply", 60, 60)
    with runtime.lock:
        template = next(
            (
                t
                for t in runtime.connector_postmortem_templates
                if int(t.get("id", 0)) == template_id
                and t.get("tenant_id") == auth.tenant_id
                and bool(t.get("enabled", True))
            ),
            None,
        )
        if template is None:
            raise HTTPException(status_code=404, detail="Postmortem template not found.")
        connector = next(
            (
                c
                for c in runtime.connectors
                if int(c.get("id", 0)) == payload.connector_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if connector is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        valid_event_ids = {
            int(event.get("id", 0))
            for event in runtime.connector_escalation_events
            if event.get("tenant_id") == auth.tenant_id and int(event.get("connector_id", 0)) == payload.connector_id
        }
        incident_event_ids = [event_id for event_id in payload.incident_event_ids if event_id in valid_event_ids]
        now = datetime.now(UTC)
        closure_sla_hours = int(template.get("closure_sla_hours", 24))
        postmortem = {
            "id": len(runtime.connector_postmortems) + 1,
            "tenant_id": auth.tenant_id,
            "connector_id": payload.connector_id,
            "connector_name": connector.get("name"),
            "title": payload.title,
            "summary": template.get("summary_template", ""),
            "incident_event_ids": incident_event_ids,
            "action_items": list(template.get("default_action_items") or []),
            "action_items_detailed": [],
            "status": "open",
            "closure_sla_hours": closure_sla_hours,
            "target_close_by": (now + timedelta(hours=closure_sla_hours)).isoformat(),
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "template_id": template_id,
            "template_name": template.get("name"),
        }
        runtime.connector_postmortems.append(postmortem)
        for item_title in list(template.get("default_action_items") or []):
            detailed = {
                "id": len(postmortem["action_items_detailed"]) + 1,
                "title": item_title,
                "owner": "",
                "status": "open",
                "note": "",
                "due_at": (now + timedelta(hours=closure_sla_hours)).isoformat(),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
            postmortem["action_items_detailed"].append(detailed)
    append_audit(runtime, auth.tenant_id, "workflow_connector_postmortem_template_applied", int(postmortem["id"]))
    return {"status": "ok", "postmortem": postmortem}


def execute_create_connector_postmortem(
    runtime: WorkflowRuntime, connector_id: int, payload: WorkflowConnectorPostmortemRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:postmortems:create", 60, 60)
    with runtime.lock:
        connector = next(
            (
                c
                for c in runtime.connectors
                if int(c.get("id", 0)) == connector_id and c.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if connector is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        valid_event_ids = {
            int(event.get("id", 0))
            for event in runtime.connector_escalation_events
            if event.get("tenant_id") == auth.tenant_id and int(event.get("connector_id", 0)) == connector_id
        }
        incident_event_ids = [event_id for event_id in payload.incident_event_ids if event_id in valid_event_ids]
        postmortem = {
            "id": len(runtime.connector_postmortems) + 1,
            "tenant_id": auth.tenant_id,
            "connector_id": connector_id,
            "connector_name": connector.get("name"),
            "title": payload.title,
            "summary": payload.summary,
            "incident_event_ids": incident_event_ids,
            "action_items": payload.action_items,
            "action_items_detailed": [],
            "status": "open",
            "closure_sla_hours": 24,
            "target_close_by": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.connector_postmortems.append(postmortem)
    append_audit(runtime, auth.tenant_id, "workflow_connector_postmortem_created", int(postmortem["id"]))
    return {"status": "ok", "postmortem": postmortem}
