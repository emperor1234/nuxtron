"""Search HTTP operations beginning with marketmuse wiring apply."""

from ..constants import AuthDep
from ..operations.marketmuse_product_catalog import operation_marketmuse_create_project
from ..operations.marketmuse_product_catalog import operation_marketmuse_create_schedule
from ..operations.marketmuse_product_catalog import operation_marketmuse_get_run
from ..operations.marketmuse_product_catalog import operation_marketmuse_list_projects
from ..operations.marketmuse_product_catalog import operation_marketmuse_list_runs
from ..operations.marketmuse_product_catalog import operation_marketmuse_run_project
from ..operations.marketmuse_vendor_inventory import operation_marketmuse_full_automation
from ..operations.marketmuse_vendor_inventory import operation_marketmuse_wiring_apply
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SitebulbScheduleCreateRequest
from ..schemas import SliceWiringApplyRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/marketmuse/wiring/apply")
    def marketmuse_wiring_apply(payload: SliceWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_wiring_apply(runtime, payload, auth)

    @router.post("/marketmuse/full-automation")
    def marketmuse_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_full_automation(runtime, payload, auth)

    @router.post("/marketmuse/projects")
    def marketmuse_create_project(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_create_project(runtime, payload, auth)

    @router.get("/marketmuse/projects")
    def marketmuse_list_projects(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_list_projects(runtime, auth)

    @router.post("/marketmuse/projects/{project_id}/run")
    def marketmuse_run_project(project_id: str, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_run_project(runtime, project_id, payload, auth)

    @router.get("/marketmuse/runs")
    def marketmuse_list_runs(auth: AuthDep, project_id: str | None = None) -> dict[str, Any]:
        return operation_marketmuse_list_runs(runtime, auth, project_id)

    @router.get("/marketmuse/runs/{run_id}")
    def marketmuse_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_get_run(runtime, run_id, auth)

    @router.post("/marketmuse/schedules")
    def marketmuse_create_schedule(payload: SitebulbScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_create_schedule(runtime, payload, auth)
