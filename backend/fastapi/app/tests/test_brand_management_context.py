"""Contract and isolation tests for the brand-management context pilot."""

from __future__ import annotations

import threading
from typing import Any

import pytest
from backend.fastapi.app.tests.contracts.route_manifest import build_app_route_manifest
from fastapi import FastAPI
from fastapi.testclient import TestClient

AUTH_A = {"X-API-Key": "test-api-key", "X-Tenant-Id": "brand-tenant-a"}
AUTH_B = {"X-API-Key": "test-api-key", "X-Tenant-Id": "brand-tenant-b"}
BRAND_PATH_PREFIX = "/api/v1/brands"


def _isolated_service() -> Any:
    from backend.fastapi.app.contexts.brand_management.memory_repository import (
        MemoryBrandRepository,
    )
    from backend.fastapi.app.contexts.brand_management.service import (
        BrandManagementService,
    )

    return BrandManagementService(MemoryBrandRepository({}, threading.RLock()))


@pytest.mark.no_legacy
class TestBrandManagementService:
    def test_crud_operations_are_tenant_scoped(self) -> None:
        service = _isolated_service()
        brand = service.create_brand("tenant-a", "Acme", owner_id="owner")

        assert service.get_brand("tenant-a", brand.id) is brand
        assert service.get_brand("tenant-b", brand.id) is None
        assert service.list_brands("tenant-b") == []
        assert service.update_brand("tenant-b", brand.id, {"name": "Stolen"}) is None
        assert service.remove_asset("tenant-b", brand.id, "asset-id") is None
        assert service.get_brand("tenant-a", brand.id).name == "Acme"

    def test_brand_invariants_are_explicit(self) -> None:
        service = _isolated_service()

        with pytest.raises(ValueError, match="tenant_id is required"):
            service.create_brand("", "Acme")
        with pytest.raises(ValueError, match="name is required"):
            service.create_brand("tenant-a", "   ")


@pytest.mark.no_legacy
def test_repository_uses_canonical_store_and_shared_lock() -> None:
    from backend.fastapi.app import memory_stores
    from backend.fastapi.app.contexts.brand_management.memory_repository import (
        brand_repository,
    )

    assert brand_repository.store is memory_stores.brand_hub_brands
    assert brand_repository._lock is memory_stores.brand_hub_brands_lock


@pytest.fixture
def context_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from backend.fastapi.app.contexts.brand_management.wiring import (
        brand_repository,
        create_brand_management_router,
    )

    monkeypatch.setenv("ALLOW_HEADER_API_KEYS", "true")
    monkeypatch.setenv("FASTAPI_API_KEY", "test-api-key")
    monkeypatch.setenv("ENVIRONMENT", "development")
    brand_repository.clear_for_tests()
    application = FastAPI()
    application.include_router(create_brand_management_router())
    return TestClient(application, raise_server_exceptions=False)


def test_http_contract_and_runtime_json_are_preserved(context_client: TestClient) -> None:
    created = context_client.post(
        BRAND_PATH_PREFIX,
        headers=AUTH_A,
        params={"name": "Acme", "description": "Brand", "website": "https://acme.test"},
    )
    assert created.status_code == 200
    brand = created.json()
    assert set(brand) == {"id", "name", "description", "website", "status", "created_at"}
    assert brand["name"] == "Acme"
    assert brand["status"] == "active"

    listed = context_client.get(BRAND_PATH_PREFIX, headers=AUTH_A)
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    details = context_client.get(f"{BRAND_PATH_PREFIX}/{brand['id']}", headers=AUTH_A)
    assert details.status_code == 200
    assert details.json()["id"] == brand["id"]


@pytest.mark.parametrize("method", ["get", "patch", "put", "post", "delete"])
def test_cross_tenant_id_probing_never_leaks(
    context_client: TestClient,
    method: str,
) -> None:
    brand_id = context_client.post(
        BRAND_PATH_PREFIX,
        headers=AUTH_A,
        params={"name": "Private"},
    ).json()["id"]
    requests = {
        "get": lambda: context_client.get(f"{BRAND_PATH_PREFIX}/{brand_id}", headers=AUTH_B),
        "patch": lambda: context_client.patch(
            f"{BRAND_PATH_PREFIX}/{brand_id}", headers=AUTH_B, json={"name": "Stolen"}
        ),
        "put": lambda: context_client.put(
            f"{BRAND_PATH_PREFIX}/{brand_id}/guidelines",
            headers=AUTH_B,
            json={"tone": "hostile"},
        ),
        "post": lambda: context_client.post(
            f"{BRAND_PATH_PREFIX}/{brand_id}/contributors/intruder",
            headers=AUTH_B,
        ),
        "delete": lambda: context_client.delete(
            f"{BRAND_PATH_PREFIX}/{brand_id}/assets/unknown",
            headers=AUTH_B,
        ),
    }

    response = requests[method]()
    assert response.status_code == 404
    assert response.json() == {"detail": "Brand not found"}


def test_router_compatibility_shim_reexports_context_surface() -> None:
    from backend.fastapi.app.contexts.brand_management import wiring
    from backend.fastapi.app.routers import brand_hub

    assert brand_hub.router is wiring.router
    assert brand_hub.brand_hub_manager is wiring.brand_hub_manager
    assert brand_hub.create_brand is wiring.create_brand
    assert brand_hub.MEMORY_STORE_UNAVAILABLE == wiring.MEMORY_STORE_UNAVAILABLE


def test_brand_route_manifest_matches_checked_in_contract() -> None:
    import json

    from backend.fastapi.app.bootstrap.application import create_app
    from backend.fastapi.app.tests.test_route_contract import BASELINE_PATH

    actual = [
        record
        for record in build_app_route_manifest(create_app())["routes"]
        if record["path"].startswith(BRAND_PATH_PREFIX)
    ]
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    expected = [
        record
        for record in baseline["routes"]
        if record["path"].startswith(BRAND_PATH_PREFIX)
    ]

    assert actual == expected
