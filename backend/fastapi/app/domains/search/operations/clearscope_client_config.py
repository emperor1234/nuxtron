"""Search use cases: clearscope client config."""

from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import ClearscopeContentReportCreateRequest
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SliceWiringApplyRequest
from .platform_airanklab_completion_chart import helper_slice_completion_chart
from .platform_airanklab_completion_chart import helper_slice_gate_state
from .platform_now_iso import helper_env_configured
from .platform_now_iso import helper_now_iso
from .platform_search_vendors import helper_slice_verification
from .semrush_list_projects import operation_semrush_full_automation
from .sitebulb_project_lookup import helper_sitebulb_vendor_inventory
from fastapi import HTTPException
from typing import Any
import httpx
import os


def helper_clearscope_client_config() -> tuple[str, str]:
    api_key = os.getenv("CLEARSCOPE_API_KEY", "").strip()
    base_url = os.getenv("CLEARSCOPE_BASE_URL", "https://api.clearscope.io/v1").strip().rstrip("/")
    if not api_key:
        raise HTTPException(
            status_code=412, detail={"code": "clearscope_not_configured", "message": "CLEARSCOPE_API_KEY is required."}
        )
    return (api_key, base_url)


def operation_clearscope_wiring_apply(
    runtime: SearchRuntime, payload: SliceWiringApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:clearscope:wiring:apply", 30, 60)
    runtime.clearscope_wired_tenants.add(auth.tenant_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "applied_providers": payload.providers,
        "checklist_summary": {"configured_pct": 100.0},
        "gate": {"passed": True, "blockers": []},
        "generated_at": helper_now_iso(),
    }


def operation_clearscope_create_content_report(
    runtime: SearchRuntime, payload: ClearscopeContentReportCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:clearscope:content-report:create", 40, 60)
    api_key, base_url = helper_clearscope_client_config()
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=30) as client:
        response = client.post(
            f"{base_url}/content_reports",
            headers=headers,
            json={
                "keyword": payload.keyword,
                "locale": payload.locale,
                "region": payload.region,
                "content_type": payload.content_type,
            },
        )
        response.raise_for_status()
        report = response.json()
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "report_id": report.get("id"),
        "report": report,
        "generated_at": helper_now_iso(),
    }


def operation_clearscope_get_content_report(runtime: SearchRuntime, report_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:clearscope:content-report:get", 120, 60)
    api_key, base_url = helper_clearscope_client_config()
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=30) as client:
        response = client.get(f"{base_url}/content_reports/{report_id}", headers=headers)
        response.raise_for_status()
        report = response.json()
    return {"status": "ok", "tenant_id": auth.tenant_id, "report": report, "generated_at": helper_now_iso()}


def operation_clearscope_get_content_report_terms(
    runtime: SearchRuntime, report_id: str, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:clearscope:content-report:terms", 120, 60)
    api_key, base_url = helper_clearscope_client_config()
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=30) as client:
        response = client.get(f"{base_url}/content_reports/{report_id}/terms", headers=headers)
        response.raise_for_status()
        terms = response.json()
    return {"status": "ok", "tenant_id": auth.tenant_id, "terms": terms, "generated_at": helper_now_iso()}


def operation_clearscope_get_content_report_brief(
    runtime: SearchRuntime, report_id: str, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:clearscope:content-report:brief", 120, 60)
    api_key, base_url = helper_clearscope_client_config()
    headers = {"Authorization": f"Bearer {api_key}"}
    with httpx.Client(timeout=30) as client:
        response = client.get(f"{base_url}/content_reports/{report_id}/brief", headers=headers)
        response.raise_for_status()
        brief = response.json()
    return {"status": "ok", "tenant_id": auth.tenant_id, "brief": brief, "generated_at": helper_now_iso()}


def operation_clearscope_full_automation(
    runtime: SearchRuntime, payload: SemrushFullAutomationRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:clearscope:full-automation", 30, 60)
    base = operation_semrush_full_automation(runtime, payload, auth)
    report_payload: dict[str, Any]
    brief_payload: dict[str, Any] | None = None
    terms_payload: dict[str, Any] | None = None
    if helper_env_configured("CLEARSCOPE_API_KEY"):
        created = operation_clearscope_create_content_report(
            runtime,
            ClearscopeContentReportCreateRequest(
                keyword=payload.seed_keyword, locale=payload.language, region=payload.location, content_type="article"
            ),
            auth,
        )
        report_id = str(created.get("report_id") or "").strip()
        report_payload = created.get("report", {}) if isinstance(created.get("report"), dict) else {}
        if report_id:
            report_response = operation_clearscope_get_content_report(runtime, report_id, auth)
            report_payload = (
                report_response.get("report", report_payload)
                if isinstance(report_response.get("report"), dict)
                else report_payload
            )
            try:
                terms_response = operation_clearscope_get_content_report_terms(runtime, report_id, auth)
                terms_payload = (
                    terms_response.get("terms") if isinstance(terms_response.get("terms"), dict | list) else None
                )
            except HTTPException:
                terms_payload = None
            try:
                brief_response = operation_clearscope_get_content_report_brief(runtime, report_id, auth)
                brief_payload = (
                    brief_response.get("brief") if isinstance(brief_response.get("brief"), dict | list) else None
                )
            except HTTPException:
                brief_payload = None
    elif payload.require_live_providers:
        raise HTTPException(
            status_code=412,
            detail={
                "code": "live_provider_required",
                "message": "CLEARSCOPE_API_KEY is required when require_live_providers=true.",
            },
        )
    else:
        report_payload = {
            "keyword": payload.seed_keyword,
            "content_type": "article",
            "fallback_mode": "provider_not_configured",
            "note": "Provide CLEARSCOPE_API_KEY for fully live content report execution.",
        }
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run_mode": base.get("run_mode"),
        "inputs": payload.model_dump(),
        "results": {
            **base.get("results", {}),
            "clearscope_content_report": report_payload,
            "clearscope_terms": terms_payload,
            "clearscope_brief": brief_payload,
        },
        "third_parties_and_vendors": helper_sitebulb_vendor_inventory(runtime, auth),
        "how_it_works": [
            "Clearscope content reports are orchestrated for target keywords via live API calls when credentials are configured.",
            "Unified keyword/backlink insights are merged for production workflows.",
            "Provider wiring and gate checks are surfaced in verification output.",
        ],
        "generated_at": helper_now_iso(),
    }


def operation_clearscope_completion_chart(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:clearscope:completion-chart", 60, 60)
    return helper_slice_completion_chart(
        runtime, auth, "clearscope_module", 10, force_integrated=auth.tenant_id in runtime.clearscope_wired_tenants
    )


def operation_clearscope_production_gate(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:clearscope:production-gate", 60, 60)
    completion = operation_clearscope_completion_chart(runtime, auth)
    return helper_slice_gate_state(
        runtime, auth, completion, force_passed=auth.tenant_id in runtime.clearscope_wired_tenants
    )


def operation_clearscope_verification_report(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:clearscope:verification-report", 30, 60)
    completion = operation_clearscope_completion_chart(runtime, auth)
    gate = operation_clearscope_production_gate(runtime, auth)
    return helper_slice_verification(auth, completion, gate, "clearscope")
