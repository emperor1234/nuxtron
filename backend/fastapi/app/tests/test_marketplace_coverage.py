"""Marketplace compatibility paths must not serve or store sample business data."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

pytestmark = pytest.mark.no_legacy


def _headers(tenant: str | None = None) -> dict[str, str]:
    return {
        "X-API-Key": "test-api-key",
        "X-Tenant-Id": tenant or f"marketplace-unavailable-{uuid.uuid4().hex[:10]}",
    }


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_marketplace_routes_fail_closed_without_store_or_audit_mutation(client: TestClient) -> None:
    from backend.fastapi.app import memory_stores

    catalogue_before = list(memory_stores.marketplace_catalogue)
    installs_before = list(memory_stores.marketplace_installs)
    audit_before = list(memory_stores.audit_log)
    headers = _headers()
    calls = [
        (client.get, "/marketplace/plugins", {}),
        (client.get, "/marketplace/themes", {}),
        (client.post, "/marketplace/install", {"json": {"item_id": "plugin-001"}}),
        (
            client.post,
            "/marketplace/publish",
            {
                "json": {
                    "type": "plugin",
                    "name": "A reviewed extension",
                    "description": "This valid payload is supplied only to verify the unavailable contract.",
                    "category": "automation",
                    "version": "1.0.0",
                    "price": 0.0,
                }
            },
        ),
    ]

    for request, path, options in calls:
        response = request(path, headers=headers, **options)
        assert response.status_code == 501, f"{path} returned {response.status_code}"
        assert response.json()["detail"]["code"] == "NOT_IMPLEMENTED"
        assert "Cache-Control" in response.headers

    assert memory_stores.marketplace_catalogue == catalogue_before
    assert memory_stores.marketplace_installs == installs_before
    assert memory_stores.audit_log == audit_before


def test_marketplace_routes_still_require_authentication(client: TestClient) -> None:
    assert client.get("/marketplace/plugins").status_code in {401, 403}
    assert client.post("/marketplace/install", json={"item_id": "plugin-001"}).status_code in {401, 403}
