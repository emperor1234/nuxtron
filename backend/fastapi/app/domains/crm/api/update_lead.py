"""Crm HTTP adapters beginning with update lead."""

from ..constants import AuthDep
from ..constants import LEAD_NOT_FOUND
from ..constants import TASK_NOT_FOUND
from ..operations.list_deals import execute_create_task
from ..operations.update_lead import execute_convert_lead
from ..operations.update_lead import execute_create_ticket
from ..operations.update_lead import execute_list_tasks
from ..operations.update_lead import execute_list_tickets
from ..operations.update_lead import execute_tasks_kanban
from ..operations.update_lead import execute_update_lead
from ..operations.update_lead import execute_update_task
from ..runtime import ContextRuntime
from ..schemas import LeadUpdateRequest
from ..schemas import TaskCreateRequest
from ..schemas import TaskUpdateRequest
from ..schemas import TicketCreateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.patch("/crm/leads/{lead_id}", responses={404: {"description": LEAD_NOT_FOUND}})
    def update_lead(lead_id: int, payload: LeadUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_update_lead(runtime, lead_id, payload, auth)

    @router.post("/crm/leads/{lead_id}/convert", responses={404: {"description": LEAD_NOT_FOUND}})
    def convert_lead(lead_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_convert_lead(runtime, lead_id, auth)

    @router.post("/crm/tasks")
    def create_task(payload: TaskCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_task(runtime, payload, auth)

    @router.get("/crm/tasks")
    def list_tasks(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        priority: Annotated[str | None, Query(max_length=20)] = None,
        assigned_to: Annotated[str | None, Query(max_length=120)] = None,
        contact_id: Annotated[int | None, Query(ge=1)] = None,
        deal_id: Annotated[int | None, Query(ge=1)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_tasks(runtime, auth, status, priority, assigned_to, contact_id, deal_id, limit, offset)

    @router.patch("/crm/tasks/{task_id}", responses={404: {"description": TASK_NOT_FOUND}})
    def update_task(task_id: int, payload: TaskUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_update_task(runtime, task_id, payload, auth)

    @router.get("/crm/tasks/kanban")
    def tasks_kanban(auth: AuthDep) -> dict[str, Any]:
        return execute_tasks_kanban(runtime, auth)

    @router.post("/crm/tickets")
    def create_ticket(payload: TicketCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_ticket(runtime, payload, auth)

    @router.get("/crm/tickets")
    def list_tickets(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        priority: Annotated[str | None, Query(max_length=20)] = None,
        channel: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_tickets(runtime, auth, status, priority, channel, limit, offset)
