"""Seo/Platform use cases: ecommerce seo."""

from functools import partial
from typing import Annotated, Any

from fastapi import BackgroundTasks, Depends
from starlette.concurrency import run_in_threadpool

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_ecommerce_service import optimize_ecommerce_seo
from .....domains.seo.services.seo_performance_service import raise_performance_unavailable
from ..constants import _ECOMMERCE_SYS
from ..runtime import ContextRuntime
from ..schemas import EcommerceSEOReq, PerformanceAuditReq, PerformanceMonitorCreateReq, PerformanceRumIngestReq
from ..services import extract_waterfall as provider_ollama_json
from ..services.get_shared_job_store import _clean
from .save_analysis import helper_save_analysis
from .sync_job_store import helper_find_cached_analysis, helper_log


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
    raise_performance_unavailable()


async def execute_performance_vendors(runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]):
    raise_performance_unavailable()


async def execute_performance_rum_ingest(
    runtime: ContextRuntime, req: PerformanceRumIngestReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()


async def execute_performance_tests_create(
    runtime: ContextRuntime,
    req: PerformanceAuditReq,
    background_tasks: BackgroundTasks,
    auth: Annotated[AuthContext, Depends(require_auth)],
):
    raise_performance_unavailable()


async def execute_performance_tests_status(
    runtime: ContextRuntime, test_id: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()


async def execute_performance_monitor_create(
    runtime: ContextRuntime, req: PerformanceMonitorCreateReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()


async def execute_performance_monitors(runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]):
    raise_performance_unavailable()


async def execute_performance_monitor_run(
    runtime: ContextRuntime, monitor_id: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()


async def execute_performance_alert_events(
    runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()


async def execute_performance_report(
    runtime: ContextRuntime, analysis_id: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()
