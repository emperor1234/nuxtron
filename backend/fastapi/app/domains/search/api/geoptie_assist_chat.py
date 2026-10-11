"""Search HTTP operations beginning with geoptie assist chat."""

from ..constants import AuthDep
from ..operations.geoptie_product_catalog import operation_geoptie_verification_report
from ..operations.geoptie_vendor_inventory import operation_geoptie_assist_chat
from ..operations.promptwatch_product_catalog import operation_promptwatch_product_detail
from ..operations.promptwatch_product_catalog import operation_promptwatch_product_run
from ..operations.promptwatch_product_catalog import operation_promptwatch_products
from ..operations.promptwatch_product_catalog import operation_promptwatch_products_completion_chart
from ..operations.promptwatch_product_catalog import operation_promptwatch_products_production_gate
from ..operations.promptwatch_product_catalog import operation_promptwatch_products_verification_report
from ..runtime import SearchRuntime
from ..schemas import HootsuiteProductRunRequest
from ..schemas import SliceAssistRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/geoptie/assist/chat")
    def geoptie_assist_chat(payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_assist_chat(runtime, payload, auth)

    @router.get("/geoptie/verification-report")
    def geoptie_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_verification_report(runtime, auth)

    @router.get("/promptwatch/products")
    def promptwatch_products(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_products(runtime, auth)

    @router.get("/promptwatch/products/detail/{product_key}")
    def promptwatch_product_detail(product_key: str, auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_product_detail(runtime, product_key, auth)

    @router.post("/promptwatch/products/{product_key}/run")
    def promptwatch_product_run(product_key: str, payload: HootsuiteProductRunRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_product_run(runtime, product_key, payload, auth)

    @router.get("/promptwatch/products/completion-chart")
    def promptwatch_products_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_products_completion_chart(runtime, auth)

    @router.get("/promptwatch/products/production-gate")
    def promptwatch_products_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_products_production_gate(runtime, auth)

    @router.get("/promptwatch/products/verification-report")
    def promptwatch_products_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_promptwatch_products_verification_report(runtime, auth)
