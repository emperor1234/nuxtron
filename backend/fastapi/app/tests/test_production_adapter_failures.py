"""Production adapters must not fabricate delivery or storage acceptance."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    return SimpleNamespace(tenant_id="org-regression")


def test_storage_presign_requires_provider(production, monkeypatch):
    from backend.fastapi.app.domains.content import storage

    monkeypatch.setattr(storage, "_enforce_rate_limit", lambda *a, **k: None)
    monkeypatch.delenv("MINIO_ENDPOINT", raising=False)
    before = len(storage._minio_objects_memory)
    with pytest.raises(HTTPException) as caught:
        storage.storage_presign(storage.MinioPresignRequest(bucket="media", object_key="file.png"), production)
    assert caught.value.status_code == 503
    assert len(storage._minio_objects_memory) == before


def test_n8n_missing_provider_cannot_acknowledge_a_job(production, monkeypatch):
    from backend.fastapi.app.domains.integrations import webhooks

    monkeypatch.setattr(webhooks, "_enforce_rate_limit", lambda *a, **k: None)
    monkeypatch.delenv("N8N_WEBHOOK_URL", raising=False)
    before = len(webhooks._n8n_jobs_memory)
    with pytest.raises(HTTPException) as caught:
        webhooks.trigger_n8n_webhook(webhooks.N8nWebhookTriggerRequest(workflow="publish"), production)
    assert caught.value.status_code == 503
    assert len(webhooks._n8n_jobs_memory) == before


def test_missing_feature_flags_never_enable_production_behavior(production, monkeypatch):
    from backend.fastapi.app.domains.integrations import webhooks

    monkeypatch.setattr(webhooks, "_enforce_rate_limit", lambda *a, **k: None)
    monkeypatch.delenv("GROWTHBOOK_API_URL", raising=False)
    result = webhooks.evaluate_growthbook_flag(
        webhooks.GrowthbookEvaluateRequest(feature_key="privileged-feature"), production
    )
    assert result["result"]["enabled"] is False


def test_legacy_json_webhook_ingress_is_not_trusted_in_production(production, monkeypatch):
    from backend.fastapi.app.domains.integrations import webhooks

    monkeypatch.setattr(webhooks, "_enforce_rate_limit", lambda *a, **k: None)
    before = len(webhooks._webhook_events_memory)
    with pytest.raises(HTTPException) as caught:
        webhooks.receive_webhook(
            "generic", webhooks.WebhookAcknowledgeRequest(provider="generic", event_type="payment"), production
        )
    assert caught.value.status_code == 501
    assert len(webhooks._webhook_events_memory) == before


def test_social_production_audit_uses_durable_writer(production, monkeypatch):
    from backend.fastapi.app.domains.social import persistence
    from backend.fastapi.app.domains.identity import security_audit

    records = []
    monkeypatch.setattr(security_audit, "record_security_event", lambda **kw: records.append(kw))
    state = persistence._SocialWorkspaceState(enforce_rate_limit=lambda *a, **k: None)
    persistence._sw_audit(state, production.tenant_id, "publishing.request", 12)
    assert len(records) == 1
    assert records[0]["tenant_id"] == production.tenant_id
    assert not state.audit_log


def test_audit_metadata_uses_typed_json_binding(monkeypatch):
    from contextlib import contextmanager
    from sqlalchemy import JSON
    from backend.fastapi.app.domains.identity import security_audit

    calls = []

    class Session:
        def execute(self, statement, parameters):
            calls.append((statement, parameters))

    @contextmanager
    def scoped(tenant_id):
        assert tenant_id == "org-regression"
        yield Session()

    monkeypatch.setattr(security_audit, "organization_scoped_session", scoped)
    security_audit.record_security_event(
        tenant_id="org-regression",
        event_type="security.test",
        principal_id="actor",
        auth_mode="test",
        method="POST",
        path="/test",
        request_id="request",
        client_ip="127.0.0.1",
        user_agent="test",
        metadata={"example": True},
    )
    statement, parameters = calls[0]
    assert isinstance(statement._bindparams["metadata"].type, JSON)
    assert parameters["metadata"] == {"example": True}
    assert parameters["ip_hash"] != "127.0.0.1"


@pytest.mark.parametrize("secret", ["", "short-key", "dev-secret-replace-in-production"])
def test_media_validation_rejects_unsafe_production_secret(production, monkeypatch, secret):
    from backend.fastapi.app.domains.content.media.services import processing

    monkeypatch.setenv("FASTAPI_SECRET", secret)
    with pytest.raises(HTTPException) as caught:
        processing._issue_validation_token("org-a", "object", "image/jpeg")
    assert caught.value.status_code == 503


def test_media_validation_binds_tenant_with_configured_secret(production, monkeypatch):
    from backend.fastapi.app.domains.content.media.services import processing

    monkeypatch.setenv("FASTAPI_SECRET", "disposable-secret-with-more-than-32-characters")
    assert processing._issue_validation_token("org-a", "object", "image/jpeg") != processing._issue_validation_token(
        "org-b", "object", "image/jpeg"
    )


def test_media_token_verifies_object_tenant_mime_and_expiry(production, monkeypatch):
    from backend.fastapi.app.domains.content.media.services import processing

    monkeypatch.setenv("FASTAPI_SECRET", "disposable-secret-with-more-than-32-characters")
    monkeypatch.setattr(processing.time, "time", lambda: 9000)
    token = processing._issue_validation_token("org-a", "uploads/object", "image/jpeg")
    assert processing._verify_validation_token(token, "org-a", "uploads/object", "image/jpeg")
    assert not processing._verify_validation_token(token, "org-b", "uploads/object", "image/jpeg")
    assert not processing._verify_validation_token(token, "org-a", "uploads/other", "image/jpeg")
    assert not processing._verify_validation_token(token, "org-a", "uploads/object", "image/png")
    monkeypatch.setattr(processing.time, "time", lambda: 9600)
    assert not processing._verify_validation_token(token, "org-a", "uploads/object", "image/jpeg")


def test_media_output_requires_real_production_presigner(production, monkeypatch):
    import threading
    from backend.fastapi.app.domains.content.media.operations import append_audit
    from backend.fastapi.app.domains.content.media.schemas import MediaOutputUrlRequest
    from backend.fastapi.app.domains.content import storage

    runtime = SimpleNamespace(
        enforce_rate_limit=lambda *a, **k: None,
        _lock=threading.Lock(),
        media_jobs_memory=[
            {
                "id": 9,
                "tenant_id": production.tenant_id,
                "status": "complete",
                "output_key": "file",
                "output_bucket": "processed-output",
            }
        ],
    )
    monkeypatch.setattr(storage, "_minio_presign", None)
    with pytest.raises(HTTPException) as caught:
        append_audit.execute_get_output_signed_url(runtime, 9, MediaOutputUrlRequest(), production)
    assert caught.value.status_code == 503


def test_n8n_private_webhook_target_fails_closed_before_network(production, monkeypatch):
    from backend.fastapi.app.domains.integrations import webhooks

    monkeypatch.setattr(webhooks, "_enforce_rate_limit", lambda *a, **k: None)
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://127.0.0.1/internal")
    monkeypatch.setattr(webhooks, "outbound_request", lambda *a, **k: pytest.fail("unsafe target reached transport"))

    with pytest.raises(HTTPException) as caught:
        webhooks.trigger_n8n_webhook(webhooks.N8nWebhookTriggerRequest(workflow="publish"), production)
    assert caught.value.status_code == 503


def test_contentshake_private_publish_webhook_is_rejected(production, monkeypatch):
    from backend.fastapi.app.routers import contentshake_ai

    draft_id = "egress-private-target-test"
    contentshake_ai._drafts[production.tenant_id] = [
        {"id": draft_id, "title": "Test draft", "content": "", "status": "draft"}
    ]
    monkeypatch.setattr(
        contentshake_ai,
        "outbound_request",
        lambda *a, **k: pytest.fail("unsafe target reached transport"),
    )

    result = contentshake_ai.publish_draft(
        draft_id,
        contentshake_ai.PublishRequest(webhook_url="https://127.0.0.1/admin"),
        production,
    )
    assert result["webhook"].get("ok") is not True
    assert "UnsafeOutboundURL" in result["webhook"]["error"]
    assert "127.0.0.1" not in result["webhook"]["error"]
    contentshake_ai._drafts.pop(production.tenant_id, None)


def test_social_workspace_private_webhook_is_rejected(monkeypatch):
    from backend.fastapi.app.domains.social.services import workspace

    monkeypatch.setattr(
        workspace,
        "outbound_request",
        lambda *a, **k: pytest.fail("unsafe target reached transport"),
    )
    result = workspace._sw_deliver_webhook(
        "https://169.254.169.254/latest/meta-data/",
        "notification.created",
        {"message": "safe test payload"},
        secret="must-not-be-forwarded",
    )
    assert result["ok"] is False
    assert "169.254.169.254" not in result["error"]


def test_wordpress_tool_rejects_private_site_before_network(monkeypatch):
    import asyncio

    from backend.fastapi.app.agents.base import ToolType
    from backend.fastapi.app.agents import cms_tools

    tool = cms_tools.WordPressTool(
        ToolType.WORDPRESS_POST,
        {"WORDPRESS_SITE_URL": "https://127.0.0.1", "WORDPRESS_REST_API_TOKEN": "test-token"},
    )
    monkeypatch.setattr(
        cms_tools,
        "outbound_async_request",
        lambda *a, **k: pytest.fail("unsafe target reached transport"),
    )

    result = asyncio.run(tool.execute({"title": "test", "content": "body"}))
    assert result.success is False
    assert result.error == "WordPress site must resolve to an allowed public HTTPS destination."


def test_tool_connectivity_probe_rejects_private_provider_target(monkeypatch):
    import asyncio

    from backend.fastapi.app.routers import tool_integrations

    monkeypatch.setitem(
        tool_integrations._TOOL_MAP["dataforseo"],
        "test_url",
        "https://127.0.0.1/internal",
    )
    monkeypatch.setattr(
        tool_integrations,
        "outbound_async_request",
        lambda *a, **k: pytest.fail("unsafe target reached transport"),
    )
    endpoint = next(
        route.endpoint
        for route in tool_integrations.create_tool_integrations_router().routes
        if getattr(route, "name", "") == "test_tool"
    )

    result = asyncio.run(endpoint("dataforseo"))
    assert result["status"] == "error"
    assert result["reason"] == "Connection test failed."
    assert "127.0.0.1" not in result["reason"]


def test_client_portal_report_escapes_tenant_html_and_rejects_unsafe_logo():
    from backend.fastapi.app.routers.client_portal import _generate_html_report

    payload = "<script>alert('xss')</script>"
    report_html = _generate_html_report(
        {
            "name": payload,
            "agency_name": payload,
            "brand_color": "red; background:url(javascript:alert(1))",
            "logo_url": "javascript:alert(1)",
        },
        {"period": payload, "created_at": "2026-10-10", "domains": [payload]},
        {payload: payload},
    )

    assert payload not in report_html
    assert "&lt;script&gt;" in report_html
    assert "javascript:alert(1)" not in report_html
    assert "background: #4A90E2;" in report_html


def test_client_portal_logo_rejects_private_https_ip():
    from backend.fastapi.app.routers.client_portal import _safe_report_logo_src

    assert _safe_report_logo_src("https://127.0.0.1/logo.png") == ""
    assert _safe_report_logo_src("https://[::1]/logo.png") == ""
    assert _safe_report_logo_src("https://cdn.example/logo.png?size=1&theme=light") == (
        "https://cdn.example/logo.png?size=1&amp;theme=light"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("logo_url", "javascript:alert(1)"),
        ("logo_url", "https://127.0.0.1/logo.png"),
        ("logo_url", "https://service.internal/logo.png"),
        ("brand_color", "#fff; background:url(javascript:alert(1))"),
    ],
)
def test_client_portal_rejects_unsafe_branding(field, value):
    from backend.fastapi.app.routers.client_portal import ClientCreateRequest

    with pytest.raises(ValueError):
        ClientCreateRequest(name="Client", **{field: value})


def test_defectdojo_private_destination_is_rejected_before_transport(monkeypatch):
    from backend.fastapi.app.domains.identity.secure_egress import UnsafeOutboundURL
    from backend.fastapi.app.routers import pentest_sync

    monkeypatch.setattr(
        pentest_sync,
        "outbound_request",
        lambda *a, **k: pytest.fail("private DefectDojo target reached transport"),
    )
    with pytest.raises(UnsafeOutboundURL):
        pentest_sync._dojo_request("POST", "https://127.0.0.1/api/v2/findings/", "sensitive-token")


@pytest.mark.parametrize(
    "url",
    [
        "http://dojo.example.com",
        "https://user:password@dojo.example.com",
        "https://dojo.example.com/?api_key=secret",
        "https://127.0.0.1",
        "https://[::1]",
    ],
)
def test_defectdojo_config_rejects_insecure_or_private_url(url):
    from backend.fastapi.app.routers.pentest_sync import _normalize_dojo_url

    with pytest.raises(ValueError):
        _normalize_dojo_url(url)


def test_defectdojo_config_normalizes_public_https_url():
    from backend.fastapi.app.routers.pentest_sync import _normalize_dojo_url

    assert _normalize_dojo_url(" https://dojo.example.com/ ") == "https://dojo.example.com"


def test_auto_link_private_cms_destination_is_rejected_before_transport(monkeypatch):
    import asyncio

    from backend.fastapi.app.modules import auto_link_agent

    agent = auto_link_agent.AutoLinkAgent.__new__(auto_link_agent.AutoLinkAgent)
    agent.cms_api_url = "https://127.0.0.1"
    agent.cms_api_key = "tenant-api-secret"
    monkeypatch.setattr(
        auto_link_agent,
        "outbound_async_request",
        lambda *a, **k: pytest.fail("private CMS target reached transport"),
    )
    decision = auto_link_agent.AgentDecision(
        link={"from_url": "https://site.example/a", "to_url": "https://site.example/b", "anchor_text": "link"},
        approved=True,
    )

    result = asyncio.run(agent._execute_link("run-test", decision))
    assert result["status"] == "error"
    assert result["error"] == "UnsafeOutboundURL"
    assert "127.0.0.1" not in result["error"]


def test_replicate_poll_rejects_untrusted_origin_before_sending_token(monkeypatch):
    from types import SimpleNamespace

    from backend.fastapi.app.services import ai_providers

    monkeypatch.setattr(
        ai_providers,
        "resolve_outbound_target",
        lambda url: SimpleNamespace(url=url, host="attacker.example", port=443),
    )
    monkeypatch.setattr(
        ai_providers,
        "outbound_request",
        lambda *a, **k: pytest.fail("Replicate token sent to untrusted origin"),
    )

    assert (
        ai_providers._poll_replicate_prediction(
            {"Authorization": "Token secret"}, "https://attacker.example/predictions/1"
        )
        is None
    )


def test_replicate_output_download_rejects_private_address():
    from backend.fastapi.app.services.ai_providers import _download_replicate_video

    assert _download_replicate_video("https://169.254.169.254/latest/meta-data/") is None


def test_live_editor_site_key_rejects_script_breakout():
    from fastapi import HTTPException

    from backend.fastapi.app.routers.live_editor import _validate_site_key

    assert _validate_site_key("site_key-123") == "site_key-123"
    with pytest.raises(HTTPException) as caught:
        _validate_site_key("');alert(document.domain);//")
    assert caught.value.status_code == 422


def test_chatbot_embed_escapes_tenant_attribute():
    from backend.fastapi.app.routers.chatbot import _build_chatbot_embed_snippet

    snippet = _build_chatbot_embed_snippet(12, 'tenant" onload="alert(1)')
    assert 'onload="alert' not in snippet
    assert "&quot;" in snippet


@pytest.mark.parametrize("provider", ["facebook", "google_analytics"])
def test_workforce_does_not_forward_provider_token_to_custom_action_url(provider):
    import asyncio

    from backend.fastapi.app.domains.automation.workforce.services.mission_execution import (
        _dispatch_provider_action,
    )

    ok, result = asyncio.run(
        _dispatch_provider_action(
            provider=provider,
            token="provider-access-token",
            mission={"id": "mission-1", "role": "analyst", "objective": "test"},
            generated_artifact="private mission output",
            connection={"metadata": {"action_url": "https://attacker.example/collect"}},
        )
    )
    assert not ok
    assert result["error"] in {
        "custom-action-endpoints-not-supported",
        "analytics-provider-does-not-support-actions",
    }
    assert "attacker.example" not in str(result)


def test_workforce_ai_generation_is_strict_in_production(monkeypatch):
    import asyncio

    from backend.fastapi.app.domains.automation.workforce.services import mission_execution

    class UnavailableClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            raise RuntimeError("https://gateway.example/path?api_key=do-not-leak")

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("WORKFORCE_STRICT_AI_EXECUTION", "false")
    monkeypatch.setenv("FASTAPI_URL", "https://api.example")
    monkeypatch.setenv("WORKFORCE_AI_GATEWAY_URL", "https://api.example/ai/gateway/generate")
    monkeypatch.setattr(mission_execution.httpx, "AsyncClient", lambda **_kwargs: UnavailableClient())

    ok, result = asyncio.run(
        mission_execution._generate_mission_artifact("org-1", {"title": "Test", "objective": "Test"})
    )
    assert not ok
    assert result["error"] == "ai-gateway-unreachable"
    assert result["detail"] == "RuntimeError"
    assert "api_key" not in str(result)
    assert "rules_fallback" not in str(result)


def test_workforce_ai_gateway_error_body_is_not_returned(monkeypatch):
    import asyncio

    from backend.fastapi.app.domains.automation.workforce.services import mission_execution

    class ErrorResponse:
        status_code = 503
        text = "secret internal endpoint details"

    class FailedClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return ErrorResponse()

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("FASTAPI_URL", "https://api.example")
    monkeypatch.setenv("WORKFORCE_AI_GATEWAY_URL", "https://api.example/ai/gateway/generate")
    monkeypatch.setattr(mission_execution.httpx, "AsyncClient", lambda **_kwargs: FailedClient())

    ok, result = asyncio.run(
        mission_execution._generate_mission_artifact("org-1", {"title": "Test", "objective": "Test"})
    )
    assert not ok
    assert result == {"error": "ai-gateway-failed", "status_code": 503}
    assert "secret internal endpoint details" not in str(result)


def test_workforce_production_gateway_requires_allowlisted_https_origin(monkeypatch):
    from backend.fastapi.app.domains.automation.workforce.services.mission_execution import _ai_gateway_url

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("FASTAPI_URL", "https://api.example")
    monkeypatch.setenv("WORKFORCE_AI_GATEWAY_URL", "https://attacker.example/generate")
    monkeypatch.delenv("WORKFORCE_AI_GATEWAY_ALLOWED_HOSTS", raising=False)
    with pytest.raises(RuntimeError, match="origin is not allowed"):
        _ai_gateway_url()

    monkeypatch.setenv("WORKFORCE_AI_GATEWAY_URL", "http://api.example/generate")
    with pytest.raises(RuntimeError, match="origin is not allowed"):
        _ai_gateway_url()

    monkeypatch.setenv("WORKFORCE_AI_GATEWAY_URL", "https://ai.internal/generate")
    monkeypatch.setenv("WORKFORCE_AI_GATEWAY_ALLOWED_HOSTS", "ai.internal")
    assert _ai_gateway_url() == "https://ai.internal/generate"


def test_workforce_production_gateway_requires_configuration(monkeypatch):
    from backend.fastapi.app.domains.automation.workforce.services.mission_execution import _ai_gateway_url

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("FASTAPI_URL", raising=False)
    monkeypatch.delenv("NEXT_PUBLIC_FASTAPI_URL", raising=False)
    monkeypatch.delenv("WORKFORCE_AI_GATEWAY_URL", raising=False)
    with pytest.raises(RuntimeError, match="not configured"):
        _ai_gateway_url()
