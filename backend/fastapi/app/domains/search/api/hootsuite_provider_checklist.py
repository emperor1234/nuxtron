"""Search HTTP operations beginning with hootsuite provider checklist."""

from ..constants import AuthDep
from ..operations.hootsuite_features import operation_hootsuite_create_project
from ..operations.hootsuite_features import operation_hootsuite_list_projects
from ..operations.hootsuite_features import operation_hootsuite_list_runs
from ..operations.hootsuite_features import operation_hootsuite_provider_checklist
from ..operations.hootsuite_features import operation_hootsuite_wiring_state
from ..operations.hootsuite_product_catalog import operation_hootsuite_run_project
from ..operations.hootsuite_wiring_apply import operation_hootsuite_full_automation
from ..operations.hootsuite_wiring_apply import operation_hootsuite_wiring_apply
from ..runtime import SearchRuntime
from ..schemas import HootsuiteWiringApplyRequest
from ..schemas import SemrushFullAutomationRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/hootsuite/provider-checklist")
    def hootsuite_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_provider_checklist(runtime, auth)

    @router.get("/hootsuite/wiring")
    def hootsuite_wiring_state(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_wiring_state(runtime, auth)

    @router.post("/hootsuite/wiring/apply")
    def hootsuite_wiring_apply(payload: HootsuiteWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_wiring_apply(runtime, payload, auth)

    @router.post("/hootsuite/full-automation")
    def hootsuite_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_full_automation(runtime, payload, auth)

    @router.post("/hootsuite/projects")
    def hootsuite_create_project(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_create_project(runtime, payload, auth)

    @router.get("/hootsuite/projects")
    def hootsuite_list_projects(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_list_projects(runtime, auth)

    @router.post("/hootsuite/projects/{project_id}/run")
    def hootsuite_run_project(project_id: str, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_run_project(runtime, project_id, payload, auth)

    @router.get("/hootsuite/runs")
    def hootsuite_list_runs(auth: AuthDep, project_id: str | None = None) -> dict[str, Any]:
        return operation_hootsuite_list_runs(runtime, auth, project_id)
