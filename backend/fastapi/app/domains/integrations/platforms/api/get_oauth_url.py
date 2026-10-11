"""Integrations/Platforms HTTP adapters beginning with get oauth url."""

from __future__ import annotations
from .....deps import AuthContext
from .....deps import require_auth
from ..operations.get_oauth_url import execute_disconnect_account
from ..operations.get_oauth_url import execute_get_oauth_url
from ..operations.get_oauth_url import execute_list_accounts
from ..operations.get_oauth_url import execute_oauth_callback
from ..operations.get_oauth_url import execute_publish_post
from ..operations.get_oauth_url import execute_refresh_account_token
from ..operations.schedule_post import execute_schedule_post
from ..operations.schedule_post import execute_schedule_single_platform_post
from ..runtime import ContextRuntime
from ..schemas import OAuthCallbackRequest
from ..schemas import PlatformScheduleRequest
from ..schemas import PublishRequest
from ..schemas import SchedulePostRequest
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/oauth/authorize/{platform}")
    def get_oauth_url(
        platform: str, redirect_uri: str = Query(...), auth: AuthContext = Depends(require_auth)
    ) -> dict[str, Any]:
        return execute_get_oauth_url(runtime, platform, redirect_uri, auth)

    @router.get("/accounts")
    def list_accounts(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return execute_list_accounts(runtime, auth)

    @router.post("/oauth/{platform}/callback")
    def oauth_callback(
        platform: str, payload: OAuthCallbackRequest, auth: AuthContext = Depends(require_auth)
    ) -> dict[str, Any]:
        return execute_oauth_callback(runtime, platform, payload, auth)

    @router.post("/accounts/{account_id}/disconnect")
    def disconnect_account(account_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return execute_disconnect_account(runtime, account_id, auth)

    @router.post("/accounts/{account_id}/refresh-token")
    def refresh_account_token(account_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return execute_refresh_account_token(runtime, account_id, auth)

    @router.post("/{platform}/publish")
    async def publish_post(
        platform: str, request: PublishRequest, auth: AuthContext = Depends(require_auth)
    ) -> dict[str, Any]:
        return await execute_publish_post(runtime, platform, request, auth)

    @router.post("/schedule")
    async def schedule_post(request: SchedulePostRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
        return await execute_schedule_post(runtime, request, auth)

    @router.post("/{platform}/schedule")
    async def schedule_single_platform_post(
        platform: str, request: PlatformScheduleRequest, auth: AuthContext = Depends(require_auth)
    ) -> dict[str, Any]:
        return await execute_schedule_single_platform_post(runtime, platform, request, auth)
