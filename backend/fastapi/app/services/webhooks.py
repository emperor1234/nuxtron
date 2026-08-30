"""Webhook & Feature Flag Integrations Service

Extracted from legacy_main.py: n8n webhook trigger, Growthbook flag evaluation.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import UTC, datetime
from typing import Annotated, TYPE_CHECKING

import httpx
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

if TYPE_CHECKING:
    from ..deps import AuthContext

JsonObject = dict[str, object]
from ..deps import AuthContext, require_auth
AuthDep = Annotated[AuthContext, Depends(require_auth)]


CONTENT_TYPE_JSON = 'application/json'

# ── Memory Store References (set by legacy_main.py) ──────────
_n8n_jobs_memory = []
_growthbook_checks_memory = []
_rate_buckets = {}
_rate_lock = None
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit  # default; may be overwritten by set_memory_stores
_json_object = dict


def set_memory_stores(
    n8n_jobs_memory=None,
    growthbook_checks_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
    json_object=None,
) -> None:
    """Inject memory store references from legacy_main.py."""
    global _n8n_jobs_memory, _growthbook_checks_memory
    global _rate_buckets, _rate_lock, _enforce_rate_limit, _json_object
    if n8n_jobs_memory is not None:
        _n8n_jobs_memory = n8n_jobs_memory
    if growthbook_checks_memory is not None:
        _growthbook_checks_memory = growthbook_checks_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit
    if json_object is not None:
        _json_object = json_object


# ── n8n Webhook Trigger ───────────────────────────────────────


def trigger_n8n_webhook(payload: N8nWebhookTriggerRequest, auth: AuthDep) -> JsonObject:
    """Trigger an n8n webhook."""
    _enforce_rate_limit(f'{auth.tenant_id}:integrations:n8n:trigger', limit=120, window_seconds=60)

    webhook_url = os.getenv('N8N_WEBHOOK_URL', '').strip()
    token = os.getenv('N8N_WEBHOOK_TOKEN', '').strip()

    request_body: JsonObject = {
        'workflow': payload.workflow,
        'tenant_id': auth.tenant_id,
        'payload': payload.payload,
    }

    if not webhook_url:
        item: JsonObject = {
            'id': len(_n8n_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': 'n8n webhook not configured',
            'request': request_body,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _n8n_jobs_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {'Content-Type': CONTENT_TYPE_JSON}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(webhook_url, headers=headers, json=request_body)
            if response.is_success:
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'delivery_status': 'sent',
                        'provider': 'n8n',
                        'response_status': response.status_code,
                    },
                }
    except Exception as ex:
        message = f'n8n request failed: {ex}'
        item: JsonObject = {
            'id': len(_n8n_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'queued',
            'reason': message,
            'request': request_body,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _n8n_jobs_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_n8n_jobs_memory) + 1,
        'tenant_id': auth.tenant_id,
        'status': 'queued',
        'reason': 'n8n responded with non-success status',
        'request': request_body,
        'created_at': datetime.now(UTC).isoformat(),
    }
    _n8n_jobs_memory.append(item)
    return {'status': 'ok', 'result': item}


# ── Growthbook Flag Evaluation ────────────────────────────────


def evaluate_growthbook_flag(payload: GrowthbookEvaluateRequest, auth: AuthDep) -> JsonObject:
    """Evaluate a Growthbook feature flag."""
    _enforce_rate_limit(f'{auth.tenant_id}:flags:growthbook:evaluate', limit=180, window_seconds=60)

    base_url = os.getenv('GROWTHBOOK_API_URL', '').rstrip('/')
    client_key = os.getenv('GROWTHBOOK_CLIENT_KEY', '').strip()
    user_id = payload.user_id or auth.tenant_id

    fallback_bucket = sum(ord(ch) for ch in f'{auth.tenant_id}:{payload.feature_key}:{user_id}') % 100
    fallback_enabled = fallback_bucket < 50

    if not base_url or not client_key:
        item: JsonObject = {
            'id': len(_growthbook_checks_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'fallback',
            'feature_key': payload.feature_key,
            'enabled': fallback_enabled,
            'source': 'deterministic-local-rule',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _growthbook_checks_memory.append(item)
        return {'status': 'ok', 'result': item}

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(f'{base_url}/api/features/{client_key}')
            if response.is_success:
                data_obj = _json_object(response.json())
                features = _json_object((data_obj or {}).get('features', {})) or {}
                feature = _json_object(features.get(payload.feature_key, {})) or {}
                enabled = bool(feature.get('defaultValue', fallback_enabled))
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'feature_key': payload.feature_key,
                        'enabled': enabled,
                        'source': 'growthbook',
                    },
                }
    except Exception as ex:
        item: JsonObject = {
            'id': len(_growthbook_checks_memory) + 1,
            'tenant_id': auth.tenant_id,
            'status': 'fallback',
            'feature_key': payload.feature_key,
            'enabled': fallback_enabled,
            'source': f'fallback-after-error:{ex}',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _growthbook_checks_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_growthbook_checks_memory) + 1,
        'tenant_id': auth.tenant_id,
        'status': 'fallback',
        'feature_key': payload.feature_key,
        'enabled': fallback_enabled,
        'source': 'fallback-after-non-success',
        'created_at': datetime.now(UTC).isoformat(),
    }
    _growthbook_checks_memory.append(item)
    return {'status': 'ok', 'result': item}


# ── Request Models ────────────────────────────────────────────

# ── Signed Webhook Receiver ───────────────────────────────────


_WEBHOOK_PROVIDERS = {'github', 'stripe', 'generic'}


class WebhookAcknowledgeRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    event_type: str = Field(min_length=1, max_length=120)
    payload: dict[str, object] = Field(default_factory=dict)
    signature: str | None = Field(default=None, max_length=512)


def receive_webhook(
    provider: str,
    payload: WebhookAcknowledgeRequest,
    auth: AuthDep,
) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:webhooks:{provider}', limit=300, window_seconds=60)

    provider_lower = provider.lower()
    if provider_lower not in _WEBHOOK_PROVIDERS:
        raise Exception(f'Unknown webhook provider: {provider}. Supported: {sorted(_WEBHOOK_PROVIDERS)}')

    signature_valid = _validate_webhook_signature(provider_lower, payload)

    event: JsonObject = {
        'id': len(_webhook_events_memory) + 1,
        'tenant_id': auth.tenant_id,
        'provider': provider_lower,
        'event_type': payload.event_type,
        'payload': payload.payload,
        'signature_valid': signature_valid,
        'received_at': datetime.now(UTC).isoformat(),
    }
    _webhook_events_memory.append(event)

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'provider': provider_lower,
        'event_type': payload.event_type,
        'event_id': event['id'],
        'signature_valid': signature_valid,
        'received_at': event['received_at'],
    }


def list_webhook_events(auth: AuthDep) -> JsonObject:
    items: list[JsonObject] = [
        e for e in _webhook_events_memory if e.get('tenant_id') == auth.tenant_id
    ]
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'events': items}


# Add webhook events memory store
_webhook_events_memory = []


# ── Request Models ────────────────────────────────────────────

from pydantic import BaseModel, Field


class N8nWebhookTriggerRequest(BaseModel):
    workflow: str = Field(min_length=1, max_length=120)
    payload: dict[str, object] = Field(default_factory=dict)


class GrowthbookEvaluateRequest(BaseModel):
    feature_key: str = Field(min_length=1, max_length=120)
    user_id: str | None = Field(default=None, max_length=120)
    attributes: dict[str, object] = Field(default_factory=dict)


# ── Webhook Signature Validation ────────────────────────────

class WebhookAcknowledgeRequest(BaseModel):
    provider: str = Field(min_length=1, max_length=60)
    event_type: str = Field(min_length=1, max_length=120)
    payload: dict[str, object] = Field(default_factory=dict)
    signature: str | None = Field(default=None, max_length=512)
    headers: dict[str, str] = Field(default_factory=dict)


def _verify_github_signature(secret: str, raw_body: bytes, sig_header: str) -> bool:
    expected = 'sha256=' + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)


def _verify_stripe_signature(secret: str, raw_body: bytes, sig_header: str) -> bool:
    parts = {kv.split('=', 1)[0]: kv.split('=', 1)[1] for kv in sig_header.split(',') if '=' in kv}
    timestamp = parts.get('t', '')
    v1 = parts.get('v1', '')
    signed = f'{timestamp}.'.encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


def _ensure_signature_header(secret: str, sig_header: str, provider_name: str) -> None:
    if secret and not sig_header:
        raise HTTPException(
            status_code=400,
            detail=f'{provider_name} webhook signature header required when {provider_name.upper()} secret is set.',
        )


def _validate_github_webhook_signature(payload: WebhookAcknowledgeRequest) -> bool | None:
    secret = os.getenv('WEBHOOK_GITHUB_SECRET', '').strip()
    sig_header = payload.signature or ''
    _ensure_signature_header(secret, sig_header, 'GitHub')
    if secret and sig_header:
        raw = str(payload.payload).encode()
        return _verify_github_signature(secret, raw, sig_header)
    return None


def _validate_stripe_webhook_signature(payload: WebhookAcknowledgeRequest) -> bool | None:
    secret = os.getenv('WEBHOOK_STRIPE_SECRET', '').strip()
    sig_header = payload.signature or ''
    _ensure_signature_header(secret, sig_header, 'Stripe')
    if secret and sig_header:
        raw = str(payload.payload).encode()
        return _verify_stripe_signature(secret, raw, sig_header)
    return None


def _validate_generic_webhook_signature(payload: WebhookAcknowledgeRequest) -> bool | None:
    secret = os.getenv('WEBHOOK_GENERIC_SECRET', '').strip()
    sig_header = payload.signature or ''
    if secret and sig_header:
        raw = str(payload.payload).encode()
        expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig_header)
    return None


def _validate_webhook_signature(provider_lower: str, payload: WebhookAcknowledgeRequest) -> bool | None:
    if provider_lower == 'github':
        return _validate_github_webhook_signature(payload)
    if provider_lower == 'stripe':
        return _validate_stripe_webhook_signature(payload)
    if provider_lower == 'generic':
        return _validate_generic_webhook_signature(payload)
    return None
