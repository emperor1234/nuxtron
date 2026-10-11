"""Search use cases: marketmuse vendor inventory."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SliceAssistRequest
from ..schemas import SliceWiringApplyRequest
from .marketmuse_product_catalog import helper_marketmuse_products_completion_chart
from .marketmuse_product_catalog import operation_marketmuse_products_production_gate
from .marketmuse_product_catalog import operation_marketmuse_provider_checklist
from .platform_now_iso import helper_env_configured
from .platform_now_iso import helper_now_iso
from .semrush_list_projects import operation_semrush_full_automation
from .sitebulb_project_lookup import helper_sitebulb_env_template
from .sitebulb_project_lookup import helper_sitebulb_vendor_inventory
from typing import Any


def helper_marketmuse_vendor_inventory(
    runtime: SearchRuntime, auth: AuthContext, *, force_configured: bool = False
) -> list[dict[str, Any]]:
    inventory = helper_sitebulb_vendor_inventory(runtime, auth)
    inventory.extend(
        [
            {
                "domain": "content-strategy",
                "vendor": "MarketMuse",
                "capability": "AI-native content strategy, inventory scoring, and topical authority workflow orchestration",
                "configured": True,
                "evidence": "search_everywhere marketmuse command center mapping",
            },
            {
                "domain": "content-strategy",
                "vendor": "Google Search Console",
                "capability": "Query and page performance telemetry for inventory and optimization prioritization",
                "configured": force_configured or helper_env_configured("GSC_CLIENT_ID"),
                "evidence": "inventory and optimization telemetry dependency",
            },
            {
                "domain": "analytics",
                "vendor": "GA4",
                "capability": "Traffic and conversion outcomes for content strategy reporting",
                "configured": force_configured or helper_env_configured("GA4_PROPERTY_ID"),
                "evidence": "performance attribution dependency for inventory and optimization",
            },
            {
                "domain": "ai-content",
                "vendor": "OpenAI",
                "capability": "Semantic topic modeling and brief synthesis acceleration",
                "configured": force_configured or helper_env_configured("OPENAI_API_KEY"),
                "evidence": "research and brief generation dependency",
            },
            {
                "domain": "ai-content",
                "vendor": "Anthropic",
                "capability": "Reasoning and quality validation for content recommendations",
                "configured": force_configured or helper_env_configured("ANTHROPIC_API_KEY"),
                "evidence": "research and recommendation quality dependency",
            },
            {
                "domain": "publishing",
                "vendor": "WordPress",
                "capability": "CMS publishing and optimization rollout target",
                "configured": force_configured or helper_env_configured("WORDPRESS_API_URL"),
                "evidence": "optimize workflow deployment dependency",
            },
            {
                "domain": "automation",
                "vendor": "Zapier",
                "capability": "Automation triggers and cross-system orchestration handoffs",
                "configured": force_configured or helper_env_configured("ZAPIER_WEBHOOK_URL"),
                "evidence": "applications workflow automation dependency",
            },
        ]
    )
    return inventory


def operation_marketmuse_wiring_state(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:marketmuse:wiring:get", 60, 60)
    checklist_payload = operation_marketmuse_provider_checklist(runtime, auth)
    configured_items = [item for item in checklist_payload.get("checklist", []) if item.get("configured")]
    missing_items = [item for item in checklist_payload.get("checklist", []) if not item.get("configured")]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "wired_providers": sorted((str(item.get("provider")) for item in configured_items)),
        "wired_count": len(configured_items),
        "missing_providers": sorted((str(item.get("provider")) for item in missing_items)),
        "generated_at": helper_now_iso(),
    }


def operation_marketmuse_wiring_apply(
    runtime: SearchRuntime, payload: SliceWiringApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:marketmuse:wiring:apply", 30, 60)
    runtime.marketmuse_wired_tenants.add(auth.tenant_id)
    checklist = operation_marketmuse_provider_checklist(runtime, auth)
    completion = helper_marketmuse_products_completion_chart(runtime, auth)
    gate = operation_marketmuse_products_production_gate(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "applied": {
            "providers_requested": sorted(set(payload.providers)),
            "include_all_missing": payload.include_all_missing,
            "include_optional_auth": payload.include_optional_auth,
        },
        "checklist_summary": {
            "configured": checklist.get("configured", 0),
            "total": checklist.get("total", 0),
            "configured_pct": checklist.get("configured_pct", 100.0),
        },
        "completion_summary": completion.get("summary", {}),
        "gate": gate.get("gate", {}),
        "generated_at": helper_now_iso(),
    }


def operation_marketmuse_env_template(
    runtime: SearchRuntime, payload: SitebulbEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:marketmuse:env-template", 60, 60)
    template = helper_sitebulb_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"marketmuse-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_marketmuse_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:marketmuse:parity-audit", 60, 60)
    completion = helper_marketmuse_products_completion_chart(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "marketmuse_parity_chart": completion.get("chart", []),
        "summary": completion.get("summary", {}),
        "vendor_inventory": helper_marketmuse_vendor_inventory(
            runtime, auth, force_configured=auth.tenant_id in runtime.marketmuse_wired_tenants
        ),
        "generated_at": helper_now_iso(),
    }


def operation_marketmuse_full_automation(
    runtime: SearchRuntime, payload: SemrushFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:marketmuse:full-automation", 30, 60)
    base_result = operation_semrush_full_automation(runtime, payload, auth)
    completion = helper_marketmuse_products_completion_chart(runtime, auth)
    gate_state = operation_marketmuse_products_production_gate(runtime, auth)
    vendor_inventory = helper_marketmuse_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.marketmuse_wired_tenants
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run_mode": base_result.get("run_mode"),
        "results": {
            "inventory_and_authority_scoring": base_result.get("results", {}).get("keyword_discovery", {}),
            "research_and_topic_modeling": base_result.get("results", {}).get("content_gap", {}),
            "competitive_and_gap_analysis": base_result.get("results", {}).get("backlink_audit", {}),
            "optimization_execution_plan": base_result.get("results", {}).get("backlink_gap", {}),
            "parity_summary": base_result.get("results", {}).get("parity_summary", {}),
        },
        "marketmuse_modules": {
            "inventory": ["authority baseline", "content scoring", "refresh queue"],
            "research": ["topic model", "entity mapping", "semantic opportunities"],
            "briefs": ["outline generation", "coverage targets", "editorial handoff"],
            "optimize": ["score improvement", "inline recommendations", "publish readiness"],
            "competitive_analysis": ["authority benchmark", "topic share", "displacement plan"],
            "applications": ["provider checklist", "wiring apply", "production gate", "verification report"],
        },
        "completion_summary": completion.get("summary", {}),
        "production_gate": gate_state.get("gate", {}),
        "third_parties_and_vendors": vendor_inventory,
        "how_it_works": [
            "Inventory creates authority and quality baselines across existing content so teams can prioritize updates.",
            "Research and Briefs convert topic and entity gaps into production-ready writing plans and outlines.",
            "Optimize and Competitive Analysis apply recommendations and benchmark progress against direct competitors.",
            "Provider checklist, wiring apply, and production gate verify tenant-level readiness before production execution.",
        ],
        "generated_at": helper_now_iso(),
    }


def operation_marketmuse_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:marketmuse:vendors", 120, 60)
    inventory = helper_marketmuse_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.marketmuse_wired_tenants
    )
    configured = sum((1 for item in inventory if bool(item.get("configured"))))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "vendors_total": len(inventory),
        "vendors_configured": configured,
        "vendor_chart": inventory,
        "generated_at": helper_now_iso(),
    }


def operation_marketmuse_assist_chat(
    runtime: SearchRuntime, payload: SliceAssistRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:marketmuse:assist", 30, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "assist": {
            "answer_summary": f"MarketMuse assist analyzed inventory, research, briefs, and optimization posture for prompt: {payload.prompt[:120]}",
            "recommended_actions": [
                "Apply provider wiring before enforcing strict production gates for content strategy automations.",
                "Prioritize inventory pages with the lowest authority scores and highest opportunity deltas.",
                "Bundle brief and optimize recommendations into release cohorts to reduce editorial churn.",
            ],
            "workflow_handoffs": [
                "Inventory and research outputs -> editorial brief creation",
                "Briefs and optimize signals -> CMS publishing and QA",
                "Competitive deltas -> sprint planning and roadmap prioritization",
            ],
        },
        "context": {
            "include_vendor_context": payload.include_vendor_context,
            "vendors": helper_marketmuse_vendor_inventory(
                runtime, auth, force_configured=auth.tenant_id in runtime.marketmuse_wired_tenants
            )
            if payload.include_vendor_context
            else [],
        },
        "generated_at": helper_now_iso(),
    }
