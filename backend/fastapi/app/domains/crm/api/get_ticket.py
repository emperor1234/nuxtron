"""Crm HTTP adapters beginning with get ticket."""

from ..constants import AuthDep
from ..constants import CAMPAIGN_NOT_FOUND
from ..constants import TICKET_NOT_FOUND
from ..operations.update_lead import execute_create_campaign
from ..operations.update_lead import execute_create_sla_rule
from ..operations.update_lead import execute_escalate_ticket
from ..operations.update_lead import execute_get_campaign
from ..operations.update_lead import execute_get_ticket
from ..operations.update_lead import execute_list_campaigns
from ..operations.update_lead import execute_list_sla_rules
from ..operations.update_lead import execute_update_ticket
from ..runtime import ContextRuntime
from ..schemas import CampaignCreateRequest
from ..schemas import SLARuleCreateRequest
from ..schemas import TicketUpdateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/crm/tickets/{ticket_id}", responses={404: {"description": TICKET_NOT_FOUND}})
    def get_ticket(ticket_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_get_ticket(runtime, ticket_id, auth)

    @router.patch("/crm/tickets/{ticket_id}", responses={404: {"description": TICKET_NOT_FOUND}})
    def update_ticket(ticket_id: int, payload: TicketUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_update_ticket(runtime, ticket_id, payload, auth)

    @router.post("/crm/tickets/{ticket_id}/escalate", responses={404: {"description": TICKET_NOT_FOUND}})
    def escalate_ticket(ticket_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_escalate_ticket(runtime, ticket_id, auth)

    @router.post("/crm/sla-rules")
    def create_sla_rule(payload: SLARuleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_sla_rule(runtime, payload, auth)

    @router.get("/crm/sla-rules")
    def list_sla_rules(auth: AuthDep) -> dict[str, Any]:
        return execute_list_sla_rules(runtime, auth)

    @router.post("/crm/campaigns")
    def create_campaign(payload: CampaignCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_campaign(runtime, payload, auth)

    @router.get("/crm/campaigns")
    def list_campaigns(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        type: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_campaigns(runtime, auth, status, type, limit, offset)

    @router.get("/crm/campaigns/{campaign_id}", responses={404: {"description": CAMPAIGN_NOT_FOUND}})
    def get_campaign(campaign_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_get_campaign(runtime, campaign_id, auth)
