"""Search HTTP operations beginning with marketmuse remediation bundle."""

from ..constants import AuthDep
from ..operations.marketmuse_product_catalog import operation_marketmuse_remediation_bundle
from ..operations.marketmuse_product_catalog import operation_marketmuse_remediation_bundle_export
from ..operations.marketmuse_product_catalog import operation_marketmuse_verification_report
from ..operations.marketmuse_vendor_inventory import operation_marketmuse_assist_chat
from ..operations.sitebulb_completion_chart import operation_sitebulb_completion_chart
from ..operations.sitebulb_completion_chart import operation_sitebulb_production_gate
from ..operations.sitebulb_remediation_bundle_export import operation_sitebulb_remediation_bundle
from ..operations.sitebulb_remediation_bundle_export import operation_sitebulb_remediation_bundle_export
from ..runtime import SearchRuntime
from ..schemas import SitebulbRemediationBundleRequest
from ..schemas import SliceAssistRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/marketmuse/remediation-bundle")
    def marketmuse_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_remediation_bundle(runtime, payload, auth)

    @router.get("/marketmuse/remediation-bundle/export")
    def marketmuse_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=12, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_marketmuse_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )

    @router.post("/marketmuse/assist/chat")
    def marketmuse_assist_chat(payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_assist_chat(runtime, payload, auth)

    @router.get("/marketmuse/verification-report")
    def marketmuse_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_verification_report(runtime, auth)

    @router.get("/sitebulb/completion-chart")
    def sitebulb_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_completion_chart(runtime, auth)

    @router.get("/sitebulb/production-gate")
    def sitebulb_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_production_gate(runtime, auth)

    @router.post("/sitebulb/remediation-bundle")
    def sitebulb_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_sitebulb_remediation_bundle(runtime, payload, auth)

    @router.get("/sitebulb/remediation-bundle/export")
    def sitebulb_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=10, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_sitebulb_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )
