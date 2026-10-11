"""Search/Crawlers use cases: deploy snippets bulk."""

from __future__ import annotations
from ..constants import _CRAWLER_COMPILED
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import AutomationRunRequest
from ..schemas import BulkSnippetDeployRequest
from ..schemas import CrawlerDetectRequest
from ..schemas import CrawlerEventIngestRequest
from ..schemas import SnippetVerifyRequest
from ..schemas import SsrRenderRequest
from ..services.detect_crawler import _detect_crawler
from .execute_automation_run import helper_execute_automation_run
from .now_iso import helper_audit
from .now_iso import helper_generate_snippet
from .now_iso import helper_get_site
from .now_iso import helper_now_iso
from .now_iso import helper_validate_site_url
from .now_iso import helper_verify_snippet_installation
from ....identity.secure_egress import UnsafeOutboundURL
from ....identity.secure_egress import outbound_request
from ....identity.secure_egress import resolve_outbound_target
from fastapi import HTTPException
from fastapi import Query
from typing import Any
import hashlib
import os
import time
import uuid


def execute_deploy_snippets_bulk(
    runtime: ContextRuntime, payload: BulkSnippetDeployRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:snippets:deploy-bulk", 20, 60)
    with runtime._lock:
        tenant_sites = [s.copy() for s in runtime.sites_memory if s["tenant_id"] == auth.tenant_id]
    if payload.site_ids:
        requested = set(payload.site_ids)
        tenant_sites = [s for s in tenant_sites if s["id"] in requested]
    deployments: list[dict[str, Any]] = []
    updated_site_ids: list[str] = []
    for site in tenant_sites:
        site_id = str(site["id"])
        snippet = helper_generate_snippet(site_id, str(site["snippet_key"]), str(site["domain"]))
        webhook_url = str(site.get("deployment_webhook_url") or "").strip()
        if payload.dry_run:
            deployments.append(
                {
                    "site_id": site_id,
                    "domain": site.get("domain", ""),
                    "status": "planned",
                    "mode": "webhook" if webhook_url else "manual",
                    "webhook_configured": bool(webhook_url),
                }
            )
            continue
        if not webhook_url:
            deployments.append(
                {
                    "site_id": site_id,
                    "domain": site.get("domain", ""),
                    "status": "manual_required",
                    "detail": "No deployment_webhook_url configured; install snippet manually.",
                }
            )
            continue
        try:
            target = resolve_outbound_target(webhook_url)
            resp = outbound_request(
                "POST",
                target,
                json={
                    "site_id": site_id,
                    "domain": site.get("domain", ""),
                    "snippet": snippet,
                    "snippet_key": site.get("snippet_key", ""),
                    "source": "nuxtron-ai-crawler-enablement",
                },
                headers={"X-Tenant-Id": auth.tenant_id},
                timeout=20.0,
                max_response_bytes=256_000,
            )
            if resp.is_success:
                deployments.append(
                    {"site_id": site_id, "domain": site.get("domain", ""), "status": "deployed", "mode": "webhook"}
                )
                updated_site_ids.append(site_id)
            else:
                deployments.append(
                    {
                        "site_id": site_id,
                        "domain": site.get("domain", ""),
                        "status": "failed",
                        "mode": "webhook",
                        "detail": f"Webhook returned HTTP {resp.status_code}",
                    }
                )
        except Exception:
            deployments.append(
                {
                    "site_id": site_id,
                    "domain": site.get("domain", ""),
                    "status": "failed",
                    "mode": "webhook",
                    "detail": "Outbound webhook failed or its destination was not allowed.",
                }
            )
    if updated_site_ids:
        now = helper_now_iso()
        with runtime._lock:
            for s in runtime.sites_memory:
                if s.get("tenant_id") == auth.tenant_id and str(s.get("id")) in updated_site_ids:
                    s["snippet_installed"] = True
                    s["snippet_last_verified_at"] = now
                    s["updated_at"] = now
    deployed_count = sum((1 for d in deployments if d.get("status") == "deployed"))
    failed_count = sum((1 for d in deployments if d.get("status") == "failed"))
    manual_count = sum((1 for d in deployments if d.get("status") == "manual_required"))
    planned_count = sum((1 for d in deployments if d.get("status") == "planned"))
    helper_audit(runtime, auth.tenant_id, "bulk_snippet_deploy", f"sites={len(deployments)} deployed={deployed_count}")
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "dry_run": payload.dry_run,
        "summary": {
            "sites_targeted": len(deployments),
            "deployed": deployed_count,
            "failed": failed_count,
            "manual_required": manual_count,
            "planned": planned_count,
        },
        "deployments": deployments,
        "generated_at": helper_now_iso(),
    }


