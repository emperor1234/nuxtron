"""Search/Crawlers HTTP adapters beginning with cloudflare status."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.cloudflare_sync import execute_cloudflare_status
from ..operations.cloudflare_sync import execute_create_rule
from ..operations.cloudflare_sync import execute_delete_rule
from ..operations.cloudflare_sync import execute_get_audit
from ..operations.cloudflare_sync import execute_list_rules
from ..operations.cloudflare_sync import execute_list_vendors
from ..operations.cloudflare_sync import execute_run_visibility_audit
from ..operations.execute_automation_run import execute_create_automation_schedule
from ..runtime import ContextRuntime
from ..schemas import AutomationScheduleCreateRequest
from ..schemas import CrawlerRuleRequest
from ..schemas import VisibilityAuditRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/cloudflare/status")
    def cloudflare_status(auth: AuthDep, site_id: str = Query(...)) -> dict[str, Any]:
        return execute_cloudflare_status(runtime, auth, site_id)

    @router.post("/rules", status_code=201)
    def create_rule(payload: CrawlerRuleRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_rule(runtime, payload, auth)

    @router.get("/rules")
    def list_rules(auth: AuthDep, site_id: str | None = Query(default=None)) -> dict[str, Any]:
        return execute_list_rules(runtime, auth, site_id)

    @router.delete("/rules/{rule_id}")
    def delete_rule(rule_id: str, auth: AuthDep) -> dict[str, Any]:
        return execute_delete_rule(runtime, rule_id, auth)

    @router.post("/audit", status_code=201)
    def run_visibility_audit(payload: VisibilityAuditRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_run_visibility_audit(runtime, payload, auth)

    @router.get("/audit/{audit_id}")
    def get_audit(audit_id: str, auth: AuthDep) -> dict[str, Any]:
        return execute_get_audit(runtime, audit_id, auth)

    @router.get("/vendors")
    def list_vendors(auth: AuthDep, site_id: str | None = Query(default=None)) -> dict[str, Any]:
        return execute_list_vendors(runtime, auth, site_id)

    @router.post("/automation/schedules", status_code=201)
    def create_automation_schedule(payload: AutomationScheduleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_automation_schedule(runtime, payload, auth)
