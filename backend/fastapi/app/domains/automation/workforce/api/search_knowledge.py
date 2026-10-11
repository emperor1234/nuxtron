"""Automation/Workforce HTTP adapters beginning with search knowledge."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.retry_action import execute_memory_stats
from ..operations.retry_action import execute_search_knowledge
from ..runtime import ContextRuntime
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/knowledge-search")
    async def search_knowledge(
        auth: AuthDep,
        query: Annotated[str, Query(min_length=1, max_length=500)] = "",
        limit: Annotated[int, Query(ge=1, le=50)] = 10,
    ) -> dict[str, Any]:
        return await execute_search_knowledge(runtime, auth, query, limit)

    @router.get("/memory/stats")
    def memory_stats(auth: AuthDep) -> dict[str, Any]:
        return execute_memory_stats(runtime, auth)
