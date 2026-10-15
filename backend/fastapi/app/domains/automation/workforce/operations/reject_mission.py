"""Automation/Workforce use cases: reject mission."""

from __future__ import annotations
from ..constants import AuthDep
from ..capabilities import require_workforce_execution_available
from ..runtime import ContextRuntime
from ..schemas import KnowledgeDocRequest
from ..schemas import MissionDecisionRequest
from ..schemas import ScheduleRequest
from ..schemas import WebhookTriggerRequest
from .now_iso import helper_audit
from .now_iso import helper_db_enabled
from .now_iso import helper_execute_mission
from .now_iso import helper_get_mission_memory
from .now_iso import helper_now_iso
from .now_iso import helper_persisted_mission_as_memory
from .now_iso import helper_queue_mission_execution
from .now_iso import helper_run_db
from .now_iso import helper_use_celery
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from typing import Annotated
from typing import Any
import uuid


def execute_reject_mission(
    runtime: ContextRuntime, mission_id: str, payload: MissionDecisionRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:missions:reject", 60, 60)
    mission = helper_get_mission_memory(runtime, auth.tenant_id, mission_id)
    if mission is None and helper_db_enabled(runtime):
        mission = helper_persisted_mission_as_memory(runtime, auth.tenant_id, mission_id)
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found.")
    mission["status"] = "rejected"
    mission["updated_at"] = helper_now_iso()
    if helper_db_enabled(runtime):
        helper_run_db(runtime, runtime._db.update_mission_status(auth.tenant_id, mission_id, "rejected"))
    with runtime._lock:
        runtime.feed_memory.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": auth.tenant_id,
                "mission_id": mission_id,
                "type": "mission_rejected",
                "status": "rejected",
                "title": mission.get("title"),
                "summary": payload.note or "Rejected",
                "created_at": helper_now_iso(),
            }
        )
    helper_audit(runtime, auth.tenant_id, "workforce_mission_rejected", mission_id)
    return {"status": "ok", "mission": mission}


def execute_create_schedule(runtime: ContextRuntime, payload: ScheduleRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:schedules:create", 60, 60)
    now = datetime.now(UTC)
    schedule = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "mission_template_id": payload.mission_template_id,
        "role": payload.role,
        "title": payload.title,
        "objective": payload.objective,
        "providers": [p.strip().lower() for p in payload.providers if p.strip()],
        "frequency_minutes": payload.frequency_minutes,
        "enabled": payload.enabled,
        "next_run_at": (now + timedelta(minutes=payload.frequency_minutes)).isoformat(),
        "last_run_at": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    with runtime._lock:
        runtime.schedules_memory.append(schedule)
    persisted = (
        helper_run_db(
            runtime,
            runtime._db.create_schedule(
                auth.tenant_id,
                payload.role,
                payload.title,
                payload.objective,
                payload.frequency_minutes,
                schedule.get("providers", []),
                payload.enabled,
                payload.mission_template_id,
            ),
        )
        if helper_db_enabled(runtime)
        else None
    )
    if isinstance(persisted, dict) and persisted:
        schedule = persisted
    helper_audit(runtime, auth.tenant_id, "workforce_schedule_created", payload.title)
    return {"status": "ok", "schedule": schedule}


async def execute_run_due_schedules(
    runtime: ContextRuntime, auth: AuthDep, limit: Annotated[int, Query(ge=1, le=200)] = 20
) -> dict[str, Any]:
    require_workforce_execution_available()
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:runner:tick", 30, 60)
    now = datetime.now(UTC)
    due: list[dict[str, Any]] = []
    if helper_db_enabled(runtime):
        persisted_due = helper_run_db(runtime, runtime._db.get_schedule_due(limit=limit * 5))
        if isinstance(persisted_due, list) and persisted_due:
            due = [s for s in persisted_due if isinstance(s, dict) and s.get("tenant_id") == auth.tenant_id][:limit]
    if not due:
        with runtime._lock:
            due = [
                s
                for s in runtime.schedules_memory
                if s.get("tenant_id") == auth.tenant_id
                and bool(s.get("enabled", True))
                and (datetime.fromisoformat(str(s.get("next_run_at"))) <= now)
            ][:limit]
    created_ids: list[str] = []
    queued_task_ids: list[str] = []
    for sched in due:
        mission = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "title": sched["title"],
            "description": f"Scheduled mission from schedule {sched['id']}",
            "role": sched["role"],
            "objective": sched["objective"],
            "providers": sched.get("providers", []),
            "requires_approval": False,
            "status": "running",
            "input_context": {"schedule_id": sched["id"]},
            "created_at": helper_now_iso(),
            "updated_at": helper_now_iso(),
            "approved_at": helper_now_iso(),
            "executed_at": None,
        }
        with runtime._lock:
            runtime.missions_memory.append(mission)
        if helper_db_enabled(runtime):
            persisted_mission = helper_run_db(
                runtime,
                runtime._db.create_mission(
                    auth.tenant_id,
                    str(mission.get("title", "")),
                    str(mission.get("description", "")),
                    str(mission.get("role", "growth_metrics")),
                    str(mission.get("objective", "")),
                    False,
                    list(mission.get("providers", [])),
                    mission.get("input_context", {}),
                ),
            )
            if isinstance(persisted_mission, dict) and persisted_mission:
                mission.update(persisted_mission)
        if helper_use_celery():
            outcome = helper_queue_mission_execution(runtime, auth.tenant_id, mission, "runner_tick_celery")
            queued_task_ids.append(str(outcome.get("queued_task_id", "")))
            if helper_db_enabled(runtime):
                helper_run_db(
                    runtime,
                    runtime._db.create_outcome(
                        auth.tenant_id, str(mission.get("id", "")), "queued", 0, 0, [], {}, "runner_tick_celery"
                    ),
                )
        else:
            outcome = await helper_execute_mission(runtime, auth.tenant_id, mission)
            if helper_db_enabled(runtime):
                helper_run_db(
                    runtime,
                    runtime._db.create_outcome(
                        auth.tenant_id,
                        str(mission.get("id", "")),
                        str(outcome.get("status", "failed")),
                        int(outcome.get("success_count", 0)),
                        int(outcome.get("failed_count", 0)),
                        outcome.get("provider_results", []),
                        outcome.get("artifact", {}),
                        "runner_tick",
                    ),
                )
        with runtime._lock:
            sched["last_run_at"] = helper_now_iso()
            sched["next_run_at"] = (datetime.now(UTC) + timedelta(minutes=int(sched["frequency_minutes"]))).isoformat()
            sched["updated_at"] = helper_now_iso()
        if helper_db_enabled(runtime):
            helper_run_db(
                runtime,
                runtime._db.update_schedule_next_run(str(sched.get("id", "")), str(sched.get("next_run_at", ""))),
            )
        created_ids.append(mission["id"])
    response = {"status": "ok", "executed": 0 if helper_use_celery() else len(created_ids), "mission_ids": created_ids}
    if queued_task_ids:
        response["queued"] = len(queued_task_ids)
        response["task_ids"] = queued_task_ids
    return response


