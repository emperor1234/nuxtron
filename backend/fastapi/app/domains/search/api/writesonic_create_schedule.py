"""Search HTTP operations beginning with writesonic create schedule."""

from ..constants import AuthDep
from ..operations.writesonic_product_catalog import operation_writesonic_execute_schedules
from ..operations.writesonic_product_catalog import operation_writesonic_gate_progress
from ..operations.writesonic_products_completion_chart import operation_writesonic_completion_chart
from ..operations.writesonic_products_completion_chart import operation_writesonic_create_schedule
from ..operations.writesonic_products_completion_chart import operation_writesonic_env_template
from ..operations.writesonic_products_completion_chart import operation_writesonic_list_schedules
from ..operations.writesonic_products_completion_chart import operation_writesonic_preflight
from ..operations.writesonic_products_completion_chart import operation_writesonic_vendors
from ..runtime import SearchRuntime
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbScheduleCreateRequest
from ..schemas import SitebulbScheduleExecuteRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: SearchRuntime):

    @router.post("/writesonic/schedules")
    def writesonic_create_schedule(payload: SitebulbScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_create_schedule(runtime, payload, auth)

    @router.get("/writesonic/schedules")
    def writesonic_list_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_list_schedules(runtime, auth)

    @router.post("/writesonic/schedules/execute")
    def writesonic_execute_schedules(payload: SitebulbScheduleExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_execute_schedules(runtime, payload, auth)

    @router.get("/writesonic/vendors")
    def writesonic_vendors(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_vendors(runtime, auth)

    @router.get("/writesonic/preflight")
    def writesonic_preflight(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_preflight(runtime, auth)

    @router.get("/writesonic/gate-progress")
    def writesonic_gate_progress(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_gate_progress(runtime, auth)

    @router.post("/writesonic/env-template")
    def writesonic_env_template(payload: SitebulbEnvTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_env_template(runtime, payload, auth)

    @router.get("/writesonic/completion-chart")
    def writesonic_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return operation_writesonic_completion_chart(runtime, auth)
