"""Social use cases: export best stack report."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ..constants import AuthDep
from ..constants import REPORT_NOT_FOUND
from ..services.workspace import _sw_http_error
from fastapi import APIRouter
from typing import Any
from typing import cast


def operation_export_best_stack_report(
    st: _SocialWorkspaceState, router: APIRouter, report_id: int, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:production-readiness:best-stack-report:export", 120, 60)
    with st.lock:
        report = next(
            (
                item
                for item in st.reports
                if item.get("tenant_id") == auth.tenant_id
                and item.get("report_type") == "best_stack_probe"
                and (int(item.get("id") or 0) == report_id)
            ),
            None,
        )
        if report is None:
            raise _sw_http_error(status_code=404, detail=REPORT_NOT_FOUND)
        artifact = cast(dict[str, Any], report.get("artifact") or {})
        markdown = str(report.get("artifact_markdown") or "")
    _sw_audit(st, auth.tenant_id, "social_best_stack_report_exported", report_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "report": {"id": report.get("id"), "name": report.get("name"), "generated_at": report.get("generated_at")},
        "artifact": artifact,
        "artifact_markdown": markdown,
    }


def operation_get_social_audit_log(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep, limit: int = 100
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:audit-log", 120, 60)
    safe_limit = max(1, min(int(limit), 500))
    with st.lock:
        rows = [item for item in st.audit_log if item.get("tenant_id") == auth.tenant_id]
    rows = list(reversed(rows))[:safe_limit]
    return {"status": "ok", "tenant_id": auth.tenant_id, "audit_log": rows, "count": len(rows)}
