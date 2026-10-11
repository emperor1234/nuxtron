"""Social HTTP adapters: get ugc performance."""

from ....domains.social.persistence import _SocialWorkspaceState
from ..constants import AuthDep
from ..operations.request_ugc_rights import operation_get_ugc_performance
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/ugc/performance")
    def get_ugc_performance(asset_id: int | None = None, *, auth: AuthDep) -> dict[str, Any]:
        return operation_get_ugc_performance(st, router, asset_id, auth=auth)
