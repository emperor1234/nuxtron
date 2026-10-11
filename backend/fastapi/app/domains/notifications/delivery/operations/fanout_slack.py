"""Notifications/Delivery use cases: fanout slack."""

from __future__ import annotations
from .....deps import AuthContext
from .....deps import require_auth
from ..constants import AuthDep
from ..constants import DIGEST_FREQUENCY_VALUES
from ..constants import PRIORITY_VALUES
from ..runtime import ContextRuntime
from ..schemas import NotificationCreateRequest
from ..schemas import NotificationPreferencesRequest
from ..services.get_default_preferences import _normalize_lower
from ..services.get_default_preferences import _policy_reason
from ..services.get_default_preferences import _safe_notification_id
from ..services.get_default_preferences import _sanitize_muted_categories
from .get_preferences import helper_append_audit
from .get_preferences import helper_append_delivery_receipt
from .get_preferences import helper_broadcast_snapshot
from .get_preferences import helper_get_preferences
from .get_preferences import helper_hydrate_tenant_notifications
from .get_preferences import helper_increment_unread_category_locked
from .get_preferences import helper_persist_created_notification
from .get_preferences import helper_snapshot_for_tenant
from .get_preferences import helper_unread_total_for_tenant
from ....identity.secure_egress import outbound_request
from ....identity.secure_egress import resolve_outbound_target
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from fastapi import Header
from fastapi import Query
from fastapi import Request
from typing import Annotated
from typing import Any
import hmac
import httpx
import os


