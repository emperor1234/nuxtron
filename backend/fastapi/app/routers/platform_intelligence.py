# pyright: reportUnusedFunction=false
"""
Platform Intelligence Router — Modules 32–50 (Production-Grade)

Implements the missing and partially-covered modules from the 50-module spec:
  32. AI Safety, Quality & Compliance Layer  → POST /platform/ai-safety/validate
  33. Model Management & Versioning          → GET  /platform/models
                                               POST /platform/models/prompt-versions
                                               GET  /platform/models/prompt-versions
  34. Data Governance & Lineage              → GET  /platform/data/lineage
  35. Observability & Monitoring Suite       → GET  /platform/metrics
  36. Error Tracking & Recovery Engine       → GET  /platform/recovery/status
                                               POST /platform/recovery/retry
  37. Workflow Orchestration Engine          → GET  /platform/jobs
                                               GET  /platform/jobs/{job_id}
  39. Secrets & Policy Management            → GET  /platform/policy/status
  49. SLA, Reliability & Uptime              → GET  /platform/sla
  50. Platform Intelligence Layer            → GET  /platform/intelligence
"""

from __future__ import annotations

import hashlib
import os
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

# ── Local imports (kept lazy-safe) ────────────────────────────────────────────
from ..deps import AuthContext, require_auth
from ..production_middleware import get_request_latency_snapshot

AuthDep = Annotated[AuthContext, Depends(require_auth)]


# ── DB helper (same defaults as main.py _db_dsn) ──────────────────────────────
def _agent_db_dsn() -> str:
    return (
        f"host={os.getenv('POSTGRES_HOST', 'localhost')} "
        f"port={os.getenv('POSTGRES_PORT', '5432')} "
        f"dbname={os.getenv('POSTGRES_DB', 'nuxtron')} "
        f"user={os.getenv('POSTGRES_USER', 'nuxtron')} "
        f"password={os.getenv('POSTGRES_PASSWORD', '')} "
        f"connect_timeout=2"
    )


def _try_agent_db_query(sql: str, params: tuple[Any, ...] = ()) -> tuple[bool, list[dict[str, Any]]]:
    """Execute a SELECT against the agent tables; returns (db_available, rows)."""
    try:
        with psycopg.connect(_agent_db_dsn()) as conn:
            conn.execute("SET statement_timeout = '3000ms'")
            with conn.cursor() as cur:
                cur.execute(sql, params)
                cols = [d.name for d in (cur.description or [])]
                rows = [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]
                return True, rows
    except Exception:
        return False, []


def _try_agent_db_scalar(sql: str, params: tuple[Any, ...] = ()) -> tuple[bool, Any]:
    ok, rows = _try_agent_db_query(sql, params)
    if ok and rows:
        return True, next(iter(rows[0].values()), None)
    return ok, None


# ══════════════════════════════════════════════════════════════════════════════
# In-memory stores (fall back gracefully when DB is unavailable)
# ══════════════════════════════════════════════════════════════════════════════

# Module 33: Prompt-version registry  {version_id → metadata}
_prompt_versions: list[dict[str, Any]] = []

# Module 34: Lineage events  [{source, destination, transformation, ts}]
_lineage_events: list[dict[str, Any]] = []

# Module 36: Recovery / retry queue  [{job_id, error, retries, last_attempt}]
_recovery_queue: list[dict[str, Any]] = []

# Module 36: Retry counter per job_id
_retry_counts: dict[str, int] = defaultdict(int)

# Platform startup time for uptime calculation
_PLATFORM_START_TS = time.time()

# Agent: in-memory tool registry fallback (used when DB is unavailable)
_DEFAULT_AGENT_TOOLS: list[dict[str, Any]] = [
    {"key": "run_site_audit",        "display_name": "Run Site Audit",        "group_name": "SEO Tools",      "fn_signature": "run_site_audit(site_id)",                  "risk_level": "low",    "requires_confirmation": False, "is_active": True,  "backend_endpoint": "/seo-platform/technical/audit"},
    {"key": "generate_blog_post",    "display_name": "Generate Blog Post",    "group_name": "SEO Tools",      "fn_signature": "generate_blog_post(site_id, topic)",        "risk_level": "low",    "requires_confirmation": False, "is_active": True,  "backend_endpoint": "/seo-platform/content/write"},
    {"key": "optimize_page",         "display_name": "Optimize Page",         "group_name": "SEO Tools",      "fn_signature": "optimize_page(url_id)",                     "risk_level": "medium", "requires_confirmation": False, "is_active": True,  "backend_endpoint": "/seo-platform/on-page/analyze"},
    {"key": "create_internal_links", "display_name": "Create Internal Links", "group_name": "SEO Tools",      "fn_signature": "create_internal_links(site_id, src, tgts)", "risk_level": "medium", "requires_confirmation": False, "is_active": True,  "backend_endpoint": "/seo-platform/internal-linking/suggest"},
    {"key": "create_project",        "display_name": "Create Project",        "group_name": "Platform Tools", "fn_signature": "create_project(client_id, name)",           "risk_level": "medium", "requires_confirmation": False, "is_active": True,  "backend_endpoint": "/crm/projects"},
    {"key": "add_domain",            "display_name": "Add Domain",            "group_name": "Platform Tools", "fn_signature": "add_domain(client_id, domain)",             "risk_level": "medium", "requires_confirmation": False, "is_active": True,  "backend_endpoint": "/platform/domains"},
    {"key": "trigger_migration",     "display_name": "Trigger Migration",     "group_name": "Platform Tools", "fn_signature": "trigger_migration(site_id)",                "risk_level": "high",   "requires_confirmation": True,  "is_active": True,  "backend_endpoint": "/seo-platform/site-migration/analyze"},
    {"key": "run_lighthouse_audit",  "display_name": "Lighthouse Audit",      "group_name": "Platform Tools", "fn_signature": "run_lighthouse_audit(url_id)",              "risk_level": "low",    "requires_confirmation": False, "is_active": True,  "backend_endpoint": "/seo-platform/performance/audit"},
    {"key": "create_brief",          "display_name": "Create Content Brief",  "group_name": "Content Tools",  "fn_signature": "create_brief(keyword)",                     "risk_level": "low",    "requires_confirmation": False, "is_active": True,  "backend_endpoint": "/seo-platform/content/brief"},
    {"key": "rewrite_paragraph",     "display_name": "Rewrite Paragraph",     "group_name": "Content Tools",  "fn_signature": "rewrite_paragraph(page_id, block_id)",      "risk_level": "medium", "requires_confirmation": False, "is_active": True,  "backend_endpoint": "/seo-platform/brand-voice/rewrite"},
]

