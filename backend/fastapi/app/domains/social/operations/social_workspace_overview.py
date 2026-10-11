"""Social use cases: social workspace overview."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import AutoPostRequest
from ....domains.social.schemas import SocialEngageRequest
from ..constants import AuthDep
from ..services.publishing import _sw_autopilot_preview
from ..services.publishing_autopilot_publish import _sw_autopilot_publish
from ..services.workspace_connect_account import _sw_engage_inbox_message
from ..services.workspace_connect_account import _sw_workspace_overview
from fastapi import APIRouter
from typing import Any


def operation_social_workspace_overview(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:overview", 240, 60)
    return _sw_workspace_overview(st, auth.tenant_id)


def operation_engage_inbox_message(
    st: _SocialWorkspaceState, router: APIRouter, message_id: int, payload: SocialEngageRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:inbox:engage", 180, 60)
    return _sw_engage_inbox_message(st, message_id, payload, auth.tenant_id)


def operation_autopilot_preview(
    st: _SocialWorkspaceState, router: APIRouter, payload: AutoPostRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:autopilot:preview", 120, 60)
    return _sw_autopilot_preview(st, payload, auth.tenant_id)


def operation_autopilot_publish(
    st: _SocialWorkspaceState, router: APIRouter, payload: AutoPostRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:social:autopilot:publish", 120, 60)
    return _sw_autopilot_publish(st, payload, auth.tenant_id)
