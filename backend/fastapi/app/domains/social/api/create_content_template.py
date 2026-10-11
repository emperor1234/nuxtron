"""Social HTTP adapters: create content template."""

from ....domains.social.persistence import _SocialWorkspaceState
from ..constants import AuthDep
from ..extended_schemas import CommunityCommentReplyRequest
from ..extended_schemas import ContentTemplateCreateRequest
from ..extended_schemas import SavedCommentReplyCreateRequest
from ..operations.create_mobile_quick_post import operation_create_community_saved_reply
from ..operations.create_mobile_quick_post import operation_create_content_template
from ..operations.create_mobile_quick_post import operation_create_post_from_comment
from ..operations.create_mobile_quick_post import operation_delete_content_template
from ..operations.create_mobile_quick_post import operation_get_comment_score
from ..operations.create_mobile_quick_post import operation_list_community_comments
from ..operations.create_mobile_quick_post import operation_list_community_saved_replies
from ..operations.create_mobile_quick_post import operation_reply_to_community_comment
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.post("/social/templates")
    def create_content_template(payload: ContentTemplateCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_content_template(st, router, payload, auth)

    @router.delete("/social/templates/{template_id}", responses={404: {"description": "Template not found"}})
    def delete_content_template(template_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_delete_content_template(st, router, template_id, auth)

    @router.get("/social/community/comments")
    def list_community_comments(
        auth: AuthDep, network: str | None = None, status: str | None = None, sort: str = "newest", limit: int = 50
    ) -> dict[str, Any]:
        return operation_list_community_comments(st, router, auth, network, status, sort, limit)

    @router.post("/social/community/comments/{comment_id}/reply", responses={404: {"description": "Comment not found"}})
    def reply_to_community_comment(
        comment_id: str, payload: CommunityCommentReplyRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return operation_reply_to_community_comment(st, router, comment_id, payload, auth)

    @router.post(
        "/social/community/comments/{comment_id}/create-post", responses={404: {"description": "Comment not found"}}
    )
    def create_post_from_comment(comment_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_create_post_from_comment(st, router, comment_id, auth)

    @router.get("/social/community/score")
    def get_comment_score(auth: AuthDep) -> dict[str, Any]:
        return operation_get_comment_score(st, router, auth)

    @router.get("/social/community/saved-replies")
    def list_community_saved_replies(auth: AuthDep) -> dict[str, Any]:
        return operation_list_community_saved_replies(st, router, auth)

    @router.post("/social/community/saved-replies")
    def create_community_saved_reply(payload: SavedCommentReplyCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_community_saved_reply(st, router, payload, auth)
