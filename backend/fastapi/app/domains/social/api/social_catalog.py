"""Social HTTP adapters: social catalog."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import SocialAccountConnectRequest
from ..constants import ACCOUNT_NOT_FOUND
from ..constants import AuthDep
from ..operations.social_catalog import operation_connect_social_account
from ..operations.social_catalog import operation_disconnect_social_account
from ..operations.social_catalog import operation_list_social_accounts
from ..operations.social_catalog import operation_social_catalog
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/accounts/catalog")
    def social_catalog(auth: AuthDep) -> dict[str, Any]:
        return operation_social_catalog(st, router, auth)

    @router.post("/social/accounts/connect", responses={422: {"description": "Unsupported social network"}})
    def connect_social_account(payload: SocialAccountConnectRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_connect_social_account(st, router, payload, auth)

    @router.get("/social/accounts")
    def list_social_accounts(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_accounts(st, router, auth)

    @router.delete("/social/accounts/{account_id}", responses={404: {"description": ACCOUNT_NOT_FOUND}})
    def disconnect_social_account(account_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_disconnect_social_account(st, router, account_id, auth)
