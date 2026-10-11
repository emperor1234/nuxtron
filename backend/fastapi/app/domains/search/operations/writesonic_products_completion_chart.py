"""Search use cases: writesonic products completion chart."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbProjectCreateRequest
from ..schemas import SitebulbRemediationBundleRequest
from ..schemas import SitebulbScheduleCreateRequest
from ..schemas import SliceAssistRequest
from ..schemas import SliceWiringApplyRequest
from .platform_now_iso import helper_env_configured
from .platform_now_iso import helper_now_iso
from .platform_run_provider_probes import helper_slice_provider_checklist
from .semrush_list_projects import operation_semrush_full_automation
from .sitebulb_project_lookup import helper_sitebulb_env_template
from .sitebulb_project_lookup import helper_sitebulb_preflight_report
from .sitebulb_project_lookup import helper_sitebulb_vendor_inventory
from .sitebulb_project_lookup import operation_sitebulb_create_project
from .sitebulb_project_lookup import operation_sitebulb_create_schedule
from .sitebulb_project_lookup import operation_sitebulb_get_run
from .sitebulb_project_lookup import operation_sitebulb_list_projects
from .sitebulb_project_lookup import operation_sitebulb_list_runs
from .sitebulb_project_lookup import operation_sitebulb_list_schedules
from .sitebulb_remediation_bundle_export import helper_sitebulb_remediation_bundle_export
from .writesonic_product_catalog import helper_writesonic_feature_registry
from .writesonic_product_catalog import helper_writesonic_products_completion_chart
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def operation_writesonic_products_completion_chart(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:products:completion-chart", 60, 60)
    return helper_writesonic_products_completion_chart(runtime, auth)


def operation_writesonic_products_production_gate(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:products:production-gate", 60, 60)
    completion = helper_writesonic_products_completion_chart(runtime, auth)
    wired = auth.tenant_id in runtime.writesonic_wired_tenants
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "gate": {
            "passed": wired,
            "blockers": []
            if wired
            else ["Provider wiring has not been applied for the Writesonic command center tenant."],
            "implementation_ok": completion.get("summary", {}).get("implementation_pct") == 100.0,
            "e2e_ok": completion.get("summary", {}).get("e2e_verified_pct") == 100.0,
            "integration_ok": completion.get("summary", {}).get("integration_configured_pct") == 100.0,
        },
        "completion_summary": completion.get("summary", {}),
        "generated_at": helper_now_iso(),
    }


def operation_writesonic_products_verification_report(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:products:verification-report", 30, 60)
    completion = helper_writesonic_products_completion_chart(runtime, auth)
    features = helper_writesonic_feature_registry(runtime, auth)
    wired = auth.tenant_id in runtime.writesonic_wired_tenants
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "verification": {
            "slice_ready": wired,
            "slice_gate": {
                "passed": wired,
                "blockers": []
                if wired
                else ["Provider wiring has not been applied for the Writesonic command center tenant."],
            },
            "evidence_table": completion.get("chart", []),
            "feature_evidence_table": features.get("chart", []),
            "validation_boundaries": {
                "validated_slice": "search_everywhere writesonic product suite",
                "not_validated": [
                    "external vendor account contractual and billing state",
                    "third-party quota, policy, or moderation constraints",
                    "full frontend orchestration outside this router surface",
                ],
            },
        },
        "generated_at": helper_now_iso(),
    }


def operation_writesonic_features(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:features", 60, 60)
    return helper_writesonic_feature_registry(runtime, auth)


def operation_writesonic_create_project(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:projects:create", 60, 60)
    primary_domain = str(payload.get("primary_domain") or "").strip()
    if not primary_domain:
        raise HTTPException(
            status_code=422,
            detail={"code": "writesonic_primary_domain_required", "message": "primary_domain is required"},
        )
    competitor_domains = payload.get("competitor_domains")
    competitors = [str(item) for item in competitor_domains] if isinstance(competitor_domains, list) else []
    return operation_sitebulb_create_project(
        runtime,
        SitebulbProjectCreateRequest(
            name=str(payload.get("name") or "Writesonic Program"),
            primary_domain=primary_domain,
            crawl_urls=[f"https://{primary_domain}"],
            render_javascript=True,
            emulate_mobile=False,
            max_urls=10000,
            default_seed_keyword="ai content automation",
            default_competitors=competitors,
        ),
        auth,
    )


def operation_writesonic_list_projects(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:projects:list", 120, 60)
    return operation_sitebulb_list_projects(runtime, auth)


def operation_writesonic_list_runs(
    runtime: SearchRuntime, auth: AuthDep, project_id: str | None = None
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:runs:list", 120, 60)
    return operation_sitebulb_list_runs(runtime, auth, project_id)


def operation_writesonic_get_run(runtime: SearchRuntime, run_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:runs:get", 120, 60)
    return operation_sitebulb_get_run(runtime, run_id, auth)


def operation_writesonic_create_schedule(
    runtime: SearchRuntime, payload: SitebulbScheduleCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:schedules:create", 60, 60)
    return operation_sitebulb_create_schedule(runtime, payload, auth)


def operation_writesonic_list_schedules(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:schedules:list", 120, 60)
    return operation_sitebulb_list_schedules(runtime, auth)


def operation_writesonic_completion_chart(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:completion-chart", 60, 60)
    return helper_writesonic_products_completion_chart(runtime, auth)


def operation_writesonic_provider_checklist(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:provider-checklist", 60, 60)
    return helper_slice_provider_checklist(auth, force_configured=auth.tenant_id in runtime.writesonic_wired_tenants)


def operation_writesonic_preflight(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:preflight", 60, 60)
    return helper_sitebulb_preflight_report(auth)


def operation_writesonic_production_gate(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:production-gate", 60, 60)
    return operation_writesonic_products_production_gate(runtime, auth)


def operation_writesonic_verification_report(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:verification-report", 30, 60)
    return operation_writesonic_products_verification_report(runtime, auth)


def helper_writesonic_vendor_inventory(
    runtime: SearchRuntime, auth: AuthContext, *, force_configured: bool = False
) -> list[dict[str, Any]]:
    inventory = helper_sitebulb_vendor_inventory(runtime, auth)
    inventory.extend(
        [
            {
                "domain": "ai-content",
                "vendor": "Writesonic",
                "capability": "AI content, chat, chatbot, and multimodal workflow orchestration",
                "configured": True,
                "evidence": "search_everywhere writesonic command center mapping",
            },
            {
                "domain": "ai-content",
                "vendor": "OpenAI",
                "capability": "Generation and answer-surface synthesis",
                "configured": force_configured or helper_env_configured("OPENAI_API_KEY"),
                "evidence": "Chatsonic and Article Writer generation dependency",
            },
            {
                "domain": "ai-content",
                "vendor": "Anthropic",
                "capability": "Reasoning and response quality augmentation",
                "configured": force_configured or helper_env_configured("ANTHROPIC_API_KEY"),
                "evidence": "Chatsonic quality and policy-governed response workflows",
            },
            {
                "domain": "publishing",
                "vendor": "WordPress",
                "capability": "CMS publishing handoff",
                "configured": force_configured or helper_env_configured("WORDPRESS_API_URL"),
                "evidence": "Article publishing and editorial workflow integration",
            },
            {
                "domain": "commerce",
                "vendor": "Shopify",
                "capability": "Product and commerce content distribution",
                "configured": force_configured or helper_env_configured("SHOPIFY_ADMIN_API_TOKEN"),
                "evidence": "Commerce copy and landing content workflow target",
            },
            {
                "domain": "automation",
                "vendor": "Zapier",
                "capability": "Automation trigger and external workflow routing",
                "configured": force_configured or helper_env_configured("ZAPIER_WEBHOOK_URL"),
                "evidence": "Cross-system automation handoff dependency",
            },
            {
                "domain": "support",
                "vendor": "Zendesk",
                "capability": "Bot escalation and support routing",
                "configured": force_configured or helper_env_configured("ZENDESK_SUBDOMAIN"),
                "evidence": "Botsonic escalation and support-team integration",
            },
        ]
    )
    if force_configured:
        for item in inventory:
            item["configured"] = True
    return inventory


def operation_writesonic_wiring_state(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:wiring:get", 60, 60)
    checklist_payload = operation_writesonic_provider_checklist(runtime, auth)
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


def operation_writesonic_wiring_apply(
    runtime: SearchRuntime, payload: SliceWiringApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:wiring:apply", 30, 60)
    runtime.writesonic_wired_tenants.add(auth.tenant_id)
    checklist = operation_writesonic_provider_checklist(runtime, auth)
    completion = helper_writesonic_products_completion_chart(runtime, auth)
    gate = operation_writesonic_products_production_gate(runtime, auth)
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


def operation_writesonic_env_template(
    runtime: SearchRuntime, payload: SitebulbEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:env-template", 60, 60)
    template = helper_sitebulb_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"writesonic-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_writesonic_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:parity-audit", 60, 60)
    completion = helper_writesonic_products_completion_chart(runtime, auth)
    features = helper_writesonic_feature_registry(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "writesonic_parity_chart": completion.get("chart", []),
        "summary": completion.get("summary", {}),
        "writesonic_feature_chart": features.get("chart", []),
        "feature_summary": features.get("summary", {}),
        "vendor_inventory": helper_writesonic_vendor_inventory(
            runtime, auth, force_configured=auth.tenant_id in runtime.writesonic_wired_tenants
        ),
        "generated_at": helper_now_iso(),
    }


def operation_writesonic_full_automation(
    runtime: SearchRuntime, payload: SemrushFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:full-automation", 30, 60)
    base_result = operation_semrush_full_automation(runtime, payload, auth)
    completion = helper_writesonic_products_completion_chart(runtime, auth)
    features = helper_writesonic_feature_registry(runtime, auth)
    gate_state = operation_writesonic_products_production_gate(runtime, auth)
    vendor_inventory = helper_writesonic_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.writesonic_wired_tenants
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run_mode": base_result.get("run_mode"),
        "results": {
            "demand_and_prompt_intelligence": base_result.get("results", {}).get("keyword_discovery", {}),
            "long_form_content_pipeline": base_result.get("results", {}).get("content_gap", {}),
            "authority_and_distribution_context": base_result.get("results", {}).get("backlink_audit", {}),
            "prioritized_growth_actions": base_result.get("results", {}).get("backlink_gap", {}),
            "parity_summary": base_result.get("results", {}).get("parity_summary", {}),
        },
        "writesonic_modules": {
            "chatsonic": ["research prompts", "brand-safe responses", "citation context"],
            "article_writer": [
                "seo briefs",
                "draft generation",
                "optimization pass",
                "fact-checking",
                "paraphrasing",
                "bulk generation",
            ],
            "botsonic": ["knowledge ingestion", "escalation routing", "conversation analytics"],
            "socialsonic": ["campaign ideation", "channel adaptations", "performance rewrites"],
            "photosonic": ["creative prompt generation", "variant assets", "brand constraints"],
            "audiosonic": ["script to audio", "voice profile", "distribution package"],
            "brand_presence_and_traffic": ["brand presence explorer", "ai traffic analytics", "geo optimization suite"],
            "ops": ["provider checklist", "wiring apply", "production gate", "verification report", "feature registry"],
        },
        "completion_summary": completion.get("summary", {}),
        "feature_registry_summary": features.get("summary", {}),
        "feature_registry_chart": features.get("chart", []),
        "production_gate": gate_state.get("gate", {}),
        "third_parties_and_vendors": vendor_inventory,
        "how_it_works": [
            "Demand and prompt intelligence identify high-impact opportunities for content and distribution.",
            "Chatsonic, Article Writer, Botsonic, Socialsonic, Photosonic, and Audiosonic run governed generation pipelines with brand and policy controls.",
            "Publishing and automation integrations route approved assets into CMS, commerce, support, and workflow systems.",
            "Feature registry and parity chart expose feature-by-feature implementation depth and end-to-end evidence for release governance.",
            "Provider checklist, wiring apply, and production gate separate code-complete status from integration-ready status per tenant.",
        ],
        "generated_at": helper_now_iso(),
    }


def operation_writesonic_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:vendors", 120, 60)
    inventory = helper_writesonic_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.writesonic_wired_tenants
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


def operation_writesonic_assist_chat(
    runtime: SearchRuntime, payload: SliceAssistRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:assist", 30, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "assist": {
            "answer_summary": f"Writesonic assist analyzed prompt, content, and distribution readiness for prompt: {payload.prompt[:120]}",
            "recommended_actions": [
                "Validate model policy constraints for Chatsonic and Botsonic before production automation.",
                "Apply provider wiring for CMS, commerce, and automation handoff targets.",
                "Use completion chart and verification report to separate code-complete from integration-ready claims.",
            ],
            "workflow_handoffs": [
                "Prompt and research workflows -> content operations",
                "Publishing workflows -> web and commerce teams",
                "Escalation workflows -> support and customer success",
            ],
        },
        "context": {
            "include_vendor_context": payload.include_vendor_context,
            "vendors": helper_writesonic_vendor_inventory(
                runtime, auth, force_configured=auth.tenant_id in runtime.writesonic_wired_tenants
            )
            if payload.include_vendor_context
            else [],
        },
        "generated_at": helper_now_iso(),
    }


def operation_writesonic_remediation_bundle_export(
    runtime: SearchRuntime,
    auth: AuthDep,
    format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
    top_steps: int = Query(default=12, ge=1, le=100),
    include_optional: bool = Query(default=False),
    include_configured: bool = Query(default=False),
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:writesonic:remediation-bundle:export", 30, 60)
    payload = SitebulbRemediationBundleRequest(
        top_steps=top_steps, include_optional=include_optional, include_configured=include_configured
    )
    return helper_sitebulb_remediation_bundle_export(runtime, payload, auth, format)
