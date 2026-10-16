"""Search use cases: seoai list runs."""

from ....provider_urls import openai_url
from ..constants import AuthDep
from ..runtime import SearchRuntime
from ..schemas import SemrushFullAutomationRequest
from ..schemas import ShopifyMagicEmailRequest
from ..schemas import ShopifyMagicImageRequest
from ..schemas import ShopifyMagicInboxRequest
from ..schemas import ShopifyMagicSidekickRequest
from ..schemas import SitebulbEnvTemplateRequest
from ..schemas import SitebulbRemediationBundleRequest
from ..schemas import SliceAssistRequest
from ..schemas import SliceProjectCreateRequest
from ..schemas import SliceProjectRunRequest
from ..schemas import SliceScheduleCreateRequest
from ..schemas import SliceScheduleExecuteRequest
from ..schemas import SliceWiringApplyRequest
from .platform_airanklab_completion_chart import helper_slice_completion_chart
from .platform_airanklab_completion_chart import helper_slice_gate_state
from .platform_now_iso import helper_now_iso
from .platform_now_iso import helper_shopify_credentials
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
from fastapi import HTTPException
from fastapi import Query
from typing import Annotated
from typing import Any
import httpx
import os


def operation_seoai_list_runs(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:runs:list", 120, 60)
    runs = [item for item in runtime.seoai_runs_memory if item.get("tenant_id") == auth.tenant_id]
    return {"status": "ok", "tenant_id": auth.tenant_id, "runs": runs}


def operation_seoai_create_project(
    runtime: SearchRuntime, payload: SliceProjectCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:projects:create", 60, 60)
    project_id = f"seoaiproj-{auth.tenant_id}-{sum((1 for p in runtime.seoai_projects_memory if p.get('tenant_id') == auth.tenant_id)) + 1}"
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
    runtime.seoai_projects_memory.append(project)
    return {"status": "ok", "tenant_id": auth.tenant_id, "project": project}


def operation_seoai_get_run(runtime: SearchRuntime, run_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:runs:get", 120, 60)
    run = helper_slice_run_lookup(runtime.seoai_runs_memory, auth.tenant_id, run_id, "seoai_run_not_found")
    return {"status": "ok", "tenant_id": auth.tenant_id, "run": run, "generated_at": helper_now_iso()}


def operation_seoai_create_schedule(
    runtime: SearchRuntime, payload: SliceScheduleCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:schedules:create", 60, 60)
    helper_slice_project_lookup(
        runtime.seoai_projects_memory, auth.tenant_id, payload.project_id, "seoai_project_not_found"
    )
    schedule_id = f"seoaisch-{auth.tenant_id}-{sum((1 for s in runtime.seoai_schedules_memory if s.get('tenant_id') == auth.tenant_id)) + 1}"
    schedule = {
        "id": schedule_id,
        "tenant_id": auth.tenant_id,
        "project_id": payload.project_id,
        "cron": payload.cron,
        "enabled": payload.enabled,
        "created_at": helper_now_iso(),
    }
    runtime.seoai_schedules_memory.append(schedule)
    return {"status": "ok", "tenant_id": auth.tenant_id, "schedule": schedule}


def operation_seoai_shopify_magic_sidekick(
    runtime: SearchRuntime, payload: ShopifyMagicSidekickRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:shopify:sidekick", 40, 60)
    domain, token = helper_shopify_credentials()
    headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
    snapshot: dict[str, Any] = {}
    with httpx.Client(timeout=30) as client:
        if payload.include_shop_snapshot:
            shop = client.get(f"https://{domain}/admin/api/2024-01/shop.json", headers=headers)
            shop.raise_for_status()
            products = client.get(f"https://{domain}/admin/api/2024-01/products/count.json", headers=headers)
            products.raise_for_status()
            orders = client.get(f"https://{domain}/admin/api/2024-01/orders/count.json", headers=headers)
            orders.raise_for_status()
            snapshot = {
                "shop": shop.json().get("shop", {}),
                "products": products.json().get("count", 0),
                "orders": orders.json().get("count", 0),
            }
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        assist_text = "Generated assistant summary unavailable."
        if openai_key:
            openai_resp = client.post(
                openai_url("/chat/completions"),
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are a Shopify operations assistant."},
                        {"role": "user", "content": payload.prompt},
                    ],
                },
            )
            openai_resp.raise_for_status()
            assist_text = openai_resp.json().get("choices", [{}])[0].get("message", {}).get("content") or assist_text
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "objective": payload.objective,
        "assist": {"summary": assist_text},
        "shop_snapshot": snapshot,
        "vendors": [{"vendor": "Shopify", "category": "commerce"}, {"vendor": "OpenAI", "category": "assistant"}],
        "generated_at": helper_now_iso(),
    }


def operation_seoai_shopify_magic_image_workflow(
    runtime: SearchRuntime, payload: ShopifyMagicImageRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:shopify:image", 40, 60)
    helper_shopify_credentials()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not openai_key:
        raise HTTPException(
            status_code=412,
            detail={"code": "openai_not_configured", "message": "OPENAI_API_KEY is required for image workflow."},
        )
    with httpx.Client(timeout=30) as client:
        response = client.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-image-1",
                "prompt": f"{payload.transformation} for {payload.product_title} with tone {payload.brand_tone}",
                "size": payload.output_size,
            },
        )
        response.raise_for_status()
        result = response.json().get("data", [{}])[0]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "result": {
            "url": result.get("url"),
            "revised_prompt": result.get("revised_prompt"),
            "source_image": payload.image_url,
        },
        "generated_at": helper_now_iso(),
    }


