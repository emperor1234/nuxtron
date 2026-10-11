"""Registers every HTTP surface onto a freshly created application."""

from __future__ import annotations

from fastapi import FastAPI

from .. import legacy_main as lg
from .. import memory_stores
from ..contexts.brand_management.wiring import router as brand_management_router
from ..rate_limiter import rate_limit_metrics_snapshot
from ..routers.content_generation_legacy import create_content_generation_router
from ..routers.finance_legacy import create_finance_router
from ..routers.frontend_compat import create_frontend_compat_router
from ..routers.health import create_health_router
from ..domains.content import generation as cg
from .route_compatibility import merge_frozen_http_route_overlaps


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
            rate_metrics_snapshot=rate_limit_metrics_snapshot,
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
            content_generation_note_telemetry=service.note_telemetry,
            persist_content_generation_job=lambda job: lg._persist_content_generation_job(job),
            find_content_generation_job=lambda job_id, tenant_id: lg._find_content_generation_job(job_id, tenant_id),
            content_generation_inflight_count=lambda tenant_id: lg._content_generation_inflight_count(tenant_id),
            content_generation_max_inflight=lambda: lg._content_generation_max_inflight(),
            content_generation_strict_production_mode=lambda: lg._content_generation_strict_production_mode(),
            content_generation_required_provider_state=lambda: lg._content_generation_required_provider_state(),
            content_generation_production_verification_payload=(
                lambda tenant_id: lg._content_generation_production_verification_payload(tenant_id)
            ),
            content_generation_job_retention_seconds=lambda: lg._content_generation_job_retention_seconds(),
            content_generation_job_terminal=lambda status: lg._content_generation_job_terminal(status),
            content_generation_job_expires_at=lambda job: lg._content_generation_job_expires_at(job),
            content_generation_prune_expired_terminal_jobs=(
                lambda: lg._content_generation_prune_expired_terminal_jobs()
            ),
            run_content_generation_job_if_needed=lambda job, auth: lg._run_content_generation_job_if_needed(job, auth),
            strict_no_mock_module_store_counts=lambda tenant_id: lg._strict_no_mock_module_store_counts(tenant_id),
            platform_status_payload=lambda auth: lg._platform_status_payload(auth),
            json_object=lg._json_object,
            env_bool=cg._env_bool,
            safe_int=cg._safe_int,
            is_production=lg._is_production,
        )
    )


def register_legacy_router_catalog(app: FastAPI) -> None:
    """Adapter for the not-yet-decomposed bulk registration module."""
    from ..router_registration import register_all_routers

    register_all_routers(app)


def register_brand_management_context(app: FastAPI) -> None:
    """Register the first domain-package pilot through the composition root."""
    app.include_router(brand_management_router)


def register_frontend_compatibility_router(app: FastAPI) -> None:
    app.include_router(create_frontend_compat_router())


def register_all_contexts(app: FastAPI) -> None:
    """Register every context's HTTP surface, in contract order, exactly once."""
    register_health_router(app)
    register_finance_router(app)
    register_content_generation_router(app)
    register_legacy_router_catalog(app)
    register_brand_management_context(app)
    register_frontend_compatibility_router(app)
    merge_frozen_http_route_overlaps(app)
