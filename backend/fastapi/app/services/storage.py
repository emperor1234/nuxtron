"""Storage Operations Service (MinIO)

Extracted from legacy_main.py: MinIO presigned URLs, object listing.
"""

from __future__ import annotations

import os
from fastapi import Depends
import re
from datetime import UTC, datetime
from typing import Annotated, TYPE_CHECKING, Literal

import httpx

if TYPE_CHECKING:
    from ..deps import AuthContext

JsonObject = dict[str, object]
from ..deps import AuthContext, require_auth
AuthDep = Annotated[AuthContext, Depends(require_auth)]


# ── Memory Store References (set by legacy_main.py) ──────────
_minio_objects_memory = []
_rate_buckets = {}
_rate_lock = None
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit  # default; may be overwritten by set_memory_stores
_minio_presign = None


def set_memory_stores(
    minio_objects_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
    minio_presign=None,
) -> None:
    """Inject memory store references and helpers from legacy_main.py."""
    global _minio_objects_memory, _rate_buckets, _rate_lock, _enforce_rate_limit, _minio_presign
    if minio_objects_memory is not None:
        _minio_objects_memory = minio_objects_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit
    if minio_presign is not None:
        _minio_presign = minio_presign


# ── Storage Operations ────────────────────────────────────────


def storage_presign(payload: MinioPresignRequest, auth: AuthDep) -> JsonObject:
    """Generate a presigned URL for MinIO object."""
    _enforce_rate_limit(f'{auth.tenant_id}:storage:presign', limit=120, window_seconds=60)

    endpoint = os.getenv('MINIO_ENDPOINT', '').strip()
    access_key = os.getenv('MINIO_ACCESS_KEY', '').strip()
    secret_key = os.getenv('MINIO_SECRET_KEY', '').strip()

    tenant_bucket = f'{auth.tenant_id}-{payload.bucket}'

    if not endpoint or not access_key or not secret_key:
        record: JsonObject = {
            'id': len(_minio_objects_memory) + 1,
            'tenant_id': auth.tenant_id,
            'bucket': tenant_bucket,
            'object_key': payload.object_key,
            'method': payload.method,
            'status': 'queued',
            'reason': 'MinIO not configured',
            'presigned_url': None,
            'created_at': datetime.now(UTC).isoformat(),
        }
        _minio_objects_memory.append(record)
        return {'status': 'ok', 'result': record}

    presigned_url = _minio_presign(
        endpoint, access_key, secret_key,
        tenant_bucket, payload.object_key,
        payload.method, payload.expires_seconds,
    )

    record: JsonObject = {
        'id': len(_minio_objects_memory) + 1,
        'tenant_id': auth.tenant_id,
        'bucket': tenant_bucket,
        'object_key': payload.object_key,
        'method': payload.method,
        'presigned_url': presigned_url,
        'expires_seconds': payload.expires_seconds,
        'created_at': datetime.now(UTC).isoformat(),
    }
    _minio_objects_memory.append(record)
    return {'status': 'ok', 'result': record}


def storage_list_objects(payload: MinioListObjectsRequest, auth: AuthDep) -> JsonObject:
    """List objects in a MinIO bucket."""
    _enforce_rate_limit(f'{auth.tenant_id}:storage:list', limit=180, window_seconds=60)

    endpoint = os.getenv('MINIO_ENDPOINT', '').strip()
    access_key = os.getenv('MINIO_ACCESS_KEY', '').strip()
    secret_key = os.getenv('MINIO_SECRET_KEY', '').strip()

    tenant_bucket = f'{auth.tenant_id}-{payload.bucket}'

    if not endpoint or not access_key or not secret_key:
        items: list[JsonObject] = []
        for r in _minio_objects_memory:
            if r.get('tenant_id') != auth.tenant_id or r.get('bucket') != tenant_bucket:
                continue
            object_key = r.get('object_key')
            if isinstance(object_key, str) and object_key.startswith(payload.prefix):
                items.append(r)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'bucket': tenant_bucket,
            'prefix': payload.prefix,
            'objects': [{'key': r['object_key'], 'created_at': r['created_at']} for r in items[: payload.max_keys]],
            'total': len(items),
            'source': 'memory-fallback',
        }

    headers: dict[str, str] = {}
    params: dict[str, str] = {'list-type': '2', 'max-keys': str(payload.max_keys)}
    if payload.prefix:
        params['prefix'] = payload.prefix

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(f'{endpoint}/{tenant_bucket}', headers=headers, params=params)
            if response.is_success:
                text = response.text
                keys = re.findall(r'<Key>(.*?)</Key>', text)
                return {
                    'status': 'ok',
                    'tenant_id': auth.tenant_id,
                    'bucket': tenant_bucket,
                    'prefix': payload.prefix,
                    'objects': [{'key': k} for k in keys],
                    'total': len(keys),
                    'source': 'minio',
                }
    except Exception as ex:
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'bucket': tenant_bucket,
            'objects': [],
            'total': 0,
            'source': f'error:{ex}',
        }

    return {
        'status': 'ok',
        'tenant_id': auth.tenant_id,
        'bucket': tenant_bucket,
        'objects': [],
        'total': 0,
        'source': 'minio-non-success',
    }


# ── Request Models ────────────────────────────────────────────

from pydantic import BaseModel, Field


class MinioPresignRequest(BaseModel):
    bucket: str = Field(min_length=1, max_length=120)
    object_key: str = Field(min_length=1, max_length=512)
    method: Literal['GET', 'PUT'] = 'GET'
    expires_seconds: int = Field(default=3600, ge=60, le=86400)


class MinioListObjectsRequest(BaseModel):
    bucket: str = Field(min_length=1, max_length=120)
    prefix: str = Field(default='', max_length=256)
    max_keys: int = Field(default=50, ge=1, le=500)
