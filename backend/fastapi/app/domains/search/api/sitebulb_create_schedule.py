"""Search HTTP operations beginning with sitebulb create schedule."""

from ..constants import AuthDep
from ..operations.botify_list_runs import operation_botify_create_project
from ..operations.sitebulb_completion_chart import operation_sitebulb_execute_schedules
from ..operations.sitebulb_completion_chart import operation_sitebulb_gate_progress
from ..operations.sitebulb_project_lookup import operation_sitebulb_create_schedule
from ..operations.sitebulb_project_lookup import operation_sitebulb_env_template
from ..operations.sitebulb_project_lookup import operation_sitebulb_list_schedules
from ..operations.sitebulb_project_lookup import operation_sitebulb_preflight
from ..operations.sitebulb_project_lookup import operation_sitebulb_vendors
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbScheduleCreateRequest
from ..schemas import SitebulbScheduleExecuteRequest
from ..schemas import SliceProjectCreateRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/sitebulb/schedules")
    def sitebulb_create_schedule(payload: SitebulbScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_create_schedule(runtime, payload, auth)

    @router.get("/sitebulb/schedules")
    def sitebulb_list_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_list_schedules(runtime, auth)

    @router.post("/sitebulb/schedules/execute")
    def sitebulb_execute_schedules(payload: SitebulbScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_execute_schedules(runtime, payload, auth)

    @router.get("/sitebulb/vendors")
    def sitebulb_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_vendors(runtime, auth)

    @router.get("/sitebulb/preflight")
    def sitebulb_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_preflight(runtime, auth)

    @router.get("/sitebulb/gate-progress")
    def sitebulb_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_gate_progress(runtime, auth)

    @router.post("/sitebulb/env-template")
    def sitebulb_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_env_template(runtime, payload, auth)

    @router.post("/botify/projects")
    def botify_create_project(payload: SliceProjectCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_botify_create_project(runtime, payload, auth)
