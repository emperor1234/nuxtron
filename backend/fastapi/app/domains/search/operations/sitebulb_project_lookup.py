"""Search use cases: sitebulb project lookup."""

from ....deps import AuthContext
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushEnvTemplateRequest
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbProjectCreateRequest
from ..schemas import SitebulbScheduleCreateRequest
from .platform_now_iso import helper_now_iso
from .platform_run_provider_probes import helper_env_template
from .platform_run_provider_probes import operation_vendors
from .platform_search_vendors import helper_provider_requirements
from fastapi import HTTPException
from typing import Any


def helper_sitebulb_project_lookup(runtime: SearchRuntime, tenant_id: str, project_id: str) -> dict[str, Any]:
    for project in runtime.sitebulb_projects_memory:
        if str(project.get("tenant_id")) == tenant_id and str(project.get("id")) == project_id:
            return project
    raise HTTPException(status_code=404, detail={"code": "sitebulb_project_not_found", "project_id": project_id})


def helper_sitebulb_run_lookup(runtime: SearchRuntime, tenant_id: str, run_id: str) -> dict[str, Any]:
    for run in runtime.sitebulb_runs_memory:
        if str(run.get("tenant_id")) == tenant_id and str(run.get("id")) == run_id:
            return run
    raise HTTPException(status_code=404, detail={"code": "sitebulb_run_not_found", "run_id": run_id})


def helper_sitebulb_issue_chart(
    *, automation_result: dict[str, Any], strict_probe: dict[str, Any], checklist: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    keyword_discovery = automation_result.get("results", {}).get("keyword_discovery", {})
    backlink_audit = automation_result.get("results", {}).get("backlink_audit", {})
    if strict_probe.get("status") != "passed":
        issues.append(
            {
                "type": "integration",
                "severity": "critical",
                "title": "Strict live keyword probe is failing",
                "evidence": strict_probe,
                "recommended_fix": "Configure missing keyword providers and re-run production gate.",
            }
        )
    if bool(keyword_discovery.get("fallback_used")):
        issues.append(
            {
                "type": "data_quality",
                "severity": "high",
                "title": "Keyword discovery used fallback provider chain",
                "evidence": {
                    "provider_selected": keyword_discovery.get("provider_selected"),
                    "fallback_used": keyword_discovery.get("fallback_used"),
                },
                "recommended_fix": "Enable at least one strict-live provider for non-synthetic keyword data.",
            }
        )
    toxic_count = int(backlink_audit.get("toxic_count") or 0)
    if toxic_count > 0:
        issues.append(
            {
                "type": "backlink_risk",
                "severity": "medium",
                "title": "Potentially toxic backlinks detected",
                "evidence": {"toxic_count": toxic_count, "risk_level": backlink_audit.get("risk_level")},
                "recommended_fix": "Review disavow candidates and update off-page remediation backlog.",
            }
        )
    for item in checklist:
        if item.get("configured"):
            continue
        issues.append(
            {
                "type": "integration",
                "severity": "high",
                "title": f"Provider not configured: {item.get('provider')}",
                "evidence": {"required_missing": item.get("required_missing", [])},
                "recommended_fix": "Set missing required environment variables and re-run provider probes.",
            }
        )
    return issues


def helper_sitebulb_remediation_export_rows(bundle_payload: dict[str, Any]) -> list[dict[str, Any]]:
    bundle = bundle_payload.get("bundle", {})
    preflight = bundle.get("preflight", {})
    progression = bundle.get("gate_progress", {}).get("provider_progression", [])
    progression_index = {str(item.get("provider", "")): item for item in progression}
    gate_state = bundle.get("gate_state", {})
    blockers = ";".join((str(item) for item in gate_state.get("blockers", [])))
    rows: list[dict[str, Any]] = []
    for item in preflight.get("missing_provider_steps", []):
        provider = str(item.get("provider", ""))
        projected = progression_index.get(provider, {})
        rows.append(
            {
                "provider": provider,
                "kind": str(item.get("kind", "")),
                "priority": str(item.get("priority", "")),
                "required_missing": ";".join((str(v) for v in item.get("required_missing", []))),
                "integration_pct_if_added": projected.get("integration_pct_if_added", ""),
                "gate_passed": bool(gate_state.get("passed", False)),
                "gate_blockers": blockers,
            }
        )
    return rows


def helper_sitebulb_remediation_export_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    headers = [
        "provider",
        "kind",
        "priority",
        "required_missing",
        "integration_pct_if_added",
        "gate_passed",
        "gate_blockers",
    ]
    lines = [",".join(headers)]
    for row in rows:
        values: list[str] = []
        for key in headers:
            value = str(row.get(key, "")).replace('"', '""')
            values.append(f'"{value}"')
        lines.append(",".join(values))
    return "\n".join(lines)


def operation_sitebulb_create_project(
    runtime: SearchRuntime, payload: SitebulbProjectCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:projects:create", 60, 60)
    project_id = f"sbproj-{auth.tenant_id}-{sum((1 for p in runtime.sitebulb_projects_memory if p.get('tenant_id') == auth.tenant_id)) + 1}"
    project = {
        "id": project_id,
        "tenant_id": auth.tenant_id,
        "name": payload.name,
        "primary_domain": payload.primary_domain,
        "crawl_urls": payload.crawl_urls,
        "render_javascript": payload.render_javascript,
        "emulate_mobile": payload.emulate_mobile,
        "max_urls": payload.max_urls,
        "default_seed_keyword": payload.default_seed_keyword,
        "default_competitors": payload.default_competitors,
        "created_at": helper_now_iso(),
        "updated_at": helper_now_iso(),
    }
    runtime.sitebulb_projects_memory.append(project)
    return {"status": "ok", "tenant_id": auth.tenant_id, "project": project}


def operation_sitebulb_list_projects(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:projects:list", 120, 60)
    projects = [p.copy() for p in runtime.sitebulb_projects_memory if p.get("tenant_id") == auth.tenant_id]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(projects),
        "projects": projects,
        "generated_at": helper_now_iso(),
    }


def operation_sitebulb_list_runs(
    runtime: SearchRuntime, auth: AuthDep, project_id: str | None = None
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:runs:list", 120, 60)
    runs = [r.copy() for r in runtime.sitebulb_runs_memory if r.get("tenant_id") == auth.tenant_id]
    if project_id:
        runs = [r for r in runs if str(r.get("project_id")) == project_id]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(runs),
        "runs": runs,
        "generated_at": helper_now_iso(),
    }


def operation_sitebulb_get_run(runtime: SearchRuntime, run_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:runs:get", 120, 60)
    run_record = helper_sitebulb_run_lookup(runtime, auth.tenant_id, run_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "run": run_record, "generated_at": helper_now_iso()}


def operation_sitebulb_create_schedule(
    runtime: SearchRuntime, payload: SitebulbScheduleCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:schedules:create", 60, 60)
    helper_sitebulb_project_lookup(runtime, auth.tenant_id, payload.project_id)
    schedule_id = f"sbsch-{auth.tenant_id}-{sum((1 for s in runtime.sitebulb_schedules_memory if s.get('tenant_id') == auth.tenant_id)) + 1}"
    schedule = {
        "id": schedule_id,
        "tenant_id": auth.tenant_id,
        "project_id": payload.project_id,
        "cron": payload.cron,
        "enabled": payload.enabled,
        "created_at": helper_now_iso(),
        "updated_at": helper_now_iso(),
    }
    runtime.sitebulb_schedules_memory.append(schedule)
    return {"status": "ok", "tenant_id": auth.tenant_id, "schedule": schedule}


def operation_sitebulb_list_schedules(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:schedules:list", 120, 60)
    schedules = [s.copy() for s in runtime.sitebulb_schedules_memory if s.get("tenant_id") == auth.tenant_id]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(schedules),
        "schedules": schedules,
        "generated_at": helper_now_iso(),
    }


def helper_sitebulb_preflight_report(auth: AuthContext) -> dict[str, Any]:
    checklist = helper_provider_requirements()
    missing_rows: list[dict[str, Any]] = []
    for item in checklist:
        if item.get("configured"):
            continue
        provider = str(item.get("provider", ""))
        kind = str(item.get("kind", "integration"))
        priority = "P0" if kind == "keyword_provider" else "P1"
        missing_required = [str(env_name) for env_name in item.get("required_missing", [])]
        missing_rows.append(
            {
                "provider": provider,
                "kind": kind,
                "priority": priority,
                "required_missing": missing_required,
                "verify_with": [
                    "GET /search-everywhere/sitebulb/completion-chart",
                    "GET /search-everywhere/sitebulb/production-gate",
                    "POST /search-everywhere/semrush/provider-probes",
                ],
                "preflight_commands_powershell": [f"Test-Path Env:{env_name}" for env_name in missing_required],
            }
        )
    missing_rows.sort(key=lambda row: (0 if row["priority"] == "P0" else 1, row["provider"]))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "configured": sum((1 for item in checklist if item.get("configured"))),
        "total": len(checklist),
        "configured_pct": round(
            sum((1 for item in checklist if item.get("configured"))) / max(len(checklist), 1) * 100.0, 1
        ),
        "missing_provider_steps": missing_rows,
        "generated_at": helper_now_iso(),
    }


def helper_sitebulb_vendor_inventory(runtime: SearchRuntime, auth: AuthContext) -> list[dict[str, Any]]:
    vendors_payload = operation_vendors(runtime, auth)
    vendor_chart = [dict(item) for item in vendors_payload.get("unified_vendor_chart", [])]
    provider_checklist = helper_provider_requirements()
    for item in provider_checklist:
        vendor_chart.append(
            {
                "source": "sitebulb_keyword_pipeline",
                "vendor": item["provider"],
                "category": item["kind"],
                "integration": item["provider"].strip().lower().replace(" ", "_"),
                "configured_units": 1 if item.get("configured") else 0,
                "total_units": 1,
                "runtime_dependency": True,
            }
        )
    vendor_chart.sort(key=lambda row: (str(row.get("source", "")), str(row.get("vendor", ""))))
    return vendor_chart


def helper_sitebulb_env_template(payload: SitebulbEnvTemplateRequest) -> dict[str, Any]:
    template = helper_env_template(
        SemrushEnvTemplateRequest(
            include_optional=payload.include_optional, include_configured=payload.include_configured
        )
    )
    return {
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "content": template["content"],
    }


def operation_sitebulb_preflight(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:preflight", 60, 60)
    return helper_sitebulb_preflight_report(auth)


def operation_sitebulb_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:vendors", 120, 60)
    inventory = helper_sitebulb_vendor_inventory(runtime, auth)
    configured = sum((1 for item in inventory if int(item.get("configured_units", 0) or 0) >= 1))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "vendors_total": len(inventory),
        "vendors_configured": configured,
        "vendor_chart": inventory,
        "generated_at": helper_now_iso(),
    }


def operation_sitebulb_env_template(
    runtime: SearchRuntime, payload: SitebulbEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:sitebulb:env-template", 60, 60)
    template = helper_sitebulb_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"sitebulb-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }
