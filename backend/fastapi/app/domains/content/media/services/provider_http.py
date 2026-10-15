"""Pinned, bounded HTTP transport for managed media provider adapters."""

from __future__ import annotations

import httpx

from ....identity.async_egress import outbound_async_request
from ....identity.async_egress import resolve_outbound_target_async
from ....identity.secure_egress import OutboundTarget


MAX_PROVIDER_RESPONSE_BYTES = 2_000_000


async def request_provider_api(
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    body: bytes,
    timeout: float = 30.0,
) -> httpx.Response:
    """Send a bounded request to a validated HTTPS provider origin without redirects or ambient proxies."""
    target: OutboundTarget = await resolve_outbound_target_async(url)
    return await outbound_async_request(
        method,
        target,
        headers=headers,
        content=body,
        timeout=timeout,
        max_response_bytes=MAX_PROVIDER_RESPONSE_BYTES,
    )


async def validate_public_media_source_url(source_url: str | None) -> str:
    """Require an explicit public HTTPS source before asking a provider to pull media."""
    candidate = (source_url or "").strip()
    if not candidate:
        raise ValueError("MEDIA_SOURCE_URL_REQUIRED")
    target = await resolve_outbound_target_async(candidate)
    return target.url


def provider_unavailable(provider: str, error_code: str, message: str) -> dict[str, str]:
    """Return an explicit unavailable result; callers must never treat it as a successful dispatch."""
    return {
        "provider": provider,
        "status": "unavailable",
        "error_code": error_code,
        "error": message,
    }


def provider_request_failed(provider: str, exc: Exception) -> dict[str, str]:
    """Return a sanitized transport error without provider response bodies or credential-bearing details."""
    return {
        "provider": provider,
        "status": "error",
        "error_code": "PROVIDER_REQUEST_FAILED",
        "error": f"Provider request failed ({type(exc).__name__}).",
    }
