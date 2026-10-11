"""Assistant use cases: frontier stack catalog."""

from ..services import reasoning_support as port_module_available
from ..runtime import ContextRuntime
from ..services.reasoning_support import compute_tenant_suspicious_signal
from .db_dsn import helper_free_tier_readiness
from .db_dsn import helper_split_env_assignment
from typing import Any
import os


def helper_frontier_stack_catalog() -> dict[str, Any]:
    temporal_ready = port_module_available._module_available("temporalio")
    crewai_ready = (
        port_module_available._module_available("crewai") and os.getenv("IRA_ENABLE_CREWAI", "0").strip() == "1"
    )
    langgraph_ready = port_module_available._module_available("langgraph")
    neo4j_ready = bool(os.getenv("NEO4J_URI", "").strip())
    pinecone_ready = bool(os.getenv("PINECONE_API_KEY", "").strip())
    weaviate_ready = bool(os.getenv("WEAVIATE_URL", "").strip())
    redis_ready = bool(os.getenv("REDIS_HOST", "").strip())
    openai_ready = bool(os.getenv("OPENAI_API_KEY", "").strip())
    anthropic_ready = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    cohere_ready = bool(os.getenv("COHERE_API_KEY", "").strip())
    gemini_ready = bool(os.getenv("GOOGLE_VERTEX_API_KEY", "").strip())
    cloudflare_ready = bool(os.getenv("CLOUDFLARE_API_TOKEN", "").strip()) and bool(
        os.getenv("CLOUDFLARE_ZONE_ID", "").strip()
    )
    vercel_ready = bool(os.getenv("VERCEL_TOKEN", "").strip()) and bool(os.getenv("VERCEL_PROJECT_ID", "").strip())
    flyio_ready = bool(os.getenv("FLY_API_TOKEN", "").strip()) and bool(os.getenv("FLY_APP_NAME", "").strip())
    upstash_ready = bool(os.getenv("UPSTASH_REDIS_REST_URL", "").strip()) and bool(
        os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
    )
    posthog_ready = bool(os.getenv("POSTHOG_PROJECT_API_KEY", "").strip())
    sentry_ready = bool(os.getenv("SENTRY_DSN", "").strip())
    langsmith_ready = bool(os.getenv("LANGSMITH_API_KEY", "").strip()) or bool(
        os.getenv("LANGCHAIN_API_KEY", "").strip()
    )
    langfuse_ready = bool(os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()) and bool(
        os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    )
    grafana_ready = bool(os.getenv("GRAFANA_URL", "").strip()) and bool(os.getenv("GRAFANA_API_KEY", "").strip())
    neon_ready = bool(os.getenv("NEON_DATABASE_URL", "").strip())
    firecrawl_ready = bool(os.getenv("FIRECRAWL_API_KEY", "").strip())
    agentops_ready = bool(os.getenv("AGENTOPS_API_KEY", "").strip())
    uploadthing_ready = bool(os.getenv("UPLOADTHING_TOKEN", "").strip())
    otel_ready = bool(os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip())
    betterstack_ready = bool(os.getenv("BETTER_STACK_SOURCE_TOKEN", "").strip())
    frontend_acceleration_enabled = {
        "million_js": os.getenv("NEXT_PUBLIC_ENABLE_MILLION", "0").strip() == "1",
        "partytown": os.getenv("NEXT_PUBLIC_ENABLE_PARTYTOWN", "0").strip() == "1",
        "zustand": os.getenv("NEXT_PUBLIC_ENABLE_ZUSTAND", "0").strip() == "1",
    }
    api_architecture_selected = {
        "hono": os.getenv("API_BFF_FRAMEWORK", "").strip().lower() == "hono",
        "trpc": os.getenv("API_TRANSPORT", "").strip().lower() == "trpc",
        "drizzle": os.getenv("DATABASE_ORM", "").strip().lower() == "drizzle",
        "zod": os.getenv("API_SCHEMA_VALIDATION", "").strip().lower() == "zod",
    }
    groq_ready = bool(os.getenv("GROQ_API_KEY", "").strip())
    gemini_free_ready = bool(os.getenv("GEMINI_API_KEY", "").strip())
    openrouter_ready = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    ollama_ready = bool(ollama_url)
    free_providers_configured = sum([groq_ready, gemini_free_ready, openrouter_ready, ollama_ready])
    paid_providers_configured = sum([openai_ready, anthropic_ready, cohere_ready, gemini_ready])
    return {
        "free_tier_ai_providers": {
            "note": "Tier 0 — tried before any paid provider. Zero cost, no billing required.",
            "providers": {
                "groq": {
                    "configured": groq_ready,
                    "cost": "FREE",
                    "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it", "llama-3.1-8b-instant"],
                    "limits": "14,400 req/day · 500k tokens/min",
                    "quality_score": 0.84,
                    "speed": "ultra-fast (~280ms)",
                    "setup": "GROQ_API_KEY — free at console.groq.com",
                },
                "gemini_free": {
                    "configured": gemini_free_ready,
                    "cost": "FREE",
                    "models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
                    "limits": "1,500 req/day · 1M token context",
                    "quality_score": 0.85,
                    "speed": "fast (~600ms)",
                    "setup": "GEMINI_API_KEY — free at aistudio.google.com",
                },
                "openrouter": {
                    "configured": openrouter_ready,
                    "cost": "FREE (free-model suffixed routes)",
                    "models": [
                        "meta-llama/llama-3.2-3b-instruct:free",
                        "deepseek/deepseek-r1:free",
                        "mistralai/mistral-7b-instruct:free",
                        "google/gemma-3-1b-it:free",
                    ],
                    "limits": "Rate-limited per free model",
                    "quality_score": 0.75,
                    "speed": "moderate (~500ms)",
                    "setup": "OPENROUTER_API_KEY — free at openrouter.ai",
                },
                "ollama": {
                    "configured": ollama_ready,
                    "cost": "FREE (fully local)",
                    "models": ["llama3.3", "mistral", "gemma2", "phi4", "deepseek-r1"],
                    "limits": "None — runs on your hardware",
                    "quality_score": 0.83,
                    "speed": "hardware-dependent",
                    "setup": "OLLAMA_BASE_URL — install from ollama.com/download",
                },
            },
            "summary": {
                "free_providers_configured": free_providers_configured,
                "free_providers_total": 4,
                "readiness": helper_free_tier_readiness(free_providers_configured),
            },
        },
        "platform_acceleration_best_of": {
            "note": "Deduplicated best integrations requested for speed, reliability, and observability.",
            "delivery_and_edge": {
                "cloudflare": {
                    "configured": cloudflare_ready,
                    "role": "global edge cache, WAF, and CDN acceleration",
                    "env": ["CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ZONE_ID"],
                },
                "vercel": {
                    "configured": vercel_ready,
                    "role": "Next.js edge deployment + analytics",
                    "includes": ["vercel_analytics"],
                    "env": ["VERCEL_TOKEN", "VERCEL_PROJECT_ID", "NEXT_PUBLIC_VERCEL_ANALYTICS_ID"],
                },
                "fly_io": {
                    "configured": flyio_ready,
                    "role": "global FastAPI deployment close to users",
                    "env": ["FLY_API_TOKEN", "FLY_APP_NAME"],
                },
            },
            "data_and_runtime_speed": {
                "upstash": {
                    "configured": upstash_ready,
                    "role": "serverless Redis cache, queue, and rate limit acceleration",
                    "env": ["UPSTASH_REDIS_REST_URL", "UPSTASH_REDIS_REST_TOKEN"],
                },
                "neon": {
                    "configured": neon_ready,
                    "role": "autoscaling serverless Postgres for bursty workloads",
                    "env": ["NEON_DATABASE_URL"],
                },
                "uploadthing": {
                    "configured": uploadthing_ready,
                    "role": "fast direct-to-storage uploads and media ingress",
                    "env": ["UPLOADTHING_TOKEN", "UPLOADTHING_APP_ID"],
                },
            },
            "observability_and_ai_ops": {
                "posthog": {
                    "configured": posthog_ready,
                    "role": "product analytics, feature flags, and session replay",
                },
                "sentry": {
                    "configured": sentry_ready,
                    "role": "error + performance monitoring (dedupes sentry and sentry performance)",
                    "env": ["SENTRY_DSN", "SENTRY_TRACES_SAMPLE_RATE"],
                },
                "langsmith": {
                    "configured": langsmith_ready,
                    "role": "LLM chain debugging and evals",
                    "env": ["LANGSMITH_API_KEY", "LANGCHAIN_TRACING_V2", "LANGCHAIN_PROJECT"],
                },
                "langfuse": {
                    "configured": langfuse_ready,
                    "role": "prompt and generation tracing with cost visibility",
                    "env": ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"],
                },
                "grafana": {
                    "configured": grafana_ready,
                    "role": "metrics dashboards and alerting",
                    "env": ["GRAFANA_URL", "GRAFANA_API_KEY"],
                },
                "open_telemetry": {
                    "configured": otel_ready,
                    "role": "vendor-neutral distributed tracing",
                    "env": ["OTEL_EXPORTER_OTLP_ENDPOINT", "OTEL_SERVICE_NAME"],
                },
                "better_stack": {
                    "configured": betterstack_ready,
                    "role": "logs, uptime, and incident response automation",
                    "env": ["BETTER_STACK_SOURCE_TOKEN"],
                },
                "agentops": {
                    "configured": agentops_ready,
                    "role": "agent execution observability and guardrails",
                    "env": ["AGENTOPS_API_KEY"],
                },
            },
            "ai_data_enrichment": {
                "firecrawl": {
                    "configured": firecrawl_ready,
                    "role": "turn websites into clean AI-ingestion markdown and JSON",
                    "env": ["FIRECRAWL_API_KEY"],
                }
            },
            "frontend_and_api_architecture": {
                "frontend_speed_toggles": {
                    "million_js": {"enabled": frontend_acceleration_enabled["million_js"]},
                    "partytown": {"enabled": frontend_acceleration_enabled["partytown"]},
                    "zustand": {"enabled": frontend_acceleration_enabled["zustand"]},
                },
                "api_stack_choices": {
                    "hono_js": {"enabled": api_architecture_selected["hono"]},
                    "trpc": {"enabled": api_architecture_selected["trpc"]},
                    "drizzle_orm": {"enabled": api_architecture_selected["drizzle"]},
                    "zod": {"enabled": api_architecture_selected["zod"]},
                },
            },
        },
        "frontier_reasoning_and_multi_agent_intelligence": {
            "providers": {
                "openai": {"configured": openai_ready, "role": "strongest general reasoning + tool calling"},
                "anthropic": {"configured": anthropic_ready, "role": "long-context + structured reasoning"},
                "cohere": {"configured": cohere_ready, "role": "enterprise embeddings + RAG"},
            },
            "orchestration": {
                "crewai": {"available": crewai_ready, "role_based_ai_teams": True},
                "langgraph": {"available": langgraph_ready, "persistent_workflows": True},
            },
            "summary": {"paid_providers_configured": paid_providers_configured},
        },
        "long_term_memory_and_knowledge": {
            "vector_memory": {"pinecone": {"configured": pinecone_ready}, "weaviate": {"configured": weaviate_ready}},
            "graph_memory": {"neo4j": {"configured": neo4j_ready, "relationship_reasoning": True}},
            "realtime_memory": {"redis": {"configured": redis_ready}},
            "recommendation": "combine vector + graph memory for higher-context reasoning",
        },
        "multimodal_perception": {
            "providers": {
                "openai_vision_speech": {"configured": openai_ready},
                "google_deepmind_gemini": {"configured": gemini_ready},
                "assemblyai": {"configured": bool(os.getenv("ASSEMBLYAI_API_KEY", "").strip())},
                "runway": {"configured": bool(os.getenv("RUNWAY_API_KEY", "").strip())},
            },
            "enables": [
                "meeting_audio_and_video_analysis",
                "screenshot_and_ui_understanding",
                "automated_content_pipeline_generation",
            ],
        },
        "autonomous_tool_execution_layer": {
            "automation": {
                "n8n": {"enabled": True, "note": "kept as primary automation layer"},
                "zapier": {"available": bool(os.getenv("ZAPIER_WEBHOOK_URL", "").strip())},
                "make": {"available": bool(os.getenv("MAKE_WEBHOOK_URL", "").strip())},
            },
            "durable_workflows": {
                "temporal": {
                    "available": temporal_ready,
                    "free_or_open_source": True,
                    "benefits": ["retries", "state_persistence", "complex_multi_step_automation"],
                }
            },
        },
        "advanced_rag": {
            "frameworks": {
                "llamaindex": {"available": port_module_available._module_available("llama_index")},
                "haystack": {"available": port_module_available._module_available("haystack")},
            },
            "techniques": ["hybrid_search", "query_rewriting", "multi_hop_reasoning", "context_compression"],
        },
        "continuous_learning_and_evaluation": {
            "platforms": {
                "weights_and_biases": {"configured": bool(os.getenv("WANDB_API_KEY", "").strip())},
                "langsmith": {"configured": bool(os.getenv("LANGCHAIN_API_KEY", "").strip())},
                "humanloop": {"configured": bool(os.getenv("HUMANLOOP_API_KEY", "").strip())},
            },
            "enables": ["feedback_loops", "auto_optimization", "task_level_performance_tracking"],
        },
        "guardrails_and_ai_safety": {
            "guardrails_ai": {"available": port_module_available._module_available("guardrails")},
            "rebuff": {"available": port_module_available._module_available("rebuff")},
            "prevents": ["hallucinations", "prompt_injection_attacks", "unsafe_actions"],
        },
        "high_performance_compute_and_scaling": {"clouds": ["aws", "gcp", "azure"], "accelerators": ["nvidia"]},
        "deep_enterprise_integrations": {
            "salesforce": {"configured": bool(os.getenv("SALESFORCE_CLIENT_ID", "").strip())},
            "slack": {"configured": bool(os.getenv("SLACK_BOT_TOKEN", "").strip())},
            "notion": {"configured": bool(os.getenv("NOTION_API_KEY", "").strip())},
            "google_workspace": {"configured": bool(os.getenv("GOOGLE_WORKSPACE_CLIENT_ID", "").strip())},
        },
        "god_like_ingredients": [
            "multi_agent_systems_planner_executor_critic",
            "persistent_memory_across_users_tasks_history",
            "reliable_tool_mastery_and_api_execution",
            "self_improvement_feedback_logs_failures",
            "multimodal_awareness_text_audio_video_ui",
        ],
        "hard_truths": [
            "true_autonomy_requires_tight_constraints",
            "edge_cases_will_break_flows_without_guarded_fallbacks",
            "costs_can_explode_without_quotas_and_budget_controls",
            "reliability_is_the_hardest_problem",
        ],
    }


