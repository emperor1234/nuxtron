"""Intelligence/Platform HTTP adapters beginning with get agent config."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.get_job import execute_get_agent_config
from ..operations.get_job import execute_register_agent_tool
from ..operations.get_job import execute_update_agent_config
from ..operations.list_agent_tools import execute_get_agent_audit
from ..operations.list_agent_tools import execute_list_agent_tools
from ..runtime import ContextRuntime
from ..schemas import AgentConfigUpdateRequest
from ..schemas import AgentToolRegisterRequest
from fastapi import APIRouter
from fastapi import Query


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/agent-config", summary="Kodee-class agent — stack configuration & health for this tenant")
    async def get_agent_config(auth: AuthDep):
        return await execute_get_agent_config(auth)

    @router.put("/agent-config", summary="Update agent configuration for this tenant")
    async def update_agent_config(req: AgentConfigUpdateRequest, auth: AuthDep):
        return await execute_update_agent_config(req, auth)

    @router.get("/agent-tools", summary="List registered tools in the agent tool registry")
    async def list_agent_tools(
        auth: AuthDep,
        group: str | None = Query(default=None, description="Filter by group_name"),
        risk_level: str | None = Query(default=None, description="Filter by risk_level: low | medium | high"),
        active_only: bool = Query(default=True),
    ):
        return await execute_list_agent_tools(auth, group, risk_level, active_only)

    @router.post("/agent-tools", summary="Register a new tool in the agent tool registry", status_code=201)
    async def register_agent_tool(req: AgentToolRegisterRequest, auth: AuthDep):
        return await execute_register_agent_tool(req, auth)

    @router.get("/agent-audit", summary="Audit trail of all agent tool calls for this tenant")
    async def get_agent_audit(
        auth: AuthDep,
        limit: int = Query(default=50, ge=1, le=500),
        tool_key: str | None = Query(default=None),
        status: str | None = Query(default=None),
    ):
        return await execute_get_agent_audit(auth, limit, tool_key, status)
