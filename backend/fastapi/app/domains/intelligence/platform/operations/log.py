"""Intelligence/Platform use cases: log."""

from __future__ import annotations
from .....production_middleware import get_request_latency_snapshot
from ..constants import AuthDep
from ..constants import _lineage_events
from ..constants import _prompt_versions
from ..constants import _recovery_queue
from ..constants import _retry_counts
from ..runtime import ContextRuntime
from ..schemas import AIValidateRequest
from ..schemas import PromptVersionCreateRequest
from ..schemas import RetryRequest
from ..services.observability import _detect_hallucination_indicators
from ..services.observability import _get_env_model_registry
from ..services.observability import _get_sla_metrics
from ..services.observability import _now
from ..services.observability import _record_lineage
from ..services.observability import _sha256
from ..services.observability import _uptime_seconds
from ..services.observability import _validate_json_keys
from fastapi import HTTPException
from fastapi import Query
from typing import Any
import os


def helper_log(runtime: ContextRuntime, tenant_id: str, action: str, data: dict[str, Any]) -> None:
    runtime.audit_log_memory.append(
        {"timestamp": _now(), "tenant_id": tenant_id, "source": "platform-intelligence", "action": action, **data}
    )


async def execute_ai_safety_validate(runtime: ContextRuntime, req: AIValidateRequest, auth: AuthDep) -> dict[str, Any]:
    """
    Validate any AI-generated content for:
    - Hallucination risk (heuristic scoring)
    - Schema compliance (required JSON keys)
    - Content quality signals (length, diversity, confidence)
    - Policy flags (over-confident language, impossible claims)

    Stack: Guardrails-AI patterns, JSON schema validation, OpenSearch-ready audit trail.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:ai-safety", limit=60, window_seconds=60)
    content_hash = _sha256(req.content)
    hallucination = _detect_hallucination_indicators(req.content)
    schema_check: dict[str, Any] = {"applicable": False}
    if req.schema_type == "json" or req.expected_keys:
        schema_check = _validate_json_keys(req.content, req.expected_keys)
        schema_check["applicable"] = True
    if req.schema_type == "structured_seo" and (not req.expected_keys):
        seo_keys = ["score", "recommendations", "quick_wins"]
        schema_check = _validate_json_keys(req.content, seo_keys)
        schema_check["applicable"] = True
    overall_safe = hallucination["risk_level"] != "high" and (
        not schema_check["applicable"] or schema_check.get("valid", True)
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
    helper_log(
        runtime,
        auth.tenant_id,
        "ai_safety_validate",
        {"module": req.module, "verdict": result["verdict"], "content_hash": content_hash},
    )
    return result


def execute_ai_safety_audit_log(
    runtime: ContextRuntime, auth: AuthDep, limit: int = Query(default=50, ge=1, le=200)
) -> dict[str, Any]:
    """Return the last N AI safety validation events for the calling tenant."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:ai-safety-log", limit=30, window_seconds=60)
    events = [
        e
        for e in runtime.audit_log_memory
        if e.get("source") == "platform-intelligence"
        and e.get("action") == "ai_safety_validate"
        and (e.get("tenant_id") == auth.tenant_id)
    ]
    return {"tenant_id": auth.tenant_id, "total": len(events), "events": events[-limit:]}


def execute_list_models(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """
    Returns the current AI model registry with provider configs, quality scores,
    cost estimates, and enabled status.  Stack: MLflow-style versioning, MinIO registry.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:models", limit=60, window_seconds=60)
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


def execute_create_prompt_version(
    runtime: ContextRuntime, req: PromptVersionCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    """
    Register a versioned prompt for a module. Supports rollback, A/B testing,
    and audit trails. Equivalent to MLflow prompt versioning.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:prompt-versions", limit=30, window_seconds=60)
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
    for pv in _prompt_versions:
        if pv["module"] == req.module and pv["tenant_id"] == auth.tenant_id and (pv["model"] == req.model):
            pv["active"] = False
    _prompt_versions.append(record)
    _record_lineage(
        source=f"prompt_author:{req.author}",
        destination=f"prompt_registry:{req.module}",
        transformation="prompt_version_create",
        tenant_id=auth.tenant_id,
        meta={"version_id": version_id},
    )
    helper_log(runtime, auth.tenant_id, "prompt_version_create", {"version_id": version_id, "module": req.module})
    return {"status": "registered", **record}


def execute_list_prompt_versions(
    runtime: ContextRuntime,
    auth: AuthDep,
    module: str | None = Query(default=None),
    active_only: bool = Query(default=False),
) -> dict[str, Any]:
    """List all prompt versions for this tenant, optionally filtered by module or active status."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:prompt-versions", limit=60, window_seconds=60)
    results = [pv for pv in _prompt_versions if pv["tenant_id"] == auth.tenant_id]
    if module:
        results = [pv for pv in results if pv["module"] == module]
    if active_only:
        results = [pv for pv in results if pv.get("active")]
    return {"tenant_id": auth.tenant_id, "total": len(results), "prompt_versions": results}


def execute_data_lineage(
    runtime: ContextRuntime,
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
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:lineage", limit=30, window_seconds=60)
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


def execute_record_lineage_event(
    runtime: ContextRuntime,
    auth: AuthDep,
    source: str = Query(..., min_length=1, max_length=200),
    destination: str = Query(..., min_length=1, max_length=200),
    transformation: str = Query(default="manual", max_length=200),
) -> dict[str, Any]:
    """Manually record a data lineage hop (e.g. CSV export → reporting dashboard)."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:lineage-write", limit=20, window_seconds=60)
    _record_lineage(source, destination, transformation, auth.tenant_id)
    return {
        "status": "recorded",
        "source": source,
        "destination": destination,
        "transformation": transformation,
        "recorded_at": _now(),
    }


