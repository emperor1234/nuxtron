"""Marketing/Ads HTTP adapters beginning with list connectors."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.append_notification import execute_connector_credentials_status
from ..operations.append_notification import execute_create_campaign
from ..operations.append_notification import execute_disconnect_connector
from ..operations.append_notification import execute_get_credit_balances
from ..operations.append_notification import execute_list_campaigns
from ..operations.append_notification import execute_list_connectors
from ..operations.append_notification import execute_oauth_callback
from ..operations.append_notification import execute_oauth_start
from ..runtime import ContextRuntime
from ..schemas import CampaignCreateRequest
from ..schemas import ConnectorCallbackRequest
from ..schemas import ConnectorListResponse
from ..schemas import ConnectorStartResponse
from fastapi import APIRouter
from fastapi import Query


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/connectors", response_model=ConnectorListResponse)
    async def list_connectors(auth: AuthDep):
        return await execute_list_connectors(runtime, auth)

    @router.post("/connectors/{platform}/oauth/start", response_model=ConnectorStartResponse)
    async def oauth_start(platform: str, auth: AuthDep):
        return await execute_oauth_start(runtime, platform, auth)

    @router.post("/connectors/{platform}/oauth/callback")
    async def oauth_callback(platform: str, body: ConnectorCallbackRequest, auth: AuthDep):
        return await execute_oauth_callback(runtime, platform, body, auth)

    @router.get("/connectors/{platform}/credentials/status")
    async def connector_credentials_status(platform: str, auth: AuthDep):
        return await execute_connector_credentials_status(runtime, platform, auth)

    @router.delete("/connectors/{platform}")
    async def disconnect_connector(platform: str, auth: AuthDep):
        return await execute_disconnect_connector(runtime, platform, auth)

    @router.get("/credits")
    async def get_credit_balances(auth: AuthDep):
        return await execute_get_credit_balances(runtime, auth)

    @router.post("/campaigns")
    async def create_campaign(payload: CampaignCreateRequest, auth: AuthDep):
        return await execute_create_campaign(runtime, payload, auth)

    @router.get("/campaigns")
    async def list_campaigns(
        auth: AuthDep, platform: str | None = Query(default=None), status: str | None = Query(default=None)
    ):
        return await execute_list_campaigns(runtime, auth, platform, status)
