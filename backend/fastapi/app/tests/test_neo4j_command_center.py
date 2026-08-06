from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def _headers(tenant_id: str) -> dict[str, str]:
    return {
        "X-Tenant-Id": tenant_id,
        "X-API-Key": os.environ.get("FASTAPI_API_KEY", "test-api-key"),
    }


class _FakeRecord(dict[str, Any]):
    pass


class _FakeResult(list[_FakeRecord]):
    def single(self) -> _FakeRecord | None:
        return self[0] if self else None


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run(self, query: str, params: dict[str, Any] | None = None) -> _FakeResult:
        payload = params or {}
        self.calls.append((query, payload))

        if "RETURN 1 AS ok" in query:
            return _FakeResult([_FakeRecord({"ok": 1, "now": "2026-05-22T00:00:00Z"})])
        if "RETURN root, nbr" in query:
            return _FakeResult([
                _FakeRecord({"root": {"node_id": "acct-1"}, "nbr": {"node_id": "txn-1"}, "hops": 1})
            ])
        if "RETURN n LIMIT" in query:
            return _FakeResult([_FakeRecord({"n": {"node_id": "acct-1", "tenant_id": payload.get("tenant_id")}})])
        if "RETURN" in query:
            return _FakeResult([_FakeRecord({"ok": True, "tenant": payload.get("tenant_id")})])
        return _FakeResult([])

    def close(self) -> None:
        return None


@pytest.fixture
def patch_neo4j_session(monkeypatch: pytest.MonkeyPatch) -> _FakeSession:
    from backend.fastapi.app.routers import neo4j_graph_intelligence as neo_router

    fake_session = _FakeSession()

    @contextmanager
    def _fake_driver_session() -> Iterator[_FakeSession]:
        yield fake_session

    monkeypatch.setattr(neo_router, "_driver_session", _fake_driver_session)
    return fake_session


def test_neo4j_end_to_end_command_center(client: TestClient, patch_neo4j_session: _FakeSession) -> None:
    tenant_id = "tenant-neo4j-e2e"

    caps = client.get("/search-everywhere/neo4j/capabilities", headers=_headers(tenant_id))
    assert caps.status_code == 200, caps.text
    assert caps.json()["status"] == "ok"
    assert any(item["capability"] == "Cypher query execution" for item in caps.json()["capabilities"])

    vendors = client.get("/search-everywhere/neo4j/vendors", headers=_headers(tenant_id))
    assert vendors.status_code == 200, vendors.text
    assert any(v["name"] == "Neo4j" for v in vendors.json()["vendors"])

    gate = client.get("/search-everywhere/neo4j/production-gate", headers=_headers(tenant_id))
    assert gate.status_code == 200, gate.text
    assert "checks" in gate.json()["gate"]

    probe = client.get("/search-everywhere/neo4j/health/probe", headers=_headers(tenant_id))
    assert probe.status_code == 200, probe.text
    assert probe.json()["probe"]["ok"] is True

    upsert = client.post(
        "/search-everywhere/neo4j/knowledge-graph/upsert",
        headers=_headers(tenant_id),
        json={
            "nodes": [
                {"node_id": "acct-1", "labels": ["Account"], "properties": {"name": "Acme"}},
                {"node_id": "txn-1", "labels": ["Transaction"], "properties": {"amount": 100}},
            ],
            "relationships": [
                {"source_id": "acct-1", "target_id": "txn-1", "rel_type": "HAS_TRANSACTION", "properties": {"risk": "medium"}}
            ],
        },
    )
    assert upsert.status_code == 200, upsert.text
    assert upsert.json()["nodes_upserted"] == 2

    search = client.post(
        "/search-everywhere/neo4j/knowledge-graph/search",
        headers=_headers(tenant_id),
        json={"label": "Account", "key": "node_id", "value": "acct-1", "limit": 10},
    )
    assert search.status_code == 200, search.text
    assert search.json()["count"] >= 1

    context = client.post(
        "/search-everywhere/neo4j/graphrag/context",
        headers=_headers(tenant_id),
        json={"entity_node_id": "acct-1", "max_hops": 2, "max_neighbors": 10},
    )
    assert context.status_code == 200, context.text
    assert context.json()["count"] >= 1

    query = client.post(
        "/search-everywhere/neo4j/cypher/query",
        headers=_headers(tenant_id),
        json={"query": "RETURN $tenant_id AS tenant", "params": {}, "mode": "read", "allow_write": False},
    )
    assert query.status_code == 200, query.text
    assert query.json()["row_count"] >= 1

    chart = client.get("/search-everywhere/neo4j/completion-chart", headers=_headers(tenant_id))
    assert chart.status_code == 200, chart.text
    assert chart.json()["summary"]["implemented"].endswith("/7")

    assert len(patch_neo4j_session.calls) >= 5
