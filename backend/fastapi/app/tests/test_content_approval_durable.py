"""Durable, role-checked content approvals (routers/content_approval.py)."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.fastapi.app.deps import AuthContext, require_auth
from backend.fastapi.app.models import ContentApprovalRequest
from backend.fastapi.app.routers.content_approval import count_approval_requests, create_content_approval_router

TENANT = "tenant-approvals"
OTHER_TENANT = "tenant-other"


@pytest.fixture()
def engine() -> Iterator[Engine]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    yield engine
    engine.dispose()


def _session_scope(engine: Engine) -> Callable[[str], Any]:
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def scope(_tenant_id: str) -> Iterator[Session]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return scope


class Caller:
    """Mutable identity the app's require_auth override returns."""

    def __init__(self) -> None:
        self.context = AuthContext(tenant_id=TENANT, auth_mode="bearer_jwt", subject="creator", roles=["user"])

    def act_as(self, *, roles: list[str], tenant_id: str = TENANT, auth_mode: str = "bearer_jwt") -> None:
        self.context = AuthContext(tenant_id=tenant_id, auth_mode=auth_mode, subject="-".join(roles) or "key", roles=roles)


def _build_client(engine: Engine, caller: Caller) -> TestClient:
    app = FastAPI()
    app.dependency_overrides[require_auth] = lambda: caller.context
    app.include_router(
        create_content_approval_router(
            enforce_rate_limit=lambda *_args: None,
            audit_log_memory=[],
            session_scope=_session_scope(engine),
        )
    )
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def caller() -> Caller:
    return Caller()


@pytest.fixture()
def client(engine: Engine, caller: Caller) -> TestClient:
    return _build_client(engine, caller)


def _configure(client: TestClient, caller: Caller, levels: list[str], require_all: bool = True) -> None:
    caller.act_as(roles=["admin"])
    r = client.put(
        "/content/approval/config",
        json={"levels": levels, "require_all_levels": require_all, "expiry_hours": 24},
    )
    assert r.status_code == 200, r.text


def _submit(client: TestClient, caller: Caller, post_id: int, platform: str = "linkedin") -> int:
    caller.act_as(roles=["user"])
    r = client.post(
        "/content/approval/requests",
        json={
            "scheduled_post_id": post_id,
            "platform": platform,
            "content_preview": f"Post {post_id}",
            "requested_by": "Ada",
        },
    )
    assert r.status_code == 200, r.text
    return int(r.json()["request"]["id"])


def _decide(client: TestClient, request_id: int, role: str, decision: str = "approved", comment: str | None = None):
    body: dict[str, Any] = {"decision": decision, "reviewer_role": role}
    if comment is not None:
        body["comment"] = comment
    return client.post(f"/content/approval/requests/{request_id}/decision", json=body)


def test_config_is_empty_until_configured(client: TestClient) -> None:
    r = client.get("/content/approval/config")
    assert r.status_code == 200
    assert r.json()["config"] is None


def test_only_admins_can_change_the_chain(client: TestClient, caller: Caller) -> None:
    caller.act_as(roles=["editor"])
    r = client.put("/content/approval/config", json={"levels": ["editor"]})
    assert r.status_code == 403
    assert client.get("/content/approval/config").json()["config"] is None

    _configure(client, caller, [" Editor ", "legal", "editor"])
    assert client.get("/content/approval/config").json()["config"]["levels"] == ["editor", "legal"]


def test_requests_survive_a_router_restart(engine: Engine, caller: Caller, client: TestClient) -> None:
    request_id = _submit(client, caller, 11, platform="x")

    restarted = _build_client(engine, caller)
    listed = restarted.get("/content/approval/requests").json()
    assert [item["id"] for item in listed["requests"]] == [request_id]
    assert listed["requests"][0]["platform"] == "x"
    assert listed["requests"][0]["approval_levels"] == ["manager"]
    assert count_approval_requests(TENANT, session_scope=_session_scope(engine)) == 1


