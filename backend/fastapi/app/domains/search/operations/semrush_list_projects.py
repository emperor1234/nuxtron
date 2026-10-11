"""Search use cases: semrush list projects."""

from ....deps import AuthContext
from ....routers import backlink_intelligence as backlink_intel_router
from ....routers import rank_tracker as rank_tracker_router
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushEnvTemplateRequest
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SemrushProviderBootstrapRequest
from ..schemas import SemrushProviderProbeRequest
from ..schemas import SliceProjectCreateRequest
from ..schemas import SliceProjectRunRequest
from .platform_now_iso import helper_bootstrap_plan
from .platform_now_iso import helper_env_configured
from .platform_now_iso import helper_now_iso
from .platform_now_iso import helper_slice_project_lookup
from .platform_run_provider_probes import helper_env_template
from .platform_run_provider_probes import helper_run_provider_probes
from .platform_run_provider_probes import operation_vendors
from .platform_search_vendors import helper_provider_requirements
from typing import Any


def operation_semrush_list_projects(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:projects:list", 120, 60)
    projects = [item for item in runtime.semrush_projects_memory if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "projects": projects}


def operation_semrush_list_runs(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:runs:list", 120, 60)
    runs = [item for item in runtime.semrush_runs_memory if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "runs": runs}


def helper_semrush_vendor_inventory() -> list[dict[str, Any]]:
    return [
        {
            "vendor": "DataForSEO",
            "module": "keyword_research",
            "type": "third_party_api",
            "configured": helper_env_configured("DATAFORSEO_LOGIN") and helper_env_configured("DATAFORSEO_API_KEY"),
            "evidence": "rank_tracker keyword provider chain",
        },
        {
            "vendor": "Serper.dev",
            "module": "keyword_research",
            "type": "third_party_api",
            "configured": helper_env_configured("SERPER_API_KEY"),
            "evidence": "rank_tracker related search ingestion",
        },
        {
            "vendor": "Google Ads Keyword Planner",
            "module": "keyword_research",
            "type": "first_party_api",
            "configured": helper_env_configured("GOOGLE_ADS_DEVELOPER_TOKEN")
            and helper_env_configured("GOOGLE_ADS_CUSTOMER_ID"),
            "evidence": "rank_tracker google keyword planner adapter",
        },
        {
            "vendor": "Google Search Console",
            "module": "keyword_research",
            "type": "first_party_api",
            "configured": helper_env_configured("GSC_SITE_URL")
            and (
                helper_env_configured("GSC_SERVICE_ACCOUNT_JSON") or helper_env_configured("GOOGLE_OAUTH_ACCESS_TOKEN")
            ),
            "evidence": "rank_tracker gsc adapter",
        },
        {
            "vendor": "Cloudflare",
            "module": "site_audit_and_crawler_enablement",
            "type": "third_party_api",
            "configured": helper_env_configured("CLOUDFLARE_API_TOKEN"),
            "evidence": "ai_crawler cloudflare sync",
        },
        {
            "vendor": "Nuxtron SSR Proxy",
            "module": "site_audit_and_crawler_enablement",
            "type": "internal_service",
            "configured": helper_env_configured("SSR_PROXY_URL"),
            "evidence": "ai_crawler snippet verification and pre-render",
        },
        {
            "vendor": "PostHog",
            "module": "reporting_and_analytics",
            "type": "third_party_api",
            "configured": helper_env_configured("POSTHOG_HOST") and helper_env_configured("POSTHOG_API_KEY"),
            "evidence": "search_everywhere analytics integration",
        },
        {
            "vendor": "Sentry",
            "module": "operations_and_reliability",
            "type": "third_party_sdk",
            "configured": helper_env_configured("SENTRY_DSN"),
            "evidence": "search_everywhere error monitoring integration",
        },
        {
            "vendor": "Upstash Redis",
            "module": "operations_and_reliability",
            "type": "third_party_api",
            "configured": helper_env_configured("UPSTASH_REDIS_REST_URL")
            and helper_env_configured("UPSTASH_REDIS_REST_TOKEN"),
            "evidence": "search_everywhere cache integration",
        },
    ]


def operation_semrush_create_project(
    runtime: SearchRuntime, payload: SliceProjectCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:projects:create", 60, 60)
    project_id = f"smproj-{auth.tenant_id}-{sum((1 for p in runtime.semrush_projects_memory if p.get('tenant_id') == auth.tenant_id)) + 1}"
    project = {
        "id": project_id,
        "tenant_id": auth.tenant_id,
        "name": payload.name,
        "primary_domain": payload.primary_domain,
        "competitor_domains": payload.competitor_domains,
        "default_seed_keyword": payload.default_seed_keyword,
        "created_at": helper_now_iso(),
        "updated_at": helper_now_iso(),
    }
    runtime.semrush_projects_memory.append(project)
    return {"status": "ok", "tenant_id": auth.tenant_id, "project": project}


def operation_semrush_provider_checklist(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:provider-checklist", 60, 60)
    checklist = helper_provider_requirements()
    configured = sum((1 for item in checklist if item["configured"]))
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


def operation_semrush_provider_bootstrap(
    runtime: SearchRuntime, payload: SemrushProviderBootstrapRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:provider-bootstrap", 60, 60)
    checklist = helper_provider_requirements()
    provider_filter = {p.strip().lower() for p in payload.providers if p and p.strip()}
    plan = helper_bootstrap_plan(
        checklist=checklist, include_configured=payload.include_configured, provider_filter=provider_filter
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "requested_providers": sorted(provider_filter),
        "include_configured": payload.include_configured,
        "steps_total": len(plan),
        "steps": plan,
        "next": {
            "run_checklist": "GET /search-everywhere/semrush/provider-checklist",
            "run_gate": "POST /search-everywhere/semrush/production-gate",
        },
        "generated_at": helper_now_iso(),
    }


def helper_semrush_parity_chart(runtime: SearchRuntime, auth: AuthContext) -> dict[str, Any]:
    vendors_payload = operation_vendors(runtime, auth)
    inventory_summary = vendors_payload.get("inventory_summary", {})
    checklist = helper_provider_requirements()
    modules = [
        {
            "module": "site_audit_and_crawler_enablement",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "ai_crawler sites/snippet/verify/events/dashboard",
                "ai_crawler cloudflare sync and visibility audits",
            ],
        },
        {
            "module": "keyword_research",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "rank_tracker keyword-research sources and vendors endpoints",
                "rank_tracker dataforseo/serper/google ads/gsc adapters with fallback",
            ],
        },
        {
            "module": "rank_tracking",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "rank_tracker positions/history/lost-gained/alerts",
                "rank_tracker competitor tracking and forecasts",
            ],
        },
        {
            "module": "backlink_analytics_and_audit",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "backlink_intel overview/backlinks/audit/gap/prospects/disavow",
                "backlink_intel analytics timeseries and authority scoring",
            ],
        },
        {
            "module": "vendor_reporting_and_readiness",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["search_everywhere vendors/report/export/readiness", "cross-domain vendor inventory chart"],
        },
    ]
    configured_units = sum((1 for item in checklist if item["configured"]))
    total_units = len(checklist)
    implementation_pct = round(
        sum((1 for module in modules if module["implemented"])) / max(len(modules), 1) * 100.0, 1
    )
    integration_pct = round(configured_units / max(total_units, 1) * 100.0, 1)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "semrush_parity_chart": modules,
        "summary": {
            "modules_total": len(modules),
            "modules_implemented": sum((1 for module in modules if module["implemented"])),
            "implementation_pct": implementation_pct,
            "integration_configured_units": configured_units,
            "integration_total_units": total_units,
            "integration_configured_pct": integration_pct,
        },
        "vendor_inventory": helper_semrush_vendor_inventory(),
        "inventory_summary": inventory_summary,
        "generated_at": helper_now_iso(),
        "validation_note": "Implementation percentage reflects feature availability; integration percentage reflects environment wiring completeness.",
    }


