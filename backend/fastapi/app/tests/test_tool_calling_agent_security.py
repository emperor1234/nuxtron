from __future__ import annotations

import asyncio

from backend.fastapi.app.tool_calling_agent import ToolCallingAgent, ToolRegistry, create_tool_registry_for_mission


def test_mission_registry_contains_only_explicit_adapters():
    async def real_tool(value: str) -> dict[str, str]:
        return {"value": value}

    registry = create_tool_registry_for_mission({"real_tool": real_tool})
    assert list(registry.tools) == ["real_tool"]
    assert create_tool_registry_for_mission().tools == {}


def test_tool_agent_does_not_call_gateway_without_configured_key(monkeypatch):
    from backend.fastapi.app import tool_calling_agent

    def unexpected_client(**_kwargs):
        raise AssertionError("gateway must not be called without credentials")

    monkeypatch.delenv("FASTAPI_API_KEY", raising=False)
    monkeypatch.setattr(tool_calling_agent.httpx, "AsyncClient", unexpected_client)
    agent = ToolCallingAgent("agent", "analyst", ToolRegistry(), "https://gateway.example", tenant_id="org-1")

    result = asyncio.run(agent._call_ai_for_next_step("goal", {}))
    assert result == {"error": "AI gateway credentials are not configured"}


def test_tool_agent_sends_configured_key_and_tenant(monkeypatch):
    from backend.fastapi.app import tool_calling_agent

    observed: dict[str, object] = {}

    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"content": '{"final_answer":"done"}'}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, json, headers):
            observed.update(url=url, headers=headers)
            return Response()

    monkeypatch.setattr(tool_calling_agent.httpx, "AsyncClient", lambda **_kwargs: Client())
    agent = ToolCallingAgent(
        "agent",
        "analyst",
        ToolRegistry(),
        "https://gateway.example/generate",
        tenant_id="org-1",
        api_key="service-secret",
    )

    result = asyncio.run(agent._call_ai_for_next_step("goal", {}))
    assert result == {"final_answer": "done"}
    assert observed["url"] == "https://gateway.example/generate"
    assert observed["headers"] == {
        "Content-Type": "application/json",
        "X-API-Key": "service-secret",
        "X-Tenant-Id": "org-1",
    }


def test_tool_agent_redacts_gateway_exception(monkeypatch):
    from backend.fastapi.app import tool_calling_agent

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            raise RuntimeError("secret query token must not be returned")

    monkeypatch.setattr(tool_calling_agent.httpx, "AsyncClient", lambda **_kwargs: Client())
    agent = ToolCallingAgent(
        "agent",
        "analyst",
        ToolRegistry(),
        "https://gateway.example/generate",
        tenant_id="org-1",
        api_key="service-secret",
    )

    result = asyncio.run(agent._call_ai_for_next_step("goal", {}))
    assert result == {"error": "RuntimeError"}


def test_workforce_tool_calling_is_unavailable_without_real_adapters():
    import asyncio
    import threading
    from types import SimpleNamespace

    import pytest
    from fastapi import HTTPException

    from backend.fastapi.app.deps import AuthContext
    from backend.fastapi.app.domains.automation.workforce.operations.retry_action import (
        execute_enable_tool_calling_for_mission,
    )

    runtime = SimpleNamespace(
        enforce_rate_limit=lambda *_args: None,
        _lock=threading.Lock(),
        missions_memory=[{"id": "mission-1", "tenant_id": "org-1", "status": "approved"}],
        tool_adapters={},
    )
    with pytest.raises(HTTPException) as caught:
        asyncio.run(execute_enable_tool_calling_for_mission(runtime, "mission-1", AuthContext(tenant_id="org-1")))
    assert caught.value.status_code == 503
    assert "no executable tool adapters" in caught.value.detail
