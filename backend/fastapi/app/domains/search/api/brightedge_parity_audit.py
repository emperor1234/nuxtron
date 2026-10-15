"""Search HTTP operations beginning with brightedge parity audit."""

from typing import Any

from fastapi import APIRouter

from ..constants import AuthDep
from ..operations.brightedge_product_catalog import (
    operation_brightedge_create_project,
    operation_brightedge_list_projects,
    operation_brightedge_provider_checklist,
    operation_brightedge_run_project,
)
from ..operations.brightedge_vendor_inventory import (
    operation_brightedge_full_automation,
    operation_brightedge_parity_audit,
    operation_brightedge_wiring_apply,
    operation_brightedge_wiring_state,
)
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest, SliceWiringApplyRequest
from .keyword_unavailable_response import KEYWORD_RESEARCH_501_RESPONSE


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/brightedge/parity-audit")
    def brightedge_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_parity_audit(runtime, auth)

    @router.get("/brightedge/provider-checklist")
    def brightedge_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_provider_checklist(runtime, auth)

    @router.get("/brightedge/wiring")
    def brightedge_wiring_state(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_wiring_state(runtime, auth)

    @router.post("/brightedge/wiring/apply")
    def brightedge_wiring_apply(payload: SliceWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_wiring_apply(runtime, payload, auth)

    @router.post("/brightedge/full-automation", status_code=501, response_model=None, responses={501: KEYWORD_RESEARCH_501_RESPONSE})
    def brightedge_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_full_automation(runtime, payload, auth)

    @router.post("/brightedge/projects")
    def brightedge_create_project(payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_create_project(runtime, payload, auth)

    @router.get("/brightedge/projects")
    def brightedge_list_projects(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_list_projects(runtime, auth)

    @router.post("/brightedge/projects/{project_id}/run")
    def brightedge_run_project(project_id: str, payload: dict[str, Any], auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_run_project(runtime, project_id, payload, auth)
