"""Search HTTP operations beginning with cost savings calculator."""

from ..constants import AuthDep
from ..operations.platform_airanklab_completion_chart import operation_airanklab_completion_chart
from ..operations.platform_airanklab_completion_chart import operation_airanklab_verification_report
from ..operations.platform_run_provider_probes import operation_readiness
from ..operations.platform_run_provider_probes import operation_vendors
from ..operations.platform_search_vendors import operation_ai_search_impact_calculator
from ..operations.platform_search_vendors import operation_cost_savings_calculator
from ..operations.platform_strict_live_probe import operation_vendors_report
from ..operations.platform_strict_live_probe import operation_vendors_report_export
from ..runtime import SearchRuntime
from ..schemas import AiSearchRevenueImpactRequest
from ..schemas import CostSavingsCalculatorRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/cost-savings-calculator")
    def cost_savings_calculator(payload: CostSavingsCalculatorRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_cost_savings_calculator(runtime, payload, auth)

    @router.post("/ai-search-impact-calculator")
    def ai_search_impact_calculator(payload: AiSearchRevenueImpactRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_ai_search_impact_calculator(runtime, payload, auth)

    @router.get("/vendors")
    def vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_vendors(runtime, auth)

    @router.get("/vendors/report")
    def vendors_report(auth: AuthDep, format: Annotated[str, Query(pattern="^(json|csv)$")] = "json") -> dict[str, Any]:
        return operation_vendors_report(runtime, auth, format)

    @router.get("/vendors/report/export")
    def vendors_report_export(
        auth: AuthDep, format: Annotated[str, Query(pattern="^(json|csv)$")] = "json"
    ) -> dict[str, Any]:
        return operation_vendors_report_export(runtime, auth, format)

    @router.get("/readiness")
    def readiness(auth: AuthDep) -> dict[str, Any]:
        return operation_readiness(runtime, auth)

    @router.get("/airanklab/completion-chart")
    def airanklab_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_airanklab_completion_chart(runtime, auth)

    @router.get("/airanklab/verification-report")
    def airanklab_verification_report(auth: AuthDep) -> dict[str, Any]:
        return operation_airanklab_verification_report(runtime, auth)
