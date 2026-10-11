"""Social HTTP adapters: repurpose longform asset."""

from ....domains.social.persistence import _SocialWorkspaceState
from ..constants import AuthDep
from ..extended_schemas import LongformRepurposeRequest
from ..extended_schemas import StartPageUpdateRequest
from ..extended_schemas import TeamMemberInviteRequest
from ..extended_schemas import TeamMemberUpdateRequest
from ..operations.download_report import operation_get_start_page
from ..operations.download_report import operation_invite_team_member
from ..operations.download_report import operation_list_team_members
from ..operations.download_report import operation_remove_team_member
from ..operations.download_report import operation_repurpose_longform_asset
from ..operations.download_report import operation_update_start_page
from ..operations.download_report import operation_update_team_member
from ..operations.invite_team_member_legacy import operation_invite_team_member_legacy
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.post("/social/automation/repurpose")
    def repurpose_longform_asset(payload: LongformRepurposeRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_repurpose_longform_asset(st, router, payload, auth)

    @router.get("/social/team/members", operation_id="social_workspace_list_team_members")
    def list_team_members(auth: AuthDep) -> dict[str, Any]:
        return operation_list_team_members(st, router, auth)

    @router.post("/social/team/members/invite", operation_id="social_workspace_invite_team_member")
    def invite_team_member(payload: TeamMemberInviteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_invite_team_member(st, router, payload, auth)

    @router.post("/social/team/invite", operation_id="social_workspace_invite_team_member_legacy")
    def invite_team_member_legacy(payload: TeamMemberInviteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_invite_team_member_legacy(st, router, payload, auth)

    @router.put("/social/team/members/{member_id}", responses={404: {"description": "Team member not found"}})
    def update_team_member(member_id: str, payload: TeamMemberUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_update_team_member(st, router, member_id, payload, auth)

    @router.delete("/social/team/members/{member_id}", responses={404: {"description": "Team member not found"}})
    def remove_team_member(member_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_remove_team_member(st, router, member_id, auth)

    @router.get("/social/start-page")
    def get_start_page(auth: AuthDep) -> dict[str, Any]:
        return operation_get_start_page(st, router, auth)

    @router.put("/social/start-page")
    def update_start_page(payload: StartPageUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_update_start_page(st, router, payload, auth)
