"""Search HTTP operations beginning with promptwatch env template."""

from ..constants import AuthDep
from ..operations.marketmuse_product_catalog import operation_marketmuse_products
from ..operations.promptwatch_product_catalog import operation_promptwatch_completion_chart
from ..operations.promptwatch_product_catalog import operation_promptwatch_production_gate
from ..operations.promptwatch_product_catalog import operation_promptwatch_remediation_bundle
from ..operations.promptwatch_product_catalog import operation_promptwatch_remediation_bundle_export
from ..operations.promptwatch_product_catalog import operation_promptwatch_verification_report
from ..operations.promptwatch_vendor_inventory import operation_promptwatch_assist_chat
from ..operations.promptwatch_vendor_inventory import operation_promptwatch_env_template
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbRemediationBundleRequest
from ..schemas import SliceAssistRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/promptwatch/env-template")
    def promptwatch_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_env_template(runtime, payload, auth)

    @router.get("/promptwatch/completion-chart")
    def promptwatch_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_completion_chart(runtime, auth)

    @router.get("/promptwatch/production-gate")
    def promptwatch_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_production_gate(runtime, auth)

    @router.post("/promptwatch/remediation-bundle")
    def promptwatch_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_remediation_bundle(runtime, payload, auth)

    @router.get("/promptwatch/remediation-bundle/export")
    def promptwatch_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=12, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_promptwatch_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )

    @router.post("/promptwatch/assist/chat")
    def promptwatch_assist_chat(payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_assist_chat(runtime, payload, auth)

    @router.get("/promptwatch/verification-report")
    def promptwatch_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_verification_report(runtime, auth)

    @router.get("/marketmuse/products")
    def marketmuse_products(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_products(runtime, auth)
