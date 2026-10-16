"""The legacy influencer discovery router has no data provider, so it refuses every request."""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "influencer-provider-required"}


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/influencer/profile/1001", None),
        ("POST", "/influencer/fraud-check", {"influencer_id": 1001}),
    ],
)
def test_influencer_discovery_is_not_available_without_a_provider(
    client: TestClient, method: str, path: str, body: dict | None
) -> None:
    response = client.request(method, path, headers=H, json=body)
    assert response.status_code == 501
    assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"
