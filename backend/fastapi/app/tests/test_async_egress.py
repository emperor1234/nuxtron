"""Tests for async DNS-pinned outbound egress; never uses a live network."""

from __future__ import annotations

import asyncio
import socket
import threading
from types import SimpleNamespace

import httpcore
import httpx
import pytest

from backend.fastapi.app.domains.identity import async_egress
from backend.fastapi.app.domains.identity import secure_egress


def _public_answer(host, port, *args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


class _AsyncStream:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.closed = False

    def __aiter__(self):
        async def chunks():
            yield self.body

        return chunks()

    async def aclose(self) -> None:
        self.closed = True


class _NetworkBackendStub:
    def __init__(self) -> None:
        self.connected = None

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        self.connected = (host, port)
        return object()

    async def connect_unix_socket(self, path, timeout=None, socket_options=None):
        raise AssertionError("Unix socket connection must never be requested")

    async def sleep(self, seconds: float) -> None:
        return None


class _PoolStub:
    instances = []
    response_body = b"async provider response"

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.request = None
        self.__class__.instances.append(self)

    async def handle_async_request(self, request):
        self.request = request
        return SimpleNamespace(
            status=200,
            headers=[(b"content-type", b"text/plain")],
            stream=_AsyncStream(self.response_body),
            extensions={},
        )

    async def aclose(self) -> None:
        return None


@pytest.fixture(autouse=True)
def clear_pool_stubs():
    _PoolStub.instances.clear()
    _PoolStub.response_body = b"async provider response"


def test_async_network_backend_pins_ip_and_rejects_unvalidated_origin():
    target = secure_egress.OutboundTarget("https://example.com/path", "example.com", 443, "93.184.216.34")
    backend = _NetworkBackendStub()
    pinned = async_egress._PinnedAsyncNetworkBackend(target, backend)

    asyncio.run(pinned.connect_tcp("example.com", 443))
    assert backend.connected == ("93.184.216.34", 443)

    with pytest.raises(httpcore.ConnectError):
        asyncio.run(pinned.connect_tcp("other.example", 443))


def test_async_target_resolution_runs_off_event_loop(monkeypatch):
    event_loop_thread = threading.get_ident()
    resolver_threads = []
    target = secure_egress.OutboundTarget("https://example.com/path", "example.com", 443, "93.184.216.34")

    def resolve(url, *, allow_http=False):
        resolver_threads.append(threading.get_ident())
        return target

    monkeypatch.setattr(async_egress, "resolve_outbound_target", resolve)
    resolved = asyncio.run(async_egress.resolve_outbound_target_async("https://example.com/path"))

    assert resolved is target
    assert resolver_threads
    assert resolver_threads[0] != event_loop_thread


def test_async_request_preserves_original_http_origin_and_caps_body(monkeypatch):
    monkeypatch.setattr(async_egress.httpcore, "AsyncConnectionPool", _PoolStub)
    target = secure_egress.OutboundTarget("https://example.com/path", "example.com", 443, "93.184.216.34")

    response = asyncio.run(async_egress.outbound_async_request("GET", target))
    pool = _PoolStub.instances[-1]
    request_headers = {key.decode().lower(): value.decode() for key, value in pool.request.headers}

    assert response.content == b"async provider response"
    assert pool.request.url.host == b"example.com"
    assert request_headers["host"] == "example.com"
    assert pool.kwargs["network_backend"]._target.address == "93.184.216.34"

    _PoolStub.response_body = b"x" * 12
    with pytest.raises(secure_egress.OutboundResponseTooLarge):
        asyncio.run(async_egress.outbound_async_request("GET", target, max_response_bytes=8))


def test_async_safe_get_revalidates_redirect_and_strips_cross_origin_headers(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    seen = []
    responses = [
        httpx.Response(302, headers={"Location": "https://other.example/next"}),
        httpx.Response(200, text="done"),
    ]

    async def request(method, target, **kwargs):
        seen.append((method, target, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(async_egress, "outbound_async_request", request)
    result = asyncio.run(
        async_egress.safe_outbound_get_async(
            "https://example.com/start",
            headers={"Authorization": "secret", "X-Tenant-Id": "org-a", "User-Agent": "crawler"},
        )
    )

    assert result.status_code == 200
    assert len(seen) == 2
    assert seen[0][1].address == seen[1][1].address
    assert "Authorization" not in seen[1][2]["headers"]
    assert "X-Tenant-Id" not in seen[1][2]["headers"]
    assert seen[1][2]["headers"]["User-Agent"] == "crawler"


def test_async_safe_get_rejects_private_redirect_before_second_request(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    seen = []

    async def request(method, target, **kwargs):
        seen.append(target)
        return httpx.Response(302, headers={"Location": "https://127.0.0.1/admin"})

    monkeypatch.setattr(async_egress, "outbound_async_request", request)
    with pytest.raises(secure_egress.UnsafeOutboundURL):
        asyncio.run(async_egress.safe_outbound_get_async("https://example.com/start"))
    assert len(seen) == 1


def test_async_safe_get_keeps_registered_site_redirects_on_same_host_boundary(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    seen = []

    async def request(method, target, **kwargs):
        seen.append(target)
        return httpx.Response(302, headers={"Location": "https://attacker.example/collect"})

    monkeypatch.setattr(async_egress, "outbound_async_request", request)
    with pytest.raises(secure_egress.UnsafeOutboundURL):
        asyncio.run(
            async_egress.safe_outbound_get_async(
                "https://shop.example.com/start",
                allowed_host_suffix="example.com",
            )
        )
    assert len(seen) == 1
