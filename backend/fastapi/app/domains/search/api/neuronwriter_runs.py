"""Search HTTP operations beginning with neuronwriter runs."""

from ..constants import AuthDep
from ..operations.clearscope_client_config import operation_clearscope_completion_chart
from ..operations.clearscope_client_config import operation_clearscope_create_content_report
from ..operations.clearscope_client_config import operation_clearscope_full_automation
from ..operations.clearscope_client_config import operation_clearscope_get_content_report
from ..operations.clearscope_client_config import operation_clearscope_get_content_report_brief
from ..operations.clearscope_client_config import operation_clearscope_get_content_report_terms
from ..operations.clearscope_client_config import operation_clearscope_wiring_apply
from ..operations.neuronwriter_wiring_apply import operation_neuronwriter_runs
from ..runtime import SearchRuntime
from ..schemas import ClearscopeContentReportCreateRequest
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SliceWiringApplyRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/neuronwriter/runs")
    def neuronwriter_runs(auth: AuthDep) -> dict[str, Any]:
        return operation_neuronwriter_runs(runtime, auth)

    @router.post("/clearscope/wiring/apply")
    def clearscope_wiring_apply(payload: SliceWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_clearscope_wiring_apply(runtime, payload, auth)

    @router.post("/clearscope/content-report")
    def clearscope_create_content_report(
        payload: ClearscopeContentReportCreateRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return operation_clearscope_create_content_report(runtime, payload, auth)

    @router.get("/clearscope/content-report/{report_id}")
    def clearscope_get_content_report(report_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_clearscope_get_content_report(runtime, report_id, auth)

    @router.get("/clearscope/content-report/{report_id}/terms")
    def clearscope_get_content_report_terms(report_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_clearscope_get_content_report_terms(runtime, report_id, auth)

    @router.get("/clearscope/content-report/{report_id}/brief")
    def clearscope_get_content_report_brief(report_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_clearscope_get_content_report_brief(runtime, report_id, auth)

    @router.post("/clearscope/full-automation")
    def clearscope_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_clearscope_full_automation(runtime, payload, auth)

    @router.get("/clearscope/completion-chart")
    def clearscope_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_clearscope_completion_chart(runtime, auth)
