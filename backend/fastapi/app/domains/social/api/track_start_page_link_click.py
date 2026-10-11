"""Social HTTP adapters: track start page link click."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import BestStackReportCreateRequest
from ..constants import AuthDep
from ..operations.create_best_stack_report import operation_create_best_stack_report
from ..operations.create_best_stack_report import operation_social_growth_integration_matrix
from ..operations.download_report import operation_track_start_page_link_click
from ..operations.export_best_stack_report import operation_export_best_stack_report
from ..operations.export_best_stack_report import operation_get_social_audit_log
from ..operations.integration_growth_specs import operation_list_best_stack_reports
from ..operations.invite_team_member_legacy import operation_social_production_readiness
from ..operations.social_production_readiness_remediation_plan import (
    operation_social_production_readiness_remediation_plan,
)
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.post("/social/start-page/links/{link_id}/click")
    def track_start_page_link_click(link_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_track_start_page_link_click(st, router, link_id, auth)

    @router.get("/social/production-readiness")
    def social_production_readiness(auth: AuthDep) -> dict[str, Any]:
        return operation_social_production_readiness(st, router, auth)

    @router.get("/social/production-readiness/remediation-plan")
    def social_production_readiness_remediation_plan(auth: AuthDep) -> dict[str, Any]:
        return operation_social_production_readiness_remediation_plan(st, router, auth)

    @router.post("/social/production-readiness/best-stack-report")
    def create_best_stack_report(payload: BestStackReportCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_best_stack_report(st, router, payload, auth)

    @router.get("/social/production-readiness/best-stack-reports")
    def list_best_stack_reports(auth: AuthDep) -> dict[str, Any]:
        return operation_list_best_stack_reports(st, router, auth)

    @router.get(
        "/social/production-readiness/best-stack-report/{report_id}/export",
        responses={404: {"description": "Report not found"}},
    )
    def export_best_stack_report(report_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_export_best_stack_report(st, router, report_id, auth)

    @router.get("/social/audit-log")
    def get_social_audit_log(auth: AuthDep, limit: int = 100) -> dict[str, Any]:
        return operation_get_social_audit_log(st, router, auth, limit)

    @router.get("/social/integrations/growth-matrix")
    def social_growth_integration_matrix(auth: AuthDep) -> dict[str, Any]:
        return operation_social_growth_integration_matrix(st, router, auth)