def helper_fanout_slack(runtime: ContextRuntime, notification: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    notification_id = _safe_notification_id(notification)
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return helper_append_delivery_receipt(
            runtime,
            tenant_id,
            notification_id,
            "slack",
            "slack-incoming-webhook",
            "queued",
            reason="SLACK_WEBHOOK_URL not configured",
        )
    body = {
        "text": f"[{str(notification.get('priority', 'info')).upper()}] {notification.get('title', 'Notification')}\n{notification.get('message', '')}".strip()
    }
    try:
        target = resolve_outbound_target(webhook_url)
        response = outbound_request("POST", target, json=body, timeout=10.0, max_response_bytes=64_000)
        if response.is_success:
            return helper_append_delivery_receipt(
                runtime, tenant_id, notification_id, "slack", "slack-incoming-webhook", "sent"
            )
        return helper_append_delivery_receipt(
            runtime, tenant_id, notification_id, "slack", "slack-incoming-webhook", "queued-after-non-success"
        )
    except (httpx.HTTPError, ValueError):
        return helper_append_delivery_receipt(
            runtime, tenant_id, notification_id, "slack", "slack-incoming-webhook", "queued-after-error"
        )


def helper_fanout_email(runtime: ContextRuntime, notification: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    notification_id = _safe_notification_id(notification)
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    from_email = os.getenv("RESEND_FROM_EMAIL", "onboarding@nuxtron.local").strip()
    to_email = os.getenv("NOTIFICATION_EMAIL_TO", "").strip()
    api_base_url = os.getenv("RESEND_API_BASE_URL", "https://api.resend.com").rstrip("/")
    if not api_key or not to_email:
        return helper_append_delivery_receipt(
            runtime,
            tenant_id,
            notification_id,
            "email",
            "resend",
            "queued",
            reason="RESEND_API_KEY or NOTIFICATION_EMAIL_TO not configured",
        )
    body = {
        "from": from_email,
        "to": [to_email],
        "subject": f"[{str(notification.get('priority', 'info')).upper()}] {notification.get('title', 'Notification')}",
        "text": str(notification.get("message", "") or ""),
    }
    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                f"{api_base_url}/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=body,
            )
            if response.is_success:
                try:
                    data = response.json()
                except ValueError:
                    data = {}
                return helper_append_delivery_receipt(
                    runtime,
                    tenant_id,
                    notification_id,
                    "email",
                    "resend",
                    "sent",
                    external_id=str(data.get("id") or ""),
                )
        return helper_append_delivery_receipt(
            runtime, tenant_id, notification_id, "email", "resend", "queued-after-non-success"
        )
    except httpx.HTTPError:
        return helper_append_delivery_receipt(
            runtime, tenant_id, notification_id, "email", "resend", "queued-after-error"
        )


def helper_fanout_webhook(runtime: ContextRuntime, notification: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    notification_id = _safe_notification_id(notification)
    webhook_url = os.getenv("NOTIFICATION_WEBHOOK_URL", "").strip()
    webhook_token = os.getenv("NOTIFICATION_WEBHOOK_TOKEN", "").strip()
    if not webhook_url:
        return helper_append_delivery_receipt(
            runtime,
            tenant_id,
            notification_id,
            "webhook",
            "generic-webhook",
            "queued",
            reason="NOTIFICATION_WEBHOOK_URL not configured",
        )
    headers = {"Content-Type": "application/json"}
    if webhook_token:
        headers["Authorization"] = f"Bearer {webhook_token}"
    payload = {"event": "notification.created", "tenant_id": tenant_id, "notification": notification}
    try:
        target = resolve_outbound_target(webhook_url)
        response = outbound_request(
            "POST", target, headers=headers, json=payload, timeout=10.0, max_response_bytes=64_000
        )
        if response.is_success:
            return helper_append_delivery_receipt(
                runtime, tenant_id, notification_id, "webhook", "generic-webhook", "sent"
            )
        return helper_append_delivery_receipt(
            runtime, tenant_id, notification_id, "webhook", "generic-webhook", "queued-after-non-success"
        )
    except (httpx.HTTPError, ValueError):
        return helper_append_delivery_receipt(
            runtime, tenant_id, notification_id, "webhook", "generic-webhook", "queued-after-error"
        )


def helper_fanout_notification(
    runtime: ContextRuntime, notification: dict[str, Any], prefs: dict[str, Any]
) -> list[dict[str, Any]]:
    tenant_id = str(notification.get("tenant_id") or "")
    priority = _normalize_lower(notification.get("priority", "info"), "info")
    notification_id = _safe_notification_id(notification)
    receipts: list[dict[str, Any]] = []
    slack_enabled = bool(prefs.get("slack_enabled", False))
    slack_policy_match = priority in {"warning", "error", "critical"}
    if slack_enabled and slack_policy_match:
        receipt = helper_fanout_slack(runtime, notification, tenant_id)
        receipt["policy_decision"] = _policy_reason(True, True, "slack")
        receipts.append(receipt)
    else:
        receipts.append(
            helper_append_delivery_receipt(
                runtime,
                tenant_id,
                notification_id,
                "slack",
                "slack-incoming-webhook",
                "skipped",
                reason="channel disabled by preference or priority policy",
                policy_decision=_policy_reason(slack_enabled, slack_policy_match, "slack"),
            )
        )
    email_enabled = bool(prefs.get("email_enabled", True))
    email_policy_match = priority in {"error", "critical"}
    if email_enabled and email_policy_match:
        receipt = helper_fanout_email(runtime, notification, tenant_id)
        receipt["policy_decision"] = _policy_reason(True, True, "email")
        receipts.append(receipt)
    else:
        receipts.append(
            helper_append_delivery_receipt(
                runtime,
                tenant_id,
                notification_id,
                "email",
                "resend",
                "skipped",
                reason="channel disabled by preference or priority policy",
                policy_decision=_policy_reason(email_enabled, email_policy_match, "email"),
            )
        )
    webhook_enabled = True
    webhook_policy_match = priority == "critical"
    if webhook_policy_match:
        receipt = helper_fanout_webhook(runtime, notification, tenant_id)
        receipt["policy_decision"] = _policy_reason(True, True, "webhook")
        receipts.append(receipt)
    else:
        receipts.append(
            helper_append_delivery_receipt(
                runtime,
                tenant_id,
                notification_id,
                "webhook",
                "generic-webhook",
                "skipped",
                reason="webhook fan-out enabled for critical notifications only",
                policy_decision=_policy_reason(webhook_enabled, webhook_policy_match, "webhook"),
            )
        )
    return receipts


async def helper_stream_auth(
    request: Request,
    api_key: Annotated[str | None, Query(alias="api_key")] = None,
    tenant_id: Annotated[str | None, Query(alias="tenant_id")] = None,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> AuthContext:
    if isinstance(authorization, str) and authorization.strip().lower().startswith("bearer "):
        return await require_auth(request=request, x_tenant_id=tenant_id, authorization=authorization)
    if api_key and tenant_id:
        expected = os.getenv("FASTAPI_API_KEY", "change-this-fastapi-key").strip()
        if expected and hmac.compare_digest(api_key, expected):
            return AuthContext(tenant_id=tenant_id, auth_mode="api_key")
    raise HTTPException(status_code=401, detail="Missing or invalid stream authentication.")


def execute_list_notifications(
    runtime: ContextRuntime,
    auth: AuthDep,
    category: Annotated[str | None, Query(max_length=40)] = None,
    priority: Annotated[str | None, Query(max_length=20)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:list", 1200, 60)
    return helper_snapshot_for_tenant(
        runtime, auth.tenant_id, category=category, priority=priority, limit=limit, offset=offset
    )


def execute_update_preferences(
    runtime: ContextRuntime, payload: NotificationPreferencesRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:preferences:update", 60, 60)
    digest_frequency = _normalize_lower(payload.digest_frequency, "realtime")
    if digest_frequency not in DIGEST_FREQUENCY_VALUES:
        raise HTTPException(status_code=422, detail="Invalid digest frequency.")
    muted_categories = _sanitize_muted_categories(payload.muted_categories)
    with runtime.memory_lock:
        existing = next((p for p in runtime._preferences_memory if p.get("tenant_id") == auth.tenant_id), None)
        if existing:
            existing.update(
                {
                    "muted_categories": muted_categories,
                    "email_enabled": payload.email_enabled,
                    "sms_enabled": payload.sms_enabled,
                    "slack_enabled": payload.slack_enabled,
                    "realtime_enabled": payload.realtime_enabled,
                    "digest_frequency": digest_frequency,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            prefs = existing.copy()
        else:
            prefs = {
                "tenant_id": auth.tenant_id,
                "muted_categories": muted_categories,
                "email_enabled": payload.email_enabled,
                "sms_enabled": payload.sms_enabled,
                "slack_enabled": payload.slack_enabled,
                "realtime_enabled": payload.realtime_enabled,
                "digest_frequency": digest_frequency,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            runtime._preferences_memory.append(prefs)
            prefs = prefs.copy()
    helper_append_audit(runtime, auth.tenant_id, "notification_preferences_updated")
    return {"status": "ok", "tenant_id": auth.tenant_id, "preferences": prefs}


def execute_notification_unread_count(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:unread-count", 300, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "unreadCount": helper_unread_total_for_tenant(runtime, auth.tenant_id),
    }


def execute_create_notification(
    runtime: ContextRuntime, payload: NotificationCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:notifications:create", 120, 60)
    helper_hydrate_tenant_notifications(runtime, auth.tenant_id)
    safe_priority = _normalize_lower(payload.priority, "info")
    if safe_priority not in PRIORITY_VALUES:
        safe_priority = "info"
    safe_category = _normalize_lower(payload.category, "general")
    with runtime.memory_lock:
        item = {
            "id": len(runtime.notifications_memory) + 1,
            "tenant_id": auth.tenant_id,
            "title": payload.title,
            "message": payload.message,
            "category": safe_category,
            "priority": safe_priority,
            "read": False,
            "read_at": None,
            "created_at": datetime.now(UTC).isoformat(),
            "source": "api",
            "persistence": "memory-fallback",
        }
        runtime.notifications_memory.append(item)
        helper_increment_unread_category_locked(runtime, auth.tenant_id, safe_category, 1)
        helper_persist_created_notification(runtime, item)
    prefs = helper_get_preferences(runtime, auth.tenant_id)
    receipts = helper_fanout_notification(runtime, item, prefs)
    helper_append_audit(runtime, auth.tenant_id, "notification_created", item["id"])
    helper_broadcast_snapshot(runtime, auth.tenant_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "notification": item, "deliveryReceipts": receipts}
