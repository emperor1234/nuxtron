"""Notifications/Delivery HTTP composition and legacy import exports."""

from __future__ import annotations
from .runtime import ContextRuntime
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any
import threading
from .api import (
    list_notifications,
    mark_notifications_read_all,
)
from .services.get_default_preferences import _get_default_preferences as _get_default_preferences
from .services.get_default_preferences import _sse_message as _sse_message
from .services.get_default_preferences import _normalize_lower as _normalize_lower
from .services.get_default_preferences import _sanitize_muted_categories as _sanitize_muted_categories
from .services.get_default_preferences import _safe_notification_id as _safe_notification_id
from .services.get_default_preferences import _parse_iso_timestamp as _parse_iso_timestamp
from .services.get_default_preferences import _policy_reason as _policy_reason
from .services.get_default_preferences import _batch_notifications_for_digest as _batch_notifications_for_digest
from .services.get_default_preferences import _apply_delivery_backoff as _apply_delivery_backoff
from .schemas import NotificationPreferencesRequest as NotificationPreferencesRequest
from .schemas import NotificationCreateRequest as NotificationCreateRequest
from .constants import NOTIFICATION_NOT_FOUND as NOTIFICATION_NOT_FOUND
from .constants import DIGEST_FREQUENCY_VALUES as DIGEST_FREQUENCY_VALUES
from .constants import AuthDep as AuthDep
from .constants import PRIORITY_VALUES as PRIORITY_VALUES
import asyncio
import hmac
import json
import os
from collections.abc import AsyncIterator
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Annotated
import httpx
import psycopg
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from pydantic import Field
from ....deps import AuthContext
from ....deps import require_auth


def create_notifications_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    notifications_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
    notification_preferences_memory: list[dict[str, Any]] | None = None,
    notification_delivery_receipts_memory: list[dict[str, Any]] | None = None,
    db_ready_fn: Callable[[], bool] | None = None,
    db_dsn_fn: Callable[[], str] | None = None,
) -> APIRouter:
    """
    Create notification router with preferences support.

    Complexity kept low by extracting helper logic into module-level functions.
    """
    _preferences_memory: list[dict[str, Any]] = (
        notification_preferences_memory if notification_preferences_memory is not None else []
    )
    _delivery_receipts_memory: list[dict[str, Any]] = (
        notification_delivery_receipts_memory if notification_delivery_receipts_memory is not None else []
    )
    _db_ready_fn = db_ready_fn if db_ready_fn is not None else lambda: False
    _db_dsn_fn = db_dsn_fn if db_dsn_fn is not None else lambda: ""
    router = APIRouter()
    memory_lock = threading.Lock()
    subscribers: dict[str, list[dict[str, Any]]] = {}
    unread_by_tenant_category: dict[str, dict[str, int]] = {}
    db_bootstrap = {"done": False}
    hydrated_tenants: set[str] = set()
    tenant_hydration_locks: dict[str, threading.Lock] = {}
    runtime = ContextRuntime(
        _db_dsn_fn=_db_dsn_fn,
        _db_ready_fn=_db_ready_fn,
        _delivery_receipts_memory=_delivery_receipts_memory,
        _preferences_memory=_preferences_memory,
        audit_log_memory=audit_log_memory,
        db_bootstrap=db_bootstrap,
        enforce_rate_limit=enforce_rate_limit,
        hydrated_tenants=hydrated_tenants,
        memory_lock=memory_lock,
        notifications_memory=notifications_memory,
        subscribers=subscribers,
        tenant_hydration_locks=tenant_hydration_locks,
        unread_by_tenant_category=unread_by_tenant_category,
    )
    list_notifications.register(router, runtime)
    mark_notifications_read_all.register(router, runtime)
    return router
