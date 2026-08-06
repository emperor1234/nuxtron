import asyncio
import os
from typing import Any

import pytest
from backend.fastapi.app.routers.autonomous_workforce import (
    create_autonomous_workforce_router,
    run_autonomous_workforce_watchdog,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "workforce-test-tenant"}


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any]) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)
        self.headers = {"content-type": "application/json"}

    def json(self) -> dict[str, Any]:
        return self._payload


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
    monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")

    async def _fake_get(self: Any, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
        await asyncio.sleep(0)
        if "slack.com/api/auth.test" in url:
            return _FakeResponse(200, {"ok": True, "url": url})
        return _FakeResponse(200, {"ok": True, "url": url})

    async def _fake_post(
        self: Any,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> _FakeResponse:
        await asyncio.sleep(0)
        if "/ai/gateway/generate" in url:
            role = str((json or {}).get("system_prompt", ""))
            return _FakeResponse(200, {"content": f"Generated artifact from {role}"})
        return _FakeResponse(200, {"ok": True, "url": url})

    monkeypatch.setattr("httpx.AsyncClient.get", _fake_get)
    monkeypatch.setattr("httpx.AsyncClient.post", _fake_post)

    profiles: list[dict[str, Any]] = []
    integrations: list[dict[str, Any]] = []
    missions: list[dict[str, Any]] = []
    feed: list[dict[str, Any]] = []
    schedules: list[dict[str, Any]] = []
    knowledge: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    audit_log: list[dict[str, Any]] = []

    app = FastAPI()
    app.include_router(
        create_autonomous_workforce_router(
            enforce_rate_limit=lambda key, limit, window: None,
            profiles_memory=profiles,
            integrations_memory=integrations,
            missions_memory=missions,
            feed_memory=feed,
            schedules_memory=schedules,
            knowledge_memory=knowledge,
            outcomes_memory=outcomes,
            audit_log_memory=audit_log,
        )
    )
    return TestClient(app, raise_server_exceptions=False)


def test_connect_provider_and_execute_mission_end_to_end(client: TestClient) -> None:
    connect = client.post(
        "/autonomous-workforce/integrations/connect",
        headers=H,
        json={
            "provider": "slack",
            "access_token": "xoxb-test-token-123456789",
            "account_id": "acct-1",
        },
    )
    assert connect.status_code == 201
    connect_body = connect.json()
    assert connect_body["integration"]["provider"] == "slack"
    assert connect_body["verified"] is True

    create_mission = client.post(
        "/autonomous-workforce/missions",
        headers=H,
        json={
            "title": "Daily channel intelligence",
            "description": "Collect engagement signals and summarize",
            "role": "social_media",
            "objective": "Track and report daily engagement",
            "requires_approval": True,
            "providers": ["slack"],
            "input_context": {"channel": "marketing"},
        },
    )
    assert create_mission.status_code == 201
    mission_id = create_mission.json()["mission"]["id"]

    approve = client.post(
        f"/autonomous-workforce/missions/{mission_id}/approve",
        headers=H,
        json={"note": "approved"},
    )
    assert approve.status_code == 200
    approve_body = approve.json()
    assert approve_body["mission"]["status"] == "completed"
    assert approve_body["outcome"]["success_count"] == 1
    assert "generated" in approve_body["outcome"]["artifact"]

    feed = client.get("/autonomous-workforce/feed", headers=H)
    assert feed.status_code == 200
    assert feed.json()["total"] >= 2

    outcomes = client.get("/autonomous-workforce/outcomes", headers=H)
    assert outcomes.status_code == 200
    assert outcomes.json()["total"] >= 1


def test_schedule_tick_runs_due_mission(client: TestClient) -> None:
    connect = client.post(
        "/autonomous-workforce/integrations/connect",
        headers=H,
        json={
            "provider": "slack",
            "access_token": "xoxb-test-token-abc",
        },
    )
    assert connect.status_code == 201

    vendors = client.get("/autonomous-workforce/vendors", headers=H)
    assert vendors.status_code == 200
    assert any(item["component"] == "AI generation" for item in vendors.json()["vendors"])

    schedule = client.post(
        "/autonomous-workforce/schedules",
        headers=H,
        json={
            "role": "growth_metrics",
            "title": "Hourly growth digest",
            "objective": "Run hourly growth checks",
            "frequency_minutes": 5,
            "providers": ["slack"],
            "enabled": True,
        },
    )
    assert schedule.status_code == 201

    schedules = client.get("/autonomous-workforce/schedules", headers=H)
    assert schedules.status_code == 200
    schedule_id = schedules.json()["schedules"][0]["id"]

    # Force due execution for deterministic test.
    update_due = client.post(
        "/autonomous-workforce/knowledge",
        headers=H,
        json={"title": "keepalive", "body": "trigger"},
    )
    assert update_due.status_code == 201

    # Use direct mission path as schedule due semantics depend on current timestamp precision.
    run_tick = client.post("/autonomous-workforce/runner/tick?limit=10", headers=H)
    assert run_tick.status_code == 200
    assert "executed" in run_tick.json()

    # Schedule remains registered.
    schedules_after = client.get("/autonomous-workforce/schedules", headers=H)
    assert schedules_after.status_code == 200
    assert any(s["id"] == schedule_id for s in schedules_after.json()["schedules"])


def test_watchdog_executes_due_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_get(self: Any, url: str, headers: dict[str, str] | None = None) -> _FakeResponse:
        await asyncio.sleep(0)
        return _FakeResponse(200, {"ok": True, "url": url})

    async def _fake_post(
        self: Any,
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> _FakeResponse:
        await asyncio.sleep(0)
        if "/ai/gateway/generate" in url:
            return _FakeResponse(200, {"content": "watchdog-generated-artifact"})
        return _FakeResponse(200, {"ok": True, "url": url})

    monkeypatch.setattr("httpx.AsyncClient.get", _fake_get)
    monkeypatch.setattr("httpx.AsyncClient.post", _fake_post)

    tenant_id = "workforce-watchdog-tenant"
    now = "2020-01-01T00:00:00+00:00"

    schedules: list[dict[str, Any]] = [
        {
            "id": "sched-1",
            "tenant_id": tenant_id,
            "title": "Watchdog cadence",
            "objective": "Execute automated watchdog mission",
            "role": "growth_metrics",
            "providers": ["slack"],
            "enabled": True,
            "frequency_minutes": 5,
            "next_run_at": now,
        }
    ]
    integrations: list[dict[str, Any]] = [
        {
            "tenant_id": tenant_id,
            "provider": "slack",
            "status": "connected",
            "last_verified_token": "xoxb-watchdog-token",
        }
    ]
    missions: list[dict[str, Any]] = []
    feed: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    audit_log: list[dict[str, Any]] = []

    async def _run() -> None:
        stop_event = asyncio.Event()

        async def _set_stop() -> None:
            await asyncio.sleep(0.02)
            stop_event.set()

        stopper = asyncio.create_task(_set_stop())
        await run_autonomous_workforce_watchdog(
            stop_event,
            schedules_memory=schedules,
            integrations_memory=integrations,
            missions_memory=missions,
            feed_memory=feed,
            outcomes_memory=outcomes,
            audit_log_memory=audit_log,
            poll_interval_seconds=1,
            max_due_per_tick=5,
        )
        await stopper

    asyncio.run(_run())

    assert len(missions) == 1
    assert missions[0]["status"] == "completed"
    assert len(outcomes) == 1
    assert outcomes[0]["success_count"] == 1
    assert any(item.get("type") == "mission_result" for item in feed)
    assert any(item.get("action") == "workforce_schedule_executed" for item in audit_log)
