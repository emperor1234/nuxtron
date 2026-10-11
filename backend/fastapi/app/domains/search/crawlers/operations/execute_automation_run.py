"""Search/Crawlers use cases: execute automation run."""

from __future__ import annotations
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import AutomationRunRequest
from ..schemas import AutomationScheduleCreateRequest
from ..schemas import AutomationScheduleUpdateRequest
from ..schemas import AutomationSchedulesExecuteRequest
from .now_iso import helper_audit
from .now_iso import helper_generate_snippet
from .now_iso import helper_get_site
from .now_iso import helper_now_iso
from .now_iso import helper_parse_iso_datetime
from .now_iso import helper_run_visibility_audit_for_url
from .now_iso import helper_sync_cloudflare_site
from .now_iso import helper_vendor_matrix_for_site
from .now_iso import helper_validate_site_url
from .now_iso import helper_verify_snippet_installation
from ....identity.secure_egress import outbound_request
from ....identity.secure_egress import resolve_outbound_target
from ....identity.secure_egress import UnsafeOutboundURL
from ....identity.secure_egress import OutboundTarget
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from fastapi import Query
from typing import Any
import uuid


def helper_execute_automation_run(
    runtime: ContextRuntime,
    tenant_id: str,
    payload: AutomationRunRequest,
    *,
    trigger: str,
    schedule_id: str | None = None,
) -> dict[str, Any]:
    site = helper_get_site(runtime, tenant_id, payload.site_id)
    page_target: OutboundTarget | None = None
    if not payload.dry_run and (payload.verify_snippet or payload.run_visibility_audit):
        try:
            page_target = helper_validate_site_url(str(site.get("domain") or ""), payload.page_url)
        except UnsafeOutboundURL as exc:
            raise HTTPException(
                status_code=422, detail="Page URL must be a public URL on the registered site."
            ) from exc
    now = helper_now_iso()
    steps: list[dict[str, Any]] = []
    if payload.deploy_snippet:
        webhook_url = str(site.get("deployment_webhook_url") or "").strip()
        if payload.dry_run:
            steps.append(
                {"step": "deploy_snippet", "status": "planned", "mode": "webhook" if webhook_url else "manual"}
            )
        elif webhook_url:
            snippet = helper_generate_snippet(str(site["id"]), str(site["snippet_key"]), str(site["domain"]))
            try:
                target = resolve_outbound_target(webhook_url)
                resp = outbound_request(
                    "POST",
                    target,
                    json={
                        "site_id": site.get("id", ""),
                        "domain": site.get("domain", ""),
                        "snippet": snippet,
                        "snippet_key": site.get("snippet_key", ""),
                        "source": "nuxtron-ai-crawler-enablement",
                    },
                    headers={"X-Tenant-Id": tenant_id},
                    timeout=20.0,
                    max_response_bytes=256_000,
                )
                if resp.is_success:
                    with runtime._lock:
                        for s in runtime.sites_memory:
                            if s.get("id") == payload.site_id and s.get("tenant_id") == tenant_id:
                                s["snippet_installed"] = True
                                s["snippet_last_verified_at"] = now
                                s["updated_at"] = now
                    steps.append({"step": "deploy_snippet", "status": "completed", "mode": "webhook"})
                else:
                    steps.append(
                        {
                            "step": "deploy_snippet",
                            "status": "failed",
                            "mode": "webhook",
                            "detail": f"Webhook returned HTTP {resp.status_code}",
                        }
                    )
            except Exception:
                steps.append(
                    {
                        "step": "deploy_snippet",
                        "status": "failed",
                        "mode": "webhook",
                        "detail": "Outbound webhook failed or its destination was not allowed.",
                    }
                )
        else:
            steps.append(
                {
                    "step": "deploy_snippet",
                    "status": "manual_required",
                    "mode": "manual",
                    "detail": "No deployment_webhook_url configured; install snippet manually.",
                }
            )
    if payload.verify_snippet:
        if payload.dry_run:
            steps.append({"step": "verify_snippet", "status": "planned"})
        else:
            installed, detail = helper_verify_snippet_installation(
                str(site["snippet_key"]),
                payload.page_url,
                site_domain=str(site.get("domain") or ""),
                pinned_target=page_target,
            )
            with runtime._lock:
                for s in runtime.sites_memory:
                    if s.get("id") == payload.site_id and s.get("tenant_id") == tenant_id:
                        s["snippet_installed"] = installed
                        s["snippet_last_verified_at"] = helper_now_iso()
                        s["updated_at"] = helper_now_iso()
            steps.append(
                {
                    "step": "verify_snippet",
                    "status": "completed" if installed else "warning",
                    "installed": installed,
                    "detail": detail,
                }
            )
    if payload.sync_cloudflare:
        if payload.dry_run:
            steps.append({"step": "sync_cloudflare", "status": "planned", "action": payload.cloudflare_action})
        else:
            sync_result = helper_sync_cloudflare_site(site, payload.cloudflare_action)
            steps.append(
                {
                    "step": "sync_cloudflare",
                    "status": "completed" if sync_result.get("synced") else "warning",
                    "action": payload.cloudflare_action,
                    "result": sync_result,
                }
            )
    audit_record: dict[str, Any] | None = None
    if payload.run_visibility_audit:
        if payload.dry_run:
            steps.append({"step": "visibility_audit", "status": "planned", "crawlers": payload.crawlers_to_test[:10]})
        else:
            audit_record = helper_run_visibility_audit_for_url(
                tenant_id,
                site_id=payload.site_id,
                page_url=payload.page_url,
                crawlers_to_test=payload.crawlers_to_test,
                site_domain=str(site.get("domain") or ""),
                pinned_target=page_target,
            )
            with runtime._lock:
                runtime.audit_results_memory.append(audit_record)
                if len(runtime.audit_results_memory) > 2000:
                    del runtime.audit_results_memory[:500]
            steps.append(
                {
                    "step": "visibility_audit",
                    "status": "completed",
                    "audit_id": audit_record["id"],
                    "visibility_score": audit_record["visibility_score"],
                }
            )
    completed = sum((1 for s in steps if s.get("status") == "completed"))
    planned = sum((1 for s in steps if s.get("status") == "planned"))
    warnings = sum((1 for s in steps if s.get("status") == "warning"))
    failed = sum((1 for s in steps if s.get("status") == "failed"))
    manual_required = sum((1 for s in steps if s.get("status") == "manual_required"))
    total = len(steps)
    completion_pct = round(completed / max(total, 1) * 100.0, 1)
    run_id = str(uuid.uuid4())
    with runtime._lock:
        runtime.automation_runs_memory.append(
            {
                "id": run_id,
                "tenant_id": tenant_id,
                "trigger": trigger,
                "schedule_id": schedule_id,
                "site_id": payload.site_id,
                "page_url": payload.page_url,
                "dry_run": payload.dry_run,
                "steps": steps,
                "summary": {
                    "total_steps": total,
                    "completed": completed,
                    "planned": planned,
                    "warning": warnings,
                    "failed": failed,
                    "manual_required": manual_required,
                    "completion_pct": completion_pct,
                },
                "created_at": helper_now_iso(),
            }
        )
        if len(runtime.automation_runs_memory) > 4000:
            del runtime.automation_runs_memory[:1000]
    helper_audit(
        runtime,
        tenant_id,
        "automation_run",
        f"site={payload.site_id} trigger={trigger} completed={completed}/{total} dry_run={payload.dry_run}",
    )
    return {
        "status": "ok",
        "run_id": run_id,
        "tenant_id": tenant_id,
        "site_id": payload.site_id,
        "dry_run": payload.dry_run,
        "page_url": payload.page_url,
        "trigger": trigger,
        "schedule_id": schedule_id,
        "steps": steps,
        "summary": {
            "total_steps": total,
            "completed": completed,
            "planned": planned,
            "warning": warnings,
            "failed": failed,
            "manual_required": manual_required,
            "completion_pct": completion_pct,
        },
        "vendors": helper_vendor_matrix_for_site(site),
        "audit": {"audit_id": audit_record["id"], "visibility_score": audit_record["visibility_score"]}
        if audit_record
        else None,
        "generated_at": helper_now_iso(),
    }


