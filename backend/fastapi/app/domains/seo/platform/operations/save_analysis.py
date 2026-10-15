"""Seo/Platform use cases: save analysis."""

import base64
import json
import os
import uuid
from datetime import UTC, datetime
from functools import partial
from typing import Annotated, Any

import httpx
import psycopg
from fastapi import Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from .....deps import AuthContext, require_auth
from .....domains.seo.seo_module_registry import (
    SEO_MODULE_MAP,
    SEO_MODULE_REGISTRY,
    audit_seo_module_registry,
    grouped_seo_modules,
)
from .....domains.seo.services.seo_on_page_service import analyze_on_page
from .....domains.seo.services.seo_performance_service import raise_performance_unavailable
from .....domains.seo.services.seo_schema_service import generate_schema_markup
from .....domains.seo.services.seo_technical_audit_service import analyze_technical_audit
from ..constants import (
    _ONPAGE_SYS,
    _SCHEMA_SYS,
    _TECHNICAL_SYS,
    OLLAMA_BASE_URL,
    SEO_ANALYSIS_CACHE_TTL_SEC,
    SEO_DEFAULT_MODEL,
    SEO_MODULE_COUNT,
    logger,
)
from ..runtime import ContextRuntime
from ..schemas import OnPageReq, SchemaGenReq, TechnicalAuditReq
from ..services import extract_waterfall as provider_ollama_json
from ..services.get_shared_job_store import (
    _clean,
    _seo_analysis_cache_key,
    _seo_analysis_dist_cache_enabled,
    _upstash_command,
)
from .sync_job_store import (
    helper_db_available,
    helper_enrich_response,
    helper_ensure_db_tables,
    helper_log,
    helper_payload_hash,
)


def helper_save_analysis(
    runtime: ContextRuntime, tenant_id: str, module: str, payload: dict[str, Any], result: dict[str, Any]
) -> str:
    helper_enrich_response(runtime, module, result)
    analysis_id = str(uuid.uuid4())
    created_at = datetime.now(UTC).isoformat()
    payload_hash = helper_payload_hash(payload)
    item = {
        "id": analysis_id,
        "tenant_id": tenant_id,
        "module": module,
        "payload_hash": payload_hash,
        "payload": payload,
        "result": result,
        "created_at": created_at,
    }
    if helper_db_available(runtime):
        helper_ensure_db_tables(runtime)
        try:
            with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
                cur.execute(
                    "\n                        INSERT INTO seo_platform_analyses (id, tenant_id, module, payload_hash, payload, result, created_at)\n                        VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)\n                        ",
                    (analysis_id, tenant_id, module, payload_hash, json.dumps(payload), json.dumps(result), created_at),
                )
                conn.commit()
            return analysis_id
        except Exception as exc:
            logger.warning("SEO platform DB write failed: %s", exc)
            if os.getenv("ENVIRONMENT", "development").strip().lower() == "production":
                raise HTTPException(status_code=503, detail="SEO platform analysis persistence failed.") from exc
    runtime.seo_analyses_memory.append(item)
    if SEO_ANALYSIS_CACHE_TTL_SEC > 0 and _seo_analysis_dist_cache_enabled():
        try:
            cache_key = _seo_analysis_cache_key(tenant_id, module, payload_hash)
            cache_payload = {"id": analysis_id, "result": result, "created_at": created_at}
            raw = json.dumps(cache_payload, separators=(",", ":"))
            encoded = base64.b64encode(raw.encode("utf-8")).decode("ascii")
            _upstash_command(["SETEX", cache_key, str(max(SEO_ANALYSIS_CACHE_TTL_SEC, 30)), encoded])
        except Exception:
            pass
    return analysis_id


