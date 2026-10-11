"""Notifications/Delivery explicit runtime dependencies."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
import threading


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    _db_dsn_fn: Any
    _db_ready_fn: Any
    _delivery_receipts_memory: list[dict[str, Any]]
    _preferences_memory: list[dict[str, Any]]
    audit_log_memory: list[dict[str, Any]]
    db_bootstrap: Any
    enforce_rate_limit: Callable[[str, int, int], None]
    hydrated_tenants: set[str]
    memory_lock: Any
    notifications_memory: list[dict[str, Any]]
    subscribers: dict[str, list[dict[str, Any]]]
    tenant_hydration_locks: dict[str, threading.Lock]
    unread_by_tenant_category: dict[str, dict[str, int]]
