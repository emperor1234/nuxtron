"""Social HTTP adapters: get brand profile."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import BrandProfileRequest
from ....domains.social.schemas import BrandWebsiteFetchRequest
from ....domains.social.schemas import UgcTemplateProfileRequest
from ..constants import AuthDep
from ..operations.get_brand_profile import operation_avatar_catalog
from ..operations.get_brand_profile import operation_fetch_brand_profile_from_website
from ..operations.get_brand_profile import operation_get_brand_profile
from ..operations.get_brand_profile import operation_update_brand_profile
from ..operations.get_brand_profile import operation_update_ugc_template_profile
from ..operations.get_brand_profile import operation_voiceover_catalog
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/brand-profile")
    def get_brand_profile(auth: AuthDep) -> dict[str, Any]:
        return operation_get_brand_profile(st, router, auth)

    @router.get("/social/avatar/catalog")
    def avatar_catalog(auth: AuthDep) -> dict[str, Any]:
        return operation_avatar_catalog(st, router, auth)

    @router.get("/social/voiceover/catalog")
    def voiceover_catalog(auth: AuthDep) -> dict[str, Any]:
        return operation_voiceover_catalog(st, router, auth)

    @router.put("/social/brand-profile")
    def update_brand_profile(payload: BrandProfileRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_update_brand_profile(st, router, payload, auth)

    @router.put("/social/brand-profile/ugc-template")
    def update_ugc_template_profile(payload: UgcTemplateProfileRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_update_ugc_template_profile(st, router, payload, auth)

    @router.post("/social/brand-profile/fetch-from-website", responses={422: {"description": "Invalid website URL"}})
    def fetch_brand_profile_from_website(payload: BrandWebsiteFetchRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_fetch_brand_profile_from_website(st, router, payload, auth)
