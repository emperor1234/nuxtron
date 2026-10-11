"""Seo/Platform use cases: ecommerce seo."""

from ..services import extract_waterfall as provider_ollama_json
from functools import partial
from .....deps import AuthContext
from .....deps import require_auth
from .....domains.seo.services.seo_ecommerce_service import optimize_ecommerce_seo
from ..constants import _ECOMMERCE_SYS
from ..runtime import ContextRuntime
from ..schemas import EcommerceSEOReq
from ..schemas import PerformanceAuditReq
from ..schemas import PerformanceMonitorCreateReq
from ..schemas import PerformanceRumIngestReq
from ..services.get_shared_job_store import _clean
from ..services.get_shared_job_store import _normalize_perf_metric_name
from ..services.rollup_performance_rum import _rollup_performance_rum
from .run_performance_audit import helper_run_performance_audit
from .save_analysis import helper_list_analyses
from .save_analysis import helper_save_analysis
from .sync_job_store import helper_find_cached_analysis
from .sync_job_store import helper_get_analysis
from .sync_job_store import helper_log
from datetime import UTC
from datetime import datetime
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from typing import Annotated
from typing import Any
import uuid


async def execute_ecommerce_seo(
    runtime: ContextRuntime, req: EcommerceSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Optimize product pages: title, description, bullets, schema, category keywords."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:ecommerce", limit=20, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "ecommerce", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "ecommerce_seo",
            {"product": req.product_name, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await optimize_ecommerce_seo(
        product_name=req.product_name,
        category=req.category,
        description=req.description,
        keywords=req.keywords,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_ECOMMERCE_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "ecommerce", payload, result
    )
    helper_log(runtime, auth.tenant_id, "ecommerce_seo", {"product": req.product_name, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


def helper_monitor_alert_rules(monitor_cfg: dict[str, Any], audit_result: dict[str, Any]) -> list[dict[str, Any]]:
    vitals = audit_result.get("core_web_vitals") if isinstance(audit_result.get("core_web_vitals"), dict) else {}
    lcp_value = float(vitals.get("lcp_ms", 0) or 0)
    inp_value = float(vitals.get("inp_ms", 0) or 0)
    cls_value = float(vitals.get("cls", 0) or 0)
    lcp_threshold = float(monitor_cfg.get("alert_lcp_ms_threshold", 2500) or 2500)
    inp_threshold = float(monitor_cfg.get("alert_inp_ms_threshold", 200) or 200)
    cls_threshold = float(monitor_cfg.get("alert_cls_threshold", 0.1) or 0.1)
    return [
        {
            "metric": "lcp_ms",
            "threshold": lcp_threshold,
            "current": lcp_value,
            "state": "ok" if lcp_value <= lcp_threshold else "breached",
        },
        {
            "metric": "inp_ms",
            "threshold": inp_threshold,
            "current": inp_value,
            "state": "ok" if inp_value <= inp_threshold else "breached",
        },
        {
            "metric": "cls",
            "threshold": cls_threshold,
            "current": cls_value,
            "state": "ok" if cls_value <= cls_threshold else "breached",
        },
    ]


async def execute_performance_capabilities(
    runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]
):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-capabilities", limit=60, window_seconds=60)
    features = [
        {
            "feature": "Single URL synthetic audit",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/audit",
        },
        {
            "feature": "Free provider stack orchestration",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/audit",
        },
        {
            "feature": "Lighthouse category scoring",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/audit",
        },
        {
            "feature": "Core Web Vitals + field overlays",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/audit",
        },
        {
            "feature": "Waterfall and filmstrip payload",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/audit",
        },
        {
            "feature": "One-click auto-fix suggestions",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/auto-fix",
        },
        {
            "feature": "Historical trend retrieval",
            "status": "implemented",
            "endpoint": "GET /seo-platform/performance/history",
        },
        {
            "feature": "CrUX-style 6 month trend timeline",
            "status": "implemented",
            "endpoint": "GET /seo-platform/performance/crux/history",
        },
        {
            "feature": "Global test locations catalog",
            "status": "implemented",
            "endpoint": "GET /seo-platform/performance/test-locations",
        },
        {
            "feature": "Browser and network profiles",
            "status": "implemented",
            "endpoint": "GET /seo-platform/performance/browser-profiles",
        },
        {
            "feature": "Recurring monitor configuration",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/monitor/create",
        },
        {
            "feature": "Run monitor on demand",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/monitors/{monitor_id}/run",
        },
        {
            "feature": "Alert events timeline",
            "status": "implemented",
            "endpoint": "GET /seo-platform/performance/alerts/events",
        },
        {
            "feature": "Fetch full report by analysis id",
            "status": "implemented",
            "endpoint": "GET /seo-platform/performance/report/{analysis_id}",
        },
        {
            "feature": "Share token report links",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/report/{analysis_id}/share",
        },
        {
            "feature": "Read shared report by token",
            "status": "implemented",
            "endpoint": "GET /seo-platform/performance/report/shared/{share_token}",
        },
        {
            "feature": "Compare two performance reports",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/reports/compare",
        },
        {
            "feature": "Async API-style test trigger",
            "status": "implemented",
            "endpoint": "POST /seo-platform/performance/tests",
        },
        {
            "feature": "Async API-style test polling",
            "status": "implemented",
            "endpoint": "GET /seo-platform/performance/tests/{test_id}",
        },
        {"feature": "Strict no-mock fail-closed mode", "status": "implemented", "endpoint": "SEO_STRICT_NO_MOCK=true"},
    ]
    implemented = sum((1 for row in features if row["status"] == "implemented"))
    coverage_pct = round(implemented / len(features) * 100.0, 2)
    return {
        "vendor": "GTmetrix-style",
        "data_sources": {
            "free_provider_stack": [
                {"name": "Lighthouse CLI", "category": "Local synthetic audit runner"},
                {"name": "PageSpeed Insights API", "category": "Google-hosted Lighthouse and diagnostics"},
                {"name": "Chrome UX Report API", "category": "Field p75 Core Web Vitals"},
                {"name": "WebPageTest Public API", "category": "Optional remote waterfall and filmstrip"},
                {"name": "web-vitals RUM", "category": "First-party browser telemetry"},
            ]
        },
        "coverage_pct": coverage_pct,
        "implemented": implemented,
        "total_features": len(features),
        "features": features,
        "vendors": [
            {"name": "Google Lighthouse", "category": "Audit engine"},
            {"name": "Chrome DevTools Protocol", "category": "Waterfall/filmstrip telemetry"},
            {"name": "Playwright", "category": "Browser automation"},
            {"name": "Google Web Vitals", "category": "CWV measurement model"},
            {"name": "Chrome UX Report (CrUX)", "category": "Field data benchmark model"},
            {"name": "Prometheus", "category": "Metrics storage"},
            {"name": "Grafana", "category": "Visualization and alerting"},
            {"name": "OpenSearch", "category": "Telemetry index and trend retrieval"},
            {"name": "Ollama", "category": "AI copilot and remediation"},
        ],
    }


async def execute_performance_vendors(runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]):
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-vendors", limit=120, window_seconds=60)
    return {
        "vendor": "GTmetrix-style",
        "free_provider_stack": [
            {"name": "Lighthouse CLI", "role": "Local synthetic audits without a paid API"},
            {"name": "PageSpeed Insights API", "role": "Google-run lab audit and diagnostics data"},
            {"name": "Chrome UX Report API", "role": "Free field-data benchmark overlays"},
            {"name": "WebPageTest Public API", "role": "Optional remote waterfall, video, and global test runs"},
            {"name": "web-vitals RUM", "role": "First-party real-user telemetry collection"},
        ],
        "third_parties": [
            {"name": "Google Lighthouse", "role": "Lab audits and category scoring"},
            {"name": "Chrome DevTools Protocol", "role": "Network waterfall and filmstrip traces"},
            {"name": "Playwright", "role": "Synthetic browser execution"},
            {"name": "Google Web Vitals", "role": "CWV metric model"},
            {"name": "Chrome UX Report (CrUX)", "role": "Field trend alignment and p75 benchmark model"},
            {"name": "Prometheus", "role": "Time-series SLO telemetry"},
            {"name": "Grafana", "role": "Alerting and dashboards"},
            {"name": "OpenSearch", "role": "Report history and anomaly search"},
            {"name": "Ollama", "role": "AI remediation summaries and change narratives"},
        ],
    }


async def execute_performance_rum_ingest(
    runtime: ContextRuntime, req: PerformanceRumIngestReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Ingest a single first-party web-vitals RUM measurement."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-rum-ingest", limit=600, window_seconds=60)
    payload = req.model_dump()
    payload["metric_name"] = _normalize_perf_metric_name(req.metric_name) or req.metric_name
    result = {
        "accepted": True,
        "metric_name": payload["metric_name"],
        "value": req.value,
        "rating": req.rating,
        "received_at": datetime.now(UTC).isoformat(),
    }
    rum_event_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "performance_rum_event", payload, result
    )
    rollup = _rollup_performance_rum(
        helper_list_analyses(runtime, auth.tenant_id, "performance_rum_event", 1000), req.url
    )
    helper_log(
        runtime,
        auth.tenant_id,
        "performance_rum_ingest",
        {"url": req.url, "metric": payload["metric_name"], "value": req.value},
    )
    return {"rum_event_id": rum_event_id, **result, "rollup": rollup}


async def execute_performance_tests_create(
    runtime: ContextRuntime,
    req: PerformanceAuditReq,
    background_tasks: BackgroundTasks,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    """Create an async GTmetrix-style test run and return a polling token."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-tests-create", limit=20, window_seconds=60)
    test_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    runtime._PERF_ASYNC_TEST_JOBS[test_id] = {
        "test_id": test_id,
        "tenant_id": auth.tenant_id,
        "status": "queued",
        "created_at": created_at,
        "started_at": None,
        "completed_at": None,
        "error": None,
        "request": req.model_dump(),
        "result": None,
    }

    async def _execute() -> None:
        job = runtime._PERF_ASYNC_TEST_JOBS.get(test_id)
        if not job:
            return
        job["status"] = "running"
        job["started_at"] = datetime.now(UTC).isoformat()
        try:
            audit = await helper_run_performance_audit(runtime, req, auth, source=f"api:{test_id}")
            job["status"] = "completed"
            job["result"] = audit
            job["completed_at"] = datetime.now(UTC).isoformat()
        except Exception as exc:
            job["status"] = "failed"
            job["error"] = str(exc)
            job["completed_at"] = datetime.now(UTC).isoformat()

    background_tasks.add_task(_execute)
    return {
        "test_id": test_id,
        "status": "queued",
        "created_at": created_at,
        "poll_endpoint": f"/seo-platform/performance/tests/{test_id}",
    }


async def execute_performance_tests_status(
    runtime: ContextRuntime, test_id: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Poll async test status until completed."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-tests-status", limit=120, window_seconds=60)
    job = runtime._PERF_ASYNC_TEST_JOBS.get(test_id)
    if not job or str(job.get("tenant_id")) != auth.tenant_id:
        raise HTTPException(status_code=404, detail="Performance test not found.")
    response = {
        "test_id": test_id,
        "status": job.get("status"),
        "created_at": job.get("created_at"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "error": job.get("error"),
    }
    if job.get("status") == "completed" and isinstance(job.get("result"), dict):
        response["result"] = job.get("result")
    return response


async def execute_performance_monitor_create(
    runtime: ContextRuntime, req: PerformanceMonitorCreateReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Create a recurring GTmetrix-style monitor profile."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-monitor-create", limit=20, window_seconds=60)
    payload = req.model_dump()
    payload["status"] = "active"
    payload["created_at"] = datetime.now(UTC).isoformat()
    monitor_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime),
        auth.tenant_id,
        "performance_monitor",
        payload,
        {"status": "active", "type": "monitor"},
    )
    helper_log(
        runtime,
        auth.tenant_id,
        "performance_monitor_create",
        {"monitor_id": monitor_id, "url": req.url, "schedule": req.schedule},
    )
    return {"monitor_id": monitor_id, "status": "active", "monitor": payload}


async def execute_performance_monitors(runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]):
    """List monitor profiles for the tenant."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-monitors", limit=60, window_seconds=60)
    rows = helper_list_analyses(runtime, auth.tenant_id, "performance_monitor", 200)
    monitors = [
        {
            "monitor_id": row.get("id"),
            "created_at": row.get("created_at"),
            "status": (row.get("payload") or {}).get("status", "active"),
            "name": (row.get("payload") or {}).get("name", "Primary Monitor"),
            "url": (row.get("payload") or {}).get("url", ""),
            "schedule": (row.get("payload") or {}).get("schedule", "daily"),
            "target_device": (row.get("payload") or {}).get("target_device", "mobile"),
            "target_region": (row.get("payload") or {}).get("target_region", "lhr1"),
            "connection": (row.get("payload") or {}).get("connection", "4g"),
            "browser": (row.get("payload") or {}).get("browser", "chrome"),
            "alerts_enabled": bool((row.get("payload") or {}).get("alerts_enabled", True)),
            "alert_channels": list((row.get("payload") or {}).get("alert_channels") or ["email"]),
            "alert_targets": list((row.get("payload") or {}).get("alert_targets") or []),
        }
        for row in rows
    ]
    return {"count": len(monitors), "monitors": monitors}


async def execute_performance_monitor_run(
    runtime: ContextRuntime, monitor_id: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Run a configured monitor immediately and return the audit report."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-monitor-run", limit=20, window_seconds=60)
    monitor = helper_get_analysis(runtime, auth.tenant_id, monitor_id)
    if not monitor or monitor.get("module") != "performance_monitor":
        raise HTTPException(status_code=404, detail="Performance monitor not found.")
    cfg = monitor.get("payload") if isinstance(monitor.get("payload"), dict) else {}
    req = PerformanceAuditReq(
        url=str(cfg.get("url") or ""),
        target_device=str(cfg.get("target_device") or "mobile"),
        target_region=str(cfg.get("target_region") or "lhr1"),
        connection=str(cfg.get("connection") or "4g"),
        browser=str(cfg.get("browser") or "chrome"),
        include_video=bool(cfg.get("include_video", True)),
        adblock_enabled=bool(cfg.get("adblock_enabled", False)),
        capture_har=bool(cfg.get("capture_har", True)),
        notes=str(cfg.get("notes") or ""),
    )
    report = await helper_run_performance_audit(runtime, req, auth, source=f"monitor:{monitor_id}")
    rules = helper_monitor_alert_rules(cfg, report)
    breached = [rule for rule in rules if rule.get("state") == "breached"]
    channels = list(cfg.get("alert_channels") or ["email"])
    targets = list(cfg.get("alert_targets") or [])
    if bool(cfg.get("alerts_enabled", True)) and breached:
        event_payload = {
            "monitor_id": monitor_id,
            "url": cfg.get("url"),
            "channels": channels,
            "targets": targets,
            "rules": rules,
            "status": "triggered",
            "triggered_at": datetime.now(UTC).isoformat(),
        }
        await run_in_threadpool(
            partial(helper_save_analysis, runtime),
            auth.tenant_id,
            "performance_alert_event",
            event_payload,
            {"status": "triggered", "rules": rules},
        )
        helper_log(
            runtime,
            auth.tenant_id,
            "performance_monitor_alert",
            {"monitor_id": monitor_id, "breached_rules": len(breached)},
        )
    report["alerts"] = {
        "status": "triggered" if breached else "healthy",
        "rules": rules,
        "channels": channels,
        "targets": targets,
        "breached_rules": len(breached),
    }
    return report


async def execute_performance_alert_events(
    runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """List monitor-triggered alert events."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-alert-events", limit=120, window_seconds=60)
    events = helper_list_analyses(runtime, auth.tenant_id, "performance_alert_event", 200)
    rows = [
        {
            "event_id": e.get("id"),
            "created_at": e.get("created_at"),
            "monitor_id": (e.get("payload") or {}).get("monitor_id"),
            "url": (e.get("payload") or {}).get("url"),
            "status": (e.get("result") or {}).get("status", "triggered"),
            "breached_rules": [
                r
                for r in (e.get("result") or {}).get("rules") or []
                if isinstance(r, dict) and r.get("state") == "breached"
            ],
        }
        for e in events
    ]
    return {"count": len(rows), "events": rows}


async def execute_performance_report(
    runtime: ContextRuntime, analysis_id: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Fetch a full performance report payload by analysis id."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-report", limit=120, window_seconds=60)
    analysis = helper_get_analysis(runtime, auth.tenant_id, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Performance analysis not found.")
    if analysis.get("module") not in {"performance_audit", "performance_auto_fix", "performance_monitor"}:
        raise HTTPException(status_code=400, detail="Analysis id does not belong to performance module.")
    return {
        "analysis_id": analysis.get("id"),
        "module": analysis.get("module"),
        "created_at": analysis.get("created_at"),
        "payload": analysis.get("payload") if isinstance(analysis.get("payload"), dict) else {},
        "result": analysis.get("result") if isinstance(analysis.get("result"), dict) else {},
    }
