"""Search HTTP operations beginning with botify run project."""

from ..constants import AuthDep
from ..operations.botify_list_runs import operation_botify_create_schedule
from ..operations.botify_list_runs import operation_botify_execute_schedules
from ..operations.botify_list_runs import operation_botify_gate_progress
from ..operations.botify_list_runs import operation_botify_get_run
from ..operations.botify_list_runs import operation_botify_preflight
from ..operations.botify_list_runs import operation_botify_provider_checklist
from ..operations.botify_list_runs import operation_botify_run_project
from ..operations.botify_list_runs import operation_botify_vendors
from ..runtime import SearchRuntime
from ..schemas import SliceProjectRunRequest
from ..schemas import SliceScheduleCreateRequest
from ..schemas import SliceScheduleExecuteRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/botify/projects/{project_id}/run")
    def botify_run_project(project_id: str, payload: SliceProjectRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_botify_run_project(runtime, project_id, payload, auth)

    @router.get("/botify/runs/{run_id}")
    def botify_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_botify_get_run(runtime, run_id, auth)

    @router.post("/botify/schedules")
    def botify_create_schedule(payload: SliceScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_botify_create_schedule(runtime, payload, auth)

    @router.post("/botify/schedules/execute")
    def botify_execute_schedules(payload: SliceScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_botify_execute_schedules(runtime, payload, auth)

    @router.get("/botify/vendors")
    def botify_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_botify_vendors(runtime, auth)

    @router.get("/botify/provider-checklist")
    def botify_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_botify_provider_checklist(runtime, auth)

    @router.get("/botify/preflight")
    def botify_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_botify_preflight(runtime, auth)

    @router.get("/botify/gate-progress")
    def botify_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_botify_gate_progress(runtime, auth)
