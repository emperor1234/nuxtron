"""Assistant use cases: ira ml retrieval query."""

from ..constants import APPLICATION_JSON
from ..constants import AuthDep
from ..runtime import ContextRuntime
from ..schemas import IRAFineTuningJobRequest
from ..schemas import IRARetrievalQueryRequest
from ..schemas import IRATrainingPipelineRequest
from ..services.reasoning_support import _cosine_similarity
from ..services.reasoning_support import _lexical_overlap_score
from ..services.reasoning_support import _local_hash_embedding
from ..services.reasoning_support import _now_iso
from ..services.reasoning_support import _tokenize_text
from .copilot_env_template import helper_embed_texts
from .copilot_env_template import helper_register_model_record
from .db_dsn import helper_append_ira_event
from .db_dsn import helper_audit
from .db_dsn import helper_choose_pipeline_framework
from .db_dsn import helper_get_or_create_control
from .db_dsn import helper_require_super_admin_for_control
from .frontier_stack_catalog import helper_tenant_suspicious_signal
from fastapi import HTTPException
from fastapi import Header
from typing import Annotated
from typing import Any
from typing import cast
import httpx
import os


def execute_ira_ml_retrieval_query(
    context_runtime: ContextRuntime, payload: IRARetrievalQueryRequest, auth: AuthDep
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:ml:retrieval:query", 120, 60)
    query_tokens = _tokenize_text(payload.query)
    query_backend, query_vectors = helper_embed_texts(context_runtime, [payload.query])
    query_vector = query_vectors[0] if query_vectors else _local_hash_embedding(payload.query)
    tenant_chunks = [
        item for item in context_runtime.ira_ml_knowledge_memory if item.get("tenant_id") == auth.tenant_id
    ]
    scored_results: list[dict[str, Any]] = []
    for item in tenant_chunks:
        candidate_vector = (
            cast(list[float], item.get("embedding", [])) if isinstance(item.get("embedding"), list) else []
        )
        candidate_tokens = cast(list[str], item.get("tokens", [])) if isinstance(item.get("tokens"), list) else []
        vector_score = (
            _cosine_similarity(query_vector, candidate_vector)
            if str(item.get("embedding_backend", "")) == query_backend
            else 0.0
        )
        lexical_score = _lexical_overlap_score(query_tokens, candidate_tokens)
        total_score = round(max(0.0, vector_score * 0.72 + lexical_score * 0.28), 4)
        if total_score < payload.min_score:
            continue
        scored_results.append(
            {
                "document_id": item.get("document_id", ""),
                "chunk_id": item.get("chunk_id", ""),
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "tags": item.get("tags", []),
                "content": item.get("content", ""),
                "score": total_score,
                "signals": {
                    "vector_score": round(vector_score, 4),
                    "lexical_score": round(lexical_score, 4),
                    "embedding_backend": item.get("embedding_backend", "local_hash"),
                },
            }
        )
    scored_results.sort(key=lambda item: (-float(item.get("score", 0.0)), str(item.get("chunk_id", ""))))
    top_results = scored_results[: payload.top_k]
    if top_results:
        synthesis = "IRA RAG synthesis: " + " ".join(
            (
                f"[{result.get('title', 'Knowledge')}] {str(result.get('content', ''))[:180]}"
                for result in top_results[:3]
            )
        )
    else:
        synthesis = (
            "IRA RAG synthesis: no relevant training knowledge is indexed yet. Load source documents before querying."
        )
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "ml_retrieval_query",
        {
            "query": payload.query[:240],
            "top_k": payload.top_k,
            "result_count": len(top_results),
            "embedding_backend": query_backend,
        },
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_ml_retrieval_query",
        {"event_id": event["id"], "result_count": len(top_results)},
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "query": payload.query,
        "embedding_backend": query_backend,
        "memory_backend": top_results[0].get("provider", "in_memory") if top_results else "in_memory",
        "results": top_results,
        "synthesis": synthesis,
        "event_id": event["id"],
    }


