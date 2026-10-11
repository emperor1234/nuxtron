"""Content/Media explicit runtime dependencies."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    _lock: Any
    _subscribers: dict[str, list[dict[str, Any]]]
    audit_log_memory: list[dict[str, Any]]
    enforce_rate_limit: Callable[[str, int, int], None]
    media_jobs_dlq_memory: list[dict[str, Any]]
    media_jobs_memory: list[dict[str, Any]]
