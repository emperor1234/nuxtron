"""Assistant use cases: ml capabilities."""

from ..services import reasoning_support as port_module_available
from ..runtime import ContextRuntime
from ..schemas import IRAFrontierPlanRequest
from typing import Any
from typing import Literal
from typing import cast
import os


def helper_ml_capabilities() -> dict[str, Any]:
    openai_configured = bool(os.getenv("OPENAI_API_KEY", "").strip())
    custom_finetune_endpoint = os.getenv("IRA_CUSTOM_FINETUNE_ENDPOINT", "").strip()
    sentence_transformers_available = port_module_available._module_available("sentence_transformers")
    pytorch_available = port_module_available._module_available("torch")
    tensorflow_available = port_module_available._module_available("tensorflow")
    preferred_embedding_backend = os.getenv("IRA_EMBEDDING_BACKEND", "auto").strip().lower()
    if preferred_embedding_backend not in {"auto", "openai", "sentence_transformers", "local_hash"}:
        preferred_embedding_backend = "auto"
    if preferred_embedding_backend == "auto":
        if openai_configured:
            active_embedding_backend = "openai"
        elif sentence_transformers_available:
            active_embedding_backend = "sentence_transformers"
        else:
            active_embedding_backend = "local_hash"
    else:
        active_embedding_backend = preferred_embedding_backend
    if pytorch_available:
        local_training_recommendation = "PyTorch"
    elif tensorflow_available:
        local_training_recommendation = "TensorFlow"
    else:
        local_training_recommendation = "managed APIs until runtime is installed"
    return {
        "embeddings": {
            "active_backend": active_embedding_backend,
            "openai_configured": openai_configured,
            "sentence_transformers_available": sentence_transformers_available,
            "local_hash_available": True,
            "openai_model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
            or "text-embedding-3-small",
            "sentence_transformer_model": os.getenv("IRA_SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2").strip()
            or "all-MiniLM-L6-v2",
        },
        "frameworks": {
            "pytorch": pytorch_available,
            "tensorflow": tensorflow_available,
            "sentence_transformers": sentence_transformers_available,
        },
        "fine_tuning": {
            "openai": {"configured": openai_configured, "managed": True},
            "custom_http": {"configured": bool(custom_finetune_endpoint), "endpoint": custom_finetune_endpoint},
        },
        "recommended_stack": {
            "rag": "sentence-transformers + hybrid lexical retrieval"
            if sentence_transformers_available
            else "hybrid hashed embeddings + lexical retrieval",
            "fine_tuning": "OpenAI managed fine-tuning" if openai_configured else "custom HTTP orchestration draft",
            "local_training": local_training_recommendation,
        },
    }


def helper_frontier_recommended_stack(payload: IRAFrontierPlanRequest) -> dict[str, Any]:
    if payload.include_free_open_source_only:
        brain = ["llama (ollama)", "mistral (ollama)"]
        agents = ["langgraph", "native_secure_loop"]
        memory = ["weaviate or pgvector", "neo4j" if payload.require_graph_memory else "postgres", "redis"]
        rag = ["llamaindex or haystack"]
        workflows = ["temporal (oss)", "n8n (oss)"]
    else:
        brain = ["openai", "anthropic", "cohere_embeddings_for_rag"]
        agents = ["crewai", "langgraph"]
        memory = ["pinecone", "neo4j" if payload.require_graph_memory else "weaviate", "redis"]
        rag = ["llamaindex", "hybrid_vector_keyword_retrieval", "query_rewriting", "context_compression"]
        workflows = ["temporal", "n8n", "zapier_or_make_for_external_actions"]
    multimodal = ["openai_vision_speech", "gemini_multimodal"] if payload.require_multimodal else ["text_only_mode"]
    observability = [
        "langsmith",
        "langfuse",
        "posthog",
        "sentry",
        "open_telemetry",
        "grafana",
        "better_stack",
        "weights_and_biases",
    ]
    safety = ["guardrails_ai", "rebuff", "human_approval_for_high_impact_actions"]
    return {
        "brain": brain,
        "agents": agents,
        "memory": memory,
        "multimodal": multimodal,
        "rag": rag,
        "workflows": workflows,
        "observability": observability,
        "safety": safety,
        "platform_acceleration": [
            "cloudflare",
            "vercel_with_analytics",
            "fly_io",
            "upstash",
            "neon",
            "uploadthing",
            "firecrawl",
            "agentops",
            "million_js",
            "partytown",
            "zustand",
            "hono_js",
            "zod",
            "trpc",
            "drizzle_orm",
        ],
        "enterprise_integrations": ["salesforce", "slack", "notion", "google_workspace"],
    }


