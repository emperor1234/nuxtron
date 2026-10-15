"""Automation/Workforce HTTP adapters beginning with list knowledge."""

from __future__ import annotations
from ..constants import AuthDep
from ..capabilities import WORKFORCE_EXECUTION_UNAVAILABLE_RESPONSES
from ..operations.reject_mission import execute_list_knowledge
from ..operations.reject_mission import execute_list_outcomes
from ..operations.reject_mission import execute_list_retry_queue
from ..operations.reject_mission import execute_metrics_dashboard
from ..operations.reject_mission import execute_metrics_providers
from ..operations.reject_mission import execute_webhook_trigger
from ..operations.retry_action import execute_enable_tool_calling_for_mission
from ..operations.retry_action import execute_retry_action
from ..runtime import ContextRuntime
from ..schemas import WebhookTriggerRequest
from fastapi import APIRouter
from fastapi import Query
from fastapi import Request
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/knowledge")
    def list_knowledge(
        auth: AuthDep, q: Annotated[str | None, Query()] = None, limit: Annotated[int, Query(ge=1, le=1000)] = 100
    ) -> dict[str, Any]:
        return execute_list_knowledge(runtime, auth, q, limit)

    @router.get("/outcomes")
    def list_outcomes(auth: AuthDep, limit: Annotated[int, Query(ge=1, le=1000)] = 100) -> dict[str, Any]:
        return execute_list_outcomes(runtime, auth, limit)

    @router.post("/webhook/trigger", status_code=202, responses=WORKFORCE_EXECUTION_UNAVAILABLE_RESPONSES)
    async def webhook_trigger(payload: WebhookTriggerRequest, auth: AuthDep, request: Request) -> dict[str, Any]:
        return await execute_webhook_trigger(runtime, payload, auth, request)

    @router.get("/metrics/dashboard")
    def metrics_dashboard(
        auth: AuthDep, time_window_minutes: Annotated[int, Query(ge=5, le=1440)] = 60
    ) -> dict[str, Any]:
        return execute_metrics_dashboard(runtime, auth, time_window_minutes)

    @router.get("/metrics/providers")
    def metrics_providers(
        auth: AuthDep, time_window_minutes: Annotated[int, Query(ge=5, le=1440)] = 60
    ) -> dict[str, Any]:
        return execute_metrics_providers(runtime, auth, time_window_minutes)

    @router.get("/retry-queue")
    def list_retry_queue(
        auth: AuthDep, status: Annotated[str, Query()] = "pending", limit: Annotated[int, Query(ge=1, le=1000)] = 100
    ) -> dict[str, Any]:
        return execute_list_retry_queue(runtime, auth, status, limit)

    @router.post("/retry-queue/{retry_id}/retry", status_code=202)
    async def retry_action(retry_id: str, auth: AuthDep) -> dict[str, Any]:
        return await execute_retry_action(runtime, retry_id, auth)

    @router.post("/missions/{mission_id}/use-tool-calling", status_code=202)
    async def enable_tool_calling_for_mission(mission_id: str, auth: AuthDep) -> dict[str, Any]:
        return await execute_enable_tool_calling_for_mission(runtime, mission_id, auth)
