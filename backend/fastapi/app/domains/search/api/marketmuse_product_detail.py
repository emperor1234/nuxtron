"""Search HTTP operations beginning with marketmuse product detail."""

from ..constants import AuthDep
from ..operations.marketmuse_product_catalog import operation_marketmuse_product_detail
from ..operations.marketmuse_product_catalog import operation_marketmuse_product_run
from ..operations.marketmuse_product_catalog import operation_marketmuse_products_completion_chart
from ..operations.marketmuse_product_catalog import operation_marketmuse_products_production_gate
from ..operations.marketmuse_product_catalog import operation_marketmuse_products_verification_report
from ..operations.marketmuse_product_catalog import operation_marketmuse_provider_checklist
from ..operations.marketmuse_vendor_inventory import operation_marketmuse_parity_audit
from ..operations.marketmuse_vendor_inventory import operation_marketmuse_wiring_state
from ..runtime import SearchRuntime
from ..schemas import HootsuiteProductRunRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/marketmuse/products/detail/{product_key}")
    def marketmuse_product_detail(product_key: str, auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_product_detail(runtime, product_key, auth)

    @router.post("/marketmuse/products/{product_key}/run")
    def marketmuse_product_run(product_key: str, payload: HootsuiteProductRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_product_run(runtime, product_key, payload, auth)

    @router.get("/marketmuse/products/completion-chart")
    def marketmuse_products_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_products_completion_chart(runtime, auth)

    @router.get("/marketmuse/products/production-gate")
    def marketmuse_products_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_products_production_gate(runtime, auth)

    @router.get("/marketmuse/products/verification-report")
    def marketmuse_products_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_products_verification_report(runtime, auth)

    @router.get("/marketmuse/parity-audit")
    def marketmuse_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_parity_audit(runtime, auth)

    @router.get("/marketmuse/provider-checklist")
    def marketmuse_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_provider_checklist(runtime, auth)

    @router.get("/marketmuse/wiring")
    def marketmuse_wiring_state(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_wiring_state(runtime, auth)