def execute_platform_metrics(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """
    Returns the full observability snapshot:
    - Request latency (p50/p95/max per path, rolling 240-request window)
    - SLA compliance status
    - Rate limiter stats
    - Model registry summary
    Stack: Prometheus patterns, Grafana-compatible output, Loki-ready event counts.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:metrics", limit=30, window_seconds=60)
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
            "local_count": sum((1 for m in registry if m.get("local"))),
        },
        "lineage": {
            "total_events": len(_lineage_events),
            "tenant_events": len([e for e in _lineage_events if e.get("tenant_id") == auth.tenant_id]),
        },
        "prompt_versions": {
            "total": len(_prompt_versions),
            "tenant_active": len(
                [p for p in _prompt_versions if p.get("tenant_id") == auth.tenant_id and p.get("active")]
            ),
        },
        "recovery_queue": {
            "depth": len(_recovery_queue),
            "tenant_items": len([r for r in _recovery_queue if r.get("tenant_id") == auth.tenant_id]),
        },
    }


def execute_recovery_status(
    runtime: ContextRuntime, auth: AuthDep, limit: int = Query(default=50, ge=1, le=200)
) -> dict[str, Any]:
    """
    Returns all items currently in the recovery queue for this tenant.
    Includes retry counts, last error, and next eligible retry time.
    Stack: Sentry-style error capture, Celery retry pattern, Temporal compensations.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:recovery", limit=30, window_seconds=60)
    tenant_items = [r for r in _recovery_queue if r.get("tenant_id") == auth.tenant_id]
    return {
        "tenant_id": auth.tenant_id,
        "total_in_queue": len(tenant_items),
        "max_retries_reached": sum((1 for r in tenant_items if r.get("retries", 0) >= 3)),
        "items": tenant_items[-limit:],
        "retrieved_at": _now(),
    }


def execute_trigger_retry(runtime: ContextRuntime, req: RetryRequest, auth: AuthDep) -> dict[str, Any]:
    """
    Manually enqueue a retry for a job that failed. Records the retry in the
    recovery queue and increments retry count. Provides full audit trail.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:recovery-retry", limit=10, window_seconds=60)
    for item in _recovery_queue:
        if item["job_id"] == req.job_id and item["tenant_id"] == auth.tenant_id:
            item["retries"] = _retry_counts[req.job_id]
            item["last_attempt"] = _now()
            item["reason"] = req.reason
            _retry_counts[req.job_id] += 1
            helper_log(
                runtime,
                auth.tenant_id,
                "recovery_retry",
                {"job_id": req.job_id, "retries": item["retries"], "reason": req.reason},
            )
            return {"status": "retry_queued", **item}
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
    if len(_recovery_queue) > 5000:
        del _recovery_queue[: len(_recovery_queue) - 5000]
    helper_log(
        runtime,
        auth.tenant_id,
        "recovery_retry",
        {"job_id": req.job_id, "retries": _retry_counts[req.job_id], "reason": req.reason},
    )
    return {"status": "retry_queued", **record}


def execute_clear_recovery_item(runtime: ContextRuntime, job_id: str, auth: AuthDep) -> dict[str, Any]:
    """Remove a resolved job from the recovery queue."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:recovery-clear", limit=20, window_seconds=60)
    before = len(_recovery_queue)
    _recovery_queue[:] = [
        r for r in _recovery_queue if not (r["job_id"] == job_id and r["tenant_id"] == auth.tenant_id)
    ]
    removed = before - len(_recovery_queue)
    if removed == 0:
        raise HTTPException(status_code=404, detail="Job not found in recovery queue")
    helper_log(runtime, auth.tenant_id, "recovery_clear", {"job_id": job_id})
    return {"status": "removed", "job_id": job_id}


def execute_list_jobs(
    runtime: ContextRuntime,
    auth: AuthDep,
    status: str | None = Query(default=None, description="Filter: queued | running | completed | failed"),
    module: str | None = Query(default=None, description="Filter by module name"),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """
    Returns all async jobs from the SEO platform job registry for this tenant.
    Supports filtering by status and module. Equivalent to a Temporal workflow list.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:jobs", limit=30, window_seconds=60)
    jobs_store: dict[str, Any] = {}
    if runtime.seo_jobs_fn is not None:
        try:
            jobs_store = runtime.seo_jobs_fn() or {}
        except Exception:
            jobs_store = {}
    tenant_jobs = [job for job in jobs_store.values() if job.get("tenant_id") == auth.tenant_id]
    if status:
        tenant_jobs = [j for j in tenant_jobs if j.get("status") == status]
    if module:
        tenant_jobs = [j for j in tenant_jobs if j.get("module") == module]
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
