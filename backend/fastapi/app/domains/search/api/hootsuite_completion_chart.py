"""Search HTTP operations beginning with hootsuite completion chart."""

from ..constants import AuthDep
from ..operations.hootsuite_features import operation_hootsuite_completion_chart
from ..operations.hootsuite_features import operation_hootsuite_production_gate
from ..operations.hootsuite_features import operation_hootsuite_verification_report
from ..operations.hootsuite_product_catalog import operation_hootsuite_remediation_bundle
from ..operations.hootsuite_product_catalog import operation_hootsuite_remediation_bundle_export
from ..operations.yext_product_catalog import operation_yext_product_detail
from ..operations.yext_product_catalog import operation_yext_product_run
from ..operations.yext_product_catalog import operation_yext_products
from ..runtime import SearchRuntime
from ..schemas import HootsuiteProductRunRequest
from ..schemas import SitebulbRemediationBundleRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/hootsuite/completion-chart")
    def hootsuite_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_completion_chart(runtime, auth)

    @router.get("/hootsuite/production-gate")
    def hootsuite_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_production_gate(runtime, auth)

    @router.post("/hootsuite/remediation-bundle")
    def hootsuite_remediation_bundle(payload: SitebulbRemediationBundleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_remediation_bundle(runtime, payload, auth)

    @router.get("/hootsuite/remediation-bundle/export")
    def hootsuite_remediation_bundle_export(
        auth: AuthDep,
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
        top_steps: int = Query(default=12, ge=1, le=100),
        include_optional: bool = Query(default=False),
        include_configured: bool = Query(default=False),
    ) -> dict[str, Any]:
        return operation_hootsuite_remediation_bundle_export(
            runtime, auth, format, top_steps, include_optional, include_configured
        )

    @router.get("/hootsuite/verification-report")
    def hootsuite_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_verification_report(runtime, auth)

    @router.get("/yext/products")
    def yext_products(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_products(runtime, auth)

    @router.get("/yext/products/detail/{product_key}")
    def yext_product_detail(product_key: str, auth: AuthDep) -> dict[str, Any]:
        return operation_yext_product_detail(runtime, product_key, auth)

    @router.post("/yext/products/{product_key}/run")
    def yext_product_run(product_key: str, payload: HootsuiteProductRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_yext_product_run(runtime, product_key, payload, auth)
