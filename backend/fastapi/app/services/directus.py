"""Directus CMS Integration Service

Extracted from legacy_main.py: Directus create item, list items.
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
_directus_items_memory = []
_rate_buckets = {}
_rate_lock = None
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit  # default; may be overwritten by set_memory_stores


def set_memory_stores(
    directus_items_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
) -> None:
    """Inject memory store references from legacy_main.py."""
    global _directus_items_memory, _rate_buckets, _rate_lock, _enforce_rate_limit
    if directus_items_memory is not None:
        _directus_items_memory = directus_items_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit


# ── Directus Operations ───────────────────────────────────────


def directus_create_item(payload: DirectusCreateItemRequest, auth: AuthDep) -> JsonObject:
    """Create an item in Directus."""
    _enforce_rate_limit(f'{auth.tenant_id}:directus:create-item', limit=120, window_seconds=60)

    base_url = os.getenv('DIRECTUS_URL', '').rstrip('/')
    token = os.getenv('DIRECTUS_STATIC_TOKEN', '').strip()

    doc: JsonObject = {**payload.data, '_tenant_id': auth.tenant_id}

    if not base_url or not token:
        item: JsonObject = {
            'id': len(_directus_items_memory) + 1,
            'tenant_id': auth.tenant_id,
            'collection': payload.collection,
            'data': doc,
            'status': 'queued',
            'reason': 'Directus not configured',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _directus_items_memory.append(item)
        return {'status': 'ok', 'result': item}

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                f'{base_url}/items/{payload.collection}',
                headers=headers,
                json=doc,
            )
            if response.is_success:
                rdata = response.json()
                return {
                    'status': 'ok',
                    'result': {
                        'tenant_id': auth.tenant_id,
                        'collection': payload.collection,
                        'directus_id': rdata.get('data', {}).get('id') if isinstance(rdata.get('data'), dict) else None,
                        'delivery_status': 'created',
                        'provider': 'directus',
                    },
                }
    except Exception as ex:
        item: JsonObject = {
            'id': len(_directus_items_memory) + 1,
            'tenant_id': auth.tenant_id,
            'collection': payload.collection,
            'data': doc,
            'status': f'queued-after-error:{ex}',
            'created_at': datetime.now(UTC).isoformat(),
        }
        _directus_items_memory.append(item)
        return {'status': 'ok', 'result': item}

    item: JsonObject = {
        'id': len(_directus_items_memory) + 1,
        'tenant_id': auth.tenant_id,
        'collection': payload.collection,
        'data': doc,
        'status': 'queued-after-non-success',
        'created_at': datetime.now(UTC).isoformat(),
    }
    _directus_items_memory.append(item)
    return {'status': 'ok', 'result': item}


def directus_list_items(payload: DirectusListItemsRequest, auth: AuthDep) -> JsonObject:
    """List items from Directus."""
    _enforce_rate_limit(f'{auth.tenant_id}:directus:list-items', limit=180, window_seconds=60)

    base_url = os.getenv('DIRECTUS_URL', '').rstrip('/')
    token = os.getenv('DIRECTUS_STATIC_TOKEN', '').strip()

    if not base_url or not token:
        items: list[JsonObject] = [
            i for i in _directus_items_memory
            if i.get('tenant_id') == auth.tenant_id and i.get('collection') == payload.collection
        ]
        page = items[payload.offset: payload.offset + payload.limit]
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'collection': payload.collection,
            'items': page,
            'total': len(items),
            'source': 'memory-fallback',
        }

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }
    params: dict[str, str | int] = {
        'limit': payload.limit,
        'offset': payload.offset,
        'filter[_tenant_id][_eq]': auth.tenant_id,
    }
    if payload.filter:
        for key, val in payload.filter.items():
            params[f'filter[{key}][_eq]'] = str(val)

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(
                f'{base_url}/items/{payload.collection}',
                headers=headers,
                params=params,
            )
            if response.is_success:
                rdata = response.json()
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'collection': payload.collection,
                    'items': rdata.get('data', []),
                    'total': rdata.get('meta', {}).get('total_count', 0) if isinstance(rdata.get('meta'), dict) else 0,
                    'source': 'directus',
                }
    except Exception as ex:
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'collection': payload.collection,
            'items': [],
            'total': 0,
            'source': f'error:{ex}',
        }

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'collection': payload.collection,
        'items': [],
        'total': 0,
        'source': 'directus-non-success',
    }


# ── Request Models ────────────────────────────────────────────

from pydantic import BaseModel, Field


class DirectusCreateItemRequest(BaseModel):
    collection: str = Field(min_length=1, max_length=120)
    data: dict[str, object] = Field(default_factory=dict)


class DirectusListItemsRequest(BaseModel):
    collection: str = Field(min_length=1, max_length=120)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    filter: dict[str, object] = Field(default_factory=dict)
