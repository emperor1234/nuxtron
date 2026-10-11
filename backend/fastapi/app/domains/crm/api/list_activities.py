"""Crm HTTP adapters beginning with list activities."""

from ..constants import AuthDep
from ..constants import LEAD_NOT_FOUND
from ..operations.list_deals import execute_create_lead
from ..operations.list_deals import execute_create_webhook
from ..operations.list_deals import execute_export_crm
from ..operations.list_deals import execute_get_lead
from ..operations.list_deals import execute_list_activities
from ..operations.list_deals import execute_list_leads
from ..operations.list_deals import execute_list_webhooks
from ..operations.list_deals import execute_test_webhook
from ..runtime import ContextRuntime
from ..schemas import CRMWebhookCreateRequest
from ..schemas import LeadCreateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/crm/activities")
    def list_activities(
        auth: AuthDep,
        type: Annotated[str | None, Query(max_length=40)] = None,
        contact_id: Annotated[int | None, Query(ge=1)] = None,
        deal_id: Annotated[int | None, Query(ge=1)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_activities(runtime, auth, type, contact_id, deal_id, limit, offset)

    @router.get("/crm/export")
    def export_crm(
        auth: AuthDep,
        resource: Annotated[str, Query(pattern="^(contacts|companies|deals|activities)$")] = "contacts",
        format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
    ) -> dict[str, Any]:
        return execute_export_crm(runtime, auth, resource, format)

    @router.post("/crm/webhooks")
    def create_webhook(payload: CRMWebhookCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_webhook(runtime, payload, auth)

    @router.get("/crm/webhooks")
    def list_webhooks(auth: AuthDep) -> dict[str, Any]:
        return execute_list_webhooks(runtime, auth)

    @router.post("/crm/webhooks/{webhook_id}/test", responses={404: {"description": "Webhook not found."}})
    def test_webhook(webhook_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_test_webhook(runtime, webhook_id, auth)

    @router.post("/crm/leads")
    def create_lead(payload: LeadCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_lead(runtime, payload, auth)

    @router.get("/crm/leads")
    def list_leads(
        auth: AuthDep,
        q: Annotated[str | None, Query(max_length=160)] = None,
        status: Annotated[str | None, Query(max_length=40)] = None,
        assigned_to: Annotated[str | None, Query(max_length=120)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_leads(runtime, auth, q, status, assigned_to, limit, offset)

    @router.get("/crm/leads/{lead_id}", responses={404: {"description": LEAD_NOT_FOUND}})
    def get_lead(lead_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_get_lead(runtime, lead_id, auth)
