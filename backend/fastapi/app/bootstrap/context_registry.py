"""Registers every HTTP surface onto a freshly created application.

Registration order is part of the contract: a handful of paths are served by
two routers and the first registration wins, so the order below must match the
historical composition order exactly. Bulk router registration still lives in
``router_registration`` and is reached through a named adapter while that
module is being decomposed.
"""

from __future__ import annotations

from fastapi import FastAPI

from .. import legacy_main as lg
from .. import memory_stores
from ..rate_limiter import get_rate_buckets, get_rate_lock
from ..routers.content_generation_legacy import create_content_generation_router
from ..routers.finance_legacy import create_finance_router
from ..routers.frontend_compat import create_frontend_compat_router
from ..routers.health import create_health_router
from ..services import content_generation as cg
from ..services.content_generation_service import ContentRequest
from ..services.platform import _platform_status_payload


def register_shared_application_state(app: FastAPI) -> None:
    """Expose the stores that request-scoped security telemetry writes to."""
    app.state.api_usage_audit = lg._api_usage_audit_memory
    app.state.siem_cases = lg._siem_cases_memory
    app.state.ira_events = lg._ira_events_memory


def register_health_router(app: FastAPI) -> None:
    app.include_router(
        create_health_router(
            get_db_ready=lambda: bool(lg._db_ready),
            auth_security_memory=memory_stores.auth_security,
            notifications_memory=memory_stores.notifications,
            all_stores_fn=memory_stores.get_all_stores,
            rate_buckets=get_rate_buckets(),
            rate_lock=get_rate_lock(),
        )
    )


def register_finance_router(app: FastAPI) -> None:
    app.include_router(
        create_finance_router(
            enforce_rate_limit=lg._enforce_rate_limit,
            accounting_integrations_memory=memory_stores.accounting_integrations,
            accounting_exports_memory=memory_stores.accounting_exports,
            record_audit=lg._record_audit,
        )
    )


def register_content_generation_router(app: FastAPI) -> None:
    service = cg._get_cg_svc()
    app.include_router(
        create_content_generation_router(
            content_generations_memory=memory_stores.trend_content_generations,
            content_generation_jobs_memory=service.jobs_memory,
            content_generation_jobs_lock=service.jobs_lock,
            content_generation_telemetry_lock=service.telemetry_lock,
            content_generation_telemetry=service.telemetry,
            persist_content_generation_job=cg._persist_content_generation_job,
            find_content_generation_job=cg._find_content_generation_job,
            content_generation_inflight_count=cg._content_generation_inflight_count,
            content_generation_max_inflight=cg._content_generation_max_inflight,
            content_generation_strict_production_mode=cg._content_generation_strict_production_mode,
            content_generation_required_provider_state=cg._content_generation_required_provider_state,
            content_generation_production_verification_payload=service.production_verification_payload,
            content_generation_job_retention_seconds=cg._content_generation_job_retention_seconds,
            content_generation_job_terminal=cg._content_generation_job_terminal,
            content_generation_job_expires_at=cg._content_generation_job_expires_at,
            content_generation_prune_expired_terminal_jobs=cg._content_generation_prune_expired_terminal_jobs,
            run_content_generation_job_if_needed=lg._run_content_generation_job_if_needed,
            strict_no_mock_module_store_counts=lg._strict_no_mock_module_store_counts,
            platform_status_payload=_platform_status_payload,
            json_object=lg._json_object,
            env_bool=cg._env_bool,
            safe_int=cg._safe_int,
            is_production=lg._is_production,
            content_request_model=ContentRequest,
        )
    )


def register_legacy_router_catalog(app: FastAPI) -> None:
    """Adapter for the not-yet-decomposed bulk registration module."""
    from ..router_registration import register_all_routers

    register_all_routers(app)


def register_frontend_compatibility_router(app: FastAPI) -> None:
    app.include_router(create_frontend_compat_router())


def register_all_contexts(app: FastAPI) -> None:
    """Register every context's HTTP surface, in contract order, exactly once."""
    register_health_router(app)
    register_finance_router(app)
    register_content_generation_router(app)
    register_legacy_router_catalog(app)
    register_frontend_compatibility_router(app)
