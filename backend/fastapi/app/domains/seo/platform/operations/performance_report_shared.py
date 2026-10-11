"""Seo/Platform use cases: performance report shared."""

from ..services import extract_waterfall as provider_ollama_json
from functools import partial
from .....deps import AuthContext
from .....deps import require_auth
from .....domains.seo.services.seo_accessibility_service import audit_accessibility
from .....domains.seo.services.seo_agent_service import analyze_agent_plan
from .....domains.seo.services.seo_internal_linking_service import suggest_internal_linking
from .....domains.seo.services.seo_landing_service import generate_landing_page
from .....domains.seo.services.seo_media_service import audit_media_seo
from .....domains.seo.services.seo_security_service import audit_security_seo
from .....domains.seo.services.seo_social_service import audit_social_seo
from ..constants import _ACCESSIBILITY_SYS
from ..constants import _AGENT_SYS
from ..constants import _INTERNAL_LINKING_SYS
from ..constants import _LANDING_SYS
from ..constants import _MEDIA_SEO_SYS
from ..constants import _SECURITY_SEO_SYS
from ..constants import _SOCIAL_SEO_SYS
from ..runtime import ContextRuntime
from ..schemas import AccessibilityAuditReq
from ..schemas import AgentRunReq
from ..schemas import InternalLinkingReq
from ..schemas import LandingPageGenerateReq
from ..schemas import MediaSeoAuditReq
from ..schemas import PerformanceCompareReq
from ..schemas import SecuritySeoAuditReq
from ..schemas import SocialSeoAuditReq
from ..services.get_shared_job_store import _clean
from .save_analysis import helper_list_analyses
from .save_analysis import helper_save_analysis
from .sync_job_store import helper_find_cached_analysis
from .sync_job_store import helper_get_analysis
from .sync_job_store import helper_log
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import Depends
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from typing import Annotated
from typing import Any
import uuid


