"""Social/Inbox use cases: audit."""

from __future__ import annotations
from .. import constants as inbox_dependencies
from ..constants import MESSAGE_STATUSES, _NETWORK_VENDOR_MAP
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..runtime import ContextRuntime
from ..schemas import InboxMessageIngestRequest
from ..schemas import MessageUpdateRequest
from ..services.classify_message import _build_suggested_replies
from ..services.classify_message import _classify_message
from ..services.classify_message import _priority_score
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from typing import Any
import asyncio
import hashlib
import os


def helper_audit(runtime: ContextRuntime, tenant_id: str, action: str, ref_id: int | None = None) -> None:
    with runtime._lock:
        runtime.audit_log_memory.append(
            {
                "id": len(runtime.audit_log_memory) + 1,
                "tenant_id": tenant_id,
                "action": action,
                "ref_id": ref_id,
                "created_at": datetime.now(UTC).isoformat(),
                "source": "smart-inbox-router",
            }
        )


def helper_get_message(runtime: ContextRuntime, tenant_id: str, message_id: int) -> dict[str, Any] | None:
    with runtime._lock:
        return next(
            (m for m in runtime.messages_memory if m.get("tenant_id") == tenant_id and m.get("id") == message_id), None
        )


def helper_resolve_saved_reply(runtime: ContextRuntime, tenant_id: str, reply_id: int) -> dict[str, Any] | None:
    with runtime._lock:
        return next(
            (r for r in runtime.saved_replies_memory if r.get("tenant_id") == tenant_id and r.get("id") == reply_id),
            None,
        )


def helper_resolve_delivery_target(network: str) -> tuple[str, str]:
    network_key = network.strip().lower()
    vendor_id = _NETWORK_VENDOR_MAP.get(network_key)
    if vendor_id is None:
        raise HTTPException(
            status_code=422, detail=f"Network {network_key} does not support outbound inbox delivery yet"
        )
    network_env_key = network_key.upper().replace("-", "_")
    endpoint = os.getenv(f"INBOX_REPLY_ENDPOINT_{network_env_key}", "").strip()
    if not endpoint:
        endpoint = "/messages/reply/{message_id}"
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    return (vendor_id, endpoint)


def helper_delivery_readiness_for(network: str) -> dict[str, Any]:
    network_key = network.strip().lower()
    vendor_id = _NETWORK_VENDOR_MAP.get(network_key)
    if vendor_id is None:
        return {
            "delivery_vendor": None,
            "delivery_ready": False,
            "delivery_blocker": f"Unsupported network: {network_key}",
        }
    credentials = inbox_dependencies.vendor_manager.get_credentials(vendor_id)
    if credentials is None:
        return {
            "delivery_vendor": vendor_id,
            "delivery_ready": False,
            "delivery_blocker": f"Missing vendor credentials for {vendor_id}",
        }
    return {"delivery_vendor": vendor_id, "delivery_ready": True, "delivery_blocker": None}


def helper_record_replay_run(
    runtime: ContextRuntime,
    *,
    tenant_id: str,
    operator: str,
    note: str | None,
    requested_limit: int,
    selected_failure_ids: list[int],
    network_filter: str | None,
    replay_result: dict[str, Any],
    duration_ms: int,
) -> dict[str, Any]:
    now_iso = datetime.now(UTC).isoformat()
    with runtime._lock:
        run_record = {
            "id": len(runtime.delivery_replay_runs_memory) + 1,
            "tenant_id": tenant_id,
            "operator": operator,
            "note": note,
            "requested_limit": requested_limit,
            "selected_count": len(selected_failure_ids),
            "selected_failure_ids": selected_failure_ids,
            "network_filter": network_filter,
            "count": int(replay_result.get("count") or 0),
            "replayed_count": int(replay_result.get("replayed_count") or 0),
            "failed_count": int(replay_result.get("failed_count") or 0),
            "skipped_count": int(replay_result.get("skipped_count") or 0),
            "not_found_count": int(replay_result.get("not_found_count") or 0),
            "duration_ms": duration_ms,
            "created_at": now_iso,
        }
        runtime.delivery_replay_runs_memory.append(run_record)
    return run_record.copy()


