"""Media validation, job records, streaming frames, and provider processing."""

from __future__ import annotations
from ..constants import ASSEMBLYAI_TRANSCRIPT_API_ENDPOINT
from ..constants import JSON_CONTENT_TYPE
from ..constants import MUX_ASSET_API_ENDPOINT
from ..constants import _MAGIC_SIGNATURES
from ..schemas import MediaJobCreateRequest
from typing import Any
from fastapi import HTTPException
import asyncio
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
    configured = os.getenv("FASTAPI_SECRET", "").strip()
    production = os.getenv("ENVIRONMENT", "development").strip().lower() == "production"
    if production and (len(configured) < 32 or configured == "dev-secret-replace-in-production"):
        raise HTTPException(status_code=503, detail="Media validation signing is not configured.")
    secret = (configured or "dev-secret-replace-in-production").encode()
    payload = f"{tenant_id}:{storage_key}:{mime}:{int(time.time()) // 300}"
    return hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()


def _verify_validation_token(token: str, tenant_id: str, storage_key: str, mime: str) -> bool:
    """Verify an object-bound validation token for the current/previous five-minute window."""
    configured = os.getenv("FASTAPI_SECRET", "").strip()
    production = os.getenv("ENVIRONMENT", "development").strip().lower() == "production"
    if production and (len(configured) < 32 or configured == "dev-secret-replace-in-production"):
        raise HTTPException(status_code=503, detail="Media validation signing is not configured.")
    secret = (configured or "dev-secret-replace-in-production").encode()
    if len(token) != 64 or not storage_key or not mime:
        return False
    bucket = int(time.time()) // 300
    for epoch in (bucket, bucket - 1):
        raw = f"{tenant_id}:{storage_key}:{mime}:{epoch}"
        expected = hmac.new(secret, raw.encode(), hashlib.sha256).hexdigest()
        if hmac.compare_digest(token, expected):
            return True
    return False


def _build_job_record(job_id: int, tenant_id: str, payload: MediaJobCreateRequest, now_iso: str) -> dict[str, Any]:
    """Construct a new media job dict."""
    return {
        "id": job_id,
        "tenant_id": tenant_id,
        "storage_key": payload.storage_key,
        "media_type": payload.media_type,
        "output_bucket": payload.output_bucket,
        "processing_options": payload.processing_options,
        "status": "queued",
        "progress_pct": 0,
        "output_key": None,
        "error": None,
        "validation_token_provided": payload.validation_token is not None,
        "created_at": now_iso,
        "updated_at": now_iso,
        "completed_at": None,
        "source": "api",
        "persistence": "memory-fallback",
        "provider": payload.provider or "internal",
        "retry_count": 0,
    }


