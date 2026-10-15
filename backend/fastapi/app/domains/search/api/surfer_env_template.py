"""Search HTTP operations beginning with surfer env template."""

from typing import Any

from fastapi import APIRouter

from ..constants import AuthDep
from ..operations.frase_provider_checklist import (
    operation_frase_parity_audit,
    operation_frase_production_gate,
    operation_frase_provider_bootstrap,
    operation_frase_provider_checklist,
    operation_frase_setup_playbook,
    operation_frase_wiring_plan,
)
from ..operations.surfer_parity_chart import operation_surfer_env_template, operation_surfer_full_automation
from ..runtime import SearchRuntime
from ..schemas import (
    FraseProductionGateRequest,
    FraseProviderBootstrapRequest,
    SurferEnvTemplateRequest,
    SurferFullAutomationRequest,
)
from .keyword_unavailable_response import KEYWORD_RESEARCH_501_RESPONSE


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/surfer/env-template")
    def surfer_env_template(payload: SurferEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_surfer_env_template(runtime, payload, auth)

    @router.post("/surfer/full-automation", status_code=501, response_model=None, responses={501: KEYWORD_RESEARCH_501_RESPONSE})
    def surfer_full_automation(payload: SurferFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_surfer_full_automation(runtime, payload, auth)

    @router.get("/frase/parity-audit")
    def frase_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_frase_parity_audit(runtime, auth)

    @router.get("/frase/provider-checklist")
    def frase_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_frase_provider_checklist(runtime, auth)

    @router.get("/frase/wiring-plan")
    def frase_wiring_plan(auth: AuthDep) -> dict[str, Any]:
        return operation_frase_wiring_plan(runtime, auth)

    @router.get("/frase/setup-playbook")
    def frase_setup_playbook(auth: AuthDep) -> dict[str, Any]:
        return operation_frase_setup_playbook(runtime, auth)

    @router.post("/frase/production-gate", status_code=501, response_model=None, responses={501: KEYWORD_RESEARCH_501_RESPONSE})
    def frase_production_gate(payload: FraseProductionGateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_frase_production_gate(runtime, payload, auth)

    @router.post("/frase/provider-bootstrap")
    def frase_provider_bootstrap(payload: FraseProviderBootstrapRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_frase_provider_bootstrap(runtime, payload, auth)
