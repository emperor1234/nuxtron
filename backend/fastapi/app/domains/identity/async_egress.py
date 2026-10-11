"""Async DNS-pinned HTTP egress for tenant-controlled page and provider URLs."""

from __future__ import annotations

import asyncio
import ssl
from urllib.parse import urljoin, urlsplit

import httpcore
import httpx

from .secure_egress import OutboundResponseTooLarge
from .secure_egress import OutboundTarget
from .secure_egress import UnsafeOutboundURL
from .secure_egress import _normalize_host
from .secure_egress import resolve_outbound_target


class _PinnedAsyncNetworkBackend(httpcore.AsyncNetworkBackend):
    """Connect the verified origin to its resolved public address at TCP time."""

    def __init__(self, target: OutboundTarget, backend: httpcore.AsyncNetworkBackend | None = None) -> None:
        self._target = target
        self._backend = backend or httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        try:
            requested_host = _normalize_host(host)
        except UnsafeOutboundURL as exc:
            raise httpcore.ConnectError("Outbound request attempted an invalid origin.") from exc
        if requested_host != self._target.host or port != self._target.port:
            raise httpcore.ConnectError("Outbound request attempted an unvalidated origin.")
        return await self._backend.connect_tcp(
            self._target.address,
            self._target.port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    async def connect_unix_socket(self, path, timeout=None, socket_options=None):
        raise httpcore.ConnectError("Unix sockets are not permitted for connector egress.")

    async def sleep(self, seconds: float) -> None:
        await self._backend.sleep(seconds)


class _PinnedAsyncResponseStream(httpx.AsyncByteStream):
    def __init__(self, stream) -> None:
        self._stream = stream

    async def __aiter__(self):
        async for chunk in self._stream:
            yield chunk

    async def aclose(self) -> None:
        await self._stream.aclose()


class _PinnedAsyncHTTPTransport(httpx.AsyncBaseTransport):
    """HTTPX async transport backed by a DNS-pinned HTTPCore pool."""

    def __init__(self, target: OutboundTarget) -> None:
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(),
            max_connections=4,
            max_keepalive_connections=0,
            retries=0,
            network_backend=_PinnedAsyncNetworkBackend(target),
        )

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        core_request = httpcore.Request(
            method=request.method,
            url=httpcore.URL(
                scheme=request.url.raw_scheme,
                host=request.url.raw_host,
                port=request.url.port,
                target=request.url.raw_path,
            ),
            headers=request.headers.raw,
            content=request.stream,
            extensions=request.extensions,
        )
        try:
            response = await self._pool.handle_async_request(core_request)
        except httpcore.TimeoutException as exc:
            raise httpx.TimeoutException(str(exc), request=request) from exc
        except httpcore.NetworkError as exc:
            raise httpx.NetworkError(str(exc), request=request) from exc
        except httpcore.ProtocolError as exc:
            raise httpx.ProtocolError(str(exc), request=request) from exc
        return httpx.Response(
            status_code=response.status,
            headers=response.headers,
            stream=_PinnedAsyncResponseStream(response.stream),
            extensions=response.extensions,
            request=request,
        )

    async def aclose(self) -> None:
        await self._pool.aclose()


async def resolve_outbound_target_async(
    url: str | OutboundTarget,
    *,
    allow_http: bool = False,
) -> OutboundTarget:
    """Resolve and validate an outbound destination without blocking the event loop."""
    if isinstance(url, OutboundTarget):
        return url
    return await asyncio.to_thread(resolve_outbound_target, url, allow_http=allow_http)


async def outbound_async_request(
    method: str,
    target: OutboundTarget,
    *,
    max_response_bytes: int = 2_000_000,
    **kwargs,
) -> httpx.Response:
    """Send one bounded async request through the validated, pinned origin."""
    if max_response_bytes < 1:
        raise ValueError("max_response_bytes must be positive.")
    timeout = kwargs.pop("timeout", 15.0)
    async with httpx.AsyncClient(
        transport=_PinnedAsyncHTTPTransport(target),
        trust_env=False,
        follow_redirects=False,
        timeout=timeout,
    ) as client:
        async with client.stream(method, target.url, **kwargs) as response:
            body = bytearray()
            async for chunk in response.aiter_bytes():
                if len(body) + len(chunk) > max_response_bytes:
                    raise OutboundResponseTooLarge("Outbound response exceeded its configured size limit.")
                body.extend(chunk)
            return httpx.Response(
                status_code=response.status_code,
                headers=response.headers,
                content=bytes(body),
                extensions=response.extensions,
                request=response.request,
            )


def _validate_suffix(target: OutboundTarget, allowed_host_suffix: str | None) -> str | None:
    if not allowed_host_suffix:
        return None
    suffix = allowed_host_suffix.strip()
    if "://" in suffix:
        suffix = urlsplit(suffix).hostname or ""
    normalized = _normalize_host(suffix)
    if target.host != normalized and not target.host.endswith(f".{normalized}"):
        raise UnsafeOutboundURL("Outbound page is outside its registered hostname boundary.")
    return normalized


async def safe_outbound_get_async(
    url: str | OutboundTarget,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    max_redirects: int = 5,
    allow_http: bool = False,
    allowed_host_suffix: str | None = None,
    max_response_bytes: int = 2_000_000,
) -> httpx.Response:
    """Fetch a public page asynchronously, pinning and revalidating each redirect."""
    if not isinstance(max_redirects, int) or not 0 <= max_redirects <= 10:
        raise ValueError("max_redirects must be between 0 and 10.")
    request_headers = dict(headers or {})
    target = await resolve_outbound_target_async(url, allow_http=allow_http)
    suffix = _validate_suffix(target, allowed_host_suffix)
    redirect_statuses = {301, 302, 303, 307, 308}

    for redirect_count in range(max_redirects + 1):
        response = await outbound_async_request(
            "GET",
            target,
            headers=request_headers,
            timeout=timeout,
            max_response_bytes=max_response_bytes,
        )
        location = response.headers.get("location")
        if response.status_code not in redirect_statuses or not location:
            return response
        if redirect_count >= max_redirects:
            response.close()
            raise UnsafeOutboundURL("Outbound page exceeded the redirect limit.")

        previous_scheme = urlsplit(target.url).scheme.lower()
        try:
            next_target = await resolve_outbound_target_async(urljoin(target.url, location), allow_http=allow_http)
            if suffix and next_target.host != suffix and not next_target.host.endswith(f".{suffix}"):
                raise UnsafeOutboundURL("Outbound page redirected outside its registered hostname boundary.")
        except (TypeError, ValueError) as exc:
            response.close()
            raise UnsafeOutboundURL("Outbound page redirect destination is not allowed.") from exc
        next_scheme = urlsplit(next_target.url).scheme.lower()
        if previous_scheme == "https" and next_scheme != "https":
            response.close()
            raise UnsafeOutboundURL("Outbound page redirected from HTTPS to an insecure scheme.")
        if (target.host, target.port, previous_scheme) != (next_target.host, next_target.port, next_scheme):
            request_headers = {
                key: value
                for key, value in request_headers.items()
                if key.lower() in {"user-agent", "accept", "accept-language"}
            }
        response.close()
        target = next_target
    raise UnsafeOutboundURL("Outbound page exceeded the redirect limit.")
