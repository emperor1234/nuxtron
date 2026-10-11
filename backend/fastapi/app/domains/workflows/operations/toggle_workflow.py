"""Workflow use cases: toggle workflow."""

from ..constants import AuthDep
from ..constants import WORKFLOW_NOT_FOUND
from ..graph import count_approvals
from ..graph import is_high_risk
from ..repository import store_create_execution
from ..repository import store_get_workflow
from ..repository import store_increment_workflow_counts
from ..repository import store_list_executions
from ..repository import store_toggle_workflow
from ..runtime import WorkflowRuntime
from ..schemas import ManualEnrollRequest
from ..schemas import WorkflowApprovalPolicyRequest
from ..service import append_audit
from ..service import get_policy
from ..service import simulate_execution
from ..service import workflow_platform_readiness_payload
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_toggle_workflow(
    runtime: WorkflowRuntime, workflow_id: int, auth: AuthDep, active: Annotated[bool, Query()]
) -> dict[str, Any]:
    """NEW: Activate or pause a workflow."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:toggle", 60, 60)
    with runtime.lock:
        wf = next(
            (w for w in runtime.workflows if w.get("id") == workflow_id and w.get("tenant_id") == auth.tenant_id), None
        )
        if wf is not None:
            wf["status"] = "active" if active else "paused"
            wf["updated_at"] = datetime.now(UTC).isoformat()
    persisted = store_toggle_workflow(workflow_id, auth.tenant_id, active)
    if wf is None and persisted is None:
        raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
    if isinstance(persisted, dict) and persisted:
        wf = persisted
    append_audit(runtime, auth.tenant_id, f"workflow_{('activated' if active else 'paused')}", workflow_id)
    return {"status": "ok", "workflow": wf.copy() if isinstance(wf, dict) else wf}


def execute_enroll_contact(
    runtime: WorkflowRuntime, workflow_id: int, payload: ManualEnrollRequest, auth: AuthDep
) -> dict[str, Any]:
    """NEW: Manually enroll a contact into a workflow."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:enroll", 120, 60)
    with runtime.lock:
        wf = next(
            (w for w in runtime.workflows if w.get("id") == workflow_id and w.get("tenant_id") == auth.tenant_id), None
        )
    if wf is None:
        persisted = store_get_workflow(workflow_id, auth.tenant_id)
        if isinstance(persisted, dict) and persisted:
            wf = persisted
    if wf is None:
        raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
    if wf.get("status") != "active":
        raise HTTPException(status_code=409, detail="Workflow is not active.")
    policy = get_policy(runtime, workflow_id, auth.tenant_id)
    if policy is not None:
        high_risk_workflow = is_high_risk(wf)
        enforce_for_high_risk_only = bool(policy.get("enforce_for_high_risk_only", True))
        should_enforce = high_risk_workflow if enforce_for_high_risk_only else True
        if should_enforce:
            with runtime.lock:
                matching_requests = [
                    r
                    for r in runtime.approval_requests
                    if r.get("tenant_id") == auth.tenant_id
                    and r.get("workflow_id") == workflow_id
                    and (r.get("contact_id") == payload.contact_id)
                ]
            approved = any(
                (
                    r.get("status") == "approved" and count_approvals(r) >= int(policy.get("required_approvals", 1))
                    for r in matching_requests
                )
            )
            if not approved:
                raise HTTPException(
                    status_code=409, detail="Approval required before enrollment for this workflow/contact."
                )
    result = simulate_execution(runtime, wf, payload.contact_id, payload.contact_email, auth.tenant_id)
    with runtime.lock:
        execution = {
            "id": len(runtime.workflow_executions) + 1,
            "tenant_id": auth.tenant_id,
            "workflow_id": workflow_id,
            "workflow_name": wf.get("name", ""),
            "contact_id": payload.contact_id,
            "contact_email": payload.contact_email,
            "status": "completed",
            "steps_executed": result["steps_executed"],
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        }
        runtime.workflow_executions.append(execution)
        wf["enrollment_count"] = wf.get("enrollment_count", 0) + 1
        wf["execution_count"] = wf.get("execution_count", 0) + 1
    persisted_execution = store_create_execution(
        tenant_id=auth.tenant_id,
        workflow_id=workflow_id,
        workflow_name=str(wf.get("name", "")),
        contact_id=payload.contact_id,
        contact_email=payload.contact_email,
        trigger_source="manual_enroll",
        trigger_event_type=str(wf.get("trigger", {}).get("trigger_type", "manual")),
        step_logs=result["step_logs"],
    )
    store_increment_workflow_counts(workflow_id, auth.tenant_id, enroll_delta=1, execution_delta=1)
    if isinstance(persisted_execution, dict) and persisted_execution:
        execution = persisted_execution
    append_audit(runtime, auth.tenant_id, "workflow_contact_enrolled", execution["id"])
    return {"status": "ok", "execution": execution}


