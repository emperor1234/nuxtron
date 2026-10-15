"""Social HTTP adapters: get ugc performance."""

from typing import Any

from fastapi import APIRouter

from ....domains.social.persistence import _SocialWorkspaceState
from ..constants import AuthDep
from ..operations.request_ugc_rights import operation_get_ugc_performance
from ..ugc_unavailable import UGC_UNAVAILABLE_RESPONSES


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get(
        "/social/ugc/performance",
        status_code=501,
        response_model=None,
        responses=UGC_UNAVAILABLE_RESPONSES,
    )
    def get_ugc_performance(asset_id: int | None = None, *, auth: AuthDep) -> dict[str, Any]:
        return operation_get_ugc_performance(st, router, asset_id, auth=auth)
