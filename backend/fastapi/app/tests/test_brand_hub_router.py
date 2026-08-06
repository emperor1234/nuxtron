"""Tests for Brand Hub router hardening."""

import os

import pytest
from backend.fastapi.app.routers import brand_hub as brand_hub_router
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("ALLOW_HEADER_API_KEYS", "true")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "brand-hub-test-tenant"}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
    monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
    monkeypatch.setenv("ENVIRONMENT", "development")
    brand_hub_router.brand_hub_manager.brands.clear()

    app = FastAPI()
    app.include_router(brand_hub_router.router)
    return TestClient(app, raise_server_exceptions=False)


class TestBrandHubRouterDevelopmentMode:
    def test_create_brand_requires_auth_in_development(self, client: TestClient) -> None:
        response = client.post("/api/v1/brands", params={"name": "Acme"})
        assert response.status_code == 401

    def test_create_brand_accepts_valid_auth_in_development(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/brands",
            headers=H,
            params={"name": "Acme", "description": "Brand"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Acme"
        assert "id" in body

    def test_list_brands_accepts_valid_auth_in_development(self, client: TestClient) -> None:
        create = client.post("/api/v1/brands", headers=H, params={"name": "Acme"})
        assert create.status_code == 200

        response = client.get("/api/v1/brands", headers=H)
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1


class TestBrandHubRouterProductionMode:
    def test_create_brand_fails_closed_in_production_without_durable_store(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
        monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
        monkeypatch.setenv("ENVIRONMENT", "production")
        brand_hub_router.brand_hub_manager.brands.clear()

        app = FastAPI()
        app.include_router(brand_hub_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post("/api/v1/brands", headers=H, params={"name": "Blocked"})
        assert response.status_code == 503
        assert response.json()["detail"] == brand_hub_router.MEMORY_STORE_UNAVAILABLE

    def test_create_brand_still_requires_auth_in_production(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
        monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
        monkeypatch.setenv("ENVIRONMENT", "production")

        app = FastAPI()
        app.include_router(brand_hub_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.post("/api/v1/brands", params={"name": "Blocked"})
        assert response.status_code == 401

    def test_list_brands_read_succeeds_in_production_with_auth(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
        monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
        monkeypatch.setenv("ENVIRONMENT", "production")
        brand_hub_router.brand_hub_manager.brands.clear()
        brand_hub_router.brand_hub_manager.create_brand(
            tenant_id=H["X-Tenant-Id"],
            name="Acme",
            owner_id="owner",
        )

        app = FastAPI()
        app.include_router(brand_hub_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.get("/api/v1/brands", headers=H)
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_update_brand_fails_closed_in_production_without_durable_store(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
        monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
        monkeypatch.setenv("ENVIRONMENT", "production")
        brand_hub_router.brand_hub_manager.brands.clear()
        brand = brand_hub_router.brand_hub_manager.create_brand(
            tenant_id=H["X-Tenant-Id"],
            name="Acme",
            owner_id="owner",
        )

        app = FastAPI()
        app.include_router(brand_hub_router.router)
        client = TestClient(app, raise_server_exceptions=False)

        response = client.patch(
            f"/api/v1/brands/{brand.id}",
            headers=H,
            json={"description": "updated"},
        )
        assert response.status_code == 503
        assert response.json()["detail"] == brand_hub_router.MEMORY_STORE_UNAVAILABLE
