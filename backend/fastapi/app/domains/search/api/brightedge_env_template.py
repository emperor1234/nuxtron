"""Search HTTP operations beginning with brightedge env template."""

from ..constants import AuthDep
from ..operations.brightedge_product_catalog import operation_brightedge_completion_chart
from ..operations.brightedge_product_catalog import operation_brightedge_production_gate
from ..operations.brightedge_product_catalog import operation_brightedge_remediation_bundle
from ..operations.brightedge_product_catalog import operation_brightedge_remediation_bundle_export
from ..operations.brightedge_product_catalog import operation_brightedge_verification_report
from ..operations.brightedge_vendor_inventory import operation_brightedge_assist_chat
from ..operations.brightedge_vendor_inventory import operation_brightedge_env_template
from ..operations.writesonic_product_catalog import operation_writesonic_products
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbRemediationBundleRequest
from ..schemas import SliceAssistRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/brightedge/env-template")
    def brightedge_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_env_template(runtime, payload, auth)

    @router.get("/brightedge/completion-chart")
    def brightedge_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_completion_chart(runtime, auth)

    @router.get("/brightedge/production-gate")
    def brightedge_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_production_gate(runtime, auth)

    @router.post("/brightedge/remediation-bundle")
    def brightedge_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_remediation_bundle(runtime, payload, auth)

    @router.get("/brightedge/remediation-bundle/export")
    def brightedge_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=12, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_brightedge_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )

    @router.post("/brightedge/assist/chat")
    def brightedge_assist_chat(payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_assist_chat(runtime, payload, auth)

    @router.get("/brightedge/verification-report")
    def brightedge_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_verification_report(runtime, auth)

    @router.get("/writesonic/products")
    def writesonic_products(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_products(runtime, auth)
