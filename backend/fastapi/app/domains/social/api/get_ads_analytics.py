"""Social HTTP adapters: get ads analytics."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import BulkScheduleRequest
from ....domains.social.schemas import ReportCreateRequest
from ..constants import AuthDep
from ..operations.create_mobile_quick_post import operation_get_best_time_to_post
from ..operations.get_ads_analytics import operation_bulk_schedule_posts
from ..operations.get_ads_analytics import operation_create_report
from ..operations.get_ads_analytics import operation_delete_report
from ..operations.get_ads_analytics import operation_export_report
from ..operations.get_ads_analytics import operation_get_ads_analytics
from ..operations.get_ads_analytics import operation_get_report
from ..operations.get_ads_analytics import operation_list_reports
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/ads/analytics")
    def get_ads_analytics(auth: AuthDep) -> dict[str, Any]:
        return operation_get_ads_analytics(st, router, auth)

    @router.get("/social/reports")
    def list_reports(auth: AuthDep) -> dict[str, Any]:
        return operation_list_reports(st, router, auth)

    @router.post("/social/reports")
    def create_report(payload: ReportCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_report(st, router, payload, auth)

    @router.get("/social/reports/{report_id}", responses={404: {"description": "Report not found"}})
    def get_report(report_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_get_report(st, router, report_id, auth)

    @router.post("/social/reports/{report_id}/export", responses={404: {"description": "Report not found"}})
    def export_report(report_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_export_report(st, router, report_id, auth)

    @router.delete("/social/reports/{report_id}", responses={404: {"description": "Report not found"}})
    def delete_report(report_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_delete_report(st, router, report_id, auth)

    @router.get("/social/best-time")
    def get_best_time_to_post(auth: AuthDep) -> dict[str, Any]:
        return operation_get_best_time_to_post(st, router, auth)

    @router.post("/social/bulk-schedule")
    def bulk_schedule_posts(payload: BulkScheduleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_bulk_schedule_posts(st, router, payload, auth)
