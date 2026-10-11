"""Automation/Workforce explicit runtime dependencies."""

from __future__ import annotations
from ....workforce_persistence import WorkforceDB
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    _db: WorkforceDB | None
    _lock: Any
    _metrics: Any
    _retry_queue: list[dict[str, Any]]
    audit_log_memory: list[dict[str, Any]]
    enforce_rate_limit: Callable[[str, int, int], None]
    feed_memory: list[dict[str, Any]]
    integrations_memory: list[dict[str, Any]]
    knowledge_memory: list[dict[str, Any]]
    missions_memory: list[dict[str, Any]]
    outcomes_memory: list[dict[str, Any]]
    profiles_memory: list[dict[str, Any]]
    schedules_memory: list[dict[str, Any]]
    tool_adapters: dict[str, Callable[..., Any]] = field(default_factory=dict)
