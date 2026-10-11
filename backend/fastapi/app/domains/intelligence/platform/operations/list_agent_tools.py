"""Intelligence/Platform use cases: list agent tools."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import _DEFAULT_AGENT_TOOLS
from ..constants import _agent_tool_calls
from ..services.observability import _now
from ..services.observability import _try_agent_db_query
from fastapi import Query
from typing import Any


async def execute_list_agent_tools(
    auth: AuthDep,
    group: str | None = Query(default=None, description="Filter by group_name"),
    risk_level: str | None = Query(default=None, description="Filter by risk_level: low | medium | high"),
    active_only: bool = Query(default=True),
):
    """Returns the full MCP-style tool registry. Reads from DB with in-memory fallback."""
    _tools_sql = (
        "SELECT key, display_name, group_name, description, fn_signature, risk_level, requires_confirmation, is_active, backend_endpoint FROM ai_agent_tools WHERE is_active = %s"
        if active_only
        else "SELECT key, display_name, group_name, description, fn_signature, risk_level, requires_confirmation, is_active, backend_endpoint FROM ai_agent_tools"
    )
    _tools_params: tuple[Any, ...] = (True,) if active_only else ()
    db_ok, db_rows = _try_agent_db_query(_tools_sql, _tools_params)
    tools: list[dict[str, Any]] = db_rows if db_ok and db_rows else list(_DEFAULT_AGENT_TOOLS)
    if active_only and (not (db_ok and db_rows)):
        tools = [t for t in tools if t.get("is_active", True)]
    if group:
        tools = [t for t in tools if str(t.get("group_name", "")).lower() == group.lower()]
    if risk_level:
        tools = [t for t in tools if t.get("risk_level") == risk_level]
    groups: dict[str, list[dict[str, Any]]] = {}
    for t in tools:
        g = str(t.get("group_name", "Other"))
        groups.setdefault(g, []).append(t)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "total": len(tools),
        "tools": tools,
        "by_group": [{"group": g, "count": len(items), "tools": items} for g, items in groups.items()],
        "db_source": db_ok,
        "retrieved_at": _now(),
    }


async def execute_get_agent_audit(
    auth: AuthDep,
    limit: int = Query(default=50, ge=1, le=500),
    tool_key: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    """Returns a chronological audit log of every tool invocation. Reads from DB with fallback."""
    _SEL = "SELECT tool_key, status, risk_level, agent_role, created_at, duration_ms, error_message FROM ai_agent_tool_calls"
    if tool_key and status:
        _audit_sql = _SEL + " WHERE tenant_id = %s AND tool_key = %s AND status = %s ORDER BY created_at DESC LIMIT %s"
        _audit_params: tuple[Any, ...] = (auth.tenant_id, tool_key, status, limit)
    elif tool_key:
        _audit_sql = _SEL + " WHERE tenant_id = %s AND tool_key = %s ORDER BY created_at DESC LIMIT %s"
        _audit_params = (auth.tenant_id, tool_key, limit)
    elif status:
        _audit_sql = _SEL + " WHERE tenant_id = %s AND status = %s ORDER BY created_at DESC LIMIT %s"
        _audit_params = (auth.tenant_id, status, limit)
    else:
        _audit_sql = _SEL + " WHERE tenant_id = %s ORDER BY created_at DESC LIMIT %s"
        _audit_params = (auth.tenant_id, limit)
    db_ok, calls = _try_agent_db_query(_audit_sql, _audit_params)
    for c in calls:
        if hasattr(c.get("created_at"), "isoformat"):
            c["created_at"] = c["created_at"].isoformat()
    if not db_ok:
        mem_calls = [c for c in _agent_tool_calls if c.get("tenant_id") == auth.tenant_id]
        if tool_key:
            mem_calls = [c for c in mem_calls if c.get("tool_key") == tool_key]
        if status:
            mem_calls = [c for c in mem_calls if c.get("status") == status]
        calls = sorted(mem_calls, key=lambda c: c.get("created_at", ""), reverse=True)[:limit]
    success_count = sum((1 for c in calls if c.get("status") == "success"))
    error_count = sum((1 for c in calls if c.get("status") == "error"))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "total_calls": len(calls),
        "success_count": success_count,
        "error_count": error_count,
        "calls": calls,
        "db_source": db_ok,
        "retrieved_at": _now(),
    }