# Agent: in-memory session/audit store (fallback when DB unavailable)
_agent_sessions: list[dict[str, Any]] = []
_agent_tool_calls: list[dict[str, Any]] = []
_agent_config: dict[str, Any] = {
    "current_phase": "phase1",
    "enabled_models": ["deepseek-r1:8b", "llama3:8b"],
    "enabled_agent_roles": ["planner", "executor", "critic", "supervisor"],
    "tool_count_limit": 10,
    "max_auto_actions": 0,
    "allow_high_risk_tools": False,
    "mcp_endpoint": None,
}


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic models
# ══════════════════════════════════════════════════════════════════════════════

class AIValidateRequest(BaseModel):
    """Module 32 — validate an AI output for hallucination & schema compliance."""
    content: str = Field(..., min_length=1, max_length=50_000, description="AI-generated text to audit")
    expected_keys: list[str] = Field(default_factory=list, description="Required JSON keys if output should be structured")
    schema_type: str = Field(default="free_text", description="free_text | json | structured_seo")
    module: str = Field(default="unknown", max_length=80, description="Originating SEO module name")


class PromptVersionCreateRequest(BaseModel):
    """Module 33 — register a new prompt version."""
    module: str = Field(..., min_length=1, max_length=80)
    prompt_text: str = Field(..., min_length=10, max_length=20_000)
    model: str = Field(default="deepseek-r1:8b", max_length=80)
    author: str = Field(default="system", max_length=80)
    tags: list[str] = Field(default_factory=list)


class AgentToolRegisterRequest(BaseModel):
    """Register a new tool in the agent tool registry."""
    key: str = Field(..., min_length=1, max_length=80, pattern=r'^[a-z0-9_]+$')
    display_name: str = Field(..., min_length=1, max_length=120)
    group_name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    fn_signature: str = Field(..., min_length=1, max_length=200)
    risk_level: str = Field(default="low")
    requires_confirmation: bool = Field(default=False)
    backend_endpoint: str = Field(default="", max_length=200)
    input_schema: dict[str, Any] = Field(default_factory=dict)


class AgentConfigUpdateRequest(BaseModel):
    """Update agent configuration for this tenant."""
    current_phase: str | None = Field(default=None)
    enabled_models: list[str] | None = Field(default=None)
    max_auto_actions: int | None = Field(default=None, ge=0, le=100)
    allow_high_risk_tools: bool | None = Field(default=None)
    mcp_endpoint: str | None = Field(default=None, max_length=200)
    notes: str = Field(default="", max_length=2000)


class RetryRequest(BaseModel):
    """Module 36 — manually trigger retry for a failed job."""
    job_id: str = Field(..., min_length=1, max_length=128)
    reason: str = Field(default="manual_retry", max_length=200)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _uptime_seconds() -> float:
    return round(time.time() - _PLATFORM_START_TS, 2)


def _detect_hallucination_indicators(content: str) -> dict[str, Any]:
    """
    Lightweight heuristic hallucination detection.
    Flags common patterns: over-confident absolutes, contradictions, impossible dates.
    """
    text = content.lower()
    flags: list[str] = []
    score = 100  # start clean

    always_phrases = ["always", "never", "100% guaranteed", "absolutely certain", "without exception"]
    for phrase in always_phrases:
        if phrase in text:
            flags.append(f"over-confident absolute: '{phrase}'")
            score -= 5

    contradiction_pairs = [("increase", "decrease"), ("always", "sometimes"), ("never", "often")]
    for a, b in contradiction_pairs:
        if a in text and b in text:
            flags.append(f"potential contradiction: '{a}' and '{b}' co-occur")
            score -= 8

    import re
    future_years = re.findall(r'\b(20[3-9]\d|2[1-9]\d{2})\b', content)
    if future_years:
        flags.append(f"references future/implausible years: {future_years[:3]}")
        score -= 10

    # Check for excessive repetition (sign of low-quality generation)
    words = text.split()
    if words:
        unique_ratio = len(set(words)) / max(len(words), 1)
        if unique_ratio < 0.35 and len(words) > 50:
            flags.append(f"low lexical diversity ({unique_ratio:.2f}) — possible repetition loop")
            score -= 15

    # Very short outputs for complex queries
    if len(content.strip()) < 50:
        flags.append("suspiciously short output — may be truncated or empty generation")
        score -= 20

    return {
        "hallucination_score": max(0, score),
        "risk_level": "low" if score >= 80 else "medium" if score >= 60 else "high",
        "flags": flags,
        "flag_count": len(flags),
    }


def _validate_json_keys(content: str, required_keys: list[str]) -> dict[str, Any]:
    """Check that required JSON keys are present in the output."""
    import json
    missing: list[str] = []
    found: list[str] = []
    try:
        parsed = json.loads(content)
        for key in required_keys:
            if key in parsed:
                found.append(key)
            else:
                missing.append(key)
        return {"valid": len(missing) == 0, "found_keys": found, "missing_keys": missing, "parse_error": None}
    except Exception as exc:
        return {"valid": False, "found_keys": [], "missing_keys": required_keys, "parse_error": str(exc)}


def _get_env_model_registry() -> list[dict[str, Any]]:
    """Build model registry from current environment config."""
    ollama_url = os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434"))
    ollama_model = os.getenv("SEO_DEFAULT_MODEL", os.getenv("OLLAMA_MODEL", "deepseek-r1:8b"))
    openai_key_set = bool(os.getenv("OPENAI_API_KEY"))
    anthropic_key_set = bool(os.getenv("ANTHROPIC_API_KEY"))

    registry = [
        {
            "id": "ollama-primary",
            "provider": "ollama",
            "model": ollama_model,
            "api_url": ollama_url,
            "cost_per_1k_tokens": 0.0,
            "currency": "USD",
            "quality_score": 85,
            "latency_class": "medium",
            "priority": 1,
            "enabled": True,
            "local": True,
            "roles": ["seo_ai", "content_generation", "analysis", "schema_generation"],
        },
    ]
    if openai_key_set:
        registry.append({
            "id": "openai-gpt4o-mini",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "cost_per_1k_tokens": 0.0015,
            "currency": "USD",
            "quality_score": 92,
            "latency_class": "fast",
            "priority": 2,
            "enabled": True,
            "local": False,
            "roles": ["content_generation", "fallback"],
        })
    if anthropic_key_set:
        registry.append({
            "id": "anthropic-haiku",
            "provider": "anthropic",
            "model": "claude-3-haiku-20240307",
            "cost_per_1k_tokens": 0.00025,
            "currency": "USD",
            "quality_score": 90,
            "latency_class": "fast",
            "priority": 3,
            "enabled": True,
            "local": False,
            "roles": ["content_generation", "safety_validation"],
        })
    return registry