def helper_frontier_readiness_summary(stack: dict[str, Any]) -> dict[str, Any]:
    signals_total = 0
    signals_ready = 0
    missing_signals: list[str] = []

    def _walk(value: Any, path: str) -> None:
        nonlocal signals_total, signals_ready
        if isinstance(value, dict):
            value_map = cast(dict[str, Any], value)
            for signal_name in ("configured", "available", "enabled"):
                if signal_name in value_map and isinstance(value_map[signal_name], bool):
                    signals_total += 1
                    signal_path = f"{path}.{signal_name}" if path else signal_name
                    if bool(value_map[signal_name]):
                        signals_ready += 1
                    else:
                        missing_signals.append(signal_path)
            for key, nested in value_map.items():
                next_path = f"{path}.{key}" if path else str(key)
                _walk(nested, next_path)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                _walk(item, f"{path}[{index}]")

    _walk(stack, "")
    readiness_score = 0
    if signals_total > 0:
        readiness_score = int(round(signals_ready / signals_total * 100))
    readiness_state = "low"
    if readiness_score >= 75:
        readiness_state = "high"
    elif readiness_score >= 40:
        readiness_state = "medium"
    return {
        "score_pct": readiness_score,
        "state": readiness_state,
        "signals_ready": signals_ready,
        "signals_total": signals_total,
        "missing_signals": missing_signals[:30],
    }


