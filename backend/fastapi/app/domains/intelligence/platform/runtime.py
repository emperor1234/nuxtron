"""Intelligence/Platform explicit runtime dependencies."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    audit_log_memory: list[dict[str, Any]]
    enforce_rate_limit: Any
    seo_jobs_fn: Any | None
