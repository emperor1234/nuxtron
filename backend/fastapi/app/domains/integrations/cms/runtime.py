"""Integrations/Cms explicit runtime dependencies."""

from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    audit_log_memory: list[dict[str, Any]]
    cms_attribution_automation_runs_memory: list[dict[str, Any]]
    cms_attribution_events_memory: list[dict[str, Any]]
    cms_attribution_links_memory: list[dict[str, Any]]
    cms_attribution_rules_memory: list[dict[str, Any]]
    cms_connections_memory: list[dict[str, Any]]
    cms_pages_memory: list[dict[str, Any]]
    cms_sync_log_memory: list[dict[str, Any]]
    email_sequences_memory: list[dict[str, Any]]
    enforce_rate_limit: Callable[[str, int, int], None]
    lock: Any
