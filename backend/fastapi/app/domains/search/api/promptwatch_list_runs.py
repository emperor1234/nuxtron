"""Search HTTP operations beginning with promptwatch list runs."""

from ..constants import AuthDep
from ..operations.promptwatch_product_catalog import operation_promptwatch_create_schedule
from ..operations.promptwatch_product_catalog import operation_promptwatch_execute_schedules
from ..operations.promptwatch_product_catalog import operation_promptwatch_gate_progress
from ..operations.promptwatch_product_catalog import operation_promptwatch_get_run
from ..operations.promptwatch_product_catalog import operation_promptwatch_list_runs
from ..operations.promptwatch_product_catalog import operation_promptwatch_list_schedules
from ..operations.promptwatch_product_catalog import operation_promptwatch_preflight
from ..operations.promptwatch_vendor_inventory import operation_promptwatch_vendors
from ..runtime import SearchRuntime
from ..schemas import SitebulbScheduleCreateRequest
from ..schemas import SitebulbScheduleExecuteRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/promptwatch/runs")
    def promptwatch_list_runs(auth: AuthDep, project_id: str | None = None) -> dict[str, Any]:
        return operation_promptwatch_list_runs(runtime, auth, project_id)

    @router.get("/promptwatch/runs/{run_id}")
    def promptwatch_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_get_run(runtime, run_id, auth)

    @router.post("/promptwatch/schedules")
    def promptwatch_create_schedule(payload: SitebulbScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_create_schedule(runtime, payload, auth)

    @router.get("/promptwatch/schedules")
    def promptwatch_list_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_list_schedules(runtime, auth)

    @router.post("/promptwatch/schedules/execute")
    def promptwatch_execute_schedules(payload: SitebulbScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_execute_schedules(runtime, payload, auth)

    @router.get("/promptwatch/vendors")
    def promptwatch_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_vendors(runtime, auth)

    @router.get("/promptwatch/preflight")
    def promptwatch_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_preflight(runtime, auth)

    @router.get("/promptwatch/gate-progress")
    def promptwatch_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_gate_progress(runtime, auth)
