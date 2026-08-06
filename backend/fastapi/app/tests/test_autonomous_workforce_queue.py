from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_autonomous_workforce_queue.db")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "autonomous-workforce-queue-test"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("WORKFORCE_USE_CELERY", "true")

    from backend.fastapi.app import memory_stores
    from backend.fastapi.app.main import app
    from backend.fastapi.app.tasks import workforce_tasks

    queued: list[dict[str, Any]] = []

    def _fake_enqueue(
        tenant_id: str,
        mission_id: str,
        mission: dict[str, Any],
        provider_connections: list[dict[str, Any]],
    ) -> str:
        queued.append(
            {
                "tenant_id": tenant_id,
                "mission_id": mission_id,
                "mission": mission,
                "provider_connections": provider_connections,
            }
        )
        return f"task-{len(queued)}"

    monkeypatch.setattr(workforce_tasks, "enqueue_execute_mission", _fake_enqueue)

    for store in (
        memory_stores.autonomous_workforce_profiles,
        memory_stores.autonomous_workforce_integrations,
        memory_stores.autonomous_workforce_missions,
        memory_stores.autonomous_workforce_feed,
        memory_stores.autonomous_workforce_schedules,
        memory_stores.autonomous_workforce_knowledge,
        memory_stores.autonomous_workforce_outcomes,
    ):
        store.clear()

    test_client = TestClient(app, raise_server_exceptions=False)
    test_client.app.state._queued_workforce_calls = queued  # type: ignore[attr-defined]
    return test_client


def test_approval_path_queues_mission_when_celery_enabled(client: TestClient) -> None:
    created = client.post(
        "/autonomous-workforce/missions",
        headers=H,
        json={
            "title": "Queue approved mission",
            "description": "Approval should enqueue the mission.",
            "role": "social_media",
            "objective": "Publish queued content",
            "requires_approval": True,
            "providers": [],
            "input_context": {},
        },
    )
    assert created.status_code == 201
    mission_id = str(created.json()["mission"]["id"])

    approved = client.post(
        f"/autonomous-workforce/missions/{mission_id}/approve",
        headers=H,
        json={"note": "queue it"},
    )
    assert approved.status_code == 200
    body = approved.json()
    assert body["outcome"]["status"] == "queued"
    assert str(body["outcome"]["queued_task_id"]).startswith("task-")


def test_runner_tick_queues_due_schedule_when_celery_enabled(client: TestClient) -> None:
    from backend.fastapi.app import memory_stores

    created = client.post(
        "/autonomous-workforce/schedules",
        headers=H,
        json={
            "role": "growth_metrics",
            "title": "Queued scheduled mission",
            "objective": "Run from queue",
            "frequency_minutes": 5,
            "providers": [],
            "enabled": True,
        },
    )
    assert created.status_code == 201

    memory_stores.autonomous_workforce_schedules[-1]["next_run_at"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()

    tick = client.post("/autonomous-workforce/runner/tick", headers=H)
    assert tick.status_code == 200
    body = tick.json()
    assert body["executed"] == 0
    assert body["queued"] == 1
    assert len(body["mission_ids"]) == 1
    assert len(body["task_ids"]) == 1


def test_webhook_auto_execution_queues_when_celery_enabled(client: TestClient) -> None:
    response = client.post(
        "/autonomous-workforce/webhook/trigger",
        headers=H,
        json={
            "role": "social_media",
            "trigger_source": "zapier",
            "objective": "Queue from webhook",
            "providers": [],
            "event_data": {"kind": "test"},
            "requires_approval": False,
        },
    )
    assert response.status_code == 202
    body = response.json()
    assert body["executed"] is False
    assert body["queued"] is True
    assert str(body["task_id"]).startswith("task-")