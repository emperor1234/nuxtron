"""Social HTTP adapters: list oauth providers."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import ConnectAllRequest
from ....domains.social.schemas import OAuthCallbackRequest
from ....domains.social.schemas import OAuthStartRequest
from ..constants import AuthDep
from ..operations.list_oauth_providers import operation_list_oauth_providers
from ..operations.list_oauth_providers import operation_oauth_callback
from ..operations.list_oauth_providers import operation_oauth_connect_all
from ..operations.list_oauth_providers import operation_oauth_start
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/oauth/providers")
    def list_oauth_providers(auth: AuthDep) -> dict[str, Any]:
        return operation_list_oauth_providers(st, router, auth)

    @router.post("/social/oauth/{network}/start", responses={422: {"description": "Unsupported social network"}})
    def oauth_start(network: str, payload: OAuthStartRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_oauth_start(st, router, network, payload, auth)

    @router.post(
        "/social/oauth/{network}/callback",
        responses={
            400: {"description": "Invalid OAuth state"},
            422: {"description": "Unsupported social network"},
            503: {"description": "OAuth provider not configured"},
        },
    )
    def oauth_callback(network: str, payload: OAuthCallbackRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_oauth_callback(st, router, network, payload, auth)

    @router.post("/social/oauth/connect-all")
    def oauth_connect_all(payload: ConnectAllRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_oauth_connect_all(st, router, payload, auth)
