"""Assistant use cases: ira list ab tests."""

from ..constants import AuthDep
from ..constants import DEFAULT_BLOCKED_ACTIONS
from ..runtime import ContextRuntime
from ..schemas import IRAAutonomyUpdateRequest
from ..schemas import IRAConnectorUpsertRequest
from ..schemas import IRACrmGovernanceUpdateRequest
from ..schemas import IRAFeedbackRequest
from ..schemas import IRAFinanceSampleRequest
from ..services.reasoning_support import _now_iso
from .db_dsn import helper_append_ira_event
from .db_dsn import helper_audit
from .db_dsn import helper_default_crm_governance_map
from .db_dsn import helper_get_or_create_connector
from .db_dsn import helper_get_or_create_control
from .db_dsn import helper_load_crm_governance
from .db_dsn import helper_persist_crm_governance_row
from .db_dsn import helper_probe_crm_connectors
from .db_dsn import helper_require_super_admin_for_control
from fastapi import HTTPException
from fastapi import Header
from typing import Annotated
from typing import Any


def execute_ira_list_ab_tests(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """List all A/B tests for this tenant with computed winner analysis."""
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:abtest:list", 120, 60)
    tests = [t for t in context_runtime.ira_ab_tests_memory if t.get("tenant_id") == auth.tenant_id]
    enriched: list[dict[str, Any]] = []
    for test in tests:
        analysis: dict[str, Any] = {"winner": None, "confidence": 0.0, "by_variant": {}}
        best_rate = -1.0
        for variant, stats in test.get("results", {}).items():
            impressions = int(stats.get("impressions", 0))
            successes = int(stats.get("successes", 0))
            rate = round(successes / impressions, 4) if impressions else 0.0
            avg_value = round(float(stats.get("total_value", 0)) / impressions, 4) if impressions else 0.0
            analysis["by_variant"][variant] = {"impressions": impressions, "success_rate": rate, "avg_value": avg_value}
            if rate > best_rate:
                best_rate = rate
                analysis["winner"] = variant
                rates = [s.get("successes", 0) / max(s.get("impressions", 1), 1) for s in test["results"].values()]
                rates_sorted = sorted(rates, reverse=True)
                gap = rates_sorted[0] - rates_sorted[1] if len(rates_sorted) > 1 else 0.0
                analysis["confidence"] = round(min(gap * 10 + 0.5, 1.0), 3)
        enriched.append({**test, "analysis": analysis})
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "total": len(tests),
        "tests": sorted(enriched, key=lambda t: t.get("created_at", ""), reverse=True),
    }


def execute_update_ira_control(
    context_runtime: ContextRuntime,
    payload: IRAAutonomyUpdateRequest,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:control", 60, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id)
        helper_require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail="IRA control updates are restricted to super admin sessions.",
        )
        if not payload.policy_change_human_validation:
            raise HTTPException(status_code=422, detail="Policy updates require human validation confirmation.")
        strict_policy_lock = bool(control.get("strict_policy_lock", True))
        if strict_policy_lock:
            if payload.allow_high_impact_actions:
                raise HTTPException(
                    status_code=422, detail="Strict policy lock prevents enabling high-impact autonomous actions."
                )
            if not payload.require_super_admin:
                raise HTTPException(
                    status_code=422, detail="Strict policy lock prevents disabling super-admin requirement."
                )
        control["autonomy_enabled"] = payload.autonomy_enabled
        control["allow_high_impact_actions"] = payload.allow_high_impact_actions
        control["min_profit_margin_pct"] = payload.min_profit_margin_pct
        control["suspicious_signal_threshold"] = payload.suspicious_signal_threshold
        control["require_super_admin"] = payload.require_super_admin
        control["max_dispute_auto_resolution_gbp"] = payload.max_dispute_auto_resolution_gbp
        control["strict_policy_lock"] = payload.strict_policy_lock
        control["updated_at"] = _now_iso()
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "control_updated",
        {
            "autonomy_enabled": payload.autonomy_enabled,
            "allow_high_impact_actions": payload.allow_high_impact_actions,
            "min_profit_margin_pct": payload.min_profit_margin_pct,
            "suspicious_signal_threshold": payload.suspicious_signal_threshold,
            "require_super_admin": payload.require_super_admin,
            "max_dispute_auto_resolution_gbp": payload.max_dispute_auto_resolution_gbp,
            "strict_policy_lock": payload.strict_policy_lock,
        },
    )
    helper_audit(context_runtime, auth.tenant_id, "ira_control_updated", {"event_id": event["id"]})
    return {"status": "ok", "tenant_id": auth.tenant_id, "control": control, "event_id": event["id"]}


