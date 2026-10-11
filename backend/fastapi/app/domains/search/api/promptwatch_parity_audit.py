"""Search HTTP operations beginning with promptwatch parity audit."""

from ..constants import AuthDep
from ..operations.promptwatch_product_catalog import operation_promptwatch_create_project
from ..operations.promptwatch_product_catalog import operation_promptwatch_list_projects
from ..operations.promptwatch_product_catalog import operation_promptwatch_provider_checklist
from ..operations.promptwatch_product_catalog import operation_promptwatch_run_project
from ..operations.promptwatch_vendor_inventory import operation_promptwatch_full_automation
from ..operations.promptwatch_vendor_inventory import operation_promptwatch_parity_audit
from ..operations.promptwatch_vendor_inventory import operation_promptwatch_wiring_apply
from ..operations.promptwatch_vendor_inventory import operation_promptwatch_wiring_state
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SliceWiringApplyRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/promptwatch/parity-audit")
    def promptwatch_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_parity_audit(runtime, auth)

    @router.get("/promptwatch/provider-checklist")
    def promptwatch_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_provider_checklist(runtime, auth)

    @router.get("/promptwatch/wiring")
    def promptwatch_wiring_state(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_wiring_state(runtime, auth)

    @router.post("/promptwatch/wiring/apply")
    def promptwatch_wiring_apply(payload: SliceWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_wiring_apply(runtime, payload, auth)

    @router.post("/promptwatch/full-automation")
    def promptwatch_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_full_automation(runtime, payload, auth)

    @router.post("/promptwatch/projects")
    def promptwatch_create_project(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_create_project(runtime, payload, auth)

    @router.get("/promptwatch/projects")
    def promptwatch_list_projects(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_list_projects(runtime, auth)

    @router.post("/promptwatch/projects/{project_id}/run")
    def promptwatch_run_project(project_id: str, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_run_project(runtime, project_id, payload, auth)
