"""Search use cases: platform strict live probe."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SemrushProductionGateRequest
from .platform_run_provider_probes import helper_build_vendor_report
from .platform_run_provider_probes import helper_vendor_report_export
from .semrush_list_projects import operation_semrush_full_automation
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any


def helper_strict_live_probe(
    runtime: SearchRuntime, auth: AuthContext, payload: SemrushProductionGateRequest
) -> dict[str, Any]:
    try:
        probe_result = operation_semrush_full_automation(
            runtime,
            SemrushFullAutomationRequest(
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


def operation_vendors_report(
    runtime: SearchRuntime, auth: AuthDep, format: Annotated[str, Query(pattern="^(json|csv)$")] = "json"
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:vendors:report", 120, 60)
    report = helper_build_vendor_report(runtime, auth)
    if format == "csv":
        return helper_vendor_report_export(runtime, auth, format)
    return report


def operation_vendors_report_export(
    runtime: SearchRuntime, auth: AuthDep, format: Annotated[str, Query(pattern="^(json|csv)$")] = "json"
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:vendors:report:export", 120, 60)
    return helper_vendor_report_export(runtime, auth, format)
