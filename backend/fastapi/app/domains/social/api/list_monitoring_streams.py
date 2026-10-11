"""Social HTTP adapters: list monitoring streams."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import AdBoostRequest
from ....domains.social.schemas import AdCampaignCreateRequest
from ....domains.social.schemas import StreamCreateRequest
from ....domains.social.schemas import StreamUpdateRequest
from ..constants import AuthDep
from ..operations.get_competitor_insights import operation_boost_organic_post
from ..operations.get_competitor_insights import operation_create_ad_campaign
from ..operations.get_competitor_insights import operation_create_monitoring_stream
from ..operations.get_competitor_insights import operation_delete_monitoring_stream
from ..operations.get_competitor_insights import operation_list_ad_campaigns
from ..operations.get_competitor_insights import operation_list_monitoring_streams
from ..operations.get_competitor_insights import operation_update_ad_campaign_status
from ..operations.get_competitor_insights import operation_update_monitoring_stream
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/streams")
    def list_monitoring_streams(auth: AuthDep) -> dict[str, Any]:
        return operation_list_monitoring_streams(st, router, auth)

    @router.post("/social/streams")
    def create_monitoring_stream(payload: StreamCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_monitoring_stream(st, router, payload, auth)

    @router.patch("/social/streams/{stream_id}", responses={404: {"description": "Stream not found"}})
    def update_monitoring_stream(stream_id: int, payload: StreamUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_update_monitoring_stream(st, router, stream_id, payload, auth)

    @router.delete("/social/streams/{stream_id}", responses={404: {"description": "Stream not found"}})
    def delete_monitoring_stream(stream_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_delete_monitoring_stream(st, router, stream_id, auth)

    @router.get("/social/ads/campaigns")
    def list_ad_campaigns(auth: AuthDep) -> dict[str, Any]:
        return operation_list_ad_campaigns(st, router, auth)

    @router.post("/social/ads/campaigns")
    def create_ad_campaign(payload: AdCampaignCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_ad_campaign(st, router, payload, auth)

    @router.patch("/social/ads/campaigns/{campaign_id}/status", responses={404: {"description": "Campaign not found"}})
    def update_ad_campaign_status(campaign_id: int, status: str, auth: AuthDep) -> dict[str, Any]:
        return operation_update_ad_campaign_status(st, router, campaign_id, status, auth)

    @router.post("/social/ads/boost")
    def boost_organic_post(payload: AdBoostRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_boost_organic_post(st, router, payload, auth)
