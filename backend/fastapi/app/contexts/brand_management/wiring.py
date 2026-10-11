"""Compose brand-management service, adapter, and HTTP routes."""

from __future__ import annotations

from fastapi import APIRouter

from .api import (
    MEMORY_STORE_UNAVAILABLE,
    ensure_brand_store_writable,
    register_asset_routes,
    register_brand_routes,
)
from .memory_repository import LegacyBrandHubManager, brand_repository
from .service import BrandManagementService

brand_service = BrandManagementService(brand_repository)
brand_hub_manager = LegacyBrandHubManager(brand_service, brand_repository)


def _build_router() -> tuple[APIRouter, tuple[object, ...]]:
    context_router = APIRouter(prefix="/api/v1/brands", tags=["Brand Hub"])
    brand_endpoints = register_brand_routes(context_router, brand_service)
    asset_endpoints = register_asset_routes(context_router, brand_service)
    return context_router, (*brand_endpoints, *asset_endpoints)


def create_brand_management_router() -> APIRouter:
    """Create a router for isolated tests without changing process ownership."""
    context_router, _ = _build_router()
    return context_router


router, _endpoint_exports = _build_router()
(
    create_brand,
    list_brands,
    get_brand,
    update_brand,
    update_guidelines,
    add_contributor,
    get_brand_analytics,
    add_asset,
    list_assets,
    remove_asset,
) = _endpoint_exports

# Historical private names remain importable while callers migrate.
_ensure_brand_hub_store_writable = ensure_brand_store_writable


def _is_production() -> bool:
    """Compatibility helper retained for imports from the old router."""
    import os

    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"


__all__ = [
    "MEMORY_STORE_UNAVAILABLE",
    "_ensure_brand_hub_store_writable",
    "_is_production",
    "add_asset",
    "add_contributor",
    "brand_hub_manager",
    "brand_repository",
    "brand_service",
    "create_brand",
    "create_brand_management_router",
    "get_brand",
    "get_brand_analytics",
    "list_assets",
    "list_brands",
    "remove_asset",
    "router",
    "update_brand",
    "update_guidelines",
]
