"""Social/Inbox explicit runtime dependencies."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    _lock: Any
    audit_log_memory: list[dict[str, Any]]
    delivery_failures_memory: list[dict[str, Any]]
    delivery_replay_runs_memory: list[dict[str, Any]]
    enforce_rate_limit: Callable[[str, int, int], None]
    locks_memory: list[dict[str, Any]]
    messages_memory: list[dict[str, Any]]
    notes_memory: list[dict[str, Any]]
    saved_replies_memory: list[dict[str, Any]]
