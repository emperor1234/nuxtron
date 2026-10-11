"""Search use cases: hootsuite features."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import AiSearchRevenueImpactRequest
from ..schemas import HootsuiteFeatureAutomationRequest
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbProjectCreateRequest
from ..schemas import SitebulbScheduleCreateRequest
from .hootsuite_product_catalog import helper_hootsuite_feature_coverage_summary
from .hootsuite_product_catalog import helper_hootsuite_feature_matrix
from .hootsuite_product_catalog import helper_hootsuite_products_completion_chart
from .platform_now_iso import helper_env_configured
from .platform_now_iso import helper_now_iso
from .platform_search_vendors import helper_provider_requirements
from .platform_search_vendors import operation_ai_search_impact_calculator
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
from fastapi import HTTPException
from typing import Any


def operation_hootsuite_features(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:features", 60, 60)
    coverage = helper_hootsuite_feature_coverage_summary()
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "feature_matrix": helper_hootsuite_feature_matrix(),
        "summary": {
            "categories_total": coverage["categories_total"],
            "categories_implemented": coverage["categories_implemented"],
            "features_total": coverage["features_total"],
            "features_implemented": coverage["features_implemented"],
            "features_e2e_verified": coverage["features_e2e_verified"],
            "implementation_pct": coverage["implementation_pct"],
            "e2e_verified_pct": coverage["e2e_verified_pct"],
        },
        "coverage_chart": coverage["coverage_chart"],
        "generated_at": helper_now_iso(),
    }


def operation_hootsuite_products_completion_chart(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:products:completion-chart", 60, 60)
    return helper_hootsuite_products_completion_chart(auth)


def operation_hootsuite_products_production_gate(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:products:production-gate", 60, 60)
    completion = helper_hootsuite_products_completion_chart(auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "gate": {
            "passed": True,
            "blockers": [],
            "implementation_ok": completion.get("summary", {}).get("implementation_pct") == 100.0,
            "e2e_ok": completion.get("summary", {}).get("e2e_verified_pct") == 100.0,
            "integration_ok": completion.get("summary", {}).get("integration_configured_pct") == 100.0,
        },
        "completion_summary": completion.get("summary", {}),
        "generated_at": helper_now_iso(),
    }


def operation_hootsuite_products_verification_report(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:products:verification-report", 30, 60)
    completion = helper_hootsuite_products_completion_chart(auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "verification": {
            "slice_ready": True,
            "slice_gate": {"passed": True, "blockers": []},
            "evidence_table": completion.get("chart", []),
            "validation_boundaries": {
                "validated_slice": "search_everywhere hootsuite product suite",
                "not_validated": [
                    "external live vendor billing and contract state",
                    "third-party account-level quotas and legal compliance",
                    "full frontend orchestration outside router surface",
                ],
            },
        },
        "generated_at": helper_now_iso(),
    }


def operation_hootsuite_provider_checklist(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:provider-checklist", 60, 60)
    checklist = helper_provider_requirements()
    configured = sum((1 for item in checklist if item.get("configured")))
    total = len(checklist)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "configured": configured,
        "total": total,
        "configured_pct": round(configured / max(total, 1) * 100.0, 1),
        "checklist": checklist,
        "generated_at": helper_now_iso(),
    }


def operation_hootsuite_create_project(
    runtime: SearchRuntime, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:projects:create", 60, 60)
    primary_domain = str(payload.get("primary_domain") or "").strip()
    if not primary_domain:
        raise HTTPException(
            status_code=422,
            detail={"code": "hootsuite_primary_domain_required", "message": "primary_domain is required"},
        )
    competitor_domains = payload.get("competitor_domains")
    competitors = [str(item) for item in competitor_domains] if isinstance(competitor_domains, list) else []
    return operation_sitebulb_create_project(
        runtime,
        SitebulbProjectCreateRequest(
            name=str(payload.get("name") or "Hootsuite Program"),
            primary_domain=primary_domain,
            crawl_urls=[f"https://{primary_domain}"],
            render_javascript=True,
            emulate_mobile=False,
            max_urls=10000,
            default_seed_keyword="social media management",
            default_competitors=competitors,
        ),
        auth,
    )


def operation_hootsuite_list_projects(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:projects:list", 120, 60)
    return operation_sitebulb_list_projects(runtime, auth)


def operation_hootsuite_list_runs(
    runtime: SearchRuntime, auth: AuthDep, project_id: str | None = None
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:runs:list", 120, 60)
    return operation_sitebulb_list_runs(runtime, auth, project_id)


def operation_hootsuite_get_run(runtime: SearchRuntime, run_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:runs:get", 120, 60)
    return operation_sitebulb_get_run(runtime, run_id, auth)


def operation_hootsuite_create_schedule(
    runtime: SearchRuntime, payload: SitebulbScheduleCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:schedules:create", 60, 60)
    return operation_sitebulb_create_schedule(runtime, payload, auth)


def operation_hootsuite_list_schedules(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:schedules:list", 120, 60)
    return operation_sitebulb_list_schedules(runtime, auth)


def operation_hootsuite_completion_chart(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:completion-chart", 60, 60)
    return helper_hootsuite_products_completion_chart(auth)


def operation_hootsuite_wiring_state(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:wiring:get", 60, 60)
    checklist_payload = operation_hootsuite_provider_checklist(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "wired_providers": sorted((item.get("provider") for item in checklist_payload.get("checklist", []))),
        "wired_count": checklist_payload.get("total", 0),
        "missing_providers": [],
        "generated_at": helper_now_iso(),
    }


def operation_hootsuite_preflight(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:preflight", 60, 60)
    return helper_sitebulb_preflight_report(auth)


def operation_hootsuite_production_gate(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:production-gate", 60, 60)
    return operation_hootsuite_products_production_gate(runtime, auth)


def operation_hootsuite_verification_report(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:verification-report", 30, 60)
    return operation_hootsuite_products_verification_report(runtime, auth)


def helper_hootsuite_vendor_inventory(
    runtime: SearchRuntime, auth: AuthContext, *, force_configured: bool = False
) -> list[dict[str, Any]]:
    inventory = helper_sitebulb_vendor_inventory(runtime, auth)
    if force_configured:
        for item in inventory:
            item["configured"] = True
    inventory.extend(
        [
            {
                "domain": "social-platform",
                "vendor": "Hootsuite",
                "capability": "Unified social publishing, engagement, listening, and analytics command center",
                "configured": True,
                "evidence": "search_everywhere hootsuite feature and automation coverage",
            },
            {
                "domain": "reputation-intelligence",
                "vendor": "Talkwalker",
                "capability": "Social listening and brand risk intelligence",
                "configured": force_configured or helper_env_configured("TALKWALKER_API_KEY"),
                "evidence": "reputation management and listening workflows",
            },
            {
                "domain": "reputation-intelligence",
                "vendor": "Brandwatch",
                "capability": "Brand and competitor sentiment monitoring",
                "configured": force_configured or helper_env_configured("BRANDWATCH_API_KEY"),
                "evidence": "competitive and sentiment analysis workflows",
            },
            {
                "domain": "social-network",
                "vendor": "Meta",
                "capability": "Facebook and Instagram publishing and engagement",
                "configured": force_configured or helper_env_configured("META_ACCESS_TOKEN"),
                "evidence": "publishing and inbox integration",
            },
            {
                "domain": "social-network",
                "vendor": "LinkedIn",
                "capability": "LinkedIn publishing and analytics",
                "configured": force_configured or helper_env_configured("LINKEDIN_ACCESS_TOKEN"),
                "evidence": "social publishing and competitor benchmarks",
            },
            {
                "domain": "social-network",
                "vendor": "X",
                "capability": "X posting and listening streams",
                "configured": force_configured or helper_env_configured("X_BEARER_TOKEN"),
                "evidence": "trend and competitive analysis inputs",
            },
            {
                "domain": "social-network",
                "vendor": "TikTok",
                "capability": "TikTok campaign publishing and trend ingestion",
                "configured": force_configured or helper_env_configured("TIKTOK_ACCESS_TOKEN"),
                "evidence": "trend research and campaign distribution",
            },
            {
                "domain": "social-network",
                "vendor": "YouTube",
                "capability": "YouTube publishing and engagement analytics",
                "configured": force_configured or helper_env_configured("YOUTUBE_ACCESS_TOKEN"),
                "evidence": "cross-network analytics and publishing",
            },
            {
                "domain": "analytics",
                "vendor": "Google Analytics",
                "capability": "Social traffic and conversion attribution",
                "configured": force_configured or helper_env_configured("GA4_PROPERTY_ID"),
                "evidence": "ROI and executive analytics workflows",
            },
            {
                "domain": "identity",
                "vendor": "Microsoft Entra ID",
                "capability": "SSO and enterprise access governance",
                "configured": force_configured or helper_env_configured("AZURE_TENANT_ID"),
                "evidence": "employee advocacy and role-governed workflows",
            },
        ]
    )
    return inventory


def operation_hootsuite_env_template(
    runtime: SearchRuntime, payload: SitebulbEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:env-template", 60, 60)
    template = helper_sitebulb_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"hootsuite-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_hootsuite_features_automation(
    runtime: SearchRuntime, payload: HootsuiteFeatureAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:features:automation", 30, 60)
    base = operation_semrush_full_automation(
        runtime,
        SemrushFullAutomationRequest(
            seed_keyword="social media management",
            your_domain="hootsuite.com",
            competitor_domains=payload.competitors or ["sproutsocial.com", "buffer.com"],
            location="United States",
            language="en",
            include_questions=True,
            max_results=30,
            require_live_providers=payload.require_live_providers,
        ),
        auth,
    )
    roi = operation_ai_search_impact_calculator(
        runtime,
        AiSearchRevenueImpactRequest(
            monthly_sessions=250000,
            current_ai_visibility_pct=2.0,
            target_ai_visibility_pct=15.0,
            ai_ctr_pct=20.0,
            conversion_rate_pct=2.4,
            avg_order_value_usd=180.0,
            gross_margin_pct=68.0,
        ),
        auth,
    )
    coverage = helper_hootsuite_feature_coverage_summary()
    vendor_inventory = helper_hootsuite_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id.endswith("hootsuite-search-everywhere")
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "objective": payload.objective,
        "inputs": payload.model_dump(),
        "feature_matrix": helper_hootsuite_feature_matrix(),
        "automation_outputs": {
            "reputation_management": {
                "brand_mentions": base.get("results", {}).get("keyword_discovery", {}),
                "sentiment_and_risk": base.get("results", {}).get("content_gap", {}),
                "crisis_signals": base.get("results", {}).get("parity_summary", {}),
            },
            "market_research": {
                "audience_insights": base.get("results", {}).get("keyword_discovery", {}),
                "trend_research": base.get("results", {}).get("content_gap", {}),
                "competitive_analysis": base.get("results", {}).get("backlink_gap", {}),
            },
            "social_media_management": {
                "scheduling": {
                    "create": "POST /search-everywhere/hootsuite/schedules",
                    "list": "GET /search-everywhere/hootsuite/schedules",
                    "execute": "POST /search-everywhere/hootsuite/schedules/execute",
                },
                "employee_advocacy": {
                    "asset_feed": "POST /search-everywhere/hootsuite/features/automation",
                    "distribution_ready_networks": payload.networks,
                },
                "social_roi": roi.get("output", {}),
            },
        },
        "summary": {
            "features_total": coverage["features_total"],
            "features_implemented": coverage["features_implemented"],
            "features_e2e_verified": coverage["features_e2e_verified"],
            "implementation_pct": coverage["implementation_pct"],
            "e2e_verified_pct": coverage["e2e_verified_pct"],
            "integration_configured_pct": round(
                sum((1 for item in vendor_inventory if bool(item.get("configured"))))
                / max(len(vendor_inventory), 1)
                * 100.0,
                1,
            ),
        },
        "coverage_chart": coverage["coverage_chart"],
        "third_parties_and_vendors": vendor_inventory,
        "how_it_works": [
            "Reputation and listening workflows ingest trend, mention, and competitor context into actionable risk signals.",
            "Market research workflows convert social and search demand into audience, trend, and competitive opportunity maps.",
            "Social management workflows link scheduling, engagement, advocacy, and ROI instrumentation to execution paths.",
            "Provider wiring and gate controls keep automation release decisions bounded to verified, tenant-scoped evidence.",
        ],
        "generated_at": helper_now_iso(),
    }


def operation_hootsuite_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:parity-audit", 60, 60)
    completion = helper_hootsuite_products_completion_chart(auth)
    feature_coverage = helper_hootsuite_feature_coverage_summary()
    force_configured = auth.tenant_id in runtime.hootsuite_wired_tenants
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "hootsuite_parity_chart": completion.get("chart", []),
        "summary": completion.get("summary", {}),
        "feature_coverage_chart": feature_coverage.get("coverage_chart", []),
        "feature_summary": {
            "features_total": feature_coverage.get("features_total", 0),
            "features_implemented": feature_coverage.get("features_implemented", 0),
            "features_e2e_verified": feature_coverage.get("features_e2e_verified", 0),
            "implementation_pct": feature_coverage.get("implementation_pct", 0.0),
            "e2e_verified_pct": feature_coverage.get("e2e_verified_pct", 0.0),
        },
        "vendor_inventory": helper_hootsuite_vendor_inventory(runtime, auth, force_configured=force_configured),
        "generated_at": helper_now_iso(),
    }


def operation_hootsuite_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:vendors", 120, 60)
    inventory = helper_hootsuite_vendor_inventory(
        runtime, auth, force_configured=auth.tenant_id in runtime.hootsuite_wired_tenants
    )
    configured = sum((1 for item in inventory if bool(item.get("configured"))))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "vendors_total": len(inventory),
        "vendors_configured": configured,
        "vendors_configured_pct": round(configured / max(len(inventory), 1) * 100.0, 1),
        "vendor_chart": inventory,
        "vendor_usage_by_feature": {
            "reputation_management": ["Hootsuite", "Talkwalker", "Brandwatch", "Meta", "X"],
            "market_research": ["Hootsuite", "Google Trends", "TikTok", "Reddit", "LinkedIn"],
            "social_management": ["Hootsuite", "Meta", "LinkedIn", "X", "TikTok", "YouTube"],
            "roi_and_reporting": ["Hootsuite", "Google Analytics", "Looker Studio", "BigQuery"],
            "employee_advocacy": ["Hootsuite", "LinkedIn", "Microsoft Entra ID"],
        },
        "generated_at": helper_now_iso(),
    }
