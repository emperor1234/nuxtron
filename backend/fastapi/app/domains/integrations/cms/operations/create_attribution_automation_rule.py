"""Integrations/Cms use cases: create attribution automation rule."""

from __future__ import annotations
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import CmsAttributionAutomationRuleRequest
from .audit import helper_audit
from datetime import UTC
from datetime import datetime
from fastapi import HTTPException
from typing import Any


def execute_create_attribution_automation_rule(
    runtime: ContextRuntime, payload: CmsAttributionAutomationRuleRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:attribution:automation-rules:create", 90, 60)
    with runtime.lock:
        rule: dict[str, Any] = {
            "id": len(runtime.cms_attribution_rules_memory) + 1,
            "tenant_id": auth.tenant_id,
            "campaign": payload.campaign,
            "trigger_event_type": payload.trigger_event_type,
            "min_value": payload.min_value,
            "auto_enroll_sequence_id": payload.auto_enroll_sequence_id,
            "create_deal": payload.create_deal,
            "deal_title": payload.deal_title,
            "deal_stage": payload.deal_stage,
            "transition_deal_stage_to": payload.transition_deal_stage_to,
            "create_followup_task": payload.create_followup_task,
            "task_title": payload.task_title,
            "task_priority": payload.task_priority,
            "task_assigned_to": payload.task_assigned_to,
            "task_due_in_days": payload.task_due_in_days,
            "enabled": payload.enabled,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        runtime.cms_attribution_rules_memory.append(rule)
    helper_audit(runtime, auth.tenant_id, "cms_attribution_automation_rule_created", rule["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "rule": rule}


def execute_delete_attribution_automation_rule(runtime: ContextRuntime, rule_id: int, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:attribution:automation-rules:delete", 90, 60)
    with runtime.lock:
        before = len(runtime.cms_attribution_rules_memory)
        runtime.cms_attribution_rules_memory[:] = [
            r
            for r in runtime.cms_attribution_rules_memory
            if not (r.get("id") == rule_id and r.get("tenant_id") == auth.tenant_id)
        ]
        removed = before - len(runtime.cms_attribution_rules_memory)
    if removed == 0:
        raise HTTPException(status_code=404, detail="Attribution automation rule not found.")
    helper_audit(runtime, auth.tenant_id, "cms_attribution_automation_rule_deleted", rule_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "removed": True, "rule_id": rule_id}


def execute_list_attribution_automation_runs(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:attribution:automation-runs:list", 180, 60)
    with runtime.lock:
        runs = [
            r.copy() for r in runtime.cms_attribution_automation_runs_memory if r.get("tenant_id") == auth.tenant_id
        ]
    runs.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(runs), "runs": runs}


def execute_attribution_report(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:cms:attribution:report", 120, 60)
    with runtime.lock:
        links = [l.copy() for l in runtime.cms_attribution_links_memory if l.get("tenant_id") == auth.tenant_id]
        events = [e.copy() for e in runtime.cms_attribution_events_memory if e.get("tenant_id") == auth.tenant_id]
    by_campaign: dict[str, dict[str, Any]] = {}
    for link in links:
        campaign = str(link.get("campaign") or "unattributed")
        if campaign not in by_campaign:
            by_campaign[campaign] = {
                "campaign": campaign,
                "links": 0,
                "visits": 0,
                "leads": 0,
                "customers": 0,
                "pipeline_value": 0.0,
                "revenue": 0.0,
            }
        by_campaign[campaign]["links"] += 1
    link_to_campaign = {int(l.get("id", 0)): str(l.get("campaign") or "unattributed") for l in links}
    for event in events:
        campaign = link_to_campaign.get(int(event.get("attribution_link_id", 0)), "unattributed")
        if campaign not in by_campaign:
            by_campaign[campaign] = {
                "campaign": campaign,
                "links": 0,
                "visits": 0,
                "leads": 0,
                "customers": 0,
                "pipeline_value": 0.0,
                "revenue": 0.0,
            }
        event_type = str(event.get("event_type") or "")
        value = float(event.get("value") or 0.0)
        if event_type == "visit":
            by_campaign[campaign]["visits"] += 1
        if event_type in {"lead", "mql", "sql", "opportunity", "customer"}:
            by_campaign[campaign]["leads"] += 1
            by_campaign[campaign]["pipeline_value"] = round(by_campaign[campaign]["pipeline_value"] + value, 2)
        if event_type == "customer":
            by_campaign[campaign]["customers"] += 1
            by_campaign[campaign]["revenue"] = round(by_campaign[campaign]["revenue"] + value, 2)
    campaigns: list[dict[str, Any]] = []
    total_visits = 0
    total_leads = 0
    total_customers = 0
    total_pipeline = 0.0
    total_revenue = 0.0
    for item in by_campaign.values():
        visits = int(item["visits"])
        leads = int(item["leads"])
        customers = int(item["customers"])
        lead_conv = round(leads / visits * 100.0, 2) if visits > 0 else 0.0
        customer_conv = round(customers / visits * 100.0, 2) if visits > 0 else 0.0
        campaign_item = {
            **item,
            "visit_to_lead_conversion_pct": lead_conv,
            "visit_to_customer_conversion_pct": customer_conv,
        }
        campaigns.append(campaign_item)
        total_visits += visits
        total_leads += leads
        total_customers += customers
        total_pipeline = round(total_pipeline + float(item["pipeline_value"]), 2)
        total_revenue = round(total_revenue + float(item["revenue"]), 2)
    campaigns.sort(key=lambda c: float(c.get("revenue", 0.0)), reverse=True)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "summary": {
            "campaigns": len(campaigns),
            "links": len(links),
            "events": len(events),
            "visits": total_visits,
            "leads": total_leads,
            "customers": total_customers,
            "pipeline_value": total_pipeline,
            "revenue": total_revenue,
            "visit_to_lead_conversion_pct": round(total_leads / total_visits * 100.0, 2) if total_visits > 0 else 0.0,
        },
        "campaigns": campaigns,
        "generated_at": datetime.now(UTC).isoformat(),
    }
