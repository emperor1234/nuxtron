"""Coverage tests for marketplace.py — plugins, themes, install, publish."""
from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)



def _headers(tenant: str | None = None) -> dict[str, str]:
    return {
        "X-API-Key": "test-api-key",
        "X-Tenant-Id": tenant or f"marketplace-coverage-{uuid.uuid4().hex[:10]}",
    }


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def ensure_marketplace_seed() -> None:
    from backend.fastapi.app import memory_stores
    from backend.fastapi.app.routers.marketplace import _SEED_PLUGINS, _SEED_THEMES

    if not memory_stores.marketplace_catalogue:
        memory_stores.marketplace_catalogue.extend(item.copy() for item in (_SEED_PLUGINS + _SEED_THEMES))


class TestMarketplaceCoverage:
    def test_list_plugins(self, client: TestClient) -> None:
        r = client.get("/marketplace/plugins", headers=_headers())
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert isinstance(data["plugins"], list)
        assert data["count"] >= 3  # seeded with 3 plugins

    def test_list_themes(self, client: TestClient) -> None:
        r = client.get("/marketplace/themes", headers=_headers())
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert isinstance(data["themes"], list)
        assert data["count"] >= 2  # seeded with 2 themes

    def test_install_plugin_success(self, client: TestClient) -> None:
        headers = _headers()
        r = client.post(
            "/marketplace/install",
            headers=headers,
            json={"item_id": "plugin-001"},
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["status"] == "ok"
        assert data["install"]["item_id"] == "plugin-001"
        assert data.get("already_installed") is not True

    def test_install_same_plugin_is_idempotent(self, client: TestClient) -> None:
        headers = _headers()
        first = client.post(
            "/marketplace/install",
            headers=headers,
            json={"item_id": "plugin-001"},
        )
        assert first.status_code in (200, 201)

        # Install plugin-001 again in the same tenant scope — should be idempotent
        r = client.post(
            "/marketplace/install",
            headers=headers,
            json={"item_id": "plugin-001"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data.get("already_installed") is True

    def test_install_theme_success(self, client: TestClient) -> None:
        headers = _headers()
        r = client.post(
            "/marketplace/install",
            headers=headers,
            json={"item_id": "theme-001"},
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["install"]["item_type"] == "theme"

    def test_install_unknown_item_returns_404(self, client: TestClient) -> None:
        r = client.post(
            "/marketplace/install",
            headers=_headers(),
            json={"item_id": "plugin-does-not-exist"},
        )
        assert r.status_code == 404

    def test_publish_plugin(self, client: TestClient) -> None:
        r = client.post(
            "/marketplace/publish",
            headers=_headers(),
            json={
                "type": "plugin",
                "name": "My Custom Plugin",
                "description": "A plugin that does something useful for marketing.",
                "category": "automation",
                "version": "1.0.0",
                "price": 0.0,
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["status"] == "ok"
        assert data["item"]["type"] == "plugin"
        assert data["item"]["status"] == "pending_review"

    def test_publish_theme(self, client: TestClient) -> None:
        r = client.post(
            "/marketplace/publish",
            headers=_headers(),
            json={
                "type": "theme",
                "name": "My Custom Theme",
                "description": "A beautiful theme with custom colors for the dashboard.",
                "category": "dashboard",
                "version": "2.0.0",
                "price": 19.99,
                "currency": "USD",
            },
        )
        assert r.status_code in (200, 201)
        data = r.json()
        assert data["item"]["type"] == "theme"
        assert data["item"]["price"] == 19.99
