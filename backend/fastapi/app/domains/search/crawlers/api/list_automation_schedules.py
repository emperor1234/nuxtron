"""Search/Crawlers HTTP adapters beginning with list automation schedules."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.cloudflare_sync import execute_delete_automation_schedule
from ..operations.deploy_snippets_bulk import execute_list_automation_schedules
from ..operations.deploy_snippets_bulk import execute_run_automation
from ..operations.execute_automation_run import execute_execute_automation_schedules
from ..operations.execute_automation_run import execute_list_automation_history
from ..operations.execute_automation_run import execute_update_automation_schedule
from ..runtime import ContextRuntime
from ..schemas import AutomationRunRequest
from ..schemas import AutomationScheduleUpdateRequest
from ..schemas import AutomationSchedulesExecuteRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/automation/schedules")
    def list_automation_schedules(auth: AuthDep) -> dict[str, Any]:
        return execute_list_automation_schedules(runtime, auth)

    @router.patch("/automation/schedules/{schedule_id}")
    def update_automation_schedule(
        schedule_id: str, payload: AutomationScheduleUpdateRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_update_automation_schedule(runtime, schedule_id, payload, auth)

    @router.delete("/automation/schedules/{schedule_id}")
    def delete_automation_schedule(schedule_id: str, auth: AuthDep) -> dict[str, Any]:
        return execute_delete_automation_schedule(runtime, schedule_id, auth)

    @router.post("/automation/schedules/execute")
    def execute_automation_schedules(payload: AutomationSchedulesExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_execute_automation_schedules(runtime, payload, auth)

    @router.get("/automation/history")
    def list_automation_history(
        auth: AuthDep, site_id: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=500)
    ) -> dict[str, Any]:
        return execute_list_automation_history(runtime, auth, site_id, limit)

    @router.post("/automation/run")
    def run_automation(payload: AutomationRunRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_run_automation(runtime, payload, auth)