def operation_semrush_provider_probes(
    runtime: SearchRuntime, payload: SemrushProviderProbeRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:provider-probes", 30, 60)
    probe_summary = helper_run_provider_probes(auth, payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "summary": {
            "providers_requested": len(probe_summary["providers_requested"]),
            "passed": probe_summary["passed"],
            "failed": probe_summary["failed"],
            "skipped": probe_summary["skipped"],
            "strict_live_ready": probe_summary["strict_live_ready"],
        },
        "probes": probe_summary["probes"],
        "generated_at": helper_now_iso(),
    }


def operation_semrush_env_template(
    runtime: SearchRuntime, payload: SemrushEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:env-template", 60, 60)
    template = helper_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"semrush-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_semrush_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:parity-audit", 60, 60)
    return helper_semrush_parity_chart(runtime, auth)


def operation_semrush_full_automation(
    runtime: SearchRuntime, payload: SemrushFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:full-automation", 30, 60)
    discover_payload = rank_tracker_router.KeywordResearchRequest(
        seed_keyword=payload.seed_keyword,
        location=payload.location,
        language=payload.language,
        include_questions=payload.include_questions,
        max_results=payload.max_results,
        require_live_providers=payload.require_live_providers,
    )
    content_gap_payload = rank_tracker_router.KeywordContentGapRequest(
        your_domain=payload.your_domain,
        competitor_domains=payload.competitor_domains,
        max_results=payload.max_results,
        require_live_providers=payload.require_live_providers,
    )
    backlink_audit_payload = backlink_intel_router.AuditRequest(domain=payload.your_domain)
    backlink_gap_payload = backlink_intel_router.GapAnalysisRequest(
        your_domain=payload.your_domain, competitor_domains=payload.competitor_domains[:4]
    )
    keyword_discovery = rank_tracker_router.keyword_research_discover(discover_payload, auth)
    content_gap = rank_tracker_router.keyword_research_content_gap(content_gap_payload, auth)
    backlink_audit = backlink_intel_router.run_audit(backlink_audit_payload, auth)
    backlink_gap = backlink_intel_router.gap_analysis(backlink_gap_payload, auth)
    parity = helper_semrush_parity_chart(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run_mode": "strict_live_only" if payload.require_live_providers else "hybrid_with_resilient_fallback",
        "inputs": payload.model_dump(),
        "results": {
            "keyword_discovery": {
                "provider_selected": keyword_discovery.get("provider_selected"),
                "fallback_used": keyword_discovery.get("fallback_used"),
                "keywords_analyzed": keyword_discovery.get("coverage", {}).get("keywords_analyzed", 0),
                "clusters_found": keyword_discovery.get("coverage", {}).get("clusters_found", 0),
            },
            "content_gap": {
                "provider_selected": content_gap.get("provider_selected"),
                "fallback_used": content_gap.get("fallback_used"),
                "total_opportunities": content_gap.get("summary", {}).get("total_opportunities", 0),
                "high_coverage_gaps": content_gap.get("summary", {}).get("high_coverage_gaps", 0),
            },
            "backlink_audit": {
                "risk_level": backlink_audit.get("audit", {}).get("risk_level"),
                "overall_risk_pct": backlink_audit.get("audit", {}).get("overall_risk_pct"),
                "toxic_count": backlink_audit.get("audit", {}).get("toxic_count"),
                "suspicious_count": backlink_audit.get("audit", {}).get("suspicious_count"),
            },
            "backlink_gap": {
                "unique_opportunities": backlink_gap.get("gap_analysis", {}).get("unique_opportunities", 0),
                "competitors_analyzed": len(backlink_gap.get("gap_analysis", {}).get("competitors", [])),
            },
            "parity_summary": parity.get("summary", {}),
        },
        "providers": {
            "keyword_discovery_attempts": keyword_discovery.get("provider_attempts", []),
            "content_gap_attempts": content_gap.get("provider_attempts", []),
            "vendor_inventory": parity.get("vendor_inventory", []),
        },
        "generated_at": helper_now_iso(),
    }


def operation_semrush_run_project(
    runtime: SearchRuntime, project_id: str, payload: SliceProjectRunRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:runs:create", 30, 60)
    project = helper_slice_project_lookup(
        runtime.semrush_projects_memory, auth.tenant_id, project_id, "semrush_project_not_found"
    )
    automation = operation_semrush_full_automation(
        runtime,
        SemrushFullAutomationRequest(
            seed_keyword=payload.seed_keyword or str(project.get("default_seed_keyword") or "social media management"),
            your_domain=str(project.get("primary_domain")),
            competitor_domains=list(project.get("competitor_domains") or ["ahrefs.com", "moz.com"]),
            max_results=payload.max_results,
            require_live_providers=payload.require_live_providers,
        ),
        auth,
    )
    run_id = f"smrun-{auth.tenant_id}-{sum((1 for r in runtime.semrush_runs_memory if r.get('tenant_id') == auth.tenant_id)) + 1}"
    run = {
        "id": run_id,
        "tenant_id": auth.tenant_id,
        "project_id": project_id,
        "completed_at": helper_now_iso(),
        "run_mode": automation.get("run_mode"),
    }
    runtime.semrush_runs_memory.append(run)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run": run,
        "results": automation.get("results", {}),
        "generated_at": helper_now_iso(),
    }
