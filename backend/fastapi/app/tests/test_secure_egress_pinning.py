"""Outbound requests must connect to the exact IP address that was validated."""

from __future__ import annotations

import socket

import httpcore
import pytest

from backend.fastapi.app.domains.identity.secure_egress import (
    UnsafeOutboundURL,
    _PinnedNetworkBackend,
    resolve_outbound_target,
)


def _answer(address: str, family: int = socket.AF_INET):
    packed = (address, 443) if family == socket.AF_INET else (address, 0, 0, 0, 443)
    return [(family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", packed)]


class _RecordingBackend:
    def __init__(self):
        self.calls = []

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        self.calls.append((host, port))
        return object()

    def connect_unix_socket(self, *args, **kwargs):
        raise AssertionError("Unix sockets are not valid outbound connector targets")

    def sleep(self, seconds):
        return None


def test_resolves_once_and_connects_to_the_pinned_public_ip(monkeypatch):
    calls = []

    def resolve(host, port, *, type):
        calls.append((host, port))
        return _answer("93.184.216.34")

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    target = resolve_outbound_target("https://hooks.example.test:8443/webhook")
    backend = _RecordingBackend()
    pinned = _PinnedNetworkBackend(target, backend)

    pinned.connect_tcp(target.host, target.port)

    assert calls == [("hooks.example.test", 8443)]
    assert backend.calls == [("93.184.216.34", 8443)]
    assert target.url == "https://hooks.example.test:8443/webhook"


def test_rejects_mixed_public_and_private_dns_answers(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, *, type: _answer("93.184.216.34") + _answer("10.0.0.8"),
    )
    with pytest.raises(UnsafeOutboundURL):
        resolve_outbound_target("https://hooks.example.test/webhook")


def test_pinned_backend_rejects_unexpected_origin_and_port(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, *, type: _answer("93.184.216.34"))
    target = resolve_outbound_target("https://hooks.example.test/webhook")
    backend = _RecordingBackend()
    pinned = _PinnedNetworkBackend(target, backend)

    with pytest.raises(httpcore.ConnectError):
        pinned.connect_tcp("attacker.example", 443)
    with pytest.raises(httpcore.ConnectError):
        pinned.connect_tcp("hooks.example.test", 444)
    assert backend.calls == []


def test_rejects_public_redirect_target_until_it_is_independently_pinned(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, *, type: _answer("93.184.216.34"))
    first = resolve_outbound_target("https://hooks.example.test/webhook")
    redirect_backend = _RecordingBackend()
    pinned = _PinnedNetworkBackend(first, redirect_backend)

    with pytest.raises(httpcore.ConnectError):
        pinned.connect_tcp("redirect.example", 443)
    assert redirect_backend.calls == []


def test_transport_preserves_hostname_for_host_header_and_tls(monkeypatch):
    from backend.fastapi.app.domains.identity import secure_egress

    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port, *, type: _answer("93.184.216.34"))
    target = secure_egress.resolve_outbound_target("https://hooks.example.test/webhook")
    transport = secure_egress._PinnedHTTPTransport(target)

    class FakeResponseStream:
        def __iter__(self):
            return iter(())

        def close(self):
            pass

    class FakePool:
        def handle_request(self, request):
            assert request.url.host == b"hooks.example.test"
            assert request.url.port is None
            assert any(name.lower() == b"host" and value == b"hooks.example.test" for name, value in request.headers)
            return type(
                "Response", (), {"status": 204, "headers": [], "stream": FakeResponseStream(), "extensions": {}}
            )()

        def close(self):
            pass

    transport._pool.close()
    transport._pool = FakePool()
    import httpx

    response = transport.handle_request(httpx.Request("POST", target.url))
    assert response.status_code == 204
    assert transport._pool is not None


def test_outbound_request_does_not_follow_redirects(monkeypatch):
    import httpx
    from backend.fastapi.app.domains.identity import secure_egress

    target = secure_egress.OutboundTarget(
        url="https://hooks.example.test/webhook",
        host="hooks.example.test",
        port=443,
        address="93.184.216.34",
    )
    seen = []

    def respond(request):
        seen.append(request)
        return httpx.Response(302, headers={"Location": "https://redirect.example/"})

    monkeypatch.setattr(secure_egress, "_PinnedHTTPTransport", lambda _: httpx.MockTransport(respond))
    response = secure_egress.outbound_request("POST", target, json={"value": "test"})

    assert response.status_code == 302
    assert len(seen) == 1
    assert seen[0].url.host == "hooks.example.test"


def test_production_vendor_credentials_remain_tenant_scoped_with_test_marker(monkeypatch):
    from backend.fastapi.app.domains.integrations.platforms.services import clients

    seen = []
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "leaked-marker")
    monkeypatch.setattr(
        clients._vendor_manager,
        "ensure_tenant_vendor",
        lambda tenant_id, vendor_id: seen.append((tenant_id, vendor_id)) or "org-a::" + vendor_id,
    )

    result = clients._platform_vendor_id("twitter", "org-a")

    assert result == "org-a::twitter_api"
    assert seen == [("org-a", "twitter_api")]
