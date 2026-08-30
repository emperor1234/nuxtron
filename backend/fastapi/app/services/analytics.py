"""Analytics Event Tracking Service

Extracted from legacy_main.py: PostHog, Matomo, Plausible event tracking.
"""

from __future__ import annotations

import os
from fastapi import Depends
from datetime import UTC, datetime
from typing import Annotated, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from ..deps import AuthContext

JsonObject = dict[str, object]
from ..deps import AuthContext, require_auth
AuthDep = Annotated[AuthContext, Depends(require_auth)]


# ── Memory Store References (set by legacy_main.py) ──────────
_posthog_events_memory = []
_matomo_events_memory = []
_plausible_events_memory = []
_rate_buckets = {}
_rate_lock = None
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit  # default; may be overwritten by set_memory_stores


def set_memory_stores(
    posthog_events_memory=None,
    matomo_events_memory=None,
    plausible_events_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
) -> None:
    """Inject memory store references from legacy_main.py."""
    global _posthog_events_memory, _matomo_events_memory, _plausible_events_memory
    global _rate_buckets, _rate_lock, _enforce_rate_limit
    if posthog_events_memory is not None:
        _posthog_events_memory = posthog_events_memory
    if matomo_events_memory is not None:
        _matomo_events_memory = matomo_events_memory
    if plausible_events_memory is not None:
        _plausible_events_memory = plausible_events_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit


# ── Helper: Generic event queuing ─────────────────────────────


def _queue_analytics_event(memory_store: list, tenant_id: str, status: str, reason: str, event: JsonObject) -> JsonObject:
    """Queue an analytics event to memory store and return result."""
    item: JsonObject = {
        'id': len(memory_store) + 1,
        'tenant_id': tenant_id,
        'status': status,
        'reason': reason,
        'event': event,
        'created_at': datetime.now(UTC).isoformat(),
    }
    memory_store.append(item)
    return {'status': 'ok', 'result': item}


def _send_success_result(tenant_id: str, provider: str, response_status: int, event_name: str) -> JsonObject:
    """Return success result for sent event."""
    return {
        'status': 'ok',
        'result': {
            'tenant_id': tenant_id,
            'delivery_status': 'sent',
            'provider': provider,
            'response_status': response_status,
            'event': event_name,
        },
    }


# ── PostHog ───────────────────────────────────────────────────


