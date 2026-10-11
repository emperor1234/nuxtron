"""Social HTTP adapters: social workspace overview."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import AutoPostRequest
from ....domains.social.schemas import SocialEngageRequest
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..operations.social_workspace_overview import operation_autopilot_preview
from ..operations.social_workspace_overview import operation_autopilot_publish
from ..operations.social_workspace_overview import operation_engage_inbox_message
from ..operations.social_workspace_overview import operation_social_workspace_overview
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/workspace/overview")
    def social_workspace_overview(auth: AuthDep) -> dict[str, Any]:
        return operation_social_workspace_overview(st, router, auth)

    @router.post("/social/inbox/messages/{message_id}/engage", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def engage_inbox_message(message_id: int, payload: SocialEngageRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_engage_inbox_message(st, router, message_id, payload, auth)

    @router.post("/social/autopilot/preview", responses={404: {"description": "Account not found"}})
    def autopilot_preview(payload: AutoPostRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_autopilot_preview(st, router, payload, auth)

    @router.post("/social/autopilot/publish", responses={404: {"description": "Account not found"}})
    def autopilot_publish(payload: AutoPostRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_autopilot_publish(st, router, payload, auth)
