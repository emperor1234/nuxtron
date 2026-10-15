"""SEO workflow planner HTTP adapters."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from .....deps import AuthContext, require_auth
from ..operations.review_reputation_analyze import (
    execute_planner_execute,
    execute_planner_execute_all_modules,
)
from ..runtime import ContextRuntime
from ..schemas import PlannerExecuteAllReq, PlannerExecuteReq


def register(router: APIRouter, runtime: ContextRuntime) -> None:
    @router.post("/planner/draft", summary="Create a review-only SEO workflow draft")
    async def planner_draft(req: PlannerExecuteReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_planner_execute(runtime, req, auth)

    @router.post(
        "/planner/execute",
        deprecated=True,
        summary="Legacy endpoint; creates a review-only draft and executes no tasks",
    )
    async def planner_execute(req: PlannerExecuteReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_planner_execute(runtime, req, auth)

    @router.post(
        "/planner/execute-all-modules",
        responses={501: {"description": "Automated SEO module orchestration is not implemented."}},
    )
    async def planner_execute_all_modules(
        req: PlannerExecuteAllReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_planner_execute_all_modules(runtime, req, auth)