def execute_upsert_ira_connector(
    context_runtime: ContextRuntime,
    payload: IRAConnectorUpsertRequest,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:connectors:upsert", 60, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id)
        helper_require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail="IRA connector updates are restricted to super admin sessions.",
        )
        connector = helper_get_or_create_connector(context_runtime, auth.tenant_id, payload.channel)
        connector["enabled"] = payload.enabled
        connector["provider"] = payload.provider
        connector["config"] = payload.config
        connector["updated_at"] = _now_iso()
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "connector_updated",
        {"channel": payload.channel, "enabled": payload.enabled, "provider": payload.provider},
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_connector_updated",
        {"event_id": event["id"], "channel": payload.channel, "enabled": payload.enabled},
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "connector": connector, "event_id": event["id"]}


def execute_ira_ingest_finance_sample(
    context_runtime: ContextRuntime, payload: IRAFinanceSampleRequest, auth: AuthDep
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:finance:ingest", 120, 60)
    control = helper_get_or_create_control(context_runtime, auth.tenant_id)
    total_cost = payload.cogs + payload.credits_cost
    profit_margin_pct = (
        0.0 if payload.revenue <= 0 else round((payload.revenue - total_cost) / payload.revenue * 100.0, 2)
    )
    below_profit_target = profit_margin_pct < float(control.get("min_profit_margin_pct", 70.0))
    suspicious = payload.suspicious_signal_score >= float(control.get("suspicious_signal_threshold", 0.75))
    sample_event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "finance_sample_ingested",
        {
            "revenue": payload.revenue,
            "cogs": payload.cogs,
            "credits_cost": payload.credits_cost,
            "profit_margin_pct": profit_margin_pct,
            "suspicious_signal_score": payload.suspicious_signal_score,
            "note": payload.note,
        },
    )
    activation_event = None
    if below_profit_target or suspicious:
        control["protection_mode"] = True
        control["blocked_actions"] = list(DEFAULT_BLOCKED_ACTIONS)
        control["updated_at"] = _now_iso()
        activation_event = helper_append_ira_event(
            context_runtime,
            auth.tenant_id,
            "protection_mode_activated",
            {
                "reason": "profit_below_target" if below_profit_target else "suspicious_signal",
                "blocked_actions": control["blocked_actions"],
                "metrics": {
                    "profit_margin_pct": profit_margin_pct,
                    "min_profit_margin_pct": control.get("min_profit_margin_pct", 70.0),
                    "suspicious_signal_score": payload.suspicious_signal_score,
                    "suspicious_signal_threshold": control.get("suspicious_signal_threshold", 0.75),
                },
            },
        )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_finance_sample_ingested",
        {
            "event_id": sample_event["id"],
            "profit_margin_pct": profit_margin_pct,
            "protection_mode": bool(control.get("protection_mode", False)),
        },
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "profit_margin_pct": profit_margin_pct,
        "below_profit_target": below_profit_target,
        "suspicious_signal": suspicious,
        "protection_mode": bool(control.get("protection_mode", False)),
        "activation_event_id": activation_event["id"] if activation_event else None,
    }


