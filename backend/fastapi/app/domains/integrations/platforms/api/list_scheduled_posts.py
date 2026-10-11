"""Integrations/Platforms HTTP adapters beginning with list scheduled posts."""

from __future__ import annotations
from .....deps import AuthContext
from .....deps import require_auth
from ..operations.force_publish import execute_force_publish
from ..operations.schedule_post import execute_analytics_dashboard
from ..operations.schedule_post import execute_cancel_scheduled_post
from ..operations.schedule_post import execute_get_inbox
from ..operations.schedule_post import execute_get_message
from ..operations.schedule_post import execute_get_post_metrics
from ..operations.schedule_post import execute_list_scheduled_posts
from ..operations.schedule_post import execute_reply_to_message
from ..runtime import ContextRuntime
from ..schemas import MessageReplyRequest
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/scheduled-posts")
    def list_scheduled_posts(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return execute_list_scheduled_posts(runtime, auth)

    @router.post("/scheduled-posts/{post_id}/publish-now")
    async def force_publish(post_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return await execute_force_publish(runtime, post_id, auth)

    @router.post("/scheduled-posts/{post_id}/cancel")
    def cancel_scheduled_post(post_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return execute_cancel_scheduled_post(runtime, post_id, auth)

    @router.get("/posts/{post_id}/metrics")
    async def get_post_metrics(
        post_id: str, platform: str = Query(...), auth: AuthContext = Depends(require_auth)
    ) -> dict[str, Any]:
        return await execute_get_post_metrics(runtime, post_id, platform, auth)

    @router.get("/analytics/dashboard")
    def analytics_dashboard(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return execute_analytics_dashboard(runtime, auth)

    @router.get("/messages/inbox")
    def get_inbox(
        auth: AuthContext = Depends(require_auth), platform: str | None = None, limit: int = Query(20, ge=1, le=100)
    ) -> dict[str, Any]:
        return execute_get_inbox(runtime, auth, platform, limit)

    @router.get("/messages/{message_id}")
    def get_message(message_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return execute_get_message(runtime, message_id, auth)

    @router.post("/messages/{message_id}/reply")
    async def reply_to_message(
        message_id: str, request: MessageReplyRequest, auth: AuthContext = Depends(require_auth)
    ) -> dict[str, Any]:
        return await execute_reply_to_message(runtime, message_id, request, auth)
