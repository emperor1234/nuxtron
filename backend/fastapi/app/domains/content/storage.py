"""Storage Operations Service (MinIO)

Extracted from legacy_main.py: MinIO presigned URLs, object listing.
"""

from __future__ import annotations


import os
import re
from datetime import UTC, datetime
from typing import Annotated, Literal

import httpx
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from ... import memory_stores
from ...deps import AuthContext, require_auth
from ...rate_limiter import enforce_rate_limit as _enforce_rate_limit

JsonObject = dict[str, object]

AuthDep = Annotated[AuthContext, Depends(require_auth)]


# ── Memory Store References (set by legacy_main.py) ──────────
_minio_objects_memory = memory_stores.minio_objects

_minio_presign = None


def set_memory_stores(
    minio_objects_memory=None,
    enforce_rate_limit=None,
    minio_presign=None,
) -> None:
    """Inject memory store references and helpers from legacy_main.py."""
    global _minio_objects_memory, _enforce_rate_limit, _minio_presign
    if minio_objects_memory is not None:
        _minio_objects_memory = minio_objects_memory
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit
    if minio_presign is not None:
        _minio_presign = minio_presign


def delete_minio_object(bucket: str, object_key: str) -> None:
    """Delete one object using the configured SigV4 signer and operator-owned endpoint."""
    endpoint = os.getenv("MINIO_ENDPOINT", "").strip().rstrip("/")
    access_key = os.getenv("MINIO_ACCESS_KEY", "").strip()
    secret_key = os.getenv("MINIO_SECRET_KEY", "").strip()
    if not endpoint or not access_key or not secret_key:
        raise HTTPException(status_code=503, detail="Object storage is unavailable.")

    from urllib.parse import urlsplit

    parsed = urlsplit(endpoint)
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or not bucket
        or "/" in bucket
    ):
        raise HTTPException(status_code=503, detail="Object storage configuration is invalid.")
    if os.getenv("ENVIRONMENT", "development").strip().lower() == "production" and parsed.scheme.lower() != "https":
        raise HTTPException(status_code=503, detail="Object storage must use HTTPS in production.")
    if not callable(_minio_presign):
        raise HTTPException(status_code=503, detail="Object storage signer is unavailable.")

    signed_url = _minio_presign(endpoint, access_key, secret_key, bucket, object_key, "DELETE", 60)
    try:
        with httpx.Client(timeout=10.0, trust_env=False, follow_redirects=False) as client:
            with client.stream("DELETE", signed_url) as response:
                if not response.is_success:
                    raise HTTPException(status_code=502, detail="Object storage deletion failed.")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Object storage deletion failed.") from exc


# ── Storage Operations ────────────────────────────────────────


def storage_presign(payload: MinioPresignRequest, auth: AuthDep) -> JsonObject:
    """Generate a presigned URL for MinIO object."""
    _enforce_rate_limit(f"{auth.tenant_id}:storage:presign", limit=120, window_seconds=60)

    endpoint = os.getenv("MINIO_ENDPOINT", "").strip()
    access_key = os.getenv("MINIO_ACCESS_KEY", "").strip()
    secret_key = os.getenv("MINIO_SECRET_KEY", "").strip()

    tenant_bucket = f"{auth.tenant_id}-{payload.bucket}"

    if not endpoint or not access_key or not secret_key:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="Object storage is unavailable.")
        record: JsonObject = {
            "id": len(_minio_objects_memory) + 1,
            "tenant_id": auth.tenant_id,
            "bucket": tenant_bucket,
            "object_key": payload.object_key,
            "method": payload.method,
            "status": "queued",
            "reason": "MinIO not configured",
            "presigned_url": None,
            "created_at": datetime.now(UTC).isoformat(),
        }
        _minio_objects_memory.append(record)
        return {"status": "ok", "result": record}

    if not callable(_minio_presign):
        raise HTTPException(status_code=503, detail="Object storage signer is unavailable.")
    presigned_url = _minio_presign(
        endpoint,
        access_key,
        secret_key,
        tenant_bucket,
        payload.object_key,
        payload.method,
        payload.expires_seconds,
    )

    record: JsonObject = {
        "id": len(_minio_objects_memory) + 1,
        "tenant_id": auth.tenant_id,
        "bucket": tenant_bucket,
        "object_key": payload.object_key,
        "method": payload.method,
        "presigned_url": presigned_url,
        "expires_seconds": payload.expires_seconds,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _minio_objects_memory.append(record)
    return {"status": "ok", "result": record}


def storage_list_objects(payload: MinioListObjectsRequest, auth: AuthDep) -> JsonObject:
    """List objects in a MinIO bucket."""
    _enforce_rate_limit(f"{auth.tenant_id}:storage:list", limit=180, window_seconds=60)

    endpoint = os.getenv("MINIO_ENDPOINT", "").strip()
    access_key = os.getenv("MINIO_ACCESS_KEY", "").strip()
    secret_key = os.getenv("MINIO_SECRET_KEY", "").strip()

    tenant_bucket = f"{auth.tenant_id}-{payload.bucket}"

    if not endpoint or not access_key or not secret_key:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="Object storage is unavailable.")
        items: list[JsonObject] = []
        for r in _minio_objects_memory:
            if r.get("tenant_id") != auth.tenant_id or r.get("bucket") != tenant_bucket:
                continue
            object_key = r.get("object_key")
            if isinstance(object_key, str) and object_key.startswith(payload.prefix):
                items.append(r)
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "bucket": tenant_bucket,
            "prefix": payload.prefix,
            "objects": [{"key": r["object_key"], "created_at": r["created_at"]} for r in items[: payload.max_keys]],
            "total": len(items),
            "source": "memory-fallback",
        }

    headers: dict[str, str] = {}
    params: dict[str, str] = {"list-type": "2", "max-keys": str(payload.max_keys)}
    if payload.prefix:
        params["prefix"] = payload.prefix

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.get(f"{endpoint}/{tenant_bucket}", headers=headers, params=params)
            if response.is_success:
                text = response.text
                keys = re.findall(r"<Key>(.*?)</Key>", text)
                return {
                    "status": "ok",
                    "tenant_id": auth.tenant_id,
                    "bucket": tenant_bucket,
                    "prefix": payload.prefix,
                    "objects": [{"key": k} for k in keys],
                    "total": len(keys),
                    "source": "minio",
                }
    except Exception as ex:
        if os.getenv("ENVIRONMENT", "development").lower() == "production":
            raise HTTPException(status_code=503, detail="Object storage listing unavailable.") from ex
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "bucket": tenant_bucket,
            "objects": [],
            "total": 0,
            "source": f"error:{ex}",
        }

    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(status_code=503, detail="Object storage listing unavailable.")
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "bucket": tenant_bucket,
        "objects": [],
        "total": 0,
        "source": "minio-non-success",
    }


# ── Request Models ────────────────────────────────────────────


class MinioPresignRequest(BaseModel):
    bucket: str = Field(min_length=1, max_length=120)
    object_key: str = Field(min_length=1, max_length=512)
    method: Literal["GET", "PUT"] = "GET"
    expires_seconds: int = Field(default=3600, ge=60, le=86400)


class MinioListObjectsRequest(BaseModel):
    bucket: str = Field(min_length=1, max_length=120)
    prefix: str = Field(default="", max_length=256)
    max_keys: int = Field(default=50, ge=1, le=500)
