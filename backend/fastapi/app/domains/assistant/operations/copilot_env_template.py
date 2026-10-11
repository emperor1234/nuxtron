"""Assistant use cases: copilot env template."""

from .... import ira_connector_integration as port_dispatch_via_ira_connector
from ....ira_agent import IRAAgentRuntime
from ..constants import APPLICATION_JSON
from ..runtime import ContextRuntime
from ..schemas import IRAChatActionPlan
from ..services.reasoning_support import _local_hash_embedding
from ..services.reasoning_support import _normalize_brain_provider
from ..services.reasoning_support import _now_iso
from .ira_response import helper_ira_response
from .ml_capabilities import helper_ml_capabilities
from typing import Any
from typing import cast
import httpx
import importlib.util
import os


def helper_copilot_env_template() -> dict[str, Any]:
    required_env = [
        "GITHUB_TOKEN=",
        "GITHUB_ORG=",
        "GITHUB_REPO=",
        "IRA_COPILOT_MODEL_ROUTING=github_auto",
        "IRA_ENABLE_COPILOT_CHAT=1",
        "IRA_ENABLE_COPILOT_AGENT=1",
    ]
    recommended_env = [
        "GITHUB_MODELS_TOKEN=",
        "IRA_ENABLE_COPILOT_TELEMETRY=1",
        "IRA_COPILOT_POLICY_LOCK=1",
        "IRA_COPILOT_MAX_ITERATIONS=6",
        "IRA_COPILOT_DEFAULT_MODEL=gpt-4.1",
        "IRA_COPILOT_FALLBACK_MODEL=gpt-4.1-mini",
        "IRA_COPILOT_AUDIT_RETENTION_DAYS=90",
        "IRA_COPILOT_APPROVAL_REQUIRED_FOR_HIGH_IMPACT=1",
        "IRA_COPILOT_ALLOWED_TOOLS=file_edit,terminal,tests,diagnostics",
    ]
    lines = [
        "# GitHub Copilot platform integration template",
        "# Required settings",
        *required_env,
        "",
        "# Recommended settings",
        *recommended_env,
    ]
    return {
        "required_env_count": len(required_env),
        "recommended_env_count": len(recommended_env),
        "required_env": required_env,
        "recommended_env": recommended_env,
        "template": "\n".join(lines).strip(),
    }


