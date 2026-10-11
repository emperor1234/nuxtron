"""Workflow use cases: list workflow approval policies."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..constants import WORKFLOW_NOT_FOUND
from ..graph import coerce_int as _coerce_int
from ..graph import count_approvals
from ..reliability import ensure_reliability_fields
from ..runtime import WorkflowRuntime
from ..schemas import ApprovalDecisionRequest
from ..schemas import ApprovalRequestCreateRequest
from ..schemas import WorkflowConnectorMaintenanceWindowRequest
from ..schemas import WorkflowConnectorTemplateApplyRequest
from ..schemas import WorkflowConnectorTemplateRequest
from ..service import append_audit
from ..service import get_policy
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_list_workflow_approval_policies(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:approval-policy:list", 120, 60)
    with runtime.lock:
        policies = [p.copy() for p in runtime.approval_policies if p.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "policies": policies, "total": len(policies)}


def execute_create_approval_request(
    runtime: WorkflowRuntime, payload: ApprovalRequestCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:approval-request:create", 60, 60)
    with runtime.lock:
        wf = next(
            (
                w
                for w in runtime.workflows
                if w.get("id") == payload.workflow_id and w.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if wf is None:
            raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
        request: dict[str, Any] = {
            "id": len(runtime.approval_requests) + 1,
            "tenant_id": auth.tenant_id,
            "workflow_id": payload.workflow_id,
            "workflow_name": wf.get("name"),
            "contact_id": payload.contact_id,
            "reason": payload.reason,
            "status": "pending",
            "approved_by": [],
            "rejected_by": [],
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.approval_requests.append(request)
    append_audit(runtime, auth.tenant_id, "workflow_approval_requested", request["id"])
    return {"status": "ok", "approval_request": request}


def execute_decide_approval_request(
    runtime: WorkflowRuntime, request_id: int, payload: ApprovalDecisionRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:approval-request:decision", 120, 60)
    decision = payload.decision.strip().lower()
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail="decision must be approve or reject")
    with runtime.lock:
        req = next(
            (
                r
                for r in runtime.approval_requests
                if r.get("id") == request_id and r.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if req is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        if req.get("status") == "rejected":
            raise HTTPException(status_code=409, detail="Approval request already rejected.")
        if decision == "approve":
            approved_by = req.setdefault("approved_by", [])
            if payload.reviewer not in approved_by:
                approved_by.append(payload.reviewer)
            policy = get_policy(runtime, int(req.get("workflow_id", 0)), auth.tenant_id)
            required_approvals = int((policy or {}).get("required_approvals", 1))
            req["status"] = "approved" if count_approvals(req) >= required_approvals else "pending"
        else:
            rejected_by = req.setdefault("rejected_by", [])
            if payload.reviewer not in rejected_by:
                rejected_by.append(payload.reviewer)
            req["status"] = "rejected"
        req["last_note"] = payload.note
        req["updated_at"] = datetime.now(UTC).isoformat()
    append_audit(runtime, auth.tenant_id, "workflow_approval_decided", request_id)
    return {"status": "ok", "approval_request": req}


def execute_list_approval_requests(
    runtime: WorkflowRuntime, auth: AuthDep, limit: Annotated[int, Query(ge=1, le=200)] = 50
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:approval-request:list", 120, 60)
    with runtime.lock:
        requests = [r.copy() for r in runtime.approval_requests if r.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "approval_requests": requests[:limit], "total": len(requests)}


def execute_create_connector_template(
    runtime: WorkflowRuntime, payload: WorkflowConnectorTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:templates:create", 40, 60)
    with runtime.lock:
        template = {
            "id": len(runtime.connector_policy_templates) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name,
            "description": payload.description,
            "policy": {
                "max_retries": payload.max_retries,
                "base_backoff_ms": payload.base_backoff_ms,
                "circuit_failure_threshold": payload.circuit_failure_threshold,
                "circuit_cooldown_seconds": payload.circuit_cooldown_seconds,
                "slo_availability_target_pct": payload.slo_availability_target_pct,
                "slo_latency_p95_target_ms": payload.slo_latency_p95_target_ms,
                "replay_enabled": payload.replay_enabled,
            },
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.connector_policy_templates.append(template)
    append_audit(runtime, auth.tenant_id, "workflow_connector_template_created", _coerce_int(template.get("id")))
    return {"status": "ok", "template": template}


def execute_list_connector_templates(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:templates:list", 120, 60)
    with runtime.lock:
        templates = [t.copy() for t in runtime.connector_policy_templates if t.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "templates": templates, "total": len(templates)}


def execute_apply_connector_template(
    runtime: WorkflowRuntime, template_id: int, payload: WorkflowConnectorTemplateApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:templates:apply", 60, 60)
    with runtime.lock:
        template = next(
            (
                t
                for t in runtime.connector_policy_templates
                if int(t.get("id", 0)) == template_id and t.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if template is None:
            raise HTTPException(status_code=404, detail="Connector template not found.")
        target_ids = payload.connector_ids
        connectors = [c for c in runtime.connectors if c.get("tenant_id") == auth.tenant_id]
        if target_ids:
            connectors = [c for c in connectors if int(c.get("id", 0)) in target_ids]
        updated: list[int] = []
        for connector in connectors:
            ensure_reliability_fields(connector)
            connector["reliability_policy"] = dict(template.get("policy", {}))
            connector["circuit_breaker"]["cooldown_seconds"] = int(
                connector["reliability_policy"].get("circuit_cooldown_seconds", 120)
            )
            connector["updated_at"] = datetime.now(UTC).isoformat()
            updated.append(int(connector.get("id", 0)))
    append_audit(runtime, auth.tenant_id, "workflow_connector_template_applied", template_id)
    return {"status": "ok", "template_id": template_id, "updated_connector_ids": updated, "count": len(updated)}


def execute_create_maintenance_window(
    runtime: WorkflowRuntime, payload: WorkflowConnectorMaintenanceWindowRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:maintenance:create", 60, 60)
    with runtime.lock:
        window = {
            "id": len(runtime.connector_maintenance_windows) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name,
            "start_hour_utc": payload.start_hour_utc,
            "end_hour_utc": payload.end_hour_utc,
            "connector_ids": payload.connector_ids,
            "enabled": payload.enabled,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.connector_maintenance_windows.append(window)
    append_audit(
        runtime, auth.tenant_id, "workflow_connector_maintenance_window_created", _coerce_int(window.get("id"))
    )
    return {"status": "ok", "window": window}
