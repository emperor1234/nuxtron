"""Search HTTP operations beginning with botify env template."""

from ..constants import AuthDep
from ..operations.botify_list_runs import operation_botify_assist_chat
from ..operations.botify_list_runs import operation_botify_completion_chart
from ..operations.botify_list_runs import operation_botify_env_template
from ..operations.botify_list_runs import operation_botify_production_gate
from ..operations.botify_list_runs import operation_botify_remediation_bundle
from ..operations.botify_list_runs import operation_botify_remediation_bundle_export
from ..operations.botify_list_runs import operation_botify_verification_report
from ..operations.seoai_list_runs import operation_seoai_create_project
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbRemediationBundleRequest
from ..schemas import SliceAssistRequest
from ..schemas import SliceProjectCreateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/botify/env-template")
    def botify_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_botify_env_template(runtime, payload, auth)

    @router.post("/botify/remediation-bundle")
    def botify_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_botify_remediation_bundle(runtime, payload, auth)

    @router.get("/botify/remediation-bundle/export")
    def botify_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=10, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_botify_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )

    @router.post("/botify/assist/chat")
    def botify_assist_chat(payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_botify_assist_chat(runtime, payload, auth)

    @router.get("/botify/completion-chart")
    def botify_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_botify_completion_chart(runtime, auth)

    @router.get("/botify/production-gate")
    def botify_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_botify_production_gate(runtime, auth)

    @router.get("/botify/verification-report")
    def botify_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_botify_verification_report(runtime, auth)

    @router.post("/seoai/projects")
    def seoai_create_project(payload: SliceProjectCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_seoai_create_project(runtime, payload, auth)
