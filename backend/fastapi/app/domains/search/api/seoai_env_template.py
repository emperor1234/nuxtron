"""Search HTTP operations beginning with seoai env template."""

from ..constants import AuthDep
from ..operations.seoai_list_runs import operation_seoai_assist_chat
from ..operations.seoai_list_runs import operation_seoai_completion_chart
from ..operations.seoai_list_runs import operation_seoai_env_template
from ..operations.seoai_list_runs import operation_seoai_production_gate
from ..operations.seoai_list_runs import operation_seoai_remediation_bundle
from ..operations.seoai_list_runs import operation_seoai_remediation_bundle_export
from ..operations.seoai_list_runs import operation_seoai_verification_report
from ..operations.seoai_list_runs import operation_seoai_wiring_apply
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbRemediationBundleRequest
from ..schemas import SliceAssistRequest
from ..schemas import SliceWiringApplyRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/seoai/env-template")
    def seoai_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_env_template(runtime, payload, auth)

    @router.post("/seoai/remediation-bundle")
    def seoai_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_remediation_bundle(runtime, payload, auth)

    @router.get("/seoai/remediation-bundle/export")
    def seoai_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=10, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_seoai_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )

    @router.post("/seoai/assist/chat")
    def seoai_assist_chat(payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_assist_chat(runtime, payload, auth)

    @router.post("/seoai/wiring/apply")
    def seoai_wiring_apply(payload: SliceWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_wiring_apply(runtime, payload, auth)

    @router.get("/seoai/completion-chart")
    def seoai_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_completion_chart(runtime, auth)

    @router.get("/seoai/production-gate")
    def seoai_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_production_gate(runtime, auth)

    @router.get("/seoai/verification-report")
    def seoai_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_verification_report(runtime, auth)
