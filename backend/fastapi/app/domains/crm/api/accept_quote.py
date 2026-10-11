"""Crm HTTP adapters beginning with accept quote."""

from ..constants import AuthDep
from ..constants import INVOICE_NOT_FOUND
from ..constants import QUOTE_NOT_FOUND
from ..constants import SEQUENCE_NOT_FOUND
from ..operations.create_segment import execute_accept_quote
from ..operations.create_segment import execute_create_invoice
from ..operations.create_segment import execute_create_sequence
from ..operations.create_segment import execute_enroll_in_sequence
from ..operations.create_segment import execute_list_invoices
from ..operations.create_segment import execute_update_invoice
from ..operations.create_workflow_rule import execute_create_workflow_rule
from ..operations.update_lead import execute_list_sequences
from ..runtime import ContextRuntime
from ..schemas import CRMInvoiceCreateRequest
from ..schemas import CRMInvoiceUpdateRequest
from ..schemas import EmailSequenceCreateRequest
from ..schemas import WorkflowRuleCreateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/crm/quotes/{quote_id}/accept", responses={404: {"description": QUOTE_NOT_FOUND}})
    def accept_quote(quote_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_accept_quote(runtime, quote_id, auth)

    @router.post("/crm/invoices")
    def create_invoice(payload: CRMInvoiceCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_invoice(runtime, payload, auth)

    @router.get("/crm/invoices")
    def list_invoices(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_invoices(runtime, auth, status, limit, offset)

    @router.patch("/crm/invoices/{invoice_id}", responses={404: {"description": INVOICE_NOT_FOUND}})
    def update_invoice(invoice_id: int, payload: CRMInvoiceUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_update_invoice(runtime, invoice_id, payload, auth)

    @router.post("/crm/email-sequences")
    def create_sequence(payload: EmailSequenceCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_sequence(runtime, payload, auth)

    @router.get("/crm/email-sequences")
    def list_sequences(auth: AuthDep) -> dict[str, Any]:
        return execute_list_sequences(runtime, auth)

    @router.post("/crm/email-sequences/{seq_id}/enroll", responses={404: {"description": SEQUENCE_NOT_FOUND}})
    def enroll_in_sequence(seq_id: int, auth: AuthDep, contact_id: int) -> dict[str, Any]:
        return execute_enroll_in_sequence(runtime, seq_id, auth, contact_id)

    @router.post("/crm/workflow-rules")
    def create_workflow_rule(payload: WorkflowRuleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_workflow_rule(runtime, payload, auth)
