"""Workflow use cases: connector health check."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..incidents import close_sla_alerts_if_recovered
from ..incidents import record_sla_alert
from ..reliability import compute_reliability_snapshot
from ..reliability import ensure_reliability_fields
from ..reliability import is_in_maintenance_window
from ..reliability import is_retryable_failure
from ..reliability import next_retry_at
from ..reliability import process_replay_item_locked
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorFailureSimulationRequest
from ..schemas import WorkflowConnectorReliabilityPolicyRequest
from ..schemas import WorkflowConnectorReplayProcessorRequest
from ..service import append_audit
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def execute_connector_health_check(runtime: WorkflowRuntime, connector_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:health", 90, 60)
    with runtime.lock:
        connector = next(
            (c for c in runtime.connectors if c.get("id") == connector_id and c.get("tenant_id") == auth.tenant_id),
            None,
        )
        if connector is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        ensure_reliability_fields(connector)
        score_seed = len(str(connector.get("name", ""))) + len(str(connector.get("vendor", "")))
        health = "healthy" if score_seed % 3 != 0 else "degraded"
        connector["status"] = health
        connector["last_checked_at"] = datetime.now(UTC).isoformat()
        connector["updated_at"] = datetime.now(UTC).isoformat()
        connector["reliability_stats"]["total_requests"] = (
            int(connector["reliability_stats"].get("total_requests", 0)) + 1
        )
        if health != "healthy":
            connector["reliability_stats"]["failed_requests"] = (
                int(connector["reliability_stats"].get("failed_requests", 0)) + 1
            )
    append_audit(runtime, auth.tenant_id, "workflow_connector_health_checked", connector_id)
    reliability = compute_reliability_snapshot(connector)
    record_sla_alert(runtime, auth.tenant_id, connector, reliability)
    close_sla_alerts_if_recovered(runtime, auth.tenant_id, connector_id, reliability)
    return {
        "status": "ok",
        "connector": connector,
        "health": {
            "status": connector["status"],
            "latency_ms_p95": 120 if connector["status"] == "healthy" else 480,
            "availability_pct_24h": 99.95 if connector["status"] == "healthy" else 97.1,
        },
        "reliability": reliability,
    }


def execute_update_connector_reliability_policy(
    runtime: WorkflowRuntime, connector_id: int, payload: WorkflowConnectorReliabilityPolicyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:policy:update", 60, 60)
    with runtime.lock:
        connector = next(
            (c for c in runtime.connectors if c.get("id") == connector_id and c.get("tenant_id") == auth.tenant_id),
            None,
        )
        if connector is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        ensure_reliability_fields(connector)
        connector["reliability_policy"] = {
            "max_retries": payload.max_retries,
            "base_backoff_ms": payload.base_backoff_ms,
            "circuit_failure_threshold": payload.circuit_failure_threshold,
            "circuit_cooldown_seconds": payload.circuit_cooldown_seconds,
            "slo_availability_target_pct": payload.slo_availability_target_pct,
            "slo_latency_p95_target_ms": payload.slo_latency_p95_target_ms,
            "replay_enabled": payload.replay_enabled,
        }
        connector["circuit_breaker"]["cooldown_seconds"] = payload.circuit_cooldown_seconds
        connector["updated_at"] = datetime.now(UTC).isoformat()
    append_audit(runtime, auth.tenant_id, "workflow_connector_reliability_policy_updated", connector_id)
    return {"status": "ok", "connector": connector, "policy": connector["reliability_policy"]}


def execute_get_connector_reliability(runtime: WorkflowRuntime, connector_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:reliability:get", 120, 60)
    with runtime.lock:
        connector = next(
            (c for c in runtime.connectors if c.get("id") == connector_id and c.get("tenant_id") == auth.tenant_id),
            None,
        )
        if connector is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        ensure_reliability_fields(connector)
        replay_items = [
            i
            for i in runtime.connector_replay_queue
            if i.get("tenant_id") == auth.tenant_id and i.get("connector_id") == connector_id
        ]
        reliability = compute_reliability_snapshot(connector)
        record_sla_alert(runtime, auth.tenant_id, connector, reliability)
        close_sla_alerts_if_recovered(runtime, auth.tenant_id, connector_id, reliability)
    return {
        "status": "ok",
        "connector": connector,
        "circuit_breaker": connector["circuit_breaker"],
        "policy": connector["reliability_policy"],
        "stats": connector["reliability_stats"],
        "replay_queue": {
            "total": len(replay_items),
            "pending": len([i for i in replay_items if i.get("status") == "pending"]),
            "items": replay_items[:25],
        },
        "slo": reliability,
    }


def execute_simulate_connector_failure(
    runtime: WorkflowRuntime, connector_id: int, payload: WorkflowConnectorFailureSimulationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:simulate-failure", 60, 60)
    failure_type = payload.failure_type.strip().lower() or "timeout"
    with runtime.lock:
        connector = next(
            (c for c in runtime.connectors if c.get("id") == connector_id and c.get("tenant_id") == auth.tenant_id),
            None,
        )
        if connector is None:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        ensure_reliability_fields(connector)
        policy = connector["reliability_policy"]
        stats = connector["reliability_stats"]
        circuit = connector["circuit_breaker"]
        stats["total_requests"] = int(stats.get("total_requests", 0)) + 1
        stats["failed_requests"] = int(stats.get("failed_requests", 0)) + 1
        if is_retryable_failure(failure_type):
            stats["retries_attempted"] = int(stats.get("retries_attempted", 0)) + int(policy.get("max_retries", 0))
        circuit["consecutive_failures"] = int(circuit.get("consecutive_failures", 0)) + 1
        if int(circuit["consecutive_failures"]) >= int(policy.get("circuit_failure_threshold", 5)):
            circuit["state"] = "open"
            circuit["opened_at"] = datetime.now(UTC).isoformat()
        connector["status"] = "degraded"
        replay_item = None
        if bool(policy.get("replay_enabled", True)):
            now = datetime.now(UTC)
            replay_item = {
                "id": len(runtime.connector_replay_queue) + 1,
                "tenant_id": auth.tenant_id,
                "connector_id": connector_id,
                "connector_name": connector.get("name"),
                "failure_type": failure_type,
                "operation_ref": payload.operation_ref or f"op-{len(runtime.connector_replay_queue) + 1}",
                "attempts": 0,
                "status": "pending",
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "next_retry_at": next_retry_at(now, 1, int(policy.get("base_backoff_ms", 250))),
            }
            runtime.connector_replay_queue.append(replay_item)
            stats["replay_enqueued"] = int(stats.get("replay_enqueued", 0)) + 1
        connector["updated_at"] = datetime.now(UTC).isoformat()
        reliability = compute_reliability_snapshot(connector)
        record_sla_alert(runtime, auth.tenant_id, connector, reliability)
    append_audit(runtime, auth.tenant_id, "workflow_connector_failure_simulated", connector_id)
    return {"status": "ok", "connector": connector, "replay_item": replay_item, "slo": reliability}


def execute_list_connector_replay_queue(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    connector_id: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:replay:list", 120, 60)
    with runtime.lock:
        items = [item.copy() for item in runtime.connector_replay_queue if item.get("tenant_id") == auth.tenant_id]
    if connector_id is not None:
        items = [item for item in items if item.get("connector_id") == connector_id]
    return {"status": "ok", "items": items[:limit], "total": len(items)}


def execute_list_connector_sla_alerts(
    runtime: WorkflowRuntime,
    auth: AuthDep,
    status: Annotated[str | None, Query(max_length=20)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:sla-alerts:list", 120, 60)
    with runtime.lock:
        items = [a.copy() for a in runtime.connector_sla_alerts if a.get("tenant_id") == auth.tenant_id]
    if status:
        items = [a for a in items if str(a.get("status", "")).strip().lower() == status.strip().lower()]
    return {"status": "ok", "alerts": items[:limit], "total": len(items)}


def execute_reconcile_connector_circuits(runtime: WorkflowRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:circuits:reconcile", 60, 60)
    now = datetime.now(UTC)
    transitioned: list[dict[str, Any]] = []
    with runtime.lock:
        for connector in runtime.connectors:
            if connector.get("tenant_id") != auth.tenant_id:
                continue
            ensure_reliability_fields(connector)
            circuit = connector["circuit_breaker"]
            state = str(circuit.get("state", "closed"))
            if state != "open":
                continue
            opened_at_raw = circuit.get("opened_at")
            if not opened_at_raw:
                continue
            opened_at = datetime.fromisoformat(str(opened_at_raw))
            elapsed = (now - opened_at).total_seconds()
            cooldown = int(circuit.get("cooldown_seconds", 120))
            if elapsed >= cooldown:
                circuit["state"] = "half_open"
                circuit["consecutive_failures"] = 0
                connector["status"] = "degraded"
                connector["updated_at"] = now.isoformat()
                transitioned.append({"connector_id": connector.get("id"), "state": "half_open"})
    append_audit(runtime, auth.tenant_id, "workflow_connector_circuits_reconciled", len(transitioned))
    return {"status": "ok", "transitioned": transitioned, "count": len(transitioned)}


def execute_process_connector_replay_queue(
    runtime: WorkflowRuntime, payload: WorkflowConnectorReplayProcessorRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workflows:connectors:replay:process", 60, 60)
    now = datetime.now(UTC)
    processed: list[dict[str, Any]] = []
    with runtime.lock:
        pending = [
            item
            for item in runtime.connector_replay_queue
            if item.get("tenant_id") == auth.tenant_id and item.get("status") == "pending"
        ]
        if payload.connector_id is not None:
            pending = [item for item in pending if int(item.get("connector_id", 0)) == payload.connector_id]

        def _is_due(item: dict[str, Any]) -> bool:
            next_retry_at = item.get("next_retry_at")
            if not next_retry_at:
                return True
            return datetime.fromisoformat(str(next_retry_at)) <= now

        due_items = [item for item in pending if _is_due(item) or payload.include_not_due][: payload.limit]
        for item in due_items:
            connector = next(
                (
                    c
                    for c in runtime.connectors
                    if int(c.get("id", 0)) == int(item.get("connector_id", 0)) and c.get("tenant_id") == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                item["status"] = "failed"
                item["updated_at"] = now.isoformat()
                item["next_retry_at"] = None
                processed.append({"item_id": item.get("id"), "status": "failed", "reason": "connector_not_found"})
                continue
            if is_in_maintenance_window(runtime, auth.tenant_id, int(connector.get("id", 0)), now):
                processed.append(
                    {
                        "item_id": item.get("id"),
                        "connector_id": connector.get("id"),
                        "status": item.get("status"),
                        "next_retry_at": item.get("next_retry_at"),
                        "reason": "maintenance_window_active",
                    }
                )
                continue
            result = process_replay_item_locked(connector=connector, item=item, force_success=payload.force_success)
            reliability = result["slo"]
            record_sla_alert(runtime, auth.tenant_id, connector, reliability)
            close_sla_alerts_if_recovered(runtime, auth.tenant_id, int(connector.get("id", 0)), reliability)
            processed.append(
                {
                    "item_id": item.get("id"),
                    "connector_id": connector.get("id"),
                    "status": item.get("status"),
                    "next_retry_at": item.get("next_retry_at"),
                }
            )
    append_audit(runtime, auth.tenant_id, "workflow_connector_replay_queue_processed", len(processed))
    return {"status": "ok", "processed": processed, "count": len(processed)}
