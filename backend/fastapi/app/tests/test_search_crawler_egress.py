from __future__ import annotations

import socket
from threading import RLock

import httpx
import pytest
from fastapi import HTTPException

from backend.fastapi.app import deps
from backend.fastapi.app.domains.identity import secure_egress
from backend.fastapi.app.domains.search.crawlers import runtime as crawler_runtime
from backend.fastapi.app.domains.search.crawlers.operations import (
    cloudflare_sync,
    deploy_snippets_bulk,
    execute_automation_run,
    now_iso,
)
from backend.fastapi.app.domains.search.crawlers.schemas import (
    AutomationRunRequest,
    SsrRenderRequest,
    VisibilityAuditRequest,
)


def _public_answer(host: str, port: int, *, type: int):
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]


def _runtime(*, site_url: str = "https://example.com/page") -> crawler_runtime.ContextRuntime:
    return crawler_runtime.ContextRuntime(
        _lock=RLock(),
        audit_log_memory=[],
        audit_results_memory=[],
        automation_runs_memory=[],
        automation_schedules_memory=[],
        crawler_events_memory=[],
        crawler_rules_memory=[],
        enforce_rate_limit=lambda *_: None,
        sites_memory=[
            {
                "id": "site-a",
                "tenant_id": "org-a",
                "domain": "example.com",
                "url": site_url,
                "snippet_key": "snippet-key-1",
            }
        ],
        ssr_cache_memory=[],
    )


