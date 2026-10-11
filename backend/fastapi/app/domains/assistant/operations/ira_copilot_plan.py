"""Assistant use cases: ira copilot plan."""

from ..constants import AUTONOMY_DISABLED_DETAIL
from ..constants import AuthDep
from ..constants import CONNECTOR_CHANNELS
from ..runtime import ContextRuntime
from ..schemas import IRAAgentBrainReasonRequest
from ..schemas import IRAAgentPreferenceUpdateRequest
from ..schemas import IRAAgentRunRequest
from ..schemas import IRACopilotPlanRequest
from ..schemas import IRAKnowledgeDocumentRequest
from ..schemas import IRAStructuredMemoryUpsertRequest
from ..services.reasoning_support import _chunk_text
from ..services.reasoning_support import _local_hash_embedding
from ..services.reasoning_support import _now_iso
from ..services.reasoning_support import _slugify
from ..services.reasoning_support import _tokenize_text
from .copilot_env_template import helper_agent_runtime_for_tenant
from .copilot_env_template import helper_copilot_env_template
from .copilot_env_template import helper_embed_texts
from .db_dsn import helper_append_ira_event
from .db_dsn import helper_audit
from .db_dsn import helper_get_or_create_connector
from .db_dsn import helper_get_or_create_control
from .db_dsn import helper_require_super_admin_for_control
from .db_dsn import helper_tenant_revenue_snapshot
from .frontier_stack_catalog import helper_tenant_suspicious_signal
from .ml_capabilities import helper_copilot_catalog
from .ml_capabilities import helper_copilot_readiness
from .ml_capabilities import helper_ml_summary
from fastapi import HTTPException
from fastapi import Header
from typing import Annotated
from typing import Any
from typing import cast
import os
import uuid


def execute_ira_copilot_plan(
    context_runtime: ContextRuntime, payload: IRACopilotPlanRequest, auth: AuthDep
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:copilot:plan", 60, 60)
    readiness = helper_copilot_readiness()
    phases: list[dict[str, Any]] = [
        {
            "phase": 1,
            "name": "Foundation + Access",
            "deliverables": ["token_setup", "org_repo_binding", "chat_flag_enablement", "policy_lock_defaults"],
        },
        {
            "phase": 2,
            "name": "Feature Enablement",
            "deliverables": ["chat_surface", "code_actions", "diagnostics", "test_runner_flows", "context_routing"],
        },
        {
            "phase": 3,
            "name": "Agent Workflows",
            "deliverables": ["task_planning", "tool_execution", "bounded_iterations", "approval_gates_for_high_impact"],
        },
        {
            "phase": 4,
            "name": "Enterprise Ops + Telemetry",
            "deliverables": ["audit_trails", "usage_analytics", "security_controls", "rollout_playbook", "runbooks"],
        },
    ]
    if not payload.include_agent_mode:
        phases = [phase for phase in phases if int(phase.get("phase", 0) or 0) != 3]
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "copilot_plan_generated",
        {
            "priority": payload.priority,
            "objective_preview": payload.objective[:140],
            "include_enterprise_controls": payload.include_enterprise_controls,
            "include_telemetry": payload.include_telemetry,
            "include_agent_mode": payload.include_agent_mode,
        },
    )
    helper_audit(context_runtime, auth.tenant_id, "ira_copilot_plan_generated", {"event_id": event["id"]})
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "objective": payload.objective,
        "priority": payload.priority,
        "implementation_phases": phases,
        "readiness": readiness,
        "catalog": helper_copilot_catalog(),
        "env_template": helper_copilot_env_template(),
        "event_id": event["id"],
    }


def execute_ira_ml_overview(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:ml:overview", 120, 60)
    knowledge = [
        item.copy() for item in context_runtime.ira_ml_knowledge_memory if item.get("tenant_id") == auth.tenant_id
    ]
    jobs = [item.copy() for item in context_runtime.ira_ml_jobs_memory if item.get("tenant_id") == auth.tenant_id][-20:]
    models = [item.copy() for item in context_runtime.ira_ml_models_memory if item.get("tenant_id") == auth.tenant_id][
        -20:
    ]
    documents: dict[str, dict[str, Any]] = {}
    for item in knowledge:
        document_id = str(item.get("document_id", "")).strip()
        if not document_id:
            continue
        existing = documents.get(document_id)
        if existing is None:
            documents[document_id] = {
                "document_id": document_id,
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "tags": item.get("tags", []),
                "chunk_count": 1,
                "embedding_backend": item.get("embedding_backend", "local_hash"),
                "updated_at": item.get("updated_at", item.get("created_at", "")),
            }
        else:
            existing["chunk_count"] = int(existing.get("chunk_count", 0) or 0) + 1
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "summary": helper_ml_summary(context_runtime, auth.tenant_id),
        "memory": context_runtime.memory_system.overview(auth.tenant_id),
        "documents": list(documents.values())[-25:],
        "jobs": jobs,
        "models": models,
    }


