"""Automation/Workforce HTTP adapters beginning with list missions."""

from __future__ import annotations
from ..constants import AuthDep
from ..capabilities import WORKFORCE_EXECUTION_UNAVAILABLE_RESPONSES
from ..operations.list_capabilities import execute_approve_mission
from ..operations.list_capabilities import execute_list_missions
from ..operations.list_capabilities import execute_list_schedules
from ..operations.list_capabilities import execute_live_feed
from ..operations.reject_mission import execute_add_knowledge
from ..operations.reject_mission import execute_create_schedule
from ..operations.reject_mission import execute_reject_mission
from ..operations.reject_mission import execute_run_due_schedules
from ..runtime import ContextRuntime
from ..schemas import KnowledgeDocRequest
from ..schemas import MissionDecisionRequest
from ..schemas import ScheduleRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/missions")
    def list_missions(
        auth: AuthDep, status: Annotated[str | None, Query()] = None, limit: Annotated[int, Query(ge=1, le=1000)] = 100
    ) -> dict[str, Any]:
        return execute_list_missions(runtime, auth, status, limit)

    @router.post(
        "/missions/{mission_id}/approve",
        responses={**WORKFORCE_EXECUTION_UNAVAILABLE_RESPONSES, 404: {"description": "Mission not found."}, 409: {"description": "Mission already finalized."}},
    )
    async def approve_mission(mission_id: str, payload: MissionDecisionRequest, auth: AuthDep) -> dict[str, Any]:
        return await execute_approve_mission(runtime, mission_id, payload, auth)

    @router.post("/missions/{mission_id}/reject", responses={404: {"description": "Mission not found."}})
    def reject_mission(mission_id: str, payload: MissionDecisionRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_reject_mission(runtime, mission_id, payload, auth)

    @router.get("/feed")
    def live_feed(auth: AuthDep, limit: Annotated[int, Query(ge=1, le=1000)] = 100) -> dict[str, Any]:
        return execute_live_feed(runtime, auth, limit)

    @router.post("/schedules", status_code=201)
    def create_schedule(payload: ScheduleRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_schedule(runtime, payload, auth)

    @router.get("/schedules")
    def list_schedules(auth: AuthDep) -> dict[str, Any]:
        return execute_list_schedules(runtime, auth)

    @router.post("/runner/tick", responses=WORKFORCE_EXECUTION_UNAVAILABLE_RESPONSES)
    async def run_due_schedules(auth: AuthDep, limit: Annotated[int, Query(ge=1, le=200)] = 20) -> dict[str, Any]:
        return await execute_run_due_schedules(runtime, auth, limit)

    @router.post("/knowledge", status_code=201)
    def add_knowledge(payload: KnowledgeDocRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_add_knowledge(runtime, payload, auth)
