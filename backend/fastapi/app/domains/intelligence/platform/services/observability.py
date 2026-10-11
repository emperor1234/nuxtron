"""Platform database metrics, lineage, uptime, and model diagnostics."""

from __future__ import annotations
from .....production_middleware import get_request_latency_snapshot
from ..constants import _PLATFORM_START_TS
from ..constants import _lineage_events
from datetime import UTC
from datetime import datetime
from typing import Any
import hashlib
import os
import psycopg
import time


def _agent_db_dsn() -> str:
    return f"host={os.getenv('POSTGRES_HOST', 'localhost')} port={os.getenv('POSTGRES_PORT', '5432')} dbname={os.getenv('POSTGRES_DB', 'nuxtron')} user={os.getenv('POSTGRES_USER', 'nuxtron')} password={os.getenv('POSTGRES_PASSWORD', '')} connect_timeout=2"


def _try_agent_db_query(sql: str, params: tuple[Any, ...] = ()) -> tuple[bool, list[dict[str, Any]]]:
    """Execute a SELECT against the agent tables; returns (db_available, rows)."""
    try:
        with psycopg.connect(_agent_db_dsn()) as conn:
            conn.execute("SET statement_timeout = '3000ms'")
            with conn.cursor() as cur:
                cur.execute(sql, params)
                cols = [d.name for d in cur.description or []]
                rows = [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]
                return (True, rows)
    except Exception:
        return (False, [])


def _try_agent_db_scalar(sql: str, params: tuple[Any, ...] = ()) -> tuple[bool, Any]:
    ok, rows = _try_agent_db_query(sql, params)
    if ok and rows:
        return (True, next(iter(rows[0].values()), None))
    return (ok, None)


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
    score = 100
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

    future_years = re.findall("\\b(20[3-9]\\d|2[1-9]\\d{2})\\b", content)
    if future_years:
        flags.append(f"references future/implausible years: {future_years[:3]}")
        score -= 10
    words = text.split()
    if words:
        unique_ratio = len(set(words)) / max(len(words), 1)
        if unique_ratio < 0.35 and len(words) > 50:
            flags.append(f"low lexical diversity ({unique_ratio:.2f}) — possible repetition loop")
            score -= 15
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
        }
    ]
    if openai_key_set:
        registry.append(
            {
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
            }
        )
    if anthropic_key_set:
        registry.append(
            {
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
            }
        )
    return registry


def _record_lineage(
    source: str, destination: str, transformation: str, tenant_id: str, meta: dict[str, Any] | None = None
) -> None:
    """Module 34 — record a data lineage event (internal helper for other modules to call)."""
    _lineage_events.append(
        {
            "id": _sha256(f"{source}{destination}{_now()}"),
            "source": source,
            "destination": destination,
            "transformation": transformation,
            "tenant_id": tenant_id,
            "timestamp": _now(),
            "meta": meta or {},
        }
    )
    if len(_lineage_events) > 10000:
        del _lineage_events[: len(_lineage_events) - 10000]


def _get_sla_metrics() -> dict[str, Any]:
    """Module 49 — calculate SLA stats from latency snapshot."""
    snapshot = get_request_latency_snapshot()
    paths = snapshot.get("paths", {})
    sla_target_ms = float(os.getenv("SLA_TARGET_P95_MS", "2000"))
    breached: list[str] = []
    compliant: list[str] = []
    for path, stats in paths.items():
        p95 = float(stats.get("p95_ms", 0))
        if p95 > sla_target_ms:
            breached.append(path)
        else:
            compliant.append(path)
    uptime = _uptime_seconds()
    total = len(breached) + len(compliant)
    compliance_pct = round(len(compliant) / max(total, 1) * 100, 2)
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
