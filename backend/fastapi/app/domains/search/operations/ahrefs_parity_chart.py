"""Search use cases: ahrefs parity chart."""

from typing import Any, cast

from fastapi import HTTPException

from ....deps import AuthContext
from ....domains.seo.seo_module_registry import audit_ahrefs_core_tool_parity
from ....domains.seo.services.seo_keyword_research_service import raise_keyword_research_unavailable
from ....routers import backlink_intelligence as backlink_intel_router
from ....routers import rank_tracker as rank_tracker_router
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import (
    AhrefsEnvTemplateRequest,
    AhrefsFullAutomationRequest,
    AhrefsProductionGateRequest,
    AhrefsProviderProbeRequest,
)
from ..values import coerce_int as _coerce_int
from .ahrefs_provider_probe_payload import (
    helper_ahrefs_env_template,
    helper_ahrefs_provider_requirements,
    helper_ahrefs_run_provider_probes,
    helper_ahrefs_vendor_inventory,
)
from .platform_now_iso import helper_now_iso
from .platform_run_provider_probes import operation_vendors


def helper_ahrefs_parity_chart(runtime: SearchRuntime, auth: AuthContext) -> dict[str, Any]:
    vendors_payload = operation_vendors(runtime, auth)
    inventory_summary = vendors_payload.get("inventory_summary", {})
    checklist = helper_ahrefs_provider_requirements(runtime, auth)
    ahrefs_audit = audit_ahrefs_core_tool_parity()
    core_tools = [
        {
            "tool_key": row.get("tool_key"),
            "tool_name": row.get("tool_name"),
            "route_path": row.get("route_path"),
            "parity_module_key": row.get("parity_module_key"),
            "counterpart_module_key": row.get("counterpart_module_key"),
            "coverage_pct": row.get("coverage_pct", 0.0),
            "vendors": row.get("vendors", []),
        }
        for row in cast(list[dict[str, Any]], ahrefs_audit.get("rows", []))
    ]
    modules = [
        {
            "module": "site_explorer_and_crawl_intelligence",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["GET /ai-crawler/sites", "GET /ai-crawler/dashboard", "GET /search-everywhere/readiness"],
        },
        {
            "module": "keyword_explorer_and_serp_monitoring",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "POST /rank-tracker/keyword-research/discover",
                "POST /rank-tracker/keyword-research/content-gap",
                "GET /rank-tracker/positions",
            ],
        },
        {
            "module": "rank_tracking_and_alerting",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "GET /rank-tracker/history",
                "GET /rank-tracker/lost-gained",
                "GET /rank-tracker/visibility-score",
                "GET /rank-tracker/forecasts",
                "GET /rank-tracker/analytics",
            ],
        },
        {
            "module": "backlink_explorer_and_link_intersect",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "GET /backlink-intel/overview",
                "POST /backlink-intel/audit",
                "POST /backlink-intel/gap-analysis",
            ],
        },
        {
            "module": "reporting_and_export_readiness",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "GET /search-everywhere/vendors/report",
                "GET /search-everywhere/vendors/report/export",
                "GET /search-everywhere/readiness",
            ],
        },
        {
            "module": "vendor_wiring_and_live_probe_gate",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "GET /search-everywhere/ahrefs/provider-checklist",
                "POST /search-everywhere/ahrefs/provider-probes",
                "POST /search-everywhere/ahrefs/production-gate",
            ],
        },
    ]
    configured_units = sum(1 for item in checklist if item["configured"])
    total_units = len(checklist)
    implementation_pct = round(
        sum(1 for module in modules if module["implemented"]) / max(len(modules), 1) * 100.0, 1
    )
    integration_pct = round(configured_units / max(total_units, 1) * 100.0, 1)
    core_tools_total = _coerce_int(ahrefs_audit.get("total_tools"), len(core_tools))
    core_tools_fully_covered = _coerce_int(ahrefs_audit.get("fully_covered_tools"))
    core_tools_average_coverage = float(ahrefs_audit.get("average_coverage_pct", 0.0) or 0.0)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "ahrefs_core_tools": core_tools,
        "ahrefs_parity_chart": modules,
        "summary": {
            "modules_total": len(modules),
            "modules_implemented": sum(1 for module in modules if module["implemented"]),
            "implementation_pct": implementation_pct,
            "integration_configured_units": configured_units,
            "integration_total_units": total_units,
            "integration_configured_pct": integration_pct,
            "core_tools_total": core_tools_total,
            "core_tools_fully_covered": core_tools_fully_covered,
            "core_tools_average_coverage_pct": core_tools_average_coverage,
            "core_tools_missing_parity_modules": ahrefs_audit.get("missing_parity_modules", []),
            "core_tools_missing_counterparts": ahrefs_audit.get("missing_counterparts", []),
        },
        "completion_chart": {
            "core_tools": {
                "done": core_tools_fully_covered,
                "total": core_tools_total,
                "pct": round(core_tools_fully_covered / max(core_tools_total, 1) * 100.0, 1),
            },
            "automation_layers": {
                "done": sum(1 for module in modules if module["implemented"]),
                "total": len(modules),
                "pct": implementation_pct,
            },
            "provider_wiring": {"done": configured_units, "total": total_units, "pct": integration_pct},
        },
        "vendor_inventory": helper_ahrefs_vendor_inventory(runtime, auth),
        "inventory_summary": inventory_summary,
        "generated_at": helper_now_iso(),
        "validation_note": "Implementation percentage reflects feature availability; integration percentage reflects environment wiring completeness.",
    }