def helper_list_analyses(
    runtime: ContextRuntime, tenant_id: str, module: str | None, limit: int
) -> list[dict[str, Any]]:
    cap = max(1, min(limit, 100))
    memory_items = [a for a in runtime.seo_analyses_memory if a.get("tenant_id") == tenant_id]
    if module:
        memory_items = [a for a in memory_items if a.get("module") == module]
    db_items: list[dict[str, Any]] = []
    if helper_db_available(runtime):
        helper_ensure_db_tables(runtime)
        try:
            with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
                if module:
                    cur.execute(
                        "\n                            SELECT id, tenant_id, module, payload, result, created_at\n                            FROM seo_platform_analyses\n                            WHERE tenant_id = %s AND module = %s\n                            ORDER BY created_at DESC\n                            LIMIT %s\n                            ",
                        (tenant_id, module, cap),
                    )
                else:
                    cur.execute(
                        "\n                            SELECT id, tenant_id, module, payload, result, created_at\n                            FROM seo_platform_analyses\n                            WHERE tenant_id = %s\n                            ORDER BY created_at DESC\n                            LIMIT %s\n                            ",
                        (tenant_id, cap),
                    )
                for row in cur.fetchall():
                    created_raw = row[5]
                    created_at = created_raw.isoformat() if isinstance(created_raw, datetime) else str(created_raw)
                    db_items.append(
                        {
                            "id": row[0],
                            "tenant_id": row[1],
                            "module": row[2],
                            "payload": row[3],
                            "result": row[4],
                            "created_at": created_at,
                        }
                    )
        except Exception as exc:
            logger.warning("SEO platform DB read failed: %s", exc)
            if os.getenv("ENVIRONMENT", "development").strip().lower() == "production":
                raise HTTPException(status_code=503, detail="SEO platform analysis lookup failed.") from exc
    merged: dict[str, dict[str, Any]] = {}
    for item in db_items + memory_items:
        item_id = str(item.get("id", ""))
        if not item_id:
            continue
        merged[item_id] = item
    items = list(merged.values())
    items.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
    return items[:cap]


_CUSTOMER_EXCLUDED_MODULE_KEYS = frozenset(
    {
        "client-portal",
        "eyeon",
        "one2target",
        "contentshake",
        "local-seo-suite",
        "map-rank-tracker",
        "local-heatmap",
        "review-reputation-engine",
        "performance-audit",
        "retail-media-app-growth-hub",
        "unified-ads-control-tower",
        "cross-network-campaign-orchestrator",
        "budget-pacing-bid-engine",
        "attribution-conversion-intelligence",
        "ai-creative-keyword-lab",
    }
)
_CUSTOMER_EXCLUDED_MODULE_PREFIXES = ("ahrefs-",)
_CUSTOMER_GROUP_OVERRIDES = {
    "domain-overview": "Search Intelligence",
    "market-explorer": "Market Intelligence",
    "map-rank-tracker": "Local Search",
    "local-heatmap": "Local Search",
    "pla-research": "Paid Search Intelligence",
    "competitor-activity-monitor": "Search Intelligence",
}
_CUSTOMER_ROUTE_OVERRIDES = {
    "competitor-activity-monitor": "/seo/competitor-monitoring",
}
_VENDOR_LABELS = ("ahrefs", "semrush", "one2target", "contentshake", "eyeon")


