"""Search HTTP operations beginning with airanklab wiring required keys."""

from typing import Any

from fastapi import APIRouter

from ..constants import AuthDep
from ..operations.platform_airanklab_completion_chart import operation_airanklab_wiring_apply
from ..operations.platform_run_provider_probes import operation_airanklab_wiring_required_keys
from ..operations.semrush_list_projects import (
    operation_semrush_env_template,
    operation_semrush_parity_audit,
    operation_semrush_provider_bootstrap,
    operation_semrush_provider_checklist,
    operation_semrush_provider_probes,
)
from ..operations.semrush_production_gate import operation_semrush_production_gate
from ..runtime import SearchRuntime
from ..schemas import (
    AiranklabWiringApplyRequest,
    SemrushEnvTemplateRequest,
    SemrushProductionGateRequest,
    SemrushProviderBootstrapRequest,
    SemrushProviderProbeRequest,
)
from .keyword_unavailable_response import KEYWORD_RESEARCH_501_RESPONSE


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/airanklab/wiring/required-keys")
    def airanklab_wiring_required_keys(auth: AuthDep) -> dict[str, Any]:
        return operation_airanklab_wiring_required_keys(runtime, auth)

    @router.post("/airanklab/wiring/apply")
    def airanklab_wiring_apply(payload: AiranklabWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_airanklab_wiring_apply(runtime, payload, auth)

    @router.get("/semrush/parity-audit")
    def semrush_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_parity_audit(runtime, auth)

    @router.get("/semrush/provider-checklist")
    def semrush_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_provider_checklist(runtime, auth)

    @router.post("/semrush/production-gate", status_code=501, response_model=None, responses={501: KEYWORD_RESEARCH_501_RESPONSE})
    def semrush_production_gate(payload: SemrushProductionGateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_production_gate(runtime, payload, auth)

    @router.post("/semrush/provider-bootstrap")
    def semrush_provider_bootstrap(payload: SemrushProviderBootstrapRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_provider_bootstrap(runtime, payload, auth)

    @router.post("/semrush/provider-probes")
    def semrush_provider_probes(payload: SemrushProviderProbeRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_provider_probes(runtime, payload, auth)

    @router.post("/semrush/env-template")
    def semrush_env_template(payload: SemrushEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_env_template(runtime, payload, auth)
