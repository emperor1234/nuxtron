"""Social HTTP adapters: list hashtag groups."""

from ....domains.social.persistence import _SocialWorkspaceState
from ..constants import AuthDep
from ..extended_schemas import FirstCommentRequest
from ..extended_schemas import HashtagGroupCreateRequest
from ..extended_schemas import HashtagGroupUpdateRequest
from ..extended_schemas import ThreadPostRequest
from ..operations.list_hashtag_groups import operation_create_hashtag_group
from ..operations.list_hashtag_groups import operation_create_thread_post
from ..operations.list_hashtag_groups import operation_delete_hashtag_group
from ..operations.list_hashtag_groups import operation_get_first_comment
from ..operations.list_hashtag_groups import operation_get_thread_post
from ..operations.list_hashtag_groups import operation_list_hashtag_groups
from ..operations.list_hashtag_groups import operation_set_first_comment
from ..operations.list_hashtag_groups import operation_update_hashtag_group
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/hashtag-groups")
    def list_hashtag_groups(auth: AuthDep) -> dict[str, Any]:
        return operation_list_hashtag_groups(st, router, auth)

    @router.post("/social/hashtag-groups")
    def create_hashtag_group(payload: HashtagGroupCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_hashtag_group(st, router, payload, auth)

    @router.put("/social/hashtag-groups/{group_id}", responses={404: {"description": "Hashtag group not found"}})
    def update_hashtag_group(group_id: str, payload: HashtagGroupUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_update_hashtag_group(st, router, group_id, payload, auth)

    @router.delete("/social/hashtag-groups/{group_id}", responses={404: {"description": "Hashtag group not found"}})
    def delete_hashtag_group(group_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_delete_hashtag_group(st, router, group_id, auth)

    @router.post("/social/content/first-comment")
    def set_first_comment(payload: FirstCommentRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_set_first_comment(st, router, payload, auth)

    @router.get("/social/content/{post_id}/first-comment")
    def get_first_comment(post_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_get_first_comment(st, router, post_id, auth)

    @router.post("/social/content/thread")
    def create_thread_post(payload: ThreadPostRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_thread_post(st, router, payload, auth)

    @router.get("/social/content/{post_id}/thread")
    def get_thread_post(post_id: str, auth: AuthDep) -> dict[str, Any]:
        return operation_get_thread_post(st, router, post_id, auth)
