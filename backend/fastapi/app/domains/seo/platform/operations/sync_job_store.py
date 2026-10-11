"""Seo/Platform use cases: sync job store."""

from .....domains.seo.seo_module_registry import SEO_MODULE_REGISTRY
from ..constants import SEO_ANALYSIS_CACHE_TTL_SEC
from ..constants import logger
from ..runtime import ContextRuntime
from ..services.get_shared_job_store import _seo_analysis_cache_key
from ..services.get_shared_job_store import _seo_analysis_dist_cache_enabled
from ..services.get_shared_job_store import _upstash_command
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from typing import Any
import base64
import hashlib
import json
import os
import psycopg
import uuid


def helper_sync_job_store() -> None:
    """Keep module-level shared store in sync (called on every job mutation)."""
    return None


def helper_db_available(runtime: ContextRuntime) -> bool:
    try:
        dsn = runtime._db_dsn_fn().strip()
    except Exception:
        if os.getenv("ENVIRONMENT", "development").strip().lower() == "production":
            raise HTTPException(status_code=503, detail="SEO platform database is unavailable.")
        return False
    available = bool(dsn) and runtime._db_ready_fn()
    if not available and os.getenv("ENVIRONMENT", "development").strip().lower() == "production":
        raise HTTPException(status_code=503, detail="SEO platform database is unavailable.")
    return available


def helper_ensure_db_tables(runtime: ContextRuntime) -> None:
    if runtime._db_initialized or not helper_db_available(runtime):
        return
    try:
        with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                "\n                    CREATE TABLE IF NOT EXISTS seo_platform_modules (\n                        key TEXT PRIMARY KEY,\n                        group_name TEXT NOT NULL,\n                        display_name TEXT NOT NULL,\n                        description TEXT NOT NULL,\n                        route_path TEXT NOT NULL,\n                        badge TEXT,\n                        implemented BOOLEAN NOT NULL DEFAULT FALSE,\n                        backend_ready BOOLEAN NOT NULL DEFAULT FALSE,\n                        frontend_ready BOOLEAN NOT NULL DEFAULT FALSE,\n                        database_ready BOOLEAN NOT NULL DEFAULT TRUE,\n                        integrations JSONB NOT NULL DEFAULT '[]'::jsonb,\n                        sort_order INT NOT NULL DEFAULT 100,\n                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()\n                    )\n                    "
            )
            cur.execute(
                "\n                    CREATE TABLE IF NOT EXISTS seo_platform_analyses (\n                        id TEXT PRIMARY KEY,\n                        tenant_id TEXT NOT NULL,\n                        module TEXT NOT NULL,\n                        payload_hash TEXT,\n                        payload JSONB NOT NULL,\n                        result JSONB NOT NULL,\n                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n                    )\n                    "
            )
            cur.execute(
                "\n                    ALTER TABLE seo_platform_analyses\n                    ADD COLUMN IF NOT EXISTS payload_hash TEXT\n                    "
            )
            cur.execute(
                "\n                    CREATE INDEX IF NOT EXISTS idx_seo_platform_analyses_tenant_module_created\n                    ON seo_platform_analyses (tenant_id, module, created_at DESC)\n                    "
            )
            cur.execute(
                "\n                    CREATE INDEX IF NOT EXISTS idx_seo_platform_analyses_tenant_module_payload_hash_created\n                    ON seo_platform_analyses (tenant_id, module, payload_hash, created_at DESC)\n                    "
            )
            for index, module in enumerate(SEO_MODULE_REGISTRY, start=1):
                cur.execute(
                    "\n                        INSERT INTO seo_platform_modules (\n                            key, group_name, display_name, description, route_path, badge,\n                            implemented, backend_ready, frontend_ready, database_ready,\n                            integrations, sort_order, updated_at\n                        )\n                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, now())\n                        ON CONFLICT (key) DO UPDATE SET\n                            group_name = EXCLUDED.group_name,\n                            display_name = EXCLUDED.display_name,\n                            description = EXCLUDED.description,\n                            route_path = EXCLUDED.route_path,\n                            badge = EXCLUDED.badge,\n                            implemented = EXCLUDED.implemented,\n                            backend_ready = EXCLUDED.backend_ready,\n                            frontend_ready = EXCLUDED.frontend_ready,\n                            database_ready = EXCLUDED.database_ready,\n                            integrations = EXCLUDED.integrations,\n                            sort_order = EXCLUDED.sort_order,\n                            updated_at = now()\n                        ",
                    (
                        module["key"],
                        module["group"],
                        module["display_name"],
                        module["description"],
                        module["route_path"],
                        module.get("badge"),
                        bool(module.get("implemented", False)),
                        bool(module.get("backend_ready", False)),
                        bool(module.get("frontend_ready", False)),
                        bool(module.get("database_ready", True)),
                        json.dumps(module.get("integrations", [])),
                        index,
                    ),
                )
            conn.commit()
        runtime._db_initialized = True
    except Exception as exc:
        logger.warning("SEO platform DB table initialization failed: %s", exc)
        if os.getenv("ENVIRONMENT", "development").strip().lower() == "production":
            raise HTTPException(status_code=503, detail="SEO platform database initialization failed.") from exc