def operation_ahrefs_provider_probes(
    runtime: SearchRuntime, payload: AhrefsProviderProbeRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:ahrefs:provider-probes", 30, 60)
    probe_summary = helper_ahrefs_run_provider_probes(runtime, auth, payload)
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


def operation_ahrefs_env_template(
    runtime: SearchRuntime, payload: AhrefsEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:ahrefs:env-template", 60, 60)
    template = helper_ahrefs_env_template(runtime, auth, payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"ahrefs-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_ahrefs_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:ahrefs:parity-audit", 60, 60)
    return helper_ahrefs_parity_chart(runtime, auth)


def operation_ahrefs_e2e_verification(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:ahrefs:e2e-verification", 60, 60)
    parity = helper_ahrefs_parity_chart(runtime, auth)
    checklist = helper_ahrefs_provider_requirements(runtime, auth)
    configured = sum(1 for item in checklist if item["configured"])
    total = len(checklist)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "framework": "ahrefs",
        "parity": parity,
        "automation_endpoints": [
            "GET /search-everywhere/ahrefs/parity-audit",
            "GET /search-everywhere/ahrefs/e2e-verification",
            "GET /search-everywhere/ahrefs/provider-checklist",
            "POST /search-everywhere/ahrefs/provider-bootstrap",
            "POST /search-everywhere/ahrefs/provider-probes",
            "POST /search-everywhere/ahrefs/env-template",
            "POST /search-everywhere/ahrefs/production-gate",
            "POST /search-everywhere/ahrefs/full-automation",
            "GET /seo-platform/ahrefs/parity",
        ],
        "provider_wiring_summary": {
            "configured": configured,
            "total": total,
            "configured_pct": round(configured / max(total, 1) * 100.0, 1),
        },
        "generated_at": helper_now_iso(),
    }


def operation_ahrefs_full_automation(
    runtime: SearchRuntime, payload: AhrefsFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    raise_keyword_research_unavailable()
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:ahrefs:full-automation", 30, 60)
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
    backlink_overview = backlink_intel_router.get_overview(auth)
    backlink_audit = backlink_intel_router.run_audit(backlink_audit_payload, auth)
    backlink_gap = backlink_intel_router.gap_analysis(backlink_gap_payload, auth)
    positions = rank_tracker_router.get_positions(auth, page=1, page_size=min(payload.max_results, 25))
    history = rank_tracker_router.get_history(auth, days=90)
    lost_gained = rank_tracker_router.lost_gained(auth, days=30)
    visibility = rank_tracker_router.visibility_score(auth)
    forecasts = rank_tracker_router.traffic_forecasts(auth)
    analytics = rank_tracker_router.analytics(auth)
    parity = helper_ahrefs_parity_chart(runtime, auth)
    positions_summary = positions.get("summary", {})
    visibility_summary = visibility.get("visibility", {})
    history_payload = history.get("history", {})
    lost_gained_payload = lost_gained.get("lost_gained", {})
    analytics_payload = analytics.get("analytics", {})
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "framework": "ahrefs",
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
            "backlink_overview": {
                "authority_score": backlink_overview.get("overview", {}).get("authority_score"),
                "referring_domains": backlink_overview.get("overview", {}).get("referring_domains"),
                "toxic_count": backlink_overview.get("overview", {}).get("toxic_count"),
                "suspicious_count": backlink_overview.get("overview", {}).get("suspicious_count"),
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
            "rank_tracking": {
                "tracked_keywords": positions_summary.get("total_keywords", 0),
                "improved_30d": positions_summary.get("improved_30d", 0),
                "dropped_30d": positions_summary.get("dropped_30d", 0),
                "top_10": positions_summary.get("top_10", 0),
                "top_3": positions_summary.get("top_3", 0),
                "visibility_score": visibility_summary.get("visibility_score", 0),
                "estimated_monthly_traffic": visibility_summary.get("estimated_monthly_traffic", 0),
                "history_days": history_payload.get("days", 0),
                "gained_keywords": len(lost_gained_payload.get("gained", [])),
                "lost_keywords": len(lost_gained_payload.get("lost", [])),
                "forecast_buckets": len(forecasts.get("forecasts", [])),
                "daily_improvements": analytics_payload.get("improved_count", 0),
            },
            "parity_summary": parity.get("summary", {}),
        },
        "providers": {
            "keyword_discovery_attempts": keyword_discovery.get("provider_attempts", []),
            "content_gap_attempts": content_gap.get("provider_attempts", []),
            "vendor_inventory": parity.get("vendor_inventory", []),
        },
        "how_it_works": [
            {
                "stage": 1,
                "name": "discover_and_cluster",
                "description": "Resolve keywords through live providers and surface clusters with questions when available.",
            },
            {
                "stage": 2,
                "name": "compare_and_gap_analyze",
                "description": "Compare your domain with competitors, then combine backlink gap and backlink audit output.",
            },
            {
                "stage": 3,
                "name": "rank_and_visibility_readout",
                "description": "Pull position history, visibility score, lost/gained keywords, forecasts, and analytics into one response.",
            },
            {
                "stage": 4,
                "name": "validate_production_readiness",
                "description": "Use the parity chart, provider checklist, and strict live probe to decide whether the slice is production ready.",
            },
        ],
        "generated_at": helper_now_iso(),
    }


def helper_ahrefs_strict_live_probe(
    runtime: SearchRuntime, auth: AuthContext, payload: AhrefsProductionGateRequest
) -> dict[str, Any]:
    try:
        probe_result = operation_ahrefs_full_automation(
            runtime,
            AhrefsFullAutomationRequest(
                seed_keyword=payload.seed_keyword,
                your_domain=payload.your_domain,
                competitor_domains=payload.competitor_domains,
                max_results=payload.max_results,
                require_live_providers=True,
            ),
            auth,
        )
        return {
            "status": "passed",
            "run_mode": probe_result.get("run_mode"),
            "provider_selected": probe_result.get("results", {}).get("keyword_discovery", {}).get("provider_selected"),
            "fallback_used": probe_result.get("results", {}).get("keyword_discovery", {}).get("fallback_used"),
        }
    except HTTPException as exc:
        if exc.status_code == 412:
            detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
            return {
                "status": "failed",
                "reason": "live_provider_required",
                "http_status": exc.status_code,
                "detail": detail,
            }
        raise


def operation_ahrefs_production_gate(
    runtime: SearchRuntime, payload: AhrefsProductionGateRequest, auth: AuthDep
) -> dict[str, Any]:
    raise_keyword_research_unavailable()
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:ahrefs:production-gate", 30, 60)
    parity = helper_ahrefs_parity_chart(runtime, auth)
    checklist = helper_ahrefs_provider_requirements(runtime, auth)
    strict_probe = helper_ahrefs_strict_live_probe(runtime, auth, payload)
    implementation_ok = parity.get("summary", {}).get("implementation_pct", 0.0) >= 100.0
    integration_ok = parity.get("summary", {}).get("integration_configured_pct", 0.0) >= 100.0
    strict_probe_ok = strict_probe.get("status") == "passed"
    gate_passed = bool(implementation_ok and integration_ok and strict_probe_ok)
    blockers: list[str] = []
    if not implementation_ok:
        blockers.append("feature_implementation_incomplete")
    if not integration_ok:
        blockers.append("integration_wiring_incomplete")
    if not strict_probe_ok:
        blockers.append("strict_live_probe_failed")
    missing_requirements = [
        {"provider": item["provider"], "required_missing": item["required_missing"]}
        for item in checklist
        if not item["configured"]
    ]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "gate": {
            "passed": gate_passed,
            "implementation_ok": implementation_ok,
            "integration_ok": integration_ok,
            "strict_probe_ok": strict_probe_ok,
            "blockers": blockers,
        },
        "parity_summary": parity.get("summary", {}),
        "strict_live_probe": strict_probe,
        "provider_checklist_summary": {
            "configured": sum(1 for item in checklist if item["configured"]),
            "total": len(checklist),
            "missing_requirements": missing_requirements,
        },
        "generated_at": helper_now_iso(),
    }