def test_duplicate_pending_request_is_rejected(client: TestClient, caller: Caller) -> None:
    _submit(client, caller, 12)
    r = client.post(
        "/content/approval/requests",
        json={"scheduled_post_id": 12, "platform": "linkedin", "content_preview": "again", "requested_by": "Ada"},
    )
    assert r.status_code == 400


def test_reviewer_must_hold_the_role_they_sign_for(client: TestClient, caller: Caller) -> None:
    _configure(client, caller, ["editor", "legal"])
    request_id = _submit(client, caller, 13)

    caller.act_as(roles=["editor"])
    denied = _decide(client, request_id, "legal")
    assert denied.status_code == 403

    caller.act_as(roles=[], auth_mode="api_key")
    assert _decide(client, request_id, "editor").status_code == 403

    caller.act_as(roles=["editor"])
    first = _decide(client, request_id, "editor")
    assert first.status_code == 200
    assert first.json()["request"]["status"] == "pending"
    assert first.json()["request"]["approvals_received"] == ["editor"]

    caller.act_as(roles=["legal"])
    second = _decide(client, request_id, "legal")
    assert second.json()["request"]["status"] == "approved"

    assert _decide(client, request_id, "legal").status_code == 400


def test_admin_can_sign_any_level_and_any_level_suffices_when_configured(
    client: TestClient, caller: Caller
) -> None:
    _configure(client, caller, ["editor", "legal"], require_all=False)
    request_id = _submit(client, caller, 14)
    caller.act_as(roles=["admin"])
    r = _decide(client, request_id, "legal")
    assert r.status_code == 200
    assert r.json()["request"]["status"] == "approved"


def test_unknown_level_and_missing_request(client: TestClient, caller: Caller) -> None:
    request_id = _submit(client, caller, 15)
    caller.act_as(roles=["admin"])
    assert _decide(client, request_id, "cfo").status_code == 422
    assert _decide(client, 9999, "manager").status_code == 404
    assert client.get("/content/approval/requests/9999/comments").status_code == 404


def test_rejection_records_reason_and_comment(client: TestClient, caller: Caller) -> None:
    request_id = _submit(client, caller, 16)
    caller.act_as(roles=["manager"])
    r = _decide(client, request_id, "manager", decision="rejected", comment="Off-brand imagery")
    assert r.status_code == 200
    body = r.json()["request"]
    assert body["status"] == "rejected"
    assert body["rejection_reason"] == "Off-brand imagery"

    comments = client.get(f"/content/approval/requests/{request_id}/comments").json()
    assert comments["count"] == 1
    assert comments["comments"][0]["reviewer_role"] == "manager"
    assert client.get("/content/approval/requests?approval_status=rejected").json()["count"] == 1


def test_requests_are_isolated_per_tenant(client: TestClient, caller: Caller) -> None:
    request_id = _submit(client, caller, 17)
    caller.act_as(roles=["admin"], tenant_id=OTHER_TENANT)
    assert client.get("/content/approval/requests").json()["requests"] == []
    assert _decide(client, request_id, "manager").status_code == 404
    assert client.get(f"/content/approval/requests/{request_id}/comments").status_code == 404


def test_expired_requests_cannot_be_signed(engine: Engine, client: TestClient, caller: Caller) -> None:
    request_id = _submit(client, caller, 18)
    with _session_scope(engine)(TENANT) as session:
        session.execute(
            update(ContentApprovalRequest)
            .where(ContentApprovalRequest.id == request_id)
            .values(expires_at=datetime.now(UTC) - timedelta(minutes=1))
        )

    caller.act_as(roles=["manager"])
    assert _decide(client, request_id, "manager").status_code == 400
    listed = client.get("/content/approval/requests").json()["requests"]
    assert listed[0]["status"] == "expired"

    # An expired request no longer blocks resubmitting the same post.
    _submit(client, caller, 18)
