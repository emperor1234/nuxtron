"""Brand Hub API routes."""

import logging
import os
from typing import Annotated, Any

from ..brand_hub.core import BrandAsset, BrandStatus, brand_hub_manager
from ..deps import AuthContext, require_auth
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix="/api/v1/brands", tags=["Brand Hub"])
logger = logging.getLogger(__name__)

MEMORY_STORE_UNAVAILABLE = (
    "Brand Hub persistence is not configured for production. Configure a durable backend before enabling brand management."
)
BRAND_NOT_FOUND = "Brand not found"


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"


def _ensure_brand_hub_store_writable() -> None:
    if _is_production():
        raise HTTPException(status_code=503, detail=MEMORY_STORE_UNAVAILABLE)


@router.post("")
async def create_brand(
    name: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
    description: str | None = None,
    website: str | None = None,
) -> dict:
    """Create new brand."""
    try:
        _ensure_brand_hub_store_writable()
        tenant_id = auth.tenant_id

        if not name or len(name.strip()) == 0:
            raise HTTPException(status_code=400, detail="name is required")

        brand = brand_hub_manager.create_brand(
            tenant_id=tenant_id,
            name=name,
            description=description or "",
            website=website,
            owner_id="current_user",
        )

        return {
            "id": brand.id,
            "name": brand.name,
            "description": brand.description,
            "website": brand.website,
            "status": brand.status.value,
            "created_at": brand.created_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create brand.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("")
async def list_brands(
    auth: Annotated[AuthContext, Depends(require_auth)],
    status: Annotated[str | None, Query()] = None,
) -> dict:
    """List all brands."""
    try:
        tenant_id = auth.tenant_id
        status_filter = None
        if status:
            try:
                status_filter = BrandStatus(status)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        brands = brand_hub_manager.list_brands(tenant_id, status_filter)

        return {
            "brands": [
                {
                    "id": b.id,
                    "name": b.name,
                    "description": b.description,
                    "status": b.status.value,
                    "assets_count": len(b.assets),
                    "team_size": len(b.owners) + len(b.contributors),
                    "created_at": b.created_at.isoformat(),
                }
                for b in brands
            ],
            "count": len(brands),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list brands.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{brand_id}")
async def get_brand(
    brand_id: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Get brand details."""
    try:
        tenant_id = auth.tenant_id
        brand = brand_hub_manager.get_brand(brand_id)

        if not brand or brand.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)

        return {
            "id": brand.id,
            "name": brand.name,
            "description": brand.description,
            "website": brand.website,
            "status": brand.status.value,
            "guidelines": {
                "primary_color": brand.guidelines.primary_color,
                "secondary_color": brand.guidelines.secondary_color,
                "tone": brand.guidelines.tone,
                "required_keywords": brand.guidelines.required_keywords,
                "restricted_keywords": brand.guidelines.restricted_keywords,
                "version": brand.guidelines.version,
            },
            "assets_count": len(brand.assets),
            "team": {
                "owners": brand.owners,
                "contributors": brand.contributors,
            },
            "created_at": brand.created_at.isoformat(),
            "updated_at": brand.updated_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get brand.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.patch("/{brand_id}")
async def update_brand(
    brand_id: str,
    updates: dict[str, Any],
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Update brand."""
    try:
        _ensure_brand_hub_store_writable()
        tenant_id = auth.tenant_id
        brand = brand_hub_manager.get_brand(brand_id)

        if not brand or brand.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)

        updated = brand_hub_manager.update_brand(brand_id, **updates)

        return {
            "id": updated.id,
            "name": updated.name,
            "updated_at": updated.updated_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update brand.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/{brand_id}/guidelines")
async def update_guidelines(
    brand_id: str,
    guidelines: dict[str, Any],
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Update brand guidelines."""
    try:
        _ensure_brand_hub_store_writable()
        tenant_id = auth.tenant_id
        brand = brand_hub_manager.get_brand(brand_id)

        if not brand or brand.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)

        updated = brand_hub_manager.update_guidelines(brand_id, **guidelines)

        return {
            "brand_id": brand_id,
            "guidelines": {
                "version": updated.guidelines.version,
                "updated_at": updated.guidelines.updated_at.isoformat(),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update guidelines.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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
        _ensure_brand_hub_store_writable()
        tenant_id = auth.tenant_id
        brand = brand_hub_manager.get_brand(brand_id)

        if not brand or brand.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)

        asset = BrandAsset(
            name=name,
            asset_type=asset_type,
            url=url,
            category=category,
            tags=tags or [],
            rights_holder="unknown",
            usage_rights="internal",
        )

        brand_hub_manager.add_asset(brand_id, asset)

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
        tenant_id = auth.tenant_id
        brand = brand_hub_manager.get_brand(brand_id)

        if not brand or brand.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)

        assets = brand_hub_manager.get_assets(brand_id, asset_type, category)

        return {
            "assets": [
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.asset_type,
                    "category": a.category,
                    "usage_count": a.usage_count,
                    "last_used": a.last_used_at.isoformat() if a.last_used_at else None,
                }
                for a in assets
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
        _ensure_brand_hub_store_writable()
        tenant_id = auth.tenant_id
        brand = brand_hub_manager.get_brand(brand_id)

        if not brand or brand.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)

        brand_hub_manager.remove_asset(brand_id, asset_id)

        return {"status": "removed", "asset_id": asset_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to remove asset.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{brand_id}/contributors/{user_id}")
async def add_contributor(
    brand_id: str,
    user_id: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Add contributor to brand."""
    try:
        _ensure_brand_hub_store_writable()
        tenant_id = auth.tenant_id
        brand = brand_hub_manager.get_brand(brand_id)

        if not brand or brand.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)

        brand_hub_manager.add_contributor(brand_id, user_id)

        return {
            "status": "added",
            "brand_id": brand_id,
            "contributor": user_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to add contributor.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{brand_id}/analytics")
async def get_brand_analytics(
    brand_id: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
) -> dict:
    """Get brand analytics."""
    try:
        tenant_id = auth.tenant_id
        brand = brand_hub_manager.get_brand(brand_id)

        if not brand or brand.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)

        analytics = brand_hub_manager.get_brand_analytics(brand_id)
        return analytics
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get analytics.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


