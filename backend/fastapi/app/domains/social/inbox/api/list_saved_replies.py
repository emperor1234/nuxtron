"""Social/Inbox HTTP adapters beginning with list saved replies."""

from __future__ import annotations
from ..constants import REPLY_NOT_FOUND
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..operations.approve_response import execute_approve_response
from ..operations.inbox_ops_go_live_gate import execute_auto_respond
from ..operations.inbox_ops_go_live_gate import execute_reject_response
from ..operations.list_messages import execute_delete_saved_reply
from ..operations.replay_delivery_failure import execute_update_saved_reply
from ..operations.replay_delivery_failures_bulk import execute_list_saved_replies
from ..runtime import ContextRuntime
from ..schemas import AutoResponseRequest
from ..schemas import ResponseApprovalRequest
from ..schemas import ResponseRejectionRequest
from ..schemas import SavedReplyUpdateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/inbox/saved-replies")
    def list_saved_replies(
        auth: AuthDep,
        search: Annotated[str | None, Query(max_length=120)] = None,
        tag: Annotated[str | None, Query(max_length=40)] = None,
        network: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_saved_replies(runtime, auth, search, tag, network, limit, offset)

    @router.patch("/inbox/saved-replies/{reply_id}", responses={404: {"description": REPLY_NOT_FOUND}})
    def update_saved_reply(reply_id: int, payload: SavedReplyUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_update_saved_reply(runtime, reply_id, payload, auth)

    @router.delete("/inbox/saved-replies/{reply_id}", responses={404: {"description": REPLY_NOT_FOUND}})
    def delete_saved_reply(reply_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_delete_saved_reply(runtime, reply_id, auth)

    @router.post(
        "/inbox/messages/{message_id}/auto-respond",
        responses={404: {"description": MESSAGE_NOT_FOUND}, 422: {"description": "Invalid auto-response request"}},
    )
    def auto_respond(message_id: int, payload: AutoResponseRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_auto_respond(runtime, message_id, payload, auth)

    @router.post(
        "/inbox/messages/{message_id}/approve-response",
        responses={
            404: {"description": MESSAGE_NOT_FOUND},
            409: {"description": "No approval-pending response exists"},
            422: {"description": "Unsupported delivery network"},
            502: {"description": "Outbound provider delivery failed"},
        },
    )
    async def approve_response(message_id: int, payload: ResponseApprovalRequest, auth: AuthDep) -> dict[str, Any]:
        return await execute_approve_response(runtime, message_id, payload, auth)

    @router.post(
        "/inbox/messages/{message_id}/reject-response",
        responses={
            404: {"description": MESSAGE_NOT_FOUND},
            409: {"description": "No approval-pending response exists"},
        },
    )
    def reject_response(message_id: int, payload: ResponseRejectionRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_reject_response(runtime, message_id, payload, auth)
