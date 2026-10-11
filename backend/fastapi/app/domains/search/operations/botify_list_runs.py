"""Search use cases: botify list runs."""

from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbRemediationBundleRequest
from ..schemas import SliceAssistRequest
from ..schemas import SliceProjectCreateRequest
from ..schemas import SliceProjectRunRequest
from ..schemas import SliceScheduleCreateRequest
from ..schemas import SliceScheduleExecuteRequest
from .platform_airanklab_completion_chart import helper_slice_completion_chart
from .platform_airanklab_completion_chart import helper_slice_gate_state
from .platform_now_iso import helper_now_iso
from .platform_now_iso import helper_slice_project_lookup
from .platform_now_iso import helper_slice_run_lookup
from .platform_run_provider_probes import helper_slice_provider_checklist
from .platform_search_vendors import helper_slice_verification
from .semrush_list_projects import operation_semrush_full_automation
from .sitebulb_completion_chart import helper_sitebulb_gate_progress
from .sitebulb_completion_chart import helper_sitebulb_remediation_bundle
from .sitebulb_project_lookup import helper_sitebulb_env_template
from .sitebulb_project_lookup import helper_sitebulb_preflight_report
from .sitebulb_project_lookup import helper_sitebulb_vendor_inventory
from .sitebulb_remediation_bundle_export import helper_sitebulb_remediation_bundle_export
from fastapi import Query
from typing import Annotated
from typing import Any


