"""Search HTTP operations beginning with writesonic wiring state."""

from ..constants import AuthDep
from ..operations.writesonic_product_catalog import operation_writesonic_run_project
from ..operations.writesonic_products_completion_chart import operation_writesonic_create_project
from ..operations.writesonic_products_completion_chart import operation_writesonic_full_automation
from ..operations.writesonic_products_completion_chart import operation_writesonic_get_run
from ..operations.writesonic_products_completion_chart import operation_writesonic_list_projects
from ..operations.writesonic_products_completion_chart import operation_writesonic_list_runs
from ..operations.writesonic_products_completion_chart import operation_writesonic_wiring_apply
from ..operations.writesonic_products_completion_chart import operation_writesonic_wiring_state
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SliceWiringApplyRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/writesonic/wiring")
    def writesonic_wiring_state(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_wiring_state(runtime, auth)

    @router.post("/writesonic/wiring/apply")
    def writesonic_wiring_apply(payload: SliceWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_wiring_apply(runtime, payload, auth)

    @router.post("/writesonic/full-automation")
    def writesonic_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_full_automation(runtime, payload, auth)

    @router.post("/writesonic/projects")
    def writesonic_create_project(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_create_project(runtime, payload, auth)

    @router.get("/writesonic/projects")
    def writesonic_list_projects(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_list_projects(runtime, auth)

    @router.post("/writesonic/projects/{project_id}/run")
    def writesonic_run_project(project_id: str, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_run_project(runtime, project_id, payload, auth)

    @router.get("/writesonic/runs")
    def writesonic_list_runs(auth: AuthDep, project_id: str | None = None) -> dict[str, Any]:
        return operation_writesonic_list_runs(runtime, auth, project_id)

    @router.get("/writesonic/runs/{run_id}")
    def writesonic_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_get_run(runtime, run_id, auth)
