"""Search use cases: semrush production gate."""

from typing import Any

from ....domains.seo.services.seo_keyword_research_service import raise_keyword_research_unavailable
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushProductionGateRequest
from .platform_now_iso import helper_now_iso
from .platform_search_vendors import helper_provider_requirements
from .platform_strict_live_probe import helper_strict_live_probe
from .semrush_list_projects import helper_semrush_parity_chart


def operation_semrush_production_gate(
    runtime: SearchRuntime, payload: SemrushProductionGateRequest, auth: AuthDep
) -> dict[str, Any]:
    raise_keyword_research_unavailable()
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:semrush:production-gate", 30, 60)
    parity = helper_semrush_parity_chart(runtime, auth)
    checklist = helper_provider_requirements()
    strict_probe = helper_strict_live_probe(runtime, auth, payload)
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
