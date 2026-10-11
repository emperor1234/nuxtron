"""Search HTTP operations beginning with yext assist chat."""

from ..constants import AuthDep
from ..operations.brightedge_product_catalog import operation_brightedge_product_detail
from ..operations.brightedge_product_catalog import operation_brightedge_product_run
from ..operations.brightedge_product_catalog import operation_brightedge_products
from ..operations.brightedge_product_catalog import operation_brightedge_products_completion_chart
from ..operations.brightedge_product_catalog import operation_brightedge_products_production_gate
from ..operations.brightedge_product_catalog import operation_brightedge_products_verification_report
from ..operations.yext_product_catalog import operation_yext_verification_report
from ..operations.yext_vendor_inventory import operation_yext_assist_chat
from ..runtime import SearchRuntime
from ..schemas import HootsuiteProductRunRequest
from ..schemas import SliceAssistRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/yext/assist/chat")
    def yext_assist_chat(payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_yext_assist_chat(runtime, payload, auth)

    @router.get("/yext/verification-report")
    def yext_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_verification_report(runtime, auth)

    @router.get("/brightedge/products")
    def brightedge_products(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_products(runtime, auth)

    @router.get("/brightedge/products/detail/{product_key}")
    def brightedge_product_detail(product_key: str, auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_product_detail(runtime, product_key, auth)

    @router.post("/brightedge/products/{product_key}/run")
    def brightedge_product_run(product_key: str, payload: HootsuiteProductRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_product_run(runtime, product_key, payload, auth)

    @router.get("/brightedge/products/completion-chart")
    def brightedge_products_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_products_completion_chart(runtime, auth)

    @router.get("/brightedge/products/production-gate")
    def brightedge_products_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_products_production_gate(runtime, auth)

    @router.get("/brightedge/products/verification-report")
    def brightedge_products_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_brightedge_products_verification_report(runtime, auth)
