"""Search use cases: sitebulb remediation bundle export."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SitebulbRemediationBundleRequest
from .platform_now_iso import helper_now_iso
from .sitebulb_completion_chart import helper_sitebulb_remediation_bundle
from .sitebulb_completion_chart import helper_sitebulb_verification_report
from .sitebulb_project_lookup import helper_sitebulb_remediation_export_csv
from .sitebulb_project_lookup import helper_sitebulb_remediation_export_rows
from fastapi import Query
from typing import Annotated
from typing import Any


def helper_sitebulb_remediation_bundle_export(
    runtime: SearchRuntime, payload: SitebulbRemediationBundleRequest, auth: AuthContext, export_format: str
) -> dict[str, Any]:
    bundle_payload = helper_sitebulb_remediation_bundle(runtime, payload, auth)
    rows = helper_sitebulb_remediation_export_rows(bundle_payload)
    base = {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "format": export_format,
        "count": len(rows),
        "generated_at": helper_now_iso(),
    }
    if export_format == "csv":
        return {
            **base,
            "filename": f"sitebulb-remediation-bundle-{auth.tenant_id}.csv",
            "csv": helper_sitebulb_remediation_export_csv(rows),
        }
    return {**base, "filename": f"sitebulb-remediation-bundle-{auth.tenant_id}.json", "json": rows}


def operation_sitebulb_remediation_bundle(
    runtime: SearchRuntime, payload: SitebulbRemediationBundleRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:remediation-bundle", 30, 60)
    return helper_sitebulb_remediation_bundle(runtime, payload, auth)


def operation_sitebulb_verification_report(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:verification-report", 30, 60)
    return helper_sitebulb_verification_report(runtime, auth)


def operation_sitebulb_remediation_bundle_export(
    runtime: SearchRuntime,
    auth: AuthDep,
    format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
    top_steps: int = Query(default=10, ge=1, le=100),
    include_optional: bool = Query(default=False),
    include_configured: bool = Query(default=False),
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:remediation-bundle:export", 30, 60)
    payload = SitebulbRemediationBundleRequest(
        top_steps=top_steps, include_optional=include_optional, include_configured=include_configured
    )
    return helper_sitebulb_remediation_bundle_export(runtime, payload, auth, format)
