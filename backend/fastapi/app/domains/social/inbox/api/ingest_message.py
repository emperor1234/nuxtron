"""Social/Inbox HTTP adapters beginning with ingest message."""

from __future__ import annotations
from ..constants import LOCK_NOT_HELD
from ..constants import AuthDep
from ..constants import MESSAGE_NOT_FOUND
from ..operations.audit import execute_ingest_message
from ..operations.audit import execute_update_message
from ..operations.list_messages import execute_acquire_lock
from ..operations.list_messages import execute_add_note
from ..operations.list_messages import execute_get_message
from ..operations.list_messages import execute_list_messages
from ..operations.list_messages import execute_list_notes
from ..operations.list_messages import execute_release_lock
from ..runtime import ContextRuntime
from ..schemas import InboxMessageIngestRequest
from ..schemas import InternalNoteRequest
from ..schemas import LockRequest
from ..schemas import MessageUpdateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/inbox/messages")
    def ingest_message(payload: InboxMessageIngestRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ingest_message(runtime, payload, auth)

    @router.get("/inbox/messages")
    def list_messages(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        network: Annotated[str | None, Query(max_length=40)] = None,
        message_type: Annotated[str | None, Query(max_length=40)] = None,
        sentiment: Annotated[str | None, Query(max_length=20)] = None,
        assigned_to: Annotated[str | None, Query(max_length=160)] = None,
        unread_only: Annotated[bool, Query()] = False,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_messages(
            runtime, auth, status, network, message_type, sentiment, assigned_to, unread_only, limit, offset
        )

    @router.get("/inbox/messages/{message_id}", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def get_message(message_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_get_message(runtime, message_id, auth)

    @router.patch(
        "/inbox/messages/{message_id}",
        responses={404: {"description": MESSAGE_NOT_FOUND}, 422: {"description": "Invalid status value"}},
    )
    def update_message(message_id: int, payload: MessageUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_update_message(runtime, message_id, payload, auth)

    @router.post("/inbox/messages/{message_id}/notes", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def add_note(message_id: int, payload: InternalNoteRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_add_note(runtime, message_id, payload, auth)

    @router.get("/inbox/messages/{message_id}/notes", responses={404: {"description": MESSAGE_NOT_FOUND}})
    def list_notes(message_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_list_notes(runtime, message_id, auth)

    @router.post(
        "/inbox/messages/{message_id}/lock",
        responses={
            404: {"description": MESSAGE_NOT_FOUND},
            409: {"description": "Message already locked by another team member."},
        },
    )
    def acquire_lock(message_id: int, payload: LockRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_acquire_lock(runtime, message_id, payload, auth)

    @router.delete("/inbox/messages/{message_id}/lock", responses={404: {"description": LOCK_NOT_HELD}})
    def release_lock(
        message_id: int, locked_by: Annotated[str, Query(min_length=1, max_length=160)], auth: AuthDep
    ) -> dict[str, Any]:
        return execute_release_lock(runtime, message_id, locked_by, auth)
