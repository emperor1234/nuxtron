"""Seo/Platform explicit runtime dependencies."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    _DEFAULT_NEXT_STEPS: Any
    _MODULE_NEXT_STEPS: dict[str, list[dict[str, str]]]
    _PERF_ASYNC_TEST_JOBS: dict[str, dict[str, Any]]
    _PERF_BROWSER_PROFILES: list[dict[str, Any]]
    _PERF_TEST_LOCATIONS: list[dict[str, Any]]
    _db_dsn_fn: Any
    _db_initialized: Any
    _db_ready_fn: Any
    _job_lock: Any
    _job_store: dict[str, dict[str, Any]]
    audit_log_memory: list[dict[str, Any]]
    enforce_rate_limit: Any
    seo_analyses_memory: list[dict[str, Any]]