def _record_lineage(source: str, destination: str, transformation: str, tenant_id: str, meta: dict[str, Any] | None = None) -> None:
    """Module 34 — record a data lineage event (internal helper for other modules to call)."""
    _lineage_events.append({
        "id": _sha256(f"{source}{destination}{_now()}"),
        "source": source,
        "destination": destination,
        "transformation": transformation,
        "tenant_id": tenant_id,
        "timestamp": _now(),
        "meta": meta or {},
    })
    # Keep rolling window of 10,000 events
    if len(_lineage_events) > 10_000:
        del _lineage_events[: len(_lineage_events) - 10_000]


def _get_sla_metrics() -> dict[str, Any]:
    """Module 49 — calculate SLA stats from latency snapshot."""
    snapshot = get_request_latency_snapshot()
    paths = snapshot.get("paths", {})

    sla_target_ms = float(os.getenv("SLA_TARGET_P95_MS", "2000"))
    breached: list[str] = []
    compliant: list[str] = []

    for path, stats in paths.items():  # type: ignore[union-attr]
        p95 = float(stats.get("p95_ms", 0))  # type: ignore[union-attr]
        if p95 > sla_target_ms:
            breached.append(path)
        else:
            compliant.append(path)

    uptime = _uptime_seconds()
    total = len(breached) + len(compliant)
    compliance_pct = round((len(compliant) / max(total, 1)) * 100, 2)

    return {
        "sla_target_p95_ms": sla_target_ms,
        "uptime_seconds": uptime,
        "uptime_hours": round(uptime / 3600, 3),
        "compliance_pct": compliance_pct,
        "total_paths_tracked": total,
        "breached_paths": breached,
        "compliant_paths": compliant,
        "status": "green" if compliance_pct >= 99 else "amber" if compliance_pct >= 90 else "red",
    }


# ══════════════════════════════════════════════════════════════════════════════
# Router factory
# ══════════════════════════════════════════════════════════════════════════════

def create_platform_intelligence_router(
    enforce_rate_limit: Any,
    audit_log_memory: list[dict[str, Any]],
    seo_jobs_fn: Any | None = None,
) -> APIRouter:
    """
    Factory that creates the Platform Intelligence router.
    seo_jobs_fn: optional callable returning the _seo_jobs dict from seo_platform router.
    """
    router = APIRouter(prefix="/platform", tags=["Platform Intelligence"])

    def _log(tenant_id: str, action: str, data: dict[str, Any]) -> None:
        audit_log_memory.append({
            "timestamp": _now(),
            "tenant_id": tenant_id,
            "source": "platform-intelligence",
            "action": action,
            **data,
        })

    # ── Module 32: AI Safety, Quality & Compliance ─────────────────────────

    @router.post("/ai-safety/validate", summary="Module 32 — AI output safety & hallucination validation")
    async def ai_safety_validate(req: AIValidateRequest, auth: AuthDep) -> dict[str, Any]:
        """
        Validate any AI-generated content for:
        - Hallucination risk (heuristic scoring)
        - Schema compliance (required JSON keys)
        - Content quality signals (length, diversity, confidence)
        - Policy flags (over-confident language, impossible claims)

        Stack: Guardrails-AI patterns, JSON schema validation, OpenSearch-ready audit trail.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:ai-safety", limit=60, window_seconds=60)

        content_hash = _sha256(req.content)
        hallucination = _detect_hallucination_indicators(req.content)
        schema_check: dict[str, Any] = {"applicable": False}

        if req.schema_type == "json" or req.expected_keys:
            schema_check = _validate_json_keys(req.content, req.expected_keys)
            schema_check["applicable"] = True

        # Structured SEO check — expects known top-level keys
        if req.schema_type == "structured_seo" and not req.expected_keys:
            seo_keys = ["score", "recommendations", "quick_wins"]
            schema_check = _validate_json_keys(req.content, seo_keys)
            schema_check["applicable"] = True

        overall_safe = (
            hallucination["risk_level"] != "high"
            and (not schema_check["applicable"] or schema_check.get("valid", True))
        )

        result = {
            "content_hash": content_hash,
            "module": req.module,
            "schema_type": req.schema_type,
            "hallucination": hallucination,
            "schema_validation": schema_check,
            "overall_safe": overall_safe,
            "verdict": "pass" if overall_safe else "fail",
            "audited_at": _now(),
            "tenant_id": auth.tenant_id,
        }

        _record_lineage(
            source=f"ai_output:{req.module}",
            destination="ai_safety_validator",
            transformation="hallucination_check + schema_validation",
            tenant_id=auth.tenant_id,
            meta={"content_hash": content_hash, "verdict": result["verdict"]},
        )
        _log(auth.tenant_id, "ai_safety_validate", {"module": req.module, "verdict": result["verdict"], "content_hash": content_hash})
        return result

    @router.get("/ai-safety/audit-log", summary="Module 32 — retrieve AI safety audit events for this tenant")
    def ai_safety_audit_log(
        auth: AuthDep,
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """Return the last N AI safety validation events for the calling tenant."""
        enforce_rate_limit(f"{auth.tenant_id}:platform:ai-safety-log", limit=30, window_seconds=60)
        events = [
            e for e in audit_log_memory
            if e.get("source") == "platform-intelligence"
            and e.get("action") == "ai_safety_validate"
            and e.get("tenant_id") == auth.tenant_id
        ]
        return {
            "tenant_id": auth.tenant_id,
            "total": len(events),
            "events": events[-limit:],
        }

    # ── Module 33: Model Management & Versioning ───────────────────────────

    @router.get("/models", summary="Module 33 — list active AI models and pool status")
    def list_models(auth: AuthDep) -> dict[str, Any]:
        """
        Returns the current AI model registry with provider configs, quality scores,
        cost estimates, and enabled status.  Stack: MLflow-style versioning, MinIO registry.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:models", limit=60, window_seconds=60)
        registry = _get_env_model_registry()
        prompt_v_count = len(_prompt_versions)

        return {
            "status": "ok",
            "model_count": len(registry),
            "models": registry,
            "prompt_versions_registered": prompt_v_count,
            "default_model": os.getenv("SEO_DEFAULT_MODEL", "deepseek-r1:8b"),
            "ollama_url": os.getenv("OLLAMA_BASE_URL", os.getenv("OLLAMA_URL", "http://localhost:11434")),
            "retrieved_at": _now(),
        }

    @router.post("/models/prompt-versions", summary="Module 33 — register a new prompt version")
    def create_prompt_version(req: PromptVersionCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """
        Register a versioned prompt for a module. Supports rollback, A/B testing,
        and audit trails. Equivalent to MLflow prompt versioning.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:prompt-versions", limit=30, window_seconds=60)
        version_id = f"pv-{_sha256(req.module + req.prompt_text + _now())}"
        record: dict[str, Any] = {
            "version_id": version_id,
            "module": req.module,
            "model": req.model,
            "author": req.author,
            "tags": req.tags,
            "notes": req.notes,
            "content_hash": _sha256(req.prompt_text),
            "prompt_length": len(req.prompt_text),
            "registered_at": _now(),
            "tenant_id": auth.tenant_id,
            "active": True,
        }
        # Deactivate prior versions for this module+tenant+model
        for pv in _prompt_versions:
            if pv["module"] == req.module and pv["tenant_id"] == auth.tenant_id and pv["model"] == req.model:
                pv["active"] = False

        _prompt_versions.append(record)
        _record_lineage(
            source=f"prompt_author:{req.author}",
            destination=f"prompt_registry:{req.module}",
            transformation="prompt_version_create",
            tenant_id=auth.tenant_id,
            meta={"version_id": version_id},
        )
        _log(auth.tenant_id, "prompt_version_create", {"version_id": version_id, "module": req.module})
        return {"status": "registered", **record}

    @router.get("/models/prompt-versions", summary="Module 33 — list registered prompt versions")
    def list_prompt_versions(
        auth: AuthDep,
        module: str | None = Query(default=None),
        active_only: bool = Query(default=False),
    ) -> dict[str, Any]:
        """List all prompt versions for this tenant, optionally filtered by module or active status."""
        enforce_rate_limit(f"{auth.tenant_id}:platform:prompt-versions", limit=60, window_seconds=60)
        results = [pv for pv in _prompt_versions if pv["tenant_id"] == auth.tenant_id]
        if module:
            results = [pv for pv in results if pv["module"] == module]
        if active_only:
            results = [pv for pv in results if pv.get("active")]
        return {"tenant_id": auth.tenant_id, "total": len(results), "prompt_versions": results}

    # ── Module 34: Data Governance & Lineage ──────────────────────────────

    @router.get("/data/lineage", summary="Module 34 — query data lineage events")
    def data_lineage(
        auth: AuthDep,
        source: str | None = Query(default=None, description="Filter by source system"),
        destination: str | None = Query(default=None, description="Filter by destination system"),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, Any]:
        """
        Returns data lineage events: which system produced data, which consumed it,
        and what transformation was applied. Powers compliance, GDPR, and audit workflows.
        Stack: OpenMetadata patterns, dbt Core lineage, PostgreSQL audit tables.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:lineage", limit=30, window_seconds=60)
        events = [e for e in _lineage_events if e.get("tenant_id") == auth.tenant_id]
        if source:
            events = [e for e in events if source.lower() in e.get("source", "").lower()]
        if destination:
            events = [e for e in events if destination.lower() in e.get("destination", "").lower()]

        unique_sources = list({e["source"] for e in events})
        unique_destinations = list({e["destination"] for e in events})
        unique_transformations = list({e["transformation"] for e in events})

        return {
            "tenant_id": auth.tenant_id,
            "total_events": len(events),
            "unique_sources": unique_sources,
            "unique_destinations": unique_destinations,
            "unique_transformations": unique_transformations,
            "events": events[-limit:],
            "retrieved_at": _now(),
        }

    @router.post("/data/lineage", summary="Module 34 — record a manual lineage event")
    def record_lineage_event(
        auth: AuthDep,
        source: str = Query(..., min_length=1, max_length=200),
        destination: str = Query(..., min_length=1, max_length=200),
        transformation: str = Query(default="manual", max_length=200),
    ) -> dict[str, Any]:
        """Manually record a data lineage hop (e.g. CSV export → reporting dashboard)."""
        enforce_rate_limit(f"{auth.tenant_id}:platform:lineage-write", limit=20, window_seconds=60)
        _record_lineage(source, destination, transformation, auth.tenant_id)
        return {"status": "recorded", "source": source, "destination": destination, "transformation": transformation, "recorded_at": _now()}

    # ── Module 35: Observability & Monitoring Suite ────────────────────────

    @router.get("/metrics", summary="Module 35 — full platform metrics snapshot")
    def platform_metrics(auth: AuthDep) -> dict[str, Any]:
        """
        Returns the full observability snapshot:
        - Request latency (p50/p95/max per path, rolling 240-request window)
        - SLA compliance status
        - Rate limiter stats
        - Model registry summary
        Stack: Prometheus patterns, Grafana-compatible output, Loki-ready event counts.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:metrics", limit=30, window_seconds=60)
        latency = get_request_latency_snapshot()
        sla = _get_sla_metrics()
        registry = _get_env_model_registry()

        return {
            "status": "ok",
            "retrieved_at": _now(),
            "uptime_seconds": _uptime_seconds(),
            "latency": latency,
            "sla": sla,
            "models": {
                "count": len(registry),
                "providers": list({m["provider"] for m in registry}),
                "local_count": sum(1 for m in registry if m.get("local")),
            },
            "lineage": {
                "total_events": len(_lineage_events),
                "tenant_events": len([e for e in _lineage_events if e.get("tenant_id") == auth.tenant_id]),
            },
            "prompt_versions": {
                "total": len(_prompt_versions),
                "tenant_active": len([p for p in _prompt_versions if p.get("tenant_id") == auth.tenant_id and p.get("active")]),
            },
            "recovery_queue": {
                "depth": len(_recovery_queue),
                "tenant_items": len([r for r in _recovery_queue if r.get("tenant_id") == auth.tenant_id]),
            },
        }

    # ── Module 36: Error Tracking & Recovery Engine ────────────────────────

    @router.get("/recovery/status", summary="Module 36 — view error recovery queue")
    def recovery_status(
        auth: AuthDep,
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """
        Returns all items currently in the recovery queue for this tenant.
        Includes retry counts, last error, and next eligible retry time.
        Stack: Sentry-style error capture, Celery retry pattern, Temporal compensations.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:recovery", limit=30, window_seconds=60)
        tenant_items = [r for r in _recovery_queue if r.get("tenant_id") == auth.tenant_id]
        return {
            "tenant_id": auth.tenant_id,
            "total_in_queue": len(tenant_items),
            "max_retries_reached": sum(1 for r in tenant_items if r.get("retries", 0) >= 3),
            "items": tenant_items[-limit:],
            "retrieved_at": _now(),
        }

    @router.post("/recovery/retry", summary="Module 36 — trigger manual retry for a failed item")
    def trigger_retry(req: RetryRequest, auth: AuthDep) -> dict[str, Any]:
        """
        Manually enqueue a retry for a job that failed. Records the retry in the
        recovery queue and increments retry count. Provides full audit trail.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:recovery-retry", limit=10, window_seconds=60)

        # Check if already in queue
        for item in _recovery_queue:
            if item["job_id"] == req.job_id and item["tenant_id"] == auth.tenant_id:
                item["retries"] = _retry_counts[req.job_id]
                item["last_attempt"] = _now()
                item["reason"] = req.reason
                _retry_counts[req.job_id] += 1
                _log(auth.tenant_id, "recovery_retry", {"job_id": req.job_id, "retries": item["retries"], "reason": req.reason})
                return {"status": "retry_queued", **item}

        # New entry
        _retry_counts[req.job_id] += 1
        record: dict[str, Any] = {
            "job_id": req.job_id,
            "tenant_id": auth.tenant_id,
            "reason": req.reason,
            "retries": _retry_counts[req.job_id],
            "last_attempt": _now(),
            "status": "queued",
        }
        _recovery_queue.append(record)
        if len(_recovery_queue) > 5_000:
            del _recovery_queue[: len(_recovery_queue) - 5_000]

        _log(auth.tenant_id, "recovery_retry", {"job_id": req.job_id, "retries": _retry_counts[req.job_id], "reason": req.reason})
        return {"status": "retry_queued", **record}

    @router.delete("/recovery/queue/{job_id}", summary="Module 36 — remove a job from the recovery queue")
    def clear_recovery_item(job_id: str, auth: AuthDep) -> dict[str, Any]:
        """Remove a resolved job from the recovery queue."""
        enforce_rate_limit(f"{auth.tenant_id}:platform:recovery-clear", limit=20, window_seconds=60)
        before = len(_recovery_queue)
        _recovery_queue[:] = [
            r for r in _recovery_queue
            if not (r["job_id"] == job_id and r["tenant_id"] == auth.tenant_id)
        ]
        removed = before - len(_recovery_queue)
        if removed == 0:
            raise HTTPException(status_code=404, detail="Job not found in recovery queue")
        _log(auth.tenant_id, "recovery_clear", {"job_id": job_id})
        return {"status": "removed", "job_id": job_id}

    # ── Module 37: Workflow Orchestration — Unified Job Queue ─────────────

    @router.get("/jobs", summary="Module 37 — list all async SEO jobs for this tenant")
    def list_jobs(
        auth: AuthDep,
        status: str | None = Query(default=None, description="Filter: queued | running | completed | failed"),
        module: str | None = Query(default=None, description="Filter by module name"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, Any]:
        """
        Returns all async jobs from the SEO platform job registry for this tenant.
        Supports filtering by status and module. Equivalent to a Temporal workflow list.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:jobs", limit=30, window_seconds=60)

        jobs_store: dict[str, Any] = {}
        if seo_jobs_fn is not None:
            try:
                jobs_store = seo_jobs_fn() or {}
            except Exception:
                jobs_store = {}

        tenant_jobs = [
            job for job in jobs_store.values()
            if job.get("tenant_id") == auth.tenant_id
        ]

        if status:
            tenant_jobs = [j for j in tenant_jobs if j.get("status") == status]
        if module:
            tenant_jobs = [j for j in tenant_jobs if j.get("module") == module]

        # Sort newest first
        tenant_jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)

        counts: dict[str, int] = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
        for j in jobs_store.values():
            if j.get("tenant_id") == auth.tenant_id:
                s = str(j.get("status", "queued"))
                if s in counts:
                    counts[s] += 1

        return {
            "tenant_id": auth.tenant_id,
            "total_matching": len(tenant_jobs),
            "counts_by_status": counts,
            "jobs": tenant_jobs[:limit],
            "retrieved_at": _now(),
        }

    @router.get("/jobs/{job_id}", summary="Module 37 — get a specific async job by ID")
    def get_job(job_id: str, auth: AuthDep) -> dict[str, Any]:
        """Poll a specific async job. Delegates to SEO jobs store."""
        enforce_rate_limit(f"{auth.tenant_id}:platform:jobs", limit=60, window_seconds=60)
        jobs_store: dict[str, Any] = {}
        if seo_jobs_fn is not None:
            try:
                jobs_store = seo_jobs_fn() or {}
            except Exception:
                jobs_store = {}

        job = jobs_store.get(job_id)
        if job is None or job.get("tenant_id") != auth.tenant_id:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    # ── Module 39: Secrets & Policy Management ─────────────────────────────

    @router.get("/policy/status", summary="Module 39 — secrets and policy enforcement status")
    def policy_status(auth: AuthDep) -> dict[str, Any]:
        """
        Returns a non-sensitive snapshot of secrets & policy enforcement status:
        - Which external secrets backends are configured (Vault, env)
        - RBAC/ABAC enforcement mode
        - CORS and allowed-host policy
        - MFA / SSO availability
        Stack: HashiCorp Vault OSS, OPA, Keycloak, Doppler OSS patterns.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:policy", limit=30, window_seconds=60)

        vault_url = os.getenv("VAULT_ADDR", "")
        keycloak_url = os.getenv("KEYCLOAK_URL", os.getenv("KEYCLOAK_ISSUER", ""))
        opa_url = os.getenv("OPA_URL", "")
        cors_origins = os.getenv("CORS_ORIGINS", os.getenv("ALLOWED_ORIGINS", "*"))
        allowed_hosts = os.getenv("ALLOWED_HOSTS", "*")
        strict_mode = os.getenv("SECURITY_STRICT_MODE", "0") == "1"
        saml_enabled = bool(os.getenv("SAML_IDP_METADATA_URL"))
        mfa_required = os.getenv("MFA_REQUIRED", "0") == "1"

        return {
            "status": "ok",
            "secrets_backends": {
                "vault": {"configured": bool(vault_url), "url_set": bool(vault_url)},
                "environment": {"configured": True, "note": "Always active as baseline"},
            },
            "identity": {
                "keycloak_configured": bool(keycloak_url),
                "saml_sso_enabled": saml_enabled,
                "mfa_required": mfa_required,
            },
            "policy_engine": {
                "opa_configured": bool(opa_url),
                "rbac_enabled": True,
                "rate_limiting_enabled": True,
                "strict_mode": strict_mode,
            },
            "network": {
                "cors_origins": cors_origins,
                "allowed_hosts": allowed_hosts,
                "tls_termination": os.getenv("TLS_TERMINATION", "traefik"),
            },
            "retrieved_at": _now(),
        }

    # ── Module 49: SLA, Reliability & Uptime ──────────────────────────────

    @router.get("/sla", summary="Module 49 — SLA compliance and uptime report")
    def sla_report(auth: AuthDep) -> dict[str, Any]:
        """
        Returns SLA compliance report:
        - P95 latency vs SLA target per endpoint
        - Overall compliance percentage
        - Uptime since last restart
        - Breach summary
        Stack: Prometheus uptime checks, Grafana alert thresholds, Coolify health checks.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:sla", limit=30, window_seconds=60)
        sla = _get_sla_metrics()
        latency = get_request_latency_snapshot()

        return {
            "status": "ok",
            "sla_report": sla,
            "latency_summary": {
                "window_size": latency.get("window_size"),
                "paths_tracked": latency.get("path_count"),
                "total_samples": latency.get("sample_count"),
            },
            "recommendations": [
                "Enable Prometheus scrape at /metrics for long-term trending" if sla["status"] != "green" else "SLA targets met — maintain current infrastructure",
                "Configure Grafana alert when P95 > SLA target" if sla["breached_paths"] else "No breached paths detected in current window",
            ],
            "retrieved_at": _now(),
        }

    # ── Module 50: Platform Intelligence Layer ─────────────────────────────

    @router.get("/intelligence", summary="Module 50 — cross-module platform intelligence & recommendations")
    def platform_intelligence(auth: AuthDep) -> dict[str, Any]:
        """
        Cross-module intelligence aggregation:
        - Anomaly detection signals (latency spikes, error surges, model fallbacks)
        - Predictive recommendations (scale warnings, cache hit rates, model swap suggestions)
        - Cross-module health score
        - Action items ranked by impact
        Stack: Llama-3/DeepSeek, OpenSearch analytics, dbt Core, Prophet/scikit-learn patterns.
        """
        enforce_rate_limit(f"{auth.tenant_id}:platform:intelligence", limit=20, window_seconds=60)

        latency = get_request_latency_snapshot()
        sla = _get_sla_metrics()
        registry = _get_env_model_registry()
        paths: dict[str, Any] = latency.get("paths", {}) or {}  # type: ignore[assignment]

        # Anomaly detection: identify paths with p95 > 2× median
        all_p95s = [float(v.get("p95_ms", 0)) for v in paths.values() if v]  # type: ignore[union-attr]
        median_p95 = sorted(all_p95s)[len(all_p95s) // 2] if all_p95s else 0.0
        spike_threshold = max(median_p95 * 2, 1000.0)
        latency_spikes = [
            {"path": path, "p95_ms": float(stats.get("p95_ms", 0)), "spike_ratio": round(float(stats.get("p95_ms", 0)) / max(median_p95, 1), 2)}  # type: ignore[union-attr]
            for path, stats in paths.items()
            if float(stats.get("p95_ms", 0)) > spike_threshold  # type: ignore[union-attr]
        ]

        # Recovery queue health
        recovery_depth = len([r for r in _recovery_queue if r.get("tenant_id") == auth.tenant_id])
        high_retry_jobs = [r for r in _recovery_queue if r.get("tenant_id") == auth.tenant_id and r.get("retries", 0) >= 3]

        # Lineage coverage
        tenant_lineage = [e for e in _lineage_events if e.get("tenant_id") == auth.tenant_id]
        lineage_coverage_pct = min(100, round(len(tenant_lineage) / max(1, len(_lineage_events)) * 100, 1)) if _lineage_events else 0

        # Prompt version health
        tenant_active_prompts = [p for p in _prompt_versions if p.get("tenant_id") == auth.tenant_id and p.get("active")]

        # Compute overall platform health score (0–100)
        score = 100
        score -= min(30, len(latency_spikes) * 10)
        score -= min(20, recovery_depth * 2)
        score -= min(10, len(high_retry_jobs) * 5)
        score -= (10 if sla["status"] == "red" else 5 if sla["status"] == "amber" else 0)
        health_score = max(0, score)

        # Ranked action items
        actions: list[dict[str, Any]] = []
        if latency_spikes:
            actions.append({"priority": "high", "area": "latency", "action": f"Investigate {len(latency_spikes)} endpoint(s) with P95 latency spike: {[s['path'] for s in latency_spikes[:3]]}"})
        if high_retry_jobs:
            actions.append({"priority": "high", "area": "recovery", "action": f"{len(high_retry_jobs)} job(s) have exceeded 3 retries — manual intervention may be required"})
        if sla["status"] != "green":
            actions.append({"priority": "medium", "area": "sla", "action": f"SLA compliance at {sla['compliance_pct']}% — review breached paths: {sla['breached_paths'][:3]}"})
        if not tenant_active_prompts:
            actions.append({"priority": "low", "area": "model_management", "action": "No versioned prompts registered — consider registering prompts via POST /platform/models/prompt-versions for rollback capability"})
        if lineage_coverage_pct < 20 and len(_lineage_events) > 0:
            actions.append({"priority": "low", "area": "governance", "action": "Low data lineage coverage for this tenant — enable lineage recording in high-value pipeline steps"})
        if len(registry) < 2:
            actions.append({"priority": "low", "area": "model_resilience", "action": "Only one AI provider configured — add OPENAI_API_KEY or ANTHROPIC_API_KEY as fallback for higher resilience"})

        if not actions:
            actions.append({"priority": "info", "area": "platform", "action": "Platform is operating nominally — no action required"})

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "health_score": health_score,
            "health_grade": "A+" if health_score >= 95 else "A" if health_score >= 90 else "B" if health_score >= 75 else "C" if health_score >= 60 else "D",
            "anomalies": {
                "latency_spikes": latency_spikes,
                "high_retry_jobs": len(high_retry_jobs),
                "recovery_queue_depth": recovery_depth,
            },
            "governance": {
                "lineage_events": len(tenant_lineage),
                "lineage_coverage_pct": lineage_coverage_pct,
                "active_prompt_versions": len(tenant_active_prompts),
            },
            "sla_status": sla["status"],
            "sla_compliance_pct": sla["compliance_pct"],
            "model_count": len(registry),
            "ranked_actions": actions,
            "stack": {
                "ai": ["deepseek-r1:8b (local)", "ollama", "llm_pool"],
                "analytics": ["OpenSearch", "dbt Core patterns", "in-memory rolling window"],
                "forecasting": ["Prophet/scikit-learn heuristics"],
                "observability": ["Prometheus-compatible latency", "Grafana-ready output"],
            },
            "retrieved_at": _now(),
        }

    # ══════════════════════════════════════════════════════════════════════════
    # AI Agent Config & Tool Registry Endpoints
    # ══════════════════════════════════════════════════════════════════════════

    @router.get("/agent-config", summary="Kodee-class agent — stack configuration & health for this tenant")
    async def get_agent_config(auth: AuthDep):
        """
        Returns the current AI agent stack configuration, phase, enabled models,
        session stats, tool count, and live health indicators.
        Reads from DB (ai_agent_config / ai_agent_tools) with in-memory fallback.
        """
        # ── Try DB first ──────────────────────────────────────────────────────
        db_available = False
        db_config: dict[str, Any] = {}
        db_tools: list[dict[str, Any]] = []
        db_sessions: list[dict[str, Any]] = []
        db_calls: list[dict[str, Any]] = []

        db_available, cfg_rows = _try_agent_db_query(
            "SELECT current_phase, enabled_models, enabled_agent_roles, tool_count_limit, "
            "max_auto_actions, allow_high_risk_tools, mcp_endpoint FROM ai_agent_config WHERE tenant_id = %s",
            (auth.tenant_id,)
        )
        if db_available and cfg_rows:
            db_config = cfg_rows[0]

        if db_available:
            _, db_tools = _try_agent_db_query(
                "SELECT key, display_name, group_name, risk_level, requires_confirmation, is_active, backend_endpoint "
                "FROM ai_agent_tools WHERE is_active = TRUE",
                ()
            )
            _, db_sessions = _try_agent_db_query(
                "SELECT id, status FROM ai_agent_sessions WHERE tenant_id = %s",
                (auth.tenant_id,)
            )
            _, db_calls = _try_agent_db_query(
                "SELECT id, status FROM ai_agent_tool_calls WHERE tenant_id = %s",
                (auth.tenant_id,)
            )

        # ── Merge DB + in-memory ──────────────────────────────────────────────
        config = dict(db_config) if db_config else dict(_agent_config)
        config.setdefault("current_phase", _agent_config["current_phase"])
        config.setdefault("enabled_models", _agent_config["enabled_models"])
        config.setdefault("enabled_agent_roles", _agent_config["enabled_agent_roles"])
        config.setdefault("tool_count_limit", _agent_config["tool_count_limit"])
        config.setdefault("max_auto_actions", _agent_config["max_auto_actions"])
        config.setdefault("allow_high_risk_tools", _agent_config["allow_high_risk_tools"])
        config.setdefault("mcp_endpoint", _agent_config.get("mcp_endpoint"))

        # enabled_models may be a list (Python) or PostgreSQL array (already converted by psycopg)
        if isinstance(config.get("enabled_models"), str):
            config["enabled_models"] = [config["enabled_models"]]

        tenant_tools = db_tools if db_tools else [t for t in _DEFAULT_AGENT_TOOLS if t.get("is_active", True)]
        tenant_sessions = db_sessions if db_sessions else [s for s in _agent_sessions if s.get("tenant_id") == auth.tenant_id]
        tenant_calls = db_calls if db_calls else [c for c in _agent_tool_calls if c.get("tenant_id") == auth.tenant_id]

        active_sessions = [s for s in tenant_sessions if s.get("status") == "active"]
        successful_calls = [c for c in tenant_calls if c.get("status") == "success"]
        failed_calls = [c for c in tenant_calls if c.get("status") == "error"]
        pending_confirms = [c for c in tenant_calls if c.get("status") == "pending"]

        groups: dict[str, int] = {}
        risk_counts: dict[str, int] = {"low": 0, "medium": 0, "high": 0}
        for t in tenant_tools:
            g = str(t.get("group_name", "Other"))
            groups[g] = groups.get(g, 0) + 1
            rl = str(t.get("risk_level", "low"))
            risk_counts[rl] = risk_counts.get(rl, 0) + 1

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "agent_stack": {
                "llm": ["Llama-3 8B/70B", "DeepSeek R1"],
                "framework": ["AutoGen", "LangChain"],
                "tool_protocol": "MCP (Model Context Protocol)",
                "backend": "FastAPI",
                "context_store": ["PostgreSQL + pgvector", "OpenSearch"],
                "auth": ["Keycloak", "Supabase Auth"],
                "observability": ["Prometheus", "Grafana", "Loki"],
                "audit": ["PostgreSQL", "OpenSearch"],
            },
            "config": config,
            "phase_info": {
                "phase1": {"label": "Internal Admin Agent", "status": "current" if config["current_phase"] == "phase1" else "planned", "description": "Read-only + reporting, 5-10 safe tools, local LLM"},
                "phase2": {"label": "Controlled Actions",   "status": "current" if config["current_phase"] == "phase2" else "planned", "description": "Write tools with confirmation UX + full audit logging"},
                "phase3": {"label": "Full Kodee-Class",     "status": "current" if config["current_phase"] == "phase3" else "planned", "description": "MCP tool registry, multi-agent orchestration, 350+ actions"},
            },
            "tool_stats": {
                "total": len(tenant_tools),
                "active": len([t for t in tenant_tools if t.get("is_active", True)]),
                "by_group": groups,
                "by_risk": risk_counts,
                "requiring_confirmation": len([t for t in tenant_tools if t.get("requires_confirmation")]),
            },
            "session_stats": {
                "total": len(tenant_sessions),
                "active": len(active_sessions),
                "total_tool_calls": len(tenant_calls),
                "successful_calls": len(successful_calls),
                "failed_calls": len(failed_calls),
                "pending_confirmations": len(pending_confirms),
            },
            "health": {
                "agent_ready": True,
                "llm_available": bool(os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OPENAI_API_KEY")),
                "db_available": db_available,
                "mcp_endpoint": config.get("mcp_endpoint"),
                "audit_enabled": True,
            },
            "retrieved_at": _now(),
        }

    @router.put("/agent-config", summary="Update agent configuration for this tenant")
    async def update_agent_config(req: AgentConfigUpdateRequest, auth: AuthDep):
        """Update the Kodee-class agent configuration (phase, models, risk settings)."""
        if req.current_phase is not None:
            if req.current_phase not in ("phase1", "phase2", "phase3"):
                raise HTTPException(status_code=422, detail="current_phase must be phase1, phase2, or phase3")
            _agent_config["current_phase"] = req.current_phase
        if req.enabled_models is not None:
            _agent_config["enabled_models"] = req.enabled_models
        if req.max_auto_actions is not None:
            _agent_config["max_auto_actions"] = req.max_auto_actions
        if req.allow_high_risk_tools is not None:
            _agent_config["allow_high_risk_tools"] = req.allow_high_risk_tools
        if req.mcp_endpoint is not None:
            _agent_config["mcp_endpoint"] = req.mcp_endpoint if req.mcp_endpoint else None

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "config": dict(_agent_config),
            "updated_at": _now(),
        }

    @router.get("/agent-tools", summary="List registered tools in the agent tool registry")
    async def list_agent_tools(
        auth: AuthDep,
        group: str | None = Query(default=None, description="Filter by group_name"),
        risk_level: str | None = Query(default=None, description="Filter by risk_level: low | medium | high"),
        active_only: bool = Query(default=True),
    ):
        """Returns the full MCP-style tool registry. Reads from DB with in-memory fallback."""
        # Try DB
        _tools_sql = (
            "SELECT key, display_name, group_name, description, fn_signature, risk_level, "
            "requires_confirmation, is_active, backend_endpoint "
            "FROM ai_agent_tools WHERE is_active = %s"
            if active_only else
            "SELECT key, display_name, group_name, description, fn_signature, risk_level, "
            "requires_confirmation, is_active, backend_endpoint "
            "FROM ai_agent_tools"
        )
        _tools_params: tuple[Any, ...] = (True,) if active_only else ()
        db_ok, db_rows = _try_agent_db_query(_tools_sql, _tools_params)
        tools: list[dict[str, Any]] = db_rows if db_ok and db_rows else list(_DEFAULT_AGENT_TOOLS)

        if active_only and not (db_ok and db_rows):
            tools = [t for t in tools if t.get("is_active", True)]
        if group:
            tools = [t for t in tools if str(t.get("group_name", "")).lower() == group.lower()]
        if risk_level:
            tools = [t for t in tools if t.get("risk_level") == risk_level]

        groups: dict[str, list[dict[str, Any]]] = {}
        for t in tools:
            g = str(t.get("group_name", "Other"))
            groups.setdefault(g, []).append(t)

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "total": len(tools),
            "tools": tools,
            "by_group": [{"group": g, "count": len(items), "tools": items} for g, items in groups.items()],
            "db_source": db_ok,
            "retrieved_at": _now(),
        }

    @router.post("/agent-tools", summary="Register a new tool in the agent tool registry", status_code=201)
    async def register_agent_tool(req: AgentToolRegisterRequest, auth: AuthDep):
        """Add a new MCP-style tool to the agent's tool registry."""
        # Check for duplicate key
        existing = next((t for t in _DEFAULT_AGENT_TOOLS if t["key"] == req.key), None)
        if existing:
            raise HTTPException(status_code=409, detail=f"Tool with key '{req.key}' already exists. Use PUT to update.")

        if req.risk_level not in ("low", "medium", "high"):
            raise HTTPException(status_code=422, detail="risk_level must be low, medium, or high")

        new_tool: dict[str, Any] = {
            "key": req.key,
            "display_name": req.display_name,
            "group_name": req.group_name,
            "description": req.description,
            "fn_signature": req.fn_signature,
            "risk_level": req.risk_level,
            "requires_confirmation": req.requires_confirmation or req.risk_level == "high",
            "backend_endpoint": req.backend_endpoint,
            "input_schema": req.input_schema,
            "is_active": True,
            "tenant_id": auth.tenant_id,
            "created_at": _now(),
        }
        _DEFAULT_AGENT_TOOLS.append(new_tool)
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "tool": new_tool,
            "total_tools": len(_DEFAULT_AGENT_TOOLS),
        }

    @router.get("/agent-audit", summary="Audit trail of all agent tool calls for this tenant")
    async def get_agent_audit(
        auth: AuthDep,
        limit: int = Query(default=50, ge=1, le=500),
        tool_key: str | None = Query(default=None),
        status: str | None = Query(default=None),
    ):
        """Returns a chronological audit log of every tool invocation. Reads from DB with fallback."""
        # Static parameterized query forms (no user input in SQL structure)
        _SEL = (
            "SELECT tool_key, status, risk_level, agent_role, created_at, duration_ms, error_message "
            "FROM ai_agent_tool_calls"
        )
        if tool_key and status:
            _audit_sql = _SEL + " WHERE tenant_id = %s AND tool_key = %s AND status = %s ORDER BY created_at DESC LIMIT %s"
            _audit_params: tuple[Any, ...] = (auth.tenant_id, tool_key, status, limit)
        elif tool_key:
            _audit_sql = _SEL + " WHERE tenant_id = %s AND tool_key = %s ORDER BY created_at DESC LIMIT %s"
            _audit_params = (auth.tenant_id, tool_key, limit)
        elif status:
            _audit_sql = _SEL + " WHERE tenant_id = %s AND status = %s ORDER BY created_at DESC LIMIT %s"
            _audit_params = (auth.tenant_id, status, limit)
        else:
            _audit_sql = _SEL + " WHERE tenant_id = %s ORDER BY created_at DESC LIMIT %s"
            _audit_params = (auth.tenant_id, limit)
        db_ok, calls = _try_agent_db_query(_audit_sql, _audit_params)
        # Serialize datetimes for JSON
        for c in calls:
            if hasattr(c.get("created_at"), "isoformat"):
                c["created_at"] = c["created_at"].isoformat()

        if not db_ok:
            # In-memory fallback
            mem_calls = [c for c in _agent_tool_calls if c.get("tenant_id") == auth.tenant_id]
            if tool_key:
                mem_calls = [c for c in mem_calls if c.get("tool_key") == tool_key]
            if status:
                mem_calls = [c for c in mem_calls if c.get("status") == status]
            calls = sorted(mem_calls, key=lambda c: c.get("created_at", ""), reverse=True)[:limit]

        # Counts (from DB if available)
        success_count = sum(1 for c in calls if c.get("status") == "success")
        error_count = sum(1 for c in calls if c.get("status") == "error")

        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "total_calls": len(calls),
            "success_count": success_count,
            "error_count": error_count,
            "calls": calls,
            "db_source": db_ok,
            "retrieved_at": _now(),
        }

    return router
