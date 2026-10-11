"""Search HTTP operations beginning with brightedge list runs."""

from ..constants import AuthDep
from ..operations.brightedge_product_catalog import operation_brightedge_create_schedule
from ..operations.brightedge_product_catalog import operation_brightedge_execute_schedules
from ..operations.brightedge_product_catalog import operation_brightedge_gate_progress
from ..operations.brightedge_product_catalog import operation_brightedge_get_run
from ..operations.brightedge_product_catalog import operation_brightedge_list_runs
from ..operations.brightedge_product_catalog import operation_brightedge_list_schedules
from ..operations.brightedge_product_catalog import operation_brightedge_preflight
from ..operations.brightedge_vendor_inventory import operation_brightedge_vendors
from ..runtime import SearchRuntime
from ..schemas import SitebulbScheduleCreateRequest
from ..schemas import SitebulbScheduleExecuteRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/brightedge/runs")
    def brightedge_list_runs(auth: AuthDep, project_id: str | None = None) -> dict[str, Any]:
        return operation_brightedge_list_runs(runtime, auth, project_id)

    @router.get("/brightedge/runs/{run_id}")
    def brightedge_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_get_run(runtime, run_id, auth)

    @router.post("/brightedge/schedules")
    def brightedge_create_schedule(payload: SitebulbScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_create_schedule(runtime, payload, auth)

    @router.get("/brightedge/schedules")
    def brightedge_list_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_list_schedules(runtime, auth)

    @router.post("/brightedge/schedules/execute")
    def brightedge_execute_schedules(payload: SitebulbScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_execute_schedules(runtime, payload, auth)

    @router.get("/brightedge/vendors")
    def brightedge_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_vendors(runtime, auth)

    @router.get("/brightedge/preflight")
    def brightedge_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_preflight(runtime, auth)

    @router.get("/brightedge/gate-progress")
    def brightedge_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_gate_progress(runtime, auth)
