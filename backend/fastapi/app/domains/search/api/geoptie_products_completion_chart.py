"""Search HTTP operations beginning with geoptie products completion chart."""

from ..constants import AuthDep
from ..operations.geoptie_product_catalog import operation_geoptie_products_completion_chart
from ..operations.geoptie_product_catalog import operation_geoptie_products_production_gate
from ..operations.geoptie_product_catalog import operation_geoptie_products_verification_report
from ..operations.geoptie_product_catalog import operation_geoptie_provider_checklist
from ..operations.geoptie_vendor_inventory import operation_geoptie_full_automation
from ..operations.geoptie_vendor_inventory import operation_geoptie_parity_audit
from ..operations.geoptie_vendor_inventory import operation_geoptie_wiring_apply
from ..operations.geoptie_vendor_inventory import operation_geoptie_wiring_state
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SliceWiringApplyRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/geoptie/products/completion-chart")
    def geoptie_products_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_products_completion_chart(runtime, auth)

    @router.get("/geoptie/products/production-gate")
    def geoptie_products_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_products_production_gate(runtime, auth)

    @router.get("/geoptie/products/verification-report")
    def geoptie_products_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_products_verification_report(runtime, auth)

    @router.get("/geoptie/parity-audit")
    def geoptie_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_parity_audit(runtime, auth)

    @router.get("/geoptie/provider-checklist")
    def geoptie_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_provider_checklist(runtime, auth)

    @router.get("/geoptie/wiring")
    def geoptie_wiring_state(auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_wiring_state(runtime, auth)

    @router.post("/geoptie/wiring/apply")
    def geoptie_wiring_apply(payload: SliceWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_wiring_apply(runtime, payload, auth)

    @router.post("/geoptie/full-automation")
    def geoptie_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_geoptie_full_automation(runtime, payload, auth)
