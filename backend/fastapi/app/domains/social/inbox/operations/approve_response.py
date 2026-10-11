"""Social/Inbox use cases: approve response."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..runtime import ContextRuntime
from ..schemas import ResponseApprovalRequest
from .audit import helper_append_delivery_failure
from .audit import helper_attempt_outbound_delivery
from .audit import helper_audit
from .audit import helper_build_delivery_idempotency_key
from .audit import helper_resolve_delivery_target
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from typing import Any


async def execute_approve_response(
    runtime: ContextRuntime, message_id: int, payload: ResponseApprovalRequest, auth: AuthDep
) -> dict[str, Any]:
    """Approve and deliver a staged auto-response for messages awaiting approval."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:inbox:approve-response", 180, 60)
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
        network = str(message.get("network", ""))
        external_message_id = str(message.get("external_message_id") or message.get("id") or "")
        response_text = str(message.get("last_response_preview", ""))
    vendor_id, endpoint_template = helper_resolve_delivery_target(network)
    endpoint = endpoint_template.replace("{message_id}", external_message_id)
    request_payload = {
        "message_id": external_message_id,
        "reply_text": response_text,
        "network": network,
        "approved_by": payload.approver.strip(),
    }
    idempotency_key = str(
        message.get("response_delivery_idempotency_key")
        or helper_build_delivery_idempotency_key(auth.tenant_id, message_id, response_text)
    )
    request_payload["idempotency_key"] = idempotency_key
    vendor_response, delivery_errors, attempts_made = await helper_attempt_outbound_delivery(
        vendor_id=vendor_id, endpoint=endpoint, request_payload=request_payload, idempotency_key=idempotency_key
    )
    if vendor_response is None:
        failure = helper_append_delivery_failure(
            runtime,
            auth.tenant_id,
            message_id=message_id,
            network=network,
            vendor_id=vendor_id,
            endpoint=endpoint,
            payload=request_payload,
            errors=delivery_errors,
        )
        with runtime._lock:
            message = next(
                (
                    m
                    for m in runtime.messages_memory
                    if m.get("tenant_id") == auth.tenant_id and m.get("id") == message_id
                ),
                None,
            )
            if message is not None:
                message["response_delivery_status"] = "failed"
                message["response_delivery_attempts"] = attempts_made
                message["response_delivery_failure_id"] = failure.get("id")
                message["response_delivery_last_error"] = delivery_errors[-1] if delivery_errors else "delivery failed"
                message["response_delivery_idempotency_key"] = idempotency_key
                message["updated_at"] = datetime.now(UTC).isoformat()
        raise HTTPException(
            status_code=502, detail=f"Approved response delivery failed after retries; failure_id={failure.get('id')}"
        )
    now_iso = datetime.now(UTC).isoformat()
    with runtime._lock:
        message = next(
            (m for m in runtime.messages_memory if m.get("tenant_id") == auth.tenant_id and m.get("id") == message_id),
            None,
        )
        if message is None:
            raise HTTPException(status_code=404, detail=MESSAGE_NOT_FOUND)
        message["status"] = "complete"
        message["replied"] = True
        message["replied_at"] = now_iso
        message["response_approved_by"] = payload.approver.strip()
        message["response_approved_at"] = now_iso
        message["response_approval_note"] = payload.note.strip() if payload.note else None
        message["response_delivered_at"] = now_iso
        message["response_delivery_vendor"] = vendor_id
        message["response_delivery_status"] = "sent"
        message["response_delivery_attempts"] = attempts_made
        message["response_delivery_result"] = vendor_response
        message["response_delivery_failure_id"] = None
        message["response_delivery_last_error"] = None
        message["response_delivery_idempotency_key"] = idempotency_key
        message["updated_at"] = now_iso
        updated = message.copy()
    helper_audit(runtime, auth.tenant_id, "inbox_auto_response_approved", message_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "message": updated,
        "response": {
            "text": str(updated.get("last_response_preview", "")),
            "source": updated.get("last_response_source"),
            "approved_by": updated.get("response_approved_by"),
            "delivered": True,
        },
    }