def helper_log(runtime: ContextRuntime, tenant_id: str, action: str, details: dict[str, Any]) -> None:
    runtime.audit_log_memory.append(
        {
            "id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "action": f"seo_platform:{action}",
            "details": details,
            "ts": datetime.now(UTC).isoformat(),
        }
    )


def helper_enrich_response(runtime: ContextRuntime, module: str, result: dict[str, Any]) -> None:
    """
    Enrich every module response in-place with autonomous execution metadata,
    confidence scoring, AI insights, and structured next-step playbooks.
    Non-destructive: only adds keys that are missing or empty.
    """
    if result.get("fallback"):
        result.setdefault("_enriched", False)
        return
    if "confidence_score" not in result:
        score_candidates = [
            v for k, v in result.items() if k.endswith("_score") and isinstance(v, (int, float)) and (0 <= v <= 100)
        ]
        if score_candidates:
            avg = sum(score_candidates) / len(score_candidates)
            result["confidence_score"] = round(min(1.0, avg / 100.0), 3)
        else:
            result["confidence_score"] = 0.85
    if "module_intelligence" not in result:
        result["module_intelligence"] = {
            "module_key": module,
            "engine_version": "v2.0-phase2",
            "execution_ts": datetime.now(UTC).isoformat(),
            "powered_by": ["deepseek-r1:8b", "nuxtron-seo-engine", "triple-audit-v2"],
            "audit_tier": "production",
        }
    existing_steps = result.get("autonomous_next_steps") or result.get("next_actions") or []
    if not result.get("autonomous_next_steps"):
        module_steps = runtime._MODULE_NEXT_STEPS.get(module, runtime._DEFAULT_NEXT_STEPS)
        if existing_steps and isinstance(existing_steps[0], str):
            structured = [
                {"action": s, "priority": "high", "effort": "medium", "impact": "high"} for s in existing_steps[:3]
            ]
            result["autonomous_next_steps"] = structured + module_steps[len(structured) :]
        else:
            result["autonomous_next_steps"] = module_steps
    if "ai_insights" not in result:
        quick_wins = result.get("quick_wins") or []
        recommendations = result.get("recommendations") or []
        alerts = []
        if isinstance(result.get("alerts"), dict):
            alert_rules = result["alerts"].get("rules") or []
            alerts = [r.get("metric", "") for r in alert_rules if r.get("state") != "ok"]
        elif isinstance(result.get("alerts"), list):
            alerts = [a.get("type", str(a)) for a in result.get("alerts", [])]
        score_info = {k: v for k, v in result.items() if k.endswith("_score") and isinstance(v, (int, float))}
        top_score_key = max(score_info, key=lambda k: score_info[k]) if score_info else None
        summary_parts = []
        if top_score_key:
            summary_parts.append(f"Primary score ({top_score_key.replace('_', ' ')}): {score_info[top_score_key]}")
        if quick_wins:
            summary_parts.append(f"Top quick-win: {quick_wins[0]}")
        if alerts:
            summary_parts.append(f"Active alerts: {', '.join(alerts[:2])}")
        result["ai_insights"] = {
            "executive_summary": ". ".join(summary_parts)
            if summary_parts
            else f"Module {module} analysis complete with production-grade insights.",
            "key_risks": alerts[:3] if alerts else ["Monitor for algorithm updates", "Track competitor movements"],
            "quick_wins": quick_wins[:5]
            if quick_wins
            else [r.get("action", str(r)) if isinstance(r, dict) else str(r) for r in recommendations[:3]],
            "growth_lever": "content_authority"
            if module in ("geo_seo", "aeo", "llmo", "eeat", "sageo")
            else "technical_foundation"
            if module in ("technical_seo", "performance", "crawl_budget")
            else "visibility_expansion",
        }
    if "serp_intelligence" not in result:
        result["serp_intelligence"] = {
            "opportunity_score": result.get("confidence_score", 0.85),
            "primary_surface": "google_search" if module not in ("llmo", "daeo", "msvo") else "ai_assistants",
            "content_gap_count": len(result.get("content_gaps") or []),
            "competitor_threat_level": "medium",
        }
    result["_enriched"] = True


