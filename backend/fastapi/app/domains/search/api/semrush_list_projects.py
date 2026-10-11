"""Search HTTP operations beginning with semrush list projects."""

from ..constants import AuthDep
from ..operations.botify_list_runs import operation_botify_list_runs
from ..operations.botify_list_runs import operation_botify_parity_audit
from ..operations.semrush_list_projects import operation_semrush_create_project
from ..operations.semrush_list_projects import operation_semrush_list_projects
from ..operations.semrush_list_projects import operation_semrush_list_runs
from ..operations.semrush_list_projects import operation_semrush_run_project
from ..operations.seoai_list_runs import operation_seoai_list_runs
from ..operations.seoai_list_runs import operation_seoai_parity_audit
from ..runtime import SearchRuntime
from ..schemas import SliceProjectCreateRequest
from ..schemas import SliceProjectRunRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/semrush/projects")
    def semrush_list_projects(auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_list_projects(runtime, auth)

    @router.post("/semrush/projects")
    def semrush_create_project(payload: SliceProjectCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_create_project(runtime, payload, auth)

    @router.post("/semrush/projects/{project_id}/run")
    def semrush_run_project(project_id: str, payload: SliceProjectRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_run_project(runtime, project_id, payload, auth)

    @router.get("/semrush/runs")
    def semrush_list_runs(auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_list_runs(runtime, auth)

    @router.get("/botify/parity-audit")
    def botify_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_botify_parity_audit(runtime, auth)

    @router.get("/botify/runs")
    def botify_list_runs(auth: AuthDep) -> dict[str, Any]:
        return operation_botify_list_runs(runtime, auth)

    @router.get("/seoai/parity-audit")
    def seoai_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_parity_audit(runtime, auth)

    @router.get("/seoai/runs")
    def seoai_list_runs(auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_list_runs(runtime, auth)