def test_safe_get_revalidates_redirect_and_strips_credentials_cross_origin(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    responses = [
        httpx.Response(302, headers={"Location": "https://second.example/final"}),
        httpx.Response(200, text="page"),
    ]
    requests = []

    def request(method, target, **kwargs):
        requests.append((method, target, kwargs))
        return responses.pop(0)

    monkeypatch.setattr(secure_egress, "outbound_request", request)
    response = secure_egress.safe_outbound_get(
        "https://first.example/start",
        headers={
            "Authorization": "secret",
            "Cookie": "private=1",
            "X-Tenant-Id": "org-a",
            "User-Agent": "crawler",
        },
    )

    assert response.status_code == 200
    assert [item[1].host for item in requests] == ["first.example", "second.example"]
    assert requests[0][2]["headers"]["Authorization"] == "secret"
    assert "Authorization" not in requests[1][2]["headers"]
    assert "Cookie" not in requests[1][2]["headers"]
    assert "X-Tenant-Id" not in requests[1][2]["headers"]
    assert requests[1][2]["headers"]["User-Agent"] == "crawler"


def test_safe_get_rejects_private_redirect_before_second_request(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    requests = []

    def request(method, target, **kwargs):
        requests.append(target)
        return httpx.Response(302, headers={"Location": "https://127.0.0.1/admin"})

    monkeypatch.setattr(secure_egress, "outbound_request", request)
    with pytest.raises(secure_egress.UnsafeOutboundURL):
        secure_egress.safe_outbound_get("https://first.example/start")
    assert len(requests) == 1


def test_safe_get_allows_public_http_page_and_pins_default_port(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    requests = []

    def request(method, target, **kwargs):
        requests.append((method, target, kwargs))
        return httpx.Response(200, text="page")

    monkeypatch.setattr(secure_egress, "outbound_request", request)
    response = secure_egress.safe_outbound_get("http://example.com/page", allow_http=True)

    assert response.status_code == 200
    assert requests[0][1].port == 80
    assert requests[0][1].address == "93.184.216.34"


def test_registered_site_fetch_does_not_follow_to_another_public_host(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    requests = []

    def request(method, target, **kwargs):
        requests.append(target)
        return httpx.Response(302, headers={"Location": "https://attacker.example/collect"})

    monkeypatch.setattr(secure_egress, "outbound_request", request)
    pinned = now_iso.helper_validate_site_url("example.com", "https://shop.example.com/page")
    with pytest.raises(secure_egress.UnsafeOutboundURL):
        secure_egress.safe_outbound_get(pinned, allowed_host_suffix="example.com")
    assert len(requests) == 1


def test_outbound_response_body_is_bounded(monkeypatch):
    response = httpx.Response(200, content=b"12345")

    class ClientStub:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            response.close()

        def stream(self, *_args, **_kwargs):
            class ResponseContext:
                def __enter__(self):
                    return response

                def __exit__(self, *_args):
                    response.close()

            return ResponseContext()

    monkeypatch.setattr(secure_egress.httpx, "Client", lambda **_kwargs: ClientStub())
    target = secure_egress.OutboundTarget("https://example.com/", "example.com", 443, "93.184.216.34")
    with pytest.raises(secure_egress.OutboundResponseTooLarge):
        secure_egress.outbound_request("GET", target, max_response_bytes=4)


def test_visibility_audit_fetches_real_page_without_placeholder(monkeypatch):
    body = "<html><body>" + ("real page content " * 50) + "</body></html>"
    seen = []
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)

    def fake_fetch(url, **kwargs):
        seen.append((url, kwargs))
        return httpx.Response(200, text=body)

    monkeypatch.delenv("SSR_PROXY_URL", raising=False)
    monkeypatch.setattr(now_iso, "safe_outbound_get", fake_fetch)
    result = cloudflare_sync.execute_run_visibility_audit(
        _runtime(),
        VisibilityAuditRequest(url="https://example.com/page", site_id="site-a", crawlers_to_test=["GPTBot"]),
        deps.AuthContext(tenant_id="org-a"),
    )

    assert seen and seen[0][0].url == "https://example.com/page"
    assert result["audit"]["results"][0]["status_code"] == 200
    assert result["audit"]["results"][0]["content_length"] == len(body)
    assert result["audit"]["results"][0]["issue"] is None


def test_snippet_verification_uses_registered_public_page_target(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    requested = []

    def fake_fetch(target, **kwargs):
        requested.append((target, kwargs))
        return httpx.Response(200, text="<script>ace-key-1</script>")

    monkeypatch.setattr(now_iso, "safe_outbound_get", fake_fetch)
    installed, detail = now_iso.helper_verify_snippet_installation(
        "ace-key-1", "https://shop.example.com/page", site_domain="example.com"
    )

    assert installed is True
    assert "detected" in detail
    assert requested[0][0].address == "93.184.216.34"
    assert requested[0][1]["allow_http"] is True


def test_private_deployment_webhook_is_not_sent(monkeypatch):
    runtime = _runtime()
    runtime.sites_memory[0]["deployment_webhook_url"] = "https://127.0.0.1/hook"

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("unsafe webhook must not reach the network")

    monkeypatch.setattr(execute_automation_run, "outbound_request", fail_if_called)
    result = execute_automation_run.helper_execute_automation_run(
        runtime,
        "org-a",
        AutomationRunRequest(
            site_id="site-a",
            page_url="https://example.com/page",
            deploy_snippet=True,
            verify_snippet=False,
            sync_cloudflare=False,
            run_visibility_audit=False,
        ),
        trigger="manual",
    )

    deploy_step = next(step for step in result["steps"] if step["step"] == "deploy_snippet")
    assert deploy_step["status"] == "failed"
    assert "not allowed" in deploy_step["detail"]


def test_bulk_deployment_rejects_private_webhook_without_network_call(monkeypatch):
    runtime = _runtime()
    runtime.sites_memory[0]["deployment_webhook_url"] = "https://10.0.0.5/deploy"

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("unsafe bulk webhook must not reach the network")

    monkeypatch.setattr(deploy_snippets_bulk, "outbound_request", fail_if_called)
    result = deploy_snippets_bulk.execute_deploy_snippets_bulk(
        runtime,
        deploy_snippets_bulk.BulkSnippetDeployRequest(),
        deps.AuthContext(tenant_id="org-a"),
    )

    assert result["summary"]["failed"] == 1
    assert result["deployments"][0]["status"] == "failed"


def test_ssr_render_requires_the_site_owned_host(monkeypatch):
    monkeypatch.setenv("SSR_PROXY_URL", "https://render.example.net")
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("site-mismatched render must not reach the provider")

    monkeypatch.setattr(deploy_snippets_bulk, "outbound_request", fail_if_called)
    with pytest.raises(HTTPException) as exc_info:
        deploy_snippets_bulk.execute_request_ssr_render(
            _runtime(),
            SsrRenderRequest(url="https://attacker.example/page", site_id="site-a"),
            deps.AuthContext(tenant_id="org-a"),
        )
    assert exc_info.value.status_code == 422


def test_ssr_render_uses_pinned_proxy_and_only_caches_real_output(monkeypatch):
    monkeypatch.setenv("SSR_PROXY_URL", "https://render.example.net")
    monkeypatch.setattr(socket, "getaddrinfo", _public_answer)
    requests = []

    def fake_request(method, target, **kwargs):
        requests.append((method, target, kwargs))
        return httpx.Response(200, text="<html><body>rendered</body></html>")

    monkeypatch.setattr(deploy_snippets_bulk, "outbound_request", fake_request)
    result = deploy_snippets_bulk.execute_request_ssr_render(
        _runtime(),
        SsrRenderRequest(url="https://shop.example.com/page", site_id="site-a"),
        deps.AuthContext(tenant_id="org-a"),
    )

    assert result["status"] == "ok"
    assert result["source"] == "proxy"
    assert requests[0][1].host == "render.example.net"
    assert requests[0][2]["params"]["url"] == "https://shop.example.com/page"
    assert result["render"]["rendered_html_length"] == len("<html><body>rendered</body></html>")


def test_ssr_render_does_not_return_stub_success_when_provider_is_missing(monkeypatch):
    monkeypatch.delenv("SSR_PROXY_URL", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        deploy_snippets_bulk.execute_request_ssr_render(
            _runtime(),
            SsrRenderRequest(url="https://example.com/page", site_id="site-a"),
            deps.AuthContext(tenant_id="org-a"),
        )
    assert exc_info.value.status_code == 503
