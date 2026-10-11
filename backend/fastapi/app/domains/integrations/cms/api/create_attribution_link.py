"""Integrations/Cms HTTP adapters beginning with create attribution link."""

from __future__ import annotations
from ..constants import AuthDep
from ..constants import CMS_CONNECTION_NOT_FOUND
from ..operations.audit import execute_create_attribution_link
from ..operations.audit import execute_list_attribution_automation_rules
from ..operations.audit import execute_list_attribution_links
from ..operations.create_attribution_automation_rule import execute_attribution_report
from ..operations.create_attribution_automation_rule import execute_create_attribution_automation_rule
from ..operations.create_attribution_automation_rule import execute_delete_attribution_automation_rule
from ..operations.create_attribution_automation_rule import execute_list_attribution_automation_runs
from ..operations.ingest_attribution_event import execute_ingest_attribution_event
from ..runtime import ContextRuntime
from ..schemas import CmsAttributionAutomationRuleRequest
from ..schemas import CmsAttributionEventRequest
from ..schemas import CmsAttributionLinkRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/cms/attribution/links", responses={404: {"description": CMS_CONNECTION_NOT_FOUND}})
    def create_attribution_link(payload: CmsAttributionLinkRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_attribution_link(runtime, payload, auth)

    @router.get("/cms/attribution/links")
    def list_attribution_links(auth: AuthDep) -> dict[str, Any]:
        return execute_list_attribution_links(runtime, auth)

    @router.post("/cms/attribution/automation-rules")
    def create_attribution_automation_rule(
        payload: CmsAttributionAutomationRuleRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_create_attribution_automation_rule(runtime, payload, auth)

    @router.get("/cms/attribution/automation-rules")
    def list_attribution_automation_rules(auth: AuthDep) -> dict[str, Any]:
        return execute_list_attribution_automation_rules(runtime, auth)

    @router.delete(
        "/cms/attribution/automation-rules/{rule_id}",
        responses={404: {"description": "Attribution automation rule not found."}},
    )
    def delete_attribution_automation_rule(rule_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_delete_attribution_automation_rule(runtime, rule_id, auth)

    @router.get("/cms/attribution/automation-runs")
    def list_attribution_automation_runs(auth: AuthDep) -> dict[str, Any]:
        return execute_list_attribution_automation_runs(runtime, auth)

    @router.post("/cms/attribution/events", responses={404: {"description": "Attribution link not found."}})
    def ingest_attribution_event(payload: CmsAttributionEventRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ingest_attribution_event(runtime, payload, auth)

    @router.get("/cms/attribution/report")
    def attribution_report(auth: AuthDep) -> dict[str, Any]:
        return execute_attribution_report(runtime, auth)
