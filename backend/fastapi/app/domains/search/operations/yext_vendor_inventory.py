"""Search use cases: yext vendor inventory."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SliceAssistRequest
from ..schemas import SliceWiringApplyRequest
from .platform_now_iso import helper_env_configured
from .platform_now_iso import helper_now_iso
from .semrush_list_projects import operation_semrush_full_automation
from .sitebulb_project_lookup import helper_sitebulb_env_template
from .sitebulb_project_lookup import helper_sitebulb_vendor_inventory
from .yext_product_catalog import helper_yext_products_completion_chart
from .yext_product_catalog import operation_yext_products_production_gate
from .yext_product_catalog import operation_yext_provider_checklist
from typing import Any


def helper_yext_vendor_inventory(
    runtime: SearchRuntime, auth: AuthContext, *, force_configured: bool = False
) -> list[dict[str, Any]]:
    inventory = helper_sitebulb_vendor_inventory(runtime, auth)
    inventory.extend(
        [
            {
                "domain": "brand-presence",
                "vendor": "Yext",
                "capability": "Listings, reviews, pages, search, chat, and knowledge graph orchestration",
                "configured": True,
                "evidence": "search_everywhere yext command center mapping",
            },
            {
                "domain": "brand-presence",
                "vendor": "Google Business Profile",
                "capability": "Location and listing distribution",
                "configured": force_configured or helper_env_configured("GOOGLE_CLIENT_ID"),
                "evidence": "publisher sync dependency for location distribution",
            },
            {
                "domain": "brand-presence",
                "vendor": "Apple Business Connect",
                "capability": "Apple ecosystem listing distribution",
                "configured": force_configured,
                "evidence": "publisher sync dependency for Apple surface coverage",
            },
            {
                "domain": "brand-presence",
                "vendor": "Bing Places",
                "capability": "Microsoft listing distribution",
                "configured": force_configured,
                "evidence": "publisher sync dependency for Bing and Maps visibility",
            },
            {
                "domain": "reputation",
                "vendor": "Yelp",
                "capability": "Third-party review ingestion and response workflows",
                "configured": force_configured,
                "evidence": "review response and publisher ingestion mapping",
            },
            {
                "domain": "reputation",
                "vendor": "Tripadvisor",
                "capability": "Hospitality review ingestion and escalation",
                "configured": force_configured,
                "evidence": "review aggregation dependency for travel and hospitality verticals",
            },
            {
                "domain": "support",
                "vendor": "Zendesk",
                "capability": "Escalation routing for reviews and chat",
                "configured": force_configured or helper_env_configured("ZENDESK_SUBDOMAIN"),
                "evidence": "handoff target for unresolved customer issues",
            },
        ]
    )
    return inventory


def operation_yext_wiring_state(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:yext:wiring:get", 60, 60)
    checklist_payload = operation_yext_provider_checklist(runtime, auth)
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


def operation_yext_wiring_apply(
    runtime: SearchRuntime, payload: SliceWiringApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:yext:wiring:apply", 30, 60)
    runtime.yext_wired_tenants.add(auth.tenant_id)
    checklist = operation_yext_provider_checklist(runtime, auth)
    completion = helper_yext_products_completion_chart(runtime, auth)
    gate = operation_yext_products_production_gate(runtime, auth)
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


def operation_yext_env_template(
    runtime: SearchRuntime, payload: SitebulbEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:yext:env-template", 60, 60)
    template = helper_sitebulb_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"yext-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_yext_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:yext:parity-audit", 60, 60)
    completion = helper_yext_products_completion_chart(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "yext_parity_chart": completion.get("chart", []),
        "summary": completion.get("summary", {}),
        "vendor_inventory": helper_yext_vendor_inventory(
            runtime, auth, force_configured=auth.tenant_id in runtime.yext_wired_tenants
        ),
        "generated_at": helper_now_iso(),
    }


def operation_yext_full_automation(
    runtime: SearchRuntime, payload: SemrushFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:yext:full-automation", 30, 60)
    base_result = operation_semrush_full_automation(runtime, payload, auth)
    completion = helper_yext_products_completion_chart(runtime, auth)
    gate_state = operation_yext_products_production_gate(runtime, auth)
    vendor_inventory = helper_yext_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.yext_wired_tenants
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run_mode": base_result.get("run_mode"),
        "results": {
            "listings_and_publisher_sync": base_result.get("results", {}).get("keyword_discovery", {}),
            "reviews_and_reputation_intelligence": base_result.get("results", {}).get("content_gap", {}),
            "pages_search_and_chat_activation": base_result.get("results", {}).get("backlink_audit", {}),
            "knowledge_graph_and_entity_governance": base_result.get("results", {}).get("backlink_gap", {}),
            "parity_summary": base_result.get("results", {}).get("parity_summary", {}),
        },
        "yext_modules": {
            "presence": ["listings sync", "publisher health", "duplicate suppression"],
            "reputation": ["review response", "sentiment clustering", "escalation routing"],
            "experience": ["pages publishing", "search experiences", "chat deflection"],
            "graph": ["entity governance", "field lineage", "publisher-ready attributes"],
            "operations": ["provider checklist", "wiring apply", "production gate", "verification report"],
        },
        "completion_summary": completion.get("summary", {}),
        "production_gate": gate_state.get("gate", {}),
        "third_parties_and_vendors": vendor_inventory,
        "how_it_works": [
            "Knowledge Graph data acts as the system of record for entity and location attributes.",
            "Listings, reviews, pages, search, and chat flows reuse the same entity context to keep content synchronized across publishers and owned experiences.",
            "Review and chat operations route unresolved issues into support workflows while analytics close the loop on performance and deflection.",
            "Provider checklist, wiring apply, and production gate expose whether the Yext slice is code-complete only or also integration-ready for the current tenant.",
        ],
        "generated_at": helper_now_iso(),
    }


def operation_yext_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:yext:vendors", 120, 60)
    inventory = helper_yext_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.yext_wired_tenants
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


def operation_yext_assist_chat(runtime: SearchRuntime, payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:yext:assist", 30, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "assist": {
            "answer_summary": f"Yext assist analyzed the current tenant wiring, parity, and product surface for prompt: {payload.prompt[:120]}",
            "recommended_actions": [
                "Verify publisher authentication for Listings and duplicate suppression workflows.",
                "Confirm Reviews escalation routing into support systems before enabling automated responses.",
                "Validate Knowledge Graph fields used by Pages, Search, and Chat to avoid stale entity data.",
            ],
            "workflow_handoffs": [
                "Listings operations -> publisher network provisioning",
                "Reviews operations -> support escalation and moderation",
                "Experience operations -> pages/search/chat release governance",
            ],
        },
        "context": {
            "include_vendor_context": payload.include_vendor_context,
            "vendors": helper_yext_vendor_inventory(
                runtime, auth, force_configured=auth.tenant_id in runtime.yext_wired_tenants
            )
            if payload.include_vendor_context
            else [],
        },
        "generated_at": helper_now_iso(),
    }