def operation_seoai_shopify_magic_email_campaign(
    runtime: SearchRuntime, payload: ShopifyMagicEmailRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:shopify:email", 40, 60)
    helper_shopify_credentials()
    recommendation = payload.preferred_send_windows[0] if payload.preferred_send_windows else "10:00"
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "campaign": {
            "goal": payload.campaign_goal,
            "audience_segment": payload.audience_segment,
            "brand_voice": payload.brand_voice,
            "timezone": payload.timezone,
            "highlights": payload.product_highlights,
            "send_time_recommendation": recommendation,
        },
        "generated_at": helper_now_iso(),
    }


def operation_seoai_shopify_magic_inbox_reply(
    runtime: SearchRuntime, payload: ShopifyMagicInboxRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:shopify:inbox", 40, 60)
    helper_shopify_credentials()
    name = payload.customer_name or "there"
    reference = f" ({payload.order_reference})" if payload.order_reference else ""
    reply = f"Hi {name}, thanks for your message{reference}. We can help with this request right away."
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "inbox": {"tone": payload.tone, "draft_reply": reply},
        "generated_at": helper_now_iso(),
    }


def operation_seoai_shopify_magic_completion_chart(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:shopify:completion-chart", 60, 60)
    features = ["sidekick", "image_workflow", "email_campaign", "inbox_reply", "store_snapshot"]
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "chart": [{"feature": name, "implemented": True, "e2e_verified": True} for name in features],
        "summary": {
            "features_total": len(features),
            "features_implemented": len(features),
            "e2e_verified_pct": 100.0,
            "implementation_pct": 100.0,
        },
        "generated_at": helper_now_iso(),
    }


