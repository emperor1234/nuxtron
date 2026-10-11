"""Search HTTP operations beginning with frase provider probes."""

from ..constants import AuthDep
from ..operations.frase_provider_checklist import operation_frase_env_template
from ..operations.frase_provider_checklist import operation_frase_full_automation
from ..operations.frase_provider_checklist import operation_frase_provider_probes
from ..operations.sitebulb_completion_chart import operation_sitebulb_run_project
from ..operations.sitebulb_project_lookup import operation_sitebulb_create_project
from ..operations.sitebulb_project_lookup import operation_sitebulb_get_run
from ..operations.sitebulb_project_lookup import operation_sitebulb_list_projects
from ..operations.sitebulb_project_lookup import operation_sitebulb_list_runs
from ..runtime import SearchRuntime
from ..schemas import FraseEnvTemplateRequest
from ..schemas import FraseFullAutomationRequest
from ..schemas import FraseProviderProbeRequest
from ..schemas import SitebulbProjectCreateRequest
from ..schemas import SitebulbProjectRunRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/frase/provider-probes")
    def frase_provider_probes(payload: FraseProviderProbeRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_frase_provider_probes(runtime, payload, auth)

    @router.post("/frase/env-template")
    def frase_env_template(payload: FraseEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_frase_env_template(runtime, payload, auth)

    @router.post("/frase/full-automation")
    def frase_full_automation(payload: FraseFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_frase_full_automation(runtime, payload, auth)

    @router.post("/sitebulb/projects")
    def sitebulb_create_project(payload: SitebulbProjectCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_create_project(runtime, payload, auth)

    @router.get("/sitebulb/projects")
    def sitebulb_list_projects(auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_list_projects(runtime, auth)

    @router.post("/sitebulb/projects/{project_id}/run")
    def sitebulb_run_project(project_id: str, payload: SitebulbProjectRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_run_project(runtime, project_id, payload, auth)

    @router.get("/sitebulb/runs")
    def sitebulb_list_runs(auth: AuthDep, project_id: str | None = None) -> dict[str, Any]:
        return operation_sitebulb_list_runs(runtime, auth, project_id)

    @router.get("/sitebulb/runs/{run_id}")
    def sitebulb_get_run(run_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_get_run(runtime, run_id, auth)