def execute_list_executions(
    runtime: WorkflowRuntime,
    workflow_id: int,
    auth: AuthDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """NEW: List workflow execution history."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:executions", 60, 60)
    with runtime.lock:
        wf = next(
            (w for w in runtime.workflows if w.get("id") == workflow_id and w.get("tenant_id") == auth.tenant_id), None
        )
        execs = [e.copy() for e in runtime.workflow_executions if e.get("workflow_id") == workflow_id]
    if wf is None:
        wf = store_get_workflow(workflow_id, auth.tenant_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
    persisted_execs = store_list_executions(auth.tenant_id, workflow_id)
    if isinstance(persisted_execs, list) and persisted_execs:
        execs = persisted_execs
    return {"status": "ok", "executions": execs[offset : offset + limit], "total": len(execs)}


def execute_workflow_analytics(runtime: WorkflowRuntime, workflow_id: int, auth: AuthDep) -> dict[str, Any]:
    """NEW: Workflow performance analytics."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:analytics", 60, 60)
    with runtime.lock:
        wf = next(
            (
                w.copy()
                for w in runtime.workflows
                if w.get("id") == workflow_id and w.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        execs = [e for e in runtime.workflow_executions if e.get("workflow_id") == workflow_id]
    if wf is None:
        wf = store_get_workflow(workflow_id, auth.tenant_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
    persisted_execs = store_list_executions(auth.tenant_id, workflow_id)
    if isinstance(persisted_execs, list) and persisted_execs:
        execs = persisted_execs
    completed = sum((1 for e in execs if e.get("status") == "completed"))
    failed = sum((1 for e in execs if e.get("status") == "failed"))
    step_counts = [int(e.get("steps_executed", 0)) for e in execs]
    return {
        "status": "ok",
        "workflow_id": workflow_id,
        "workflow_name": wf.get("name", ""),
        "total_enrollments": len(execs),
        "completed": completed,
        "failed": failed,
        "completion_rate": round(completed / len(execs) * 100, 1) if execs else 0,
        "avg_steps_executed": round(sum(step_counts) / len(step_counts), 1) if step_counts else 0,
    }


def execute_workflow_production_readiness(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:production-readiness", 120, 60)
    return workflow_platform_readiness_payload(runtime, auth.tenant_id)


def execute_workflow_platform_completion_chart(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:completion-chart", 120, 60)
    payload = workflow_platform_readiness_payload(runtime, auth.tenant_id)
    matrix = payload.get("matrix", [])
    implemented_count = int(payload.get("implemented_count", 0))
    total_count = int(payload.get("total_count", 0))
    completion_pct = float(payload.get("completion_pct", 0.0))
    return {
        "status": "ok",
        "as_of": datetime.now(UTC).isoformat(),
        "completion_pct": completion_pct,
        "implemented_count": implemented_count,
        "total_count": total_count,
        "chart": {
            "summary": {
                "done": implemented_count,
                "remaining": max(0, total_count - implemented_count),
                "percent": completion_pct,
            },
            "features": matrix,
        },
        "tenant_stats": payload.get("tenant_stats", {}),
        "vendors": payload.get("vendors", []),
    }


def execute_delete_workflow(runtime: WorkflowRuntime, workflow_id: int, auth: AuthDep) -> dict[str, Any]:
    """NEW: Delete a workflow."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:delete", 30, 60)
    with runtime.lock:
        idx = next(
            (
                i
                for i, w in enumerate(runtime.workflows)
                if w.get("id") == workflow_id and w.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if idx is None:
            raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
        removed = runtime.workflows.pop(idx)
    append_audit(runtime, auth.tenant_id, "workflow_deleted", workflow_id)
    return {"status": "ok", "deleted": True, "workflow": removed}


def execute_upsert_workflow_approval_policy(
    runtime: WorkflowRuntime, payload: WorkflowApprovalPolicyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:approval-policy:upsert", 40, 60)
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
        existing = next(
            (
                p
                for p in runtime.approval_policies
                if p.get("workflow_id") == payload.workflow_id and p.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        now = datetime.now(UTC).isoformat()
        if existing is None:
            policy = {
                "id": len(runtime.approval_policies) + 1,
                "tenant_id": auth.tenant_id,
                "workflow_id": payload.workflow_id,
                "enabled": payload.enabled,
                "required_approvals": payload.required_approvals,
                "approver_roles": payload.approver_roles,
                "enforce_for_high_risk_only": payload.enforce_for_high_risk_only,
                "created_at": now,
                "updated_at": now,
            }
            runtime.approval_policies.append(policy)
        else:
            existing["enabled"] = payload.enabled
            existing["required_approvals"] = payload.required_approvals
            existing["approver_roles"] = payload.approver_roles
            existing["enforce_for_high_risk_only"] = payload.enforce_for_high_risk_only
            existing["updated_at"] = now
            policy = existing
    append_audit(runtime, auth.tenant_id, "workflow_approval_policy_upserted", payload.workflow_id)
    return {"status": "ok", "policy": policy}
