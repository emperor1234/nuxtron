"""Assistant HTTP adapters beginning with ira copilot env template."""

from ..constants import AuthDep
from ..operations.ira_copilot_plan import execute_ira_agent_frameworks
from ..operations.ira_copilot_plan import execute_ira_copilot_plan
from ..operations.ira_copilot_plan import execute_ira_ml_overview
from ..operations.ira_copilot_plan import execute_ira_short_term_memory
from ..operations.ira_copilot_plan import execute_ira_structured_memory_list
from ..operations.ira_copilot_plan import execute_ira_structured_memory_upsert
from ..operations.ira_response import execute_ira_memory_overview
from ..operations.ira_status import execute_ira_copilot_env_template
from ..runtime import ContextRuntime
from ..schemas import IRACopilotPlanRequest
from ..schemas import IRAStructuredMemoryUpsertRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, context_runtime: ContextRuntime):

    @router.get("/copilot/env-template")
    def ira_copilot_env_template(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_copilot_env_template(context_runtime, auth)

    @router.post("/copilot/plan")
    def ira_copilot_plan(payload: IRACopilotPlanRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_copilot_plan(context_runtime, payload, auth)

    @router.get("/ml/overview")
    def ira_ml_overview(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_ml_overview(context_runtime, auth)

    @router.get("/memory/overview")
    def ira_memory_overview(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_memory_overview(context_runtime, auth)

    @router.get("/memory/short-term")
    def ira_short_term_memory(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_short_term_memory(context_runtime, auth)

    @router.get("/memory/structured")
    def ira_structured_memory_list(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_structured_memory_list(context_runtime, auth)

    @router.post("/memory/structured/upsert")
    def ira_structured_memory_upsert(payload: IRAStructuredMemoryUpsertRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_structured_memory_upsert(context_runtime, payload, auth)

    @router.get("/agent/frameworks")
    def ira_agent_frameworks(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_agent_frameworks(context_runtime, auth)
