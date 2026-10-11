"""Social HTTP adapters: delete community saved reply."""

from ....domains.social.persistence import _SocialWorkspaceState
from ..constants import AuthDep
from ..extended_schemas import AIAssistantRequest
from ..extended_schemas import CustomReportRequest
from ..operations.create_mobile_quick_post import operation_create_custom_report
from ..operations.create_mobile_quick_post import operation_delete_community_saved_reply
from ..operations.create_mobile_quick_post import operation_get_analytics_overview
from ..operations.create_mobile_quick_post import operation_get_audience_insights
from ..operations.create_mobile_quick_post import operation_get_best_time_to_post
from ..operations.create_mobile_quick_post import operation_list_analytics_reports
from ..operations.download_report import operation_ai_assistant
from ..operations.download_report import operation_download_report
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.delete(
        "/social/community/saved-replies/{reply_id}", responses={404: {"description": "Saved reply not found"}}
    )
    def delete_community_saved_reply(reply_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_delete_community_saved_reply(st, router, reply_id, auth)

    @router.get("/social/analytics/overview")
    def get_analytics_overview(
        auth: AuthDep, networks: str = "instagram,facebook,linkedin,x", days: int = 30
    ) -> dict[str, Any]:
        return operation_get_analytics_overview(st, router, auth, networks, days)

    @router.get("/social/analytics/best-time/{network}")
    def get_best_time_to_post(network: str, auth: AuthDep) -> dict[str, Any]:
        return operation_get_best_time_to_post(st, router, network, auth)

    @router.get("/social/analytics/audience/{network}")
    def get_audience_insights(network: str, auth: AuthDep) -> dict[str, Any]:
        return operation_get_audience_insights(st, router, network, auth)

    @router.post("/social/analytics/custom-report")
    def create_custom_report(payload: CustomReportRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_custom_report(st, router, payload, auth)

    @router.get("/social/analytics/reports")
    def list_analytics_reports(auth: AuthDep) -> dict[str, Any]:
        return operation_list_analytics_reports(st, router, auth)

    @router.get("/social/analytics/reports/{report_id}/download", responses={404: {"description": "Report not found"}})
    def download_report(report_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_download_report(st, router, report_id, auth)

    @router.post("/social/ai-assistant")
    def ai_assistant(payload: AIAssistantRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_ai_assistant(st, router, payload, auth)
