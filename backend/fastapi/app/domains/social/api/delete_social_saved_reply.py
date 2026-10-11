"""Social HTTP adapters: delete social saved reply."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import InboxBulkActionRequest
from ....domains.social.schemas import MessageClaimRequest
from ....domains.social.schemas import ReviewReplyRequest
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..operations.bulk_social_inbox_action import operation_bulk_social_inbox_action
from ..operations.bulk_social_inbox_action import operation_list_social_reviews
from ..operations.bulk_social_inbox_action import operation_reply_social_review
from ..operations.create_social_automation_rule import operation_claim_social_message
from ..operations.create_social_automation_rule import operation_complete_social_message
from ..operations.create_social_automation_rule import operation_delete_social_saved_reply
from ..operations.create_social_automation_rule import operation_get_social_message_history
from ..operations.create_social_automation_rule import operation_list_social_contact_views
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.delete("/social/inbox/saved-replies/{reply_id}", responses={404: {"description": "Saved reply not found"}})
    def delete_social_saved_reply(reply_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_delete_social_saved_reply(st, router, reply_id, auth)

    @router.get("/social/inbox/contact-views")
    def list_social_contact_views(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_contact_views(st, router, auth)

    @router.get("/social/inbox/messages/{message_id}/history", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def get_social_message_history(message_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_get_social_message_history(st, router, message_id, auth)

    @router.post("/social/inbox/messages/{message_id}/claim", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def claim_social_message(message_id: int, payload: MessageClaimRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_claim_social_message(st, router, message_id, payload, auth)

    @router.post("/social/inbox/messages/{message_id}/complete", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def complete_social_message(message_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_complete_social_message(st, router, message_id, auth)

    @router.post(
        "/social/inbox/bulk-action",
        responses={400: {"description": "Invalid bulk inbox action request."}, 404: {"description": MESSAGE_NOT_FOUND}},
    )
    def bulk_social_inbox_action(payload: InboxBulkActionRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_bulk_social_inbox_action(st, router, payload, auth)

    @router.get("/social/reviews")
    def list_social_reviews(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_reviews(st, router, auth)

    @router.post("/social/reviews/{review_id}/reply", responses={404: {"description": "Review not found"}})
    def reply_social_review(review_id: int, payload: ReviewReplyRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_reply_social_review(st, router, review_id, payload, auth)
