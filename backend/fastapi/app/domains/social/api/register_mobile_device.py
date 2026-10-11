"""Social HTTP adapters: register mobile device."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import MobileDeviceRegisterRequest
from ....domains.social.schemas import MobileOfflineSyncRequest
from ....domains.social.schemas import MobileQuickPostRequest
from ..constants import AuthDep
from ..extended_schemas import PostingScheduleRequest
from ..operations.create_integration_webhook import operation_list_mobile_devices
from ..operations.create_integration_webhook import operation_register_mobile_device
from ..operations.create_mobile_quick_post import operation_create_mobile_quick_post
from ..operations.create_mobile_quick_post import operation_get_posting_schedules
from ..operations.create_mobile_quick_post import operation_list_content_templates
from ..operations.create_mobile_quick_post import operation_list_mobile_sync_batches
from ..operations.create_mobile_quick_post import operation_sync_mobile_offline_events
from ..operations.create_mobile_quick_post import operation_update_posting_schedule
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.post("/social/mobile/devices/register")
    def register_mobile_device(payload: MobileDeviceRegisterRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_register_mobile_device(st, router, payload, auth)

    @router.get("/social/mobile/devices")
    def list_mobile_devices(auth: AuthDep) -> dict[str, Any]:
        return operation_list_mobile_devices(st, router, auth)

    @router.post("/social/mobile/quick-post")
    def create_mobile_quick_post(payload: MobileQuickPostRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_mobile_quick_post(st, router, payload, auth)

    @router.post("/social/mobile/sync")
    def sync_mobile_offline_events(payload: MobileOfflineSyncRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_sync_mobile_offline_events(st, router, payload, auth)

    @router.get("/social/mobile/sync/batches")
    def list_mobile_sync_batches(auth: AuthDep, limit: int = 50) -> dict[str, Any]:
        return operation_list_mobile_sync_batches(st, router, auth, limit)

    @router.get("/social/posting-schedules")
    def get_posting_schedules(auth: AuthDep) -> dict[str, Any]:
        return operation_get_posting_schedules(st, router, auth)

    @router.put("/social/posting-schedules/{network}")
    def update_posting_schedule(network: str, payload: PostingScheduleRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_update_posting_schedule(st, router, network, payload, auth)

    @router.get("/social/templates")
    def list_content_templates(
        auth: AuthDep, content_type: str | None = None, network: str | None = None
    ) -> dict[str, Any]:
        return operation_list_content_templates(st, router, auth, content_type, network)