def execute_ira_ml_create_fine_tuning_job(
    context_runtime: ContextRuntime,
    payload: IRAFineTuningJobRequest,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:ml:fine-tuning:create", 30, 60)
    control = helper_get_or_create_control(context_runtime, auth.tenant_id)
    helper_require_super_admin_for_control(
        control=control,
        x_super_admin_key=x_super_admin_key,
        detail="IRA ML fine-tuning jobs are restricted to super admin sessions.",
    )
    provider_job_id = ""
    provider_response: dict[str, Any] = {}
    status = "draft"
    endpoint = payload.endpoint_url.strip()
    if not payload.dry_run:
        if payload.provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key:
                raise HTTPException(status_code=422, detail="OpenAI fine-tuning requires OPENAI_API_KEY.")
            if not payload.training_file_id.strip():
                raise HTTPException(status_code=422, detail="OpenAI fine-tuning requires training_file_id.")
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        "https://api.openai.com/v1/fine_tuning/jobs",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": APPLICATION_JSON},
                        json={
                            "model": payload.base_model,
                            "training_file": payload.training_file_id,
                            "validation_file": payload.validation_file_id or None,
                            "suffix": payload.suffix or None,
                            "hyperparameters": payload.hyperparameters or None,
                            "metadata": payload.metadata or None,
                        },
                    )
                provider_response = (
                    cast(dict[str, Any], response.json())
                    if response.headers.get("content-type", "").startswith(APPLICATION_JSON)
                    else {"detail": response.text}
                )
                if not response.is_success:
                    raise HTTPException(
                        status_code=422, detail=f"OpenAI fine-tuning rejected the job: {provider_response}"
                    )
                provider_job_id = str(provider_response.get("id", "")).strip()
                status = str(provider_response.get("status", "submitted")).strip() or "submitted"
            except HTTPException:
                raise
            except Exception as ex:
                raise HTTPException(status_code=422, detail=f"OpenAI fine-tuning dispatch failed: {ex}") from ex
        else:
            endpoint = endpoint or os.getenv("IRA_CUSTOM_FINETUNE_ENDPOINT", "").strip()
            if not endpoint:
                raise HTTPException(
                    status_code=422, detail="Custom fine-tuning requires endpoint_url or IRA_CUSTOM_FINETUNE_ENDPOINT."
                )
            headers = {"Content-Type": APPLICATION_JSON}
            bearer_token = os.getenv("IRA_CUSTOM_FINETUNE_BEARER_TOKEN", "").strip()
            if bearer_token:
                headers["Authorization"] = f"Bearer {bearer_token}"
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.post(
                        endpoint,
                        headers=headers,
                        json={
                            "base_model": payload.base_model,
                            "training_file_id": payload.training_file_id,
                            "validation_file_id": payload.validation_file_id,
                            "suffix": payload.suffix,
                            "hyperparameters": payload.hyperparameters,
                            "metadata": payload.metadata,
                        },
                    )
                provider_response = (
                    cast(dict[str, Any], response.json())
                    if response.headers.get("content-type", "").startswith(APPLICATION_JSON)
                    else {"detail": response.text}
                )
                if not response.is_success:
                    raise HTTPException(
                        status_code=422, detail=f"Custom fine-tuning rejected the job: {provider_response}"
                    )
                provider_job_id = str(provider_response.get("id", "") or provider_response.get("job_id", "")).strip()
                status = str(provider_response.get("status", "submitted")).strip() or "submitted"
            except HTTPException:
                raise
            except Exception as ex:
                raise HTTPException(status_code=422, detail=f"Custom fine-tuning dispatch failed: {ex}") from ex
    job: dict[str, Any] = {
        "id": len(context_runtime.ira_ml_jobs_memory) + 1,
        "tenant_id": auth.tenant_id,
        "job_type": "fine_tuning",
        "provider": payload.provider,
        "base_model": payload.base_model,
        "training_file_id": payload.training_file_id,
        "validation_file_id": payload.validation_file_id,
        "suffix": payload.suffix,
        "hyperparameters": payload.hyperparameters,
        "metadata": payload.metadata,
        "status": status,
        "dry_run": payload.dry_run,
        "provider_job_id": provider_job_id,
        "endpoint_url": endpoint,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    context_runtime.ira_ml_jobs_memory.append(job)
    model_record = helper_register_model_record(
        context_runtime,
        tenant_id=auth.tenant_id,
        model_type="fine_tuned_model",
        model_name=payload.suffix.strip() or payload.base_model,
        provider=payload.provider,
        source_job_id=str(job["id"]),
        status="draft" if payload.dry_run else status,
        metadata={"base_model": payload.base_model, "provider_job_id": provider_job_id},
    )
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "ml_fine_tuning_job_created",
        {"job_id": job["id"], "provider": payload.provider, "dry_run": payload.dry_run, "status": status},
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_ml_fine_tuning_job_created",
        {"event_id": event["id"], "job_id": job["id"], "provider": payload.provider},
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "job": job,
        "model": model_record,
        "provider_response": provider_response,
        "event_id": event["id"],
    }


