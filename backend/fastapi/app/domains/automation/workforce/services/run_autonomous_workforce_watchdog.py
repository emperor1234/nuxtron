"""Automation/Workforce service: run autonomous workforce watchdog."""

from __future__ import annotations
from .....workforce_persistence import WorkforceDB
from .mission_execution import _dispatch_provider_action
from .mission_execution import _generate_mission_artifact
from .mission_execution import _now_iso
from .mission_execution import _parse_iso_utc
from .mission_execution import _verify_provider_live_standalone
from ..capabilities import require_workforce_execution_available
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
import asyncio
import os
import uuid


async def run_autonomous_workforce_watchdog(
    stop_event: asyncio.Event,
    *,
    schedules_memory: list[dict[str, Any]],
    integrations_memory: list[dict[str, Any]],
    missions_memory: list[dict[str, Any]],
    feed_memory: list[dict[str, Any]],
    outcomes_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
    db_dsn: str = "",
    poll_interval_seconds: int = 30,
    max_due_per_tick: int = 20,
) -> None:
    """Continuously executes due autonomous schedules until shutdown."""
    require_workforce_execution_available()
    loop_sleep = max(5, int(poll_interval_seconds))
    use_celery = str(os.getenv("WORKFORCE_USE_CELERY", "false")).lower() == "true"
    db = WorkforceDB(db_dsn) if db_dsn.startswith("postgresql") else None

    async def _db_safe(coro: Any) -> Any:
        if db is None:
            return None
        try:
            return await coro
        except Exception:
            return None

    while not stop_event.is_set():
        now = datetime.now(UTC)
        due: list[dict[str, Any]] = []
        due_db = await _db_safe(db.get_schedule_due(limit=max_due_per_tick)) if db else None
        if isinstance(due_db, list) and due_db:
            due = [d for d in due_db if isinstance(d, dict)]
        else:
            for sched in schedules_memory:
                if not bool(sched.get("enabled", True)):
                    continue
                next_run = _parse_iso_utc(str(sched.get("next_run_at") or ""))
                if next_run is None:
                    continue
                if next_run <= now:
                    due.append(sched)
                if len(due) >= max_due_per_tick:
                    break
        for sched in due:
            tenant_id = str(sched.get("tenant_id", "")).strip()
            if not tenant_id:
                continue
            mission = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "title": str(sched.get("title", "Scheduled mission")),
                "description": f"Scheduled mission from schedule {sched.get('id', 'unknown')}",
                "role": str(sched.get("role", "growth_metrics")),
                "objective": str(sched.get("objective", "")),
                "providers": list(sched.get("providers", [])) if isinstance(sched.get("providers", []), list) else [],
                "requires_approval": False,
                "status": "running",
                "input_context": {"schedule_id": sched.get("id")},
                "created_at": _now_iso(),
                "updated_at": _now_iso(),
                "approved_at": _now_iso(),
                "executed_at": None,
            }
            missions_memory.append(mission)
            mission_providers = mission.get("providers", [])
            if not isinstance(mission_providers, list):
                mission_providers = []
            persisted_mission = (
                await _db_safe(
                    db.create_mission(
                        tenant_id,
                        str(mission.get("title", "Scheduled mission")),
                        str(mission.get("description", "")),
                        str(mission.get("role", "growth_metrics")),
                        str(mission.get("objective", "")),
                        False,
                        mission_providers,
                        mission.get("input_context", {}),
                    )
                )
                if db
                else None
            )
            if isinstance(persisted_mission, dict) and persisted_mission:
                mission.update(persisted_mission)
            if use_celery:
                from .....tasks.workforce_tasks import enqueue_execute_mission

                provider_connections = [
                    c.copy()
                    for c in integrations_memory
                    if c.get("tenant_id") == tenant_id
                    and c.get("provider") in mission.get("providers", [])
                    and (c.get("status") == "connected")
                ]
                task_id = enqueue_execute_mission(tenant_id, mission["id"], mission.copy(), provider_connections)
                queued_at = _now_iso()
                mission["status"] = "queued"
                mission["executed_at"] = queued_at
                mission["updated_at"] = queued_at
                outcomes_memory.append(
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": tenant_id,
                        "mission_id": mission["id"],
                        "status": "queued",
                        "success_count": 0,
                        "failed_count": 0,
                        "provider_results": [],
                        "artifact": {},
                        "queued_task_id": task_id,
                        "created_at": queued_at,
                        "source": "watchdog_celery",
                    }
                )
                feed_memory.append(
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": tenant_id,
                        "mission_id": mission["id"],
                        "type": "mission_queued",
                        "status": "queued",
                        "title": mission.get("title"),
                        "summary": f"scheduled task queued {task_id}",
                        "created_at": queued_at,
                    }
                )
                audit_log_memory.append(
                    {
                        "id": len(audit_log_memory) + 1,
                        "tenant_id": tenant_id,
                        "action": "workforce_schedule_queued",
                        "detail": str(sched.get("id", "")),
                        "source": "autonomous-workforce-watchdog",
                        "created_at": queued_at,
                    }
                )
                freq = int(sched.get("frequency_minutes") or 60)
                sched["last_run_at"] = queued_at
                sched["next_run_at"] = (datetime.now(UTC) + timedelta(minutes=max(5, freq))).isoformat()
                sched["updated_at"] = queued_at
                if db:
                    await _db_safe(
                        db.create_outcome(
                            tenant_id, str(mission.get("id", "")), "queued", 0, 0, [], {}, "watchdog_celery"
                        )
                    )
                    await _db_safe(
                        db.update_schedule_next_run(str(sched.get("id", "")), str(sched.get("next_run_at", "")))
                    )
                continue
            artifact_ok, artifact = await _generate_mission_artifact(tenant_id, mission)
            provider_results: list[dict[str, Any]] = []
            providers = [str(p).strip().lower() for p in mission.get("providers", []) if str(p).strip()]
            for provider in providers:
                conn = next(
                    (
                        c
                        for c in integrations_memory
                        if c.get("tenant_id") == tenant_id
                        and c.get("provider") == provider
                        and (c.get("status") == "connected")
                    ),
                    None,
                )
                if conn is None:
                    provider_results.append({"provider": provider, "ok": False, "error": "provider-not-connected"})
                    continue
                token = str(conn.get("last_verified_token", "")).strip()
                if not token:
                    provider_results.append({"provider": provider, "ok": False, "error": "token-not-available"})
                    continue
                live_ok, status_code, payload = await _verify_provider_live_standalone(provider, token)
                if not live_ok:
                    provider_results.append(
                        {"provider": provider, "ok": False, "status_code": status_code, "response": payload}
                    )
                    continue
                if not artifact_ok:
                    provider_results.append(
                        {
                            "provider": provider,
                            "ok": False,
                            "status_code": status_code,
                            "response": payload,
                            "execution": {"error": "artifact-generation-failed", "detail": artifact},
                        }
                    )
                    continue
                dispatch_ok, dispatch_result = await _dispatch_provider_action(
                    provider, token, mission, str(artifact.get("generated", "")), conn
                )
                provider_results.append(
                    {
                        "provider": provider,
                        "ok": dispatch_ok,
                        "status_code": status_code,
                        "response": payload,
                        "execution": dispatch_result,
                    }
                )
            success_count = sum((1 for r in provider_results if r.get("ok")))
            failed_count = len(provider_results) - success_count
            if failed_count == 0:
                status = "completed"
            elif success_count == 0:
                status = "failed"
            else:
                status = "completed"
            mission["status"] = status
            mission["executed_at"] = _now_iso()
            mission["updated_at"] = _now_iso()
            outcomes_memory.append(
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "mission_id": mission["id"],
                    "status": status,
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "provider_results": provider_results,
                    "artifact": artifact,
                    "created_at": _now_iso(),
                    "source": "watchdog",
                }
            )
            feed_memory.append(
                {
                    "id": str(uuid.uuid4()),
                    "tenant_id": tenant_id,
                    "mission_id": mission["id"],
                    "type": "mission_result",
                    "status": status,
                    "title": mission.get("title"),
                    "summary": f"scheduled success={success_count} failed={failed_count}",
                    "created_at": _now_iso(),
                }
            )
            audit_log_memory.append(
                {
                    "id": len(audit_log_memory) + 1,
                    "tenant_id": tenant_id,
                    "action": "workforce_schedule_executed",
                    "detail": str(sched.get("id", "")),
                    "source": "autonomous-workforce-watchdog",
                    "created_at": _now_iso(),
                }
            )
            freq = int(sched.get("frequency_minutes") or 60)
            sched["last_run_at"] = _now_iso()
            sched["next_run_at"] = (datetime.now(UTC) + timedelta(minutes=max(5, freq))).isoformat()
            sched["updated_at"] = _now_iso()
            if db:
                await _db_safe(
                    db.create_outcome(
                        tenant_id,
                        str(mission.get("id", "")),
                        str(status),
                        int(success_count),
                        int(failed_count),
                        provider_results,
                        artifact if isinstance(artifact, dict) else {},
                        "watchdog",
                    )
                )
                await _db_safe(db.update_schedule_next_run(str(sched.get("id", "")), str(sched.get("next_run_at", ""))))
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=loop_sleep)
        except TimeoutError:
            continue