def execute_add_knowledge(runtime: ContextRuntime, payload: KnowledgeDocRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:knowledge:add", 120, 60)
    doc = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "title": payload.title,
        "body": payload.body,
        "source": payload.source,
        "tags": payload.tags,
        "created_at": helper_now_iso(),
    }
    with runtime._lock:
        runtime.knowledge_memory.append(doc)
    persisted = (
        helper_run_db(
            runtime,
            runtime._db.add_knowledge(auth.tenant_id, payload.title, payload.body, payload.source, payload.tags),
        )
        if helper_db_enabled(runtime)
        else None
    )
    if isinstance(persisted, dict) and persisted:
        doc = persisted
    helper_audit(runtime, auth.tenant_id, "workforce_knowledge_added", payload.title)
    return {"status": "ok", "document": doc}


def execute_list_knowledge(
    runtime: ContextRuntime,
    auth: AuthDep,
    q: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:knowledge:list", 180, 60)
    with runtime._lock:
        rows = [d.copy() for d in runtime.knowledge_memory if d.get("tenant_id") == auth.tenant_id]
    if helper_db_enabled(runtime):
        persisted = helper_run_db(runtime, runtime._db.list_knowledge(auth.tenant_id, limit=limit))
        if isinstance(persisted, list) and persisted:
            rows = persisted
    if q:
        needle = q.lower().strip()
        rows = [
            d
            for d in rows
            if needle in str(d.get("title", "")).lower()
            or needle in str(d.get("body", "")).lower()
            or any((needle in str(tag).lower() for tag in d.get("tags", [])))
        ]
    return {"status": "ok", "documents": rows[-limit:], "total": len(rows)}


def execute_list_outcomes(
    runtime: ContextRuntime, auth: AuthDep, limit: Annotated[int, Query(ge=1, le=1000)] = 100
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:outcomes:list", 120, 60)
    with runtime._lock:
        rows = [o.copy() for o in runtime.outcomes_memory if o.get("tenant_id") == auth.tenant_id]
    if helper_db_enabled(runtime):
        persisted = helper_run_db(runtime, runtime._db.list_outcomes(auth.tenant_id, limit=limit))
        if isinstance(persisted, list) and persisted:
            rows = persisted
    return {"status": "ok", "outcomes": rows[-limit:], "total": len(rows)}


async def execute_webhook_trigger(
    runtime: ContextRuntime, payload: WebhookTriggerRequest, auth: AuthDep, request: Request
) -> dict[str, Any]:
    """Trigger mission creation from external webhook event."""
    require_workforce_execution_available()
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:webhook:trigger", 120, 60)
    mission_id = str(uuid.uuid4())
    now = helper_now_iso()
    mission = {
        "id": mission_id,
        "tenant_id": auth.tenant_id,
        "title": f"Webhook: {payload.trigger_source}",
        "description": f"Triggered from {payload.trigger_source} with objective: {payload.objective}",
        "role": payload.role,
        "objective": payload.objective,
        "status": "pending_approval" if payload.requires_approval else "approved",
        "requires_approval": payload.requires_approval,
        "providers": payload.providers,
        "input_context": {"webhook_source": payload.trigger_source, "event_data": payload.event_data},
        "created_at": now,
        "updated_at": now,
        "approved_at": now if not payload.requires_approval else None,
    }
    with runtime._lock:
        runtime.missions_memory.append(mission)
        runtime.feed_memory.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": auth.tenant_id,
                "mission_id": mission_id,
                "type": "webhook_triggered",
                "status": mission["status"],
                "title": mission["title"],
                "summary": f"from {payload.trigger_source}",
                "created_at": now,
            }
        )
    if helper_db_enabled(runtime):
        persisted_mission = helper_run_db(
            runtime,
            runtime._db.create_mission(
                auth.tenant_id,
                str(mission.get("title", "")),
                str(mission.get("description", "")),
                str(mission.get("role", "growth_metrics")),
                str(mission.get("objective", "")),
                bool(mission.get("requires_approval", True)),
                list(mission.get("providers", [])),
                mission.get("input_context", {}),
            ),
        )
        if isinstance(persisted_mission, dict) and persisted_mission:
            mission.update(persisted_mission)
            mission_id = str(mission.get("id", mission_id))
    helper_audit(runtime, auth.tenant_id, "workforce_webhook_triggered", str(payload.trigger_source))
    if not payload.requires_approval:
        if helper_use_celery():
            outcome = helper_queue_mission_execution(runtime, auth.tenant_id, mission, "webhook_celery")
            if helper_db_enabled(runtime):
                helper_run_db(
                    runtime,
                    runtime._db.create_outcome(
                        auth.tenant_id, str(mission.get("id", mission_id)), "queued", 0, 0, [], {}, "webhook_celery"
                    ),
                )
            return {
                "status": "accepted",
                "mission_id": mission_id,
                "executed": False,
                "queued": True,
                "task_id": outcome.get("queued_task_id"),
            }
        outcome = await helper_execute_mission(runtime, auth.tenant_id, mission)
        if helper_db_enabled(runtime):
            helper_run_db(
                runtime,
                runtime._db.create_outcome(
                    auth.tenant_id,
                    str(mission.get("id", mission_id)),
                    str(outcome.get("status", "failed")),
                    int(outcome.get("success_count", 0)),
                    int(outcome.get("failed_count", 0)),
                    outcome.get("provider_results", []),
                    outcome.get("artifact", {}),
                    "webhook",
                ),
            )
        return {"status": "accepted", "mission_id": mission_id, "executed": True, "outcome": outcome}
    return {"status": "accepted", "mission_id": mission_id, "executed": False}


