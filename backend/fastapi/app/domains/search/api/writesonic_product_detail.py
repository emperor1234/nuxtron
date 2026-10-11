"""Search HTTP operations beginning with writesonic product detail."""

from ..constants import AuthDep
from ..operations.writesonic_product_catalog import operation_writesonic_product_detail
from ..operations.writesonic_product_catalog import operation_writesonic_product_run
from ..operations.writesonic_products_completion_chart import operation_writesonic_features
from ..operations.writesonic_products_completion_chart import operation_writesonic_parity_audit
from ..operations.writesonic_products_completion_chart import operation_writesonic_products_completion_chart
from ..operations.writesonic_products_completion_chart import operation_writesonic_products_production_gate
from ..operations.writesonic_products_completion_chart import operation_writesonic_products_verification_report
from ..operations.writesonic_products_completion_chart import operation_writesonic_provider_checklist
from ..runtime import SearchRuntime
from ..schemas import HootsuiteProductRunRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/writesonic/products/detail/{product_key}")
    def writesonic_product_detail(product_key: str, auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_product_detail(runtime, product_key, auth)

    @router.post("/writesonic/products/{product_key}/run")
    def writesonic_product_run(product_key: str, payload: HootsuiteProductRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_product_run(runtime, product_key, payload, auth)

    @router.get("/writesonic/products/completion-chart")
    def writesonic_products_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_products_completion_chart(runtime, auth)

    @router.get("/writesonic/products/production-gate")
    def writesonic_products_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_products_production_gate(runtime, auth)

    @router.get("/writesonic/products/verification-report")
    def writesonic_products_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_products_verification_report(runtime, auth)

    @router.get("/writesonic/parity-audit")
    def writesonic_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_parity_audit(runtime, auth)

    @router.get("/writesonic/features")
    def writesonic_features(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_features(runtime, auth)

    @router.get("/writesonic/provider-checklist")
    def writesonic_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_provider_checklist(runtime, auth)
