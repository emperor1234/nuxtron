"""
Agent Management API Routes.

REST endpoints for:
"""

import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from ..agents.base import AgentExecution, ToolType, initialize_tools, tool_registry
from ..agents.types import AgentType, create_agent
from ..deps import AuthContext, require_auth
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def get_tenant_id() -> str:
    """Placeholder tenant ID extractor"""
    return 'default_tenant'


router = APIRouter(prefix='/api/v1/agents', tags=['Agents'])

AGENT_NOT_FOUND = 'Agent not found'
EXECUTION_NOT_FOUND = 'Execution not found'
MEMORY_STORE_UNAVAILABLE = 'Agent persistence is not configured for production. Configure a durable backend before enabling agents.'


def _is_production() -> bool:
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def _ensure_agent_store_writable() -> None:
    if _is_production():
        raise HTTPException(status_code=503, detail=MEMORY_STORE_UNAVAILABLE)


def _current_tenant_id(auth: AuthContext) -> str:
    return auth.tenant_id


def _execution_response(execution_id: str, execution: AgentExecution) -> 'ExecutionResponse':
    return ExecutionResponse(
        execution_id=execution_id,
        status=execution.status,
        final_output=execution.final_output,
        error=execution.error_message,
        steps_count=len(execution.steps),
        duration_ms=execution.total_duration_ms,
        cost_usd=execution.estimated_cost_usd,
        input_tokens=execution.input_tokens,
        output_tokens=execution.output_tokens,
    )


try:
    initialize_tools()  # type: ignore[no-untyped-call]
except Exception:
    logger.exception('Failed to initialize agent tools during router import.')


class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""

    name: str
    agent_type: str
    description: str | None = None
    system_prompt: str | None = None
    available_tools: list[str] | None = None


class ExecuteAgentRequest(BaseModel):
    """Request to execute an agent."""

    goal: str
    context: dict[str, Any] | None = None


class AgentResponse(BaseModel):
    """Agent configuration response."""

    id: str
    name: str
    agent_type: str
    description: str | None = None
    created_at: str
    created_by: str


class ExecutionResponse(BaseModel):
    """Execution result response."""

    execution_id: str
    status: str
    final_output: str | None = None
    error: str | None = None
    steps_count: int
    duration_ms: int
    cost_usd: float
    input_tokens: int
    output_tokens: int


# Development-only in-memory agent storage. Production must use a durable backend.
agents_db: dict[str, dict[str, Any]] = {}
executions_db: dict[str, AgentExecution] = {}


@router.post('/create', response_model=AgentResponse)
async def create_agent_endpoint(
    request: CreateAgentRequest,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    """Create a new agent."""

    try:
        _ensure_agent_store_writable()
        tenant_id = _current_tenant_id(auth)
        agent_id = str(uuid.uuid4())

        try:
            AgentType(request.agent_type)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent type: {request.agent_type}. Must be one of: {', '.join([t.value for t in AgentType])}",
            ) from exc

        agent_config = {
            'id': agent_id,
            'tenant_id': tenant_id,
            'name': request.name,
            'agent_type': request.agent_type,
            'description': request.description,
            'system_prompt': request.system_prompt,
            'available_tools': request.available_tools or [],
            'created_at': datetime.now(UTC).isoformat(),
            'created_by': tenant_id,
        }
        agents_db[agent_id] = agent_config
        return AgentResponse(**agent_config)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed to create agent.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/list', response_model=list[AgentResponse])
async def list_agents(
    auth: Annotated[AuthContext, Depends(require_auth)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """List all agents for a tenant."""

    try:
        tenant_id = _current_tenant_id(auth)
        tenant_agents = [
            agent for agent in agents_db.values() if agent.get('tenant_id') == tenant_id
        ][skip : skip + limit]
        return [AgentResponse(**agent) for agent in tenant_agents]

    except Exception as exc:
        logger.exception('Failed to list agents.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/{agent_id}', response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    """Get agent details."""

    try:
        tenant_id = _current_tenant_id(auth)
        agent = agents_db.get(agent_id)
        if not agent or agent.get('tenant_id') != tenant_id:
            raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)
        return AgentResponse(**agent)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed to get agent.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post('/{agent_id}/execute', response_model=ExecutionResponse)
async def execute_agent(
    agent_id: str,
    request: ExecuteAgentRequest,
    background_tasks: BackgroundTasks,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    """Execute an agent."""

    try:
        _ensure_agent_store_writable()
        tenant_id = _current_tenant_id(auth)
        agent_config = agents_db.get(agent_id)
        if not agent_config or agent_config.get('tenant_id') != tenant_id:
            raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)

        agent = create_agent(
            agent_type=agent_config['agent_type'],
            agent_id=agent_id,
            tenant_id=tenant_id,
            tool_registry=tool_registry,
            system_prompt=agent_config.get('system_prompt'),
            available_tools=[ToolType(tool_name) for tool_name in agent_config.get('available_tools', [])],
        )
        execution_id = str(uuid.uuid4())

        async def run_agent() -> None:
            try:
                execution = await agent.execute(goal=request.goal, context=request.context)
                executions_db[execution_id] = execution
                logger.info('Agent execution %s completed: %s', execution_id, execution.status)
            except Exception as exc:
                logger.exception('Agent execution failed.')
                execution = AgentExecution(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    agent_type=AgentType(agent_config['agent_type']),
                )
                execution.status = 'failed'
                execution.error_message = str(exc)
                executions_db[execution_id] = execution

        background_tasks.add_task(run_agent)
        return ExecutionResponse(
            execution_id=execution_id,
            status='started',
            final_output=None,
            error=None,
            steps_count=0,
            duration_ms=0,
            cost_usd=0.0,
            input_tokens=0,
            output_tokens=0,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed to execute agent.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/executions/{execution_id}', response_model=ExecutionResponse)
async def get_execution(
    execution_id: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    """Get execution details and results."""

    try:
        tenant_id = _current_tenant_id(auth)
        execution = executions_db.get(execution_id)
        if not execution or execution.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
        return _execution_response(execution_id, execution)

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed to get execution.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get('/executions/{execution_id}/steps')
async def get_execution_steps(
    execution_id: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    """Get detailed execution steps."""

    try:
        tenant_id = _current_tenant_id(auth)
        execution = executions_db.get(execution_id)
        if not execution or execution.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)

        return {
            'execution_id': execution_id,
            'status': execution.status,
            'steps': [
                {
                    'step_number': step.step_number,
                    'thought': step.thought,
                    'action': step.action,
                    'tool': step.tool.value if step.tool else None,
                    'tool_result': step.tool_result.dict() if step.tool_result else None,
                    'timestamp': step.timestamp.isoformat(),
                }
                for step in execution.steps
            ],
            'final_output': execution.final_output,
            'error': execution.error_message,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed to get execution steps.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete('/{agent_id}')
async def delete_agent(
    agent_id: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    """Delete an agent."""

    try:
        _ensure_agent_store_writable()
        tenant_id = _current_tenant_id(auth)
        agent = agents_db.get(agent_id)
        if not agent or agent.get('tenant_id') != tenant_id:
            raise HTTPException(status_code=404, detail=AGENT_NOT_FOUND)

        del agents_db[agent_id]
        return {'status': 'deleted'}

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed to delete agent.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc
