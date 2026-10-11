"""Crm HTTP adapters beginning with create company."""

from ..constants import AuthDep
from ..constants import DEAL_NOT_FOUND
from ..operations.get_live_sync_state import execute_create_company
from ..operations.get_live_sync_state import execute_create_deal
from ..operations.get_live_sync_state import execute_list_companies
from ..operations.list_deals import execute_create_activity
from ..operations.list_deals import execute_get_pipeline
from ..operations.list_deals import execute_get_summary
from ..operations.list_deals import execute_list_deals
from ..operations.list_deals import execute_update_deal
from ..runtime import ContextRuntime
from ..schemas import ActivityCreateRequest
from ..schemas import CompanyCreateRequest
from ..schemas import DealCreateRequest
from ..schemas import DealUpdateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/crm/companies")
    def create_company(payload: CompanyCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_company(runtime, payload, auth)

    @router.get("/crm/companies")
    def list_companies(
        auth: AuthDep,
        q: Annotated[str | None, Query(max_length=160)] = None,
        industry: Annotated[str | None, Query(max_length=80)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_companies(runtime, auth, q, industry, limit, offset)

    @router.post("/crm/deals")
    def create_deal(payload: DealCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_deal(runtime, payload, auth)

    @router.get("/crm/deals")
    def list_deals(
        auth: AuthDep,
        q: Annotated[str | None, Query(max_length=180)] = None,
        stage: Annotated[str | None, Query(max_length=60)] = None,
        min_value: Annotated[float, Query(ge=0.0)] = 0.0,
        max_value: Annotated[float | None, Query(ge=0.0)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_deals(runtime, auth, q, stage, min_value, max_value, limit, offset)

    @router.patch("/crm/deals/{deal_id}", responses={404: {"description": DEAL_NOT_FOUND}})
    def update_deal(deal_id: int, payload: DealUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_update_deal(runtime, deal_id, payload, auth)

    @router.get("/crm/pipeline")
    def get_pipeline(auth: AuthDep) -> dict[str, Any]:
        return execute_get_pipeline(runtime, auth)

    @router.get("/crm/summary")
    def get_summary(auth: AuthDep) -> dict[str, Any]:
        return execute_get_summary(runtime, auth)

    @router.post("/crm/activities")
    def create_activity(payload: ActivityCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_activity(runtime, payload, auth)
