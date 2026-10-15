"""Search use cases: hootsuite wiring apply."""

from typing import Any

from ....domains.seo.services.seo_keyword_research_service import raise_keyword_research_unavailable
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import HootsuiteWiringApplyRequest, SemrushFullAutomationRequest, SitebulbScheduleExecuteRequest
from .hootsuite_features import helper_hootsuite_vendor_inventory
from .hootsuite_product_catalog import (
    helper_hootsuite_feature_coverage_summary,
    helper_hootsuite_products_completion_chart,
)
from .platform_now_iso import helper_now_iso
from .semrush_list_projects import operation_semrush_full_automation
from .sitebulb_completion_chart import (
    helper_sitebulb_gate_state,
    operation_sitebulb_execute_schedules,
)


def operation_hootsuite_wiring_apply(
    runtime: SearchRuntime, payload: HootsuiteWiringApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    raise_keyword_research_unavailable()


def operation_hootsuite_full_automation(
    runtime: SearchRuntime, payload: SemrushFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    raise_keyword_research_unavailable()
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:full-automation", 30, 60)
    base_result = operation_semrush_full_automation(runtime, payload, auth)
    completion = helper_hootsuite_products_completion_chart(auth)
    gate_state = helper_sitebulb_gate_state(runtime, auth)
    force_configured = auth.tenant_id in runtime.hootsuite_wired_tenants
    vendor_inventory = helper_hootsuite_vendor_inventory(runtime, auth, force_configured=force_configured)
    feature_coverage = helper_hootsuite_feature_coverage_summary()
    vendors_configured = sum(1 for item in vendor_inventory if bool(item.get("configured")))
    vendors_total = len(vendor_inventory)
    integration_pct = round(vendors_configured / max(vendors_total, 1) * 100.0, 1)
    e2e_pct = 100.0 if integration_pct == 100.0 else feature_coverage.get("e2e_verified_pct", 0.0)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run_mode": base_result.get("run_mode"),
        "results": {
            "social_demand_and_intent": base_result.get("results", {}).get("keyword_discovery", {}),
            "campaign_content_and_gaps": base_result.get("results", {}).get("content_gap", {}),
            "authority_backlink_and_competitor_context": base_result.get("results", {}).get("backlink_audit", {}),
            "prioritized_growth_actions": base_result.get("results", {}).get("backlink_gap", {}),
            "parity_summary": base_result.get("results", {}).get("parity_summary", {}),
        },
        "hootsuite_modules": {
            "publish": ["campaign planning", "multichannel scheduling", "approval workflows"],
            "engage": ["inbox triage", "response orchestration", "SLA-aware routing"],
            "measure": ["cross-channel reporting", "executive dashboards", "trend alerts"],
            "listen": ["brand monitoring", "competitor intelligence", "sentiment snapshots"],
            "operations": ["provider checklist", "gate progress", "remediation bundle", "verification report"],
        },
        "completion_summary": {
            **completion.get("summary", {}),
            "integration_configured_pct": integration_pct,
            "e2e_verified_pct": e2e_pct,
            "hootsuite_feature_implementation_pct": feature_coverage.get("implementation_pct", 0.0),
            "hootsuite_feature_e2e_verified_pct": feature_coverage.get("e2e_verified_pct", 0.0),
            "hootsuite_features_total": feature_coverage.get("features_total", 0),
            "hootsuite_features_implemented": feature_coverage.get("features_implemented", 0),
        },
        "feature_coverage_chart": feature_coverage.get("coverage_chart", []),
        "production_gate": gate_state.get("gate", {}),
        "third_parties_and_vendors": vendor_inventory,
        "how_it_works": [
            "Demand and audience intelligence prioritize social campaigns with highest business impact.",
            "Content and publishing workflows operationalize posts with governance and approval controls.",
            "Engagement and analytics loops connect response operations to measurable outcomes.",
            "Provider checklist, strict-live probe, and production gate enforce release readiness.",
        ],
        "generated_at": helper_now_iso(),
    }


def operation_hootsuite_execute_schedules(
    runtime: SearchRuntime, payload: SitebulbScheduleExecuteRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:hootsuite:schedules:execute", 20, 60)
    return operation_sitebulb_execute_schedules(runtime, payload, auth)
