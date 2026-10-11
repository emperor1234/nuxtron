"""Social Workspace oauth service."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import ConnectAllRequest
from ....domains.social.schemas import OAuthCallbackRequest
from ....domains.social.schemas import OAuthStartRequest
from ..constants import OAUTH_PROVIDERS
from ..constants import SUPPORTED_NETWORKS
from ..constants import UNSUPPORTED_SOCIAL_NETWORK
from .capabilities import _strict_social_mode_enabled
from .workspace import _sw_http_error
from .workspace_connect_account import _sw_connect_account
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode
import os
import secrets


def _oauth_mode() -> str:
    configured = os.getenv("SOCIAL_OAUTH_MODE")
    if configured is not None and configured.strip():
        return configured.strip().lower()
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    return "live" if environment == "production" else "mock"


def _require_strict_live_oauth(network: str | None = None) -> None:
    if not _strict_social_mode_enabled():
        return
    if _oauth_mode() != "live":
        raise _sw_http_error(status_code=503, detail="Strict social mode requires SOCIAL_OAUTH_MODE=live.")
    if network and (not _provider_is_configured(network)):
        raise _sw_http_error(status_code=503, detail=f"Strict social mode requires OAuth credentials for {network}.")


def _default_redirect_uri(network: str) -> str:
    base = (
        os.getenv("SOCIAL_OAUTH_BASE_REDIRECT_URI")
        or os.getenv("NEXT_PUBLIC_SITE_URL")
        or os.getenv("SITE_URL")
        or "http://localhost:4173/studio/workspace"
    )
    return f"{base.rstrip('/')}/oauth/{network}/callback"


def _provider_is_configured(network: str) -> bool:
    provider = OAUTH_PROVIDERS.get(network)
    if provider is None:
        return False
    client_id = os.getenv(provider["client_id_env"], "").strip()
    return bool(client_id)


def _build_authorization_url(network: str, state: str, redirect_uri: str) -> str:
    provider = OAUTH_PROVIDERS[network]
    client_id = os.getenv(provider["client_id_env"], "").strip() or f"mock-{network}-client"
    query = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": provider["scope"],
        "state": state,
    }
    return f"{provider['authorize_url']}?{urlencode(query)}"


def _sw_list_oauth_providers(tenant_id: str) -> dict[str, Any]:
    mode = _oauth_mode()
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "mode": mode,
        "providers": [
            {
                "network": network,
                "label": meta["label"],
                "configured": _provider_is_configured(network),
                "redirect_uri": _default_redirect_uri(network),
            }
            for network, meta in OAUTH_PROVIDERS.items()
        ],
    }


def _sw_oauth_start(
    st: _SocialWorkspaceState, network: str, payload: OAuthStartRequest, tenant_id: str
) -> dict[str, Any]:
    normalized = network.strip().lower()
    if normalized not in OAUTH_PROVIDERS:
        raise _sw_http_error(status_code=422, detail=UNSUPPORTED_SOCIAL_NETWORK)
    state = secrets.token_urlsafe(24)
    redirect_uri = _default_redirect_uri(normalized)
    account_name = (payload.account_name or f"{tenant_id} {OAUTH_PROVIDERS[normalized]['label']}").strip()
    handle = (payload.handle or f"{tenant_id}_{normalized}").strip().lstrip("@")
    st.oauth_states[state] = {
        "tenant_id": tenant_id,
        "network": normalized,
        "account_name": account_name,
        "handle": handle,
        "account_type": payload.account_type,
        "website": payload.website,
        "description": payload.description,
        "created_at": datetime.now(UTC),
    }
    authorization_url = _build_authorization_url(normalized, state, redirect_uri)
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "network": normalized,
        "provider_label": OAUTH_PROVIDERS[normalized]["label"],
        "mode": _oauth_mode(),
        "configured": _provider_is_configured(normalized),
        "state": state,
        "redirect_uri": redirect_uri,
        "authorization_url": authorization_url,
    }


def _sw_oauth_callback(
    st: _SocialWorkspaceState, network: str, payload: OAuthCallbackRequest, tenant_id: str
) -> dict[str, Any]:
    normalized = network.strip().lower()
    if normalized not in OAUTH_PROVIDERS:
        raise _sw_http_error(status_code=422, detail=UNSUPPORTED_SOCIAL_NETWORK)
    state_info = st.oauth_states.pop(payload.state, None)
    if state_info is None:
        raise _sw_http_error(status_code=400, detail="OAuth state is invalid or expired.")
    if state_info.get("tenant_id") != tenant_id or state_info.get("network") != normalized:
        raise _sw_http_error(status_code=400, detail="OAuth state mismatch.")
    if datetime.now(UTC) - state_info["created_at"] > timedelta(minutes=15):
        raise _sw_http_error(status_code=400, detail="OAuth state expired. Restart connection.")
    mode = _oauth_mode()
    if mode == "live" and (not _provider_is_configured(normalized)):
        raise _sw_http_error(status_code=503, detail="OAuth provider credentials are not configured for this network.")
    account, connected = _sw_connect_account(
        st,
        tenant_id=tenant_id,
        network=normalized,
        account_name=str(state_info["account_name"]),
        handle=str(state_info["handle"]),
        account_type=str(state_info["account_type"]),
        website=state_info.get("website"),
        description=state_info.get("description"),
        oauth_provider="oauth2" if mode == "live" else "oauth2-development",
    )
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "network": normalized,
        "mode": mode,
        "code_exchanged": True,
        "connected": connected,
        "account": account,
    }


def _sw_oauth_connect_all(st: _SocialWorkspaceState, payload: ConnectAllRequest, tenant_id: str) -> dict[str, Any]:
    connected_accounts: list[dict[str, Any]] = []
    already_connected: list[str] = []
    for network, meta in SUPPORTED_NETWORKS.items():
        account, connected = _sw_connect_account(
            st,
            tenant_id=tenant_id,
            network=network,
            account_name=f"{payload.account_name_prefix.strip()} {meta['label']}",
            handle=f"{payload.handle_prefix.strip().lower().replace(' ', '_')}_{network}",
            account_type=payload.account_type,
            website=payload.website,
            description=payload.description,
            oauth_provider="oauth2-development" if _oauth_mode() != "live" else "oauth2",
        )
        if connected:
            connected_accounts.append(account)
        else:
            already_connected.append(network)
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "connected_count": len(connected_accounts),
        "already_connected_count": len(already_connected),
        "connected_accounts": connected_accounts,
        "already_connected_networks": already_connected,
    }
