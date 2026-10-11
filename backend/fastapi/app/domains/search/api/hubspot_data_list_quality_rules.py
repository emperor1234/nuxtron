"""Search HTTP operations beginning with hubspot data list quality rules."""

from ..constants import AuthDep
from ..operations.hubspot_route_coverage_chart import operation_hubspot_data_list_quality_rules
from ..operations.hubspot_route_coverage_chart import operation_hubspot_parity_audit
from ..operations.hubspot_route_coverage_chart import operation_hubspot_product_detail
from ..operations.hubspot_route_coverage_chart import operation_hubspot_product_run
from ..operations.hubspot_route_coverage_chart import operation_hubspot_products
from ..operations.hubspot_wiring_required_keys import operation_hubspot_products_completion_chart
from ..operations.hubspot_wiring_required_keys import operation_hubspot_products_production_gate
from ..operations.hubspot_wiring_required_keys import operation_hubspot_products_verification_report
from ..runtime import SearchRuntime
from ..schemas import HubspotProductRunRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/hubspot/data/quality-rules")
    def hubspot_data_list_quality_rules(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_data_list_quality_rules(runtime, auth)

    @router.get("/hubspot/products")
    def hubspot_products(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_products(runtime, auth)

    @router.get("/hubspot/products/detail/{product_key}")
    def hubspot_product_detail(product_key: str, auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_product_detail(runtime, product_key, auth)

    @router.post("/hubspot/products/{product_key}/run")
    def hubspot_product_run(product_key: str, payload: HubspotProductRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_product_run(runtime, product_key, payload, auth)

    @router.get("/hubspot/products/completion-chart")
    def hubspot_products_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_products_completion_chart(runtime, auth)

    @router.get("/hubspot/products/production-gate")
    def hubspot_products_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_products_production_gate(runtime, auth)

    @router.get("/hubspot/products/verification-report")
    def hubspot_products_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_products_verification_report(runtime, auth)

    @router.get("/hubspot/parity-audit")
    def hubspot_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_hubspot_parity_audit(runtime, auth)
