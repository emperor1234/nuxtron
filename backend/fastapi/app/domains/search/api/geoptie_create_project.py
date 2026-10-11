"""Search HTTP operations beginning with geoptie create project."""

from ..constants import AuthDep
from ..operations.geoptie_product_catalog import operation_geoptie_create_project
from ..operations.geoptie_product_catalog import operation_geoptie_create_schedule
from ..operations.geoptie_product_catalog import operation_geoptie_execute_schedules
from ..operations.geoptie_product_catalog import operation_geoptie_get_run
from ..operations.geoptie_product_catalog import operation_geoptie_list_projects
from ..operations.geoptie_product_catalog import operation_geoptie_list_runs
from ..operations.geoptie_product_catalog import operation_geoptie_list_schedules
from ..operations.geoptie_product_catalog import operation_geoptie_run_project
from ..runtime import SearchRuntime
from ..schemas import SitebulbScheduleCreateRequest
from ..schemas import SitebulbScheduleExecuteRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/geoptie/projects")
    def geoptie_create_project(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_create_project(runtime, payload, auth)

    @router.get("/geoptie/projects")
    def geoptie_list_projects(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_list_projects(runtime, auth)

    @router.post("/geoptie/projects/{project_id}/run")
    def geoptie_run_project(project_id: str, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_run_project(runtime, project_id, payload, auth)

    @router.get("/geoptie/runs")
    def geoptie_list_runs(auth: AuthDep, project_id: str | None = None) -> dict[str, Any]:
        return operation_geoptie_list_runs(runtime, auth, project_id)

    @router.get("/geoptie/runs/{run_id}")
    def geoptie_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_get_run(runtime, run_id, auth)

    @router.post("/geoptie/schedules")
    def geoptie_create_schedule(payload: SitebulbScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_create_schedule(runtime, payload, auth)

    @router.get("/geoptie/schedules")
    def geoptie_list_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_list_schedules(runtime, auth)

    @router.post("/geoptie/schedules/execute")
    def geoptie_execute_schedules(payload: SitebulbScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_execute_schedules(runtime, payload, auth)
