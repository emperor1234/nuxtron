"""Media validation, job records, streaming frames, and provider processing."""

from __future__ import annotations
from ..constants import ASSEMBLYAI_TRANSCRIPT_API_ENDPOINT
from ..constants import JSON_CONTENT_TYPE
from ..constants import MUX_ASSET_API_ENDPOINT
from ..constants import _MAGIC_SIGNATURES
from ..schemas import MediaJobCreateRequest
from ..runtime import require_durable_media_jobs
from .provider_http import provider_request_failed
from .provider_http import provider_unavailable
from .provider_http import request_provider_api
from .provider_http import validate_public_media_source_url
from typing import Any
from fastapi import HTTPException
import hashlib
import hmac
import json
import os
import time


def _sse_message(event: str, payload: dict[str, Any]) -> str:
    """Format an SSE frame."""
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


def _detect_magic_mime(raw: bytes) -> str | None:
    """Return the first MIME type whose signature matches the provided bytes."""
    for mime, signatures in _MAGIC_SIGNATURES.items():
        for offset, signature in signatures:
            if raw[offset : offset + len(signature)] == signature:
                return mime
    return None


def _validate_magic_bytes(raw: bytes, claimed_mime: str) -> tuple[bool, str]:
    """

    Check raw bytes against known magic-byte signatures.

    Returns (is_valid, detected_mime_or_reason).

    """
    detected_mime = _detect_magic_mime(raw)
    if claimed_mime not in _MAGIC_SIGNATURES:
        if detected_mime:
            return (False, f"Detected {detected_mime} but claimed {claimed_mime}")
        return (False, f"Unknown MIME type: {claimed_mime}")
    if detected_mime == claimed_mime:
        return (True, claimed_mime)
    if detected_mime:
        return (False, f"Magic bytes match {detected_mime}, not {claimed_mime}")
    return (False, f"Magic bytes do not match {claimed_mime}")


def _issue_validation_token(tenant_id: str, storage_key: str, mime: str) -> str:
    """Bind tenant/key/MIME with a short-lived HMAC; require a production secret."""
    secret = _media_validation_signing_key()
    payload = f"{tenant_id}:{storage_key}:{mime}:{int(time.time()) // 300}"
    return hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()


def _verify_validation_token(token: str, tenant_id: str, storage_key: str, mime: str) -> bool:
    """Verify an object-bound validation token for the current/previous five-minute window."""
    if len(token) != 64 or not storage_key or not mime:
        return False
    secret = _media_validation_signing_key()
    bucket = int(time.time()) // 300
    for epoch in (bucket, bucket - 1):
        raw = f"{tenant_id}:{storage_key}:{mime}:{epoch}"
        expected = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(token, expected):
            return True
    return False


def _media_validation_signing_key() -> bytes:
    """Derive a purpose-specific HMAC key from configured secret material."""
    production = os.getenv("ENVIRONMENT", "development").strip().lower() == "production"
    configured = os.getenv("FASTAPI_SECRET", "").strip()
    if production and (
        len(configured) < 32
        or "replace-with" in configured.lower()
        or "change-this" in configured.lower()
        or "dev-secret" in configured.lower()
    ):
        raise HTTPException(status_code=503, detail="Media validation signing is not configured.")
    key_material = configured or os.getenv("APP_ENC_KEY", "").strip()
    if not key_material:
        raise HTTPException(status_code=503, detail="Media validation signing is not configured.")
    return hmac.new(key_material.encode(), b"nuxtron.media.validation.v1", hashlib.sha256).digest()


def _build_job_record(job_id: int, tenant_id: str, payload: MediaJobCreateRequest, now_iso: str) -> dict[str, Any]:
    """Reject legacy process-local job records until durable media storage exists."""
    require_durable_media_jobs()


async def _dispatch_cloudinary(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """Submit a public source URL to Cloudinary over pinned provider egress."""
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    api_key = os.getenv("CLOUDINARY_API_KEY", "")
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "")
    if not (cloud_name and api_key and api_secret):
        return provider_unavailable(
            "cloudinary", "PROVIDER_CREDENTIALS_MISSING", "Cloudinary credentials are not configured."
        )
    if not source_url:
        return provider_unavailable(
            "cloudinary", "MEDIA_SOURCE_URL_REQUIRED", "A public HTTPS media source URL is required."
        )
    try:
        source_url = await validate_public_media_source_url(source_url)
    except (TypeError, ValueError):
        return provider_unavailable(
            "cloudinary", "MEDIA_SOURCE_URL_NOT_ALLOWED", "The media source URL is not a permitted public HTTPS destination."
        )

    import urllib.parse

    timestamp = str(int(time.time()))
    upload_params: dict[str, Any] = {
        "public_id": storage_key.replace("/", "_"),
        "timestamp": timestamp,
        "overwrite": "true",
    }
    if operation == "resize" and params.get("width"):
        upload_params["width"] = str(params["width"])
        if params.get("height"):
            upload_params["height"] = str(params["height"])
        upload_params["crop"] = str(params.get("crop", "fill"))
    if params.get("format"):
        upload_params["format"] = str(params["format"])
    param_str = "&".join((f"{key}={value}" for key, value in sorted(upload_params.items())))
    signature = hashlib.sha1(f"{param_str}{api_secret}".encode(), usedforsecurity=False).hexdigest()
    encoded = urllib.parse.urlencode(
        {**upload_params, "api_key": api_key, "signature": signature, "file": source_url}
    ).encode()
    cloud_path = urllib.parse.quote(cloud_name, safe="-_")
    endpoint = f"https://api.cloudinary.com/v1_1/{cloud_path}/auto/upload"
    try:
        response = await request_provider_api(
            "POST",
            endpoint,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            body=encoded,
        )
        if response.status_code >= 400:
            return {
                "provider": "cloudinary",
                "status": "error",
                "error_code": "PROVIDER_REJECTED_REQUEST",
                "error": "Cloudinary rejected the media request.",
            }
        result = response.json()
        return {
            "provider": "cloudinary",
            "status": "complete",
            "mode": "live",
            "public_id": result.get("public_id"),
            "secure_url": result.get("secure_url"),
            "format": result.get("format"),
            "bytes": result.get("bytes"),
            "width": result.get("width"),
            "height": result.get("height"),
        }
    except Exception as exc:
        return provider_request_failed("cloudinary", exc)

