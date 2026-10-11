"""Notifications/Delivery HTTP adapters beginning with mark notifications read all."""

from __future__ import annotations
from ..operations.fanout_slack import helper_stream_auth
from .....deps import AuthContext
from ..constants import AuthDep
from ..constants import NOTIFICATION_NOT_FOUND
from ..operations.list_delivery_receipts import execute_delete_notification
from ..operations.list_delivery_receipts import execute_get_digest_batch_status
from ..operations.list_delivery_receipts import execute_get_notification_digest
from ..operations.list_delivery_receipts import execute_mark_notifications_read_all
from ..operations.list_delivery_receipts import execute_stream_notifications
from ..runtime import ContextRuntime
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi.responses import StreamingResponse
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/notifications/read-all")
    def mark_notifications_read_all(auth: AuthDep) -> dict[str, Any]:
        return execute_mark_notifications_read_all(runtime, auth)

    @router.delete("/notifications/{notification_id}", responses={404: {"description": NOTIFICATION_NOT_FOUND}})
    def delete_notification(notification_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_delete_notification(runtime, notification_id, auth)

    @router.get("/notifications/digest")
    def get_notification_digest(
        auth: AuthDep,
        frequency: Annotated[str | None, Query(max_length=20)] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> dict[str, Any]:
        return execute_get_notification_digest(runtime, auth, frequency, limit)

    @router.get("/notifications/digest/batch-status")
    def get_digest_batch_status(auth: AuthDep) -> dict[str, Any]:
        return execute_get_digest_batch_status(runtime, auth)

    @router.get("/notifications/stream")
    async def stream_notifications(
        request: Request, auth: Annotated[AuthContext, Depends(helper_stream_auth)]
    ) -> StreamingResponse:
        return await execute_stream_notifications(runtime, request, auth)