def helper_frontier_env_template(readiness: dict[str, Any]) -> dict[str, Any]:
    signal_to_env: dict[str, list[str]] = {
        "frontier_reasoning_and_multi_agent_intelligence.providers.openai.configured": [
            "OPENAI_API_KEY=",
            "OPENAI_MODEL=gpt-4.1-mini",
        ],
        "frontier_reasoning_and_multi_agent_intelligence.providers.anthropic.configured": [
            "ANTHROPIC_API_KEY=",
            "ANTHROPIC_MODEL=claude-3-5-sonnet-latest",
        ],
        "frontier_reasoning_and_multi_agent_intelligence.providers.cohere.configured": [
            "COHERE_API_KEY=",
            "COHERE_MODEL=command-r-plus",
        ],
        "frontier_reasoning_and_multi_agent_intelligence.orchestration.crewai.available": [
            "IRA_ENABLE_CREWAI=1",
            "IRA_CREWAI_SECURE_MODE=1",
        ],
        "long_term_memory_and_knowledge.vector_memory.pinecone.configured": [
            "PINECONE_API_KEY=",
            "PINECONE_INDEX_HOST=",
            "PINECONE_NAMESPACE=ira-memory",
        ],
        "long_term_memory_and_knowledge.vector_memory.weaviate.configured": [
            "WEAVIATE_URL=",
            "WEAVIATE_API_KEY=",
            "WEAVIATE_CLASS_NAME=IraMemoryChunk",
        ],
        "long_term_memory_and_knowledge.graph_memory.neo4j.configured": [
            "NEO4J_URI=",
            "NEO4J_USERNAME=",
            "NEO4J_PASSWORD=",
        ],
        "long_term_memory_and_knowledge.realtime_memory.redis.configured": [
            "REDIS_HOST=",
            "REDIS_PORT=6379",
            "REDIS_PASSWORD=",
            "REDIS_DB=0",
        ],
        "multimodal_perception.providers.google_deepmind_gemini.configured": [
            "GOOGLE_VERTEX_API_KEY=",
            "GOOGLE_VERTEX_PROJECT_ID=",
            "GOOGLE_VERTEX_MODEL=gemini-2.0-flash",
            "GOOGLE_VERTEX_LOCATION=us-central1",
        ],
        "multimodal_perception.providers.assemblyai.configured": ["ASSEMBLYAI_API_KEY="],
        "multimodal_perception.providers.runway.configured": ["RUNWAY_API_KEY="],
        "autonomous_tool_execution_layer.automation.zapier.available": ["ZAPIER_WEBHOOK_URL="],
        "autonomous_tool_execution_layer.automation.make.available": ["MAKE_WEBHOOK_URL="],
        "continuous_learning_and_evaluation.platforms.weights_and_biases.configured": ["WANDB_API_KEY="],
        "continuous_learning_and_evaluation.platforms.langsmith.configured": [
            "LANGCHAIN_API_KEY=",
            "LANGCHAIN_TRACING_V2=true",
            "LANGCHAIN_PROJECT=nuxtron-ira",
        ],
        "continuous_learning_and_evaluation.platforms.humanloop.configured": ["HUMANLOOP_API_KEY="],
        "platform_acceleration_best_of.delivery_and_edge.cloudflare.configured": [
            "CLOUDFLARE_API_TOKEN=",
            "CLOUDFLARE_ZONE_ID=",
        ],
        "platform_acceleration_best_of.delivery_and_edge.vercel.configured": [
            "VERCEL_TOKEN=",
            "VERCEL_PROJECT_ID=",
            "NEXT_PUBLIC_VERCEL_ANALYTICS_ID=",
        ],
        "platform_acceleration_best_of.delivery_and_edge.fly_io.configured": ["FLY_API_TOKEN=", "FLY_APP_NAME="],
        "platform_acceleration_best_of.data_and_runtime_speed.upstash.configured": [
            "UPSTASH_REDIS_REST_URL=",
            "UPSTASH_REDIS_REST_TOKEN=",
        ],
        "platform_acceleration_best_of.data_and_runtime_speed.neon.configured": ["NEON_DATABASE_URL="],
        "platform_acceleration_best_of.data_and_runtime_speed.uploadthing.configured": [
            "UPLOADTHING_TOKEN=",
            "UPLOADTHING_APP_ID=",
        ],
        "platform_acceleration_best_of.observability_and_ai_ops.sentry.configured": [
            "SENTRY_DSN=",
            "SENTRY_TRACES_SAMPLE_RATE=0.2",
        ],
        "platform_acceleration_best_of.observability_and_ai_ops.langsmith.configured": [
            "LANGSMITH_API_KEY=",
            "LANGCHAIN_TRACING_V2=true",
            "LANGCHAIN_PROJECT=nuxtron-ira",
        ],
        "platform_acceleration_best_of.observability_and_ai_ops.langfuse.configured": [
            "LANGFUSE_PUBLIC_KEY=",
            "LANGFUSE_SECRET_KEY=",
            "LANGFUSE_HOST=https://cloud.langfuse.com",
        ],
        "platform_acceleration_best_of.observability_and_ai_ops.grafana.configured": [
            "GRAFANA_URL=",
            "GRAFANA_API_KEY=",
        ],
        "platform_acceleration_best_of.observability_and_ai_ops.open_telemetry.configured": [
            "OTEL_EXPORTER_OTLP_ENDPOINT=",
            "OTEL_SERVICE_NAME=nuxtron-fastapi",
        ],
        "platform_acceleration_best_of.observability_and_ai_ops.better_stack.configured": [
            "BETTER_STACK_SOURCE_TOKEN="
        ],
        "platform_acceleration_best_of.observability_and_ai_ops.agentops.configured": ["AGENTOPS_API_KEY="],
        "platform_acceleration_best_of.ai_data_enrichment.firecrawl.configured": ["FIRECRAWL_API_KEY="],
        "platform_acceleration_best_of.frontend_and_api_architecture.frontend_speed_toggles.million_js.enabled": [
            "NEXT_PUBLIC_ENABLE_MILLION=1"
        ],
        "platform_acceleration_best_of.frontend_and_api_architecture.frontend_speed_toggles.partytown.enabled": [
            "NEXT_PUBLIC_ENABLE_PARTYTOWN=1"
        ],
        "platform_acceleration_best_of.frontend_and_api_architecture.frontend_speed_toggles.zustand.enabled": [
            "NEXT_PUBLIC_ENABLE_ZUSTAND=1"
        ],
        "platform_acceleration_best_of.frontend_and_api_architecture.api_stack_choices.hono_js.enabled": [
            "API_BFF_FRAMEWORK=hono"
        ],
        "platform_acceleration_best_of.frontend_and_api_architecture.api_stack_choices.trpc.enabled": [
            "API_TRANSPORT=trpc"
        ],
        "platform_acceleration_best_of.frontend_and_api_architecture.api_stack_choices.drizzle_orm.enabled": [
            "DATABASE_ORM=drizzle"
        ],
        "platform_acceleration_best_of.frontend_and_api_architecture.api_stack_choices.zod.enabled": [
            "API_SCHEMA_VALIDATION=zod"
        ],
        "deep_enterprise_integrations.salesforce.configured": [
            "SALESFORCE_CLIENT_ID=",
            "SALESFORCE_CLIENT_SECRET=",
            "SALESFORCE_USERNAME=",
            "SALESFORCE_PASSWORD=",
        ],
        "deep_enterprise_integrations.slack.configured": ["SLACK_BOT_TOKEN=", "SLACK_SIGNING_SECRET="],
        "deep_enterprise_integrations.notion.configured": ["NOTION_API_KEY="],
        "deep_enterprise_integrations.google_workspace.configured": [
            "GOOGLE_WORKSPACE_CLIENT_ID=",
            "GOOGLE_WORKSPACE_CLIENT_SECRET=",
        ],
    }
    missing = (
        cast(list[str], readiness.get("missing_signals", []))
        if isinstance(readiness.get("missing_signals"), list)
        else []
    )
    lines: list[str] = []
    seen: set[str] = set()
    for signal in missing:
        env_lines = signal_to_env.get(signal, [])
        for line in env_lines:
            if line not in seen:
                seen.add(line)
                lines.append(line)
    required = [line for line in lines if line.endswith("=")]
    defaults = [line for line in lines if not line.endswith("=")]
    template_sections = [
        "# Frontier AI Stack generated template",
        "# Fill required values below, keep defaults unless needed.",
        "",
        "# Required values",
        *required,
        "",
        "# Recommended defaults",
        *defaults,
    ]
    return {
        "required_env_count": len(required),
        "recommended_defaults_count": len(defaults),
        "required_env": required,
        "recommended_defaults": defaults,
        "template": "\n".join(template_sections).strip(),
    }


