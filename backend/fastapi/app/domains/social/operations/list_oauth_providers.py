"""Social use cases: list oauth providers."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import ConnectAllRequest
from ....domains.social.schemas import OAuthCallbackRequest
from ....domains.social.schemas import OAuthStartRequest
from ..constants import AuthDep
from ..services.oauth import _require_strict_live_oauth
from ..services.oauth import _sw_list_oauth_providers
from ..services.oauth import _sw_oauth_callback
from ..services.oauth import _sw_oauth_connect_all
from ..services.oauth import _sw_oauth_start
from fastapi import APIRouter
from typing import Any


def operation_list_oauth_providers(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:oauth:providers", 180, 60)
    return _sw_list_oauth_providers(auth.tenant_id)


def operation_oauth_start(
    st: _SocialWorkspaceState, router: APIRouter, network: str, payload: OAuthStartRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:oauth:start", 120, 60)
    _require_strict_live_oauth(network.strip().lower())
    return _sw_oauth_start(st, network, payload, auth.tenant_id)


def operation_oauth_callback(
    st: _SocialWorkspaceState, router: APIRouter, network: str, payload: OAuthCallbackRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:oauth:callback", 120, 60)
    return _sw_oauth_callback(st, network, payload, auth.tenant_id)


def operation_oauth_connect_all(
    st: _SocialWorkspaceState, router: APIRouter, payload: ConnectAllRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:oauth:connect-all", 20, 60)
    _require_strict_live_oauth()
    return _sw_oauth_connect_all(st, payload, auth.tenant_id)
