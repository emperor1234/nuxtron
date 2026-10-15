"""Search HTTP operations beginning with ahrefs full automation."""

from typing import Any

from fastapi import APIRouter

from ..constants import AuthDep
from ..operations.ahrefs_parity_chart import operation_ahrefs_full_automation
from ..operations.surfer_parity_chart import (
    operation_surfer_parity_audit,
    operation_surfer_production_gate,
    operation_surfer_provider_probes,
    operation_surfer_setup_playbook,
    operation_surfer_wiring_plan,
)
from ..operations.surfer_vendor_inventory import (
    operation_surfer_provider_bootstrap,
    operation_surfer_provider_checklist,
)
from ..runtime import SearchRuntime
from ..schemas import (
    AhrefsFullAutomationRequest,
    SurferProductionGateRequest,
    SurferProviderBootstrapRequest,
    SurferProviderProbeRequest,
)
from .keyword_unavailable_response import KEYWORD_RESEARCH_501_RESPONSE


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/ahrefs/full-automation", status_code=501, response_model=None, responses={501: KEYWORD_RESEARCH_501_RESPONSE})
    def ahrefs_full_automation(payload: AhrefsFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_ahrefs_full_automation(runtime, payload, auth)

    @router.get("/surfer/parity-audit")
    def surfer_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_surfer_parity_audit(runtime, auth)

    @router.get("/surfer/provider-checklist")
    def surfer_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_surfer_provider_checklist(runtime, auth)

    @router.get("/surfer/wiring-plan")
    def surfer_wiring_plan(auth: AuthDep) -> dict[str, Any]:
        return operation_surfer_wiring_plan(runtime, auth)

    @router.get("/surfer/setup-playbook")
    def surfer_setup_playbook(auth: AuthDep) -> dict[str, Any]:
        return operation_surfer_setup_playbook(runtime, auth)

    @router.post("/surfer/production-gate", status_code=501, response_model=None, responses={501: KEYWORD_RESEARCH_501_RESPONSE})
    def surfer_production_gate(payload: SurferProductionGateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_surfer_production_gate(runtime, payload, auth)

    @router.post("/surfer/provider-bootstrap")
    def surfer_provider_bootstrap(payload: SurferProviderBootstrapRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_surfer_provider_bootstrap(runtime, payload, auth)

    @router.post("/surfer/provider-probes")
    def surfer_provider_probes(payload: SurferProviderProbeRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_surfer_provider_probes(runtime, payload, auth)