def execute_verify_snippet(
    runtime: ContextRuntime, site_id: str, payload: SnippetVerifyRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:snippet:verify", 30, 60)
    site = helper_get_site(runtime, auth.tenant_id, site_id)
    snippet_key = site["snippet_key"]
    installed, detail = helper_verify_snippet_installation(
        snippet_key, payload.page_url, site_domain=str(site.get("domain") or "")
    )
    with runtime._lock:
        for s in runtime.sites_memory:
            if s["id"] == site_id and s["tenant_id"] == auth.tenant_id:
                s["snippet_installed"] = installed
                s["snippet_last_verified_at"] = helper_now_iso()
    return {"status": "ok", "site_id": site_id, "installed": installed, "detail": detail}


def execute_list_crawlers(
    runtime: ContextRuntime,
    auth: AuthDep,
    category: str | None = Query(default=None),
    enabled_only: bool = Query(default=False),
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:crawlers:list", 120, 60)
    crawlers = [
        {k: v for k, v in c.items() if k != "_re"}
        for c in _CRAWLER_COMPILED
        if (not category or c["category"] == category) and (not enabled_only or c["enabled"])
    ]
    return {"status": "ok", "count": len(crawlers), "crawlers": crawlers}


def execute_detect_crawler(runtime: ContextRuntime, payload: CrawlerDetectRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:crawlers:detect", 300, 60)
    match = _detect_crawler(payload.user_agent)
    return {"status": "ok", "user_agent": payload.user_agent, "is_known_crawler": match is not None, "crawler": match}


def execute_ingest_crawler_event(
    runtime: ContextRuntime, payload: CrawlerEventIngestRequest, auth: AuthDep
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:events:ingest", 1000, 60)
    ua = payload.user_agent or payload.crawler_name
    crawler_info = _detect_crawler(ua) or {"name": payload.crawler_name, "category": "unknown"}
    is_ai_crawler = crawler_info.get("category") == "ai_search"
    now = helper_now_iso()
    event: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "site_id": payload.site_id,
        "crawler_name": payload.crawler_name,
        "crawler_category": crawler_info.get("category", "unknown"),
        "is_ai_crawler": is_ai_crawler,
        "page_url": payload.page_url,
        "status_code": payload.status_code,
        "response_type": payload.response_type,
        "render_time_ms": payload.render_time_ms,
        "ip_hash": hashlib.sha256((payload.ip_address or "").encode()).hexdigest()[:16] if payload.ip_address else "",
        "timestamp": int(time.time()),
        "created_at": now,
    }
    with runtime._lock:
        runtime.crawler_events_memory.append(event)
        if len(runtime.crawler_events_memory) > 50000:
            del runtime.crawler_events_memory[:10000]
        for s in runtime.sites_memory:
            if s["id"] == payload.site_id and s["tenant_id"] == auth.tenant_id:
                s["crawlers_detected_total"] = int(s.get("crawlers_detected_total", 0)) + 1
                if is_ai_crawler:
                    s["ai_crawlers_detected_total"] = int(s.get("ai_crawlers_detected_total", 0)) + 1
    return {"status": "ok", "event_id": event["id"], "is_ai_crawler": is_ai_crawler}


def execute_get_crawler_events(
    runtime: ContextRuntime,
    auth: AuthDep,
    site_id: str | None = Query(default=None),
    crawler_name: str | None = Query(default=None),
    ai_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:events:list", 120, 60)
    with runtime._lock:
        events = [
            e.copy()
            for e in runtime.crawler_events_memory
            if e["tenant_id"] == auth.tenant_id
            and (not site_id or e["site_id"] == site_id)
            and (not crawler_name or e["crawler_name"] == crawler_name)
            and (not ai_only or e.get("is_ai_crawler"))
        ]
    events = events[-limit:]
    return {"status": "ok", "count": len(events), "events": events}


def execute_crawler_dashboard(
    runtime: ContextRuntime,
    auth: AuthDep,
    site_id: str | None = Query(default=None),
    window_hours: int = Query(default=24, ge=1, le=168),
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:dashboard", 60, 60)
    cutoff = int(time.time()) - window_hours * 3600
    with runtime._lock:
        events = [
            e
            for e in runtime.crawler_events_memory
            if e["tenant_id"] == auth.tenant_id
            and e.get("timestamp", 0) >= cutoff
            and (not site_id or e["site_id"] == site_id)
        ]
        tenant_sites = [s.copy() for s in runtime.sites_memory if s["tenant_id"] == auth.tenant_id]
    total_hits = len(events)
    ai_hits = sum((1 for e in events if e.get("is_ai_crawler")))
    ssr_hits = sum((1 for e in events if e.get("response_type") == "ssr"))
    blocked = sum((1 for e in events if e.get("response_type") == "blocked"))
    avg_render = round(sum((e.get("render_time_ms", 0) for e in events)) / total_hits, 1) if total_hits else 0
    by_crawler: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_page: dict[str, int] = {}
    for e in events:
        cn = str(e.get("crawler_name", "unknown"))
        cat = str(e.get("crawler_category", "unknown"))
        page = str(e.get("page_url", ""))[:120]
        by_crawler[cn] = by_crawler.get(cn, 0) + 1
        by_category[cat] = by_category.get(cat, 0) + 1
        by_page[page] = by_page.get(page, 0) + 1
    top_crawlers = sorted(by_crawler.items(), key=lambda x: -x[1])[:20]
    top_pages = sorted(by_page.items(), key=lambda x: -x[1])[:10]
    ai_events = [e for e in events if e.get("is_ai_crawler")]
    ai_ssr = sum((1 for e in ai_events if e.get("response_type") in {"ssr", "cached"}))
    visibility_score = round(ai_ssr / max(len(ai_events), 1) * 100, 1)
    return {
        "status": "ok",
        "window_hours": window_hours,
        "site_id": site_id,
        "summary": {
            "total_hits": total_hits,
            "ai_crawler_hits": ai_hits,
            "ssr_served_hits": ssr_hits,
            "blocked_hits": blocked,
            "avg_render_time_ms": avg_render,
            "visibility_score": visibility_score,
            "sites_registered": len(tenant_sites),
            "sites_with_snippet": sum((1 for s in tenant_sites if s.get("snippet_installed"))),
        },
        "by_category": by_category,
        "top_crawlers": [{"name": n, "hits": c} for n, c in top_crawlers],
        "top_pages": [{"url": u, "hits": c} for u, c in top_pages],
        "recent_events": events[-20:],
    }


def execute_request_ssr_render(runtime: ContextRuntime, payload: SsrRenderRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:ssr:render", 100, 60)
    site = helper_get_site(runtime, auth.tenant_id, payload.site_id)
    cache_key = hashlib.sha256(f"{auth.tenant_id}:{payload.site_id}:{payload.url}".encode()).hexdigest()[:24]
    with runtime._lock:
        existing = next(
            (
                record
                for record in runtime.ssr_cache_memory
                if record.get("cache_key") == cache_key
                and record.get("tenant_id") == auth.tenant_id
                and record.get("site_id") == payload.site_id
                and record.get("source") == "proxy"
                and not payload.force_refresh
            ),
            None,
        )
    if existing:
        age_seconds = int(time.time()) - int(existing.get("rendered_at_ts", 0))
        if age_seconds < payload.cache_ttl_seconds:
            return {"status": "ok", "source": "cache", "cache_key": cache_key, "render": existing}

    try:
        page_target = helper_validate_site_url(str(site.get("domain") or ""), payload.url)
    except UnsafeOutboundURL as exc:
        raise HTTPException(status_code=422, detail="Page URL must be a public URL on the registered site.") from exc
    proxy_url = os.getenv("SSR_PROXY_URL", "").strip()
    if not proxy_url:
        raise HTTPException(status_code=503, detail="SSR rendering provider is not configured.")
    try:
        proxy_target = resolve_outbound_target(f"{proxy_url.rstrip('/')}/render")
    except UnsafeOutboundURL as exc:
        raise HTTPException(
            status_code=503, detail="SSR rendering provider destination is not configured safely."
        ) from exc

    started = time.perf_counter()
    try:
        response = outbound_request(
            "GET",
            proxy_target,
            params={"url": page_target.url, "crawler": payload.crawler_hint or "GPTBot"},
            headers={"X-Tenant-Id": auth.tenant_id},
            timeout=30.0,
            max_response_bytes=5_000_000,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="SSR rendering provider is unavailable.") from exc
    if not response.is_success:
        raise HTTPException(status_code=502, detail="SSR rendering provider returned an unsuccessful response.")
    if not response.content:
        raise HTTPException(status_code=502, detail="SSR rendering provider returned an empty response.")

    now = helper_now_iso()
    render_record: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "site_id": payload.site_id,
        "url": page_target.url,
        "cache_key": cache_key,
        "rendered_html_length": len(response.text),
        "render_time_ms": round((time.perf_counter() - started) * 1000),
        "cache_ttl_seconds": payload.cache_ttl_seconds,
        "rendered_at_ts": int(time.time()),
        "rendered_at": now,
        "source": "proxy",
        "error": None,
    }
    with runtime._lock:
        runtime.ssr_cache_memory[:] = [
            record for record in runtime.ssr_cache_memory if record.get("cache_key") != cache_key
        ]
        runtime.ssr_cache_memory.append(render_record)
        if len(runtime.ssr_cache_memory) > 5000:
            del runtime.ssr_cache_memory[:1000]
    return {"status": "ok", "source": "proxy", "cache_key": cache_key, "render": render_record}


def execute_list_ssr_cache(
    runtime: ContextRuntime,
    auth: AuthDep,
    site_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:ssr:cache:list", 60, 60)
    with runtime._lock:
        items = [
            c.copy()
            for c in runtime.ssr_cache_memory
            if c["tenant_id"] == auth.tenant_id and (not site_id or c.get("site_id") == site_id)
        ]
    return {"status": "ok", "count": len(items), "items": items[-limit:]}


def execute_list_automation_schedules(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:automation:schedules:list", 120, 60)
    with runtime._lock:
        items = [s.copy() for s in runtime.automation_schedules_memory if s.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda s: str(s.get("created_at", "")), reverse=True)
    return {"status": "ok", "count": len(items), "schedules": items}


def execute_run_automation(runtime: ContextRuntime, payload: AutomationRunRequest, auth: AuthDep) -> dict[str, Any]:
    runtime.enforce_rate_limit(f"{auth.tenant_id}:ace:automation:run", 20, 60)
    return helper_execute_automation_run(runtime, auth.tenant_id, payload, trigger="manual")
