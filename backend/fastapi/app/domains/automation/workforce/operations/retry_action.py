"""Automation/Workforce use cases: retry action."""

from __future__ import annotations
from .....tool_calling_agent import ToolCallingAgent
from .....tool_calling_agent import create_tool_registry_for_mission
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..services.mission_execution import _ai_gateway_url
from .now_iso import helper_audit
from .now_iso import helper_now_iso
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


async def execute_retry_action(runtime: ContextRuntime, retry_id: str, auth: AuthDep) -> dict[str, Any]:
    """Manually trigger a retry for a queued action."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:retry:trigger", 60, 60)
    with runtime._lock:
        retry_item = next(
            (r for r in runtime._retry_queue if r.get("id") == retry_id and r.get("tenant_id") == auth.tenant_id), None
        )
    if retry_item is None:
        raise HTTPException(status_code=404, detail="Retry item not found.")
    mission_id = retry_item.get("mission_id")
    with runtime._lock:
        mission = next(
            (m for m in runtime.missions_memory if m.get("id") == mission_id and m.get("tenant_id") == auth.tenant_id),
            None,
        )
    if mission is None:
        raise HTTPException(status_code=404, detail="Associated mission not found.")
    retry_item["retry_count"] = retry_item.get("retry_count", 0) + 1
    retry_item["status"] = "executing"
    helper_audit(runtime, auth.tenant_id, "workforce_retry_manually_triggered", retry_id)
    return {"status": "accepted", "retry_id": retry_id, "retry_count": retry_item["retry_count"]}


async def execute_enable_tool_calling_for_mission(
    runtime: ContextRuntime, mission_id: str, auth: AuthDep
) -> dict[str, Any]:
    """Enable multi-step tool-calling agent loop for a mission."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:missions:tool-calling", 60, 60)
    with runtime._lock:
        mission = next(
            (m for m in runtime.missions_memory if m.get("id") == mission_id and m.get("tenant_id") == auth.tenant_id),
            None,
        )
    if mission is None:
        raise HTTPException(status_code=404, detail="Mission not found.")
    if mission.get("status") not in ("approved", "running"):
        raise HTTPException(status_code=422, detail="Mission must be approved before enabling tool calling.")
    tool_registry = create_tool_registry_for_mission(runtime.tool_adapters)
    if not tool_registry.tools:
        raise HTTPException(
            status_code=503,
            detail="Workforce tool-calling is unavailable because no executable tool adapters are configured.",
        )
    agent = ToolCallingAgent(
        name=f"Agent-{mission_id[:8]}",
        role=str(mission.get("role", "general")),
        tool_registry=tool_registry,
        ai_gateway_url=_ai_gateway_url(),
        tenant_id=auth.tenant_id,
        max_steps=10,
    )
    goal = f"Execute mission: {mission.get('title')} - {mission.get('objective')}"
    result = await agent.run(goal, mission.get("input_context", {}))
    success = result.get("success") is True
    mission["status"] = "running" if success else "failed"
    mission["updated_at"] = helper_now_iso()
    mission["tool_calling_enabled"] = success
    mission["tool_calling_result"] = result
    helper_audit(
        runtime,
        auth.tenant_id,
        "workforce_tool_calling_completed" if success else "workforce_tool_calling_failed",
        mission_id,
    )
    return {"status": "ok" if success else "failed", "mission_id": mission_id, "agent_result": result}


async def execute_search_knowledge(
    runtime: ContextRuntime,
    auth: AuthDep,
    query: Annotated[str, Query(min_length=1, max_length=500)] = "",
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> dict[str, Any]:
    """Semantic search over knowledge base using embeddings."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:knowledge:search", 180, 60)
    needle = query.lower().strip()
    with runtime._lock:
        rows = [
            d.copy()
            for d in runtime.knowledge_memory
            if d.get("tenant_id") == auth.tenant_id
            and (
                needle in str(d.get("title", "")).lower()
                or needle in str(d.get("body", "")).lower()
                or any((needle in str(tag).lower() for tag in d.get("tags", [])))
            )
        ]
    return {"status": "ok", "results": rows[-limit:], "total": len(rows)}


def execute_memory_stats(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Get memory and knowledge base statistics."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:workforce:memory:stats", 180, 60)
    with runtime._lock:
        tenant_missions = [m for m in runtime.missions_memory if m.get("tenant_id") == auth.tenant_id]
        tenant_outcomes = [o for o in runtime.outcomes_memory if o.get("tenant_id") == auth.tenant_id]
        tenant_knowledge = [k for k in runtime.knowledge_memory if k.get("tenant_id") == auth.tenant_id]
        tenant_integ = [i for i in runtime.integrations_memory if i.get("tenant_id") == auth.tenant_id]
        tenant_retry = [r for r in runtime._retry_queue if r.get("tenant_id") == auth.tenant_id]
    stats = {
        "missions_total": len(tenant_missions),
        "missions_completed": sum((1 for m in tenant_missions if m.get("status") == "completed")),
        "missions_failed": sum((1 for m in tenant_missions if m.get("status") == "failed")),
        "outcomes_total": len(tenant_outcomes),
        "knowledge_documents": len(tenant_knowledge),
        "integrations_connected": sum((1 for i in tenant_integ if i.get("status") == "connected")),
        "retry_queue_pending": sum((1 for r in tenant_retry if r.get("status") == "pending")),
        "success_rate": len([o for o in tenant_outcomes if o.get("status") == "completed"]) / len(tenant_outcomes)
        if tenant_outcomes
        else 0,
    }
    return {"status": "ok", "stats": stats}
