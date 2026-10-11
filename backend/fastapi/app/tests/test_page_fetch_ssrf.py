"""SSRF regressions for user-supplied site URLs across Social and SEO features."""

from __future__ import annotations

import asyncio
import socket
from contextlib import nullcontext

import httpx

from backend.fastapi.app.domains.seo.platform.services import get_shared_job_store
from backend.fastapi.app.domains.seo.services import seo_ai_service
from backend.fastapi.app.domains.social.services import website


def _public_answer(host, port, *args, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def test_social_website_fetch_rejects_private_target(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("private site must not reach an HTTP transport")

    monkeypatch.setattr(website, "safe_outbound_get", fail_if_called)
    assert website._fetch_html("https://127.0.0.1/admin") == ""


def test_social_website_fetch_uses_pinned_bounded_request(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    seen = []

    def fake_fetch(target, **kwargs):
        seen.append((target, kwargs))
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<title>brand</title>")

    monkeypatch.setattr(website, "safe_outbound_get", fake_fetch)
    assert website._fetch_html("https://shop.example.com/") == "<title>brand</title>"
    assert seen[0][0].address == "93.184.216.34"
    assert seen[0][1]["allowed_host_suffix"] == "shop.example.com"
    assert seen[0][1]["max_response_bytes"] == 300_000


def test_seo_ai_fetch_rejects_private_target_before_transport(monkeypatch):
    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("private site must not reach an async HTTP transport")

    monkeypatch.setattr(seo_ai_service, "safe_outbound_get_async", fail_if_called)
    result = asyncio.run(seo_ai_service.fetch_page_signals("http://127.0.0.1/admin"))
    assert result["fetch_ok"] is False
    assert result["error"] == "page_fetch_unavailable"


def test_seo_ai_fetch_uses_pinned_async_target(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    seen = []

    async def fake_fetch(target, **kwargs):
        seen.append((target, kwargs))
        request = httpx.Request("GET", target.url)
        return httpx.Response(200, request=request, text="<title>Acme</title><h1>Services</h1>")

    monkeypatch.setattr(seo_ai_service, "safe_outbound_get_async", fake_fetch)
    result = asyncio.run(seo_ai_service.fetch_page_signals("https://example.com"))

    assert result["fetch_ok"] is True
    assert result["title"] == "Acme"
    assert seen[0][0].address == "93.184.216.34"
    assert seen[0][1]["allowed_host_suffix"] == "example.com"
    assert seen[0][1]["max_response_bytes"] == seo_ai_service._MAX_HTML_BYTES


def test_seo_performance_page_probe_rejects_private_target(monkeypatch):
    async def fail_if_called(*_args, **_kwargs):
        raise AssertionError("private probe must not reach an async HTTP transport")

    monkeypatch.setattr(get_shared_job_store, "safe_outbound_get_async", fail_if_called)
    assert asyncio.run(get_shared_job_store._run_http_probe("https://10.0.0.2/")) is None


def test_seo_performance_network_probe_rejects_private_target(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("private probe must not open a socket")

    monkeypatch.setattr(socket, "create_connection", fail_if_called)
    assert get_shared_job_store._run_network_probe_sync("https://169.254.169.254/latest/meta-data/") is None


def test_seo_performance_network_probe_connects_to_validated_public_ip(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    connected = []

    def fake_connect(address, timeout):
        connected.append((address, timeout))
        return nullcontext()

    monkeypatch.setattr(socket, "create_connection", fake_connect)
    result = get_shared_job_store._run_network_probe_sync("https://example.com/")

    assert result is not None
    assert result["ip"] == "93.184.216.34"
    assert connected[0][0] == ("93.184.216.34", 443)
