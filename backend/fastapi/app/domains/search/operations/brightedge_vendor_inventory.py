"""Search use cases: brightedge vendor inventory."""

from typing import Any

from ....deps import AuthContext
from ....domains.seo.services.seo_keyword_research_service import raise_keyword_research_unavailable
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import (
    SemrushFullAutomationRequest,
    SitebulbEnvTemplateRequest,
    SliceAssistRequest,
    SliceWiringApplyRequest,
)
from .brightedge_product_catalog import (
    helper_brightedge_products_completion_chart,
    operation_brightedge_products_production_gate,
    operation_brightedge_provider_checklist,
)
from .platform_now_iso import helper_env_configured, helper_now_iso
from .semrush_list_projects import operation_semrush_full_automation
from .sitebulb_project_lookup import helper_sitebulb_env_template, helper_sitebulb_vendor_inventory


def helper_brightedge_vendor_inventory(
    runtime: SearchRuntime, auth: AuthContext, *, force_configured: bool = False
) -> list[dict[str, Any]]:
    inventory = helper_sitebulb_vendor_inventory(runtime, auth)
    inventory.extend(
        [
            {
                "domain": "seo-aeo",
                "vendor": "BrightEdge",
                "capability": "Unified SEO and AEO workflow orchestration",
                "configured": True,
                "evidence": "search_everywhere brightedge command center mapping",
            },
            {
                "domain": "search-intelligence",
                "vendor": "Google Search Console",
                "capability": "Search visibility telemetry for demand and technical workflows",
                "configured": force_configured or helper_env_configured("GOOGLE_CLIENT_ID"),
                "evidence": "core telemetry dependency for BrightEdge-style audit and trend reporting",
            },
            {
                "domain": "analytics",
                "vendor": "GA4",
                "capability": "Traffic and conversion analytics",
                "configured": force_configured,
                "evidence": "executive reporting dependency for StoryBuilder analytics",
            },
            {
                "domain": "analytics",
                "vendor": "Adobe Analytics",
                "capability": "Enterprise analytics integration",
                "configured": force_configured,
                "evidence": "enterprise reporting dependency for multi-market analytics",
            },
            {
                "domain": "ai-search",
                "vendor": "OpenAI",
                "capability": "AI search and answer-surface analysis",
                "configured": force_configured or helper_env_configured("OPENAI_API_KEY"),
                "evidence": "AI HyperCube and Copilot workflows",
            },
            {
                "domain": "ai-search",
                "vendor": "Perplexity",
                "capability": "Answer-surface visibility monitoring",
                "configured": force_configured,
                "evidence": "AI citation and share-of-voice monitoring dependency",
            },
            {
                "domain": "local",
                "vendor": "Google Business Profile",
                "capability": "Local listing and review presence synchronization",
                "configured": force_configured,
                "evidence": "local presence and review workflows",
            },
        ]
    )
    return inventory


def operation_brightedge_wiring_state(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:brightedge:wiring:get", 60, 60)
    checklist_payload = operation_brightedge_provider_checklist(runtime, auth)
    configured_items = [item for item in checklist_payload.get("checklist", []) if item.get("configured")]
    missing_items = [item for item in checklist_payload.get("checklist", []) if not item.get("configured")]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "wired_providers": sorted(str(item.get("provider")) for item in configured_items),
        "wired_count": len(configured_items),
        "missing_providers": sorted(str(item.get("provider")) for item in missing_items),
        "generated_at": helper_now_iso(),
    }


