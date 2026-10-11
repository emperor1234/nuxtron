"""Social/Inbox use cases: inbox ops go live gate."""

from __future__ import annotations
from .. import constants as inbox_dependencies
from ..constants import _NETWORK_VENDOR_MAP
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..runtime import ContextRuntime
from ..schemas import AutoResponseRequest
from ..schemas import DeliveryFailureBulkResolveRequest
from ..schemas import DeliveryFailureResolveRequest
from ..schemas import ResponseRejectionRequest
from .audit import helper_audit
from .audit import helper_env_float
from .audit import helper_env_int
from .audit import helper_resolve_saved_reply
from .replay_delivery_failures_bulk import execute_inbox_ops_runbooks
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from typing import Any
import os


def execute_inbox_ops_go_live_gate(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Return strict pass/fail go-live checks for Smart Inbox delivery and replay operations."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:ops:go-live-gate", 120, 60)
    required_runbook_codes = {
        "pending_backlog_ratio_high",
        "oldest_pending_age_high",
        "replay_success_rate_low",
        "replay_runs_no_selection_spike",
        "operator_success_rate_low",
        "operator_no_selection_only_runs",
        "operator_latency_spike",
    }
    configured_runbooks = execute_inbox_ops_runbooks(runtime, auth)["items"]
    configured_codes = {str(item.get("code")) for item in configured_runbooks}
    runbook_coverage_complete = required_runbook_codes.issubset(configured_codes)
    delivery_max_retries = helper_env_int("INBOX_DELIVERY_MAX_RETRIES", 3, minimum=1)
    delivery_backoff_seconds = helper_env_float("INBOX_DELIVERY_BACKOFF_SECONDS", 0.5, minimum=0.0)
    delivery_max_backoff_seconds = helper_env_float("INBOX_DELIVERY_MAX_BACKOFF_SECONDS", 8.0, minimum=0.0)
    supported_vendor_ids = sorted(set(_NETWORK_VENDOR_MAP.values()))
    missing_vendor_credentials = [
        vendor_id
        for vendor_id in supported_vendor_ids
        if inbox_dependencies.vendor_manager.get_credentials(vendor_id) is None
    ]
    live_contract_matrix_enabled = str(os.getenv("SOCIAL_CONTRACT_MATRIX_LIVE_ENABLED", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    checks = [
        {
            "code": "delivery_retry_configured",
            "passed": delivery_max_retries >= 2 and delivery_max_backoff_seconds >= delivery_backoff_seconds,
            "detail": {
                "delivery_max_retries": delivery_max_retries,
                "delivery_backoff_seconds": delivery_backoff_seconds,
                "delivery_max_backoff_seconds": delivery_max_backoff_seconds,
            },
        },
        {
            "code": "dlq_operations_wired",
            "passed": isinstance(runtime.delivery_failures_memory, list)
            and isinstance(runtime.delivery_replay_runs_memory, list),
            "detail": {
                "delivery_failures_store_present": isinstance(runtime.delivery_failures_memory, list),
                "delivery_replay_runs_store_present": isinstance(runtime.delivery_replay_runs_memory, list),
            },
        },
        {
            "code": "runbook_coverage_complete",
            "passed": runbook_coverage_complete,
            "detail": {
                "required_count": len(required_runbook_codes),
                "configured_count": len(configured_codes),
                "missing_codes": sorted(required_runbook_codes - configured_codes),
            },
        },
        {
            "code": "vendor_credentials_configured",
            "passed": len(missing_vendor_credentials) == 0,
            "detail": {
                "supported_vendor_ids": supported_vendor_ids,
                "missing_vendor_credentials": missing_vendor_credentials,
            },
        },
        {
            "code": "live_contract_checks_enabled",
            "passed": live_contract_matrix_enabled,
            "detail": {"env": "SOCIAL_CONTRACT_MATRIX_LIVE_ENABLED", "enabled": live_contract_matrix_enabled},
        },
        {
            "code": "alert_thresholds_sane",
            "passed": 0.0 <= helper_env_float("INBOX_ALERT_PENDING_RATIO_HIGH", 0.35, minimum=0.0, maximum=1.0) <= 1.0
            and 0.0 <= helper_env_float("INBOX_ALERT_REPLAY_SUCCESS_RATE_LOW", 0.7, minimum=0.0, maximum=1.0) <= 1.0
            and (0.0 <= helper_env_float("INBOX_ALERT_NO_SELECTION_RATIO_HIGH", 0.8, minimum=0.0, maximum=1.0) <= 1.0),
            "detail": {
                "pending_ratio_high": helper_env_float(
                    "INBOX_ALERT_PENDING_RATIO_HIGH", 0.35, minimum=0.0, maximum=1.0
                ),
                "replay_success_rate_low": helper_env_float(
                    "INBOX_ALERT_REPLAY_SUCCESS_RATE_LOW", 0.7, minimum=0.0, maximum=1.0
                ),
                "no_selection_ratio_high": helper_env_float(
                    "INBOX_ALERT_NO_SELECTION_RATIO_HIGH", 0.8, minimum=0.0, maximum=1.0
                ),
            },
        },
    ]
    blockers = [item["code"] for item in checks if not bool(item.get("passed"))]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "generatedAt": datetime.now(UTC).isoformat(),
        "overall_ready": len(blockers) == 0,
        "check_count": len(checks),
        "passed_count": sum((1 for item in checks if bool(item.get("passed")))),
        "failed_count": len(blockers),
        "blockers": blockers,
        "checks": checks,
    }


def execute_resolve_delivery_failure(
    runtime: ContextRuntime, failure_id: int, payload: DeliveryFailureResolveRequest, auth: AuthDep
) -> dict[str, Any]:
    """Resolve a failed delivery and return the message to manual handling."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:delivery-failures:resolve", 120, 60)
    now_iso = datetime.now(UTC).isoformat()
    with runtime._lock:
        failure = next(
            (
                item
                for item in runtime.delivery_failures_memory
                if item.get("tenant_id") == auth.tenant_id and int(item.get("id") or 0) == failure_id
            ),
            None,
        )
        if failure is None:
            raise HTTPException(status_code=404, detail="Delivery failure not found")
        message = next(
            (
                item
                for item in runtime.messages_memory
                if item.get("tenant_id") == auth.tenant_id
                and int(item.get("id") or 0) == int(failure.get("message_id") or 0)
            ),
            None,
        )
        if str(failure.get("status") or "").lower() == "resolved":
            return {
                "status": "ok",
                "tenant_id": auth.tenant_id,
                "resolved": False,
                "reason": "already_resolved",
                "failure": failure.copy(),
                "message": message.copy() if message is not None else None,
            }
        failure["status"] = "resolved"
        failure["resolution"] = "manual_followup"
        failure["resolved_at"] = now_iso
        failure["resolved_by"] = payload.operator.strip()
        failure["resolution_note"] = payload.note.strip() if payload.note else None
        updated_failure = failure.copy()
        updated_message = None
        if message is not None:
            if str(message.get("status")) == "requires_approval":
                message["status"] = "in_progress"
            message["replied"] = False
            message["replied_at"] = None
            message["response_delivery_status"] = "manual_followup_required"
            message["response_delivery_failure_id"] = None
            message["response_delivery_resolution"] = "manual_followup"
            message["updated_at"] = now_iso
            updated_message = message.copy()
    helper_audit(
        runtime, auth.tenant_id, "inbox_auto_response_delivery_resolved", int(updated_failure.get("message_id") or 0)
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "resolved": True,
        "failure": updated_failure,
        "message": updated_message,
    }


def execute_resolve_delivery_failures_bulk(
    runtime: ContextRuntime, payload: DeliveryFailureBulkResolveRequest, auth: AuthDep
) -> dict[str, Any]:
    """Resolve multiple failed deliveries into manual follow-up in one operation."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:delivery-failures:resolve-bulk", 60, 60)
    now_iso = datetime.now(UTC).isoformat()
    note = payload.note.strip() if payload.note else None
    deduped_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in payload.failure_ids:
        if raw_id in seen:
            continue
        seen.add(raw_id)
        deduped_ids.append(raw_id)
    resolved_ids: list[int] = []
    already_resolved_ids: list[int] = []
    not_found_ids: list[int] = []
    updated_message_ids: list[int] = []
    with runtime._lock:
        for failure_id in deduped_ids:
            failure = next(
                (
                    item
                    for item in runtime.delivery_failures_memory
                    if item.get("tenant_id") == auth.tenant_id and int(item.get("id") or 0) == failure_id
                ),
                None,
            )
            if failure is None:
                not_found_ids.append(failure_id)
                continue
            if str(failure.get("status") or "").lower() == "resolved":
                already_resolved_ids.append(failure_id)
                continue
            failure["status"] = "resolved"
            failure["resolution"] = "manual_followup"
            failure["resolved_at"] = now_iso
            failure["resolved_by"] = payload.operator.strip()
            failure["resolution_note"] = note
            resolved_ids.append(failure_id)
            message = next(
                (
                    item
                    for item in runtime.messages_memory
                    if item.get("tenant_id") == auth.tenant_id
                    and int(item.get("id") or 0) == int(failure.get("message_id") or 0)
                ),
                None,
            )
            if message is not None:
                if str(message.get("status")) == "requires_approval":
                    message["status"] = "in_progress"
                message["replied"] = False
                message["replied_at"] = None
                message["response_delivery_status"] = "manual_followup_required"
                message["response_delivery_failure_id"] = None
                message["response_delivery_resolution"] = "manual_followup"
                message["updated_at"] = now_iso
                updated_message_ids.append(int(message.get("id") or 0))
    for failure_id in resolved_ids:
        helper_audit(runtime, auth.tenant_id, "inbox_auto_response_delivery_resolved_bulk", failure_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "resolved_count": len(resolved_ids),
        "already_resolved_count": len(already_resolved_ids),
        "not_found_count": len(not_found_ids),
        "resolved_ids": resolved_ids,
        "already_resolved_ids": already_resolved_ids,
        "not_found_ids": not_found_ids,
        "updated_message_ids": updated_message_ids,
    }


