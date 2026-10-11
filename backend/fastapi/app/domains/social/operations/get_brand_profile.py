"""Social use cases: get brand profile."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import BrandProfileRequest
from ....domains.social.schemas import BrandWebsiteFetchRequest
from ....domains.social.schemas import UgcTemplateProfileRequest
from ..constants import AuthDep
from ..services.brand import _sw_avatar_catalog
from ..services.brand import _sw_profile_defaults
from ..services.brand import _sw_update_brand_profile
from ..services.brand import _sw_update_ugc_template
from ..services.brand import _sw_voiceover_catalog
from ..services.website import _sw_fetch_brand_from_website
from fastapi import APIRouter
from typing import Any


def operation_get_brand_profile(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:brand:get", 240, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "brand_profile": _sw_profile_defaults(st, auth.tenant_id).copy(),
    }


def operation_avatar_catalog(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:avatar:catalog", 240, 60)
    return _sw_avatar_catalog(auth.tenant_id)


def operation_voiceover_catalog(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:voiceover:catalog", 240, 60)
    return _sw_voiceover_catalog(auth.tenant_id)


def operation_update_brand_profile(
    st: _SocialWorkspaceState, router: APIRouter, payload: BrandProfileRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:brand:update", 120, 60)
    return _sw_update_brand_profile(st, payload, auth.tenant_id)


def operation_update_ugc_template_profile(
    st: _SocialWorkspaceState, router: APIRouter, payload: UgcTemplateProfileRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:brand:ugc-template:update", 180, 60)
    return _sw_update_ugc_template(st, payload, auth.tenant_id)


def operation_fetch_brand_profile_from_website(
    st: _SocialWorkspaceState, router: APIRouter, payload: BrandWebsiteFetchRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:brand:fetch-website", 40, 60)
    return _sw_fetch_brand_from_website(st, payload.website_url, auth.tenant_id)
