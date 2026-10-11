"""Search HTTP operations beginning with semrush full automation."""

from ..constants import AuthDep
from ..operations.ahrefs_parity_chart import operation_ahrefs_e2e_verification
from ..operations.ahrefs_parity_chart import operation_ahrefs_env_template
from ..operations.ahrefs_parity_chart import operation_ahrefs_parity_audit
from ..operations.ahrefs_parity_chart import operation_ahrefs_production_gate
from ..operations.ahrefs_parity_chart import operation_ahrefs_provider_probes
from ..operations.ahrefs_provider_probe_payload import operation_ahrefs_provider_bootstrap
from ..operations.ahrefs_provider_probe_payload import operation_ahrefs_provider_checklist
from ..operations.semrush_list_projects import operation_semrush_full_automation
from ..runtime import SearchRuntime
from ..schemas import AhrefsEnvTemplateRequest
from ..schemas import AhrefsProductionGateRequest
from ..schemas import AhrefsProviderBootstrapRequest
from ..schemas import AhrefsProviderProbeRequest
from ..schemas import SemrushFullAutomationRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/semrush/full-automation")
    def semrush_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_semrush_full_automation(runtime, payload, auth)

    @router.get("/ahrefs/parity-audit")
    def ahrefs_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_ahrefs_parity_audit(runtime, auth)

    @router.get("/ahrefs/e2e-verification")
    def ahrefs_e2e_verification(auth: AuthDep) -> dict[str, Any]:
        return operation_ahrefs_e2e_verification(runtime, auth)

    @router.get("/ahrefs/provider-checklist")
    def ahrefs_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_ahrefs_provider_checklist(runtime, auth)

    @router.post("/ahrefs/production-gate")
    def ahrefs_production_gate(payload: AhrefsProductionGateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_ahrefs_production_gate(runtime, payload, auth)

    @router.post("/ahrefs/provider-bootstrap")
    def ahrefs_provider_bootstrap(payload: AhrefsProviderBootstrapRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_ahrefs_provider_bootstrap(runtime, payload, auth)

    @router.post("/ahrefs/provider-probes")
    def ahrefs_provider_probes(payload: AhrefsProviderProbeRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_ahrefs_provider_probes(runtime, payload, auth)

    @router.post("/ahrefs/env-template")
    def ahrefs_env_template(payload: AhrefsEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_ahrefs_env_template(runtime, payload, auth)
