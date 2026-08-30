"""Appwrite Integration Service

Extracted from legacy_main.py: Appwrite user creation, session creation.
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


CONTENT_TYPE_JSON = 'application/json'

# ── Memory Store References (set by legacy_main.py) ──────────
_appwrite_events_memory = []
_rate_buckets = {}
_rate_lock = None
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit  # default; may be overwritten by set_memory_stores


def set_memory_stores(
    appwrite_events_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
) -> None:
    """Inject memory store references from legacy_main.py."""
    global _appwrite_events_memory, _rate_buckets, _rate_lock, _enforce_rate_limit
    if appwrite_events_memory is not None:
        _appwrite_events_memory = appwrite_events_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit


# ── Appwrite Operations ───────────────────────────────────────


def appwrite_create_user(payload: AppwriteCreateUserRequest, auth: AuthDep) -> JsonObject:
    """Create a user in Appwrite."""
    _enforce_rate_limit(f'{auth.tenant_id}:appwrite:create-user', limit=60, window_seconds=60)

    base_url = os.getenv('APPWRITE_ENDPOINT', '').rstrip('/')
    project_id = os.getenv('APPWRITE_PROJECT_ID', '').strip()
    api_key = os.getenv('APPWRITE_API_KEY', '').strip()

    if not base_url or not project_id or not api_key:
        item: JsonObject = {
            'id': len(_appwrite_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'action': 'create-user',
            'status': 'queued',
            'reason': 'Appwrite not configured',
            'user_id': payload.user_id,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _appwrite_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Content-Type': CONTENT_TYPE_JSON,
        'X-Appwrite-Project': project_id,
        'X-Appwrite-Key': api_key,
    }
    body: JsonObject = {
        'userId': payload.user_id,
        'email': payload.email,
        'password': payload.password,
        'name': payload.name,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/v1/users', headers=headers, json=body)
            if response.is_success:
                data = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'action': 'create-user',
                        'delivery_status': 'created',
                        'appwrite_user_id': data.get('$id', payload.user_id),
                    },
                }
            return {
                'status': 'ok',
                'result': {
                    'tenant_id': auth.tenant_id,
                    'action': 'create-user',
                    'delivery_status': 'appwrite-error',
                    'appwrite_status': response.status_code,
                    'detail': response.text[:200],
                },
            }
    except Exception as ex:
        item: JsonObject = {
            'id': len(_appwrite_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'action': 'create-user',
            'status': f'queued-after-error:{ex}',
            'user_id': payload.user_id,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _appwrite_events_memory.append(item)
        return {'status': 'ok', 'result': item}


def appwrite_create_session(payload: AppwriteCreateSessionRequest, auth: AuthDep) -> JsonObject:
    """Create an email/password session in Appwrite."""
    _enforce_rate_limit(f'{auth.tenant_id}:appwrite:create-session', limit=60, window_seconds=60)

    base_url = os.getenv('APPWRITE_ENDPOINT', '').rstrip('/')
    project_id = os.getenv('APPWRITE_PROJECT_ID', '').strip()

    if not base_url or not project_id:
        item: JsonObject = {
            'id': len(_appwrite_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'action': 'create-session',
            'status': 'queued',
            'reason': 'Appwrite not configured',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _appwrite_events_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Content-Type': CONTENT_TYPE_JSON,
        'X-Appwrite-Project': project_id,
    }
    body: JsonObject = {'email': payload.email, 'password': payload.password}

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/v1/account/sessions/email', headers=headers, json=body)
            if response.is_success:
                data = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'action': 'create-session',
                        'delivery_status': 'session-created',
                        'session_id': data.get('$id', ''),
                        'expire': data.get('expire', ''),
                    },
                }
            return {
                'status': 'ok',
                'result': {
                    'tenant_id': auth.tenant_id,
                    'action': 'create-session',
                    'delivery_status': 'appwrite-error',
                    'appwrite_status': response.status_code,
                },
            }
    except Exception as ex:
        item: JsonObject = {
            'id': len(_appwrite_events_memory) + 1,
            'tenant_id': auth.tenant_id,
            'action': 'create-session',
            'status': f'queued-after-error:{ex}',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _appwrite_events_memory.append(item)
        return {'status': 'ok', 'result': item}


# ── Request Models ────────────────────────────────────────────

from pydantic import BaseModel, Field


class AppwriteCreateUserRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    email: str = Field(min_length=5, max_length=320)
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=256)


class AppwriteCreateSessionRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=256)
