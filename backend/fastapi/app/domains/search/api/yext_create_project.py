"""Search HTTP operations beginning with yext create project."""

from ..constants import AuthDep
from ..operations.yext_product_catalog import operation_yext_create_project
from ..operations.yext_product_catalog import operation_yext_create_schedule
from ..operations.yext_product_catalog import operation_yext_execute_schedules
from ..operations.yext_product_catalog import operation_yext_get_run
from ..operations.yext_product_catalog import operation_yext_list_projects
from ..operations.yext_product_catalog import operation_yext_list_runs
from ..operations.yext_product_catalog import operation_yext_list_schedules
from ..operations.yext_product_catalog import operation_yext_run_project
from ..runtime import SearchRuntime
from ..schemas import SitebulbScheduleCreateRequest
from ..schemas import SitebulbScheduleExecuteRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/yext/projects")
    def yext_create_project(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_yext_create_project(runtime, payload, auth)

    @router.get("/yext/projects")
    def yext_list_projects(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_list_projects(runtime, auth)

    @router.post("/yext/projects/{project_id}/run")
    def yext_run_project(project_id: str, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_yext_run_project(runtime, project_id, payload, auth)

    @router.get("/yext/runs")
    def yext_list_runs(auth: AuthDep, project_id: str | None = None) -> dict[str, Any]:
        return operation_yext_list_runs(runtime, auth, project_id)

    @router.get("/yext/runs/{run_id}")
    def yext_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_yext_get_run(runtime, run_id, auth)

    @router.post("/yext/schedules")
    def yext_create_schedule(payload: SitebulbScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_yext_create_schedule(runtime, payload, auth)

    @router.get("/yext/schedules")
    def yext_list_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_list_schedules(runtime, auth)

    @router.post("/yext/schedules/execute")
    def yext_execute_schedules(payload: SitebulbScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_yext_execute_schedules(runtime, payload, auth)
