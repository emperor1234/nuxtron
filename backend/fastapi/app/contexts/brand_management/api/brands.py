"""Brand, guideline, contributor, and analytics HTTP endpoints."""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any, NamedTuple

from fastapi import APIRouter, Depends, HTTPException, Query

from ....deps import AuthContext, require_auth
from ..public import BrandStatus
from ..service import BrandManagementService

logger = logging.getLogger(__name__)

MEMORY_STORE_UNAVAILABLE = (
    "Brand Hub persistence is not configured for production. Configure a durable backend before enabling brand management."
)
BRAND_NOT_FOUND = "Brand not found"


class BrandRouteEndpoints(NamedTuple):
    """Endpoint references exported by the legacy compatibility shim."""

    create_brand: Any
    list_brands: Any
    get_brand: Any
    update_brand: Any
    update_guidelines: Any
    add_contributor: Any
    get_brand_analytics: Any


def ensure_brand_store_writable() -> None:
    """Retain the historical fail-closed production mutation policy."""
    if os.getenv("ENVIRONMENT", "development").strip().lower() == "production":
        raise HTTPException(status_code=503, detail=MEMORY_STORE_UNAVAILABLE)


def register_brand_routes(
    router: APIRouter,
    service: BrandManagementService,
) -> BrandRouteEndpoints:
    """Attach the seven non-asset routes to the context router."""

    @router.post("")
    async def create_brand(
        name: str,
        auth: Annotated[AuthContext, Depends(require_auth)],
        description: str | None = None,
        website: str | None = None,
    ) -> dict:
        """Create new brand."""
        try:
            ensure_brand_store_writable()
            if not name or len(name.strip()) == 0:
                raise HTTPException(status_code=400, detail="name is required")
            brand = service.create_brand(
                tenant_id=auth.tenant_id,
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
            status_filter = None
            if status:
                try:
                    status_filter = BrandStatus(status)
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
            brands = service.list_brands(auth.tenant_id, status_filter)
            return {
                "brands": [
                    {
                        "id": brand.id,
                        "name": brand.name,
                        "description": brand.description,
                        "status": brand.status.value,
                        "assets_count": len(brand.assets),
                        "team_size": len(brand.owners) + len(brand.contributors),
                        "created_at": brand.created_at.isoformat(),
                    }
                    for brand in brands
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
            brand = service.get_brand(auth.tenant_id, brand_id)
            if not brand:
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
            ensure_brand_store_writable()
            updated = service.update_brand(auth.tenant_id, brand_id, updates)
            if not updated:
                raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)
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
            ensure_brand_store_writable()
            updated = service.update_guidelines(auth.tenant_id, brand_id, guidelines)
            if not updated:
                raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)
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

    @router.post("/{brand_id}/contributors/{user_id}")
    async def add_contributor(
        brand_id: str,
        user_id: str,
        auth: Annotated[AuthContext, Depends(require_auth)],
    ) -> dict:
        """Add contributor to brand."""
        try:
            ensure_brand_store_writable()
            updated = service.add_contributor(auth.tenant_id, brand_id, user_id)
            if not updated:
                raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)
            return {"status": "added", "brand_id": brand_id, "contributor": user_id}
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
            analytics = service.get_brand_analytics(auth.tenant_id, brand_id)
            if analytics is None:
                raise HTTPException(status_code=404, detail=BRAND_NOT_FOUND)
            return analytics
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Failed to get analytics.")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return BrandRouteEndpoints(
        create_brand,
        list_brands,
        get_brand,
        update_brand,
        update_guidelines,
        add_contributor,
        get_brand_analytics,
    )