def helper_copilot_catalog() -> dict[str, Any]:
    return {
        "a_to_z": {
            "A": "Agent mode (task loops, multi-step execution)",
            "B": "Bring your own models through provider routing",
            "C": "Chat with repository context and codebase grounding",
            "D": "Documentation generation and summarization workflows",
            "E": "Enterprise policy controls and governance gates",
            "F": "Fix suggestions and code actions",
            "G": "Git-aware PR review and commit-aware assistance",
            "H": "Hybrid search: semantic + lexical retrieval",
            "I": "Inline completions and suggestion ranking",
            "J": "Just-in-time command and terminal assistance",
            "K": "Knowledge retrieval from local docs and runbooks",
            "L": "Long-context reasoning with tool contracts",
            "M": "MCP-style tool integrations and function-calling",
            "N": "Natural language to code/query transformations",
            "O": "Observability signals, traces, and usage analytics",
            "P": "Prompt templates and reusable workflows",
            "Q": "Quality gates with tests/lint/type checks",
            "R": "Refactoring orchestration and safe edits",
            "S": "Security posture checks and safe defaults",
            "T": "Task planning, decomposition, and execution phases",
            "U": "User memory and session memory continuity",
            "V": "Version-aware migrations and API compatibility",
            "W": "Workspace-aware code navigation",
            "X": "eXternal system connectors (GitHub, CI, tickets)",
            "Y": "Yield optimization for speed/cost/reliability tradeoffs",
            "Z": "Zero-trust guardrails for high-impact actions",
        },
        "feature_families": {
            "chat": [
                "multi-turn chat",
                "context carryover",
                "repo-grounded answers",
                "explain-code mode",
                "generate-code mode",
            ],
            "coding": [
                "inline completion",
                "test generation",
                "refactor proposals",
                "error-aware fixes",
                "safe patch suggestions",
            ],
            "agent": [
                "plan tool",
                "multi-step execution",
                "terminal + file operations",
                "live validation loops",
                "bounded retries and safeguards",
            ],
            "security_compliance": [
                "policy-gated actions",
                "audit events",
                "approval requirements for risky paths",
                "secret-safe handling patterns",
            ],
            "developer_experience": [
                "symbol navigation",
                "usage lookup",
                "rename actions",
                "problem diagnostics integration",
                "test run integration",
            ],
        },
    }


