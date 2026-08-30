"""Health, metrics, and readiness probes.

Extracted from legacy_main.py. Routes depend on mutable app state
(_db_ready, memory stores, rate limiter) which are injected via the
``create_health_router`` factory so they can be replaced by DI later.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..deps import require_auth

from ..production_middleware import get_health_check_data, get_metrics_data

if TYPE_CHECKING:
    from collections.abc import Mapping

JsonObject = dict[str, object]


def create_health_router(
    *,
    get_db_ready: 'Callable[[], bool]',
    auth_security_memory: 'list[dict[str, Any]]',
    notifications_memory: 'list[dict[str, Any]]',
    all_stores_fn: 'Callable[[], dict[str, list[dict[str, Any]]]]',
    rate_buckets: 'Mapping[str, list[float]]',
    rate_lock: Any,
) -> APIRouter:
    """Build the health / metrics router with injected dependencies."""
    router = APIRouter(tags=['health'])

    @router.get('/healthz')
    def healthz() -> JsonObject:
        return {
            'status': 'ok',
            'service': 'fastapi',
            'db_ready': get_db_ready(),
            'security_strict_mode': os.getenv('SECURITY_STRICT_MODE', '0'),
        }

    @router.get('/health')
    def health_comprehensive() -> JsonObject:
        return get_health_check_data(get_db_ready(), auth_security_memory, notifications_memory)

    @router.get('/health/live')
    def health_liveness() -> JsonObject:
        return {'status': 'live', 'timestamp': datetime.now(UTC).isoformat()}

    @router.get('/health/ready', response_model=None)
    def health_readiness() -> JsonObject | JSONResponse:
        from ..database import get_db_session

        if not get_db_ready():
            return JSONResponse(
                status_code=503,
                content={'status': 'not-ready', 'reason': 'Service still initializing'},
            )
        try:
            from sqlalchemy import text
            with get_db_session() as session:
                session.execute(text('SELECT 1'))
        except Exception as exc:
            return JSONResponse(
                status_code=503,
                content={'status': 'not-ready', 'reason': 'Database connectivity check failed'},
            )
        return {'status': 'ready', 'timestamp': datetime.now(UTC).isoformat()}

    @router.get('/health/vaults', dependencies=[Depends(require_auth)])
    def health_vaults() -> JsonObject:
        try:
            from ..vault_config import get_vault_health
            vault_health = get_vault_health()
            if isinstance(vault_health, dict):
                if 'status' not in vault_health:
                    return {'status': 'ok', **vault_health}
                return vault_health  # type: ignore[return-value]
            return {
                'status': 'unavailable',
                'message': 'Vault health payload is invalid',
                'timestamp': datetime.now(UTC).isoformat(),
            }
        except ImportError:
            return {
                'status': 'unavailable',
                'message': 'Vault integration not available',
                'timestamp': datetime.now(UTC).isoformat(),
            }

    @router.get('/health/schema/unified-31', response_model=None)
    def health_schema_unified_31() -> JsonObject | JSONResponse:
        from ..production_middleware import _build_schema_unified_31_block
        block = _build_schema_unified_31_block(get_db_ready())
        if not block['ready']:
            block['reason'] = 'Schema unified_31_core not yet applied or DB not ready'
            return JSONResponse(status_code=503, content=dict(block))
        return block

    @router.get('/health/encryption', dependencies=[Depends(require_auth)])
    def health_encryption() -> JsonObject:
        try:
            from ..transparent_encryption import encryption_status
            status = encryption_status()
            return {'status': 'ok', **status, 'timestamp': datetime.now(UTC).isoformat()}
        except Exception as exc:
            return {
                'status': 'error',
                'message': str(exc),
                'timestamp': datetime.now(UTC).isoformat(),
            }

    @router.get('/metrics', dependencies=[Depends(require_auth)])
    def metrics() -> JsonObject:
        all_queues = all_stores_fn()
        return get_metrics_data(all_queues, rate_buckets, rate_lock)

    @router.get('/ai/ping')
    def ai_ping() -> JsonObject:
        return {'status': 'ok', 'service': 'ai-gateway', 'timestamp': datetime.now(UTC).isoformat()}

    return router
