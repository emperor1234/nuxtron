from __future__ import annotations

import asyncio
import os
from typing import Any

from ..celery_app import celery_app
from ..routers.autonomous_workforce import (
    _dispatch_provider_action,
    _generate_mission_artifact,
    _verify_provider_live_standalone,
)
from ..workforce_persistence import WorkforceDB


def _status_from_results(results: list[dict[str, Any]]) -> str:
    if not results:
        return "failed"
    success_count = sum(1 for item in results if bool(item.get("ok")))
    failed_count = len(results) - success_count
    if failed_count == 0:
        return "completed"
    if success_count == 0:
        return "failed"
    return "completed"


@celery_app.task(bind=True, name="workforce.execute_mission", max_retries=3)
def execute_workforce_mission_task(
    self,
    tenant_id: str,
    mission_id: str,
    mission: dict[str, Any],
    provider_connections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Execute an autonomous workforce mission in a Celery worker."""

    async def _run() -> dict[str, Any]:
        dsn_raw = str(os.getenv("WORKFORCE_DB_DSN", "") or os.getenv("DATABASE_URL", "")).strip()
        dsn = dsn_raw if dsn_raw.startswith("postgresql") else ""
        db = WorkforceDB(dsn) if dsn else None

        artifact_ok, artifact = await _generate_mission_artifact(tenant_id, mission)
        providers = [str(p).strip().lower() for p in mission.get("providers", []) if str(p).strip()]

        provider_results: list[dict[str, Any]] = []
        for provider in providers:
            conn = next((c for c in provider_connections if c.get("provider") == provider), None)
            if conn is None:
                provider_results.append({"provider": provider, "ok": False, "error": "provider-not-connected"})
                continue

            token = str(conn.get("last_verified_token", "") or "").strip()
            if not token:
                provider_results.append({"provider": provider, "ok": False, "error": "token-not-available"})
                continue

            live_ok, status_code, payload = await _verify_provider_live_standalone(provider, token)
            if not live_ok:
                provider_results.append(
                    {
                        "provider": provider,
                        "ok": False,
                        "status_code": status_code,
                        "response": payload,
                    }
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
                provider,
                token,
                mission,
                str(artifact.get("generated", "")),
                conn,
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

        status = _status_from_results(provider_results)
        success_count = sum(1 for item in provider_results if bool(item.get("ok")))
        failed_count = len(provider_results) - success_count

        if db is not None:
            await db.update_mission_status(tenant_id, mission_id, status)
            await db.create_outcome(
                tenant_id,
                mission_id,
                status,
                success_count,
                failed_count,
                provider_results,
                artifact,
                source="celery_worker",
            )
            await db.audit_log(
                tenant_id,
                action="workforce_mission_executed_celery",
                detail=mission_id,
                mission_id=mission_id,
            )

        return {
            "mission_id": mission_id,
            "status": status,
            "success_count": success_count,
            "failed_count": failed_count,
            "provider_results": provider_results,
            "artifact": artifact,
            "worker_task_id": str(self.request.id),
        }

    return asyncio.run(_run())


def enqueue_execute_mission(
    tenant_id: str,
    mission_id: str,
    mission: dict[str, Any],
    provider_connections: list[dict[str, Any]],
) -> str:
    """Queue mission execution in Celery and return task ID."""
    task = execute_workforce_mission_task.apply_async(
        kwargs={
            "tenant_id": tenant_id,
            "mission_id": mission_id,
            "mission": mission,
            "provider_connections": provider_connections,
        }
    )
    return str(task.id)
