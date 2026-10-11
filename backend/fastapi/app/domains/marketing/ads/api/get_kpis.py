"""Marketing/Ads HTTP adapters beginning with get kpis."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.get_calendar import execute_ab_test_suggestions
from ..operations.get_calendar import execute_decide_campaign_approval
from ..operations.get_calendar import execute_duplicate_campaign
from ..operations.get_calendar import execute_get_best_time
from ..operations.get_calendar import execute_get_forecast
from ..operations.get_calendar import execute_get_kpis
from ..operations.get_calendar import execute_list_ads_notifications
from ..operations.get_calendar import execute_request_approval
from ..runtime import ContextRuntime
from ..schemas import ApprovalDecisionModel
from ..schemas import ApprovalRequestModel
from ..schemas import CampaignDuplicateRequest
from ..schemas import ForecastResponse
from fastapi import APIRouter
from fastapi import Query


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/kpis")
    async def get_kpis(auth: AuthDep):
        return await execute_get_kpis(runtime, auth)

    @router.get("/forecast", response_model=ForecastResponse)
    async def get_forecast(auth: AuthDep, days: int = Query(default=30, ge=1, le=365)):
        return await execute_get_forecast(runtime, auth, days)

    @router.get("/notifications")
    async def list_ads_notifications(auth: AuthDep, limit: int = Query(default=50, ge=1, le=200)):
        return await execute_list_ads_notifications(runtime, auth, limit)

    @router.get("/best-time")
    async def get_best_time(
        auth: AuthDep, platform: str = Query(default="google_ads"), objective: str = Query(default="conversions")
    ):
        return await execute_get_best_time(runtime, auth, platform, objective)

    @router.post("/campaigns/{campaign_id}/request-approval")
    async def request_approval(campaign_id: str, payload: ApprovalRequestModel, auth: AuthDep):
        return await execute_request_approval(runtime, campaign_id, payload, auth)

    @router.post("/campaigns/{campaign_id}/approve")
    async def decide_campaign_approval(campaign_id: str, payload: ApprovalDecisionModel, auth: AuthDep):
        return await execute_decide_campaign_approval(runtime, campaign_id, payload, auth)

    @router.post("/campaigns/{campaign_id}/duplicate")
    async def duplicate_campaign(campaign_id: str, payload: CampaignDuplicateRequest, auth: AuthDep):
        return await execute_duplicate_campaign(runtime, campaign_id, payload, auth)

    @router.get("/ab-test/{campaign_id}/suggestions")
    async def ab_test_suggestions(campaign_id: str, auth: AuthDep):
        return await execute_ab_test_suggestions(runtime, campaign_id, auth)