def helper_merge_env_file_non_destructive(
    existing_content: str, generated_lines: list[str]
) -> tuple[str, dict[str, int]]:
    existing_lines = existing_content.splitlines()
    existing_key_to_index: dict[str, int] = {}
    for index, line in enumerate(existing_lines):
        parsed = helper_split_env_assignment(line)
        if parsed is None:
            continue
        existing_key_to_index[parsed[0]] = index
    updated_existing_empty = 0
    kept_existing_non_empty = 0
    appended_missing = 0
    for raw_line in generated_lines:
        parsed_generated = helper_split_env_assignment(raw_line)
        if parsed_generated is None:
            continue
        key, generated_value = parsed_generated
        existing_index = existing_key_to_index.get(key)
        if existing_index is None:
            existing_lines.append(raw_line)
            existing_key_to_index[key] = len(existing_lines) - 1
            appended_missing += 1
            continue
        current_line = existing_lines[existing_index]
        parsed_current = helper_split_env_assignment(current_line)
        current_value = parsed_current[1] if parsed_current is not None else ""
        if current_value.strip():
            kept_existing_non_empty += 1
            continue
        if generated_value.strip():
            existing_lines[existing_index] = raw_line
            updated_existing_empty += 1
    merged_content = "\n".join(existing_lines).strip()
    if merged_content:
        merged_content += "\n"
    return (
        merged_content,
        {
            "updated_existing_empty": updated_existing_empty,
            "kept_existing_non_empty": kept_existing_non_empty,
            "appended_missing": appended_missing,
        },
    )


def helper_tenant_suspicious_signal(context_runtime: ContextRuntime, tenant_id: str) -> dict[str, Any]:
    return compute_tenant_suspicious_signal(
        tenant_id=tenant_id,
        stripe_events_memory=context_runtime.stripe_events_memory,
        revenue_conversions_memory=context_runtime.revenue_conversions_memory,
        api_usage_audit_memory=context_runtime.api_usage_audit_memory,
        ai_security_usage_memory=context_runtime.ai_security_usage_memory,
    )
