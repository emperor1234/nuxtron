from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> Iterator[TestClient]:
    from backend.fastapi.app.bootstrap.application import app
    from backend.fastapi.app.deps import AuthContext, require_auth

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[require_auth] = lambda: AuthContext(
        tenant_id="production-media-test",
        auth_mode="oidc",
        subject="production-media-test-user",
        roles=["tenant_admin"],
    )
    test_client = TestClient(app, raise_server_exceptions=False)
    try:
        yield test_client
    finally:
        test_client.close()
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("POST", "/media/jobs", {"storage_key": "raw-input/production-media-test/image.jpg", "media_type": "image"}),
        ("GET", "/media/jobs", None),
        ("GET", "/media/jobs/42", None),
        ("DELETE", "/media/jobs/42", None),
        ("POST", "/media/jobs/42/retry", None),
        ("POST", "/media/jobs/42/output-url", {"expires_seconds": 300}),
        ("GET", "/media/jobs/dlq", None),
        ("GET", "/media/jobs/stats", None),
        ("GET", "/media/jobs/42/audit", None),
        (
            "POST",
            "/media/sandbox/dispatch",
            {
                "storage_key": "raw-input/production-media-test/image.jpg",
                "media_type": "image",
                "provider": "cloudinary",
                "operation": "auto",
            },
        ),
    ],
)
def test_memory_backed_media_operations_are_not_available_in_production(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    from backend.fastapi.app import memory_stores

    monkeypatch.setenv("ENVIRONMENT", "production")
    existing_job_ids = tuple(job.get("id") for job in memory_stores.media_jobs)
    response = client.request(method, path, json=payload)

    assert response.status_code == 501, response.text
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"
    assert "durable" in response.json()["detail"]["message"].lower()
    assert tuple(job.get("id") for job in memory_stores.media_jobs) == existing_job_ids


def test_media_progress_stream_is_not_available_in_production(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app.deps import AuthContext
    from backend.fastapi.app.domains.content.media.operations import job_progress_stream

    async def authenticated_context(**_: Any) -> AuthContext:
        return AuthContext(tenant_id="production-media-test", auth_mode="oidc", subject="media-test-user")

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(job_progress_stream, "require_auth", authenticated_context)
    response = client.get("/media/jobs/42/stream")

    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"


def test_sandbox_configuration_does_not_claim_production_execution(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    response = client.get("/media/sandbox/config")

    assert response.status_code == 200
    sandbox = response.json()["sandbox"]
    assert sandbox["execution_mode"] == "unavailable"
    assert sandbox["available_executors"]["memory_fallback"] is False
    assert sandbox["available_executors"]["aws_lambda"] is False
    assert sandbox["available_executors"]["google_cloud_run"] is False
    assert sandbox["available_executors"]["kubernetes"] is False
    assert sandbox["job_processing"]["available"] is False
    assert sandbox["security_rules"]["rule_5_row_level_security"]["enforced"] is False
    assert sandbox["security_rules"]["rule_6_signed_urls"]["enforced"] is False


def test_production_api_replicas_do_not_start_process_local_watchdogs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app.bootstrap import lifespan

    class ForbiddenWorkerStarts:
        def __getattr__(self, name: str) -> Any:
            raise AssertionError(f"Production API attempted to access in-process worker method: {name}")

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("AUTONOMOUS_WORKFORCE_WATCHDOG_ENABLED", raising=False)
    assert lifespan.autonomous_workforce_watchdog_enabled() is False

    monkeypatch.setenv("AUTONOMOUS_WORKFORCE_WATCHDOG_ENABLED", "1")
    workers = lifespan._start_background_workers(ForbiddenWorkerStarts())  # type: ignore[arg-type]
    assert workers.security_alerts == (None, None)
    assert workers.ira_watchdog == (None, None)
    assert workers.autonomous_workforce_watchdog == (None, None)


def test_production_raw_delete_requires_durable_audit_before_storage(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app.domains.content.media.operations import purge_raw_input
    from backend.fastapi.app.domains.identity import security_audit

    storage_calls: list[tuple[str, str]] = []
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(security_audit, "durable_audit_enabled", lambda: False)
    monkeypatch.setattr(
        purge_raw_input,
        "delete_minio_object",
        lambda bucket, key: storage_calls.append((bucket, key)),
    )

    response = client.delete(
        "/media/raw-input",
        params={"storage_key": "raw-input/production-media-test/file.jpg"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Durable security audit is unavailable."
    assert storage_calls == []


def test_production_raw_delete_records_redacted_audit_before_storage(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.fastapi.app.domains.content.media.operations import purge_raw_input
    from backend.fastapi.app.domains.identity import security_audit

    calls: list[object] = []
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(security_audit, "durable_audit_enabled", lambda: True)
    monkeypatch.setattr(security_audit, "record_security_event", lambda **event: calls.append(event))
    monkeypatch.setattr(
        purge_raw_input,
        "delete_minio_object",
        lambda bucket, key: calls.append((bucket, key)),
    )

    storage_key = "raw-input/production-media-test/file.jpg"
    response = client.delete("/media/raw-input", params={"storage_key": storage_key})

    assert response.status_code == 200
    assert response.json()["deleted_from_storage"] is True
    assert len(calls) == 2
    assert isinstance(calls[0], dict)
    assert calls[0]["event_type"] == "media_raw_input_delete_requested"
    assert "storage_key_sha256" in calls[0]["metadata"]
    assert storage_key not in repr(calls[0]["metadata"])
    assert calls[1] == ("raw-input", storage_key)


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/autonomous-workforce/capabilities", None),
        ("GET", "/autonomous-workforce/missions", None),
        ("POST", "/autonomous-workforce/missions/mission-not-found/approve", {"note": "approve"}),
        ("POST", "/autonomous-workforce/runner/tick", None),
        (
            "POST",
            "/autonomous-workforce/webhook/trigger",
            {
                "role": "social_media",
                "trigger_source": "production-gate-test",
                "objective": "Do not enqueue in production",
                "providers": ["slack"],
                "event_data": {"test": True},
                "requires_approval": False,
            },
        ),
    ],
)
def test_production_workforce_execution_is_unavailable_before_state_changes(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
) -> None:
    from backend.fastapi.app import memory_stores

    monkeypatch.setenv("ENVIRONMENT", "production")
    tenant_id = "production-media-test"
    before = {
        name: tuple(item.get("id") for item in getattr(memory_stores, name) if item.get("tenant_id") == tenant_id)
        for name in (
            "autonomous_workforce_missions",
            "autonomous_workforce_outcomes",
            "autonomous_workforce_feed",
            "autonomous_workforce_schedules",
        )
    }

    response = client.request(method, path, json=payload)

    assert response.status_code == 501, response.text
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"
    assert "tenant-isolated" in response.json()["detail"]["message"]
    after = {
        name: tuple(item.get("id") for item in getattr(memory_stores, name) if item.get("tenant_id") == tenant_id)
        for name in before
    }
    assert after == before


def test_production_workforce_enqueue_does_not_send_credentials_to_broker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastapi import HTTPException

    from backend.fastapi.app.tasks import workforce_tasks

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setattr(
        workforce_tasks.execute_workforce_mission_task,
        "apply_async",
        lambda **_: pytest.fail("production attempted to serialize provider credentials to Celery"),
    )

    with pytest.raises(HTTPException) as exc_info:
        workforce_tasks.enqueue_execute_mission(
            "org-acme",
            "mission-1",
            {"id": "mission-1", "providers": ["slack"]},
            [{"provider": "slack", "last_verified_token": "must-not-enter-broker"}],
        )

    assert exc_info.value.status_code == 501
