"""Search HTTP operations beginning with seoai run project."""

from ..constants import AuthDep
from ..operations.seoai_list_runs import operation_seoai_create_schedule
from ..operations.seoai_list_runs import operation_seoai_execute_schedules
from ..operations.seoai_list_runs import operation_seoai_gate_progress
from ..operations.seoai_list_runs import operation_seoai_get_run
from ..operations.seoai_list_runs import operation_seoai_preflight
from ..operations.seoai_list_runs import operation_seoai_provider_checklist
from ..operations.seoai_list_runs import operation_seoai_run_project
from ..operations.seoai_list_runs import operation_seoai_vendors
from ..runtime import SearchRuntime
from ..schemas import SliceProjectRunRequest
from ..schemas import SliceScheduleCreateRequest
from ..schemas import SliceScheduleExecuteRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/seoai/projects/{project_id}/run")
    def seoai_run_project(project_id: str, payload: SliceProjectRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_run_project(runtime, project_id, payload, auth)

    @router.get("/seoai/runs/{run_id}")
    def seoai_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_get_run(runtime, run_id, auth)

    @router.post("/seoai/schedules")
    def seoai_create_schedule(payload: SliceScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_create_schedule(runtime, payload, auth)

    @router.post("/seoai/schedules/execute")
    def seoai_execute_schedules(payload: SliceScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_execute_schedules(runtime, payload, auth)

    @router.get("/seoai/vendors")
    def seoai_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_vendors(runtime, auth)

    @router.get("/seoai/provider-checklist")
    def seoai_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_provider_checklist(runtime, auth)

    @router.get("/seoai/preflight")
    def seoai_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_preflight(runtime, auth)

    @router.get("/seoai/gate-progress")
    def seoai_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_gate_progress(runtime, auth)