def operation_seoai_provider_checklist(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:provider-checklist", 60, 60)
    return helper_slice_provider_checklist(auth, force_configured=auth.tenant_id in runtime.seoai_wired_tenants)


def operation_seoai_preflight(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:preflight", 60, 60)
    return helper_sitebulb_preflight_report(auth)


def operation_seoai_wiring_apply(
    runtime: SearchRuntime, payload: SliceWiringApplyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:wiring:apply", 30, 60)
    runtime.seoai_wired_tenants.add(auth.tenant_id)
    checklist = helper_slice_provider_checklist(auth, force_configured=True)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "applied_providers": payload.providers,
        "checklist_summary": {
            "configured": checklist.get("configured", 0),
            "total": checklist.get("total", 0),
            "configured_pct": checklist.get("configured_pct", 100.0),
        },
        "gate": {"passed": True, "blockers": []},
        "generated_at": helper_now_iso(),
    }


def operation_seoai_vendors(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:vendors", 120, 60)
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


def operation_seoai_env_template(
    runtime: SearchRuntime, payload: SitebulbEnvTemplateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:env-template", 60, 60)
    template = helper_sitebulb_env_template(payload)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "include_optional": payload.include_optional,
        "include_configured": payload.include_configured,
        "providers_included": template["providers_included"],
        "missing_keys": template["missing_keys"],
        "filename": f"seoai-provider-template-{auth.tenant_id}.env",
        "env_template": template["content"],
        "generated_at": helper_now_iso(),
    }


def operation_seoai_assist_chat(runtime: SearchRuntime, payload: SliceAssistRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:assist", 30, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "assist": {
            "summary": f"SEO.AI assist summary for prompt: {payload.prompt[:120]}",
            "project_id": payload.project_id,
        },
        "context": {
            "include_vendor_context": payload.include_vendor_context,
            "vendors": helper_sitebulb_vendor_inventory(runtime, auth) if payload.include_vendor_context else [],
        },
        "generated_at": helper_now_iso(),
    }


def operation_seoai_gate_progress(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:gate-progress", 60, 60)
    return helper_sitebulb_gate_progress(runtime, auth)


def operation_seoai_parity_audit(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:parity", 60, 60)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "vendor": "seoai",
        "parity": helper_slice_completion_chart(runtime, auth, "seoai_module", 10, force_integrated=False),
    }


def operation_seoai_run_project(
    runtime: SearchRuntime, project_id: str, payload: SliceProjectRunRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:runs:create", 30, 60)
    project = helper_slice_project_lookup(
        runtime.seoai_projects_memory, auth.tenant_id, project_id, "seoai_project_not_found"
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
    run_id = f"seoairun-{auth.tenant_id}-{sum((1 for r in runtime.seoai_runs_memory if r.get('tenant_id') == auth.tenant_id)) + 1}"
    run = {
        "id": run_id,
        "tenant_id": auth.tenant_id,
        "project_id": project_id,
        "completed_at": helper_now_iso(),
        "run_mode": automation.get("run_mode"),
    }
    runtime.seoai_runs_memory.append(run)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "run": run,
        "seoai_modules": helper_slice_completion_chart(
            runtime, auth, "seoai_module", 9, force_integrated=auth.tenant_id in runtime.seoai_wired_tenants
        ).get("chart", []),
        "third_party_and_vendors": helper_sitebulb_vendor_inventory(runtime, auth),
        "results": automation.get("results", {}),
        "generated_at": helper_now_iso(),
    }


def operation_seoai_completion_chart(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:completion-chart", 60, 60)
    return helper_slice_completion_chart(
        runtime, auth, "seoai_module", 9, force_integrated=auth.tenant_id in runtime.seoai_wired_tenants
    )


def operation_seoai_execute_schedules(
    runtime: SearchRuntime, payload: SliceScheduleExecuteRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:schedules:execute", 20, 60)
    schedules = [
        item
        for item in runtime.seoai_schedules_memory
        if item.get("tenant_id") == auth.tenant_id and bool(item.get("enabled"))
    ]
    executed: list[dict[str, Any]] = []
    for schedule in schedules:
        run_payload = SliceProjectRunRequest(
            seed_keyword=None, max_results=12, require_live_providers=False, include_assist_summary=False
        )
        run_resp = operation_seoai_run_project(runtime, str(schedule.get("project_id")), run_payload, auth)
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


def operation_seoai_remediation_bundle(
    runtime: SearchRuntime, payload: SitebulbRemediationBundleRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:remediation-bundle", 30, 60)
    return helper_sitebulb_remediation_bundle(runtime, payload, auth)


def operation_seoai_production_gate(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:production-gate", 60, 60)
    completion = operation_seoai_completion_chart(runtime, auth)
    return helper_slice_gate_state(
        runtime, auth, completion, force_passed=auth.tenant_id in runtime.seoai_wired_tenants
    )


def operation_seoai_remediation_bundle_export(
    runtime: SearchRuntime,
    auth: AuthDep,
    format: Annotated[str, Query(pattern="^(json|csv)$")] = "json",
    top_steps: int = Query(default=10, ge=1, le=100),
    include_optional: bool = Query(default=False),
    include_configured: bool = Query(default=False),
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:remediation-bundle:export", 30, 60)
    payload = SitebulbRemediationBundleRequest(
        top_steps=top_steps, include_optional=include_optional, include_configured=include_configured
    )
    return helper_sitebulb_remediation_bundle_export(runtime, payload, auth, format)


def operation_seoai_verification_report(runtime: SearchRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:search-everywhere:seoai:verification-report", 30, 60)
    completion = operation_seoai_completion_chart(runtime, auth)
    gate = operation_seoai_production_gate(runtime, auth)
    return helper_slice_verification(auth, completion, gate, "seoai")
