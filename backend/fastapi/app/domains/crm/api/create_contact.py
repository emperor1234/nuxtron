"""Crm HTTP adapters beginning with create contact."""

from ..constants import AuthDep
from ..constants import CONTACT_NOT_FOUND
from ..operations.get_live_sync_state import execute_connect_hubspot
from ..operations.get_live_sync_state import execute_create_contact
from ..operations.get_live_sync_state import execute_dedupe_contacts
from ..operations.get_live_sync_state import execute_get_contact
from ..operations.get_live_sync_state import execute_hubspot_status
from ..operations.get_live_sync_state import execute_list_contacts
from ..operations.get_live_sync_state import execute_score_contact
from ..operations.get_live_sync_state import execute_sync_hubspot_contacts
from ..runtime import ContextRuntime
from ..schemas import ContactCreateRequest
from ..schemas import ContactDedupeRequest
from ..schemas import ContactScoreRequest
from ..schemas import HubSpotConnectRequest
from ..schemas import HubSpotSyncContactsRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/crm/contacts")
    def create_contact(payload: ContactCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_contact(runtime, payload, auth)

    @router.post("/crm/integrations/hubspot/connect")
    async def connect_hubspot(payload: HubSpotConnectRequest, auth: AuthDep) -> dict[str, Any]:
        return await execute_connect_hubspot(runtime, payload, auth)

    @router.get("/crm/integrations/hubspot/status")
    def hubspot_status(auth: AuthDep) -> dict[str, Any]:
        return execute_hubspot_status(runtime, auth)

    @router.post("/crm/integrations/hubspot/sync/contacts")
    async def sync_hubspot_contacts(payload: HubSpotSyncContactsRequest, auth: AuthDep) -> dict[str, Any]:
        return await execute_sync_hubspot_contacts(runtime, payload, auth)

    @router.get("/crm/contacts")
    def list_contacts(
        auth: AuthDep,
        q: Annotated[str | None, Query(max_length=160)] = None,
        lifecycle_stage: Annotated[str | None, Query(max_length=40)] = None,
        min_lead_score: Annotated[int, Query(ge=0, le=100)] = 0,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_contacts(runtime, auth, q, lifecycle_stage, min_lead_score, limit, offset)

    @router.post("/crm/contacts/dedupe")
    def dedupe_contacts(payload: ContactDedupeRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_dedupe_contacts(runtime, payload, auth)

    @router.get("/crm/contacts/{contact_id}", responses={404: {"description": CONTACT_NOT_FOUND}})
    def get_contact(contact_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_get_contact(runtime, contact_id, auth)

    @router.post("/crm/contacts/{contact_id}/score", responses={404: {"description": CONTACT_NOT_FOUND}})
    def score_contact(contact_id: int, payload: ContactScoreRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_score_contact(runtime, contact_id, payload, auth)
