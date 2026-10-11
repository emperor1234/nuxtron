"""Tenant-controlled HTTPS egress with DNS validation pinned to the TCP connect."""

from __future__ import annotations

import ipaddress
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpcore
import httpx


class UnsafeOutboundURL(ValueError):
    """Raised when a tenant-controlled outbound destination is not safe."""


class OutboundResponseTooLarge(ValueError):
    """Raised when an outbound response exceeds its configured memory bound."""


@dataclass(frozen=True, slots=True)
class OutboundTarget:
    """Validated target; the hostname remains intact for Host and TLS SNI."""

    url: str
    host: str
    port: int
    address: str


def _normalize_host(host: str) -> str:
    candidate = host.strip().rstrip(".").lower()
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        try:
            return candidate.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise UnsafeOutboundURL("Outbound connector hostname is invalid.") from exc


def _is_public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        address.is_global
        and not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        )
        and str(address) not in {"169.254.169.254", "100.100.100.200"}
    )


def resolve_outbound_target(url: str, *, allow_http: bool = False) -> OutboundTarget:
    """Resolve once, reject any unsafe DNS answer, and return the IP to pin."""
    candidate = url.strip()
    try:
        parsed = urlsplit(candidate)
    except ValueError as exc:
        raise UnsafeOutboundURL("Outbound connector URL is malformed.") from exc
    scheme = parsed.scheme.lower()
    allowed_schemes = {"https", "http"} if allow_http else {"https"}
    if scheme not in allowed_schemes or not parsed.hostname:
        raise UnsafeOutboundURL("Outbound URLs must use an allowed scheme and a hostname.")
    if parsed.username or parsed.password:
        raise UnsafeOutboundURL("Outbound connector URLs cannot contain userinfo.")
    try:
        parsed_port = parsed.port
    except ValueError as exc:
        raise UnsafeOutboundURL("Outbound connector URL has an invalid port.") from exc
    if parsed_port == 0:
        raise UnsafeOutboundURL("Outbound connector URL has an invalid port.")
    port = parsed_port or (80 if scheme == "http" else 443)
    host = _normalize_host(parsed.hostname)

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        try:
            records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except (OSError, ValueError) as exc:
            raise UnsafeOutboundURL("Outbound connector hostname could not be resolved safely.") from exc
        answers = set()
        for record in records:
            try:
                answers.add(ipaddress.ip_address(record[4][0].split("%", 1)[0]))
            except (IndexError, TypeError, ValueError) as exc:
                raise UnsafeOutboundURL("Outbound connector DNS returned an invalid address.") from exc
    else:
        answers = {literal}

    if not answers or any(not _is_public_address(address) for address in answers):
        raise UnsafeOutboundURL("Outbound connector target resolves to a blocked network.")
    address = sorted(answers, key=lambda item: (item.version, int(item)))[0]
    return OutboundTarget(url=candidate, host=host, port=port, address=str(address))


class _PinnedNetworkBackend(httpcore.NetworkBackend):
    """Map the original HTTP origin to its already-validated address at connect time."""

    def __init__(self, target: OutboundTarget, backend: httpcore.NetworkBackend | None = None):
        self._target = target
        self._backend = backend or httpcore.SyncBackend()

    def connect_tcp(self, host: str, port: int, timeout=None, local_address=None, socket_options=None):
        try:
            requested_host = _normalize_host(host)
        except UnsafeOutboundURL as exc:
            raise httpcore.ConnectError("Outbound request attempted an invalid origin.") from exc
        if requested_host != self._target.host or port != self._target.port:
            raise httpcore.ConnectError("Outbound request attempted an unvalidated origin.")
        return self._backend.connect_tcp(
            self._target.address,
            self._target.port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    def connect_unix_socket(self, path: str, timeout=None, socket_options=None):
        raise httpcore.ConnectError("Unix sockets are not permitted for connector egress.")

    def sleep(self, seconds: float) -> None:
        self._backend.sleep(seconds)


class _SyncResponseStream(httpx.SyncByteStream):
    def __init__(self, stream):
        self._stream = stream

    def __iter__(self):
        yield from self._stream

    def close(self) -> None:
        self._stream.close()


class _PinnedHTTPTransport(httpx.BaseTransport):
    """HTTPX transport using an explicit pool and a pinned TCP network backend."""

    def __init__(self, target: OutboundTarget):
        self._pool = httpcore.ConnectionPool(
            ssl_context=ssl.create_default_context(),
            max_connections=4,
            max_keepalive_connections=0,
            retries=0,
            network_backend=_PinnedNetworkBackend(target),
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
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
            response = self._pool.handle_request(core_request)
        except httpcore.TimeoutException as exc:
            raise httpx.TimeoutException(str(exc), request=request) from exc
        except httpcore.NetworkError as exc:
            raise httpx.NetworkError(str(exc), request=request) from exc
        except httpcore.ProtocolError as exc:
            raise httpx.ProtocolError(str(exc), request=request) from exc
        return httpx.Response(
            status_code=response.status,
            headers=response.headers,
            stream=_SyncResponseStream(response.stream),
            extensions=response.extensions,
            request=request,
        )

    def close(self) -> None:
        self._pool.close()


def outbound_request(
    method: str,
    target: OutboundTarget,
    *,
    max_response_bytes: int = 2_000_000,
    **kwargs,
) -> httpx.Response:
    """Send one bounded request over pinned IP, preserving host identity and no redirects."""
    if max_response_bytes < 1:
        raise ValueError("max_response_bytes must be positive.")
    timeout = kwargs.pop("timeout", 15.0)
    with httpx.Client(
        transport=_PinnedHTTPTransport(target),
        trust_env=False,
        follow_redirects=False,
        timeout=timeout,
    ) as client:
        with client.stream(method, target.url, **kwargs) as response:
            body = bytearray()
            for chunk in response.iter_bytes():
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


def safe_outbound_get(
    url: str | OutboundTarget,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
    max_redirects: int = 5,
    allow_http: bool = False,
    allowed_host_suffix: str | None = None,
    max_response_bytes: int = 2_000_000,
) -> httpx.Response:
    """GET a public URL, pinning each redirect hop and bounding the response body."""
    if not isinstance(max_redirects, int) or not 0 <= max_redirects <= 10:
        raise ValueError("max_redirects must be between 0 and 10.")
    request_headers = dict(headers or {})
    target = url if isinstance(url, OutboundTarget) else resolve_outbound_target(url, allow_http=allow_http)
    normalized_suffix = None
    if allowed_host_suffix:
        suffix = allowed_host_suffix.strip()
        if "://" in suffix:
            suffix = urlsplit(suffix).hostname or ""
        normalized_suffix = _normalize_host(suffix)
        if target.host != normalized_suffix and not target.host.endswith(f".{normalized_suffix}"):
            raise UnsafeOutboundURL("Outbound page is outside its registered hostname boundary.")
    redirect_statuses = {301, 302, 303, 307, 308}

    for redirect_count in range(max_redirects + 1):
        response = outbound_request(
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
            next_url = urljoin(target.url, location)
            next_target = resolve_outbound_target(next_url, allow_http=allow_http)
            if (
                normalized_suffix
                and next_target.host != normalized_suffix
                and not next_target.host.endswith(f".{normalized_suffix}")
            ):
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


def validate_outbound_url(url: str) -> str:
    """Compatibility preflight only; use outbound_request for the actual pinned connection."""
    return resolve_outbound_target(url).url
