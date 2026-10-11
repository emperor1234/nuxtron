"""Intelligence/Platform use cases: get job."""

from __future__ import annotations
from .....production_middleware import get_request_latency_snapshot
from ..constants import AuthDep
from ..constants import _DEFAULT_AGENT_TOOLS
from ..constants import _agent_config
from ..constants import _agent_sessions
from ..constants import _agent_tool_calls
from ..constants import _lineage_events
from ..constants import _prompt_versions
from ..constants import _recovery_queue
from ..runtime import ContextRuntime
from ..schemas import AgentConfigUpdateRequest
from ..schemas import AgentToolRegisterRequest
from ..services.observability import _get_env_model_registry
from ..services.observability import _get_sla_metrics
from ..services.observability import _now
from ..services.observability import _try_agent_db_query
from fastapi import HTTPException
from typing import Any
import os


def execute_get_job(runtime: ContextRuntime, job_id: str, auth: AuthDep) -> dict[str, Any]:
    """Poll a specific async job. Delegates to SEO jobs store."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:jobs", limit=60, window_seconds=60)
    jobs_store: dict[str, Any] = {}
    if runtime.seo_jobs_fn is not None:
        try:
            jobs_store = runtime.seo_jobs_fn() or {}
        except Exception:
            jobs_store = {}
    job = jobs_store.get(job_id)
    if job is None or job.get("tenant_id") != auth.tenant_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def execute_policy_status(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """
    Returns a non-sensitive snapshot of secrets & policy enforcement status:
    - Which external secrets backends are configured (Vault, env)
    - RBAC/ABAC enforcement mode
    - CORS and allowed-host policy
    - MFA / SSO availability
    Stack: HashiCorp Vault OSS, OPA, Keycloak, Doppler OSS patterns.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:policy", limit=30, window_seconds=60)
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


