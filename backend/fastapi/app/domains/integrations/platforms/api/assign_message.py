"""Integrations/Platforms HTTP adapters beginning with assign message."""

from __future__ import annotations
from .....deps import AuthContext
from .....deps import require_auth
from ..operations.force_publish import execute_compare_analytics
from ..operations.force_publish import execute_platform_analytics_summary
from ..operations.force_publish import execute_tag_message
from ..operations.force_publish import execute_verify_accounts
from ..operations.schedule_post import execute_assign_message
from ..operations.schedule_post import execute_platform_health
from ..runtime import ContextRuntime
from ..schemas import MessageAssignRequest
from ..schemas import MessageTagRequest
from fastapi import APIRouter
from fastapi import Depends
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/messages/{message_id}/assign")
    def assign_message(
        message_id: str, request: MessageAssignRequest, auth: AuthContext = Depends(require_auth)
    ) -> dict[str, Any]:
        return execute_assign_message(runtime, message_id, request, auth)

    @router.post("/messages/{message_id}/tag")
    def tag_message(
        message_id: str, request: MessageTagRequest, auth: AuthContext = Depends(require_auth)
    ) -> dict[str, Any]:
        return execute_tag_message(runtime, message_id, request, auth)

    @router.get("/health")
    def platform_health(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return execute_platform_health(runtime, auth)

    @router.get("/accounts/verify")
    def verify_accounts(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return execute_verify_accounts(runtime, auth)

    @router.get("/{platform}/analytics/summary")
    async def platform_analytics_summary(platform: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return await execute_platform_analytics_summary(runtime, platform, auth)

    @router.post("/analytics/compare")
    def compare_analytics(post_ids: list[str], auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return execute_compare_analytics(runtime, post_ids, auth)
