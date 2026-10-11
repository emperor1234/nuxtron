"""Search HTTP operations beginning with marketmuse list schedules."""

from ..constants import AuthDep
from ..operations.marketmuse_product_catalog import operation_marketmuse_completion_chart
from ..operations.marketmuse_product_catalog import operation_marketmuse_execute_schedules
from ..operations.marketmuse_product_catalog import operation_marketmuse_gate_progress
from ..operations.marketmuse_product_catalog import operation_marketmuse_list_schedules
from ..operations.marketmuse_product_catalog import operation_marketmuse_preflight
from ..operations.marketmuse_product_catalog import operation_marketmuse_production_gate
from ..operations.marketmuse_vendor_inventory import operation_marketmuse_env_template
from ..operations.marketmuse_vendor_inventory import operation_marketmuse_vendors
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbScheduleExecuteRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.get("/marketmuse/schedules")
    def marketmuse_list_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_list_schedules(runtime, auth)

    @router.post("/marketmuse/schedules/execute")
    def marketmuse_execute_schedules(payload: SitebulbScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_execute_schedules(runtime, payload, auth)

    @router.get("/marketmuse/vendors")
    def marketmuse_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_vendors(runtime, auth)

    @router.get("/marketmuse/preflight")
    def marketmuse_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_preflight(runtime, auth)

    @router.get("/marketmuse/gate-progress")
    def marketmuse_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_gate_progress(runtime, auth)

    @router.post("/marketmuse/env-template")
    def marketmuse_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_env_template(runtime, payload, auth)

    @router.get("/marketmuse/completion-chart")
    def marketmuse_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_completion_chart(runtime, auth)

    @router.get("/marketmuse/production-gate")
    def marketmuse_production_gate(auth: AuthDep) -> dict[str, Any]:
        return operation_marketmuse_production_gate(runtime, auth)