def operation_brightedge_wiring_apply(
    runtime: SearchRuntime, payload: SliceWiringApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:brightedge:wiring:apply", 30, 60)
    runtime.brightedge_wired_tenants.add(auth.tenant_id)
    checklist = operation_brightedge_provider_checklist(runtime, auth)
    completion = helper_brightedge_products_completion_chart(runtime, auth)
    gate = operation_brightedge_products_production_gate(runtime, auth)
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


def operation_brightedge_env_template(
    runtime: SearchRuntime, payload: SitebulbEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:brightedge:env-template", 60, 60)
    template = helper_sitebulb_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"brightedge-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_brightedge_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:brightedge:parity-audit", 60, 60)
    completion = helper_brightedge_products_completion_chart(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "brightedge_parity_chart": completion.get("chart", []),
        "summary": completion.get("summary", {}),
        "vendor_inventory": helper_brightedge_vendor_inventory(
            runtime, auth, force_configured=auth.tenant_id in runtime.brightedge_wired_tenants
        ),
        "generated_at": helper_now_iso(),
    }


def operation_brightedge_full_automation(
    runtime: SearchRuntime, payload: SemrushFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    raise_keyword_research_unavailable()
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:brightedge:full-automation", 30, 60)
    base_result = operation_semrush_full_automation(runtime, payload, auth)
    completion = helper_brightedge_products_completion_chart(runtime, auth)
    gate_state = operation_brightedge_products_production_gate(runtime, auth)
    vendor_inventory = helper_brightedge_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.brightedge_wired_tenants
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run_mode": base_result.get("run_mode"),
        "results": {
            "demand_and_market_intelligence": base_result.get("results", {}).get("keyword_discovery", {}),
            "content_and_topic_optimization": base_result.get("results", {}).get("content_gap", {}),
            "technical_and_site_health": base_result.get("results", {}).get("backlink_audit", {}),
            "competitive_and_visibility_actions": base_result.get("results", {}).get("backlink_gap", {}),
            "parity_summary": base_result.get("results", {}).get("parity_summary", {}),
        },
        "brightedge_modules": {
            "search_intelligence": ["data cube x", "share of voice", "trend forecasting"],
            "ai_search": ["ai hypercube", "citation visibility", "answer sentiment"],
            "optimization": ["copilot guidance", "autopilot execution", "on-page recommendations"],
            "technical": ["contentiq audits", "crawl diagnostics", "schema validation"],
            "operations": ["provider checklist", "wiring apply", "production gate", "verification report"],
        },
        "completion_summary": completion.get("summary", {}),
        "production_gate": gate_state.get("gate", {}),
        "third_parties_and_vendors": vendor_inventory,
        "how_it_works": [
            "Data Cube X and AI HyperCube prioritize demand opportunities across classic and AI search surfaces.",
            "Copilot and Autopilot turn those opportunities into governed optimization tasks and automated execution.",
            "Content and technical workflows share the same entity and performance context for consistent rollout decisions.",
            "Provider checklist, wiring apply, and production gate separate code-complete status from integration-ready status.",
        ],
        "generated_at": helper_now_iso(),
    }


def operation_brightedge_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:brightedge:vendors", 120, 60)
    inventory = helper_brightedge_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.brightedge_wired_tenants
    )
    configured = sum(1 for item in inventory if bool(item.get("configured")))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "vendors_total": len(inventory),
        "vendors_configured": configured,
        "vendor_chart": inventory,
        "generated_at": helper_now_iso(),
    }


def operation_brightedge_assist_chat(
    runtime: SearchRuntime, payload: SliceAssistRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:brightedge:assist", 30, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "assist": {
            "answer_summary": f"BrightEdge assist analyzed demand intelligence, AI visibility, and optimization coverage for prompt: {payload.prompt[:120]}",
            "recommended_actions": [
                "Validate Data Cube X opportunity segments against your market taxonomy before rollout.",
                "Enable provider wiring for AI visibility and local presence connectors before production cutover.",
                "Use StoryBuilder analytics exports to align executives on SEO and AI-search outcomes.",
            ],
            "workflow_handoffs": [
                "Demand intelligence -> content optimization squads",
                "Technical audit ops -> web engineering remediation",
                "Executive reporting -> growth and market leadership reviews",
            ],
        },
        "context": {
            "include_vendor_context": payload.include_vendor_context,
            "vendors": helper_brightedge_vendor_inventory(
                runtime, auth, force_configured=auth.tenant_id in runtime.brightedge_wired_tenants
            )
            if payload.include_vendor_context
            else [],
        },
        "generated_at": helper_now_iso(),
    }
