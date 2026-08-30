"""CRM Integrations Service

Extracted from legacy_main.py: SuiteCRM, RefferQ integrations.
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
_suitecrm_jobs_memory = []
_refferq_jobs_memory = []
_rate_buckets = {}
_rate_lock = None
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit  # default; may be overwritten by set_memory_stores


def set_memory_stores(
    suitecrm_jobs_memory=None,
    refferq_jobs_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
) -> None:
    """Inject memory store references from legacy_main.py."""
    global _suitecrm_jobs_memory, _refferq_jobs_memory
    global _rate_buckets, _rate_lock, _enforce_rate_limit
    if suitecrm_jobs_memory is not None:
        _suitecrm_jobs_memory = suitecrm_jobs_memory
    if refferq_jobs_memory is not None:
        _refferq_jobs_memory = refferq_jobs_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit


# ── Helper: Generic CRM queuing ───────────────────────────────


def _queue_crm_job(memory_store: list, tenant_id: str, status: str, reason: str, payload: JsonObject, payload_key: str) -> JsonObject:
    """Queue a CRM job to memory store and return result."""
    item: JsonObject = {
        'id': len(memory_store) + 1,
        'tenant_id': tenant_id,
        'status': status,
        'reason': reason,
        payload_key: payload,
        'created_at': datetime.now(UTC).isoformat(),
    }
    memory_store.append(item)
    return {'status': 'ok', 'result': item}


def _send_crm_success_result(tenant_id: str, provider: str, response_status: int) -> JsonObject:
    """Return success result for sent CRM request."""
    return {
        'status': 'ok',
        'result': {
            'tenant_id': tenant_id,
            'delivery_status': 'sent',
            'provider': provider,
            'response_status': response_status,
        },
    }


# ── SuiteCRM ──────────────────────────────────────────────────


def upsert_suitecrm_lead(payload: SuiteCrmLeadRequest, auth: AuthDep) -> JsonObject:
    """Upsert a lead to SuiteCRM."""
    _enforce_rate_limit(f'{auth.tenant_id}:integrations:suitecrm:upsert', limit=60, window_seconds=60)

    base_url = os.getenv('SUITECRM_URL', '').rstrip('/')
    token = os.getenv('SUITECRM_API_KEY', '')

    if not base_url or not token:
        return _queue_crm_job(
            _suitecrm_jobs_memory, auth.tenant_id, 'queued', 'SuiteCRM not configured',
            payload.model_dump(), 'lead'
        )

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    body: JsonObject = {
        'data': {
            'type': 'Leads',
            'attributes': {
                'first_name': payload.first_name,
                'last_name': payload.last_name,
                'email1': payload.email,
                'account_name': payload.company,
                'lead_source': payload.source,
                'description': f'Tenant: {auth.tenant_id}',
            },
        }
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/Api/V8/module', headers=headers, json=body)
            if response.is_success:
                return _send_crm_success_result(auth.tenant_id, 'suitecrm', response.status_code)
    except Exception as ex:
        message = f'SuiteCRM request failed: {ex}'
        return _queue_crm_job(_suitecrm_jobs_memory, auth.tenant_id, 'queued', message, payload.model_dump(), 'lead')

    return _queue_crm_job(
        _suitecrm_jobs_memory, auth.tenant_id, 'queued', 'SuiteCRM responded with non-success status',
        payload.model_dump(), 'lead'
    )


# ── RefferQ ───────────────────────────────────────────────────


def register_refferq_referral(payload: RefferqReferralRequest, auth: AuthDep) -> JsonObject:
    """Register a referral with RefferQ."""
    _enforce_rate_limit(f'{auth.tenant_id}:integrations:refferq:create', limit=60, window_seconds=60)

    base_url = os.getenv('REFFERQ_URL', '').rstrip('/')
    token = os.getenv('REFFERQ_API_KEY', '')

    if not base_url or not token:
        return _queue_crm_job(
            _refferq_jobs_memory, auth.tenant_id, 'queued', 'RefferQ not configured',
            payload.model_dump(), 'referral'
        )

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    body: JsonObject = {
        'referrer_email': payload.referrer_email,
        'referred_email': payload.referred_email,
        'campaign': payload.campaign,
        'tenant_id': auth.tenant_id,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/api/referrals', headers=headers, json=body)
            if response.is_success:
                return _send_crm_success_result(auth.tenant_id, 'refferq', response.status_code)
    except Exception as ex:
        message = f'RefferQ request failed: {ex}'
        return _queue_crm_job(_refferq_jobs_memory, auth.tenant_id, 'queued', message, payload.model_dump(), 'referral')

    return _queue_crm_job(
        _refferq_jobs_memory, auth.tenant_id, 'queued', 'RefferQ responded with non-success status',
        payload.model_dump(), 'referral'
    )


# ── Request Models (copied from legacy_main.py) ───────────────

from pydantic import BaseModel, Field


class SuiteCrmLeadRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=5, max_length=320)
    company: str = Field(default='', max_length=180)
    source: str = Field(default='nuxtron', max_length=80)


class RefferqReferralRequest(BaseModel):
    referrer_email: str = Field(min_length=5, max_length=320)
    referred_email: str = Field(min_length=5, max_length=320)
    campaign: str = Field(min_length=1, max_length=140)