def _customer_visible_modules(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    visible: list[dict[str, Any]] = []
    for item in items:
        key = str(item.get("key", "")).strip().lower()
        if key in _CUSTOMER_EXCLUDED_MODULE_KEYS or key.startswith(_CUSTOMER_EXCLUDED_MODULE_PREFIXES):
            continue

        module = dict(item)
        group = str(module.get("group", ""))
        if key in _CUSTOMER_GROUP_OVERRIDES:
            module["group"] = _CUSTOMER_GROUP_OVERRIDES[key]
        elif any(label in group.lower() for label in _VENDOR_LABELS) or "parity" in group.lower():
            continue

        if key in _CUSTOMER_ROUTE_OVERRIDES:
            module["route_path"] = _CUSTOMER_ROUTE_OVERRIDES[key]
        metadata = " ".join(
            str(module.get(field, ""))
            for field in ("key", "display_name", "group", "description", "route_path")
        ).lower()
        if any(label in metadata for label in _VENDOR_LABELS):
            continue
        visible.append(module)
    return visible


def helper_list_modules(runtime: ContextRuntime) -> list[dict[str, Any]]:
    if helper_db_available(runtime):
        helper_ensure_db_tables(runtime)
        try:
            with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
                cur.execute(
                    "\n                        SELECT\n                            key, group_name, display_name, description, route_path, badge,\n                            implemented, backend_ready, frontend_ready, database_ready,\n                            integrations\n                        FROM seo_platform_modules\n                        ORDER BY sort_order ASC, key ASC\n                        "
                )
                rows = cur.fetchall()
            modules: list[dict[str, Any]] = []
            for row in rows:
                db_module = {
                    "key": row[0],
                    "group": row[1],
                    "display_name": row[2],
                    "description": row[3],
                    "route_path": row[4],
                    "badge": row[5],
                    "implemented": bool(row[6]),
                    "backend_ready": bool(row[7]),
                    "frontend_ready": bool(row[8]),
                    "database_ready": bool(row[9]),
                    "integrations": row[10] if isinstance(row[10], list) else [],
                }
                registry_module = SEO_MODULE_MAP.get(str(row[0]), {})
                modules.append({**registry_module, **db_module})
            return _customer_visible_modules(modules)
        except Exception as exc:
            logger.warning("SEO platform module registry DB read failed; using fallback: %s", exc)
    return _customer_visible_modules([dict(item) for item in SEO_MODULE_REGISTRY])


def helper_get_module(runtime: ContextRuntime, module_key: str) -> dict[str, Any] | None:
    for item in helper_list_modules(runtime):
        if str(item.get("key")) == module_key:
            return item
    return None


def helper_job_update(runtime: ContextRuntime, job_id: str, **fields: Any) -> None:
    with runtime._job_lock:
        existing = runtime._job_store.get(job_id)
        if not existing:
            return
        existing.update(fields)


def helper_job_get(runtime: ContextRuntime, job_id: str, tenant_id: str) -> dict[str, Any] | None:
    with runtime._job_lock:
        item = runtime._job_store.get(job_id)
        if item is None:
            return None
        if str(item.get("tenant_id")) != tenant_id:
            return None
        return dict(item)


async def helper_run_technical_audit_analysis(req: TechnicalAuditReq) -> dict[str, Any]:
    return await analyze_technical_audit(
        url=req.url,
        issues_raw=req.issues_raw,
        sitemap_url=req.sitemap_url,
        crawl_depth=req.crawl_depth,
        check_mobile_friendly=req.check_mobile_friendly,
        check_core_web_vitals=req.check_core_web_vitals,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_TECHNICAL_SYS,
        clean_text_fn=_clean,
    )


async def helper_run_technical_audit_job(
    runtime: ContextRuntime, job_id: str, tenant_id: str, req: TechnicalAuditReq, payload: dict[str, Any]
) -> None:
    helper_job_update(runtime, job_id, status="running", started_at=datetime.now(UTC).isoformat())
    try:
        result = await helper_run_technical_audit_analysis(req)
        analysis_id = await run_in_threadpool(
            partial(helper_save_analysis, runtime), tenant_id, "technical_audit", payload, result
        )
        response = {"analysis_id": analysis_id, "cached": False, **result}
        helper_job_update(
            runtime, job_id, status="completed", result=response, completed_at=datetime.now(UTC).isoformat(), error=None
        )
        helper_log(
            runtime,
            tenant_id,
            "technical_audit_async",
            {"url": req.url, "analysis_id": analysis_id, "cached": False, "job_id": job_id},
        )
    except Exception as exc:
        helper_job_update(runtime, job_id, status="failed", error=str(exc), completed_at=datetime.now(UTC).isoformat())
        helper_log(runtime, tenant_id, "technical_audit_async", {"url": req.url, "job_id": job_id, "error": str(exc)})


async def helper_run_on_page_shared(req: OnPageReq) -> dict[str, Any]:
    return await analyze_on_page(
        url=req.url,
        content=req.content,
        focus_keyword=req.focus_keyword,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_ONPAGE_SYS,
        clean_text_fn=_clean,
    )


async def helper_run_on_page_job(
    runtime: ContextRuntime, job_id: str, tenant_id: str, req: OnPageReq, payload: dict[str, Any]
) -> None:
    helper_job_update(runtime, job_id, status="running", started_at=datetime.now(UTC).isoformat())
    try:
        result = await helper_run_on_page_shared(req)
        analysis_id = await run_in_threadpool(
            partial(helper_save_analysis, runtime), tenant_id, "on_page", payload, result
        )
        response = {"analysis_id": analysis_id, "cached": False, **result}
        helper_job_update(
            runtime, job_id, status="completed", result=response, completed_at=datetime.now(UTC).isoformat(), error=None
        )
        helper_log(runtime, tenant_id, "on_page_async", {"url": req.url, "analysis_id": analysis_id, "job_id": job_id})
    except Exception as exc:
        helper_job_update(runtime, job_id, status="failed", error=str(exc), completed_at=datetime.now(UTC).isoformat())
        helper_log(runtime, tenant_id, "on_page_async", {"url": req.url, "job_id": job_id, "error": str(exc)})


async def helper_run_schema_shared(req: SchemaGenReq) -> dict[str, Any]:
    return await generate_schema_markup(
        schema_type=req.schema_type,
        content=req.content,
        url=req.url,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_SCHEMA_SYS,
        clean_text_fn=_clean,
    )


async def helper_run_schema_job(
    runtime: ContextRuntime, job_id: str, tenant_id: str, req: SchemaGenReq, payload: dict[str, Any]
) -> None:
    helper_job_update(runtime, job_id, status="running", started_at=datetime.now(UTC).isoformat())
    try:
        result = await helper_run_schema_shared(req)
        analysis_id = await run_in_threadpool(
            partial(helper_save_analysis, runtime), tenant_id, "schema", payload, result
        )
        response = {"analysis_id": analysis_id, "cached": False, **result}
        helper_job_update(
            runtime, job_id, status="completed", result=response, completed_at=datetime.now(UTC).isoformat(), error=None
        )
        helper_log(
            runtime, tenant_id, "schema_async", {"type": req.schema_type, "analysis_id": analysis_id, "job_id": job_id}
        )
    except Exception as exc:
        helper_job_update(runtime, job_id, status="failed", error=str(exc), completed_at=datetime.now(UTC).isoformat())
        helper_log(runtime, tenant_id, "schema_async", {"type": req.schema_type, "job_id": job_id, "error": str(exc)})


async def execute_health(runtime: ContextRuntime):
    """Check SEO platform and Ollama connectivity."""
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass
    return {
        "status": "healthy",
        "service": "seo-platform",
        "modules": SEO_MODULE_COUNT,
        "ai_backend": "ollama",
        "persistence": "postgres" if helper_db_available(runtime) else "memory",
        "ollama_url": OLLAMA_BASE_URL,
        "ollama_connected": ollama_ok,
        "model": SEO_DEFAULT_MODEL,
    }


async def execute_list_modules(runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]):
    """List all SEO modules shown in the SEO hub."""
    modules = helper_list_modules(runtime)
    audit = audit_seo_module_registry(modules)
    grouped_items = grouped_seo_modules(modules)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "source": "database" if helper_db_available(runtime) else "fallback",
        "total": len(modules),
        "implemented": sum(1 for module in modules if bool(module.get("implemented"))),
        "readiness": audit.get("summary", {}),
        "groups": grouped_items,
        "modules": modules,
    }


async def execute_audit_modules(runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]):
    """
    Triple-audit endpoint for production readiness across all SEO modules.
    Covers structural integrity, metadata completeness, and autonomy coverage.
    """
    modules = helper_list_modules(runtime)
    audit = audit_seo_module_registry(modules)
    return {"status": "ok", "tenant_id": auth.tenant_id, "audit": audit}


async def execute_performance_test_locations(
    runtime: ContextRuntime, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()
