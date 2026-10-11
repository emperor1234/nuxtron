"""Social HTTP adapters: get social inbox stats."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import CommentToDmRequest
from ....domains.social.schemas import DmChatbotReplyRequest
from ....domains.social.schemas import SavedReplyCreateRequest
from ....domains.social.schemas import SavedReplyUpdateRequest
from ....domains.social.schemas import SocialInboxRespondRequest
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..operations.create_social_automation_rule import operation_create_social_saved_reply
from ..operations.create_social_automation_rule import operation_get_social_inbox_stats
from ..operations.create_social_automation_rule import operation_list_social_saved_replies
from ..operations.create_social_automation_rule import operation_mark_social_inbox_read
from ..operations.create_social_automation_rule import operation_respond_social_inbox
from ..operations.create_social_automation_rule import operation_respond_with_dm_chatbot
from ..operations.create_social_automation_rule import operation_run_comment_to_dm
from ..operations.create_social_automation_rule import operation_update_social_saved_reply
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/inbox/stats")
    def get_social_inbox_stats(auth: AuthDep) -> dict[str, Any]:
        return operation_get_social_inbox_stats(st, router, auth)

    @router.put("/social/inbox/{message_id}/read", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def mark_social_inbox_read(message_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_mark_social_inbox_read(st, router, message_id, auth)

    @router.post("/social/inbox/{message_id}/respond", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def respond_social_inbox(message_id: int, payload: SocialInboxRespondRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_respond_social_inbox(st, router, message_id, payload, auth)

    @router.post("/social/inbox/agents/dm-chatbot/respond", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def respond_with_dm_chatbot(payload: DmChatbotReplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_respond_with_dm_chatbot(st, router, payload, auth)

    @router.post("/social/inbox/comment-to-dm", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def run_comment_to_dm(payload: CommentToDmRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_run_comment_to_dm(st, router, payload, auth)

    @router.get("/social/inbox/saved-replies")
    def list_social_saved_replies(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_saved_replies(st, router, auth)

    @router.post("/social/inbox/saved-replies")
    def create_social_saved_reply(payload: SavedReplyCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_social_saved_reply(st, router, payload, auth)

    @router.patch("/social/inbox/saved-replies/{reply_id}", responses={404: {"description": "Saved reply not found"}})
    def update_social_saved_reply(reply_id: int, payload: SavedReplyUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_update_social_saved_reply(st, router, reply_id, payload, auth)