def execute_ira_short_term_memory(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:memory:short-term", 120, 60)
    messages = context_runtime.memory_system.get_short_term_messages(auth.tenant_id, limit=20)
    return {"status": "ok", "tenant_id": auth.tenant_id, "messages": messages}


def execute_ira_structured_memory_list(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:memory:structured:list", 120, 60)
    records = context_runtime.memory_system.list_structured_memory(auth.tenant_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "records": records}


def execute_ira_structured_memory_upsert(
    context_runtime: ContextRuntime, payload: IRAStructuredMemoryUpsertRequest, auth: AuthDep
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:memory:structured:upsert", 60, 60)
    record = context_runtime.memory_system.upsert_structured_memory(
        tenant_id=auth.tenant_id,
        memory_type=payload.memory_type,
        memory_key=payload.memory_key,
        payload=payload.payload,
    )
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "structured_memory_upserted",
        {
            "memory_type": payload.memory_type,
            "memory_key": payload.memory_key,
            "source": record.get("source", "in_memory"),
        },
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_structured_memory_upserted",
        {"event_id": event["id"], "memory_key": payload.memory_key},
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "record": record, "event_id": event["id"]}


def execute_ira_agent_frameworks(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:agent:frameworks", 120, 60)
    agent_runtime = helper_agent_runtime_for_tenant(context_runtime, auth.tenant_id)
    records = context_runtime.memory_system.list_structured_memory(auth.tenant_id, memory_type="preference")
    record = next((item for item in records if item.get("memory_key") == "agent_framework_auto"), None)
    tenant_auto_framework = "auto"
    if isinstance(record, dict):
        payload = record.get("payload")
        if isinstance(payload, dict):
            payload_map = cast(dict[str, Any], payload)
            framework_value = str(payload_map.get("framework", "")).strip().lower()
            if framework_value in {"langchain", "semantic_kernel", "native_secure_loop"}:
                tenant_auto_framework = framework_value
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "frameworks": agent_runtime.framework_status(),
        "brain": context_runtime.ai_brain.capabilities(),
        "auto_policy": {
            "env_default": os.getenv("IRA_AGENT_AUTO_FRAMEWORK", "").strip().lower() or "auto",
            "prefer_tenant_memory": os.getenv("IRA_AGENT_PREFER_TENANT_MEMORY", "1").strip() == "1",
            "tenant_override": tenant_auto_framework,
        },
    }


def execute_ira_agent_brain_capabilities(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:agent:brain:capabilities", 120, 60)
    return {"status": "ok", "tenant_id": auth.tenant_id, "brain": context_runtime.ai_brain.capabilities()}


def execute_ira_agent_brain_reason(
    context_runtime: ContextRuntime, payload: IRAAgentBrainReasonRequest, auth: AuthDep
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:agent:brain:reason", 60, 60)
    output = context_runtime.ai_brain.reason(
        prompt=payload.prompt,
        provider=payload.provider,
        tools=[cast(dict[str, Any], item) for item in payload.tools if isinstance(item, dict)],
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )
    reasoning = cast(dict[str, Any], output.get("reasoning", {}))
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "agent_brain_reasoned",
        {"provider": reasoning.get("provider", "deterministic_rule_based"), "status": output.get("status", "fallback")},
    )
    helper_audit(context_runtime, auth.tenant_id, "ira_agent_brain_reasoned", {"event_id": event["id"]})
    return {"status": "ok", "tenant_id": auth.tenant_id, "brain": output, "event_id": event["id"]}


def execute_ira_agent_preferences_update(
    context_runtime: ContextRuntime,
    payload: IRAAgentPreferenceUpdateRequest,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:agent:preferences:update", 60, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id)
        helper_require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail="IRA agent preference updates are restricted to super admin sessions.",
        )
    if payload.auto_framework == "auto":
        preference_payload = {"framework": "", "mode": "auto"}
    else:
        preference_payload = {"framework": payload.auto_framework, "mode": "tenant_override"}
    record = context_runtime.memory_system.upsert_structured_memory(
        tenant_id=auth.tenant_id,
        memory_type="preference",
        memory_key="agent_framework_auto",
        payload=preference_payload,
    )
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "agent_preference_updated",
        {"auto_framework": payload.auto_framework, "source": record.get("source", "in_memory")},
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_agent_preference_updated",
        {"event_id": event["id"], "auto_framework": payload.auto_framework},
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "record": record, "event_id": event["id"]}


def execute_ira_agent_run(
    context_runtime: ContextRuntime,
    payload: IRAAgentRunRequest,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:agent:run", 60, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id)
        helper_require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail="IRA agent execution is restricted to super admin sessions.",
        )
        if not bool(control.get("autonomy_enabled", True)):
            raise HTTPException(status_code=422, detail=AUTONOMY_DISABLED_DETAIL)
    agent_runtime = helper_agent_runtime_for_tenant(context_runtime, auth.tenant_id)
    memory_key = payload.memory_key.strip() or f"agent_{_slugify(payload.goal, fallback='run')}_{uuid.uuid4().hex[:8]}"
    run_result = agent_runtime.run(
        tenant_id=auth.tenant_id,
        goal=payload.goal,
        requested_framework=payload.framework,
        max_iterations=payload.max_iterations,
        dry_run=payload.dry_run,
        memory_key=memory_key,
    )
    job: dict[str, Any] = {
        "id": len(context_runtime.ira_ml_jobs_memory) + 1,
        "tenant_id": auth.tenant_id,
        "job_type": "agent_run",
        "name": str(run_result.get("run_id", "")),
        "objective": payload.goal,
        "framework": str(run_result.get("framework_selected", "native_secure_loop")),
        "framework_reason": str(run_result.get("framework_reason", "")),
        "iterations_executed": int(run_result.get("iterations_executed", 0)),
        "max_iterations": payload.max_iterations,
        "dry_run": payload.dry_run,
        "status": str(run_result.get("status", "completed")),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    context_runtime.ira_ml_jobs_memory.append(job)
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "agent_run_completed",
        {
            "run_id": run_result.get("run_id", ""),
            "framework_selected": run_result.get("framework_selected", "native_secure_loop"),
            "iterations_executed": run_result.get("iterations_executed", 0),
            "dry_run": payload.dry_run,
        },
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_agent_run_completed",
        {"event_id": event["id"], "run_id": run_result.get("run_id", "")},
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "run": run_result, "job": job, "event_id": event["id"]}


def execute_ira_ml_upsert_knowledge(
    context_runtime: ContextRuntime, payload: IRAKnowledgeDocumentRequest, auth: AuthDep
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:ml:knowledge:upsert", 60, 60)
    document_id = (
        payload.document_id.strip() or f"doc_{_slugify(payload.title, fallback='knowledge')}_{uuid.uuid4().hex[:8]}"
    )
    chunks = _chunk_text(
        payload.content,
        chunk_size=payload.chunk_size_chars,
        chunk_overlap=min(payload.chunk_overlap_chars, max(0, payload.chunk_size_chars - 20)),
    )
    embedding_backend, vectors = helper_embed_texts(context_runtime, chunks)
    cleaned_tags = sorted({tag.strip().lower() for tag in payload.tags if tag.strip()})
    created_at = _now_iso()
    with context_runtime.lock:
        context_runtime.ira_ml_knowledge_memory[:] = [
            item
            for item in context_runtime.ira_ml_knowledge_memory
            if not (item.get("tenant_id") == auth.tenant_id and item.get("document_id") == document_id)
        ]
        for index, chunk in enumerate(chunks):
            vector = vectors[index] if index < len(vectors) else _local_hash_embedding(chunk)
            context_runtime.ira_ml_knowledge_memory.append(
                {
                    "id": len(context_runtime.ira_ml_knowledge_memory) + 1,
                    "tenant_id": auth.tenant_id,
                    "document_id": document_id,
                    "chunk_id": f"{document_id}:chunk:{index + 1}",
                    "title": payload.title,
                    "source": payload.source,
                    "tags": cleaned_tags,
                    "metadata": payload.metadata,
                    "content": chunk,
                    "chunk_index": index,
                    "token_count": len(_tokenize_text(chunk)),
                    "chunk_count": len(chunks),
                    "embedding_backend": embedding_backend,
                    "embedding": vector,
                    "tokens": _tokenize_text(chunk),
                    "created_at": created_at,
                    "updated_at": created_at,
                }
            )
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "ml_knowledge_upserted",
        {
            "document_id": document_id,
            "title": payload.title,
            "chunk_count": len(chunks),
            "embedding_backend": embedding_backend,
        },
    )
    sync_result = context_runtime.memory_system.sync_long_term_memory(
        tenant_id=auth.tenant_id,
        records=[
            item
            for item in context_runtime.ira_ml_knowledge_memory
            if item.get("tenant_id") == auth.tenant_id and item.get("document_id") == document_id
        ],
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_ml_knowledge_upserted",
        {"event_id": event["id"], "document_id": document_id, "chunk_count": len(chunks)},
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "document": {
            "document_id": document_id,
            "title": payload.title,
            "chunk_count": len(chunks),
            "embedding_backend": embedding_backend,
            "tags": cleaned_tags,
            "source": payload.source,
            "created_at": created_at,
        },
        "memory_sync": sync_result,
        "event_id": event["id"],
    }


def execute_list_ira_connectors(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:connectors:list", 120, 60)
    with context_runtime.lock:
        connectors = [
            helper_get_or_create_connector(context_runtime, auth.tenant_id, channel).copy()
            for channel in CONNECTOR_CHANNELS
        ]
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(connectors), "connectors": connectors}


def execute_ira_finance_health(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:finance:health", 120, 60)
    control = helper_get_or_create_control(context_runtime, auth.tenant_id)
    snapshot = helper_tenant_revenue_snapshot(context_runtime, auth.tenant_id)
    suspicious_signal = helper_tenant_suspicious_signal(context_runtime, auth.tenant_id)
    risky = snapshot["profit_margin_pct"] < float(control.get("min_profit_margin_pct", 70.0))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "finance": snapshot,
        "suspicious_signal": suspicious_signal,
        "thresholds": {"min_profit_margin_pct": control.get("min_profit_margin_pct", 70.0)},
        "risk_state": "at_risk" if risky else "healthy",
        "protection_mode": bool(control.get("protection_mode", False)),
    }
