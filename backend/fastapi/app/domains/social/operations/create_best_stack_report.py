"""Social use cases: create best stack report."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.schemas import BestStackReportCreateRequest
from ..constants import AuthDep
from ..services.capabilities import _strict_social_mode_enabled
from .integration_growth_specs import operation__build_best_stack_rows
from .invite_team_member_legacy import operation__build_growth_matrix
from .invite_team_member_legacy import operation_social_production_readiness
from datetime import UTC
from datetime import datetime
from fastapi import APIRouter
from typing import Any
from typing import cast


def operation_create_best_stack_report(
    st: _SocialWorkspaceState, router: APIRouter, payload: BestStackReportCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    """Create and persist an auditable best-stack JSON/Markdown report artifact."""
    st.enforce_rate_limit(f"{auth.tenant_id}:production-readiness:best-stack-report:create", 120, 60)
    readiness = operation_social_production_readiness(st, router, auth)
    stack_rows = operation__build_best_stack_rows(st, router, readiness)
    checks = [
        {"key": item.key, "label": item.label, "ok": item.ok, "detail": item.detail} for item in payload.probe_results
    ]
    passed = sum((1 for item in checks if bool(item.get("ok"))))
    failed = sum((1 for item in checks if not bool(item.get("ok"))))
    generated_at = datetime.now(UTC).isoformat()
    report_name = f"Best Stack Probe Report ({generated_at})"
    markdown_lines = [
        "# Best Stack Probe Report",
        "",
        f"- Generated at: {generated_at}",
        f"- Tenant: {auth.tenant_id}",
        f"- Readiness score: {int(readiness.get('readiness_score') or 0)}",
        f"- Production ready: {bool(readiness.get('production_ready'))}",
        f"- Probe checks: {passed} passed / {failed} failed",
        "",
        "## Stack Coverage",
        "",
        "| Stack | Status | Completion | Vendors |",
        "|---|---:|---:|---|",
    ]
    for row in stack_rows:
        markdown_lines.append(
            f"| {row['label']} | {row['status']} | {int(row['completion_percent'])}% | {', '.join(cast(list[str], row['vendors']))} |"
        )
    markdown_lines.extend(["", "## Probe Results", "", "| Check | Result | Detail |", "|---|---:|---|"])
    for item in checks:
        markdown_lines.append(f"| {item['label']} | {('PASS' if item['ok'] else 'FAIL')} | {str(item['detail'])} |")
    markdown_artifact = "\n".join(markdown_lines)
    artifact = {
        "summary": {
            "readiness_score": int(readiness.get("readiness_score") or 0),
            "production_ready": bool(readiness.get("production_ready")),
            "checks_total": len(checks),
            "checks_passed": passed,
            "checks_failed": failed,
        },
        "stack_coverage": stack_rows,
        "probe_results": checks,
        "generated_at": generated_at,
        "generated_by": payload.generated_by,
    }
    with st.lock:
        report_id = len(st.reports) + 1
        report = {
            "id": report_id,
            "tenant_id": auth.tenant_id,
            "name": report_name,
            "report_type": "best_stack_probe",
            "networks": ["social"],
            "date_range": "point_in_time",
            "metrics": ["readiness_score", "stack_completion", "probe_pass_rate"],
            "schedule": "manual",
            "export_format": "json_markdown",
            "status": "generated",
            "generated_at": generated_at,
            "export_url": f"/api/fastapi/social/production-readiness/best-stack-report/{report_id}/export",
            "created_at": generated_at,
            "artifact": artifact,
            "artifact_markdown": markdown_artifact,
        }
        st.reports.append(report)
    _sw_audit(st, auth.tenant_id, "social_best_stack_report_created", report_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "report": {
            "id": report_id,
            "name": report_name,
            "report_type": "best_stack_probe",
            "generated_at": generated_at,
            "export_url": f"/api/fastapi/social/production-readiness/best-stack-report/{report_id}/export",
        },
        "artifact": artifact,
        "artifact_markdown": markdown_artifact,
    }


def operation_social_growth_integration_matrix(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep
) -> dict[str, Any]:
    """Return integration-by-integration growth, ROI, and implementation completion chart."""
    st.enforce_rate_limit(f"{auth.tenant_id}:integrations:growth-matrix", 120, 60)
    strict_mode_enabled = _strict_social_mode_enabled()
    available_paths = {str(getattr(route, "path", "")) for route in router.routes}
    matrix, summary = operation__build_growth_matrix(
        st, router, available_paths=available_paths, strict_mode_enabled=strict_mode_enabled
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "strict_social_mode_enabled": strict_mode_enabled,
        "summary": summary,
        "matrix": matrix,
    }
