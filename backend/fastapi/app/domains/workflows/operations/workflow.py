"""Workflow use cases: workflow."""

from ..constants import AuthDep
from ..constants import TRIGGER_TYPES
from ..constants import WORKFLOW_NOT_FOUND
from ..graph import coerce_int as _coerce_int
from ..graph import normalized_steps
from ..graph import parse_iso
from ..graph import preview_graph_path
from ..graph import validate_steps
from ..repository import store_create_workflow
from ..repository import store_get_workflow
from ..repository import store_list_workflows
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowCreateRequest
from ..schemas import WorkflowGraphValidateRequest
from ..schemas import WorkflowTemplateCreateRequest
from ..schemas import WorkflowTemplateInstantiateRequest
from ..schemas import WorkflowWebhookTriggerRequest
from ..service import append_audit
from ..service import simulate_execution
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_create_workflow(runtime: WorkflowRuntime, payload: WorkflowCreateRequest, auth: AuthDep) -> dict[str, Any]:
    """NEW: Create a marketing automation workflow."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:create", 30, 60)
    trigger_type = payload.trigger.trigger_type.strip().lower()
    if trigger_type not in TRIGGER_TYPES:
        trigger_type = "manual"
    steps = normalized_steps(payload.steps)
    validation = validate_steps(steps)
    if validation["errors"]:
        raise HTTPException(
            status_code=422, detail={"errors": validation["errors"], "warnings": validation["warnings"]}
        )
    with runtime.lock:
        workflow = {
            "id": len(runtime.workflows) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name,
            "description": payload.description,
            "trigger": {"trigger_type": trigger_type, "conditions": payload.trigger.conditions},
            "steps": steps,
            "step_count": len(steps),
            "re_enrollment": payload.re_enrollment,
            "re_enrollment_days": payload.re_enrollment_days,
            "status": "active",
            "enrollment_count": 0,
            "execution_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.workflows.append(workflow)
    persisted = store_create_workflow(auth.tenant_id, payload, steps, trigger_type)
    if isinstance(persisted, dict) and persisted:
        workflow = persisted
        with runtime.lock:
            if not any(
                (
                    _coerce_int(w.get("id", 0)) == _coerce_int(workflow.get("id", 0))
                    and w.get("tenant_id") == auth.tenant_id
                    for w in runtime.workflows
                )
            ):
                runtime.workflows.append(workflow.copy())
    append_audit(runtime, auth.tenant_id, "workflow_created", workflow["id"])
    return {"status": "ok", "workflow": workflow}


def execute_validate_workflow_graph(
    runtime: WorkflowRuntime, payload: WorkflowGraphValidateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:validate-graph", 120, 60)
    steps = normalized_steps(payload.steps)
    validation = validate_steps(steps)
    path = preview_graph_path(steps, payload.start_step_id)
    return {
        "status": "ok",
        "valid": len(validation["errors"]) == 0,
        "errors": validation["errors"],
        "warnings": validation["warnings"],
        "path_preview": path,
        "step_count": len(steps),
    }


def execute_create_workflow_template(
    runtime: WorkflowRuntime, payload: WorkflowTemplateCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:templates:create", 40, 60)
    trigger_type = payload.trigger_type.strip().lower()
    if trigger_type not in TRIGGER_TYPES:
        trigger_type = "manual"
    steps = normalized_steps(payload.steps)
    validation = validate_steps(steps)
    if validation["errors"]:
        raise HTTPException(
            status_code=422, detail={"errors": validation["errors"], "warnings": validation["warnings"]}
        )
    with runtime.lock:
        template = {
            "id": len(runtime.workflow_templates) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name,
            "description": payload.description,
            "category": payload.category,
            "trigger_type": trigger_type,
            "steps": steps,
            "step_count": len(steps),
            "tags": payload.tags,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.workflow_templates.append(template)
    append_audit(runtime, auth.tenant_id, "workflow_template_created", _coerce_int(template.get("id")))
    return {"status": "ok", "template": template, "validation_warnings": validation["warnings"]}


def execute_list_workflow_templates(
    runtime: WorkflowRuntime, auth: AuthDep, category: Annotated[str | None, Query(max_length=60)] = None
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:templates:list", 120, 60)
    with runtime.lock:
        items = [t.copy() for t in runtime.workflow_templates if t.get("tenant_id") == auth.tenant_id]
    if category:
        items = [item for item in items if str(item.get("category", "")).strip().lower() == category.strip().lower()]
    items.sort(key=lambda item: parse_iso(item.get("created_at")), reverse=True)
    return {"status": "ok", "templates": items, "total": len(items)}


def execute_instantiate_workflow_template(
    runtime: WorkflowRuntime, template_id: int, payload: WorkflowTemplateInstantiateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:templates:instantiate", 60, 60)
    with runtime.lock:
        template = next(
            (
                t
                for t in runtime.workflow_templates
                if int(t.get("id", 0)) == template_id and t.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if template is None:
            raise HTTPException(status_code=404, detail="Workflow template not found.")
        workflow = {
            "id": len(runtime.workflows) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name,
            "description": payload.description or str(template.get("description", "")),
            "trigger": {
                "trigger_type": template.get("trigger_type", "manual"),
                "conditions": payload.trigger_conditions,
            },
            "steps": list(template.get("steps") or []),
            "step_count": int(template.get("step_count", 0)),
            "re_enrollment": payload.re_enrollment,
            "re_enrollment_days": payload.re_enrollment_days,
            "status": "active",
            "enrollment_count": 0,
            "execution_count": 0,
            "template_id": int(template.get("id", 0)),
            "template_name": template.get("name", ""),
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.workflows.append(workflow)
    append_audit(runtime, auth.tenant_id, "workflow_template_instantiated", int(workflow["id"]))
    return {"status": "ok", "workflow": workflow}


def execute_trigger_workflows_webhook(
    runtime: WorkflowRuntime, payload: WorkflowWebhookTriggerRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:webhook:trigger", 240, 60)
    event_type = payload.event_type.strip().lower()
    if event_type not in TRIGGER_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported webhook trigger type.")
    with runtime.lock:
        if payload.external_event_id:
            existing_event = next(
                (
                    event
                    for event in runtime.workflow_webhook_events
                    if event.get("tenant_id") == auth.tenant_id
                    and event.get("external_event_id") == payload.external_event_id
                ),
                None,
            )
            if existing_event is not None:
                return {
                    "status": "ok",
                    "duplicate": True,
                    "external_event_id": payload.external_event_id,
                    "execution_ids": existing_event.get("execution_ids", []),
                }
        candidates = [
            workflow
            for workflow in runtime.workflows
            if workflow.get("tenant_id") == auth.tenant_id
            and workflow.get("status") == "active"
            and (workflow.get("trigger", {}).get("trigger_type") == event_type)
        ]

    def _conditions_match(workflow: dict[str, Any]) -> bool:
        conditions = workflow.get("trigger", {}).get("conditions") or []
        for condition in conditions:
            field = str(condition.get("field", "")).strip()
            expected = condition.get("value")
            if not field:
                continue
            if payload.payload.get(field) != expected:
                return False
        return True

    matched = [workflow for workflow in candidates if _conditions_match(workflow)]
    execution_ids: list[int] = []
    executions: list[dict[str, Any]] = []
    contact_id = str(payload.payload.get("contact_id") or payload.payload.get("id") or "webhook-contact")
    contact_email = str(payload.payload.get("contact_email") or payload.payload.get("email") or "")
    with runtime.lock:
        for workflow in matched:
            result = simulate_execution(runtime, workflow, contact_id, contact_email, auth.tenant_id)
            execution = {
                "id": len(runtime.workflow_executions) + 1,
                "tenant_id": auth.tenant_id,
                "workflow_id": int(workflow.get("id", 0)),
                "workflow_name": workflow.get("name", ""),
                "contact_id": contact_id,
                "contact_email": contact_email,
                "status": "completed",
                "steps_executed": result["steps_executed"],
                "started_at": datetime.now(UTC).isoformat(),
                "completed_at": datetime.now(UTC).isoformat(),
                "trigger_source": "webhook",
                "trigger_event_type": event_type,
            }
            runtime.workflow_executions.append(execution)
            workflow["enrollment_count"] = int(workflow.get("enrollment_count", 0)) + 1
            workflow["execution_count"] = int(workflow.get("execution_count", 0)) + 1
            executions.append(execution)
            execution_ids.append(int(execution["id"]))
        runtime.workflow_webhook_events.append(
            {
                "id": len(runtime.workflow_webhook_events) + 1,
                "tenant_id": auth.tenant_id,
                "event_type": event_type,
                "external_event_id": payload.external_event_id,
                "payload": payload.payload,
                "matched_workflow_ids": [int(w.get("id", 0)) for w in matched],
                "execution_ids": execution_ids,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
    append_audit(runtime, auth.tenant_id, "workflow_webhook_trigger_processed", len(execution_ids))
    return {
        "status": "ok",
        "duplicate": False,
        "event_type": event_type,
        "matched_workflows": len(matched),
        "executed": len(executions),
        "execution_ids": execution_ids,
        "executions": executions,
    }


def execute_list_workflows(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    trigger_type: Annotated[str | None, Query(max_length=40)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    """NEW: List automation workflows."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:list", 120, 60)
    items = store_list_workflows(auth.tenant_id) or []
    if not items:
        with runtime.lock:
            items = [w.copy() for w in runtime.workflows if w.get("tenant_id") == auth.tenant_id]
    if trigger_type:
        items = [w for w in items if w.get("trigger", {}).get("trigger_type") == trigger_type]
    return {"status": "ok", "workflows": items[offset : offset + limit], "total": len(items)}


def execute_get_workflow(runtime: WorkflowRuntime, workflow_id: int, auth: AuthDep) -> dict[str, Any]:
    """NEW: Get a single workflow with all steps."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:get", 120, 60)
    with runtime.lock:
        wf = next(
            (
                w.copy()
                for w in runtime.workflows
                if w.get("id") == workflow_id and w.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
    if wf is None:
        wf = store_get_workflow(workflow_id, auth.tenant_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
    return {"status": "ok", "workflow": wf}