def execute_metrics_dashboard(
    runtime: ContextRuntime, auth: AuthDep, time_window_minutes: Annotated[int, Query(ge=5, le=1440)] = 60
) -> dict[str, Any]:
    """Get observability dashboard with performance metrics."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:metrics:dashboard", 120, 60)
    dashboard = runtime._metrics.get_dashboard(time_window_minutes)
    return {"status": "ok", "metrics": dashboard}


def execute_metrics_providers(
    runtime: ContextRuntime, auth: AuthDep, time_window_minutes: Annotated[int, Query(ge=5, le=1440)] = 60
) -> dict[str, Any]:
    """Get per-provider performance statistics."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:metrics:providers", 120, 60)
    provider_stats = runtime._metrics.get_all_provider_stats(time_window_minutes)
    return {"status": "ok", "providers": provider_stats, "count": len(provider_stats)}


def execute_list_retry_queue(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: Annotated[str, Query()] = "pending",
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> dict[str, Any]:
    """List items in the retry queue."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:retry-queue:list", 120, 60)
    with runtime._lock:
        rows = [
            r.copy() for r in runtime._retry_queue if r.get("tenant_id") == auth.tenant_id and r.get("status") == status
        ]
    return {"status": "ok", "items": rows[-limit:], "total": len(rows)}
