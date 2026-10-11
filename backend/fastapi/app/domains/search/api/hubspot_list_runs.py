"""Search HTTP operations beginning with hubspot list runs."""

from ..constants import AuthDep
from ..operations.hubspot_product_catalog import operation_hubspot_execute_schedules
from ..operations.hubspot_product_catalog import operation_hubspot_gate_progress
from ..operations.hubspot_route_coverage_chart import operation_hubspot_vendors
from ..operations.hubspot_wiring_required_keys import operation_hubspot_create_schedule
from ..operations.hubspot_wiring_required_keys import operation_hubspot_get_run
from ..operations.hubspot_wiring_required_keys import operation_hubspot_list_runs
from ..operations.hubspot_wiring_required_keys import operation_hubspot_list_schedules
from ..operations.hubspot_wiring_required_keys import operation_hubspot_preflight
from ..runtime import SearchRuntime
from ..schemas import SitebulbScheduleCreateRequest
from ..schemas import SitebulbScheduleExecuteRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/hubspot/runs")
    def hubspot_list_runs(auth: AuthDep, project_id: str | None = None) -> dict[str, Any]:
        return operation_hubspot_list_runs(runtime, auth, project_id)

    @router.get("/hubspot/runs/{run_id}")
    def hubspot_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_get_run(runtime, run_id, auth)

    @router.post("/hubspot/schedules")
    def hubspot_create_schedule(payload: SitebulbScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_create_schedule(runtime, payload, auth)

    @router.get("/hubspot/schedules")
    def hubspot_list_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_list_schedules(runtime, auth)

    @router.post("/hubspot/schedules/execute")
    def hubspot_execute_schedules(payload: SitebulbScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_execute_schedules(runtime, payload, auth)

    @router.get("/hubspot/vendors")
    def hubspot_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_vendors(runtime, auth)

    @router.get("/hubspot/preflight")
    def hubspot_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_preflight(runtime, auth)

    @router.get("/hubspot/gate-progress")
    def hubspot_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_gate_progress(runtime, auth)