def helper_copilot_health_check() -> dict[str, Any]:
    model_routing = os.getenv("IRA_COPILOT_MODEL_ROUTING", "github_auto").strip().lower()
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        if model_routing == "github_auto":
            return {
                "status": "auto_mode",
                "github_api": {
                    "reachable": False,
                    "detail": "GITHUB_TOKEN is not configured; running in github_auto mode without direct GitHub API verification.",
                },
                "model_routing": model_routing,
            }
        return {
            "status": "not_configured",
            "github_api": {"reachable": False, "detail": "GITHUB_TOKEN is not configured"},
            "model_routing": model_routing,
        }
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(
                "https://api.github.com/rate_limit",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
        if response.is_success:
            payload = cast(dict[str, Any], response.json())
            resources_raw = payload.get("resources", {})
            resources = cast(dict[str, Any], resources_raw) if isinstance(resources_raw, dict) else {}
            return {
                "status": "ok",
                "github_api": {
                    "reachable": True,
                    "http_status": response.status_code,
                    "rate_limit_resources": resources,
                },
                "model_routing": model_routing,
            }
        return {
            "status": "error",
            "github_api": {"reachable": False, "http_status": response.status_code, "detail": response.text[:300]},
            "model_routing": model_routing,
        }
    except Exception as ex:
        return {
            "status": "error",
            "github_api": {"reachable": False, "detail": str(ex)},
            "model_routing": model_routing,
        }


def helper_embed_texts(context_runtime: ContextRuntime, values: list[str]) -> tuple[str, list[list[float]]]:
    capabilities = helper_ml_capabilities()
    active_backend = str(capabilities["embeddings"]["active_backend"])
    if active_backend == "sentence_transformers" and bool(capabilities["frameworks"]["sentence_transformers"]):
        try:
            model_name = str(capabilities["embeddings"]["sentence_transformer_model"])
            model = context_runtime.sentence_transformer_cache.get(model_name)
            if model is None:
                sentence_transformers_module = importlib.import_module("sentence_transformers")
                sentence_transformer_class = sentence_transformers_module.SentenceTransformer
                model = sentence_transformer_class(model_name)
                context_runtime.sentence_transformer_cache[model_name] = model
            embeddings = model.encode(values, normalize_embeddings=True)
            normalized_rows: list[list[float]] = []
            for row in cast(list[Any], embeddings):
                normalized_rows.append([float(entry) for entry in cast(list[Any], row)])
            if len(normalized_rows) == len(values):
                return ("sentence_transformers", normalized_rows)
        except Exception:
            pass
    if active_backend == "openai" and bool(capabilities["fine_tuning"]["openai"]["configured"]):
        try:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            model_name = str(capabilities["embeddings"]["openai_model"])
            with httpx.Client(timeout=20.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": APPLICATION_JSON},
                    json={"model": model_name, "input": values},
                )
            if response.is_success:
                payload = cast(dict[str, Any], response.json())
                raw_data = payload.get("data")
                data: list[Any] = []
                if isinstance(raw_data, list):
                    for entry in raw_data:
                        data.append(entry)
                if len(data) == len(values):
                    rows: list[list[float]] = []
                    for raw_item in data:
                        row_item = cast(dict[str, Any], raw_item) if isinstance(raw_item, dict) else {}
                        embedding = row_item.get("embedding")
                        if isinstance(embedding, list):
                            rows.append([float(entry) for entry in embedding])
                    if len(rows) == len(values):
                        return ("openai", rows)
        except Exception:
            pass
    return ("local_hash", [_local_hash_embedding(value) for value in values])


def helper_register_model_record(
    context_runtime: ContextRuntime,
    *,
    tenant_id: str,
    model_type: str,
    model_name: str,
    provider: str,
    source_job_id: str,
    status: str,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    existing = next(
        (
            item
            for item in context_runtime.ira_ml_models_memory
            if item.get("tenant_id") == tenant_id
            and item.get("source_job_id") == source_job_id
            and (item.get("model_type") == model_type)
        ),
        None,
    )
    if existing is not None:
        existing["model_name"] = model_name
        existing["provider"] = provider
        existing["status"] = status
        existing["metadata"] = metadata
        existing["updated_at"] = _now_iso()
        return existing
    record: dict[str, Any] = {
        "id": len(context_runtime.ira_ml_models_memory) + 1,
        "tenant_id": tenant_id,
        "model_type": model_type,
        "model_name": model_name,
        "provider": provider,
        "source_job_id": source_job_id,
        "status": status,
        "metadata": metadata,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    context_runtime.ira_ml_models_memory.append(record)
    return record


def helper_retrieve_knowledge_context(
    context_runtime: ContextRuntime, tenant_id: str, query: str, *, top_k: int = 3, min_score: float = 0.12
) -> list[dict[str, Any]]:
    _, results = context_runtime.memory_system.query_long_term_memory(
        tenant_id=tenant_id,
        query=query,
        top_k=top_k,
        min_score=min_score,
        fallback_items=[item for item in context_runtime.ira_ml_knowledge_memory if item.get("tenant_id") == tenant_id],
    )
    return results


def helper_agent_runtime_for_tenant(context_runtime: ContextRuntime, tenant_id: str) -> IRAAgentRuntime:

    def _tenant_auto_framework_preference(tenant_id_value: str) -> str | None:
        prefer_tenant_memory = os.getenv("IRA_AGENT_PREFER_TENANT_MEMORY", "1").strip() == "1"
        if prefer_tenant_memory:
            records = context_runtime.memory_system.list_structured_memory(tenant_id_value, memory_type="preference")
            record = next((item for item in records if item.get("memory_key") == "agent_framework_auto"), None)
            if isinstance(record, dict):
                payload = record.get("payload")
                if isinstance(payload, dict):
                    payload_map = cast(dict[str, Any], payload)
                    framework_value = str(payload_map.get("framework", "")).strip().lower()
                    if framework_value in {"langchain", "semantic_kernel", "native_secure_loop"}:
                        return framework_value
        env_preference = os.getenv("IRA_AGENT_AUTO_FRAMEWORK", "").strip().lower()
        if env_preference in {"langchain", "semantic_kernel", "native_secure_loop"}:
            return env_preference
        return None

    return IRAAgentRuntime(
        now_iso_fn=_now_iso,
        retrieve_knowledge=lambda query, top_k, min_score: helper_retrieve_knowledge_context(
            context_runtime, tenant_id=tenant_id, query=query, top_k=top_k, min_score=min_score
        ),
        upsert_structured_memory=lambda memory_type, memory_key, payload: (
            context_runtime.memory_system.upsert_structured_memory(
                tenant_id=tenant_id, memory_type=memory_type, memory_key=memory_key, payload=payload
            )
        ),
        get_short_term_messages=lambda tenant_id_value, limit: context_runtime.memory_system.get_short_term_messages(
            tenant_id_value, limit=limit
        ),
        compose_response=lambda message, knowledge_hits: helper_ira_response(
            "operator", "chat", message, knowledge_hits=knowledge_hits
        ),
        brain_reason=lambda prompt, provider, tools: context_runtime.ai_brain.reason(
            prompt=prompt, provider=_normalize_brain_provider(provider), tools=tools
        ),
        get_auto_framework_preference=_tenant_auto_framework_preference,
    )


def helper_classify_chat_intent(
    *, message: str, recent_history: list[dict[str, Any]] | None = None
) -> tuple[str, str, float]:
    message_text = message.strip().lower()
    history_text = " ".join((str(item.get("content", "")) for item in (recent_history or [])[-8:])).lower()
    combined = f"{message_text} {history_text}".strip()
    if any((token in combined for token in ("refund", "invoice", "billing", "charge", "credit", "dispute"))):
        return ("financial_ops", "billing", 0.86)
    if any((token in combined for token in ("breach", "incident", "security", "threat", "siem", "risk"))):
        return ("security_ops", "security", 0.88)
    if any((token in combined for token in ("campaign", "roas", "cac", "ads", "paid", "creative"))):
        return ("growth_ads", "ads", 0.82)
    if any((token in combined for token in ("seo", "keyword", "backlink", "ranking", "technical audit", "core web"))):
        return ("growth_seo", "seo", 0.83)
    if any(
        (token in combined for token in ("social", "post", "linkedin", "instagram", "tiktok", "youtube", "calendar"))
    ):
        return ("growth_social", "social", 0.8)
    if any((token in combined for token in ("ticket", "support", "customer", "onboarding", "issue", "help"))):
        return ("customer_support", "support", 0.78)
    return ("general_ops", "general", 0.62)


def helper_chat_risk_assessment(message: str) -> dict[str, Any]:
    lowered = message.lower()
    suspicious_markers = (
        "ignore previous instructions",
        "bypass policy",
        "disable security",
        "exfiltrate",
        "leak key",
        "steal token",
        "override approval",
    )
    matched = [marker for marker in suspicious_markers if marker in lowered]
    return {
        "risk_level": "high" if matched else "low",
        "prompt_injection_markers": matched,
        "needs_manual_review": bool(matched),
    }


def helper_build_chat_action_plan(*, intent: str, domain: str, risk: dict[str, Any]) -> IRAChatActionPlan:
    requires_human_validation = bool(risk.get("needs_manual_review", False)) or domain in {"billing", "security"}
    requires_explicit_approval = domain in {"billing", "security"}
    recommended_actions: list[dict[str, Any]] = [
        {
            "label": "Create IRA autonomous run plan",
            "endpoint": "/ira/agent/run",
            "method": "POST",
            "dry_run": True,
            "priority": "high",
        },
        {
            "label": "Persist operator intent to structured memory",
            "endpoint": "/ira/memory/structured/upsert",
            "method": "POST",
            "dry_run": True,
            "priority": "medium",
        },
    ]
    if domain in {"billing", "security"}:
        recommended_actions.append(
            {
                "label": "Execute guarded action with approvals",
                "endpoint": "/ira/actions",
                "method": "POST",
                "dry_run": True,
                "priority": "high",
            }
        )
    else:
        recommended_actions.append(
            {
                "label": "Execute low-risk operational action",
                "endpoint": "/ira/actions",
                "method": "POST",
                "dry_run": True,
                "priority": "medium",
            }
        )
    return IRAChatActionPlan(
        intent=intent,
        domain=domain,
        requires_human_validation=requires_human_validation,
        requires_explicit_approval=requires_explicit_approval,
        recommended_actions=recommended_actions,
    )


def helper_deliver_email(
    context_runtime: ContextRuntime, *, tenant_id: str, connector: dict[str, Any], payload: dict[str, Any]
) -> dict[str, Any]:
    """Send email via configured connector using integration layer."""
    subject = str(payload.get("subject", "IRA automated email")).strip() or "IRA automated email"
    body = str(payload.get("body", payload.get("message", ""))).strip() or "IRA automated email."
    recipient = str(payload.get("to", payload.get("recipient", "ops@nuxtron.local"))).strip() or "ops@nuxtron.local"
    result = port_dispatch_via_ira_connector.dispatch_via_ira_connector(
        channel="email", ira_connector=connector, recipient=recipient, subject=subject, body=body
    )
    if result["delivery_status"] in ("queued", "failed"):
        queued: dict[str, Any] = {
            "id": len(context_runtime.resend_messages_memory) + 1,
            "tenant_id": tenant_id,
            "provider": result.get("provider", "unknown"),
            "to": recipient,
            "subject": subject,
            "body": body,
            "status": "queued",
            "created_at": _now_iso(),
        }
        context_runtime.resend_messages_memory.append(queued)
        return {**result, "message_id": queued["id"]}
    return result
