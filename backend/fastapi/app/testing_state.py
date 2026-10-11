"""Canonical process-state reset used by the FastAPI test suite."""

from __future__ import annotations

from . import generated_asset_store, memory_stores
from .bootstrap.infrastructure import wire_process_infrastructure
from .rate_limiter import reset_rate_limits_for_tests
from .vault.hashicorp_vault import reset_vault_client_for_tests
from .vault.secrets_manager import reset_secrets_manager_for_tests


def reset_process_state_for_tests(*, include_redis: bool = False) -> None:
    """Reset canonical owners while preserving compatibility aliases."""
    infrastructure = wire_process_infrastructure()
    # Preserve the historical per-test reset scope. Clearing every canonical
    # process store broke suites whose module fixtures intentionally seed stores
    # outside the health catalog once for a group of tests.
    for store in memory_stores.get_all_stores().values():
        store.clear()
    generated_asset_store.reset_generated_assets_for_tests()
    service = infrastructure.content_generation
    with service.jobs_lock:
        service.jobs_memory.clear()
    with service.telemetry_lock:
        service.telemetry.clear()
        service.telemetry.update(
            {
                'strict_rejections_total': 0,
                'strict_rejections_by_reason': {},
                'fallback_attempts_total': 0,
                'fallback_attempts_by_reason': {},
                'timeout_failures_total': 0,
                'updated_at': None,
            }
        )
    reset_secrets_manager_for_tests()
    reset_vault_client_for_tests()
    reset_rate_limits_for_tests(include_redis=include_redis)
