"""Social HTTP adapters: list bulk schedule jobs."""

from typing import Any

from fastapi import APIRouter

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import UgcApproveRequest, UgcRepublishRequest
from ..constants import AuthDep
from ..operations.get_ads_analytics import (
    operation_approve_ugc_asset,
    operation_discover_ugc_assets,
    operation_get_bulk_schedule_template,
    operation_list_bulk_schedule_jobs,
    operation_list_ugc_assets,
    operation_republish_ugc_asset,
)
from ..operations.request_ugc_rights import operation_batch_approve_ugc, operation_request_ugc_rights
from ..ugc_unavailable import UGC_UNAVAILABLE_RESPONSES


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/bulk-schedule/jobs")
    def list_bulk_schedule_jobs(auth: AuthDep) -> dict[str, Any]:
        return operation_list_bulk_schedule_jobs(st, router, auth)

    @router.get("/social/bulk-schedule/template")
    def get_bulk_schedule_template(auth: AuthDep) -> dict[str, Any]:
        return operation_get_bulk_schedule_template(st, router, auth)

    @router.post(
        "/social/ugc/discover",
        status_code=501,
        response_model=None,
        responses=UGC_UNAVAILABLE_RESPONSES,
    )
    def discover_ugc_assets(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_discover_ugc_assets(st, router, payload, auth)

    @router.get("/social/ugc", status_code=501, response_model=None, responses=UGC_UNAVAILABLE_RESPONSES)
    def list_ugc_assets(
        sentiment: str | None = None, rights_status: str | None = None, *, auth: AuthDep
    ) -> dict[str, Any]:
        return operation_list_ugc_assets(st, router, sentiment, rights_status, auth=auth)

    @router.patch(
        "/social/ugc/{asset_id}/approve",
        status_code=501,
        response_model=None,
        responses=UGC_UNAVAILABLE_RESPONSES,
    )
    def approve_ugc_asset(asset_id: int, payload: UgcApproveRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_approve_ugc_asset(st, router, asset_id, payload, auth)

    @router.post(
        "/social/ugc/{asset_id}/republish",
        status_code=501,
        response_model=None,
        responses=UGC_UNAVAILABLE_RESPONSES,
    )
    def republish_ugc_asset(asset_id: int, auth: AuthDep, payload: UgcRepublishRequest | None = None) -> dict[str, Any]:
        return operation_republish_ugc_asset(st, router, asset_id, auth, payload)

    @router.post(
        "/social/ugc/{asset_id}/request-rights",
        status_code=501,
        response_model=None,
        responses=UGC_UNAVAILABLE_RESPONSES,
    )
    def request_ugc_rights(asset_id: int, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_request_ugc_rights(st, router, asset_id, payload, auth)

    @router.post(
        "/social/ugc/batch/approve",
        status_code=501,
        response_model=None,
        responses=UGC_UNAVAILABLE_RESPONSES,
    )
    def batch_approve_ugc(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_batch_approve_ugc(st, router, payload, auth)