def helper_percentile(values: list[int], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * percentile
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return float(ordered[lower])
    weight = rank - lower
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * weight)


def helper_env_float(name: str, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = float(raw)
    except ValueError:
        return default
    if minimum is not None and parsed < minimum:
        return minimum
    if maximum is not None and parsed > maximum:
        return maximum
    return parsed


def helper_env_int(name: str, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        parsed = int(raw)
    except ValueError:
        return default
    if minimum is not None and parsed < minimum:
        return minimum
    if maximum is not None and parsed > maximum:
        return maximum
    return parsed


def helper_append_delivery_failure(
    runtime: ContextRuntime,
    tenant_id: str,
    *,
    message_id: int,
    network: str,
    vendor_id: str,
    endpoint: str,
    payload: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    with runtime._lock:
        record = {
            "id": len(runtime.delivery_failures_memory) + 1,
            "tenant_id": tenant_id,
            "message_id": message_id,
            "network": network,
            "vendor_id": vendor_id,
            "endpoint": endpoint,
            "payload": payload,
            "errors": errors,
            "status": "pending_retry",
            "created_at": datetime.now(UTC).isoformat(),
        }
        runtime.delivery_failures_memory.append(record)
        return record.copy()


def helper_update_delivery_failure(
    runtime: ContextRuntime, tenant_id: str, failure_id: int, **updates: Any
) -> dict[str, Any] | None:
    with runtime._lock:
        failure = next(
            (
                item
                for item in runtime.delivery_failures_memory
                if item.get("tenant_id") == tenant_id and int(item.get("id") or 0) == failure_id
            ),
            None,
        )
        if failure is None:
            return None
        failure.update(updates)
        return failure.copy()


def helper_build_delivery_idempotency_key(tenant_id: str, message_id: int, response_text: str) -> str:
    digest = hashlib.sha256(f"{tenant_id}:{message_id}:{response_text}".encode()).hexdigest()[:24]
    return f"inbox-reply:{tenant_id}:{message_id}:{digest}"


async def helper_attempt_outbound_delivery(
    *, vendor_id: str, endpoint: str, request_payload: dict[str, Any], idempotency_key: str
) -> tuple[dict[str, Any] | None, list[str], int]:
    max_retries = max(1, min(int(os.getenv("INBOX_DELIVERY_MAX_RETRIES", "3") or "3"), 6))
    backoff_seconds = max(0.0, float(os.getenv("INBOX_DELIVERY_BACKOFF_SECONDS", "1") or "1"))
    vendor_response: dict[str, Any] | None = None
    delivery_errors: list[str] = []
    for attempt in range(1, max_retries + 1):
        try:
            vendor_response = await inbox_dependencies.vendor_manager.make_request(
                vendor_id, "POST", endpoint, headers={"Idempotency-Key": idempotency_key}, json_data=request_payload
            )
            return (vendor_response, delivery_errors, attempt)
        except Exception as exc:
            delivery_errors.append(f"attempt {attempt}: {exc}")
            if attempt < max_retries and backoff_seconds > 0:
                await asyncio.sleep(backoff_seconds * 2 ** (attempt - 1))
    return (None, delivery_errors, max_retries)


def helper_build_alerts(runtime: ContextRuntime, tenant_id: str) -> list[dict[str, Any]]:
    with runtime._lock:
        tenant_messages = [m.copy() for m in runtime.messages_memory if m.get("tenant_id") == tenant_id]
    alerts: list[dict[str, Any]] = []

    def _severity_for(message: dict[str, Any]) -> str:
        if message.get("message_type") == "crisis":
            return "critical"
        if int(message.get("priority_score", 0)) >= 80:
            return "high"
        return "medium"

    def _sort_rank(item: dict[str, Any]) -> tuple[int, int]:
        severity = str(item.get("severity", "medium"))
        if severity == "critical":
            severity_rank = 0
        elif severity == "high":
            severity_rank = 1
        else:
            severity_rank = 2
        return (severity_rank, -int(item.get("priority_score") or 0))

    for message in tenant_messages:
        if message.get("source_type") != "mention" and int(message.get("priority_score", 0)) < 60:
            continue
        severity = _severity_for(message)
        alerts.append(
            {
                "message_id": message.get("id"),
                "network": message.get("network"),
                "source_type": message.get("source_type"),
                "author_handle": message.get("author_handle"),
                "message_type": message.get("message_type"),
                "sentiment": message.get("sentiment"),
                "priority_score": message.get("priority_score"),
                "severity": severity,
                "text_preview": str(message.get("text", ""))[:160],
                "created_at": message.get("created_at"),
            }
        )
    alerts.sort(key=_sort_rank)
    return alerts


def execute_ingest_message(
    runtime: ContextRuntime, payload: InboxMessageIngestRequest, auth: AuthDep
) -> dict[str, Any]:
    """
    ADDED: Ingest an inbound social message into the Smart Inbox.
    Applies AI classification, sentiment detection, and priority scoring automatically.
    Deduplicates by external_message_id to avoid double-ingestion from webhooks.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:ingest", 600, 60)
    network = payload.network.strip().lower()
    source_type = payload.source_type.strip().lower()
    if payload.external_message_id:
        with runtime._lock:
            existing = next(
                (
                    m
                    for m in runtime.messages_memory
                    if m.get("tenant_id") == auth.tenant_id
                    and m.get("external_message_id") == payload.external_message_id
                ),
                None,
            )
        if existing:
            return {"status": "ok", "tenant_id": auth.tenant_id, "message": existing.copy(), "created": False}
    message_type, sentiment, confidence = _classify_message(payload.text)
    priority = _priority_score(message_type, sentiment, payload.author_follower_count)
    suggestions = _build_suggested_replies(message_type)
    with runtime._lock:
        message: dict[str, Any] = {
            "id": len(runtime.messages_memory) + 1,
            "tenant_id": auth.tenant_id,
            "network": network,
            "source_type": source_type,
            "external_message_id": payload.external_message_id,
            "parent_message_id": payload.parent_message_id,
            "author_handle": payload.author_handle.strip(),
            "author_display_name": payload.author_display_name,
            "author_follower_count": payload.author_follower_count,
            "crm_contact_id": payload.crm_contact_id,
            "text": payload.text,
            "message_type": message_type,
            "sentiment": sentiment,
            "classification_confidence": confidence,
            "priority_score": priority,
            "suggested_replies": suggestions,
            "status": "pending",
            "assigned_to": None,
            "due_at": None,
            "tags": [],
            "replied": False,
            "replied_at": None,
            "read": False,
            "read_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.messages_memory.append(message)
    helper_audit(runtime, auth.tenant_id, "inbox_message_ingested", message["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "message": message.copy(), "created": True}


def execute_update_message(
    runtime: ContextRuntime, message_id: int, payload: MessageUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    """ADDED: Update message assignment, status, or tags (§3.1.3 Assignment)."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:update", 300, 60)
    with runtime._lock:
        message = next(
            (m for m in runtime.messages_memory if m.get("tenant_id") == auth.tenant_id and m.get("id") == message_id),
            None,
        )
        if message is None:
            raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
        if payload.assigned_to is not None:
            message["assigned_to"] = payload.assigned_to.strip() or None
        if payload.status is not None:
            status_clean = payload.status.strip().lower()
            if status_clean not in MESSAGE_STATUSES:
                raise HTTPException(
                    status_code=422, detail=f"Invalid status. Must be one of: {', '.join(sorted(MESSAGE_STATUSES))}"
                )
            message["status"] = status_clean
            if status_clean == "complete":
                message["completed_at"] = datetime.now(UTC).isoformat()
        if payload.tags is not None:
            message["tags"] = [t.strip() for t in payload.tags if t.strip()]
        if payload.due_at is not None:
            message["due_at"] = payload.due_at
        message["updated_at"] = datetime.now(UTC).isoformat()
        updated = message.copy()
    helper_audit(runtime, auth.tenant_id, "inbox_message_updated", message_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "message": updated}