def helper_copilot_readiness() -> dict[str, Any]:
    model_routing = os.getenv("IRA_COPILOT_MODEL_ROUTING", "github_auto").strip().lower()
    require_models_token = model_routing in {"github_models", "direct_models_api"}
    signals: dict[str, bool] = {
        "github_token_configured": bool(os.getenv("GITHUB_TOKEN", "").strip()),
        "github_models_token_configured": bool(os.getenv("GITHUB_MODELS_TOKEN", "").strip())
        if require_models_token
        else True,
        "github_org_configured": bool(os.getenv("GITHUB_ORG", "").strip()),
        "github_repo_configured": bool(os.getenv("GITHUB_REPO", "").strip()),
        "copilot_chat_enabled_flag": os.getenv("IRA_ENABLE_COPILOT_CHAT", "0").strip() == "1",
        "copilot_agent_enabled_flag": os.getenv("IRA_ENABLE_COPILOT_AGENT", "0").strip() == "1",
        "copilot_telemetry_enabled_flag": os.getenv("IRA_ENABLE_COPILOT_TELEMETRY", "1").strip() == "1",
        "copilot_policy_lock_flag": os.getenv("IRA_COPILOT_POLICY_LOCK", "1").strip() == "1",
    }
    total = len(signals)
    ready = sum((1 for value in signals.values() if value))
    score = int(ready / total * 100) if total else 0
    missing = [key for key, value in signals.items() if not value]
    state: Literal["low", "medium", "high"] = "low"
    if score >= 75:
        state = "high"
    elif score >= 40:
        state = "medium"
    return {
        "score_pct": score,
        "state": state,
        "signals_ready": ready,
        "signals_total": total,
        "signals": signals,
        "missing_signals": missing,
        "model_routing": model_routing,
        "models_token_required": require_models_token,
    }


def helper_ml_summary(context_runtime: ContextRuntime, tenant_id: str) -> dict[str, Any]:
    tenant_knowledge = [item for item in context_runtime.ira_ml_knowledge_memory if item.get("tenant_id") == tenant_id]
    tenant_jobs = [item for item in context_runtime.ira_ml_jobs_memory if item.get("tenant_id") == tenant_id]
    tenant_models = [item for item in context_runtime.ira_ml_models_memory if item.get("tenant_id") == tenant_id]
    document_ids = {
        str(item.get("document_id", "")).strip()
        for item in tenant_knowledge
        if str(item.get("document_id", "")).strip()
    }
    active_jobs = [
        item for item in tenant_jobs if str(item.get("status", "")).lower() in {"queued", "submitted", "running"}
    ]
    memory_overview = context_runtime.memory_system.overview(tenant_id)
    return {
        "documents": len(document_ids),
        "knowledge_chunks": len(tenant_knowledge),
        "jobs": len(tenant_jobs),
        "active_jobs": len(active_jobs),
        "models": len(tenant_models),
        "capabilities": helper_ml_capabilities(),
        "memory_system": {
            "short_term_messages": int(memory_overview["summary"]["short_term_messages"]),
            "structured_records": int(memory_overview["summary"]["structured_records"]),
            "active_short_term_backend": str(memory_overview["summary"]["active_short_term_backend"]),
            "active_long_term_backend": str(memory_overview["summary"]["active_long_term_backend"]),
            "active_structured_backend": str(memory_overview["summary"]["active_structured_backend"]),
        },
    }
