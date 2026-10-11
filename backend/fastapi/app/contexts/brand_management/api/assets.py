"""Tenant-scoped brand asset HTTP endpoints."""

from __future__ import annotations

import logging
from typing import Annotated, Any, NamedTuple

from fastapi import APIRouter, Depends, HTTPException

from ....deps import AuthContext, require_auth
from ..public import BrandAsset
from ..service import BrandManagementService
from .brands import BRAND_NOT_FOUND, ensure_brand_store_writable

logger = logging.getLogger(__name__)


class AssetRouteEndpoints(NamedTuple):
    """Endpoint references exported by the legacy compatibility shim."""

    add_asset: Any
    list_assets: Any
    remove_asset: Any


def register_asset_routes(
    router: APIRouter,
    service: BrandManagementService,
) -> AssetRouteEndpoints:
    """Attach the three asset routes to the context router."""

    @router.post("/{brand_id}/assets")
    async def add_asset(
        brand_id: str,
        name: str,
        asset_type: str,
        url: str,
        auth: Annotated[AuthContext, Depends(require_auth)],
        category: str = "general",
        tags: list[str] | None = None,
    ) -> dict:
        """Add asset to brand library."""
        try:
            ensure_brand_store_writable()
            asset = BrandAsset(
                name=name,
                asset_type=asset_type,
                url=url,
                category=category,
                tags=tags or [],
                rights_holder="unknown",
                usage_rights="internal",
            )
            added = service.add_asset(auth.tenant_id, brand_id, asset)
            if added is None:
                raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)
            return {
                "asset_id": asset.id,
                "name": asset.name,
                "type": asset.asset_type,
                "created_at": asset.uploaded_at.isoformat(),
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Failed to add asset.")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/{brand_id}/assets")
    async def list_assets(
        brand_id: str,
        auth: Annotated[AuthContext, Depends(require_auth)],
        asset_type: str | None = None,
        category: str | None = None,
    ) -> dict:
        """List brand assets."""
        try:
            assets = service.list_assets(auth.tenant_id, brand_id, asset_type, category)
            if assets is None:
                raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)
            return {
                "assets": [
                    {
                        "id": asset.id,
                        "name": asset.name,
                        "type": asset.asset_type,
                        "category": asset.category,
                        "usage_count": asset.usage_count,
                        "last_used": asset.last_used_at.isoformat() if asset.last_used_at else None,
                    }
                    for asset in assets
                ],
                "count": len(assets),
            }
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Failed to list assets.")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.delete("/{brand_id}/assets/{asset_id}")
    async def remove_asset(
        brand_id: str,
        asset_id: str,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> dict:
        """Remove asset from brand library."""
        try:
            ensure_brand_store_writable()
            updated = service.remove_asset(auth.tenant_id, brand_id, asset_id)
            if updated is None:
                raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)
            return {"status": "removed", "asset_id": asset_id}
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Failed to remove asset.")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AssetRouteEndpoints(add_asset, list_assets, remove_asset)
