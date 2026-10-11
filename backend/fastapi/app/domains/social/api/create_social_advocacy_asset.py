"""Social HTTP adapters: create social advocacy asset."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import AdvocacyAssetCreateRequest
from ..constants import AuthDep
from ..operations.bulk_social_inbox_action import operation_create_social_advocacy_asset
from ..operations.bulk_social_inbox_action import operation_publish_social_advocacy_asset
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.post("/social/advocacy/assets")
    def create_social_advocacy_asset(payload: AdvocacyAssetCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_social_advocacy_asset(st, router, payload, auth)

    @router.post(
        "/social/advocacy/assets/{asset_id}/publish", responses={404: {"description": "Advocacy asset not found"}}
    )
    def publish_social_advocacy_asset(asset_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_publish_social_advocacy_asset(st, router, asset_id, auth)
