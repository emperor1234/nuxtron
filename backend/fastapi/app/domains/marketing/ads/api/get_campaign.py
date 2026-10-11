"""Marketing/Ads HTTP adapters beginning with get campaign."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.append_notification import execute_delete_campaign
from ..operations.append_notification import execute_get_campaign
from ..operations.append_notification import execute_patch_metrics
from ..operations.append_notification import execute_publish_campaign
from ..operations.append_notification import execute_update_campaign
from ..operations.get_calendar import execute_auto_resize_asset
from ..operations.get_calendar import execute_drag_reschedule
from ..operations.get_calendar import execute_get_calendar
from ..runtime import ContextRuntime
from ..schemas import AssetAutoResizeRequest
from ..schemas import CalendarRescheduleRequest
from ..schemas import CampaignMetricsPatchRequest
from ..schemas import CampaignPublishRequest
from ..schemas import CampaignUpdateRequest
from fastapi import APIRouter


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/campaigns/{campaign_id}")
    async def get_campaign(campaign_id: str, auth: AuthDep):
        return await execute_get_campaign(runtime, campaign_id, auth)

    @router.patch("/campaigns/{campaign_id}")
    async def update_campaign(campaign_id: str, payload: CampaignUpdateRequest, auth: AuthDep):
        return await execute_update_campaign(runtime, campaign_id, payload, auth)

    @router.delete("/campaigns/{campaign_id}")
    async def delete_campaign(campaign_id: str, auth: AuthDep):
        return await execute_delete_campaign(runtime, campaign_id, auth)

    @router.post("/campaigns/{campaign_id}/publish")
    async def publish_campaign(campaign_id: str, payload: CampaignPublishRequest, auth: AuthDep):
        return await execute_publish_campaign(runtime, campaign_id, payload, auth)

    @router.post("/campaigns/{campaign_id}/metrics")
    async def patch_metrics(campaign_id: str, payload: CampaignMetricsPatchRequest, auth: AuthDep):
        return await execute_patch_metrics(runtime, campaign_id, payload, auth)

    @router.get("/calendar")
    async def get_calendar(auth: AuthDep):
        return await execute_get_calendar(runtime, auth)

    @router.post("/calendar/drag-reschedule")
    async def drag_reschedule(payload: CalendarRescheduleRequest, auth: AuthDep):
        return await execute_drag_reschedule(runtime, payload, auth)

    @router.post("/assets/auto-resize")
    async def auto_resize_asset(payload: AssetAutoResizeRequest, auth: AuthDep):
        return await execute_auto_resize_asset(runtime, payload, auth)
