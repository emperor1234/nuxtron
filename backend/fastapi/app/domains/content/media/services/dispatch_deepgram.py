"""Content/Media service: dispatch deepgram."""

from __future__ import annotations
from ..constants import JSON_CONTENT_TYPE
from typing import Any
import asyncio
import os


async def _dispatch_deepgram(
    storage_key: str, operation: str, params: dict[str, Any], source_url: str | None
) -> dict[str, Any]:
    """
    Deepgram Speech Recognition API — real-time and batch transcription.
    Docs: https://developers.deepgram.com/reference/listen-remote
    Env vars: DEEPGRAM_API_KEY
    """
    await asyncio.sleep(0)
    api_key = os.getenv("DEEPGRAM_API_KEY", "")
    if not api_key:
        return {
            "provider": "deepgram",
            "status": "dispatched",
            "mode": "credentials-not-configured",
            "message": "Set DEEPGRAM_API_KEY to enable live dispatch.",
            "would_call": "https://api.deepgram.com/v1/listen",
            "operation": operation,
        }
    import json as _json
    import urllib.parse
    import urllib.request

    query = {
        "model": params.get("model", "nova-2"),
        "language": params.get("language", "en"),
        "punctuate": "true" if params.get("punctuate", True) else "false",
        "diarize": "true" if params.get("diarize", False) else "false",
        "smart_format": "true" if params.get("smart_format", True) else "false",
    }
    url = f"https://api.deepgram.com/v1/listen?{urllib.parse.urlencode(query)}"
    payload = _json.dumps({"url": source_url or f"s3://raw-input/{storage_key}"}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Token {api_key}")
    req.add_header("Content-Type", JSON_CONTENT_TYPE)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
            channels = result.get("results", {}).get("channels", [{}])
            alt = channels[0].get("alternatives", [{}])[0] if channels else {}
            transcript = alt.get("transcript", "")
            return {
                "provider": "deepgram",
                "status": "complete",
                "mode": "live",
                "transcript": transcript,
                "confidence": alt.get("confidence"),
                "words": len(transcript.split()) if transcript else 0,
                "detected_language": result.get("results", {}).get("channels", [{}])[0].get("detected_language"),
            }
    except Exception as exc:
        return {"provider": "deepgram", "status": "error", "mode": "live", "error": str(exc)}
