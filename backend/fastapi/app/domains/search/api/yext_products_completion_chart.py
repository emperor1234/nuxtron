"""Search HTTP operations beginning with yext products completion chart."""

from ..constants import AuthDep
from ..operations.yext_product_catalog import operation_yext_products_completion_chart
from ..operations.yext_product_catalog import operation_yext_products_production_gate
from ..operations.yext_product_catalog import operation_yext_products_verification_report
from ..operations.yext_product_catalog import operation_yext_provider_checklist
from ..operations.yext_vendor_inventory import operation_yext_full_automation
from ..operations.yext_vendor_inventory import operation_yext_parity_audit
from ..operations.yext_vendor_inventory import operation_yext_wiring_apply
from ..operations.yext_vendor_inventory import operation_yext_wiring_state
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SliceWiringApplyRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/yext/products/completion-chart")
    def yext_products_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_products_completion_chart(runtime, auth)

    @router.get("/yext/products/production-gate")
    def yext_products_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_products_production_gate(runtime, auth)

    @router.get("/yext/products/verification-report")
    def yext_products_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_products_verification_report(runtime, auth)

    @router.get("/yext/parity-audit")
    def yext_parity_audit(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_parity_audit(runtime, auth)

    @router.get("/yext/provider-checklist")
    def yext_provider_checklist(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_provider_checklist(runtime, auth)

    @router.get("/yext/wiring")
    def yext_wiring_state(auth: AuthDep) -> dict[str, Any]:
        return operation_yext_wiring_state(runtime, auth)

    @router.post("/yext/wiring/apply")
    def yext_wiring_apply(payload: SliceWiringApplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_yext_wiring_apply(runtime, payload, auth)

    @router.post("/yext/full-automation")
    def yext_full_automation(payload: SemrushFullAutomationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_yext_full_automation(runtime, payload, auth)
