"""Compatibility contracts for the retired, non-durable customer marketplace."""

from collections.abc import Callable
from typing import Annotated, Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

MARKETPLACE_UNAVAILABLE_DETAIL = {
    "code": "NOT_IMPLEMENTED",
    "message": "Marketplace listings, installation, and publishing are unavailable until a durable, tenant-scoped catalogue is implemented.",
}
MARKETPLACE_UNAVAILABLE_RESPONSE = {
    501: {
        "description": "Marketplace catalogue and installation are not implemented.",
        "content": {"application/json": {"example": {"detail": MARKETPLACE_UNAVAILABLE_DETAIL}}},
    }
}


class MarketplaceInstallRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=80)


class MarketplacePublishRequest(BaseModel):
    type: str = Field(pattern=r"^(plugin|theme)$")
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=10, max_length=2000)
    category: str = Field(min_length=1, max_length=80)
    version: str = Field(default="1.0.0", max_length=20)
    price: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default="USD", max_length=8)


def _raise_marketplace_unavailable() -> NoReturn:
    raise HTTPException(
        status_code=501,
        detail=MARKETPLACE_UNAVAILABLE_DETAIL,
        headers={"Cache-Control": "no-store"},
    )


def create_marketplace_router(
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    marketplace_catalogue_memory: list[dict[str, Any]],
    marketplace_installs_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> APIRouter:
    """Keep legacy paths authenticated while preventing fake data or side effects."""
    # Retain the factory contract for router-registration compatibility. These
    # stores/rate limits are intentionally not touched by unavailable handlers.
    _ = (enforce_rate_limit, marketplace_catalogue_memory, marketplace_installs_memory, audit_log_memory)
    router = APIRouter()

    @router.get(
        "/marketplace/plugins",
        status_code=501,
        response_model=None,
        responses=MARKETPLACE_UNAVAILABLE_RESPONSE,
    )
    def list_plugins(auth: AuthDep) -> NoReturn:  # pyright: ignore[reportUnusedFunction]
        _ = auth
        _raise_marketplace_unavailable()

    @router.get(
        "/marketplace/themes",
        status_code=501,
        response_model=None,
        responses=MARKETPLACE_UNAVAILABLE_RESPONSE,
    )
    def list_themes(auth: AuthDep) -> NoReturn:  # pyright: ignore[reportUnusedFunction]
        _ = auth
        _raise_marketplace_unavailable()

    @router.post(
        "/marketplace/install",
        status_code=501,
        response_model=None,
        responses=MARKETPLACE_UNAVAILABLE_RESPONSE,
    )
    def install_item(payload: MarketplaceInstallRequest, auth: AuthDep) -> NoReturn:  # pyright: ignore[reportUnusedFunction]
        _ = (payload, auth)
        _raise_marketplace_unavailable()

    @router.post(
        "/marketplace/publish",
        status_code=501,
        response_model=None,
        responses=MARKETPLACE_UNAVAILABLE_RESPONSE,
    )
    def publish_item(payload: MarketplacePublishRequest, auth: AuthDep) -> NoReturn:  # pyright: ignore[reportUnusedFunction]
        _ = (payload, auth)
        _raise_marketplace_unavailable()

    return router
