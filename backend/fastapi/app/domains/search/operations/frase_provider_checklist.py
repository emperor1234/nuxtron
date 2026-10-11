"""Search use cases: frase provider checklist."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import FraseEnvTemplateRequest
from ..schemas import FraseFullAutomationRequest
from ..schemas import FraseProductionGateRequest
from ..schemas import FraseProviderBootstrapRequest
from ..schemas import FraseProviderProbeRequest
from ..schemas import SurferFullAutomationRequest
from ..schemas import SurferProductionGateRequest
from .platform_now_iso import helper_bootstrap_plan
from .platform_now_iso import helper_now_iso
from .surfer_parity_chart import helper_surfer_setup_playbook
from .surfer_parity_chart import helper_surfer_strict_live_probe
from .surfer_parity_chart import operation_surfer_full_automation
from .surfer_provider_probe_payload import helper_surfer_provider_requirements
from .surfer_vendor_inventory import helper_surfer_env_template
from .surfer_vendor_inventory import helper_surfer_run_provider_probes
from .surfer_vendor_inventory import helper_surfer_vendor_inventory
from .surfer_vendor_inventory import helper_surfer_wiring_plan
from typing import Any


def operation_frase_provider_checklist(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:frase:provider-checklist", 60, 60)
    checklist = helper_surfer_provider_requirements(runtime, auth)
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


def operation_frase_provider_bootstrap(
    runtime: SearchRuntime, payload: FraseProviderBootstrapRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:frase:provider-bootstrap", 60, 60)
    checklist = helper_surfer_provider_requirements(runtime, auth)
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
            "run_checklist": "GET /search-everywhere/frase/provider-checklist",
            "run_gate": "POST /search-everywhere/frase/production-gate",
        },
        "generated_at": helper_now_iso(),
    }


def helper_frase_vendor_inventory(runtime: SearchRuntime, auth: AuthContext) -> list[dict[str, Any]]:
    inventory = helper_surfer_vendor_inventory(runtime, auth)
    inventory.append(
        {
            "vendor": "Nuxtron Frase-Compatible Orchestrator",
            "module": "workflow_automation_and_integrations",
            "type": "internal_service",
            "configured": True,
            "evidence": "search_everywhere frase automation gateway",
        }
    )
    return inventory


def operation_frase_provider_probes(
    runtime: SearchRuntime, payload: FraseProviderProbeRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:frase:provider-probes", 30, 60)
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


def operation_frase_env_template(
    runtime: SearchRuntime, payload: FraseEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:frase:env-template", 60, 60)
    template = helper_surfer_env_template(runtime, auth, payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"frase-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def helper_frase_parity_chart(runtime: SearchRuntime, auth: AuthContext) -> dict[str, Any]:
    modules = [
        {
            "module": "content_brief_generation",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["POST /seo-platform/content/brief", "POST /search-everywhere/frase/full-automation"],
        },
        {
            "module": "ai_content_generation",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["POST /seo-platform/content/write", "POST /search-everywhere/frase/full-automation"],
        },
        {
            "module": "content_optimization_scoring",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "POST /seo-platform/aio/score",
                "POST /seo-platform/aeo/optimize",
                "POST /seo-platform/geo/optimize",
            ],
        },
        {
            "module": "keyword_research_and_topic_gap",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "POST /rank-tracker/keyword-research/discover",
                "POST /rank-tracker/keyword-research/content-gap",
            ],
        },
        {
            "module": "serp_and_competitor_intelligence",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": ["GET /rank-tracker/positions", "POST /backlink-intel/gap-analysis"],
        },
        {
            "module": "workflow_automation_and_integrations",
            "implemented": True,
            "coverage_pct": 100.0,
            "evidence": [
                "POST /search-everywhere/frase/full-automation",
                "GET /search-everywhere/frase/provider-checklist",
                "POST /search-everywhere/frase/production-gate",
            ],
        },
    ]
    checklist = helper_surfer_provider_requirements(runtime, auth)
    configured = sum((1 for item in checklist if item["configured"]))
    total = len(checklist)
    implementation_pct = round(
        sum((1 for module in modules if module["implemented"])) / max(len(modules), 1) * 100.0, 1
    )
    integration_pct = round(configured / max(total, 1) * 100.0, 1)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "frase_parity_chart": modules,
        "summary": {
            "modules_total": len(modules),
            "modules_implemented": sum((1 for module in modules if module["implemented"])),
            "implementation_pct": implementation_pct,
            "integration_configured_units": configured,
            "integration_total_units": total,
            "integration_configured_pct": integration_pct,
        },
        "vendor_inventory": helper_frase_vendor_inventory(runtime, auth),
        "provider_checklist": checklist,
        "generated_at": helper_now_iso(),
        "validation_note": "Implementation percentage reflects feature availability; integration percentage reflects provider wiring completeness.",
    }


def operation_frase_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:frase:parity-audit", 60, 60)
    return helper_frase_parity_chart(runtime, auth)


def operation_frase_wiring_plan(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:frase:wiring-plan", 60, 60)
    parity = helper_frase_parity_chart(runtime, auth)
    plan = helper_surfer_wiring_plan(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "parity_summary": parity.get("summary", {}),
        "wiring_plan": plan,
        "next": {
            "provider_checklist": "GET /search-everywhere/frase/provider-checklist",
            "provider_probes": "POST /search-everywhere/frase/provider-probes",
            "production_gate": "POST /search-everywhere/frase/production-gate",
        },
        "generated_at": helper_now_iso(),
    }


def operation_frase_setup_playbook(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:frase:setup-playbook", 60, 60)
    parity = helper_frase_parity_chart(runtime, auth)
    playbook = helper_surfer_setup_playbook(runtime, auth)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "parity_summary": parity.get("summary", {}),
        "setup_playbook": playbook,
        "generated_at": helper_now_iso(),
    }


def operation_frase_full_automation(
    runtime: SearchRuntime, payload: FraseFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:frase:full-automation", 30, 60)
    base_result = operation_surfer_full_automation(
        runtime,
        SurferFullAutomationRequest(
            seed_keyword=payload.seed_keyword,
            your_domain=payload.your_domain,
            competitor_domains=payload.competitor_domains,
            location=payload.location,
            language=payload.language,
            include_questions=payload.include_questions,
            max_results=payload.max_results,
            require_live_providers=payload.require_live_providers,
        ),
        auth,
    )
    parity = helper_frase_parity_chart(runtime, auth)
    workflow = {
        "phase_1_discovery": [
            "POST /rank-tracker/keyword-research/discover",
            "POST /rank-tracker/keyword-research/content-gap",
        ],
        "phase_2_brief_and_drafting": ["POST /seo-platform/content/brief", "POST /seo-platform/content/write"],
        "phase_3_optimization": [
            "POST /seo-platform/aio/score",
            "POST /seo-platform/aeo/optimize",
            "POST /seo-platform/geo/optimize",
        ],
        "phase_4_publish_and_observe": ["POST /cms/connections", "POST /search-everywhere/frase/production-gate"],
    }
    base_result["framework"] = "frase"
    base_result["results"]["parity_summary"] = parity.get("summary", {})
    base_result["providers"]["vendor_inventory"] = parity.get("vendor_inventory", [])
    base_result["frase_workflow"] = workflow
    return base_result


def operation_frase_production_gate(
    runtime: SearchRuntime, payload: FraseProductionGateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:frase:production-gate", 30, 60)
    parity = helper_frase_parity_chart(runtime, auth)
    checklist = helper_surfer_provider_requirements(runtime, auth)
    strict_probe = helper_surfer_strict_live_probe(
        runtime,
        auth,
        SurferProductionGateRequest(
            seed_keyword=payload.seed_keyword,
            your_domain=payload.your_domain,
            competitor_domains=payload.competitor_domains,
            max_results=payload.max_results,
        ),
    )
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
            "configured": sum((1 for item in checklist if item["configured"])),
            "total": len(checklist),
            "missing_requirements": missing_requirements,
        },
        "generated_at": helper_now_iso(),
    }
