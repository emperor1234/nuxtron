"""Fail-closed UGC rights and performance use cases."""

from typing import Any

from fastapi import APIRouter

from ....domains.social.persistence import _SocialWorkspaceState
from ..constants import AuthDep
from ..ugc_unavailable import raise_ugc_unavailable


def operation_request_ugc_rights(
    st: _SocialWorkspaceState,
    router: APIRouter,
    asset_id: int,
    payload: dict[str, Any],
    auth: AuthDep,
) -> dict[str, Any]:
    """Do not claim a creator has received or accepted a rights request."""
    raise_ugc_unavailable()


def operation_batch_approve_ugc(
    st: _SocialWorkspaceState,
    router: APIRouter,
    payload: dict[str, Any],
    auth: AuthDep,
) -> dict[str, Any]:
    """Do not let workspace users self-attest creator rights in bulk."""
    raise_ugc_unavailable()


def operation_get_ugc_performance(
    st: _SocialWorkspaceState,
    router: APIRouter,
    asset_id: int | None = None,
    *,
    auth: AuthDep,
) -> dict[str, Any]:
    """Do not return zero-filled or provider-unverified UGC performance data."""
    raise_ugc_unavailable()
