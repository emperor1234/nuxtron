"""Backlink Intelligence used to generate links and prospects from a random seed; it is now refused."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "backlink-provider-required"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/backlink-intel/overview", None),
        ("GET", "/backlink-intel/backlinks", None),
        ("GET", "/backlink-intel/prospects", None),
        ("GET", "/backlink-intel/analytics", None),
        ("POST", "/backlink-intel/audit", {"domain": "example.com"}),
        ("POST", "/backlink-intel/prospects", {"domain": "example.com"}),
        ("POST", "/backlink-intel/disavow", {"domains": ["example.com"]}),
    ],
)
def test_backlink_routes_are_not_available_without_a_provider(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    response = client.request(method, path, headers=H, json=body)
    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"


@pytest.mark.parametrize("path", ["/domain-overview/summary?domain=example.com", "/market-explorer/overview", "/pla-research/overview?keyword=shoes"])
def test_other_estimate_generators_are_refused(client: TestClient, path: str) -> None:
    assert client.get(path, headers=H).status_code == 501