async def _dispatch_mux(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """Create a Mux asset from an explicitly validated public HTTPS source."""
    token_id = os.getenv("MUX_TOKEN_ID", "")
    token_secret = os.getenv("MUX_TOKEN_SECRET", "")
    if not (token_id and token_secret):
        return provider_unavailable("mux", "PROVIDER_CREDENTIALS_MISSING", "Mux credentials are not configured.")
    if not source_url:
        return provider_unavailable("mux", "MEDIA_SOURCE_URL_REQUIRED", "A public HTTPS media source URL is required.")
    try:
        source_url = await validate_public_media_source_url(source_url)
    except (TypeError, ValueError):
        return provider_unavailable(
            "mux", "MEDIA_SOURCE_URL_NOT_ALLOWED", "The media source URL is not a permitted public HTTPS destination."
        )

    import base64
    import json

    credentials = base64.b64encode(f"{token_id}:{token_secret}".encode()).decode()
    payload = json.dumps(
        {
            "input": [{"url": source_url}],
            "playback_policy": [params.get("playback_policy", "public")],
            "mp4_support": params.get("mp4_support", "standard"),
        }
    ).encode()
    try:
        response = await request_provider_api(
            "POST",
            MUX_ASSET_API_ENDPOINT,
            headers={"Content-Type": JSON_CONTENT_TYPE, "Authorization": f"Basic {credentials}"},
            body=payload,
        )
        if response.status_code >= 400:
            return {"provider": "mux", "status": "error", "error_code": "PROVIDER_REJECTED_REQUEST", "error": "Mux rejected the media request."}
        asset = response.json().get("data", {})
        return {
            "provider": "mux",
            "status": "processing",
            "mode": "live",
            "asset_id": asset.get("id"),
            "mux_status": asset.get("status"),
            "playback_ids": asset.get("playback_ids", []),
            "duration": asset.get("duration"),
        }
    except Exception as exc:
        return provider_request_failed("mux", exc)

async def _dispatch_bunny(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """Fail closed: the Bunny adapter lacks a real tenant-object reader/uploader."""
    if not (os.getenv("BUNNY_API_KEY", "") and os.getenv("BUNNY_STORAGE_ZONE", "")):
        return provider_unavailable(
            "bunny", "PROVIDER_CREDENTIALS_MISSING", "Bunny.net credentials are not configured."
        )
    return provider_unavailable(
        "bunny",
        "BUNNY_UPLOAD_ADAPTER_UNAVAILABLE",
        "Bunny.net upload requires a tenant-scoped object reader and streamed uploader; no empty placeholder upload was sent.",
    )

async def _dispatch_assemblyai(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """Submit an AssemblyAI transcript job using pinned provider egress."""
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "")
    if not api_key:
        return provider_unavailable(
            "assemblyai", "PROVIDER_CREDENTIALS_MISSING", "AssemblyAI credentials are not configured."
        )
    if not source_url:
        return provider_unavailable(
            "assemblyai", "MEDIA_SOURCE_URL_REQUIRED", "A public HTTPS media source URL is required."
        )
    try:
        source_url = await validate_public_media_source_url(source_url)
    except (TypeError, ValueError):
        return provider_unavailable(
            "assemblyai", "MEDIA_SOURCE_URL_NOT_ALLOWED", "The media source URL is not a permitted public HTTPS destination."
        )

    import json

    payload = json.dumps(
        {
            "audio_url": source_url,
            "speaker_labels": params.get("diarize", False),
            "sentiment_analysis": params.get("sentiment", False),
            "auto_highlights": params.get("highlights", False),
            "language_detection": params.get("detect_language", True),
            "punctuate": params.get("punctuate", True),
            "format_text": params.get("format_text", True),
        }
    ).encode()
    try:
        response = await request_provider_api(
            "POST",
            ASSEMBLYAI_TRANSCRIPT_API_ENDPOINT,
            headers={"Authorization": api_key, "Content-Type": JSON_CONTENT_TYPE},
            body=payload,
        )
        if response.status_code >= 400:
            return {
                "provider": "assemblyai",
                "status": "error",
                "error_code": "PROVIDER_REJECTED_REQUEST",
                "error": "AssemblyAI rejected the transcript request.",
            }
        result = response.json()
        transcript_id = result.get("id")
        return {
            "provider": "assemblyai",
            "status": "processing",
            "mode": "live",
            "transcript_id": transcript_id,
            "aai_status": result.get("status"),
            "poll_url": f"https://api.assemblyai.com/v2/transcript/{transcript_id}" if transcript_id else None,
            "language_code": result.get("language_code"),
        }
    except Exception as exc:
        return provider_request_failed("assemblyai", exc)
