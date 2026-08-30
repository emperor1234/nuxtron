"""Content Generation Service

Extracted from legacy_main.py: content generation configuration, telemetry,
job lifecycle management, and verification helpers.

Stateful helpers are methods on ContentGenerationService. Module-level
functions are stateless utilities.
"""

from __future__ import annotations

import logging
import os
import threading
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel

from ..config import env_bool

logger = logging.getLogger('uvicorn.error')

JsonObject = dict[str, object]

# ── Stateless Utilities ────────────────────────────────────


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {'1', 'true', 'yes', 'on'}


def _safe_int(value: object, default: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _parse_iso_datetime(value: object | None) -> datetime | None:
    if not value:
        return None
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _redis_sync_client() -> object | None:
    return None


def _content_generation_strict_production_mode() -> bool:
    explicit = os.getenv('CONTENT_GENERATION_STRICT_PRODUCTION')
    if explicit is not None:
        return explicit.strip().lower() in {'1', 'true', 'yes', 'on'}
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def _content_generation_required_provider_state() -> tuple[bool, dict[str, bool]]:
    from .ai_providers import _resolve_provider_api_key

    text_ready = bool(
        _resolve_provider_api_key('openai')
        or _resolve_provider_api_key('anthropic')
        or _resolve_provider_api_key('google_vertex')
    )
    image_ready = bool(
        _resolve_provider_api_key('stability_ai')
        or _resolve_provider_api_key('google_vertex')
    )
    allow_oss_voice = _env_bool('CONTENT_GENERATION_ALLOW_OSS_VOICE_IN_STRICT', True)
    voice_ready = bool(os.getenv('ELEVENLABS_API_KEY', '').strip()) or allow_oss_voice
    video_ready = bool(
        os.getenv('REPLICATE_API_TOKEN', '').strip()
        or os.getenv('GOOGLE_VERTEX_PROJECT_ID', '').strip()
    )
    checks = {
        'text': text_ready,
        'image': image_ready,
        'voice': voice_ready,
        'video': video_ready,
    }
    return all(checks.values()), checks


def _content_generation_job_retention_seconds() -> int:
    return max(30, _safe_int(os.getenv('CONTENT_GENERATION_JOB_RETENTION_SECONDS', '86400'), 86400))


def _content_generation_job_terminal(status: object) -> bool:
    return str(status) in {'completed', 'failed', 'cancelled'}


def _content_generation_max_inflight() -> int:
    return max(1, _safe_int(os.getenv('CONTENT_GENERATION_MAX_INFLIGHT_PER_TENANT', '3'), 3))


# ── Stateful Service ──────────────────────────────────────


class ContentGenerationService:
    """Manages content generation state: telemetry, job store, locks."""

    def __init__(self) -> None:
        self.jobs_memory: list[JsonObject] = []
        self.jobs_lock = threading.Lock()
        self.telemetry_lock = threading.Lock()
        self.telemetry: JsonObject = {
            'strict_rejections_total': 0,
            'strict_rejections_by_reason': {},
            'fallback_attempts_total': 0,
            'fallback_attempts_by_reason': {},
            'timeout_failures_total': 0,
            'updated_at': None,
        }

    def note_telemetry(self, counter_key: str, reason: str | None = None) -> None:
        with self.telemetry_lock:
            current = _safe_int(self.telemetry.get(counter_key), 0)
            self.telemetry[counter_key] = current + 1
            if reason and counter_key == 'strict_rejections_total':
                by_reason = self.telemetry.setdefault('strict_rejections_by_reason', {})
                if isinstance(by_reason, dict):
                    by_reason[reason] = _safe_int(by_reason.get(reason), 0) + 1
            if reason and counter_key == 'fallback_attempts_total':
                by_reason = self.telemetry.setdefault('fallback_attempts_by_reason', {})
                if isinstance(by_reason, dict):
                    by_reason[reason] = _safe_int(by_reason.get(reason), 0) + 1
            self.telemetry['updated_at'] = datetime.now(UTC).isoformat()

    def job_expires_at(self, job: JsonObject) -> datetime | None:
        if not _content_generation_job_terminal(job.get('status')):
            return None
        base = (
            _parse_iso_datetime(job.get('completed_at'))
            or _parse_iso_datetime(job.get('updated_at'))
            or _parse_iso_datetime(job.get('created_at'))
        )
        if base is None:
            return None
        return base + timedelta(seconds=_content_generation_job_retention_seconds())

    def prune_expired_terminal_jobs(self, now: datetime | None = None) -> None:
        check_time = now or datetime.now(UTC)
        with self.jobs_lock:
            self.jobs_memory[:] = [
                job for job in self.jobs_memory
                if (
                    (self.job_expires_at(job) is None)
                    or ((self.job_expires_at(job) or check_time) > check_time)
                )
            ]

    def persist_job(self, job: JsonObject) -> JsonObject:
        with self.jobs_lock:
            for index, existing in enumerate(self.jobs_memory):
                if str(existing.get('job_id', '')) == str(job.get('job_id', '')):
                    self.jobs_memory[index] = job
                    return job
            self.jobs_memory.append(job)
        return job

    def find_job(self, job_id: str, tenant_id: str) -> JsonObject | None:
        self.prune_expired_terminal_jobs()
        with self.jobs_lock:
            for job in self.jobs_memory:
                if str(job.get('job_id', '')) == job_id and str(job.get('tenant_id', '')) == tenant_id:
                    return job
        return None

    def inflight_count(self, tenant_id: str, *, exclude_job_id: str | None = None) -> int:
        with self.jobs_lock:
            return sum(
                1
                for job in self.jobs_memory
                if str(job.get('tenant_id', '')) == tenant_id
                and str(job.get('job_id', '')) != str(exclude_job_id or '')
                and str(job.get('status', '')) in {'pending', 'running'}
            )

    def production_verification_payload(self, tenant_id: str) -> tuple[JsonObject, bool]:
        ready, checks = _content_generation_required_provider_state()
        with self.telemetry_lock:
            counters = dict(self.telemetry)
        criteria: list[JsonObject] = [
            {'id': 'providers-ready', 'pass': ready, 'details': checks},
            {
                'id': 'no-fallback-attempts',
                'pass': _safe_int(counters.get('fallback_attempts_total'), 0) == 0,
                'details': {'fallback_attempts_total': _safe_int(counters.get('fallback_attempts_total'), 0)},
            },
            {
                'id': 'no-timeout-failures',
                'pass': _safe_int(counters.get('timeout_failures_total'), 0) == 0,
                'details': {'timeout_failures_total': _safe_int(counters.get('timeout_failures_total'), 0)},
            },
        ]
        passed = all(bool(item.get('pass')) for item in criteria)
        return {
            'status': 'ok' if passed else 'error',
            'tenant_id': tenant_id,
            'verification': {
                'passed': passed,
                'criteria': criteria,
            },
            'counters': counters,
        }, passed

    def run_job_if_needed(self, job: JsonObject, auth: object, generate_content_fn: object) -> None:
        """Execute a pending content generation job synchronously."""
        if str(job.get('status', '')) != 'pending' or bool(job.get('cancel_requested', False)):
            return
        now_iso = datetime.now(UTC).isoformat()
        job['status'] = 'running'
        job['stage'] = 'generating'
        job['progress_pct'] = 25
        job['started_at'] = now_iso
        job['updated_at'] = now_iso
        self.persist_job(job)
        try:
            payload_data = dict(job.get('payload_data', {})) or {}
            from .content_generation_service import ContentRequest
            built_payload = ContentRequest.model_validate(payload_data)
            result = generate_content_fn(built_payload, auth)
            complete_at = datetime.now(UTC).isoformat()
            job['status'] = 'completed'
            job['stage'] = 'completed'
            job['progress_pct'] = 100
            job['result'] = result
            job['error'] = None
            job['completed_at'] = complete_at
            job['updated_at'] = complete_at
        except Exception as exc:
            failed_at = datetime.now(UTC).isoformat()
            job['status'] = 'failed'
            job['stage'] = 'failed'
            job['progress_pct'] = 100
            job['result'] = None
            job['error'] = str(exc)
            job['completed_at'] = failed_at
            job['updated_at'] = failed_at
        self.persist_job(job)


# ── Module-level shims for backward compatibility ────────────
# These wrap ContentGenerationService methods so legacy_main code
# that calls _persist_content_generation_job(job) etc. still works
# during the gradual migration.

_cg_svc: ContentGenerationService | None = None


def _get_cg_svc() -> ContentGenerationService:
    global _cg_svc
    if _cg_svc is None:
        _cg_svc = ContentGenerationService()
    return _cg_svc


def _persist_content_generation_job(job: JsonObject) -> JsonObject:
    return _get_cg_svc().persist_job(job)


def _find_content_generation_job(job_id: str, tenant_id: str) -> JsonObject | None:
    return _get_cg_svc().find_job(job_id, tenant_id)


def _content_generation_inflight_count(tenant_id: str, *, exclude_job_id: str | None = None) -> int:
    return _get_cg_svc().inflight_count(tenant_id, exclude_job_id=exclude_job_id)


def _content_generation_note_telemetry(counter_key: str, reason: str | None = None) -> None:
    _get_cg_svc().note_telemetry(counter_key, reason)


def _content_generation_job_expires_at(job: JsonObject) -> datetime | None:
    return _get_cg_svc().job_expires_at(job)


def _content_generation_prune_expired_terminal_jobs(now: datetime | None = None) -> None:
    _get_cg_svc().prune_expired_terminal_jobs(now)
