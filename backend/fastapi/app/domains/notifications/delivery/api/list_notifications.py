"""Notifications/Delivery HTTP adapters beginning with list notifications."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import NOTIFICATION_NOT_FOUND
from ..operations.fanout_slack import execute_create_notification
from ..operations.fanout_slack import execute_list_notifications
from ..operations.fanout_slack import execute_notification_unread_count
from ..operations.fanout_slack import execute_update_preferences
from ..operations.get_preferences import execute_get_preferences
from ..operations.list_delivery_receipts import execute_delivery_health_summary
from ..operations.list_delivery_receipts import execute_list_delivery_receipts
from ..operations.list_delivery_receipts import execute_mark_notification_read
from ..runtime import ContextRuntime
from ..schemas import NotificationCreateRequest
from ..schemas import NotificationPreferencesRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/notifications")
    def list_notifications(
        auth: AuthDep,
        category: Annotated[str | None, Query(max_length=40)] = None,
        priority: Annotated[str | None, Query(max_length=20)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_notifications(runtime, auth, category, priority, limit, offset)

    @router.get("/notifications/preferences")
    def get_preferences(auth: AuthDep) -> dict[str, Any]:
        return execute_get_preferences(runtime, auth)

    @router.put("/notifications/preferences", responses={422: {"description": "Invalid digest frequency."}})
    def update_preferences(payload: NotificationPreferencesRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_update_preferences(runtime, payload, auth)

    @router.get("/notifications/unread-count")
    def notification_unread_count(auth: AuthDep) -> dict[str, Any]:
        return execute_notification_unread_count(runtime, auth)

    @router.post("/notifications")
    def create_notification(payload: NotificationCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_notification(runtime, payload, auth)

    @router.get("/notifications/delivery-receipts")
    def list_delivery_receipts(
        auth: AuthDep,
        notification_id: Annotated[int | None, Query(ge=1)] = None,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_delivery_receipts(runtime, auth, notification_id, limit, offset)

    @router.get("/notifications/delivery-health")
    def delivery_health_summary(
        auth: AuthDep,
        window_seconds: Annotated[int, Query(ge=60, le=604800)] = 86400,
        channel: Annotated[str | None, Query(max_length=40)] = None,
        delivery_status: Annotated[str | None, Query(max_length=40)] = None,
    ) -> dict[str, Any]:
        return execute_delivery_health_summary(runtime, auth, window_seconds, channel, delivery_status)

    @router.post("/notifications/{notification_id}/read", responses={404: {"description": NOTIFICATION_NOT_FOUND}})
    def mark_notification_read(notification_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_mark_notification_read(runtime, notification_id, auth)
