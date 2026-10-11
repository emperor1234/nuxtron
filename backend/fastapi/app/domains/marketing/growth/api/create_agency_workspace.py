"""Marketing/Growth HTTP adapters beginning with create agency workspace."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.growth_suite_bootstrap import execute_add_agency_member
from ..operations.growth_suite_bootstrap import execute_add_agency_mrr
from ..operations.growth_suite_bootstrap import execute_agency_overview
from ..operations.growth_suite_bootstrap import execute_analyze_audience
from ..operations.growth_suite_bootstrap import execute_create_ads_draft
from ..operations.growth_suite_bootstrap import execute_create_agency_workspace
from ..operations.growth_suite_bootstrap import execute_ira_health_check
from ..operations.growth_suite_bootstrap import execute_repurpose_content
from ..runtime import ContextRuntime
from ..schemas import AdsDraftRequest
from ..schemas import AgencyMemberRequest
from ..schemas import AgencyMrrRequest
from ..schemas import AgencyWorkspaceRequest
from ..schemas import AudienceDnaRequest
from ..schemas import IraBrainRequest
from ..schemas import RepurposeRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/agency/workspaces")
    def create_agency_workspace(payload: AgencyWorkspaceRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_agency_workspace(runtime, payload, auth)

    @router.post(
        "/agency/workspaces/{workspace_key}/members", responses={404: {"description": "Agency workspace not found."}}
    )
    def add_agency_member(workspace_key: str, payload: AgencyMemberRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_add_agency_member(runtime, workspace_key, payload, auth)

    @router.post(
        "/agency/workspaces/{workspace_key}/mrr", responses={404: {"description": "Agency workspace not found."}}
    )
    def add_agency_mrr(workspace_key: str, payload: AgencyMrrRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_add_agency_mrr(runtime, workspace_key, payload, auth)

    @router.get("/agency/overview")
    def agency_overview(auth: AuthDep) -> dict[str, Any]:
        return execute_agency_overview(runtime, auth)

    @router.post("/audience-dna/analyze")
    def analyze_audience(payload: AudienceDnaRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_analyze_audience(runtime, payload, auth)

    @router.post("/ira/autonomous-brain/health-check")
    def ira_health_check(payload: IraBrainRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_health_check(runtime, payload, auth)

    @router.post("/ads/campaigns/draft")
    def create_ads_draft(payload: AdsDraftRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_ads_draft(runtime, payload, auth)

    @router.post("/content/repurpose")
    def repurpose_content(payload: RepurposeRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_repurpose_content(runtime, payload, auth)