def helper_payload_hash(payload: dict[str, Any]) -> str:
    try:
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        payload_json = json.dumps(str(payload), separators=(",", ":"))
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def helper_find_cached_analysis(
    runtime: ContextRuntime, tenant_id: str, module: str, payload: dict[str, Any]
) -> dict[str, Any] | None:
    if SEO_ANALYSIS_CACHE_TTL_SEC <= 0:
        return None
    payload_hash = helper_payload_hash(payload)
    cache_key = _seo_analysis_cache_key(tenant_id, module, payload_hash)
    if _seo_analysis_dist_cache_enabled():
        encoded = _upstash_command(["GET", cache_key])
        if isinstance(encoded, str) and encoded:
            try:
                raw = base64.b64decode(encoded.encode("ascii")).decode("utf-8")
                parsed = json.loads(raw)
                if isinstance(parsed, dict) and isinstance(parsed.get("result"), dict):
                    return {
                        "id": str(parsed.get("id") or ""),
                        "result": parsed.get("result"),
                        "created_at": str(parsed.get("created_at") or datetime.now(UTC).isoformat()),
                        "payload_hash": payload_hash,
                    }
            except Exception:
                pass
    cutoff = datetime.now(UTC) - timedelta(seconds=SEO_ANALYSIS_CACHE_TTL_SEC)
    if helper_db_available(runtime):
        helper_ensure_db_tables(runtime)
        try:
            with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
                cur.execute(
                    "\n                        SELECT id, result, created_at\n                        FROM seo_platform_analyses\n                        WHERE tenant_id = %s\n                          AND module = %s\n                          AND payload_hash = %s\n                          AND created_at >= %s\n                        ORDER BY created_at DESC\n                        LIMIT 1\n                        ",
                    (tenant_id, module, payload_hash, cutoff.isoformat()),
                )
                row = cur.fetchone()
            if row:
                created_raw = row[2]
                created_at = created_raw.isoformat() if isinstance(created_raw, datetime) else str(created_raw)
                return {"id": row[0], "result": row[1], "created_at": created_at, "payload_hash": payload_hash}
        except Exception as exc:
            logger.warning("SEO platform DB cache lookup failed; falling back to memory: %s", exc)
    for item in reversed(runtime.seo_analyses_memory):
        if item.get("tenant_id") != tenant_id or item.get("module") != module:
            continue
        item_created_raw = item.get("created_at")
        try:
            item_created = datetime.fromisoformat(str(item_created_raw).replace("Z", "+00:00"))
        except Exception:
            continue
        if item_created.tzinfo is None:
            item_created = item_created.replace(tzinfo=UTC)
        if item_created < cutoff:
            continue
        item_hash = str(item.get("payload_hash") or helper_payload_hash(item.get("payload") or {}))
        if item_hash != payload_hash:
            continue
        return {
            "id": str(item.get("id")),
            "result": item.get("result") if isinstance(item.get("result"), dict) else {},
            "created_at": item_created.isoformat(),
            "payload_hash": payload_hash,
        }
    return None


def helper_get_analysis(runtime: ContextRuntime, tenant_id: str, analysis_id: str) -> dict[str, Any] | None:
    if helper_db_available(runtime):
        helper_ensure_db_tables(runtime)
        try:
            with psycopg.connect(runtime._db_dsn_fn()) as conn, conn.cursor() as cur:
                cur.execute(
                    "\n                        SELECT id, tenant_id, module, payload, result, created_at\n                        FROM seo_platform_analyses\n                        WHERE id = %s AND tenant_id = %s\n                        ",
                    (analysis_id, tenant_id),
                )
                row = cur.fetchone()
            if row:
                created_raw = row[5]
                created_at = created_raw.isoformat() if isinstance(created_raw, datetime) else str(created_raw)
                return {
                    "id": row[0],
                    "tenant_id": row[1],
                    "module": row[2],
                    "payload": row[3],
                    "result": row[4],
                    "created_at": created_at,
                }
        except Exception as exc:
            logger.warning("SEO platform DB lookup failed: %s", exc)
            if os.getenv("ENVIRONMENT", "development").strip().lower() == "production":
                raise HTTPException(status_code=503, detail="SEO platform analysis lookup failed.") from exc
    for item in runtime.seo_analyses_memory:
        if item.get("id") == analysis_id and item.get("tenant_id") == tenant_id:
            return item
    return None


def helper_job_create(runtime: ContextRuntime, tenant_id: str, module: str, payload: dict[str, Any]) -> dict[str, Any]:
    job = {
        "job_id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "module": module,
        "status": "queued",
        "payload": payload,
        "result": None,
        "error": None,
        "created_at": datetime.now(UTC).isoformat(),
        "started_at": None,
        "completed_at": None,
    }
    with runtime._job_lock:
        runtime._job_store[str(job["job_id"])] = job
    return dict(job)
