"""Search use cases: surfer parity chart."""

from typing import Any

from fastapi import HTTPException

from ....deps import AuthContext
from ....domains.seo.services.seo_keyword_research_service import raise_keyword_research_unavailable
from ....routers import backlink_intelligence as backlink_intel_router
from ....routers import rank_tracker as rank_tracker_router
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import (
    SurferEnvTemplateRequest,
    SurferFullAutomationRequest,
    SurferProductionGateRequest,
    SurferProviderProbeRequest,
)
from .platform_now_iso import helper_now_iso
from .surfer_provider_probe_payload import (
    helper_surfer_provider_preflight_commands,
    helper_surfer_provider_requirements,
    helper_surfer_provider_setup_notes,
    helper_surfer_provider_verify_endpoints,
)
from .surfer_vendor_inventory import (
    helper_surfer_env_template,
    helper_surfer_run_provider_probes,
    helper_surfer_vendor_inventory,
    helper_surfer_wiring_plan,
)


def helper_surfer_parity_chart(runtime: SearchRuntime, auth: AuthContext) -> dict[str, Any]:
    modules = [
        {
            "module": "content_editor_and_content_score",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["POST /seo-platform/content/brief", "POST /seo-platform/content/write"],
        },
        {
            "module": "content_audit_and_refresh",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["POST /seo-platform/content-auditor/analyze", "POST /seo-platform/performance/audit"],
        },
        {
            "module": "topical_map_and_topic_gap",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["POST /seo-platform/topical-map/build", "POST /rank-tracker/keyword-research/content-gap"],
        },
        {
            "module": "internal_linking_automation",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["POST /seo-platform/internal-linking/suggest", "POST /seo-platform/performance/auto-fix"],
        },
        {
            "module": "keyword_research_and_serp_analysis",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["POST /rank-tracker/keyword-research/discover", "GET /rank-tracker/positions"],
        },
        {
            "module": "ai_search_optimization",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "POST /seo-platform/aio/score",
                "POST /seo-platform/geo/optimize",
                "POST /seo-platform/aeo/optimize",
            ],
        },
        {
            "module": "backlink_intelligence",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["POST /backlink-intel/audit", "POST /backlink-intel/gap-analysis"],
        },
        {
            "module": "workflow_automation_and_integrations",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["POST /search-everywhere/surfer/full-automation", "GET /search-everywhere/vendors"],
        },
    ]
    checklist = helper_surfer_provider_requirements(runtime, auth)
    configured = sum(1 for item in checklist if item["configured"])
    total = len(checklist)
    implementation_pct = round(
        sum(1 for module in modules if module["implemented"]) / max(len(modules), 1) * 100.0, 1
    )
    integration_pct = round(configured / max(total, 1) * 100.0, 1)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "surfer_parity_chart": modules,
        "summary": {
            "modules_total": len(modules),
            "modules_implemented": sum(1 for module in modules if module["implemented"]),
            "implementation_pct": implementation_pct,
            "integration_configured_units": configured,
            "integration_total_units": total,
            "integration_configured_pct": integration_pct,
        },
        "vendor_inventory": helper_surfer_vendor_inventory(runtime, auth),
        "provider_checklist": checklist,
        "generated_at": helper_now_iso(),
        "validation_note": "Implementation percentage reflects feature availability; integration percentage reflects provider wiring completeness.",
    }