def execute_ira_ml_create_pipeline(
    context_runtime: ContextRuntime,
    payload: IRATrainingPipelineRequest,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:ml:pipelines:create", 30, 60)
    control = helper_get_or_create_control(context_runtime, auth.tenant_id)
    helper_require_super_admin_for_control(
        control=control,
        x_super_admin_key=x_super_admin_key,
        detail="IRA ML pipeline creation is restricted to super admin sessions.",
    )
    selected_framework, runtime_ready, framework_reason = helper_choose_pipeline_framework(payload)
    document_set = {
        str(item.get("document_id", "")).strip()
        for item in context_runtime.ira_ml_knowledge_memory
        if item.get("tenant_id") == auth.tenant_id
    }
    selected_documents = [document_id for document_id in payload.dataset_document_ids if document_id in document_set]
    plan_steps = [
        "Validate dataset coverage and schema.",
        "Prepare train/validation split and feature pipeline.",
        f"Execute {payload.pipeline_type} workflow on {selected_framework}.",
        "Run offline evaluation and human review gates.",
        "Register promoted model and expose retrieval/fine-tune telemetry.",
    ]
    if payload.dry_run:
        status = "planned"
    elif runtime_ready:
        status = "queued"
    else:
        status = "waiting_for_runtime"
    job: dict[str, Any] = {
        "id": len(context_runtime.ira_ml_jobs_memory) + 1,
        "tenant_id": auth.tenant_id,
        "job_type": "pipeline",
        "name": payload.name,
        "objective": payload.objective,
        "pipeline_type": payload.pipeline_type,
        "framework": selected_framework,
        "runtime_ready": runtime_ready,
        "framework_reason": framework_reason,
        "dataset_document_ids": selected_documents,
        "requested_document_ids": payload.dataset_document_ids,
        "model_name": payload.model_name,
        "epochs": payload.epochs,
        "learning_rate": payload.learning_rate,
        "batch_size": payload.batch_size,
        "dry_run": payload.dry_run,
        "plan_steps": plan_steps,
        "status": status,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    context_runtime.ira_ml_jobs_memory.append(job)
    model_record = helper_register_model_record(
        context_runtime,
        tenant_id=auth.tenant_id,
        model_type=f"{payload.pipeline_type}_pipeline",
        model_name=payload.model_name.strip() or payload.name,
        provider=selected_framework,
        source_job_id=str(job["id"]),
        status=status,
        metadata={"objective": payload.objective, "dataset_document_count": len(selected_documents)},
    )
    event = helper_append_ira_event(
        context_runtime,
        auth.tenant_id,
        "ml_pipeline_created",
        {
            "job_id": job["id"],
            "pipeline_type": payload.pipeline_type,
            "framework": selected_framework,
            "runtime_ready": runtime_ready,
            "dry_run": payload.dry_run,
        },
    )
    helper_audit(
        context_runtime,
        auth.tenant_id,
        "ira_ml_pipeline_created",
        {"event_id": event["id"], "job_id": job["id"], "framework": selected_framework},
    )
    return {"status": "ok", "tenant_id": auth.tenant_id, "job": job, "model": model_record, "event_id": event["id"]}


def execute_ira_rollback_action(
    context_runtime: ContextRuntime,
    action_snapshot_id: int,
    auth: AuthDep,
    x_super_admin_key: Annotated[str | None, Header(alias="X-Super-Admin-Key")] = None,
) -> dict[str, Any]:
    """Rollback an IRA action to its before_state snapshot"""
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:rollback", 60, 60)
    with context_runtime.lock:
        control = helper_get_or_create_control(context_runtime, auth.tenant_id)
        helper_require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail="IRA rollback is restricted to super admin sessions.",
        )
        snapshot = next(
            (
                s
                for s in context_runtime.ira_action_snapshots_memory
                if s.get("id") == action_snapshot_id and s.get("tenant_id") == auth.tenant_id
            ),
            None,
        )
        if snapshot is None:
            raise HTTPException(status_code=404, detail=f"Action snapshot {action_snapshot_id} not found.")
        if not snapshot.get("rollback_enabled", False):
            raise HTTPException(status_code=422, detail=f"Target '{snapshot.get('target')}' does not support rollback.")
        rollback_event = helper_append_ira_event(
            context_runtime,
            auth.tenant_id,
            "action_rolled_back",
            {
                "original_event_id": snapshot.get("event_id"),
                "snapshot_id": action_snapshot_id,
                "target": snapshot.get("target"),
                "restored_state": snapshot.get("before_state", {}),
            },
        )
        helper_audit(
            context_runtime,
            auth.tenant_id,
            "ira_rollback_executed",
            {"event_id": rollback_event["id"], "snapshot_id": action_snapshot_id, "target": snapshot.get("target")},
        )
        return {
            "status": "ok",
            "tenant_id": auth.tenant_id,
            "snapshot_id": action_snapshot_id,
            "rollback_event_id": rollback_event["id"],
            "message": f"Rollback initiated for {snapshot.get('target')} action. System will restore to previous state.",
        }


def execute_ira_cost_summary(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    """Cost tracking summary — total spend per action type for this tenant."""
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:costs", 120, 60)
    tenant_costs = [c for c in context_runtime.ira_cost_ledger_memory if c.get("tenant_id") == auth.tenant_id]
    by_type: dict[str, dict[str, Any]] = {}
    for entry in tenant_costs:
        atype = str(entry.get("action_type", "unknown"))
        if atype not in by_type:
            by_type[atype] = {"count": 0, "total_cost_pence": 0.0}
        by_type[atype]["count"] += int(entry.get("units", 1))
        by_type[atype]["total_cost_pence"] = round(
            by_type[atype]["total_cost_pence"] + float(entry.get("total_cost_pence", 0)), 4
        )
    total_pence = sum((c.get("total_cost_pence", 0.0) for c in tenant_costs))
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "total_cost_pence": round(total_pence, 4),
        "total_cost_gbp": round(total_pence / 100, 6),
        "by_action_type": by_type,
        "recent_ledger": sorted(tenant_costs, key=lambda c: c.get("created_at", ""), reverse=True)[:20],
    }


def execute_ira_risk_score(context_runtime: ContextRuntime, auth: AuthDep) -> dict[str, Any]:
    context_runtime.enforce_rate_limit(f"{auth.tenant_id}:ira:risk:score", 120, 60)
    control = helper_get_or_create_control(context_runtime, auth.tenant_id)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "risk_signal": helper_tenant_suspicious_signal(context_runtime, auth.tenant_id),
        "thresholds": {"suspicious_signal_threshold": float(control.get("suspicious_signal_threshold", 0.75))},
        "protection_mode": bool(control.get("protection_mode", False)),
    }
