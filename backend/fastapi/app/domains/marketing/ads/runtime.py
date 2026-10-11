"""Marketing/Ads explicit runtime dependencies."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    _campaigns: Any
    _connectors: Any
    _forecasts: Any
    _scheduler: Any
    audit_log_memory: list[dict[str, Any]]
    enforce_rate_limit: Callable[..., None]
    lock: Any
    notifications_memory: list[dict[str, Any]]
    vendor_manager: Any
