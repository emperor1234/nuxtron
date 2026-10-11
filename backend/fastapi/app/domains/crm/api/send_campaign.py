"""Crm HTTP adapters beginning with send campaign."""

from ..constants import AuthDep
from ..constants import CAMPAIGN_NOT_FOUND
from ..constants import SEGMENT_NOT_FOUND
from ..operations.create_segment import execute_create_note
from ..operations.create_segment import execute_create_quote
from ..operations.create_segment import execute_create_segment
from ..operations.create_segment import execute_list_notes
from ..operations.create_segment import execute_list_quotes
from ..operations.update_lead import execute_get_segment_members
from ..operations.update_lead import execute_list_segments
from ..operations.update_lead import execute_send_campaign
from ..runtime import ContextRuntime
from ..schemas import NoteCreateRequest
from ..schemas import QuoteCreateRequest
from ..schemas import SegmentCreateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/crm/campaigns/{campaign_id}/send", responses={404: {"description": CAMPAIGN_NOT_FOUND}})
    def send_campaign(campaign_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_send_campaign(runtime, campaign_id, auth)

    @router.post("/crm/segments")
    def create_segment(payload: SegmentCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_segment(runtime, payload, auth)

    @router.get("/crm/segments")
    def list_segments(auth: AuthDep) -> dict[str, Any]:
        return execute_list_segments(runtime, auth)

    @router.get("/crm/segments/{segment_id}/members", responses={404: {"description": SEGMENT_NOT_FOUND}})
    def get_segment_members(
        segment_id: int,
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_get_segment_members(runtime, segment_id, auth, limit, offset)

    @router.post("/crm/notes")
    def create_note(payload: NoteCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_note(runtime, payload, auth)

    @router.get("/crm/notes")
    def list_notes(
        auth: AuthDep,
        contact_id: Annotated[int | None, Query(ge=1)] = None,
        deal_id: Annotated[int | None, Query(ge=1)] = None,
        company_id: Annotated[int | None, Query(ge=1)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_notes(runtime, auth, contact_id, deal_id, company_id, limit, offset)

    @router.post("/crm/quotes")
    def create_quote(payload: QuoteCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_quote(runtime, payload, auth)

    @router.get("/crm/quotes")
    def list_quotes(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_quotes(runtime, auth, status, limit, offset)