def execute_disable_protection_mode(
    context_runtime: ContextRuntime,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:control:disable-protection", 30, 60)
    control = helper_get_or_create_control(context_runtime, auth.tenant_id)
    helper_require_super_admin_for_control(
        control=control,
        x_super_admin_key=x_super_admin_key,
        detail="Disabling IRA protection mode is restricted to super admin sessions.",
    )
    control["protection_mode"] = False
    control["blocked_actions"] = []
    control["updated_at"] = _now_iso()
    event = helper_append_ira_event(context_runtime, auth.tenant_id, "protection_mode_disabled", {})
    helper_audit(context_runtime, auth.tenant_id, "ira_protection_mode_disabled", {"event_id": event["id"]})
    return {"status": "ok", "tenant_id": auth.tenant_id, "protection_mode": False, "event_id": event["id"]}


def execute_collect_ira_feedback(
    context_runtime: ContextRuntime, payload: IRAFeedbackRequest, auth: AuthDep
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:learning:feedback", 180, 60)
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "learning_feedback_collected",
        {
            "category": payload.category,
            "rating": payload.rating,
            "comment": payload.comment,
            "action_ref": payload.action_ref,
            "actor_role": payload.actor_role,
        },
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_learning_feedback_collected",
        {"event_id": event["id"], "category": payload.category, "rating": payload.rating},
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "event_id": event["id"]}


def execute_ira_disputes_dashboard(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:disputes:dashboard", 120, 60)
    relevant_events = [
        item
        for item in context_runtime.ira_events_memory
        if item.get("tenant_id") == auth.tenant_id
        and (
            "dispute" in str(item.get("event_type", "")).lower()
            or bool(item.get("payload", {}).get("is_dispute", False))
        )
    ]
    dispute_tickets = [
        item
        for item in context_runtime.tickets_memory
        if item.get("tenant_id") == auth.tenant_id
        and ("dispute" in str(item.get("subject", "")).lower() or "dispute" in str(item.get("description", "")).lower())
    ]
    open_items = [
        item
        for item in dispute_tickets
        if str(item.get("status", "")).lower() in {"open", "queued_for_human_validation"}
    ]
    queued_items = [
        item for item in dispute_tickets if str(item.get("status", "")).lower() == "queued_for_human_validation"
    ]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "summary": {
            "total_dispute_events": len(relevant_events),
            "total_dispute_tickets": len(dispute_tickets),
            "open_dispute_tickets": len(open_items),
            "queued_for_human_validation": len(queued_items),
            "human_approval_required_for_all_disputes": True,
        },
        "tickets": dispute_tickets[-50:],
        "recent_dispute_events": relevant_events[-50:],
        "reputation_guardrail": "Use fair, transparent, and non-coercive retention guidance before any refund refusal path.",
    }


def execute_ira_crm_hybrid_recommendation(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:crm:hybrid-recommendation", 60, 60)
    control = helper_get_or_create_control(context_runtime, auth.tenant_id)
    governance = control.get("crm_feature_governance")
    if not isinstance(governance, dict):
        governance = helper_default_crm_governance_map()
        control["crm_feature_governance"] = governance
    connector_health = helper_probe_crm_connectors()
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "target": "PostgreSQL-based, open-source, SaaS-friendly CRM with maximum coverage",
        "recommended_hybrid": "Corteza CRM + Odoo CRM Community",
        "ratings": {
            "corteza_overall": {"score": 90, "percent": 90},
            "odoo_community_overall": {"score": 88, "percent": 88},
            "hybrid_overall": {"score": 95, "percent": 95},
        },
        "hybrid_dimensions": {
            "core_crm_sales": {"score": 96, "percent": 96},
            "saas_architecture_fit": {"score": 97, "percent": 97},
            "postgresql_alignment": {"score": 100, "percent": 100},
            "automation_workflows": {"score": 95, "percent": 95},
            "integrations_extensibility": {"score": 96, "percent": 96},
            "security_governance": {"score": 94, "percent": 94},
            "operational_complexity": {"score": 82, "percent": 82},
        },
        "platform_integration": {
            "required_stack": ["PostgreSQL", "Keycloak", "Kong", "WAF", "SIEM"],
            "recommendation": "Use Corteza for multi-tenant core and low-code objects; use Odoo for sales/ERP-adjacent modules.",
            "connector_health": connector_health,
        },
        "duplication_governance": {
            "policy": "Keep one source-of-truth per feature and disable duplicates in secondary system via configuration.",
            "ownership": governance,
        },
    }


def execute_update_crm_feature_governance(
    context_runtime: ContextRuntime,
    payload: IRACrmGovernanceUpdateRequest,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:crm:feature-governance", 60, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id)
        helper_require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail="CRM feature governance updates are restricted to super admin sessions.",
        )
        if not payload.policy_change_human_validation:
            raise HTTPException(
                status_code=422, detail="CRM governance policy updates require human validation confirmation."
            )
        if bool(control.get("strict_policy_lock", True)) and (not payload.disable_duplicate_in_secondary):
            raise HTTPException(
                status_code=422,
                detail="Strict policy lock requires duplicate features to stay disabled in secondary system.",
            )
        governance = helper_load_crm_governance(context_runtime, auth.tenant_id, control)
        row: dict[str, Any] = {
            "feature": payload.feature,
            "owner": payload.owner,
            "duplicate_disabled": payload.disable_duplicate_in_secondary,
            "secondary_disabled_for": "odoo" if payload.owner == "corteza" else "corteza",
            "notes": payload.notes,
            "updated_at": _now_iso(),
        }
        governance[payload.feature] = row
        control["crm_feature_governance"] = governance
        helper_persist_crm_governance_row(context_runtime, auth.tenant_id, row)
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "crm_feature_governance_updated",
        {
            "feature": payload.feature,
            "owner": payload.owner,
            "duplicate_disabled": payload.disable_duplicate_in_secondary,
            "notes": payload.notes,
        },
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_crm_feature_governance_updated",
        {"event_id": event["id"], "feature": payload.feature},
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "governance": control.get("crm_feature_governance", {}),
        "event_id": event["id"],
    }