def execute_sla_report(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """
    Returns SLA compliance report:
    - P95 latency vs SLA target per endpoint
    - Overall compliance percentage
    - Uptime since last restart
    - Breach summary
    Stack: Prometheus uptime checks, Grafana alert thresholds, Coolify health checks.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:sla", limit=30, window_seconds=60)
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
            "Enable Prometheus scrape at /metrics for long-term trending"
            if sla["status"] != "green"
            else "SLA targets met — maintain current infrastructure",
            "Configure Grafana alert when P95 > SLA target"
            if sla["breached_paths"]
            else "No breached paths detected in current window",
        ],
        "retrieved_at": _now(),
    }


def execute_platform_intelligence(runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """
    Cross-module intelligence aggregation:
    - Anomaly detection signals (latency spikes, error surges, model fallbacks)
    - Predictive recommendations (scale warnings, cache hit rates, model swap suggestions)
    - Cross-module health score
    - Action items ranked by impact
    Stack: Llama-3/DeepSeek, OpenSearch analytics, dbt Core, Prophet/scikit-learn patterns.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:platform:intelligence", limit=20, window_seconds=60)
    latency = get_request_latency_snapshot()
    sla = _get_sla_metrics()
    registry = _get_env_model_registry()
    paths: dict[str, Any] = latency.get("paths", {}) or {}
    all_p95s = [float(v.get("p95_ms", 0)) for v in paths.values() if v]
    median_p95 = sorted(all_p95s)[len(all_p95s) // 2] if all_p95s else 0.0
    spike_threshold = max(median_p95 * 2, 1000.0)
    latency_spikes = [
        {
            "path": path,
            "p95_ms": float(stats.get("p95_ms", 0)),
            "spike_ratio": round(float(stats.get("p95_ms", 0)) / max(median_p95, 1), 2),
        }
        for path, stats in paths.items()
        if float(stats.get("p95_ms", 0)) > spike_threshold
    ]
    recovery_depth = len([r for r in _recovery_queue if r.get("tenant_id") == auth.tenant_id])
    high_retry_jobs = [r for r in _recovery_queue if r.get("tenant_id") == auth.tenant_id and r.get("retries", 0) >= 3]
    tenant_lineage = [e for e in _lineage_events if e.get("tenant_id") == auth.tenant_id]
    lineage_coverage_pct = (
        min(100, round(len(tenant_lineage) / max(1, len(_lineage_events)) * 100, 1)) if _lineage_events else 0
    )
    tenant_active_prompts = [p for p in _prompt_versions if p.get("tenant_id") == auth.tenant_id and p.get("active")]
    score = 100
    score -= min(30, len(latency_spikes) * 10)
    score -= min(20, recovery_depth * 2)
    score -= min(10, len(high_retry_jobs) * 5)
    score -= 10 if sla["status"] == "red" else 5 if sla["status"] == "amber" else 0
    health_score = max(0, score)
    actions: list[dict[str, Any]] = []
    if latency_spikes:
        actions.append(
            {
                "priority": "high",
                "area": "latency",
                "action": f"Investigate {len(latency_spikes)} endpoint(s) with P95 latency spike: {[s['path'] for s in latency_spikes[:3]]}",
            }
        )
    if high_retry_jobs:
        actions.append(
            {
                "priority": "high",
                "area": "recovery",
                "action": f"{len(high_retry_jobs)} job(s) have exceeded 3 retries — manual intervention may be required",
            }
        )
    if sla["status"] != "green":
        actions.append(
            {
                "priority": "medium",
                "area": "sla",
                "action": f"SLA compliance at {sla['compliance_pct']}% — review breached paths: {sla['breached_paths'][:3]}",
            }
        )
    if not tenant_active_prompts:
        actions.append(
            {
                "priority": "low",
                "area": "model_management",
                "action": "No versioned prompts registered — consider registering prompts via POST /platform/models/prompt-versions for rollback capability",
            }
        )
    if lineage_coverage_pct < 20 and len(_lineage_events) > 0:
        actions.append(
            {
                "priority": "low",
                "area": "governance",
                "action": "Low data lineage coverage for this tenant — enable lineage recording in high-value pipeline steps",
            }
        )
    if len(registry) < 2:
        actions.append(
            {
                "priority": "low",
                "area": "model_resilience",
                "action": "Only one AI provider configured — add OPENAI_API_KEY or ANTHROPIC_API_KEY as fallback for higher resilience",
            }
        )
    if not actions:
        actions.append(
            {"priority": "info", "area": "platform", "action": "Platform is operating nominally — no action required"}
        )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "health_score": health_score,
        "health_grade": "A+"
        if health_score >= 95
        else "A"
        if health_score >= 90
        else "B"
        if health_score >= 75
        else "C"
        if health_score >= 60
        else "D",
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


async def execute_get_agent_config(auth: AuthDep):
    """
    Returns the current AI agent stack configuration, phase, enabled models,
    session stats, tool count, and live health indicators.
    Reads from DB (ai_agent_config / ai_agent_tools) with in-memory fallback.
    """
    db_available = False
    db_config: dict[str, Any] = {}
    db_tools: list[dict[str, Any]] = []
    db_sessions: list[dict[str, Any]] = []
    db_calls: list[dict[str, Any]] = []
    db_available, cfg_rows = _try_agent_db_query(
        "SELECT current_phase, enabled_models, enabled_agent_roles, tool_count_limit, max_auto_actions, allow_high_risk_tools, mcp_endpoint FROM ai_agent_config WHERE tenant_id = %s",
        (auth.tenant_id,),
    )
    if db_available and cfg_rows:
        db_config = cfg_rows[0]
    if db_available:
        _, db_tools = _try_agent_db_query(
            "SELECT key, display_name, group_name, risk_level, requires_confirmation, is_active, backend_endpoint FROM ai_agent_tools WHERE is_active = TRUE",
            (),
        )
        _, db_sessions = _try_agent_db_query(
            "SELECT id, status FROM ai_agent_sessions WHERE tenant_id = %s", (auth.tenant_id,)
        )
        _, db_calls = _try_agent_db_query(
            "SELECT id, status FROM ai_agent_tool_calls WHERE tenant_id = %s", (auth.tenant_id,)
        )
    config = dict(db_config) if db_config else dict(_agent_config)
    config.setdefault("current_phase", _agent_config["current_phase"])
    config.setdefault("enabled_models", _agent_config["enabled_models"])
    config.setdefault("enabled_agent_roles", _agent_config["enabled_agent_roles"])
    config.setdefault("tool_count_limit", _agent_config["tool_count_limit"])
    config.setdefault("max_auto_actions", _agent_config["max_auto_actions"])
    config.setdefault("allow_high_risk_tools", _agent_config["allow_high_risk_tools"])
    config.setdefault("mcp_endpoint", _agent_config.get("mcp_endpoint"))
    if isinstance(config.get("enabled_models"), str):
        config["enabled_models"] = [config["enabled_models"]]
    tenant_tools = db_tools if db_tools else [t for t in _DEFAULT_AGENT_TOOLS if t.get("is_active", True)]
    tenant_sessions = (
        db_sessions if db_sessions else [s for s in _agent_sessions if s.get("tenant_id") == auth.tenant_id]
    )
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
            "auth": ["Keycloak", "JWT"],
            "observability": ["Prometheus", "Grafana", "Loki"],
            "audit": ["PostgreSQL", "OpenSearch"],
        },
        "config": config,
        "phase_info": {
            "phase1": {
                "label": "Internal Admin Agent",
                "status": "current" if config["current_phase"] == "phase1" else "planned",
                "description": "Read-only + reporting, 5-10 safe tools, local LLM",
            },
            "phase2": {
                "label": "Controlled Actions",
                "status": "current" if config["current_phase"] == "phase2" else "planned",
                "description": "Write tools with confirmation UX + full audit logging",
            },
            "phase3": {
                "label": "Full Kodee-Class",
                "status": "current" if config["current_phase"] == "phase3" else "planned",
                "description": "MCP tool registry, multi-agent orchestration, 350+ actions",
            },
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


async def execute_update_agent_config(req: AgentConfigUpdateRequest, auth: AuthDep):
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
    return {"status": "ok", "tenant_id": auth.tenant_id, "config": dict(_agent_config), "updated_at": _now()}


async def execute_register_agent_tool(req: AgentToolRegisterRequest, auth: AuthDep):
    """Add a new MCP-style tool to the agent's tool registry."""
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
    return {"status": "ok", "tenant_id": auth.tenant_id, "tool": new_tool, "total_tools": len(_DEFAULT_AGENT_TOOLS)}