async def execute_performance_report_shared(
    runtime: ContextRuntime, share_token: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Resolve a shared report token and return the report payload."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-report-shared", limit=120, window_seconds=60)
    links = helper_list_analyses(runtime, auth.tenant_id, "performance_share_link", 500)
    link = next((row for row in links if str((row.get("payload") or {}).get("share_token", "")) == share_token), None)
    if not link:
        raise HTTPException(status_code=404, detail="Shared report token not found.")
    expires_at_raw = str((link.get("payload") or {}).get("expires_at", ""))
    try:
        expires_at = datetime.fromisoformat(expires_at_raw.replace("Z", "+00:00"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid share token metadata.") from exc
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if datetime.now(UTC) > expires_at:
        raise HTTPException(status_code=410, detail="Shared report token expired.")
    analysis_id = str((link.get("payload") or {}).get("analysis_id", ""))
    analysis = helper_get_analysis(runtime, auth.tenant_id, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Shared report target not found.")
    return {
        "share_token": share_token,
        "analysis_id": analysis.get("id"),
        "module": analysis.get("module"),
        "created_at": analysis.get("created_at"),
        "payload": analysis.get("payload") if isinstance(analysis.get("payload"), dict) else {},
        "result": analysis.get("result") if isinstance(analysis.get("result"), dict) else {},
        "expires_at": expires_at.isoformat(),
    }


async def execute_performance_reports_compare(
    runtime: ContextRuntime, req: PerformanceCompareReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Compare two performance reports and return deltas/regression signals."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-report-compare", limit=60, window_seconds=60)
    base = helper_get_analysis(runtime, auth.tenant_id, req.baseline_analysis_id)
    cand = helper_get_analysis(runtime, auth.tenant_id, req.candidate_analysis_id)
    if not base or not cand:
        raise HTTPException(status_code=404, detail="One or both performance analyses were not found.")
    base_result = base.get("result") if isinstance(base.get("result"), dict) else {}
    cand_result = cand.get("result") if isinstance(cand.get("result"), dict) else {}
    base_vitals = base_result.get("core_web_vitals") if isinstance(base_result.get("core_web_vitals"), dict) else {}
    cand_vitals = cand_result.get("core_web_vitals") if isinstance(cand_result.get("core_web_vitals"), dict) else {}

    def _num(data: dict[str, Any], key: str) -> float:
        return float(data.get(key, 0) or 0)

    score_delta = _num(cand_result, "performance_score") - _num(base_result, "performance_score")
    lcp_delta = _num(cand_vitals, "lcp_ms") - _num(base_vitals, "lcp_ms")
    inp_delta = _num(cand_vitals, "inp_ms") - _num(base_vitals, "inp_ms")
    cls_delta = _num(cand_vitals, "cls") - _num(base_vitals, "cls")
    regression_detected = bool(score_delta < 0 or lcp_delta > 0 or inp_delta > 0 or (cls_delta > 0))
    return {
        "baseline_analysis_id": req.baseline_analysis_id,
        "candidate_analysis_id": req.candidate_analysis_id,
        "score_delta": score_delta,
        "core_web_vitals_delta": {"lcp_ms": lcp_delta, "inp_ms": inp_delta, "cls": cls_delta},
        "regression_detected": regression_detected,
        "summary": "regression" if regression_detected else "improved_or_stable",
        "recommendation": "Block rollout until fixed" if regression_detected else "Safe to promote",
    }


async def execute_performance_history(
    runtime: ContextRuntime, url: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Return historical performance audit runs for a URL."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-history", limit=30, window_seconds=60)
    analyses = helper_list_analyses(runtime, auth.tenant_id, "performance_audit", 500)
    runs = [a for a in analyses if str((a.get("payload") or {}).get("url", "")).rstrip("/") == url.rstrip("/")]
    runs_sorted = sorted(runs, key=lambda r: str(r.get("created_at", "")), reverse=False)
    history = [
        {
            "ts": r.get("created_at"),
            "analysis_id": r.get("id"),
            "performance_score": (r.get("result") or {}).get("performance_score"),
            "lcp_ms": ((r.get("result") or {}).get("core_web_vitals") or {}).get("lcp_ms"),
            "cls": ((r.get("result") or {}).get("core_web_vitals") or {}).get("cls"),
            "device": (r.get("payload") or {}).get("target_device"),
        }
        for r in runs_sorted
    ]
    return {"url": url, "count": len(history), "runs": history}


async def execute_performance_crux_history(
    runtime: ContextRuntime, url: str, auth: Annotated[AuthContext, Depends(require_auth)], months: int = 6
):
    """Return CrUX-style monthly field trend points up to 6 months."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:perf-crux-history", limit=60, window_seconds=60)
    bounded_months = max(1, min(6, months))
    cutoff = datetime.now(UTC) - timedelta(days=bounded_months * 31)
    analyses = helper_list_analyses(runtime, auth.tenant_id, "performance_audit", 800)
    matching: list[dict[str, Any]] = []
    for row in analyses:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if str(payload.get("url", "")).rstrip("/") != url.rstrip("/"):
            continue
        created_raw = str(row.get("created_at", ""))
        try:
            created = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except Exception:
            continue
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if created < cutoff:
            continue
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        field = result.get("field_web_vitals") if isinstance(result.get("field_web_vitals"), dict) else {}
        core = result.get("core_web_vitals") if isinstance(result.get("core_web_vitals"), dict) else {}
        matching.append(
            {
                "created": created,
                "lcp_p75_ms": float(field.get("lcp_p75_ms", core.get("lcp_ms", 0)) or 0),
                "inp_p75_ms": float(field.get("inp_p75_ms", core.get("inp_ms", 0)) or 0),
                "cls_p75": float(field.get("cls_p75", core.get("cls", 0)) or 0),
                "sample_size": int(field.get("sample_size", 0) or 0),
            }
        )
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in matching:
        month_key = row["created"].strftime("%Y-%m")
        buckets.setdefault(month_key, []).append(row)
    points: list[dict[str, Any]] = []
    for month_key in sorted(buckets.keys()):
        rows = buckets[month_key]
        denom = float(max(len(rows), 1))
        points.append(
            {
                "month": month_key,
                "lcp_p75_ms": round(sum((float(r.get("lcp_p75_ms", 0)) for r in rows)) / denom, 2),
                "inp_p75_ms": round(sum((float(r.get("inp_p75_ms", 0)) for r in rows)) / denom, 2),
                "cls_p75": round(sum((float(r.get("cls_p75", 0)) for r in rows)) / denom, 4),
                "sample_size": int(sum((int(r.get("sample_size", 0)) for r in rows))),
            }
        )
    return {"url": url, "months": bounded_months, "count": len(points), "source": "crux-style", "points": points}


async def execute_agent_run(
    runtime: ContextRuntime, req: AgentRunReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Create an autonomous SEO strategy plan for a goal."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:agent", limit=5, window_seconds=60)
    plan_id = str(uuid.uuid4())
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "agent", payload)
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "agent_run",
            {
                "goal": req.goal,
                "plan_id": cached.get("result", {}).get("plan_id"),
                "cached": True,
                "analysis_id": cached["id"],
            },
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_agent_plan(
        goal=req.goal,
        domain=req.domain,
        plan_id=plan_id,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_AGENT_SYS,
        clean_text_fn=_clean,
    )
    result["plan_id"] = plan_id
    result["domain"] = req.domain
    result["created_at"] = datetime.now(UTC).isoformat()
    result["status"] = "planned"
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "agent", payload, result
    )
    helper_log(runtime, auth.tenant_id, "agent_run", {"goal": req.goal, "plan_id": plan_id, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_accessibility_audit(
    runtime: ContextRuntime, req: AccessibilityAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """WCAG accessibility audit with readability and assistive-tech scoring."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:accessibility", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "accessibility", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "accessibility_audit",
            {"url": req.url, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await audit_accessibility(
        url=req.url,
        standard=req.standard,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_ACCESSIBILITY_SYS,
        clean_text_fn=_clean,
    )
    result["url"] = req.url
    result["audited_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "accessibility", payload, result
    )
    helper_log(runtime, auth.tenant_id, "accessibility_audit", {"url": req.url, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_media_seo_audit(
    runtime: ContextRuntime, req: MediaSeoAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Audit alt text, image metadata, compression, and media search signals."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:media", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "media", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "media_seo_audit", {"url": req.url, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await audit_media_seo(
        url=req.url,
        check_compression=req.check_compression,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_MEDIA_SEO_SYS,
        clean_text_fn=_clean,
    )
    result["url"] = req.url
    result["audited_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "media", payload, result
    )
    helper_log(runtime, auth.tenant_id, "media_seo_audit", {"url": req.url, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_social_seo_audit(
    runtime: ContextRuntime, req: SocialSeoAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Audit Open Graph, Twitter Card, LinkedIn snippets, and social distribution signals."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:social", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "social", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "social_seo_audit", {"url": req.url, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await audit_social_seo(
        url=req.url,
        platforms=req.platforms,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_SOCIAL_SEO_SYS,
        clean_text_fn=_clean,
    )
    result["url"] = req.url
    result["audited_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "social", payload, result
    )
    helper_log(runtime, auth.tenant_id, "social_seo_audit", {"url": req.url, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_landing_page_generate(
    runtime: ContextRuntime, req: LandingPageGenerateReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Generate a conversion-ready landing page structure with schema markup and A/B hooks."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:landing", limit=5, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "landing", payload)
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "landing_page_generate",
            {"product": req.product_name, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await generate_landing_page(
        product_name=req.product_name,
        target_keyword=req.target_keyword,
        audience=req.audience,
        schema_types=req.schema_types,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_LANDING_SYS,
        clean_text_fn=_clean,
    )
    result["product_name"] = req.product_name
    result["target_keyword"] = req.target_keyword
    result["generated_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "landing", payload, result
    )
    helper_log(
        runtime,
        auth.tenant_id,
        "landing_page_generate",
        {"product": req.product_name, "keyword": req.target_keyword, "cached": False},
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_security_seo_audit(
    runtime: ContextRuntime, req: SecuritySeoAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Audit security posture, cloaking signals, spam, and SEO integrity."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:security", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "security", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "security_seo_audit", {"url": req.url, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await audit_security_seo(
        url=req.url,
        check_cloaking=req.check_cloaking,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_SECURITY_SEO_SYS,
        clean_text_fn=_clean,
    )
    result["url"] = req.url
    result["audited_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "security", payload, result
    )
    helper_log(runtime, auth.tenant_id, "security_seo_audit", {"url": req.url, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_internal_linking_suggest(
    runtime: ContextRuntime, req: InternalLinkingReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Generate semantic internal-link suggestions with anchor guidance and placement hints."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:internal_linking", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "internal_linking", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "internal_linking_suggest",
            {"page_url": req.page_url, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await suggest_internal_linking(
        page_url=req.page_url,
        page_content=req.page_content,
        target_urls=req.target_urls,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_INTERNAL_LINKING_SYS,
        clean_text_fn=_clean,
    )
    result["page_url"] = req.page_url
    result["generated_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "internal_linking", payload, result
    )
    helper_log(runtime, auth.tenant_id, "internal_linking_suggest", {"page_url": req.page_url, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}