async def _dispatch_cloudinary(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """

    Cloudinary Upload API — image/video transformation.

    Docs: https://cloudinary.com/documentation/image_upload_api_reference

    Env vars: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET

    Security: files sent directly to Cloudinary (managed sandbox) — never through this server.

    """
    await asyncio.sleep(0)
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    api_key = os.getenv("CLOUDINARY_API_KEY", "")
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "")
    if not (cloud_name and api_key and api_secret):
        return {
            "provider": "cloudinary",
            "status": "dispatched",
            "mode": "credentials-not-configured",
            "message": "Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET to enable live dispatch.",
            "would_call": "https://api.cloudinary.com/v1_1/<cloud>/auto/upload",
            "operation": operation,
            "params": params,
        }
    import urllib.parse
    import urllib.request

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
    param_str = "&".join((f"{k}={v}" for k, v in sorted(upload_params.items())))
    sig_input = f"{param_str}{api_secret}"
    signature = hashlib.sha1(sig_input.encode(), usedforsecurity=False).hexdigest()
    post_data = {**upload_params, "api_key": api_key, "signature": signature}
    if source_url:
        post_data["file"] = source_url
    encoded = urllib.parse.urlencode(post_data).encode()
    req = urllib.request.Request(
        f"https://api.cloudinary.com/v1_1/{cloud_name}/auto/upload", data=encoded, method="POST"
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        import json as _json

        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
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
        return {"provider": "cloudinary", "status": "error", "mode": "live", "error": str(exc)}


async def _dispatch_mux(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """

    Mux Video API — video transcoding and streaming.

    Docs: https://docs.mux.com/api-reference/video#operation/create-asset

    Env vars: MUX_TOKEN_ID, MUX_TOKEN_SECRET

    """
    await asyncio.sleep(0)
    token_id = os.getenv("MUX_TOKEN_ID", "")
    token_secret = os.getenv("MUX_TOKEN_SECRET", "")
    if not (token_id and token_secret):
        return {
            "provider": "mux",
            "status": "dispatched",
            "mode": "credentials-not-configured",
            "message": "Set MUX_TOKEN_ID and MUX_TOKEN_SECRET to enable live dispatch.",
            "would_call": "https://api.mux.com/video/v1/assets",
            "operation": operation,
        }
    import base64
    import json as _json
    import urllib.request

    credentials = base64.b64encode(f"{token_id}:{token_secret}".encode()).decode()
    payload = _json.dumps(
        {
            "input": [{"url": source_url or f"s3://raw-input/{storage_key}"}],
            "playback_policy": [params.get("playback_policy", "public")],
            "mp4_support": params.get("mp4_support", "standard"),
        }
    ).encode()
    req = urllib.request.Request(MUX_ASSET_API_ENDPOINT, data=payload, method="POST")
    req.add_header("Content-Type", JSON_CONTENT_TYPE)
    req.add_header("Authorization", f"Basic {credentials}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
            asset = result.get("data", {})
            return {
                "provider": "mux",
                "status": "complete" if asset.get("status") == "ready" else "processing",
                "mode": "live",
                "asset_id": asset.get("id"),
                "mux_status": asset.get("status"),
                "playback_ids": asset.get("playback_ids", []),
                "duration": asset.get("duration"),
            }
    except Exception as exc:
        return {"provider": "mux", "status": "error", "mode": "live", "error": str(exc)}


async def _dispatch_bunny(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """

    Bunny.net Storage API — cost-effective image/video CDN.

    Docs: https://docs.bunny.net/reference/storage-api

    Env vars: BUNNY_API_KEY, BUNNY_STORAGE_ZONE, BUNNY_CDN_HOSTNAME

    """
    await asyncio.sleep(0)
    api_key = os.getenv("BUNNY_API_KEY", "")
    storage_zone = os.getenv("BUNNY_STORAGE_ZONE", "")
    cdn_hostname = os.getenv("BUNNY_CDN_HOSTNAME", "")
    if not (api_key and storage_zone):
        return {
            "provider": "bunny",
            "status": "dispatched",
            "mode": "credentials-not-configured",
            "message": "Set BUNNY_API_KEY, BUNNY_STORAGE_ZONE, BUNNY_CDN_HOSTNAME to enable live dispatch.",
            "would_call": f"https://storage.bunnycdn.com/{storage_zone or '<zone>'}/",
            "operation": operation,
        }
    import urllib.request

    dest_path = storage_key.split("/", 1)[-1] if "/" in storage_key else storage_key
    upload_url = f"https://storage.bunnycdn.com/{storage_zone}/{dest_path}"
    req = urllib.request.Request(upload_url, data=b"", method="PUT")
    req.add_header("AccessKey", api_key)
    req.add_header("Content-Type", "application/octet-stream")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            cdn_url = f"https://{cdn_hostname}/{dest_path}" if cdn_hostname else upload_url
            return {
                "provider": "bunny",
                "status": "complete",
                "mode": "live",
                "cdn_url": cdn_url,
                "storage_path": dest_path,
                "http_status": resp.status,
            }
    except Exception as exc:
        return {"provider": "bunny", "status": "error", "mode": "live", "error": str(exc)}


async def _dispatch_assemblyai(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """

    AssemblyAI Transcription API — speech-to-text with diarisation and sentiment.

    Docs: https://www.assemblyai.com/docs/api-reference/transcripts/submit

    Env vars: ASSEMBLYAI_API_KEY

    """
    await asyncio.sleep(0)
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "")
    if not api_key:
        return {
            "provider": "assemblyai",
            "status": "dispatched",
            "mode": "credentials-not-configured",
            "message": "Set ASSEMBLYAI_API_KEY to enable live dispatch.",
            "would_call": "https://api.assemblyai.com/v2/transcript",
            "operation": operation,
        }
    import json as _json
    import urllib.request

    payload = _json.dumps(
        {
            "audio_url": source_url or f"s3://raw-input/{storage_key}",
            "speaker_labels": params.get("diarize", False),
            "sentiment_analysis": params.get("sentiment", False),
            "auto_highlights": params.get("highlights", False),
            "language_detection": params.get("detect_language", True),
            "punctuate": params.get("punctuate", True),
            "format_text": params.get("format_text", True),
        }
    ).encode()
    req = urllib.request.Request(ASSEMBLYAI_TRANSCRIPT_API_ENDPOINT, data=payload, method="POST")
    req.add_header("Authorization", api_key)
    req.add_header("Content-Type", JSON_CONTENT_TYPE)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
            return {
                "provider": "assemblyai",
                "status": "processing",
                "mode": "live",
                "transcript_id": result.get("id"),
                "aai_status": result.get("status"),
                "poll_url": f"https://api.assemblyai.com/v2/transcript/{result.get('id')}",
                "language_code": result.get("language_code"),
            }
    except Exception as exc:
        return {"provider": "assemblyai", "status": "error", "mode": "live", "error": str(exc)}
