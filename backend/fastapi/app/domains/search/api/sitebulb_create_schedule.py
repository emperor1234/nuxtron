"""Search HTTP operations beginning with sitebulb create schedule."""

from typing import Any

from fastapi import APIRouter

from ..constants import AuthDep
from ..operations.botify_list_runs import operation_botify_create_project
from ..operations.sitebulb_completion_chart import (
    operation_sitebulb_execute_schedules,
    operation_sitebulb_gate_progress,
)
from ..operations.sitebulb_project_lookup import (
    operation_sitebulb_create_schedule,
    operation_sitebulb_env_template,
    operation_sitebulb_list_schedules,
    operation_sitebulb_preflight,
    operation_sitebulb_vendors,
)
from ..runtime import SearchRuntime
from ..schemas import (
    SitebulbEnvTemplateRequest,
    SitebulbScheduleCreateRequest,
    SitebulbScheduleExecuteRequest,
    SliceProjectCreateRequest,
)
from .keyword_unavailable_response import KEYWORD_RESEARCH_501_RESPONSE


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/sitebulb/schedules")
    def sitebulb_create_schedule(payload: SitebulbScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_create_schedule(runtime, payload, auth)

    @router.get("/sitebulb/schedules")
    def sitebulb_list_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_list_schedules(runtime, auth)

    @router.post("/sitebulb/schedules/execute", status_code=501, response_model=None, responses={501: KEYWORD_RESEARCH_501_RESPONSE})
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
