"""Search HTTP operations beginning with neuronwriter wiring apply."""

from ..constants import AuthDep
from ..operations.neuronwriter_wiring_apply import operation_neuronwriter_completion_chart
from ..operations.neuronwriter_wiring_apply import operation_neuronwriter_create_project
from ..operations.neuronwriter_wiring_apply import operation_neuronwriter_full_automation
from ..operations.neuronwriter_wiring_apply import operation_neuronwriter_parity_audit
from ..operations.neuronwriter_wiring_apply import operation_neuronwriter_production_gate
from ..operations.neuronwriter_wiring_apply import operation_neuronwriter_run_project
from ..operations.neuronwriter_wiring_apply import operation_neuronwriter_verification_report
from ..operations.neuronwriter_wiring_apply import operation_neuronwriter_wiring_apply
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SliceProjectCreateRequest
from ..schemas import SliceProjectRunRequest
from ..schemas import SliceWiringApplyRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/neuronwriter/wiring/apply")
    def neuronwriter_wiring_apply(payload: SliceWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_neuronwriter_wiring_apply(runtime, payload, auth)

    @router.get("/neuronwriter/parity-audit")
    def neuronwriter_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_neuronwriter_parity_audit(runtime, auth)

    @router.get("/neuronwriter/completion-chart")
    def neuronwriter_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_neuronwriter_completion_chart(runtime, auth)

    @router.get("/neuronwriter/production-gate")
    def neuronwriter_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_neuronwriter_production_gate(runtime, auth)

    @router.get("/neuronwriter/verification-report")
    def neuronwriter_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_neuronwriter_verification_report(runtime, auth)

    @router.post("/neuronwriter/full-automation")
    def neuronwriter_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_neuronwriter_full_automation(runtime, payload, auth)

    @router.post("/neuronwriter/projects")
    def neuronwriter_create_project(payload: SliceProjectCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_neuronwriter_create_project(runtime, payload, auth)

    @router.post("/neuronwriter/projects/{project_id}/run")
    def neuronwriter_run_project(project_id: str, payload: SliceProjectRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_neuronwriter_run_project(runtime, project_id, payload, auth)