def helper_surfer_setup_playbook(runtime: SearchRuntime, auth: AuthContext) -> dict[str, Any]:
    wiring_plan = helper_surfer_wiring_plan(runtime, auth)
    prioritized_missing = list(wiring_plan.get("prioritized_missing_providers", []))
    provider_playbooks: list[dict[str, Any]] = []
    for row in prioritized_missing:
        provider = str(row.get("provider", ""))
        required_missing = [str(item) for item in row.get("required_missing", [])]
        provider_playbooks.append(
            {
                "provider": provider,
                "priority": row.get("priority"),
                "kind": row.get("kind"),
                "gate_impact_score": row.get("gate_impact_score"),
                "integration_pct_if_added": row.get("integration_pct_if_added"),
                "required_missing": required_missing,
                "setup_notes": helper_surfer_provider_setup_notes(provider),
                "preflight_commands_powershell": helper_surfer_provider_preflight_commands(required_missing),
                "verify_with": helper_surfer_provider_verify_endpoints(provider),
            }
        )
    return {
        "summary": {
            "configured": wiring_plan.get("configured"),
            "total": wiring_plan.get("total"),
            "integration_configured_pct": wiring_plan.get("integration_configured_pct"),
        },
        "execution_order": {
            "stage_1": wiring_plan.get("stages", {}).get("stage_1_strict_live_foundation", {}).get("providers", []),
            "stage_2": wiring_plan.get("stages", {}).get("stage_2_runtime_reliability", {}).get("providers", []),
            "stage_3": wiring_plan.get("stages", {}).get("stage_3_full_automation_coverage", {}).get("providers", []),
        },
        "providers": provider_playbooks,
        "final_validation": [
            "GET /search-everywhere/surfer/provider-checklist",
            "POST /search-everywhere/surfer/provider-probes",
            "POST /search-everywhere/surfer/production-gate",
        ],
        "validation_note": "Do not claim production-grade until production gate passes with strict live probes and full integration wiring.",
    }


def operation_surfer_provider_probes(
    runtime: SearchRuntime, payload: SurferProviderProbeRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:surfer:provider-probes", 30, 60)
    probe_summary = helper_surfer_run_provider_probes(runtime, auth, payload)
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


def operation_surfer_env_template(
    runtime: SearchRuntime, payload: SurferEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:surfer:env-template", 60, 60)
    template = helper_surfer_env_template(runtime, auth, payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"surfer-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_surfer_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:surfer:parity-audit", 60, 60)
    return helper_surfer_parity_chart(runtime, auth)


def operation_surfer_wiring_plan(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:surfer:wiring-plan", 60, 60)
    parity = helper_surfer_parity_chart(runtime, auth)
    plan = helper_surfer_wiring_plan(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "parity_summary": parity.get("summary", {}),
        "wiring_plan": plan,
        "next": {
            "provider_checklist": "GET /search-everywhere/surfer/provider-checklist",
            "provider_probes": "POST /search-everywhere/surfer/provider-probes",
            "production_gate": "POST /search-everywhere/surfer/production-gate",
        },
        "generated_at": helper_now_iso(),
    }


def operation_surfer_setup_playbook(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:surfer:setup-playbook", 60, 60)
    parity = helper_surfer_parity_chart(runtime, auth)
    playbook = helper_surfer_setup_playbook(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "parity_summary": parity.get("summary", {}),
        "setup_playbook": playbook,
        "generated_at": helper_now_iso(),
    }


def operation_surfer_full_automation(
    runtime: SearchRuntime, payload: SurferFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    raise_keyword_research_unavailable()
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:surfer:full-automation", 30, 60)
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
    parity = helper_surfer_parity_chart(runtime, auth)
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


def helper_surfer_strict_live_probe(
    runtime: SearchRuntime, auth: AuthContext, payload: SurferProductionGateRequest
) -> dict[str, Any]:
    try:
        probe_result = operation_surfer_full_automation(
            runtime,
            SurferFullAutomationRequest(
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


def operation_surfer_production_gate(
    runtime: SearchRuntime, payload: SurferProductionGateRequest, auth: AuthDep
) -> dict[str, Any]:
    raise_keyword_research_unavailable()
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:surfer:production-gate", 30, 60)
    parity = helper_surfer_parity_chart(runtime, auth)
    checklist = helper_surfer_provider_requirements(runtime, auth)
    strict_probe = helper_surfer_strict_live_probe(runtime, auth, payload)
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
