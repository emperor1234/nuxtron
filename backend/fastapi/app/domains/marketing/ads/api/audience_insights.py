"""Marketing/Ads HTTP adapters beginning with audience insights."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.ads_health import execute_ads_health
from ..operations.get_calendar import execute_audience_insights
from ..runtime import ContextRuntime
from fastapi import APIRouter


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/audience-insights")
    async def audience_insights(auth: AuthDep):
        return await execute_audience_insights(runtime, auth)

    @router.get("/health")
    async def ads_health(auth: AuthDep):
        return await execute_ads_health(runtime, auth)