def execute_auto_respond(
    runtime: ContextRuntime, message_id: int, payload: AutoResponseRequest, auth: AuthDep
) -> dict[str, Any]:
    """Execute an auto-response from saved replies or generated suggestions and update message state."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:auto-respond", 180, 60)
    with runtime._lock:
        message = next(
            (m for m in runtime.messages_memory if m.get("tenant_id") == auth.tenant_id and m.get("id") == message_id),
            None,
        )
        if message is None:
            raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
    response_text = ""
    source = "suggested_reply"
    saved_reply: dict[str, Any] | None = None
    if payload.saved_reply_id is not None:
        saved_reply = helper_resolve_saved_reply(runtime, auth.tenant_id, payload.saved_reply_id)
        if saved_reply is None:
            raise HTTPException(status_code=422, detail="Saved reply not found for tenant")
        if saved_reply.get("networks") and str(message.get("network")) not in [
            str(n) for n in saved_reply.get("networks", [])
        ]:
            raise HTTPException(status_code=422, detail="Saved reply is not configured for this network")
        response_text = str(saved_reply.get("body", ""))
        source = "saved_reply"
    else:
        suggestions = [str(item) for item in message.get("suggested_replies", [])]
        suggestion_index = payload.suggestion_index if payload.suggestion_index is not None else 0
        if suggestion_index >= len(suggestions):
            raise HTTPException(status_code=422, detail="Suggested reply index is out of range")
        response_text = suggestions[suggestion_index]
    now_iso = datetime.now(UTC).isoformat()
    approval_required = payload.require_approval or str(message.get("message_type")) == "crisis"
    with runtime._lock:
        if saved_reply is not None:
            for reply in runtime.saved_replies_memory:
                if reply.get("tenant_id") == auth.tenant_id and reply.get("id") == payload.saved_reply_id:
                    reply["use_count"] = int(reply.get("use_count", 0)) + 1
                    reply["updated_at"] = now_iso
                    break
        message["last_response_preview"] = response_text[:500]
        message["last_response_source"] = source
        message["last_response_by"] = payload.responder.strip()
        message["last_response_at"] = now_iso
        message["replied"] = not approval_required
        message["replied_at"] = now_iso if not approval_required else None
        message["status"] = "requires_approval" if approval_required else "complete"
        message["updated_at"] = now_iso
        updated = message.copy()
    helper_audit(runtime, auth.tenant_id, "inbox_auto_response_executed", message_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "message": updated,
        "response": {
            "text": response_text,
            "source": source,
            "approval_required": approval_required,
            "delivered": not approval_required,
        },
    }


def execute_reject_response(
    runtime: ContextRuntime, message_id: int, payload: ResponseRejectionRequest, auth: AuthDep
) -> dict[str, Any]:
    """Reject a staged auto-response and return the message to active handling."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:reject-response", 180, 60)
    now_iso = datetime.now(UTC).isoformat()
    with runtime._lock:
        message = next(
            (m for m in runtime.messages_memory if m.get("tenant_id") == auth.tenant_id and m.get("id") == message_id),
            None,
        )
        if message is None:
            raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
        if (
            str(message.get("status")) != "requires_approval"
            or not str(message.get("last_response_preview", "")).strip()
        ):
            raise HTTPException(status_code=409, detail="No approval-pending response exists")
        message["status"] = "in_progress"
        message["replied"] = False
        message["replied_at"] = None
        message["response_rejected_by"] = payload.reviewer.strip()
        message["response_rejected_at"] = now_iso
        message["response_rejection_note"] = payload.note.strip() if payload.note else None
        message["updated_at"] = now_iso
        updated = message.copy()
    helper_audit(runtime, auth.tenant_id, "inbox_auto_response_rejected", message_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "message": updated,
        "response": {
            "text": str(updated.get("last_response_preview", "")),
            "source": updated.get("last_response_source"),
            "rejected_by": updated.get("response_rejected_by"),
            "delivered": False,
        },
    }
