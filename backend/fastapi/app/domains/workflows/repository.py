"""Workflow repository implementation with explicit dependencies."""

import os
from fastapi import HTTPException
from ...database import get_db_session
from ...models import WorkflowExecution
from ...models import WorkflowRule
from .schemas import WorkflowCreateRequest
from datetime import UTC
from datetime import datetime
from typing import Any


def persistence_enabled() -> bool:
    raw = os.getenv("WORKFLOWS_DB_PERSISTENCE", "true").strip().lower()
    enabled = raw not in {"0", "false", "no", "off"}
    if not enabled and os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(status_code=503, detail="Workflow persistence is required.")
    return enabled


def workflow_rule_to_payload(obj: WorkflowRule) -> dict[str, Any]:
    data = dict(obj.data or {})
    actions = dict(obj.actions or {})
    steps = actions.get("steps") if isinstance(actions.get("steps"), list) else []
    return {
        "id": int(obj.id),
        "tenant_id": obj.tenant_id,
        "name": obj.name,
        "description": str(data.get("description", "")),
        "trigger": {
            "trigger_type": obj.trigger,
            "conditions": obj.conditions if isinstance(obj.conditions, list) else [],
        },
        "steps": steps,
        "step_count": int(data.get("step_count", len(steps))),
        "re_enrollment": bool(data.get("re_enrollment", False)),
        "re_enrollment_days": int(data.get("re_enrollment_days", 0)),
        "status": "active" if bool(obj.enabled) else "paused",
        "enrollment_count": int(data.get("enrollment_count", 0)),
        "execution_count": int(data.get("execution_count", 0)),
        "created_at": obj.created_at.isoformat(),
        "updated_at": obj.updated_at.isoformat(),
    }


def store_get_workflow(workflow_id: int, tenant_id: str) -> dict[str, Any] | None:
    if not persistence_enabled():
        return None
    try:
        with get_db_session() as session:
            obj = (
                session.query(WorkflowRule)
                .filter(WorkflowRule.id == workflow_id, WorkflowRule.tenant_id == tenant_id)
                .first()
            )
            if obj is None:
                return None
            return workflow_rule_to_payload(obj)
    except Exception as exc:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="Workflow persistence unavailable.") from exc
        return None


def store_create_workflow(
    tenant_id: str, payload: WorkflowCreateRequest, steps: list[dict[str, Any]], trigger_type: str
) -> dict[str, Any] | None:
    if not persistence_enabled():
        return None
    try:
        with get_db_session() as session:
            obj = WorkflowRule(
                tenant_id=tenant_id,
                name=payload.name,
                enabled=True,
                trigger=trigger_type,
                conditions=payload.trigger.conditions,
                actions={"steps": steps},
                data={
                    "description": payload.description,
                    "step_count": len(steps),
                    "re_enrollment": payload.re_enrollment,
                    "re_enrollment_days": payload.re_enrollment_days,
                    "enrollment_count": 0,
                    "execution_count": 0,
                },
            )
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return workflow_rule_to_payload(obj)
    except Exception as exc:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="Workflow persistence unavailable.") from exc
        return None


def store_list_workflows(tenant_id: str) -> list[dict[str, Any]] | None:
    if not persistence_enabled():
        return None
    try:
        with get_db_session() as session:
            rows = (
                session.query(WorkflowRule)
                .filter(WorkflowRule.tenant_id == tenant_id)
                .order_by(WorkflowRule.created_at.desc())
                .all()
            )
            return [workflow_rule_to_payload(row) for row in rows]
    except Exception as exc:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="Workflow persistence unavailable.") from exc
        return None


def store_toggle_workflow(workflow_id: int, tenant_id: str, active: bool) -> dict[str, Any] | None:
    if not persistence_enabled():
        return None
    try:
        with get_db_session() as session:
            obj = (
                session.query(WorkflowRule)
                .filter(WorkflowRule.id == workflow_id, WorkflowRule.tenant_id == tenant_id)
                .first()
            )
            if obj is None:
                return None
            obj.enabled = bool(active)
            session.commit()
            session.refresh(obj)
            return workflow_rule_to_payload(obj)
    except Exception as exc:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="Workflow persistence unavailable.") from exc
        return None


def store_increment_workflow_counts(
    workflow_id: int, tenant_id: str, *, enroll_delta: int = 0, execution_delta: int = 0
) -> None:
    if not persistence_enabled():
        return
    try:
        with get_db_session() as session:
            obj = (
                session.query(WorkflowRule)
                .filter(WorkflowRule.id == workflow_id, WorkflowRule.tenant_id == tenant_id)
                .first()
            )
            if obj is None:
                return
            data = dict(obj.data or {})
            data["enrollment_count"] = int(data.get("enrollment_count", 0)) + int(enroll_delta)
            data["execution_count"] = int(data.get("execution_count", 0)) + int(execution_delta)
            obj.data = data
            session.commit()
    except Exception as exc:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="Workflow persistence unavailable.") from exc
        return


def execution_model_to_payload(obj: WorkflowExecution, workflow_name: str = "") -> dict[str, Any]:
    data = dict(obj.data or {})
    return {
        "id": int(obj.id),
        "tenant_id": obj.tenant_id,
        "workflow_id": int(obj.workflow_id or 0),
        "workflow_name": str(data.get("workflow_name", workflow_name)),
        "contact_id": str(data.get("contact_id", "")),
        "contact_email": str(data.get("contact_email", "")),
        "status": obj.status,
        "steps_executed": len(obj.steps_executed or []),
        "started_at": obj.started_at.isoformat(),
        "completed_at": obj.completed_at.isoformat() if obj.completed_at else None,
        "trigger_source": str(data.get("trigger_source", "manual")),
        "trigger_event_type": obj.trigger_type,
    }


def store_create_execution(
    *,
    tenant_id: str,
    workflow_id: int,
    workflow_name: str,
    contact_id: str,
    contact_email: str,
    trigger_source: str,
    trigger_event_type: str,
    step_logs: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not persistence_enabled():
        return None
    now = datetime.now(UTC)
    try:
        with get_db_session() as session:
            obj = WorkflowExecution(
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                trigger_type=trigger_event_type,
                trigger_entity_id=None,
                status="completed",
                started_at=now,
                completed_at=now,
                steps_executed=step_logs,
                current_step_id=str(step_logs[-1].get("step_id", "")) if step_logs else None,
                result={"steps_executed": len(step_logs)},
                error_message=None,
                data={
                    "workflow_name": workflow_name,
                    "contact_id": contact_id,
                    "contact_email": contact_email,
                    "trigger_source": trigger_source,
                },
            )
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return execution_model_to_payload(obj, workflow_name)
    except Exception as exc:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="Workflow persistence unavailable.") from exc
        return None


def store_list_executions(tenant_id: str, workflow_id: int) -> list[dict[str, Any]] | None:
    if not persistence_enabled():
        return None
    try:
        with get_db_session() as session:
            rows = (
                session.query(WorkflowExecution)
                .filter(WorkflowExecution.tenant_id == tenant_id, WorkflowExecution.workflow_id == workflow_id)
                .order_by(WorkflowExecution.started_at.desc())
                .all()
            )
            return [execution_model_to_payload(row) for row in rows]
    except Exception as exc:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="Workflow persistence unavailable.") from exc
        return None