def execute_create_automation_schedule(
    runtime: ContextRuntime, payload: AutomationScheduleCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:automation:schedules:create", 40, 60)
    helper_get_site(runtime, auth.tenant_id, payload.site_id)
    schedule_id = str(uuid.uuid4())
    now = helper_now_iso()
    record = {
        "id": schedule_id,
        "tenant_id": auth.tenant_id,
        "site_id": payload.site_id,
        "page_url": payload.page_url,
        "interval_minutes": payload.interval_minutes,
        "enabled": payload.enabled,
        "deploy_snippet": payload.deploy_snippet,
        "verify_snippet": payload.verify_snippet,
        "sync_cloudflare": payload.sync_cloudflare,
        "cloudflare_action": payload.cloudflare_action,
        "run_visibility_audit": payload.run_visibility_audit,
        "crawlers_to_test": payload.crawlers_to_test[:10],
        "last_run_at": None,
        "next_run_at": now,
        "created_at": now,
        "updated_at": now,
    }
    with runtime._lock:
        runtime.automation_schedules_memory.append(record)
    helper_audit(
        runtime, auth.tenant_id, "automation_schedule_created", f"schedule_id={schedule_id} site={payload.site_id}"
    )
    return {"status": "ok", "schedule": record}


def execute_update_automation_schedule(
    runtime: ContextRuntime, schedule_id: str, payload: AutomationScheduleUpdateRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:automation:schedules:update", 60, 60)
    with runtime._lock:
        record = next(
            (
                s
                for s in runtime.automation_schedules_memory
                if s.get("id") == schedule_id and s.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if record is None:
            raise HTTPException(status_code=404, detail="Automation schedule not found.")
        if payload.page_url is not None:
            record["page_url"] = payload.page_url
        if payload.interval_minutes is not None:
            record["interval_minutes"] = payload.interval_minutes
        if payload.enabled is not None:
            record["enabled"] = payload.enabled
        if payload.deploy_snippet is not None:
            record["deploy_snippet"] = payload.deploy_snippet
        if payload.verify_snippet is not None:
            record["verify_snippet"] = payload.verify_snippet
        if payload.sync_cloudflare is not None:
            record["sync_cloudflare"] = payload.sync_cloudflare
        if payload.cloudflare_action is not None:
            record["cloudflare_action"] = payload.cloudflare_action
        if payload.run_visibility_audit is not None:
            record["run_visibility_audit"] = payload.run_visibility_audit
        if payload.crawlers_to_test is not None:
            record["crawlers_to_test"] = payload.crawlers_to_test[:10]
        if record.get("enabled"):
            record["next_run_at"] = helper_now_iso()
        record["updated_at"] = helper_now_iso()
        snapshot = record.copy()
    helper_audit(runtime, auth.tenant_id, "automation_schedule_updated", f"schedule_id={schedule_id}")
    return {"status": "ok", "schedule": snapshot}


def execute_execute_automation_schedules(
    runtime: ContextRuntime, payload: AutomationSchedulesExecuteRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:automation:schedules:execute", 20, 60)
    now = datetime.now(UTC)
    with runtime._lock:
        tenant_schedules = [s for s in runtime.automation_schedules_memory if s.get("tenant_id") == auth.tenant_id]
    if payload.schedule_ids:
        wanted = set(payload.schedule_ids)
        tenant_schedules = [s for s in tenant_schedules if str(s.get("id")) in wanted]
    if payload.due_only:
        filtered: list[dict[str, Any]] = []
        for schedule in tenant_schedules:
            if not bool(schedule.get("enabled", True)):
                continue
            due_at = helper_parse_iso_datetime(str(schedule.get("next_run_at") or ""))
            if due_at is None or due_at <= now:
                filtered.append(schedule)
        tenant_schedules = filtered
    tenant_schedules = tenant_schedules[: payload.max_schedules]
    run_results: list[dict[str, Any]] = []
    for schedule in tenant_schedules:
        run_payload = AutomationRunRequest(
            site_id=str(schedule.get("site_id") or ""),
            page_url=str(schedule.get("page_url") or ""),
            dry_run=payload.dry_run,
            deploy_snippet=bool(schedule.get("deploy_snippet", True)),
            verify_snippet=bool(schedule.get("verify_snippet", True)),
            sync_cloudflare=bool(schedule.get("sync_cloudflare", True)),
            cloudflare_action=str(schedule.get("cloudflare_action") or "allow_ai_crawlers"),
            run_visibility_audit=bool(schedule.get("run_visibility_audit", True)),
            crawlers_to_test=list(schedule.get("crawlers_to_test", []))[:10],
        )
        result = helper_execute_automation_run(
            runtime, auth.tenant_id, run_payload, trigger="schedule_executor", schedule_id=str(schedule.get("id") or "")
        )
        run_results.append(result)
        with runtime._lock:
            record = next(
                (
                    s
                    for s in runtime.automation_schedules_memory
                    if s.get("id") == schedule.get("id") and s.get("tenant_id") == auth.tenant_id
                ),
                None,
            )
            if record is not None:
                record["last_run_at"] = helper_now_iso()
                record["last_run_id"] = result.get("run_id")
                record["last_status"] = "ok" if result.get("summary", {}).get("failed", 0) == 0 else "warning"
                interval = int(record.get("interval_minutes", 60) or 60)
                if bool(record.get("enabled", True)):
                    record["next_run_at"] = (datetime.now(UTC) + timedelta(minutes=interval)).isoformat()
                record["updated_at"] = helper_now_iso()
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "requested": {
            "schedule_count": len(payload.schedule_ids),
            "due_only": payload.due_only,
            "max_schedules": payload.max_schedules,
            "dry_run": payload.dry_run,
        },
        "summary": {
            "targeted": len(tenant_schedules),
            "runs_created": len(run_results),
            "completed": sum((1 for r in run_results if r.get("summary", {}).get("failed", 0) == 0)),
            "warnings": sum((1 for r in run_results if r.get("summary", {}).get("warning", 0) > 0)),
            "failed": sum((1 for r in run_results if r.get("summary", {}).get("failed", 0) > 0)),
        },
        "runs": run_results,
        "generated_at": helper_now_iso(),
    }


def execute_list_automation_history(
    runtime: ContextRuntime,
    auth: AuthDep,
    site_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:automation:history", 120, 60)
    with runtime._lock:
        items = [r.copy() for r in runtime.automation_runs_memory if r.get("tenant_id") == auth.tenant_id]
    if site_id:
        items = [r for r in items if str(r.get("site_id") or "") == site_id]
    items.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
    return {"status": "ok", "count": len(items[:limit]), "history": items[:limit]}
