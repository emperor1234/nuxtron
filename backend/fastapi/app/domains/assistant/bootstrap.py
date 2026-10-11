import asyncio
import importlib
import httpx
from .operations.copilot_env_template import helper_embed_texts
from .operations.db_dsn import helper_db_dsn

"""Assistant HTTP composition and legacy import exports."""
from ...domains.ai.brain import AIBrainModelLayer
from ...ira_memory import IRAMemorySystem
from .runtime import ContextRuntime
from .schemas import IRAContext
from .services.reasoning_support import _now_iso
from collections.abc import Callable
from fastapi import APIRouter
from typing import Any
import threading
from .api import (
    ira_status,
    ira_copilot_env_template,
    ira_agent_brain_capabilities,
    ira_chat,
    ira_record_ab_result,
    disable_protection_mode,
)
from .services.reasoning_support import _now_iso as _now_iso
from .services.reasoning_support import _event_epoch as _event_epoch
from .services.reasoning_support import _slugify as _slugify
from .services.reasoning_support import _tokenize_text as _tokenize_text
from .services.reasoning_support import _normalize_vector as _normalize_vector
from .services.reasoning_support import _local_hash_embedding as _local_hash_embedding
from .services.reasoning_support import _cosine_similarity as _cosine_similarity
from .services.reasoning_support import _lexical_overlap_score as _lexical_overlap_score
from .services.reasoning_support import _chunk_text as _chunk_text
from .services.reasoning_support import _module_available as _module_available
from .services.reasoning_support import _normalize_brain_provider as _normalize_brain_provider
from .services.reasoning_support import _normalize_chat_provider_preference as _normalize_chat_provider_preference
from .services.reasoning_support import _extract_chat_provider_routing as _extract_chat_provider_routing
from .services.reasoning_support import _build_chat_reasoning_prompt as _build_chat_reasoning_prompt
from .services.reasoning_support import _contains_risk_marker as _contains_risk_marker
from .services.reasoning_support import compute_tenant_revenue_snapshot as compute_tenant_revenue_snapshot
from .services.reasoning_support import compute_tenant_suspicious_signal as compute_tenant_suspicious_signal
from .services.reasoning_support import _watchdog_activation_reason as _watchdog_activation_reason
from .services.reasoning_support import _activate_watchdog_protection as _activate_watchdog_protection
from .services.run_ira_watchdog import run_ira_watchdog as run_ira_watchdog
from .schemas import IRAFinanceSampleRequest as IRAFinanceSampleRequest
from .schemas import IRAContext as IRAContext
from .schemas import IRAAdviceRequest as IRAAdviceRequest
from .schemas import IRAFrontierEnvTemplateApplyRequest as IRAFrontierEnvTemplateApplyRequest
from .schemas import IRAAutonomyUpdateRequest as IRAAutonomyUpdateRequest
from .schemas import IRATrainingPipelineRequest as IRATrainingPipelineRequest
from .schemas import IRAFeedbackRequest as IRAFeedbackRequest
from .schemas import IRACrmGovernanceUpdateRequest as IRACrmGovernanceUpdateRequest
from .schemas import IRARetrievalQueryRequest as IRARetrievalQueryRequest
from .schemas import IRAActionRequest as IRAActionRequest
from .schemas import IRAKnowledgeDocumentRequest as IRAKnowledgeDocumentRequest
from .schemas import IRAMessageRequest as IRAMessageRequest
from .schemas import IRAStructuredMemoryUpsertRequest as IRAStructuredMemoryUpsertRequest
from .schemas import IRACopilotPlanRequest as IRACopilotPlanRequest
from .schemas import IRAConnectorUpsertRequest as IRAConnectorUpsertRequest
from .schemas import IRABatchActionsRequest as IRABatchActionsRequest
from .schemas import IRAAbTestRecordRequest as IRAAbTestRecordRequest
from .schemas import IRAAgentPreferenceUpdateRequest as IRAAgentPreferenceUpdateRequest
from .schemas import IRAFineTuningJobRequest as IRAFineTuningJobRequest
from .schemas import IRABatchActionItem as IRABatchActionItem
from .schemas import IRAChatActionPlan as IRAChatActionPlan
from .schemas import IRAFrontierPlanRequest as IRAFrontierPlanRequest
from .schemas import IRAAgentRunRequest as IRAAgentRunRequest
from .schemas import IRAAgentBrainReasonRequest as IRAAgentBrainReasonRequest
from .schemas import IRAAbTestCreateRequest as IRAAbTestCreateRequest
from .constants import AuthDep as AuthDep
from .constants import AUTONOMY_DISABLED_DETAIL as AUTONOMY_DISABLED_DETAIL
from .constants import HUMAN_VALIDATION_COMMAND_MARKERS as HUMAN_VALIDATION_COMMAND_MARKERS
from .constants import CRM_DEFAULT_OWNERSHIP as CRM_DEFAULT_OWNERSHIP
from .constants import LOCAL_EMBEDDING_DIMENSIONS as LOCAL_EMBEDDING_DIMENSIONS
from .constants import HIGH_IMPACT_TARGETS as HIGH_IMPACT_TARGETS
from .constants import IRA_PLAYBOOK_DECISION_TREE as IRA_PLAYBOOK_DECISION_TREE
from .constants import APPLICATION_JSON as APPLICATION_JSON
from .constants import TOKEN_PATTERN as TOKEN_PATTERN
from .constants import EXPLICIT_APPROVAL_COMMAND_MARKERS as EXPLICIT_APPROVAL_COMMAND_MARKERS
from .constants import DEFAULT_BLOCKED_ACTIONS as DEFAULT_BLOCKED_ACTIONS
from .constants import CONNECTOR_CHANNELS as CONNECTOR_CHANNELS
from .constants import CRM_FEATURE_KEYS as CRM_FEATURE_KEYS
from ...deps import AuthContext
from ...deps import require_auth
from ...ira_agent import IRAAgentRuntime
from ...ira_connector_integration import dispatch_via_ira_connector


