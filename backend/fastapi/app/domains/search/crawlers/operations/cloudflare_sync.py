"""Search/Crawlers use cases: cloudflare sync."""

from __future__ import annotations
from ..constants import KNOWN_CRAWLERS
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import CloudflareAutoSyncRequest
from ..schemas import CloudflareSyncRequest
from ..schemas import CrawlerRuleRequest
from ..schemas import VisibilityAuditRequest
from .now_iso import helper_audit
from .now_iso import helper_get_site
from .now_iso import helper_now_iso
from .now_iso import helper_run_visibility_audit_for_url
from .now_iso import helper_sync_cloudflare_site
from .now_iso import helper_validate_site_url
from .now_iso import helper_vendor_chart_for_sites
from .now_iso import helper_vendor_matrix_for_site
from ....identity.secure_egress import OutboundTarget
from ....identity.secure_egress import UnsafeOutboundURL
from ....identity.secure_egress import resolve_outbound_target
from fastapi import HTTPException
from fastapi import Query
from typing import Any
import httpx
import os
import uuid


def execute_cloudflare_sync(runtime: ContextRuntime, payload: CloudflareSyncRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:cloudflare:sync", 10, 60)
    site = helper_get_site(runtime, auth.tenant_id, payload.site_id)
    sync_result = helper_sync_cloudflare_site(site, payload.action)
    helper_audit(runtime, auth.tenant_id, "cloudflare_waf_synced", f"site={payload.site_id} action={payload.action}")
    if not sync_result.get("synced", False):
        reason = str(sync_result.get("reason", "unknown"))
        if reason in {"missing_cloudflare_zone_id", "missing_cloudflare_api_token"}:
            return {
                "status": "ok",
                "synced": False,
                "detail": "Cloudflare sync skipped: zone_id not set on site or CLOUDFLARE_API_TOKEN not configured. Set CLOUDFLARE_API_TOKEN and cloudflare_zone_id on the site to enable WAF rule sync.",
                "result": sync_result,
            }
        return {
            "status": "error",
            "synced": False,
            "detail": str(sync_result.get("error") or sync_result.get("reason") or "Cloudflare sync failed"),
            "result": sync_result,
        }
    ai_ua_patterns = [c["name"] for c in KNOWN_CRAWLERS if c["category"] == "ai_search" and c["enabled"]]
    return {
        "status": "ok",
        "synced": True,
        "action": payload.action,
        "crawlers_whitelisted": ai_ua_patterns[:20],
        "result": sync_result,
    }


def execute_cloudflare_auto_sync(
    runtime: ContextRuntime, payload: CloudflareAutoSyncRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:cloudflare:auto-sync", 10, 60)
    with runtime._lock:
        tenant_sites = [s.copy() for s in runtime.sites_memory if s["tenant_id"] == auth.tenant_id]
    if payload.site_ids:
        requested = set(payload.site_ids)
        tenant_sites = [s for s in tenant_sites if s["id"] in requested]
    if payload.dry_run:
        planned = []
        for site in tenant_sites:
            planned.append(
                {
                    "site_id": site.get("id", ""),
                    "domain": site.get("domain", ""),
                    "eligible": bool(site.get("cloudflare_zone_id"))
                    and bool(os.getenv("CLOUDFLARE_API_TOKEN", "").strip()),
                }
            )
        return {
            "status": "ok",
            "dry_run": True,
            "action": payload.action,
            "sites_targeted": len(planned),
            "results": planned,
            "generated_at": helper_now_iso(),
        }
    results = [helper_sync_cloudflare_site(site, payload.action) for site in tenant_sites]
    synced = sum((1 for item in results if item.get("synced")))
    skipped = sum(
        (1 for item in results if item.get("reason") in {"missing_cloudflare_zone_id", "missing_cloudflare_api_token"})
    )
    failed = max(0, len(results) - synced - skipped)
    helper_audit(runtime, auth.tenant_id, "cloudflare_auto_sync", f"sites={len(results)} synced={synced}")
    return {
        "status": "ok",
        "dry_run": False,
        "action": payload.action,
        "summary": {"sites_targeted": len(results), "synced": synced, "skipped": skipped, "failed": failed},
        "results": results,
        "generated_at": helper_now_iso(),
    }


def execute_readiness(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:readiness", 60, 60)
    with runtime._lock:
        tenant_sites = [s.copy() for s in runtime.sites_memory if s["tenant_id"] == auth.tenant_id]
    total_sites = len(tenant_sites)
    snippet_installed = sum((1 for s in tenant_sites if bool(s.get("snippet_installed"))))
    ssr_enabled = sum((1 for s in tenant_sites if bool(s.get("ssr_enabled"))))
    cf_zone_configured = sum((1 for s in tenant_sites if bool(s.get("cloudflare_zone_id"))))
    webhook_configured = sum((1 for s in tenant_sites if bool(s.get("deployment_webhook_url"))))
    token_configured = bool(os.getenv("CLOUDFLARE_API_TOKEN", "").strip())
    snippet_pct = round(snippet_installed / max(total_sites, 1) * 100.0, 1)
    ssr_pct = round(ssr_enabled / max(total_sites, 1) * 100.0, 1)
    cf_pct = round(cf_zone_configured / max(total_sites, 1) * 100.0, 1)
    webhook_pct = round(webhook_configured / max(total_sites, 1) * 100.0, 1)
    score = round(snippet_pct * 0.4 + ssr_pct * 0.2 + cf_pct * 0.2 + webhook_pct * 0.2, 1)
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D"
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "readiness": {
            "score": score,
            "grade": grade,
            "production_ready": score >= 70 and token_configured,
            "total_sites": total_sites,
        },
        "coverage": {
            "snippet_installed_pct": snippet_pct,
            "ssr_enabled_pct": ssr_pct,
            "cloudflare_zone_configured_pct": cf_pct,
            "deployment_webhook_configured_pct": webhook_pct,
        },
        "checks": {"cloudflare_api_token_configured": token_configured},
        "generated_at": helper_now_iso(),
    }


def execute_cloudflare_status(runtime: ContextRuntime, auth: AuthDep, site_id: str = Query(...)) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:cloudflare:status", 30, 60)
    site = helper_get_site(runtime, auth.tenant_id, site_id)
    zone_id = site.get("cloudflare_zone_id") or ""
    cf_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not zone_id or not cf_token:
        return {"status": "ok", "configured": False, "rules": []}
    try:
        with httpx.Client(timeout=10.0, trust_env=False, follow_redirects=False) as client:
            resp = client.get(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/firewall/rules",
                headers={"Authorization": f"Bearer {cf_token}", "Content-Type": "application/json"},
                params={"description": "Nuxtron ACE", "per_page": 10},
            )
        rules = resp.json().get("result", []) if resp.is_success else []
    except Exception as exc:
        return {"status": "error", "configured": True, "rules": [], "error": str(exc)[:200]}
    return {"status": "ok", "configured": True, "zone_id": zone_id, "rules": rules}


def execute_create_rule(runtime: ContextRuntime, payload: CrawlerRuleRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:rules:create", 60, 60)
    helper_get_site(runtime, auth.tenant_id, payload.site_id)
    rule: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "site_id": payload.site_id,
        "crawler_name": payload.crawler_name,
        "rule": payload.rule,
        "rate_limit_rpm": payload.rate_limit_rpm,
        "note": payload.note or "",
        "created_at": helper_now_iso(),
    }
    with runtime._lock:
        runtime.crawler_rules_memory.append(rule)
    return {"status": "ok", "rule": rule}


def execute_list_rules(
    runtime: ContextRuntime, auth: AuthDep, site_id: str | None = Query(default=None)
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:rules:list", 120, 60)
    with runtime._lock:
        rules = [
            r.copy()
            for r in runtime.crawler_rules_memory
            if r["tenant_id"] == auth.tenant_id and (not site_id or r["site_id"] == site_id)
        ]
    return {"status": "ok", "count": len(rules), "rules": rules}


def execute_delete_rule(runtime: ContextRuntime, rule_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:rules:delete", 30, 60)
    with runtime._lock:
        before = len(runtime.crawler_rules_memory)
        runtime.crawler_rules_memory[:] = [
            r for r in runtime.crawler_rules_memory if not (r["id"] == rule_id and r["tenant_id"] == auth.tenant_id)
        ]
        removed = before - len(runtime.crawler_rules_memory)
    if removed == 0:
        raise HTTPException(status_code=404, detail="Rule not found.")
    return {"status": "ok", "rule_id": rule_id, "removed": True}


def execute_run_visibility_audit(
    runtime: ContextRuntime, payload: VisibilityAuditRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:audit:run", 20, 60)
    site = helper_get_site(runtime, auth.tenant_id, payload.site_id) if payload.site_id else None
    try:
        page_target: OutboundTarget = (
            helper_validate_site_url(str(site.get("domain") or ""), payload.url)
            if site
            else resolve_outbound_target(payload.url, allow_http=True)
        )
    except UnsafeOutboundURL as exc:
        raise HTTPException(
            status_code=422, detail="Page URL must be a public destination on the registered site."
        ) from exc
    audit_record = helper_run_visibility_audit_for_url(
        auth.tenant_id,
        site_id=payload.site_id or "",
        page_url=payload.url,
        crawlers_to_test=payload.crawlers_to_test,
        site_domain=str(site.get("domain") or "") if site else None,
        pinned_target=page_target,
    )
    with runtime._lock:
        runtime.audit_results_memory.append(audit_record)
        if len(runtime.audit_results_memory) > 2000:
            del runtime.audit_results_memory[:500]
    return {"status": "ok", "audit": audit_record}


def execute_get_audit(runtime: ContextRuntime, audit_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:audit:get", 120, 60)
    with runtime._lock:
        record = next(
            (
                a.copy()
                for a in runtime.audit_results_memory
                if a["id"] == audit_id and a["tenant_id"] == auth.tenant_id
            ),
            None,
        )
    if record is None:
        raise HTTPException(status_code=404, detail="Audit not found.")
    return {"status": "ok", "audit": record}


def execute_list_vendors(
    runtime: ContextRuntime, auth: AuthDep, site_id: str | None = Query(default=None)
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:vendors", 120, 60)
    with runtime._lock:
        tenant_sites = [s.copy() for s in runtime.sites_memory if s["tenant_id"] == auth.tenant_id]
    if site_id:
        site = next((s for s in tenant_sites if s["id"] == site_id), None)
        if site is None:
            raise HTTPException(status_code=404, detail="Site not found.")
        site_vendors = helper_vendor_matrix_for_site(site)
        vendor_chart, summary = helper_vendor_chart_for_sites([site])
        return {
            "status": "ok",
            "site_id": site_id,
            "domain": site.get("domain", ""),
            "vendors": site_vendors,
            "vendor_chart": vendor_chart,
            "summary": summary,
            "generated_at": helper_now_iso(),
        }
    vendor_chart, summary = helper_vendor_chart_for_sites(tenant_sites)
    return {
        "status": "ok",
        "sites": [
            {"site_id": s.get("id", ""), "domain": s.get("domain", ""), "vendors": helper_vendor_matrix_for_site(s)}
            for s in tenant_sites
        ],
        "vendor_chart": vendor_chart,
        "summary": summary,
        "generated_at": helper_now_iso(),
    }


def execute_delete_automation_schedule(runtime: ContextRuntime, schedule_id: str, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:automation:schedules:delete", 60, 60)
    with runtime._lock:
        before = len(runtime.automation_schedules_memory)
        runtime.automation_schedules_memory[:] = [
            s
            for s in runtime.automation_schedules_memory
            if not (s.get("id") == schedule_id and s.get("tenant_id") == auth.tenant_id)
        ]
        removed = before - len(runtime.automation_schedules_memory)
    if removed == 0:
        raise HTTPException(status_code=404, detail="Automation schedule not found.")
    helper_audit(runtime, auth.tenant_id, "automation_schedule_deleted", f"schedule_id={schedule_id}")
    return {"status": "ok", "removed": True, "schedule_id": schedule_id}
