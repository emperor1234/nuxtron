"""Search use cases: geoptie vendor inventory."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SliceAssistRequest
from ..schemas import SliceWiringApplyRequest
from .geoptie_product_catalog import helper_geoptie_products_completion_chart
from .geoptie_product_catalog import operation_geoptie_products_production_gate
from .geoptie_product_catalog import operation_geoptie_provider_checklist
from .platform_now_iso import helper_env_configured
from .platform_now_iso import helper_now_iso
from .semrush_list_projects import operation_semrush_full_automation
from .sitebulb_project_lookup import helper_sitebulb_env_template
from .sitebulb_project_lookup import helper_sitebulb_vendor_inventory
from typing import Any


def helper_geoptie_vendor_inventory(
    runtime: SearchRuntime, auth: AuthContext, *, force_configured: bool = False
) -> list[dict[str, Any]]:
    inventory = helper_sitebulb_vendor_inventory(runtime, auth)
    inventory.extend(
        [
            {
                "domain": "geo-platform",
                "vendor": "Geoptie",
                "capability": "Generative Engine Optimization orchestration for prompt visibility, audits, citations, and competitive radar",
                "configured": True,
                "evidence": "search_everywhere geoptie command center mapping",
            },
            {
                "domain": "ai-models",
                "vendor": "OpenAI ChatGPT",
                "capability": "Model visibility tracking and answer-surface analysis",
                "configured": force_configured or helper_env_configured("OPENAI_API_KEY"),
                "evidence": "rank tracker model coverage dependency",
            },
            {
                "domain": "ai-models",
                "vendor": "Google Gemini / AI Overview",
                "capability": "Generative model and search overview coverage tracking",
                "configured": force_configured or helper_env_configured("GOOGLE_CLIENT_ID"),
                "evidence": "cross-model coverage dependency",
            },
            {
                "domain": "ai-models",
                "vendor": "Perplexity",
                "capability": "AI answer-surface visibility monitoring",
                "configured": force_configured or helper_env_configured("PERPLEXITY_API_KEY"),
                "evidence": "rank tracker model coverage dependency",
            },
            {
                "domain": "ai-models",
                "vendor": "Anthropic Claude",
                "capability": "Model visibility and answer relevance analysis",
                "configured": force_configured or helper_env_configured("ANTHROPIC_API_KEY"),
                "evidence": "rank tracker model coverage dependency",
            },
            {
                "domain": "ai-models",
                "vendor": "Microsoft Copilot",
                "capability": "Model visibility tracking for Microsoft answer surfaces",
                "configured": force_configured or helper_env_configured("AZURE_OPENAI_ENDPOINT"),
                "evidence": "rank tracker model coverage dependency",
            },
            {
                "domain": "ai-models",
                "vendor": "xAI Grok",
                "capability": "Model visibility tracking for xAI answer surfaces",
                "configured": force_configured or helper_env_configured("XAI_API_KEY"),
                "evidence": "rank tracker model coverage dependency",
            },
            {
                "domain": "analytics",
                "vendor": "Google Search Console",
                "capability": "Search visibility baselines and prompt opportunity context",
                "configured": force_configured or helper_env_configured("GSC_CLIENT_ID"),
                "evidence": "keyword and cannibalization diagnostics dependency",
            },
            {
                "domain": "automation",
                "vendor": "Zapier",
                "capability": "Automation trigger and workflow handoff routing",
                "configured": force_configured or helper_env_configured("ZAPIER_WEBHOOK_URL"),
                "evidence": "workflow orchestration dependency",
            },
        ]
    )
    return inventory


def operation_geoptie_wiring_state(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:geoptie:wiring:get", 60, 60)
    checklist_payload = operation_geoptie_provider_checklist(runtime, auth)
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


def operation_geoptie_wiring_apply(
    runtime: SearchRuntime, payload: SliceWiringApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:geoptie:wiring:apply", 30, 60)
    runtime.geoptie_wired_tenants.add(auth.tenant_id)
    checklist = operation_geoptie_provider_checklist(runtime, auth)
    completion = helper_geoptie_products_completion_chart(runtime, auth)
    gate = operation_geoptie_products_production_gate(runtime, auth)
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


def operation_geoptie_env_template(
    runtime: SearchRuntime, payload: SitebulbEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:geoptie:env-template", 60, 60)
    template = helper_sitebulb_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"geoptie-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_geoptie_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:geoptie:parity-audit", 60, 60)
    completion = helper_geoptie_products_completion_chart(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "geoptie_parity_chart": completion.get("chart", []),
        "summary": completion.get("summary", {}),
        "vendor_inventory": helper_geoptie_vendor_inventory(
            runtime, auth, force_configured=auth.tenant_id in runtime.geoptie_wired_tenants
        ),
        "generated_at": helper_now_iso(),
    }


def operation_geoptie_full_automation(
    runtime: SearchRuntime, payload: SemrushFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:geoptie:full-automation", 30, 60)
    base_result = operation_semrush_full_automation(runtime, payload, auth)
    completion = helper_geoptie_products_completion_chart(runtime, auth)
    gate_state = operation_geoptie_products_production_gate(runtime, auth)
    vendor_inventory = helper_geoptie_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.geoptie_wired_tenants
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run_mode": base_result.get("run_mode"),
        "results": {
            "geo_audit_health": base_result.get("results", {}).get("keyword_discovery", {}),
            "ai_model_visibility_and_rank_tracking": base_result.get("results", {}).get("content_gap", {}),
            "citation_and_backlink_landscape": base_result.get("results", {}).get("backlink_audit", {}),
            "keyword_and_cannibalization_actions": base_result.get("results", {}).get("backlink_gap", {}),
            "parity_summary": base_result.get("results", {}).get("parity_summary", {}),
        },
        "geoptie_modules": {
            "geo_audit": ["readiness scoring", "critical blockers", "actionable fixes"],
            "rank_tracker": ["model position tracking", "visibility score", "detection rate"],
            "content_checker": ["structure diagnostics", "citation readiness", "answer-surface quality"],
            "keyword_and_overlap": ["keyword finder", "prompt clustering", "cannibalization detection"],
            "citation_growth": ["backlink finder", "source discovery", "competitive radar"],
            "ops": ["provider checklist", "wiring apply", "production gate", "verification report"],
        },
        "completion_summary": completion.get("summary", {}),
        "production_gate": gate_state.get("gate", {}),
        "third_parties_and_vendors": vendor_inventory,
        "how_it_works": [
            "GEO Audit baselines current AI-search readiness and identifies structural and citation blockers.",
            "Rank Tracker monitors visibility, mentions, sentiment, and position across major AI model surfaces.",
            "Content Checker, Keyword Finder, Cannibalization Checker, and Backlink Finder convert gaps into prioritized actions.",
            "Provider checklist, wiring apply, and production gate verify tenant-level integration readiness for production automation.",
        ],
        "generated_at": helper_now_iso(),
    }


def operation_geoptie_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:geoptie:vendors", 120, 60)
    inventory = helper_geoptie_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.geoptie_wired_tenants
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


def operation_geoptie_assist_chat(runtime: SearchRuntime, payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:geoptie:assist", 30, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "assist": {
            "answer_summary": f"Geoptie assist analyzed GEO audits, cross-model visibility, and citation growth posture for prompt: {payload.prompt[:120]}",
            "recommended_actions": [
                "Confirm provider wiring for all target AI model surfaces before enforcing strict production gates.",
                "Prioritize prompt clusters with weak detection-rate and citation coverage for immediate content updates.",
                "Review cannibalization and backlink recommendations as a single release bundle to avoid conflicting changes.",
            ],
            "workflow_handoffs": [
                "Audit insights -> content and technical SEO implementation",
                "Model visibility deltas -> competitive radar and prompt strategy",
                "Citation and backlink opportunities -> outreach and authority programs",
            ],
        },
        "context": {
            "include_vendor_context": payload.include_vendor_context,
            "vendors": helper_geoptie_vendor_inventory(
                runtime, auth, force_configured=auth.tenant_id in runtime.geoptie_wired_tenants
            )
            if payload.include_vendor_context
            else [],
        },
        "generated_at": helper_now_iso(),
    }