def create_ira_router(*, enforce_rate_limit: Callable[[str, int, int], None], ctx: IRAContext) -> APIRouter:
    router = APIRouter(prefix="/ira", tags=["ira"])
    lock = threading.Lock()
    audit_log_memory = ctx.audit_log_memory
    tickets_memory = ctx.tickets_memory
    chatbot_conversations_memory = ctx.chatbot_conversations_memory
    credit_ledger_memory = ctx.credit_ledger_memory
    invoices_memory = ctx.invoices_memory
    stripe_events_memory = ctx.stripe_events_memory
    revenue_conversions_memory = ctx.revenue_conversions_memory
    api_usage_audit_memory = ctx.api_usage_audit_memory
    ai_security_usage_memory = ctx.ai_security_usage_memory
    slack_messages_memory = ctx.slack_messages_memory
    resend_messages_memory = ctx.resend_messages_memory
    twilio_messages_memory = ctx.twilio_messages_memory
    ira_events_memory = ctx.ira_events_memory
    ira_sessions_memory = ctx.ira_sessions_memory
    ira_controls_memory = ctx.ira_controls_memory
    ira_connectors_memory = ctx.ira_connectors_memory
    ira_ml_knowledge_memory = ctx.ira_ml_knowledge_memory
    ira_ml_jobs_memory = ctx.ira_ml_jobs_memory
    ira_ml_models_memory = ctx.ira_ml_models_memory
    ira_structured_memory = ctx.ira_structured_memory
    ira_action_snapshots_memory = ctx.ira_action_snapshots_memory
    ira_cost_ledger_memory = ctx.ira_cost_ledger_memory
    ira_ab_tests_memory = ctx.ira_ab_tests_memory
    ira_performance_log_memory = ctx.ira_performance_log_memory
    crm_governance_table_init_lock = threading.Lock()
    crm_governance_table_ready = False
    sentence_transformer_cache: dict[str, Any] = {}
    _ROLE_ALLOWED_TARGETS: dict[str, set[str]] = {
        "super_admin": {"customers", "admin", "email", "chats", "billing", "credits", "security", "customer_support"},
        "admin": {"customers", "admin", "email", "chats", "customer_support"},
        "operator": {"customers", "chats", "customer_support"},
        "customer": set(),
    }
    _ROLE_PRECEDENCE: tuple[str, ...] = ("super_admin", "admin", "operator", "customer")
    memory_system = IRAMemorySystem(
        db_dsn_fn=lambda: helper_db_dsn(),
        now_iso_fn=_now_iso,
        short_term_store=ira_sessions_memory,
        long_term_store=ira_ml_knowledge_memory,
        structured_store=ira_structured_memory,
        embed_texts=lambda *args, **kwargs: helper_embed_texts(runtime, *args, **kwargs),
    )
    ai_brain = AIBrainModelLayer(now_iso_fn=_now_iso)
    runtime = ContextRuntime(
        _ROLE_ALLOWED_TARGETS=_ROLE_ALLOWED_TARGETS,
        _ROLE_PRECEDENCE=_ROLE_PRECEDENCE,
        ai_brain=ai_brain,
        ai_security_usage_memory=ai_security_usage_memory,
        api_usage_audit_memory=api_usage_audit_memory,
        audit_log_memory=audit_log_memory,
        chatbot_conversations_memory=chatbot_conversations_memory,
        credit_ledger_memory=credit_ledger_memory,
        crm_governance_table_init_lock=crm_governance_table_init_lock,
        crm_governance_table_ready=crm_governance_table_ready,
        enforce_rate_limit=enforce_rate_limit,
        invoices_memory=invoices_memory,
        ira_ab_tests_memory=ira_ab_tests_memory,
        ira_action_snapshots_memory=ira_action_snapshots_memory,
        ira_connectors_memory=ira_connectors_memory,
        ira_controls_memory=ira_controls_memory,
        ira_cost_ledger_memory=ira_cost_ledger_memory,
        ira_events_memory=ira_events_memory,
        ira_ml_jobs_memory=ira_ml_jobs_memory,
        ira_ml_knowledge_memory=ira_ml_knowledge_memory,
        ira_ml_models_memory=ira_ml_models_memory,
        ira_performance_log_memory=ira_performance_log_memory,
        ira_sessions_memory=ira_sessions_memory,
        lock=lock,
        memory_system=memory_system,
        resend_messages_memory=resend_messages_memory,
        revenue_conversions_memory=revenue_conversions_memory,
        sentence_transformer_cache=sentence_transformer_cache,
        slack_messages_memory=slack_messages_memory,
        stripe_events_memory=stripe_events_memory,
        tickets_memory=tickets_memory,
        twilio_messages_memory=twilio_messages_memory,
    )
    ira_status.register(router, runtime)
    ira_copilot_env_template.register(router, runtime)
    ira_agent_brain_capabilities.register(router, runtime)
    ira_chat.register(router, runtime)
    ira_record_ab_result.register(router, runtime)
    disable_protection_mode.register(router, runtime)
    return router
