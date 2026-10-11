"""Social use cases: social catalog."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.schemas import SocialAccountConnectRequest
from ..constants import ACCOUNT_NOT_FOUND
from ..constants import AuthDep
from ..constants import SUPPORTED_NETWORKS
from ..constants import UNSUPPORTED_SOCIAL_NETWORK
from ..services.workspace import _sw_http_error
from ..services.workspace_connect_account import _sw_connect_account
from fastapi import APIRouter
from typing import Any


def operation_social_catalog(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:catalog", 240, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "providers": [
            {"network": network, "label": meta["label"], "supported_formats": meta["formats"]}
            for network, meta in SUPPORTED_NETWORKS.items()
        ],
    }


def operation_connect_social_account(
    st: _SocialWorkspaceState, router: APIRouter, payload: SocialAccountConnectRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:accounts:connect", 60, 60)
    network = payload.network.strip().lower()
    if network not in SUPPORTED_NETWORKS:
        raise _sw_http_error(status_code=422, detail=UNSUPPORTED_SOCIAL_NETWORK)
    account, connected = _sw_connect_account(
        st,
        tenant_id=auth.tenant_id,
        network=network,
        account_name=payload.account_name,
        handle=payload.handle,
        account_type=payload.account_type,
        website=payload.website,
        description=payload.description,
        oauth_provider="manual",
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "account": account.copy(), "connected": connected}


def operation_list_social_accounts(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:accounts:list", 240, 60)
    with st.lock:
        items = [account.copy() for account in st.social_accounts if account.get("tenant_id") == auth.tenant_id]
    connected_networks = [item.get("network") for item in items]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items),
        "connected_networks": connected_networks,
        "accounts": items,
    }


def operation_disconnect_social_account(
    st: _SocialWorkspaceState, router: APIRouter, account_id: int, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:accounts:disconnect", 60, 60)
    with st.lock:
        index = next(
            (
                i
                for i, account in enumerate(st.social_accounts)
                if account.get("tenant_id") == auth.tenant_id and account.get("id") == account_id
            ),
            None,
        )
        if index is None:
            raise _sw_http_error(status_code=404, detail=ACCOUNT_NOT_FOUND)
        removed = st.social_accounts.pop(index)
    _sw_audit(st, auth.tenant_id, "social_account_disconnected", account_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "account": removed, "disconnected": True}
