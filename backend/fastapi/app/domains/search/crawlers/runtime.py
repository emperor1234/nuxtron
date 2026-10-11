"""Search/Crawlers explicit runtime dependencies."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    _lock: Any
    audit_log_memory: list[dict[str, Any]]
    audit_results_memory: list[dict[str, Any]]
    automation_runs_memory: list[dict[str, Any]]
    automation_schedules_memory: list[dict[str, Any]]
    crawler_events_memory: list[dict[str, Any]]
    crawler_rules_memory: list[dict[str, Any]]
    enforce_rate_limit: Callable[[str, int, int], None]
    sites_memory: list[dict[str, Any]]
    ssr_cache_memory: list[dict[str, Any]]
