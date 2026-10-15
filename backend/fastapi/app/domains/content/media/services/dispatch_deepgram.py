"""Content/Media adapter for Deepgram transcription."""

from __future__ import annotations

from ..constants import JSON_CONTENT_TYPE
from typing import Any
import json
import os
import urllib.parse

from .provider_http import provider_request_failed
from .provider_http import provider_unavailable
from .provider_http import request_provider_api
from .provider_http import validate_public_media_source_url


async def _dispatch_deepgram(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """Transcribe an explicit public HTTPS source through pinned Deepgram egress."""
    api_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not api_key:
        return provider_unavailable(
            "deepgram", "PROVIDER_CREDENTIALS_MISSING", "Deepgram credentials are not configured."
        )
    if not source_url:
        return provider_unavailable(
            "deepgram", "MEDIA_SOURCE_URL_REQUIRED", "A public HTTPS audio source URL is required."
        )
    try:
        source_url = await validate_public_media_source_url(source_url)
    except (TypeError, ValueError):
        return provider_unavailable(
            "deepgram",
            "MEDIA_SOURCE_URL_NOT_ALLOWED",
            "The media source URL is not a permitted public HTTPS destination.",
        )

    query = {
        "model": params.get("model", "nova-2"),
        "language": params.get("language", "en"),
        "punctuate": "true" if params.get("punctuate", True) else "false",
        "diarize": "true" if params.get("diarize", False) else "false",
        "smart_format": "true" if params.get("smart_format", True) else "false",
    }
    url = f"https://api.deepgram.com/v1/listen?{urllib.parse.urlencode(query)}"
    payload = json.dumps({"url": source_url}).encode()
    try:
        response = await request_provider_api(
            "POST",
            url,
            headers={"Authorization": f"Token {api_key}", "Content-Type": JSON_CONTENT_TYPE},
            body=payload,
        )
        if response.status_code >= 400:
            return {
                "provider": "deepgram",
                "status": "error",
                "error_code": "PROVIDER_REJECTED_REQUEST",
                "error": "Deepgram rejected the transcription request.",
            }
        result = response.json()
        channels = result.get("results", {}).get("channels", [{}])
        alternative = channels[0].get("alternatives", [{}])[0] if channels else {}
        transcript = alternative.get("transcript", "")
        return {
            "provider": "deepgram",
            "status": "complete",
            "mode": "live",
            "transcript": transcript,
            "confidence": alternative.get("confidence"),
            "words": len(transcript.split()) if transcript else 0,
            "detected_language": channels[0].get("detected_language") if channels else None,
        }
    except Exception as exc:
        return provider_request_failed("deepgram", exc)
