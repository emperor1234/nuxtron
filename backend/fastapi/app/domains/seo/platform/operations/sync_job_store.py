"""Seo/Platform use cases: sync job store."""

from .....domains.seo.seo_module_registry import SEO_MODULE_REGISTRY
from ..constants import SEO_ANALYSIS_CACHE_TTL_SEC
from ..constants import logger
from ..runtime import ContextRuntime
from ..services.get_shared_job_store import _seo_analysis_cache_key
from ..services.get_shared_job_store import _strict_no_mock_mode
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
    """Deliberately a no-op.

    This used to stamp every response with a hard-coded 0.85 confidence, a
    "powered_by: deepseek-r1 / audit_tier: production" claim, canned next steps,
    and a fixed "medium" competitor threat level — none of which was measured,
    and all of which was attached even when no model ran. A response now carries
    only what the analysis itself produced.
    """
    del runtime, module, result


# Modules whose rule-based output is a deterministic computation over the
# caller's own input (text metrics, parsed log lines, generated JSON-LD).
# Every other module without a connected AI model would only emit templated
# guesses about search engines, competitors and third parties.
_RULE_BASED_MODULES = frozenset({"on_page", "schema", "log_file", "technical_audit"})
_AI_UNAVAILABLE_MESSAGE = (
    "This analysis needs a connected AI model and none is available, so no result was produced. "
    "Estimates are never substituted for a measurement."
)


def helper_require_ai_for_result(module: str, result: dict[str, Any]) -> None:
    """Refuse templated heuristic output in strict (production) mode."""
    if module in _RULE_BASED_MODULES or not _strict_no_mock_mode():
        return
    if result.get("analysis_mode") == "heuristic" or result.get("ai_available") is False:
        raise HTTPException(
            status_code=503,
            detail={"code": "AI_MODEL_UNAVAILABLE", "message": _AI_UNAVAILABLE_MESSAGE},
        )


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
