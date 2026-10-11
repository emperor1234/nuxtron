"""Assistant explicit runtime dependencies."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class ContextRuntime:
    """Adapters and state owned by exactly one application instance."""

    _ROLE_ALLOWED_TARGETS: dict[str, set[str]]
    _ROLE_PRECEDENCE: tuple[str, ...]
    ai_brain: Any
    ai_security_usage_memory: Any
    api_usage_audit_memory: Any
    audit_log_memory: Any
    chatbot_conversations_memory: Any
    credit_ledger_memory: Any
    crm_governance_table_init_lock: Any
    crm_governance_table_ready: Any
    enforce_rate_limit: Callable[[str, int, int], None]
    invoices_memory: Any
    ira_ab_tests_memory: Any
    ira_action_snapshots_memory: Any
    ira_connectors_memory: Any
    ira_controls_memory: Any
    ira_cost_ledger_memory: Any
    ira_events_memory: Any
    ira_ml_jobs_memory: Any
    ira_ml_knowledge_memory: Any
    ira_ml_models_memory: Any
    ira_performance_log_memory: Any
    ira_sessions_memory: Any
    lock: Any
    memory_system: Any
    resend_messages_memory: Any
    revenue_conversions_memory: Any
    sentence_transformer_cache: dict[str, Any]
    slack_messages_memory: Any
    stripe_events_memory: Any
    tickets_memory: Any
    twilio_messages_memory: Any
