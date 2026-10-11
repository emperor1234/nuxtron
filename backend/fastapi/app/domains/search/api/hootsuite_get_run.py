"""Search HTTP operations beginning with hootsuite get run."""

from ..constants import AuthDep
from ..operations.hootsuite_features import operation_hootsuite_create_schedule
from ..operations.hootsuite_features import operation_hootsuite_env_template
from ..operations.hootsuite_features import operation_hootsuite_get_run
from ..operations.hootsuite_features import operation_hootsuite_list_schedules
from ..operations.hootsuite_features import operation_hootsuite_preflight
from ..operations.hootsuite_features import operation_hootsuite_vendors
from ..operations.hootsuite_product_catalog import operation_hootsuite_gate_progress
from ..operations.hootsuite_wiring_apply import operation_hootsuite_execute_schedules
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbScheduleCreateRequest
from ..schemas import SitebulbScheduleExecuteRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/hootsuite/runs/{run_id}")
    def hootsuite_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_get_run(runtime, run_id, auth)

    @router.post("/hootsuite/schedules")
    def hootsuite_create_schedule(payload: SitebulbScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_create_schedule(runtime, payload, auth)

    @router.get("/hootsuite/schedules")
    def hootsuite_list_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_list_schedules(runtime, auth)

    @router.post("/hootsuite/schedules/execute")
    def hootsuite_execute_schedules(payload: SitebulbScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_execute_schedules(runtime, payload, auth)

    @router.get("/hootsuite/vendors")
    def hootsuite_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_vendors(runtime, auth)

    @router.get("/hootsuite/preflight")
    def hootsuite_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_preflight(runtime, auth)

    @router.get("/hootsuite/gate-progress")
    def hootsuite_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_gate_progress(runtime, auth)

    @router.post("/hootsuite/env-template")
    def hootsuite_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_env_template(runtime, payload, auth)
