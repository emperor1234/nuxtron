"""Search HTTP operations beginning with hubspot provider checklist."""

from ..constants import AuthDep
from ..operations.hubspot_product_catalog import operation_hubspot_full_automation
from ..operations.hubspot_product_catalog import operation_hubspot_run_project
from ..operations.hubspot_wiring_required_keys import operation_hubspot_create_project
from ..operations.hubspot_wiring_required_keys import operation_hubspot_list_projects
from ..operations.hubspot_wiring_required_keys import operation_hubspot_provider_checklist
from ..operations.hubspot_wiring_required_keys import operation_hubspot_wiring_apply
from ..operations.hubspot_wiring_required_keys import operation_hubspot_wiring_required_keys
from ..operations.hubspot_wiring_required_keys import operation_hubspot_wiring_state
from ..runtime import SearchRuntime
from ..schemas import HubspotWiringApplyRequest
from ..schemas import SemrushFullAutomationRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/hubspot/provider-checklist")
    def hubspot_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_provider_checklist(runtime, auth)

    @router.get("/hubspot/wiring")
    def hubspot_wiring_state(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_wiring_state(runtime, auth)

    @router.get("/hubspot/wiring/required-keys")
    def hubspot_wiring_required_keys(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_wiring_required_keys(runtime, auth)

    @router.post("/hubspot/wiring/apply")
    def hubspot_wiring_apply(payload: HubspotWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_wiring_apply(runtime, payload, auth)

    @router.post("/hubspot/full-automation")
    def hubspot_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_full_automation(runtime, payload, auth)

    @router.post("/hubspot/projects")
    def hubspot_create_project(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_create_project(runtime, payload, auth)

    @router.get("/hubspot/projects")
    def hubspot_list_projects(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_list_projects(runtime, auth)

    @router.post("/hubspot/projects/{project_id}/run")
    def hubspot_run_project(project_id: str, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_run_project(runtime, project_id, payload, auth)
