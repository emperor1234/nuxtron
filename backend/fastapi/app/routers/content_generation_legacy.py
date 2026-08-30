"""Content generation and library routes.

Extracted from legacy_main.py. Routes depend on mutable app state
(memory stores, locks, helper functions) which are injected via the
``create_content_generation_router`` factory.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from ..deps import AuthContext, require_auth

if TYPE_CHECKING:
    from collections.abc import Callable
    from threading import Lock

    from pydantic import BaseModel as PydanticBaseModel

JsonObject = dict[str, object]


def create_content_generation_router(
    *,
    content_generations_memory: list[dict[str, Any]],
    content_generation_jobs_memory: list[dict[str, Any]],
    content_generation_jobs_lock: 'Lock',
    content_generation_telemetry_lock: 'Lock',
    content_generation_telemetry: dict[str, int],
    persist_content_generation_job: 'Callable[[dict[str, Any]], dict[str, Any]]',
    find_content_generation_job: 'Callable[[str, str], dict[str, Any] | None]',
    content_generation_inflight_count: 'Callable[[str], int]',
    content_generation_max_inflight: 'Callable[[], int]',
    content_generation_strict_production_mode: 'Callable[[], bool]',
    content_generation_required_provider_state: 'Callable[[], tuple[bool, dict[str, bool]]]',
    content_generation_production_verification_payload: 'Callable[[str], tuple[dict[str, Any], bool]]',
    content_generation_job_retention_seconds: 'Callable[[], int]',
    content_generation_job_terminal: 'Callable[[object], bool]',
    content_generation_job_expires_at: 'Callable[[dict[str, Any]], datetime | None]',
    content_generation_prune_expired_terminal_jobs: 'Callable[[], None]',
    run_content_generation_job_if_needed: 'Callable[[dict[str, Any], AuthContext], None]',
    strict_no_mock_module_store_counts: 'Callable[[str], dict[str, int]]',
    platform_status_payload: 'Callable[[AuthContext], dict[str, Any]]',
    json_object: 'Callable[[object], dict[str, Any] | None]',
    env_bool: 'Callable[[str, bool], bool]',
    safe_int: 'Callable[[object, int], int]',
    is_production: 'Callable[[], bool]',
    content_request_model: type,
) -> APIRouter:
    """Build the content generation router with injected dependencies."""
    router = APIRouter(tags=['content-generation'])

    @router.get('/content/library')
    def get_content_library(auth: AuthContext = Depends(require_auth)) -> JsonObject:
        items = [
            item for item in content_generations_memory
            if str(item.get('tenant_id', '')) == auth.tenant_id
        ]
        items.sort(key=lambda entry: str(entry.get('created_at', '')), reverse=True)
        return {
            'status': 'ok',
            'count': len(items),
            'items': [
                {
                    'generation_id': str(item.get('generation_id', '')),
                    'topic': str(item.get('topic', '')),
                    'channel': str(item.get('channel', '')),
                    'headline': str(item.get('headline', '')),
                    'created_at': item.get('created_at'),
                }
                for item in items
            ],
        }

    @router.get('/content/library/{generation_id}')
    def get_content_library_item(generation_id: str, auth: AuthContext = Depends(require_auth)) -> JsonObject:
        item = next(
            (
                row for row in content_generations_memory
                if str(row.get('tenant_id', '')) == auth.tenant_id and str(row.get('generation_id', '')) == generation_id
            ),
            None,
        )
        if item is None:
            raise HTTPException(status_code=404, detail='Content generation record not found.')
        return {'status': 'ok', 'item': item}

    @router.get('/content/generate/telemetry')
    def get_content_generation_telemetry(auth: AuthContext = Depends(require_auth)) -> JsonObject:
        del auth
        with content_generation_telemetry_lock:
            counters = dict(content_generation_telemetry)
        return {'status': 'ok', 'counters': counters}

    @router.get('/content/generate/preflight/strict', response_model=None)
    def content_generation_strict_preflight(auth: AuthContext = Depends(require_auth)) -> JsonObject | JSONResponse:
        del auth
        strict_mode = content_generation_strict_production_mode()
        ready, checks = content_generation_required_provider_state()
        payload: JsonObject = {
            'status': 'ok' if (not strict_mode or ready) else 'error',
            'strict_mode_enabled': strict_mode,
            'ready': ready,
            'checks': checks,
        }
        if strict_mode and not ready:
            return JSONResponse(status_code=503, content=payload)
        return payload

    @router.get('/content/generate/production/verify', response_model=None)
    def content_generation_production_verify(auth: AuthContext = Depends(require_auth)) -> JsonObject | JSONResponse:
        payload, passed = content_generation_production_verification_payload(auth.tenant_id)
        if not passed:
            return JSONResponse(status_code=503, content=payload)
        return payload

    @router.get('/production/no-mock/verify', response_model=None)
    def strict_no_mock_verify(auth: AuthContext = Depends(require_auth)) -> JsonObject | JSONResponse:
        strict_no_mock = env_bool('NUXTRON_STRICT_NO_MOCK', is_production())
        content_payload, content_ok = content_generation_production_verification_payload(auth.tenant_id)
        platform_payload = platform_status_payload(auth)
        fallback_buffers = json_object(platform_payload.get('fallback_buffers', {})) or {}
        fallback_hot = bool(fallback_buffers.get('any_buffer_hot', False))

        module_counts = strict_no_mock_module_store_counts(auth.tenant_id)
        class_breakdown: dict[str, JsonObject] = {
            'content_pipeline': {'total': module_counts.get('scheduled_posts', 0) + module_counts.get('content_approval_requests', 0) + module_counts.get('trend_signals', 0)},
            'social_operations': {'total': module_counts.get('social_accounts', 0) + module_counts.get('smart_inbox_messages', 0) + module_counts.get('social_listening', 0) + module_counts.get('reviews', 0)},
            'distribution_surface': {'total': module_counts.get('influencers', 0) + module_counts.get('advocacy_campaigns', 0) + module_counts.get('linkinbio_pages', 0) + module_counts.get('ads_campaigns', 0)},
        }
        threshold = max(0, safe_int(os.getenv('NUXTRON_STRICT_NO_MOCK_MAX_MODULE_BUFFER_ITEMS', '100'), 100))
        class_overflow = {
            key: value
            for key, value in class_breakdown.items()
            if safe_int(value.get('total'), 0) > threshold
        }

        criteria: list[JsonObject] = [
            {
                'id': 'content-generation-production-verify',
                'pass': bool(content_ok),
                'details': content_payload,
            },
            {
                'id': 'fallback-buffers-empty',
                'pass': not fallback_hot,
                'details': fallback_buffers,
            },
            {
                'id': 'critical-module-buffers-below-limit',
                'pass': len(class_overflow) == 0,
                'details': {
                    'threshold': threshold,
                    'class_breakdown': class_breakdown,
                    'class_overflow': class_overflow,
                },
            },
        ]

        passed = all(bool(item.get('pass')) for item in criteria)
        source = 'verify'
        route_family = 'platform'
        if fallback_hot:
            source = 'fallback-buffers'
            route_family = 'fallback-buffers'
        elif class_overflow:
            source = 'critical-modules'
            route_family = 'critical-modules'

        payload: JsonObject = {
            'status': 'ok' if passed else 'error',
            'strict_no_mock_mode_enabled': strict_no_mock,
            'strict_no_mock_mode': strict_no_mock,
            'fallback_blocked': not passed,
            'source': source,
            'route_family': route_family,
            'verification': {
                'passed': passed,
                'criteria': criteria,
            },
            'platform': {
                **platform_payload,
                'critical_module_buffers': {
                    'class_breakdown': class_breakdown,
                    'class_overflow': class_overflow,
                },
            },
        }

        if strict_no_mock and not passed:
            return JSONResponse(status_code=503, content=payload)
        return payload

    @router.post('/content/generate/async', status_code=202)
    def submit_content_generation_job(payload: content_request_model, auth: AuthContext = Depends(require_auth)) -> JsonObject:
        if content_generation_inflight_count(auth.tenant_id) >= content_generation_max_inflight():
            raise HTTPException(status_code=429, detail='Too many in-flight content generation jobs.')

        now_iso = datetime.now(UTC).isoformat()
        job_id = f"cgj-{uuid.uuid4().hex[:12]}"
        job: JsonObject = {
            'job_id': job_id,
            'tenant_id': auth.tenant_id,
            'status': 'pending',
            'progress_pct': 0,
            'stage': 'queued',
            'created_at': now_iso,
            'updated_at': now_iso,
            'started_at': None,
            'completed_at': None,
            'result': None,
            'error': None,
            'cancel_requested': False,
            'payload_data': payload.model_dump(mode='python'),
        }
        persist_content_generation_job(job)
        return {
            'status': 'accepted',
            'job_id': job_id,
            'poll_url': f'/content/generate/jobs/{job_id}',
        }

    @router.get('/content/generate/jobs/{job_id}')
    def get_content_generation_job(job_id: str, auth: AuthContext = Depends(require_auth)) -> JsonObject:
        job = find_content_generation_job(job_id, auth.tenant_id)
        if job is None:
            raise HTTPException(status_code=404, detail='Content generation job not found.')

        enforce_timeouts = env_bool('CONTENT_GENERATION_ENFORCE_JOB_TIMEOUTS', False)
        max_runtime = max(30, safe_int(os.getenv('CONTENT_GENERATION_JOB_MAX_RUNTIME_SECONDS', '1800'), 1800))
        if enforce_timeouts and str(job.get('status', '')) == 'running':
            started_at_raw = job.get('started_at')
            started_at = None
            if started_at_raw:
                try:
                    parsed = datetime.fromisoformat(str(started_at_raw))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=UTC)
                    started_at = parsed.astimezone(UTC)
                except ValueError:
                    pass
            if started_at and (datetime.now(UTC) - started_at).total_seconds() > max_runtime:
                now_iso = datetime.now(UTC).isoformat()
                job['status'] = 'failed'
                job['stage'] = 'timeout'
                job['progress_pct'] = 100
                job['completed_at'] = now_iso
                job['updated_at'] = now_iso
                job['error'] = f'Job exceeded max runtime ({max_runtime}s).'
                persist_content_generation_job(job)

        if str(job.get('status', '')) == 'pending':
            run_content_generation_job_if_needed(job, auth)

        job = find_content_generation_job(job_id, auth.tenant_id)
        if job is None:
            raise HTTPException(status_code=404, detail='Content generation job not found.')
        return {'status': 'ok', 'job': job}

    @router.delete('/content/generate/jobs/{job_id}')
    def cancel_content_generation_job(job_id: str, auth: AuthContext = Depends(require_auth)) -> JsonObject:
        job = find_content_generation_job(job_id, auth.tenant_id)
        if job is None:
            raise HTTPException(status_code=404, detail='Content generation job not found.')
        if str(job.get('status', '')) not in {'pending', 'running'}:
            return {'status': 'ok', 'job': job}
        now_iso = datetime.now(UTC).isoformat()
        job['cancel_requested'] = True
        job['status'] = 'cancelled'
        job['stage'] = 'cancelled'
        job['progress_pct'] = 100
        job['completed_at'] = now_iso
        job['updated_at'] = now_iso
        persist_content_generation_job(job)
        return {'status': 'ok', 'job': job}

    @router.post('/content/generate/jobs/{job_id}/retry')
    def retry_content_generation_job(job_id: str, auth: AuthContext = Depends(require_auth)) -> JsonObject:
        job = find_content_generation_job(job_id, auth.tenant_id)
        if job is None:
            raise HTTPException(status_code=404, detail='Content generation job not found.')
        if str(job.get('status', '')) not in {'failed', 'cancelled'}:
            raise HTTPException(status_code=409, detail='Only failed or cancelled jobs can be retried.')
        if content_generation_inflight_count(auth.tenant_id) >= content_generation_max_inflight():
            raise HTTPException(status_code=429, detail='Too many in-flight content generation jobs.')
        now_iso = datetime.now(UTC).isoformat()
        job['status'] = 'pending'
        job['stage'] = 'queued'
        job['progress_pct'] = 0
        job['error'] = None
        job['result'] = None
        job['cancel_requested'] = False
        job['started_at'] = None
        job['completed_at'] = None
        job['updated_at'] = now_iso
        persist_content_generation_job(job)
        return {'status': 'ok', 'job': job}

    @router.get('/content/generate/jobs')
    def list_content_generation_jobs(
        status: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=200),
        auth: AuthContext = Depends(require_auth),
    ) -> JsonObject:
        allowed = {'pending', 'running', 'completed', 'failed', 'cancelled'}
        if status is not None and status not in allowed:
            raise HTTPException(status_code=400, detail='Invalid status filter.')

        content_generation_prune_expired_terminal_jobs()
        with content_generation_jobs_lock:
            items = [
                job.copy()
                for job in content_generation_jobs_memory
                if str(job.get('tenant_id', '')) == auth.tenant_id and (status is None or str(job.get('status', '')) == status)
            ]
        items.sort(key=lambda item: str(item.get('updated_at', item.get('created_at', ''))), reverse=True)
        items = items[:limit]
        for item in items:
            expires_at = content_generation_job_expires_at(item)
            item['is_terminal'] = content_generation_job_terminal(item.get('status'))
            item['expires_at'] = expires_at.isoformat() if expires_at else None
        return {
            'status': 'ok',
            'items': items,
            'retention': {
                'terminal_seconds': content_generation_job_retention_seconds(),
            },
        }

    @router.get('/content/generate/jobs/{job_id}/stream')
    def stream_content_generation_job(
        job_id: str,
        api_key: str = Query(default=''),
        tenant_id: str = Query(default=''),
    ) -> StreamingResponse:
        import hmac as _hmac

        expected = os.getenv('FASTAPI_API_KEY', 'change-this-fastapi-key').strip()
        if not api_key or not tenant_id or not _hmac.compare_digest(api_key, expected):
            raise HTTPException(status_code=401, detail='Invalid stream credentials.')

        job = find_content_generation_job(job_id, tenant_id)
        if job is None:
            raise HTTPException(status_code=404, detail='Content generation job not found.')

        def _event_stream() -> object:
            snapshot = json.dumps({'payload': job}, separators=(',', ':'))
            yield f"event: content-job.snapshot\ndata: {snapshot}\n\n"
            if content_generation_job_terminal(job.get('status')):
                terminated = json.dumps({'payload': job}, separators=(',', ':'))
                yield f"event: content-job.terminated\ndata: {terminated}\n\n"

        return StreamingResponse(_event_stream(), media_type='text/event-stream')

    return router
