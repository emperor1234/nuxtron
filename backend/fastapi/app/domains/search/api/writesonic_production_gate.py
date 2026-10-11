"""Search HTTP operations beginning with writesonic production gate."""

from ..constants import AuthDep
from ..operations.geoptie_product_catalog import operation_geoptie_product_detail
from ..operations.geoptie_product_catalog import operation_geoptie_product_run
from ..operations.geoptie_product_catalog import operation_geoptie_products
from ..operations.writesonic_product_catalog import operation_writesonic_remediation_bundle
from ..operations.writesonic_products_completion_chart import operation_writesonic_assist_chat
from ..operations.writesonic_products_completion_chart import operation_writesonic_production_gate
from ..operations.writesonic_products_completion_chart import operation_writesonic_remediation_bundle_export
from ..operations.writesonic_products_completion_chart import operation_writesonic_verification_report
from ..runtime import SearchRuntime
from ..schemas import HootsuiteProductRunRequest
from ..schemas import SitebulbRemediationBundleRequest
from ..schemas import SliceAssistRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/writesonic/production-gate")
    def writesonic_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_production_gate(runtime, auth)

    @router.post("/writesonic/remediation-bundle")
    def writesonic_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_remediation_bundle(runtime, payload, auth)

    @router.get("/writesonic/remediation-bundle/export")
    def writesonic_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=12, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_writesonic_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )

    @router.post("/writesonic/assist/chat")
    def writesonic_assist_chat(payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_assist_chat(runtime, payload, auth)

    @router.get("/writesonic/verification-report")
    def writesonic_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_verification_report(runtime, auth)

    @router.get("/geoptie/products")
    def geoptie_products(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_products(runtime, auth)

    @router.get("/geoptie/products/detail/{product_key}")
    def geoptie_product_detail(product_key: str, auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_product_detail(runtime, product_key, auth)

    @router.post("/geoptie/products/{product_key}/run")
    def geoptie_product_run(product_key: str, payload: HootsuiteProductRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_product_run(runtime, product_key, payload, auth)