def operation_botify_list_runs(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:runs:list", 120, 60)
    runs = [item for item in runtime.botify_runs_memory if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "runs": runs}


def operation_botify_create_project(
    runtime: SearchRuntime, payload: SliceProjectCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:projects:create", 60, 60)
    project_id = f"btfproj-{auth.tenant_id}-{sum((1 for p in runtime.botify_projects_memory if p.get('tenant_id') == auth.tenant_id)) + 1}"
    project = {
        "id": project_id,
        "tenant_id": auth.tenant_id,
        "name": payload.name,
        "primary_domain": payload.primary_domain,
        "competitor_domains": payload.competitor_domains,
        "default_seed_keyword": payload.default_seed_keyword,
        "created_at": helper_now_iso(),
        "updated_at": helper_now_iso(),
    }
    runtime.botify_projects_memory.append(project)
    return {"status": "ok", "tenant_id": auth.tenant_id, "project": project}


def operation_botify_get_run(runtime: SearchRuntime, run_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:runs:get", 120, 60)
    run = helper_slice_run_lookup(runtime.botify_runs_memory, auth.tenant_id, run_id, "botify_run_not_found")
    return {"status": "ok", "tenant_id": auth.tenant_id, "run": run, "generated_at": helper_now_iso()}


def operation_botify_create_schedule(
    runtime: SearchRuntime, payload: SliceScheduleCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:schedules:create", 60, 60)
    helper_slice_project_lookup(
        runtime.botify_projects_memory, auth.tenant_id, payload.project_id, "botify_project_not_found"
    )
    schedule_id = f"btfsch-{auth.tenant_id}-{sum((1 for s in runtime.botify_schedules_memory if s.get('tenant_id') == auth.tenant_id)) + 1}"
    schedule = {
        "id": schedule_id,
        "tenant_id": auth.tenant_id,
        "project_id": payload.project_id,
        "cron": payload.cron,
        "enabled": payload.enabled,
        "created_at": helper_now_iso(),
    }
    runtime.botify_schedules_memory.append(schedule)
    return {"status": "ok", "tenant_id": auth.tenant_id, "schedule": schedule}


def operation_botify_provider_checklist(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:provider-checklist", 60, 60)
    return helper_slice_provider_checklist(auth)


def operation_botify_preflight(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:preflight", 60, 60)
    return helper_sitebulb_preflight_report(auth)


def operation_botify_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:vendors", 120, 60)
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


def operation_botify_env_template(
    runtime: SearchRuntime, payload: SitebulbEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:env-template", 60, 60)
    template = helper_sitebulb_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"botify-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_botify_assist_chat(runtime: SearchRuntime, payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:assist", 30, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "assist": {
            "summary": f"Botify assist summary for prompt: {payload.prompt[:120]}",
            "project_id": payload.project_id,
        },
        "context": {
            "include_vendor_context": payload.include_vendor_context,
            "vendors": helper_sitebulb_vendor_inventory(runtime, auth) if payload.include_vendor_context else [],
        },
        "generated_at": helper_now_iso(),
    }


def operation_botify_gate_progress(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:gate-progress", 60, 60)
    return helper_sitebulb_gate_progress(runtime, auth)


def operation_botify_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:parity", 60, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "vendor": "botify",
        "parity": helper_slice_completion_chart(runtime, auth, "botify_module", 10, force_integrated=False),
    }


def operation_botify_run_project(
    runtime: SearchRuntime, project_id: str, payload: SliceProjectRunRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:runs:create", 30, 60)
    project = helper_slice_project_lookup(
        runtime.botify_projects_memory, auth.tenant_id, project_id, "botify_project_not_found"
    )
    automation = operation_semrush_full_automation(
        runtime,
        SemrushFullAutomationRequest(
            seed_keyword=payload.seed_keyword or str(project.get("default_seed_keyword") or "social media management"),
            your_domain=str(project.get("primary_domain")),
            competitor_domains=list(project.get("competitor_domains") or ["semrush.com", "ahrefs.com"]),
            max_results=payload.max_results,
            require_live_providers=payload.require_live_providers,
        ),
        auth,
    )
    run_id = f"btfrun-{auth.tenant_id}-{sum((1 for r in runtime.botify_runs_memory if r.get('tenant_id') == auth.tenant_id)) + 1}"
    run = {
        "id": run_id,
        "tenant_id": auth.tenant_id,
        "project_id": project_id,
        "completed_at": helper_now_iso(),
        "run_mode": automation.get("run_mode"),
    }
    runtime.botify_runs_memory.append(run)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run": run,
        "botify_modules": helper_slice_completion_chart(runtime, auth, "botify_module", 10, force_integrated=False).get(
            "chart", []
        ),
        "third_party_and_vendors": helper_sitebulb_vendor_inventory(runtime, auth),
        "results": automation.get("results", {}),
        "generated_at": helper_now_iso(),
    }


def operation_botify_completion_chart(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:completion-chart", 60, 60)
    return helper_slice_completion_chart(runtime, auth, "botify_module", 10, force_integrated=False)


def operation_botify_execute_schedules(
    runtime: SearchRuntime, payload: SliceScheduleExecuteRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:schedules:execute", 20, 60)
    schedules = [
        item
        for item in runtime.botify_schedules_memory
        if item.get("tenant_id") == auth.tenant_id and bool(item.get("enabled"))
    ]
    executed: list[dict[str, Any]] = []
    for schedule in schedules:
        run_payload = SliceProjectRunRequest(
            seed_keyword=None, max_results=12, require_live_providers=False, include_assist_summary=False
        )
        run_resp = operation_botify_run_project(runtime, str(schedule.get("project_id")), run_payload, auth)
        executed.append(
            {
                "schedule_id": schedule.get("id"),
                "project_id": schedule.get("project_id"),
                "run_id": run_resp.get("run", {}).get("id"),
            }
        )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "due_only": payload.due_only,
        "executed_count": len(executed),
        "executed": executed,
        "generated_at": helper_now_iso(),
    }


def operation_botify_remediation_bundle(
    runtime: SearchRuntime, payload: SitebulbRemediationBundleRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:remediation-bundle", 30, 60)
    return helper_sitebulb_remediation_bundle(runtime, payload, auth)


def operation_botify_production_gate(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:production-gate", 60, 60)
    completion = operation_botify_completion_chart(runtime, auth)
    return helper_slice_gate_state(runtime, auth, completion, force_passed=False)


def operation_botify_remediation_bundle_export(
    runtime: SearchRuntime,
    auth: AuthDep,
    format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
    top_steps: int = Query(default=10, ge=1, le=100),
    include_optional: bool = Query(default=False),
    include_configured: bool = Query(default=False),
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:remediation-bundle:export", 30, 60)
    payload = SitebulbRemediationBundleRequest(
        top_steps=top_steps, include_optional=include_optional, include_configured=include_configured
    )
    return helper_sitebulb_remediation_bundle_export(runtime, payload, auth, format)


def operation_botify_verification_report(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:botify:verification-report", 30, 60)
    completion = operation_botify_completion_chart(runtime, auth)
    gate = operation_botify_production_gate(runtime, auth)
    return helper_slice_verification(auth, completion, gate, "botify")
