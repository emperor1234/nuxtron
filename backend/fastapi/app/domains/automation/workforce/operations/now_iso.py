"""Automation/Workforce use cases: now iso."""

from __future__ import annotations
from .....provider_executors import get_executor
from ..constants import MissionStatus
from ..capabilities import require_workforce_execution_available
from ..constants import PROVIDER_CATALOG
from ..runtime import ContextRuntime
from ..services.mission_execution import _dispatch_provider_action
from ..services.mission_execution import _generate_mission_artifact
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
import asyncio
import httpx
import os
import time
import uuid


def helper_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def helper_db_enabled(runtime: ContextRuntime) -> bool:
    return runtime._db is not None


def helper_use_celery() -> bool:
    return str(os.getenv("WORKFORCE_USE_CELERY", "false")).lower() == "true"


def helper_get_mission_memory(runtime: ContextRuntime, tenant_id: str, mission_id: str) -> dict[str, Any] | None:
    with runtime._lock:
        return next(
            (m for m in runtime.missions_memory if m.get("id") == mission_id and m.get("tenant_id") == tenant_id), None
        )


def helper_run_db(runtime: ContextRuntime, coro: Any) -> Any:
    if not helper_db_enabled(runtime):
        return None
    try:
        return asyncio.run(coro)
    except RuntimeError:
        return None
    except Exception:
        return None


def helper_persisted_mission_as_memory(
    runtime: ContextRuntime, tenant_id: str, mission_id: str
) -> dict[str, Any] | None:
    persisted = (
        helper_run_db(runtime, runtime._db.get_mission(tenant_id, mission_id)) if helper_db_enabled(runtime) else None
    )
    if not isinstance(persisted, dict) or not persisted:
        return None
    normalized = persisted.copy()
    for key in ("created_at", "updated_at", "approved_at", "executed_at"):
        value = normalized.get(key)
        if isinstance(value, datetime):
            normalized[key] = value.isoformat()
    with runtime._lock:
        runtime.missions_memory.append(normalized)
    return normalized


async def helper_run_db_async(runtime: ContextRuntime, coro: Any) -> Any:
    if not helper_db_enabled(runtime):
        return None
    try:
        return await coro
    except Exception:
        return None


def helper_audit(runtime: ContextRuntime, tenant_id: str, action: str, detail: str = "") -> None:
    with runtime._lock:
        runtime.audit_log_memory.append(
            {
                "id": len(runtime.audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "detail": detail,
                "source": "autonomous-workforce",
                "created_at": helper_now_iso(),
            }
        )


def helper_mask_secret(value: str) -> str:
    if len(value) < 8:
        return "***"
    return f"{value[:4]}***{value[-3:]}"


async def helper_verify_provider_live(provider: str, token: str) -> tuple[bool, int, dict[str, Any]]:
    entry = PROVIDER_CATALOG.get(provider)
    if entry is None:
        return (False, 422, {"error": "unsupported-provider"})
    headers = {"Authorization": f"Bearer {token}"}
    timeout = float(os.getenv("WORKFORCE_PROVIDER_TEST_TIMEOUT_SECONDS", "15"))
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(entry["test_url"], headers=headers)
        ok = response.status_code < 400
        body: dict[str, Any]
        try:
            parsed = response.json()
            body = parsed if isinstance(parsed, dict) else {"data": parsed}
        except Exception:
            body = {"raw": response.text[:500]}
        return (ok, response.status_code, body)


def helper_connected_provider(runtime: ContextRuntime, tenant_id: str, provider: str) -> dict[str, Any] | None:
    with runtime._lock:
        return next(
            (
                c
                for c in runtime.integrations_memory
                if c.get("tenant_id") == tenant_id
                and c.get("provider") == provider
                and (c.get("status") == "connected")
            ),
            None,
        )


def helper_connected_provider_connections(
    runtime: ContextRuntime, tenant_id: str, providers: list[Any]
) -> list[dict[str, Any]]:
    provider_set = {str(provider).strip().lower() for provider in providers if str(provider).strip()}
    with runtime._lock:
        return [
            item.copy()
            for item in runtime.integrations_memory
            if item.get("tenant_id") == tenant_id
            and str(item.get("provider", "")).strip().lower() in provider_set
            and (item.get("status") == "connected")
        ]


def helper_queue_mission_execution(
    runtime: ContextRuntime, tenant_id: str, mission: dict[str, Any], source: str
) -> dict[str, Any]:
    require_workforce_execution_available()
    from .....tasks.workforce_tasks import enqueue_execute_mission

    providers_for_mission = mission.get("providers", [])
    if not isinstance(providers_for_mission, list):
        providers_for_mission = []
    task_id = enqueue_execute_mission(
        tenant_id,
        str(mission.get("id", "")),
        mission.copy(),
        helper_connected_provider_connections(runtime, tenant_id, providers_for_mission),
    )
    queued_at = helper_now_iso()
    outcome: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "mission_id": mission.get("id"),
        "status": "queued",
        "success_count": 0,
        "failed_count": 0,
        "provider_results": [],
        "artifact": {},
        "queued_task_id": task_id,
        "created_at": queued_at,
        "source": source,
    }
    with runtime._lock:
        mission["status"] = "queued"
        mission["executed_at"] = queued_at
        mission["updated_at"] = queued_at
        runtime.outcomes_memory.append(outcome)
        runtime.feed_memory.append(
            {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "mission_id": mission.get("id"),
                "type": "mission_queued",
                "status": "queued",
                "title": mission.get("title"),
                "summary": f"queued task {task_id}",
                "created_at": queued_at,
            }
        )
    return outcome


async def helper_execute_mission(runtime: ContextRuntime, tenant_id: str, mission: dict[str, Any]) -> dict[str, Any]:
    require_workforce_execution_available()
    mission_start = time.time()
    mission_id = mission.get("id", "unknown")
    role = mission.get("role", "general")
    providers = [str(p).strip().lower() for p in mission.get("providers", []) if str(p).strip()]
    if not providers:
        outcome = {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "mission_id": mission_id,
            "status": "failed",
            "success_count": 0,
            "failed_count": 1,
            "provider_results": [{"provider": None, "ok": False, "error": "mission-no-providers"}],
            "created_at": helper_now_iso(),
        }
        with runtime._lock:
            runtime.outcomes_memory.append(outcome)
            mission["status"] = "failed"
            mission["executed_at"] = helper_now_iso()
            mission["updated_at"] = helper_now_iso()
        runtime._metrics.record_counter("mission_failure", 1, {"reason": "no_providers", "role": role})
        return outcome
    artifact_start = time.time()
    artifact_ok, artifact = await _generate_mission_artifact(tenant_id, mission)
    artifact_time = time.time() - artifact_start
    runtime._metrics.record_duration(
        "artifact_generation", artifact_time, {"role": role, "status": "success" if artifact_ok else "failure"}
    )
    provider_results: list[dict[str, Any]] = []
    for provider in providers:
        provider_start = time.time()
        conn = helper_connected_provider(runtime, tenant_id, provider)
        if conn is None:
            provider_results.append({"provider": provider, "ok": False, "error": "provider-not-connected"})
            with runtime._lock:
                runtime._retry_queue.append(
                    {
                        "id": str(uuid.uuid4()),
                        "tenant_id": tenant_id,
                        "mission_id": mission_id,
                        "provider": provider,
                        "status": "pending",
                        "next_retry_at": (datetime.now(UTC) + timedelta(seconds=60)).isoformat(),
                        "retry_count": 0,
                        "max_retries": 5,
                        "error": "provider-not-connected",
                        "created_at": helper_now_iso(),
                    }
                )
            runtime._metrics.record_counter("retry_queued", 1, {"provider": provider, "reason": "not_connected"})
            continue
        token = str(conn.get("last_verified_token", "")).strip()
        if not token:
            provider_results.append({"provider": provider, "ok": False, "error": "token-not-available"})
            continue
        live_ok, status_code, payload = await helper_verify_provider_live(provider, token)
        if not live_ok:
            provider_results.append(
                {"provider": provider, "ok": False, "status_code": status_code, "response": payload}
            )
            runtime._metrics.record_counter("provider_verification_failure", 1, {"provider": provider})
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
        dispatch_ok = False
        dispatch_result: dict[str, Any] = {}
        executor = get_executor(provider, token)
        if executor:
            if provider == "slack":
                channel = str(conn.get("metadata", {}).get("channel") or "#general").strip()
                dispatch_ok, dispatch_result = await executor.post_message(channel, str(artifact.get("generated", "")))
            elif provider == "x":
                dispatch_ok, dispatch_result = await executor.post_tweet(str(artifact.get("generated", ""))[:260])
            elif provider == "facebook":
                dispatch_ok, dispatch_result = await executor.post_link(
                    str(conn.get("account_id") or "me"),
                    mission.get("input_context", {}).get("link_url", ""),
                    str(artifact.get("generated", ""))[:500],
                )
            elif provider == "instagram":
                dispatch_ok, dispatch_result = await executor.post_reel(
                    str(conn.get("account_id") or "me"),
                    mission.get("input_context", {}).get("video_url", ""),
                    mission.get("input_context", {}).get("thumbnail_url", ""),
                    str(artifact.get("generated", ""))[:300],
                )
            elif provider == "threads":
                dispatch_ok, dispatch_result = await executor.post_thread(
                    str(conn.get("account_id") or "me"), str(artifact.get("generated", ""))
                )
            elif provider == "tiktok":
                dispatch_ok, dispatch_result = await executor.upload_video(
                    mission.get("input_context", {}).get("video_url", ""), str(artifact.get("generated", ""))[:140]
                )
            elif provider == "youtube":
                dispatch_ok, dispatch_result = await executor.upload_video(
                    mission.get("title", ""),
                    str(artifact.get("generated", "")),
                    mission.get("input_context", {}).get("video_url", ""),
                )
        else:
            dispatch_ok, dispatch_result = await _dispatch_provider_action(
                provider, token, mission, str(artifact.get("generated", "")), conn
            )
        provider_time = time.time() - provider_start
        runtime._metrics.record_duration(
            "provider_action", provider_time, {"provider": provider, "status": "success" if dispatch_ok else "failure"}
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
    success_count = sum((1 for item in provider_results if item.get("ok")))
    failed_count = len(provider_results) - success_count
    if failed_count == 0:
        status: MissionStatus = "completed"
    elif success_count == 0:
        status = "failed"
    else:
        status = "completed"
    mission_time = time.time() - mission_start
    runtime._metrics.record_duration("mission_duration", mission_time, {"role": role, "status": status})
    runtime._metrics.record_counter(
        "mission_success" if status == "completed" else "mission_failure", 1, {"role": role}
    )
    outcome = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "mission_id": mission_id,
        "status": status,
        "success_count": success_count,
        "failed_count": failed_count,
        "provider_results": provider_results,
        "artifact": artifact,
        "execution_time_seconds": mission_time,
        "created_at": helper_now_iso(),
    }
    with runtime._lock:
        runtime.outcomes_memory.append(outcome)
        mission["status"] = status
        mission["executed_at"] = helper_now_iso()
        mission["updated_at"] = helper_now_iso()
    return outcome
