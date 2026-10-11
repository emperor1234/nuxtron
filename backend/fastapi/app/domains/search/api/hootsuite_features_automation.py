"""Search HTTP operations beginning with hootsuite features automation."""

from ..constants import AuthDep
from ..operations.hootsuite_features import operation_hootsuite_features_automation
from ..operations.hootsuite_features import operation_hootsuite_parity_audit
from ..operations.hootsuite_features import operation_hootsuite_products_completion_chart
from ..operations.hootsuite_features import operation_hootsuite_products_production_gate
from ..operations.hootsuite_features import operation_hootsuite_products_verification_report
from ..operations.hootsuite_product_catalog import operation_hootsuite_product_detail
from ..operations.hootsuite_product_catalog import operation_hootsuite_product_run
from ..operations.hootsuite_product_catalog import operation_hootsuite_products
from ..runtime import SearchRuntime
from ..schemas import HootsuiteFeatureAutomationRequest
from ..schemas import HootsuiteProductRunRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/hootsuite/features/automation")
    def hootsuite_features_automation(payload: HootsuiteFeatureAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_features_automation(runtime, payload, auth)

    @router.get("/hootsuite/products")
    def hootsuite_products(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_products(runtime, auth)

    @router.get("/hootsuite/products/detail/{product_key}")
    def hootsuite_product_detail(product_key: str, auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_product_detail(runtime, product_key, auth)

    @router.post("/hootsuite/products/{product_key}/run")
    def hootsuite_product_run(product_key: str, payload: HootsuiteProductRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_product_run(runtime, product_key, payload, auth)

    @router.get("/hootsuite/products/completion-chart")
    def hootsuite_products_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_products_completion_chart(runtime, auth)

    @router.get("/hootsuite/products/production-gate")
    def hootsuite_products_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_products_production_gate(runtime, auth)

    @router.get("/hootsuite/products/verification-report")
    def hootsuite_products_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_products_verification_report(runtime, auth)

    @router.get("/hootsuite/parity-audit")
    def hootsuite_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_hootsuite_parity_audit(runtime, auth)