def capture_posthog_event(payload: PosthogCaptureRequest, auth: AuthDep) -> JsonObject:
    """Capture an event to PostHog."""
    _enforce_rate_limit(f'{auth.tenant_id}:analytics:posthog:capture', limit=180, window_seconds=60)

    base_url = os.getenv('POSTHOG_URL', '').rstrip('/')
    project_api_key = os.getenv('POSTHOG_PROJECT_API_KEY', '')

    event_body: JsonObject = {
        'event': payload.event,
        'properties': {
            **payload.properties,
            'tenant_id': auth.tenant_id,
        },
        'distinct_id': payload.distinct_id or auth.tenant_id,
    }

    if not base_url or not project_api_key:
        return _queue_analytics_event(
            _posthog_events_memory, auth.tenant_id, 'queued', 'PostHog not configured', event_body
        )

    request_body: JsonObject = {
        'api_key': project_api_key,
        **event_body,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/capture/', json=request_body)
            if response.is_success:
                return _send_success_result(auth.tenant_id, 'posthog', response.status_code, payload.event)
    except Exception as ex:
        message = f'PostHog request failed: {ex}'
        return _queue_analytics_event(_posthog_events_memory, auth.tenant_id, 'queued', message, event_body)

    return _queue_analytics_event(
        _posthog_events_memory, auth.tenant_id, 'queued', 'PostHog responded with non-success status', event_body
    )


# ── Matomo ────────────────────────────────────────────────────


def track_matomo_event(payload: MatomoTrackRequest, auth: AuthDep) -> JsonObject:
    """Track an event to Matomo."""
    _enforce_rate_limit(f'{auth.tenant_id}:analytics:matomo:track', limit=180, window_seconds=60)

    matomo_url = os.getenv('MATOMO_URL', '').rstrip('/')
    matomo_site_id = os.getenv('MATOMO_SITE_ID', '').strip()
    matomo_token = os.getenv('MATOMO_AUTH_TOKEN', '').strip()

    event_record: JsonObject = {
        'event_name': payload.event_name,
        'tenant_id': auth.tenant_id,
        'url': str(payload.url) if payload.url else 'http://localhost/studio',
        'action_name': payload.action_name,
        'properties': payload.properties,
    }

    if not matomo_url or not matomo_site_id:
        return _queue_analytics_event(
            _matomo_events_memory, auth.tenant_id, 'queued', 'Matomo not configured', event_record
        )

    params: dict[str, str] = {
        'idsite': matomo_site_id,
        'rec': '1',
        'apiv': '1',
        'url': str(event_record.get('url', '')),
        'action_name': str(event_record.get('action_name', '')),
        'e_c': 'nuxtron',
        'e_a': payload.event_name,
        'e_n': auth.tenant_id,
    }
    if matomo_token:
        params['token_auth'] = matomo_token

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(f'{matomo_url}/matomo.php', params=params)
            if response.is_success:
                return _send_success_result(auth.tenant_id, 'matomo', response.status_code, payload.event_name)
    except Exception as ex:
        message = f'Matomo request failed: {ex}'
        return _queue_analytics_event(_matomo_events_memory, auth.tenant_id, 'queued', message, event_record)

    return _queue_analytics_event(
        _matomo_events_memory, auth.tenant_id, 'queued', 'Matomo responded with non-success status', event_record
    )


# ── Plausible ─────────────────────────────────────────────────


def track_plausible_event(payload: PlausibleTrackRequest, auth: AuthDep) -> JsonObject:
    """Track an event to Plausible."""
    _enforce_rate_limit(f'{auth.tenant_id}:analytics:plausible:track', limit=180, window_seconds=60)

    plausible_url = os.getenv('PLAUSIBLE_API_URL', '').rstrip('/')
    plausible_api_key = os.getenv('PLAUSIBLE_API_KEY', '').strip()
    plausible_domain = os.getenv('PLAUSIBLE_SITE_DOMAIN', '').strip()

    event_body: JsonObject = {
        'name': payload.event_name,
        'url': str(payload.url) if payload.url else 'http://localhost/studio',
        'domain': plausible_domain or 'localhost',
        'props': {
            **payload.properties,
            'tenant_id': auth.tenant_id,
        },
    }

    if not plausible_url or not plausible_domain:
        return _queue_analytics_event(
            _plausible_events_memory, auth.tenant_id, 'queued', 'Plausible not configured', event_body
        )

    headers = {'Content-Type': 'application/json'}
    if plausible_api_key:
        headers['Authorization'] = f'Bearer {plausible_api_key}'

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{plausible_url}/api/event', headers=headers, json=event_body)
            if response.is_success:
                return _send_success_result(auth.tenant_id, 'plausible', response.status_code, payload.event_name)
    except Exception as ex:
        message = f'Plausible request failed: {ex}'
        return _queue_analytics_event(_plausible_events_memory, auth.tenant_id, 'queued', message, event_body)

    return _queue_analytics_event(
        _plausible_events_memory, auth.tenant_id, 'queued', 'Plausible responded with non-success status', event_body
    )


# ── Request Models (copied from legacy_main.py) ───────────────

from pydantic import BaseModel, Field, HttpUrl


class PosthogCaptureRequest(BaseModel):
    event: str = Field(min_length=1, max_length=120)
    distinct_id: str | None = Field(default=None, max_length=120)
    properties: dict[str, object] = Field(default_factory=dict)


class MatomoTrackRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=120)
    url: HttpUrl | None = None
    action_name: str = Field(default='Nuxtron Studio Event', min_length=1, max_length=160)
    properties: dict[str, object] = Field(default_factory=dict)


class PlausibleTrackRequest(BaseModel):
    event_name: str = Field(min_length=1, max_length=120)
    url: HttpUrl | None = None
    properties: dict[str, object] = Field(default_factory=dict)
