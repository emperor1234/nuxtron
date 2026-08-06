# pyright: reportUnusedFunction=false, reportUnusedImport=false

import asyncio
import hashlib
import hmac
import importlib
import importlib.util
import math
import os
import re
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, cast

import httpx
import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from ..ai_brain import AIBrainModelLayer
from ..deps import AuthContext, require_auth
from ..ira_agent import IRAAgentRuntime
from ..ira_connector_integration import dispatch_via_ira_connector
from ..ira_memory import IRAMemorySystem

AuthDep = Annotated[AuthContext, Depends(require_auth)]

HIGH_IMPACT_TARGETS = {'admin', 'billing', 'credits', 'payouts', 'security'}
DEFAULT_BLOCKED_ACTIONS = ['billing_change', 'credit_spend', 'external_transfer']
CONNECTOR_CHANNELS: tuple[str, ...] = ('chat', 'email', 'ticket', 'webhook', 'admin', 'customer_support')
EXPLICIT_APPROVAL_COMMAND_MARKERS = ('billing_change', 'credit_spend', 'external_transfer', 'refund_force')
HUMAN_VALIDATION_COMMAND_MARKERS = ('compliance', 'bulk', 'ticket', 'campaign', 'broadcast')
TOKEN_PATTERN = re.compile(r'\w{2,}')
LOCAL_EMBEDDING_DIMENSIONS = 64
APPLICATION_JSON = 'application/json'
CRM_FEATURE_KEYS: tuple[str, ...] = (
    'multi_tenancy',
    'low_code_objects',
    'sales_pipeline_and_erp_adjacent',
    'cross_platform_workflow_orchestration',
    'ecosystem_modules',
)
CRM_DEFAULT_OWNERSHIP: dict[str, str] = {
    'multi_tenancy': 'corteza',
    'low_code_objects': 'corteza',
    'sales_pipeline_and_erp_adjacent': 'odoo',
    'cross_platform_workflow_orchestration': 'corteza',
    'ecosystem_modules': 'odoo',
}
AUTONOMY_DISABLED_DETAIL = 'IRA autonomy is disabled for this tenant.'

IRA_PLAYBOOK_DECISION_TREE: tuple[dict[str, str], ...] = (
    {
        'question': 'Do you have paying users?',
        'if_yes': 'Optimize retention and expansion; do not pause shipping.',
        'if_no': 'Refine positioning and run customer interviews before adding scope.',
    },
    {
        'question': 'Do users reach value in first 7 days?',
        'if_yes': 'Scale acquisition channels and agency partner activation.',
        'if_no': 'Improve onboarding and guided first outcomes in the control center.',
    },
    {
        'question': 'Is autonomy healthy (risk + finance + connectors)?',
        'if_yes': 'Expand automation depth safely with guarded approvals.',
        'if_no': 'Stabilize protections and connector reliability before expansion.',
    },
    {
        'question': 'Have key channels remained available?',
        'if_yes': 'Increase cadence and campaign throughput.',
        'if_no': 'Use fallback channels and activate resilience playbooks.',
    },
)


class IRAMessageRequest(BaseModel):
    role: Literal['customer', 'admin', 'operator'] = 'customer'
    channel: Literal['chat', 'email', 'ticket', 'webhook'] = 'chat'
    message: str = Field(min_length=1, max_length=4000)
    context: dict[str, Any] = Field(default_factory=dict)


class IRAActionRequest(BaseModel):
    target: Literal['customers', 'admin', 'email', 'chats', 'billing', 'credits', 'security', 'customer_support']
    command: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    dashboard_scope: Literal['super_admin_dashboard'] = 'super_admin_dashboard'
    actor_role: Literal['super_admin', 'admin', 'operator', 'customer'] = 'super_admin'
    actor_attributes: dict[str, Any] = Field(default_factory=dict)
    user_consent: bool = False
    consent_reference: str = Field(default='', max_length=160)
    risk_analysis_approved: bool = False
    human_validation_approved: bool = False
    explicit_approval: bool = False
    dry_run: bool = True


class IRAAutonomyUpdateRequest(BaseModel):
    autonomy_enabled: bool = True
    allow_high_impact_actions: bool = False
    min_profit_margin_pct: float = Field(default=70.0, ge=0.0, le=100.0)
    suspicious_signal_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    require_super_admin: bool = True
    max_dispute_auto_resolution_gbp: float = Field(default=50.0, ge=0.0, le=50.0)
    strict_policy_lock: bool = True
    policy_change_human_validation: bool = False


class IRAFeedbackRequest(BaseModel):
    category: Literal['quality', 'safety', 'usability', 'revenue', 'feature_adoption'] = 'quality'
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default='', max_length=4000)
    action_ref: str = Field(default='', max_length=120)
    actor_role: Literal['super_admin', 'admin', 'operator', 'customer'] = 'customer'


class IRAAdviceRequest(BaseModel):
    objective: str = Field(default='growth', min_length=1, max_length=160)
    horizon_days: int = Field(default=30, ge=1, le=365)
    include_feature_adoption: bool = True


class IRACrmGovernanceUpdateRequest(BaseModel):
    feature: Literal[
        'multi_tenancy',
        'low_code_objects',
        'sales_pipeline_and_erp_adjacent',
        'cross_platform_workflow_orchestration',
        'ecosystem_modules',
    ]
    owner: Literal['corteza', 'odoo']
    disable_duplicate_in_secondary: bool = True
    policy_change_human_validation: bool = False
    notes: str = Field(default='', max_length=500)


class IRAFinanceSampleRequest(BaseModel):
    revenue: float = Field(ge=0.0)
    cogs: float = Field(default=0.0, ge=0.0)
    credits_cost: float = Field(default=0.0, ge=0.0)
    suspicious_signal_score: float = Field(default=0.0, ge=0.0, le=1.0)
    note: str = Field(default='', max_length=300)


class IRAConnectorUpsertRequest(BaseModel):
    channel: Literal['chat', 'email', 'ticket', 'webhook', 'admin', 'customer_support']
    enabled: bool = True
    provider: str = Field(default='internal', max_length=80)
    config: dict[str, Any] = Field(default_factory=dict)


class IRAKnowledgeDocumentRequest(BaseModel):
    document_id: str = Field(default='', max_length=120)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=200000)
    source: str = Field(default='internal', max_length=240)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_size_chars: int = Field(default=900, ge=200, le=4000)
    chunk_overlap_chars: int = Field(default=120, ge=0, le=500)


class IRARetrievalQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=12)
    min_score: float = Field(default=0.12, ge=0.0, le=1.0)


class IRAFineTuningJobRequest(BaseModel):
    provider: Literal['openai', 'custom_http'] = 'openai'
    base_model: str = Field(min_length=1, max_length=160)
    training_file_id: str = Field(default='', max_length=160)
    validation_file_id: str = Field(default='', max_length=160)
    suffix: str = Field(default='', max_length=64)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    endpoint_url: str = Field(default='', max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class IRATrainingPipelineRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    objective: str = Field(min_length=1, max_length=500)
    pipeline_type: Literal['rag', 'fine_tuning', 'embedding', 'custom'] = 'rag'
    framework: Literal['auto', 'pytorch', 'tensorflow', 'sentence_transformers'] = 'auto'
    dataset_document_ids: list[str] = Field(default_factory=list)
    model_name: str = Field(default='', max_length=160)
    epochs: int = Field(default=3, ge=1, le=100)
    learning_rate: float = Field(default=0.0001, gt=0.0, le=1.0)
    batch_size: int = Field(default=16, ge=1, le=2048)
    dry_run: bool = True


class IRAStructuredMemoryUpsertRequest(BaseModel):
    memory_type: Literal['user_profile', 'task', 'preference', 'workflow_state'] = 'user_profile'
    memory_key: str = Field(min_length=1, max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)


class IRAAgentRunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)
    framework: Literal['auto', 'langchain', 'semantic_kernel', 'autogpt', 'crewai', 'native_secure_loop'] = 'auto'
    max_iterations: int = Field(default=4, ge=1, le=12)
    dry_run: bool = True
    memory_key: str = Field(default='', max_length=160)


class IRABatchActionItem(BaseModel):
    target: Literal['customers', 'admin', 'email', 'chats', 'billing', 'credits', 'security', 'customer_support']
    command: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class IRABatchActionsRequest(BaseModel):
    actions: list[IRABatchActionItem] = Field(min_length=1, max_length=100)
    dry_run: bool = True  # global override — if True, forces all items to dry_run
    consent_reference: str = Field(default='', max_length=160)
    human_validation_approved: bool = False
    risk_analysis_approved: bool = False


class IRAAbTestCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=500)
    variants: list[str] = Field(min_length=2, max_length=10)  # e.g. ['variant_a', 'variant_b']
    metric: str = Field(default='conversion_rate', max_length=80)  # metric being measured
    traffic_split: list[float] = Field(default_factory=list)  # must sum to 1.0, length matches variants
    target_scope: str = Field(default='all', max_length=80)  # 'all', 'seo', 'ads', 'support', etc.


class IRAAbTestRecordRequest(BaseModel):
    test_id: int
    variant: str = Field(min_length=1, max_length=80)
    outcome: Literal['success', 'failure', 'neutral'] = 'neutral'
    value: float = Field(default=1.0, ge=0.0)  # e.g. conversion value, score
    metadata: dict[str, Any] = Field(default_factory=dict)


class IRAAgentPreferenceUpdateRequest(BaseModel):
    auto_framework: Literal['auto', 'langchain', 'semantic_kernel', 'native_secure_loop'] = 'auto'


class IRAAgentBrainReasonRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    provider: Literal['auto', 'openai', 'anthropic', 'google_deepmind', 'deepseek', 'llama', 'mistral'] = 'auto'
    tools: list[Any] = Field(default_factory=list)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_tokens: int = Field(default=800, ge=64, le=4096)


class IRAFrontierPlanRequest(BaseModel):
    objective: str = Field(default='Build an AI workforce with reliable autonomous execution.', min_length=8, max_length=600)
    priority: Literal['reliability', 'cost', 'speed'] = 'reliability'
    include_free_open_source_only: bool = False
    require_multimodal: bool = True
    require_graph_memory: bool = True
    create_execution_tasks: bool = True


class IRAFrontierEnvTemplateApplyRequest(BaseModel):
    target_file: str = Field(default='.env.frontier.draft', min_length=1, max_length=80)
    mode: Literal['overwrite', 'merge_non_destructive', 'merge_and_backup'] = 'overwrite'


class IRACopilotPlanRequest(BaseModel):
    objective: str = Field(default='Integrate GitHub Copilot chat and agent workflows into the IRA platform.', min_length=8, max_length=600)
    priority: Literal['reliability', 'cost', 'speed'] = 'reliability'
    include_enterprise_controls: bool = True
    include_telemetry: bool = True
    include_agent_mode: bool = True


class IRAChatActionPlan(BaseModel):
    intent: str
    domain: str
    requires_human_validation: bool
    requires_explicit_approval: bool
    recommended_actions: list[dict[str, Any]]


@dataclass(frozen=True)
class IRAContext:
    audit_log_memory: list[dict[str, Any]]
    tickets_memory: list[dict[str, Any]]
    chatbot_conversations_memory: list[dict[str, Any]]
    credit_ledger_memory: list[dict[str, Any]]
    invoices_memory: list[dict[str, Any]]
    stripe_events_memory: list[dict[str, Any]]
    revenue_conversions_memory: list[dict[str, Any]]
    api_usage_audit_memory: list[dict[str, Any]]
    ai_security_usage_memory: list[dict[str, Any]]
    slack_messages_memory: list[dict[str, Any]]
    resend_messages_memory: list[dict[str, Any]]
    twilio_messages_memory: list[dict[str, Any]]
    ira_events_memory: list[dict[str, Any]]
    ira_sessions_memory: list[dict[str, Any]]
    ira_controls_memory: list[dict[str, Any]]
    ira_connectors_memory: list[dict[str, Any]]
    ira_ml_knowledge_memory: list[dict[str, Any]]
    ira_ml_jobs_memory: list[dict[str, Any]]
    ira_ml_models_memory: list[dict[str, Any]]
    ira_structured_memory: list[dict[str, Any]]
    ira_action_snapshots_memory: list[dict[str, Any]]
    ira_cost_ledger_memory: list[dict[str, Any]]
    ira_ab_tests_memory: list[dict[str, Any]]
    ira_performance_log_memory: list[dict[str, Any]]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _event_epoch(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        normalized = value.replace('Z', '+00:00') if value.endswith('Z') else value
        try:
            return int(datetime.fromisoformat(normalized).timestamp())
        except ValueError:
            return 0
    return 0


def _slugify(value: str, *, fallback: str) -> str:
    lowered = re.sub(r'[^a-zA-Z0-9]+', '-', value.strip().lower()).strip('-')
    return lowered[:80] or fallback


def _tokenize_text(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(value)]


def _normalize_vector(values: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude <= 0:
        return values
    return [round(value / magnitude, 8) for value in values]


def _local_hash_embedding(value: str, *, dimensions: int = LOCAL_EMBEDDING_DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    for token in _tokenize_text(value):
        digest = hashlib.sha256(token.encode('utf-8')).digest()
        index = int.from_bytes(digest[:4], byteorder='big') % dimensions
        direction = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + (digest[5] / 255.0)
        vector[index] += direction * weight
    return _normalize_vector(vector)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return max(-1.0, min(1.0, round(sum(a * b for a, b in zip(left, right, strict=False)), 6)))


def _lexical_overlap_score(query_tokens: list[str], candidate_tokens: list[str]) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0
    query_set = set(query_tokens)
    candidate_set = set(candidate_tokens)
    overlap = len(query_set & candidate_set)
    return round(overlap / max(1, len(query_set)), 6)


def _chunk_text(value: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    normalized = ' '.join(value.split())
    if len(normalized) <= chunk_size:
        return [normalized]

    step = max(1, chunk_size - chunk_overlap)
    chunks: list[str] = []
    index = 0
    while index < len(normalized):
        chunk = normalized[index:index + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        index += step
    return chunks or [normalized]


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _normalize_brain_provider(value: str) -> Literal['auto', 'openai', 'anthropic', 'google_deepmind', 'deepseek', 'llama', 'mistral']:
    lowered = value.strip().lower()
    if lowered in {'openai', 'anthropic', 'google_deepmind', 'deepseek', 'llama', 'mistral'}:
        return cast(Literal['openai', 'anthropic', 'google_deepmind', 'deepseek', 'llama', 'mistral'], lowered)
    return 'auto'


def _normalize_chat_provider_preference(value: str) -> str:
    # Canonical alias families are intentionally broad and are validated by
    # test_normalize_chat_provider_preference_alias_matrix in test_ira_router.py.
    # - OpenAI family: openai/chatgpt/gpt*/azure-openai variants
    # - Anthropic family: anthropic/claude variants
    # - Internal/auto keep guarded defaults
    lowered = value.strip().lower()
    if lowered in {'', 'auto', 'default'}:
        return 'auto'
    if lowered in {'internal', 'built_in', 'builtin', 'rule_based'}:
        return 'internal'
    if (
        lowered in {'openai', 'chatgpt', 'azure-openai', 'azure_openai'}
        or lowered.startswith('gpt')
        or 'openai' in lowered
        or 'chatgpt' in lowered
        or 'azureopenai' in lowered
        or 'azure-openai' in lowered
        or 'azure_openai' in lowered
    ):
        return 'openai'
    if (
        lowered in {'anthropic', 'claude', 'claudebot'}
        or lowered.startswith('claude')
        or 'anthropic' in lowered
        or 'claude' in lowered
    ):
        return 'anthropic'
    return lowered


def _extract_chat_provider_routing(context: dict[str, Any]) -> dict[str, Any]:
    llm_routing = cast(dict[str, Any], context.get('llm_routing') or {}) if isinstance(context.get('llm_routing'), dict) else {}
    requested = _normalize_chat_provider_preference(str(llm_routing.get('preferred_provider', 'auto') or 'auto'))
    brain_provider = _normalize_brain_provider(requested)
    return {
        'requested_provider': requested,
        'brain_provider': None if requested in {'auto', 'internal'} or brain_provider == 'auto' else brain_provider,
        'custom_provider_label': str(llm_routing.get('custom_provider_label', '') or '').strip(),
        'requested_external_provider': bool(llm_routing.get('requested_external_provider', False)),
    }


def _build_chat_reasoning_prompt(
    *,
    role: str,
    channel: str,
    message: str,
    intent: str,
    domain: str,
    risk: dict[str, Any],
    action_plan: IRAChatActionPlan,
    knowledge_hits: list[dict[str, Any]],
    recent_history: list[dict[str, Any]],
) -> str:
    knowledge_lines = [
        f"- {str(hit.get('title', 'Knowledge')).strip()}: {str(hit.get('content', '')).strip()[:180]}"
        for hit in knowledge_hits[:3]
    ]
    history_lines = [
        f"- {str(item.get('role', 'unknown'))}: {str(item.get('content', '')).strip()[:160]}"
        for item in recent_history[-4:]
        if str(item.get('content', '')).strip()
    ]
    action_lines = [
        f"- {str(item.get('label', item.get('action', 'step'))).strip()}"
        for item in action_plan.recommended_actions[:5]
    ]
    risk_level = str(risk.get('risk_level', 'low')).strip() or 'low'

    return (
        'You are IRA, a guarded autonomous operations copilot for Nuxtron. '
        'Respond concisely, stay operationally useful, avoid inventing actions that bypass approvals, '
        'and mention approval or human validation when the supplied risk/action plan requires it.\n\n'
        f'Role: {role}\n'
        f'Channel: {channel}\n'
        f'User message: {message.strip()}\n'
        f'Intent: {intent}\n'
        f'Domain: {domain}\n'
        f'Risk level: {risk_level}\n'
        f'Requires human validation: {action_plan.requires_human_validation}\n'
        f'Requires explicit approval: {action_plan.requires_explicit_approval}\n\n'
        'Recommended actions:\n'
        f"{chr(10).join(action_lines) if action_lines else '- No recommended actions generated.'}\n\n"
        'Knowledge hits:\n'
        f"{chr(10).join(knowledge_lines) if knowledge_lines else '- No grounded knowledge hits available.'}\n\n"
        'Recent conversation history:\n'
        f"{chr(10).join(history_lines) if history_lines else '- No recent history available.'}\n\n"
        'Return a single end-user-facing answer in plain text.'
    )


def _contains_risk_marker(value: object, markers: tuple[str, ...]) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.strip().lower()
    return any(marker in lowered for marker in markers)


def compute_tenant_revenue_snapshot(
    *,
    tenant_id: str,
    invoices_memory: list[dict[str, Any]],
    credit_ledger_memory: list[dict[str, Any]],
) -> dict[str, float]:
    revenue = 0.0
    for inv in invoices_memory:
        if inv.get('tenant_id') != tenant_id:
            continue
        if str(inv.get('status', '')).lower() not in {'paid', 'settled'}:
            continue
        revenue += float(inv.get('amount', 0.0) or 0.0)

    credits_granted = sum(
        max(0, int(entry.get('amount', 0) or 0))
        for entry in credit_ledger_memory
        if entry.get('tenant_id') == tenant_id
    )
    credits_cost = round(credits_granted * 0.002, 2)
    estimated_cogs = round(revenue * 0.2, 2)
    total_cost = round(estimated_cogs + credits_cost, 2)
    profit_margin_pct = 0.0 if revenue <= 0 else round(((revenue - total_cost) / revenue) * 100.0, 2)
    return {
        'revenue': round(revenue, 2),
        'estimated_cogs': estimated_cogs,
        'credits_cost': credits_cost,
        'total_cost': total_cost,
        'profit_margin_pct': profit_margin_pct,
    }


def compute_tenant_suspicious_signal(
    *,
    tenant_id: str,
    stripe_events_memory: list[dict[str, Any]],
    revenue_conversions_memory: list[dict[str, Any]],
    api_usage_audit_memory: list[dict[str, Any]],
    ai_security_usage_memory: list[dict[str, Any]],
) -> dict[str, Any]:
    now_ts = int(datetime.now(UTC).timestamp())
    api_window_seconds = int(os.getenv('IRA_RISK_API_WINDOW_SECONDS', '900'))
    payment_window_seconds = int(os.getenv('IRA_RISK_PAYMENT_WINDOW_SECONDS', '86400'))
    ai_window_seconds = int(os.getenv('IRA_RISK_AI_WINDOW_SECONDS', '3600'))
    api_threshold = max(1, int(os.getenv('IRA_RISK_API_BURST_THRESHOLD', '250')))
    ai_cost_threshold = max(0.1, float(os.getenv('IRA_RISK_AI_COST_THRESHOLD', '25.0')))

    recent_api = [
        item for item in api_usage_audit_memory
        if item.get('tenant_id') == tenant_id and _event_epoch(item.get('timestamp', 0)) >= now_ts - api_window_seconds
    ]
    recent_payments = [
        item for item in stripe_events_memory
        if item.get('tenant_id') == tenant_id and _event_epoch(item.get('created_at')) >= now_ts - payment_window_seconds
    ]
    recent_conversions = [
        item for item in revenue_conversions_memory
        if item.get('tenant_id') == tenant_id and _event_epoch(item.get('received_at') or item.get('created_at')) >= now_ts - payment_window_seconds
    ]
    recent_ai_usage = [
        item for item in ai_security_usage_memory
        if item.get('tenant_id') == tenant_id and _event_epoch(item.get('timestamp', 0)) >= now_ts - ai_window_seconds
    ]

    payment_failures = [
        item for item in recent_payments
        if _contains_risk_marker(item.get('event_type') or item.get('type'), ('fail', 'refund', 'chargeback', 'dispute'))
        or _contains_risk_marker(item.get('status'), ('failed', 'refunded', 'disputed'))
    ]
    api_score = min(1.0, len(recent_api) / api_threshold)
    ai_cost_total = round(sum(float(item.get('estimated_cost', 0.0) or 0.0) for item in recent_ai_usage), 4)
    ai_score = min(1.0, ai_cost_total / ai_cost_threshold)
    payment_denominator = max(1, len(recent_conversions) + len(payment_failures))
    payment_score = min(1.0, len(payment_failures) / payment_denominator)

    reasons: list[str] = []
    if api_score >= 0.8:
        reasons.append('api_burst_detected')
    if payment_score >= 0.5:
        reasons.append('payment_failure_ratio_high')
    if ai_score >= 0.8:
        reasons.append('ai_cost_burn_high')
    if not recent_conversions and payment_failures:
        reasons.append('payments_failing_without_conversions')

    score = round((api_score * 0.35) + (payment_score * 0.4) + (ai_score * 0.25), 4)
    return {
        'score': score,
        'components': {
            'api_burst_score': round(api_score, 4),
            'payment_failure_score': round(payment_score, 4),
            'ai_cost_burn_score': round(ai_score, 4),
        },
        'metrics': {
            'api_requests_window': len(recent_api),
            'payment_failures_window': len(payment_failures),
            'conversion_count_window': len(recent_conversions),
            'ai_cost_window': ai_cost_total,
        },
        'reasons': reasons,
    }


def _watchdog_activation_reason(control: dict[str, Any], snapshot: dict[str, float], suspicious_signal: dict[str, Any]) -> str | None:
    min_margin = float(control.get('min_profit_margin_pct', 70.0))
    if float(snapshot.get('profit_margin_pct', 0.0)) < min_margin:
        return 'profit_below_target'
    if float(suspicious_signal.get('score', 0.0)) >= float(control.get('suspicious_signal_threshold', 0.75)):
        return 'suspicious_signal'
    return None


def _activate_watchdog_protection(
    *,
    tenant_id: str,
    control: dict[str, Any],
    snapshot: dict[str, float],
    suspicious_signal: dict[str, Any],
    reason: str,
    ira_events_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> None:
    control['protection_mode'] = True
    control['blocked_actions'] = list(DEFAULT_BLOCKED_ACTIONS)
    control['updated_at'] = _now_iso()
    audit_log_memory.append({
        'id': len(audit_log_memory) + 1,
        'tenant_id': tenant_id,
        'action': 'ira_watchdog_protection_mode_activated',
        'source': 'ira-watchdog',
        'metadata': {
            'profit_margin_pct': snapshot.get('profit_margin_pct', 0.0),
            'suspicious_signal_score': suspicious_signal.get('score', 0.0),
            'reason': reason,
        },
        'created_at': _now_iso(),
    })
    ira_events_memory.append({
        'id': len(ira_events_memory) + 1,
        'tenant_id': tenant_id,
        'event_type': 'watchdog_protection_mode_activated',
        'payload': {
            'reason': reason,
            'profit_margin_pct': snapshot.get('profit_margin_pct', 0.0),
            'suspicious_signal': suspicious_signal,
            'blocked_actions': control['blocked_actions'],
        },
        'created_at': _now_iso(),
    })


async def run_ira_watchdog(
    stop_event: asyncio.Event,
    *,
    ira_controls_memory: list[dict[str, Any]],
    ira_events_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
    invoices_memory: list[dict[str, Any]],
    credit_ledger_memory: list[dict[str, Any]],
    stripe_events_memory: list[dict[str, Any]],
    revenue_conversions_memory: list[dict[str, Any]],
    api_usage_audit_memory: list[dict[str, Any]],
    ai_security_usage_memory: list[dict[str, Any]],
) -> None:
    interval = max(10, int(os.getenv('IRA_WATCHDOG_INTERVAL_SECONDS', '60')))
    while not stop_event.is_set():
        for control in ira_controls_memory:
            tenant_id = str(control.get('tenant_id', '')).strip()
            if not tenant_id or not bool(control.get('autonomy_enabled', True)):
                continue
            snapshot = compute_tenant_revenue_snapshot(
                tenant_id=tenant_id,
                invoices_memory=invoices_memory,
                credit_ledger_memory=credit_ledger_memory,
            )
            suspicious_signal = compute_tenant_suspicious_signal(
                tenant_id=tenant_id,
                stripe_events_memory=stripe_events_memory,
                revenue_conversions_memory=revenue_conversions_memory,
                api_usage_audit_memory=api_usage_audit_memory,
                ai_security_usage_memory=ai_security_usage_memory,
            )
            reason = _watchdog_activation_reason(control, snapshot, suspicious_signal)
            if reason is not None and not bool(control.get('protection_mode', False)):
                _activate_watchdog_protection(
                    tenant_id=tenant_id,
                    control=control,
                    snapshot=snapshot,
                    suspicious_signal=suspicious_signal,
                    reason=reason,
                    ira_events_memory=ira_events_memory,
                    audit_log_memory=audit_log_memory,
                )
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except TimeoutError:
            continue


def create_ira_router(*, enforce_rate_limit: Callable[[str, int, int], None], ctx: IRAContext) -> APIRouter:  # NOSONAR
    router = APIRouter(prefix='/ira', tags=['ira'])
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

    def _db_dsn() -> str:
        host = os.getenv('POSTGRES_HOST', 'localhost')
        port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'nuxtron')
        user = os.getenv('POSTGRES_USER', 'nuxtron')
        password = os.getenv('POSTGRES_PASSWORD', '')
        return f'host={host} port={port} dbname={db_name} user={user} password={password} connect_timeout=2'

    def _init_crm_governance_table() -> None:
        nonlocal crm_governance_table_ready
        if crm_governance_table_ready:
            return
        with crm_governance_table_init_lock:
            if crm_governance_table_ready:
                return
            try:
                with psycopg.connect(_db_dsn()) as conn:
                    conn.execute("SET lock_timeout = '2000ms'")
                    conn.execute("SET statement_timeout = '5000ms'")
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            CREATE TABLE IF NOT EXISTS ira_crm_feature_governance (
                                id BIGSERIAL PRIMARY KEY,
                                tenant_id TEXT NOT NULL,
                                feature_key TEXT NOT NULL,
                                owner TEXT NOT NULL,
                                duplicate_disabled BOOLEAN NOT NULL DEFAULT TRUE,
                                notes TEXT NOT NULL DEFAULT '',
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                                UNIQUE (tenant_id, feature_key)
                            )
                            """
                        )
                    conn.commit()
                crm_governance_table_ready = True
            except Exception:
                crm_governance_table_ready = False

    def _default_crm_governance_map() -> dict[str, dict[str, Any]]:
        return {
            key: {
                'feature': key,
                'owner': owner,
                'duplicate_disabled': True,
                'secondary_disabled_for': 'odoo' if owner == 'corteza' else 'corteza',
                'notes': 'default ownership',
            }
            for key, owner in CRM_DEFAULT_OWNERSHIP.items()
        }

    def _load_crm_governance(tenant_id: str, control: dict[str, Any]) -> dict[str, dict[str, Any]]:
        governance = control.get('crm_feature_governance')
        if isinstance(governance, dict):
            cleaned: dict[str, dict[str, Any]] = {}
            governance_map = cast(dict[str, Any], governance)
            for key, value in governance_map.items():
                if not isinstance(value, dict):
                    continue
                value_map = cast(dict[str, Any], value)
                cleaned[key] = {str(sub_key): sub_value for sub_key, sub_value in value_map.items()}
            return cleaned

        loaded = _default_crm_governance_map()
        _init_crm_governance_table()
        if crm_governance_table_ready:
            try:
                with psycopg.connect(_db_dsn()) as conn, conn.cursor() as cur:
                    cur.execute(
                        """
                            SELECT feature_key, owner, duplicate_disabled, notes, updated_at
                            FROM ira_crm_feature_governance
                            WHERE tenant_id = %s
                            """,
                        (tenant_id,),
                    )
                    for feature_key, owner, duplicate_disabled, notes, updated_at in cur.fetchall():
                        feature = str(feature_key or '').strip()
                        if feature not in CRM_FEATURE_KEYS:
                            continue
                        owner_value = str(owner or '').strip().lower()
                        if owner_value not in {'corteza', 'odoo'}:
                            continue
                        loaded[feature] = {
                            'feature': feature,
                            'owner': owner_value,
                            'duplicate_disabled': bool(duplicate_disabled),
                            'secondary_disabled_for': 'odoo' if owner_value == 'corteza' else 'corteza',
                            'notes': str(notes or ''),
                            'updated_at': updated_at.isoformat() if isinstance(updated_at, datetime) else '',
                        }
            except Exception:
                pass
        control['crm_feature_governance'] = loaded
        return loaded

    def _persist_crm_governance_row(tenant_id: str, row: dict[str, Any]) -> None:
        _init_crm_governance_table()
        if not crm_governance_table_ready:
            return
        try:
            with psycopg.connect(_db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ira_crm_feature_governance (tenant_id, feature_key, owner, duplicate_disabled, notes, updated_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (tenant_id, feature_key)
                        DO UPDATE SET
                            owner = EXCLUDED.owner,
                            duplicate_disabled = EXCLUDED.duplicate_disabled,
                            notes = EXCLUDED.notes,
                            updated_at = NOW()
                        """,
                        (
                            tenant_id,
                            str(row.get('feature', '')),
                            str(row.get('owner', 'corteza')),
                            bool(row.get('duplicate_disabled', True)),
                            str(row.get('notes', '')),
                        ),
                    )
                conn.commit()
        except Exception:
            pass

    def _probe_crm_connectors() -> dict[str, Any]:
        # Keep probe latency safely below frontend proxy timeout budget.
        timeout = httpx.Timeout(connect=0.8, read=1.2, write=1.2, pool=0.8)
        probe_enabled = os.getenv('IRA_CONNECTOR_HEALTH_PROBE_ENABLED', 'false').strip().lower() in {
            '1',
            'true',
            'yes',
            'on',
        }
        result: dict[str, Any] = {
            'corteza': {'configured': False, 'healthy': False, 'detail': 'not configured'},
            'odoo': {'configured': False, 'healthy': False, 'detail': 'not configured'},
        }

        corteza_base = os.getenv('CORTEZA_API_BASE_URL', '').strip().rstrip('/')
        corteza_token = os.getenv('CORTEZA_API_TOKEN', '').strip()
        if corteza_base:
            headers = {'Accept': APPLICATION_JSON}
            if corteza_token:
                headers['Authorization'] = f'Bearer {corteza_token}'
            result['corteza']['configured'] = True
            if not probe_enabled:
                result['corteza']['detail'] = 'probe disabled'
            else:
                try:
                    response = httpx.get(f'{corteza_base}/healthcheck', headers=headers, timeout=timeout)
                    result['corteza']['healthy'] = response.is_success
                    result['corteza']['detail'] = f'status={response.status_code}'
                except Exception as ex:
                    result['corteza']['detail'] = str(ex)

        odoo_base = os.getenv('ODOO_API_BASE_URL', '').strip().rstrip('/')
        odoo_api_key = os.getenv('ODOO_API_KEY', '').strip()
        if odoo_base:
            headers = {'Accept': APPLICATION_JSON}
            if odoo_api_key:
                headers['X-API-Key'] = odoo_api_key
            result['odoo']['configured'] = True
            if not probe_enabled:
                result['odoo']['detail'] = 'probe disabled'
            else:
                try:
                    response = httpx.get(f'{odoo_base}/web/health', headers=headers, timeout=timeout)
                    result['odoo']['healthy'] = response.is_success
                    result['odoo']['detail'] = f'status={response.status_code}'
                except Exception as ex:
                    result['odoo']['detail'] = str(ex)

        return result

    def _audit(tenant_id: str, action: str, metadata: dict[str, Any] | None = None) -> None:
        audit_log_memory.append({
            'id': len(audit_log_memory) + 1,
            'tenant_id': tenant_id,
            'action': action,
            'source': 'ira-router',
            'metadata': metadata or {},
            'created_at': _now_iso(),
        })

    def _append_ira_event(tenant_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        event: dict[str, Any] = {
            'id': len(ira_events_memory) + 1,
            'tenant_id': tenant_id,
            'event_type': event_type,
            'payload': payload,
            'created_at': _now_iso(),
        }
        ira_events_memory.append(event)
        return event

    def _get_or_create_control(tenant_id: str) -> dict[str, Any]:
        existing = next((item for item in ira_controls_memory if item.get('tenant_id') == tenant_id), None)
        if existing is not None:
            return existing
        created: dict[str, Any] = {
            'id': len(ira_controls_memory) + 1,
            'tenant_id': tenant_id,
            'autonomy_enabled': True,
            'allow_high_impact_actions': False,
            'min_profit_margin_pct': 70.0,
            'suspicious_signal_threshold': 0.75,
            'require_super_admin': True,
            'max_dispute_auto_resolution_gbp': 50.0,
            'strict_policy_lock': True,
            'protection_mode': False,
            'blocked_actions': [],
            'updated_at': _now_iso(),
        }
        ira_controls_memory.append(created)
        return created

    def _is_super_admin(key: str | None) -> bool:
        expected = os.getenv('SUPER_ADMIN_API_KEY', '').strip()
        supplied = (key or '').strip()
        if not expected:
            return False
        return hmac.compare_digest(expected, supplied)

    def _require_super_admin_for_control(*, control: dict[str, Any], x_super_admin_key: str | None, detail: str) -> None:
        if bool(control.get('require_super_admin', True)) and not _is_super_admin(x_super_admin_key):
            raise HTTPException(status_code=403, detail=detail)

    def _requires_human_validation(payload: IRAActionRequest) -> bool:
        command = payload.command.strip().lower()
        if any(marker in command for marker in HUMAN_VALIDATION_COMMAND_MARKERS):
            return True
        if bool(payload.payload.get('is_compliance_operation', False)):
            return True
        if bool(payload.payload.get('bulk', False)):
            return True
        if int(payload.payload.get('recipient_count', 1) or 1) > 1:
            return True
        return payload.target in {'email', 'customer_support'}

    def _requires_explicit_approval(payload: IRAActionRequest) -> bool:
        command = payload.command.strip().lower()
        return any(marker in command for marker in EXPLICIT_APPROVAL_COMMAND_MARKERS)

    # Role → allowed IRA targets. Order matters: this is a precedence list, not
    # just a lookup table — see `_effective_actor_role` below.
    _ROLE_ALLOWED_TARGETS: dict[str, set[str]] = {
        'super_admin': {'customers', 'admin', 'email', 'chats', 'billing', 'credits', 'security', 'customer_support'},
        'admin': {'customers', 'admin', 'email', 'chats', 'customer_support'},
        'operator': {'customers', 'chats', 'customer_support'},
        'customer': set(),
    }
    _ROLE_PRECEDENCE: tuple[str, ...] = ('super_admin', 'admin', 'operator', 'customer')

    def _effective_actor_role(auth: AuthContext, *, verified_super_admin: bool) -> str:
        """Derive the caller's IRA role from verified, server-side signals ONLY.

        `payload.actor_role` on IRAActionRequest is client-supplied and must
        never be trusted for authorization — it existed only as the input to
        this function, which is exactly the vulnerability being fixed.

        Two verified signals are honored, in order:
        1. `verified_super_admin` — the caller presented a valid
           `X-Super-Admin-Key` (checked via `_is_super_admin`, a real
           `hmac`-comparable server secret) before this function ever runs, on
           routes that require it. Possession of that secret is itself the
           privileged credential this router already defers to, so it maps to
           `super_admin` regardless of JWT roles (API-key auth carries none).
        2. `auth.roles` — populated server-side in deps.py from the bearer
           JWT's `roles` claim (empty for API-key auth otherwise).

        Returns the highest-precedence role actually present, defaulting to
        the least privileged ('customer') if neither signal grants one.
        """
        if verified_super_admin:
            return 'super_admin'
        caller_roles = set(auth.roles)
        for role in _ROLE_PRECEDENCE:
            if role in caller_roles:
                return role
        return 'customer'

    def _validate_rbac_abac(*, payload: IRAActionRequest, auth: AuthContext, verified_super_admin: bool = False) -> None:
        effective_role = _effective_actor_role(auth, verified_super_admin=verified_super_admin)
        allowed = _ROLE_ALLOWED_TARGETS.get(effective_role, set())
        if payload.target not in allowed:
            raise HTTPException(status_code=403, detail='RBAC policy denied this IRA action for the authenticated role.')

        if payload.dashboard_scope != 'super_admin_dashboard':
            raise HTTPException(status_code=403, detail='ABAC policy requires super_admin_dashboard scope for IRA actions.')

        actor_tenant = str(payload.actor_attributes.get('tenant_id', '')).strip()
        if actor_tenant and actor_tenant != auth.tenant_id:
            raise HTTPException(status_code=403, detail='ABAC policy denied tenant mismatch for IRA action.')

    def _get_or_create_connector(tenant_id: str, channel: str) -> dict[str, Any]:
        existing = next(
            (
                item for item in ira_connectors_memory
                if item.get('tenant_id') == tenant_id and item.get('channel') == channel
            ),
            None,
        )
        if existing is not None:
            return existing
        created: dict[str, Any] = {
            'id': len(ira_connectors_memory) + 1,
            'tenant_id': tenant_id,
            'channel': channel,
            'enabled': True,
            'provider': 'internal',
            'config': {},
            'updated_at': _now_iso(),
        }
        ira_connectors_memory.append(created)
        return created

    def _connector_enabled(tenant_id: str, channel: str) -> bool:
        return bool(_get_or_create_connector(tenant_id, channel).get('enabled', True))

    def _ml_capabilities() -> dict[str, Any]:
        openai_configured = bool(os.getenv('OPENAI_API_KEY', '').strip())
        custom_finetune_endpoint = os.getenv('IRA_CUSTOM_FINETUNE_ENDPOINT', '').strip()
        sentence_transformers_available = _module_available('sentence_transformers')
        pytorch_available = _module_available('torch')
        tensorflow_available = _module_available('tensorflow')

        preferred_embedding_backend = os.getenv('IRA_EMBEDDING_BACKEND', 'auto').strip().lower()
        if preferred_embedding_backend not in {'auto', 'openai', 'sentence_transformers', 'local_hash'}:
            preferred_embedding_backend = 'auto'

        if preferred_embedding_backend == 'auto':
            if openai_configured:
                active_embedding_backend = 'openai'
            elif sentence_transformers_available:
                active_embedding_backend = 'sentence_transformers'
            else:
                active_embedding_backend = 'local_hash'
        else:
            active_embedding_backend = preferred_embedding_backend

        if pytorch_available:
            local_training_recommendation = 'PyTorch'
        elif tensorflow_available:
            local_training_recommendation = 'TensorFlow'
        else:
            local_training_recommendation = 'managed APIs until runtime is installed'

        return {
            'embeddings': {
                'active_backend': active_embedding_backend,
                'openai_configured': openai_configured,
                'sentence_transformers_available': sentence_transformers_available,
                'local_hash_available': True,
                'openai_model': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small').strip() or 'text-embedding-3-small',
                'sentence_transformer_model': os.getenv('IRA_SENTENCE_TRANSFORMER_MODEL', 'all-MiniLM-L6-v2').strip() or 'all-MiniLM-L6-v2',
            },
            'frameworks': {
                'pytorch': pytorch_available,
                'tensorflow': tensorflow_available,
                'sentence_transformers': sentence_transformers_available,
            },
            'fine_tuning': {
                'openai': {'configured': openai_configured, 'managed': True},
                'custom_http': {'configured': bool(custom_finetune_endpoint), 'endpoint': custom_finetune_endpoint},
            },
            'recommended_stack': {
                'rag': 'sentence-transformers + hybrid lexical retrieval' if sentence_transformers_available else 'hybrid hashed embeddings + lexical retrieval',
                'fine_tuning': 'OpenAI managed fine-tuning' if openai_configured else 'custom HTTP orchestration draft',
                'local_training': local_training_recommendation,
            },
        }

    def _free_tier_readiness(count: int) -> str:
        if count >= 3:
            return 'full'
        if count > 0:
            return 'partial'
        return 'none'

    def _frontier_stack_catalog() -> dict[str, Any]:
        temporal_ready = _module_available('temporalio')
        crewai_ready = _module_available('crewai') and os.getenv('IRA_ENABLE_CREWAI', '0').strip() == '1'
        langgraph_ready = _module_available('langgraph')
        neo4j_ready = bool(os.getenv('NEO4J_URI', '').strip())
        pinecone_ready = bool(os.getenv('PINECONE_API_KEY', '').strip())
        weaviate_ready = bool(os.getenv('WEAVIATE_URL', '').strip())
        redis_ready = bool(os.getenv('REDIS_HOST', '').strip())
        openai_ready = bool(os.getenv('OPENAI_API_KEY', '').strip())
        anthropic_ready = bool(os.getenv('ANTHROPIC_API_KEY', '').strip())
        cohere_ready = bool(os.getenv('COHERE_API_KEY', '').strip())
        gemini_ready = bool(os.getenv('GOOGLE_VERTEX_API_KEY', '').strip())
        cloudflare_ready = bool(os.getenv('CLOUDFLARE_API_TOKEN', '').strip()) and bool(os.getenv('CLOUDFLARE_ZONE_ID', '').strip())
        vercel_ready = bool(os.getenv('VERCEL_TOKEN', '').strip()) and bool(os.getenv('VERCEL_PROJECT_ID', '').strip())
        flyio_ready = bool(os.getenv('FLY_API_TOKEN', '').strip()) and bool(os.getenv('FLY_APP_NAME', '').strip())
        upstash_ready = bool(os.getenv('UPSTASH_REDIS_REST_URL', '').strip()) and bool(os.getenv('UPSTASH_REDIS_REST_TOKEN', '').strip())
        posthog_ready = bool(os.getenv('POSTHOG_PROJECT_API_KEY', '').strip())
        sentry_ready = bool(os.getenv('SENTRY_DSN', '').strip())
        langsmith_ready = bool(os.getenv('LANGSMITH_API_KEY', '').strip()) or bool(os.getenv('LANGCHAIN_API_KEY', '').strip())
        langfuse_ready = bool(os.getenv('LANGFUSE_PUBLIC_KEY', '').strip()) and bool(os.getenv('LANGFUSE_SECRET_KEY', '').strip())
        grafana_ready = bool(os.getenv('GRAFANA_URL', '').strip()) and bool(os.getenv('GRAFANA_API_KEY', '').strip())
        neon_ready = bool(os.getenv('NEON_DATABASE_URL', '').strip())
        firecrawl_ready = bool(os.getenv('FIRECRAWL_API_KEY', '').strip())
        agentops_ready = bool(os.getenv('AGENTOPS_API_KEY', '').strip())
        uploadthing_ready = bool(os.getenv('UPLOADTHING_TOKEN', '').strip())
        otel_ready = bool(os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', '').strip())
        betterstack_ready = bool(os.getenv('BETTER_STACK_SOURCE_TOKEN', '').strip())
        frontend_acceleration_enabled = {
            'million_js': os.getenv('NEXT_PUBLIC_ENABLE_MILLION', '0').strip() == '1',
            'partytown': os.getenv('NEXT_PUBLIC_ENABLE_PARTYTOWN', '0').strip() == '1',
            'zustand': os.getenv('NEXT_PUBLIC_ENABLE_ZUSTAND', '0').strip() == '1',
        }
        api_architecture_selected = {
            'hono': os.getenv('API_BFF_FRAMEWORK', '').strip().lower() == 'hono',
            'trpc': os.getenv('API_TRANSPORT', '').strip().lower() == 'trpc',
            'drizzle': os.getenv('DATABASE_ORM', '').strip().lower() == 'drizzle',
            'zod': os.getenv('API_SCHEMA_VALIDATION', '').strip().lower() == 'zod',
        }
        # Free-tier providers
        groq_ready = bool(os.getenv('GROQ_API_KEY', '').strip())
        gemini_free_ready = bool(os.getenv('GEMINI_API_KEY', '').strip())
        openrouter_ready = bool(os.getenv('OPENROUTER_API_KEY', '').strip())
        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434').strip()
        ollama_ready = bool(ollama_url)

        free_providers_configured = sum([groq_ready, gemini_free_ready, openrouter_ready, ollama_ready])
        paid_providers_configured = sum([openai_ready, anthropic_ready, cohere_ready, gemini_ready])

        return {
            'free_tier_ai_providers': {
                'note': 'Tier 0 — tried before any paid provider. Zero cost, no billing required.',
                'providers': {
                    'groq': {
                        'configured': groq_ready,
                        'cost': 'FREE',
                        'models': ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768', 'gemma2-9b-it', 'llama-3.1-8b-instant'],
                        'limits': '14,400 req/day · 500k tokens/min',
                        'quality_score': 0.84,
                        'speed': 'ultra-fast (~280ms)',
                        'setup': 'GROQ_API_KEY — free at console.groq.com',
                    },
                    'gemini_free': {
                        'configured': gemini_free_ready,
                        'cost': 'FREE',
                        'models': ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro'],
                        'limits': '1,500 req/day · 1M token context',
                        'quality_score': 0.85,
                        'speed': 'fast (~600ms)',
                        'setup': 'GEMINI_API_KEY — free at aistudio.google.com',
                    },
                    'openrouter': {
                        'configured': openrouter_ready,
                        'cost': 'FREE (free-model suffixed routes)',
                        'models': ['meta-llama/llama-3.2-3b-instruct:free', 'deepseek/deepseek-r1:free', 'mistralai/mistral-7b-instruct:free', 'google/gemma-3-1b-it:free'],
                        'limits': 'Rate-limited per free model',
                        'quality_score': 0.75,
                        'speed': 'moderate (~500ms)',
                        'setup': 'OPENROUTER_API_KEY — free at openrouter.ai',
                    },
                    'ollama': {
                        'configured': ollama_ready,
                        'cost': 'FREE (fully local)',
                        'models': ['llama3.3', 'mistral', 'gemma2', 'phi4', 'deepseek-r1'],
                        'limits': 'None — runs on your hardware',
                        'quality_score': 0.83,
                        'speed': 'hardware-dependent',
                        'setup': 'OLLAMA_BASE_URL — install from ollama.com/download',
                    },
                },
                'summary': {
                    'free_providers_configured': free_providers_configured,
                    'free_providers_total': 4,
                    'readiness': _free_tier_readiness(free_providers_configured),
                },
            },
            'platform_acceleration_best_of': {
                'note': 'Deduplicated best integrations requested for speed, reliability, and observability.',
                'delivery_and_edge': {
                    'cloudflare': {
                        'configured': cloudflare_ready,
                        'role': 'global edge cache, WAF, and CDN acceleration',
                        'env': ['CLOUDFLARE_API_TOKEN', 'CLOUDFLARE_ZONE_ID'],
                    },
                    'vercel': {
                        'configured': vercel_ready,
                        'role': 'Next.js edge deployment + analytics',
                        'includes': ['vercel_analytics'],
                        'env': ['VERCEL_TOKEN', 'VERCEL_PROJECT_ID', 'NEXT_PUBLIC_VERCEL_ANALYTICS_ID'],
                    },
                    'fly_io': {
                        'configured': flyio_ready,
                        'role': 'global FastAPI deployment close to users',
                        'env': ['FLY_API_TOKEN', 'FLY_APP_NAME'],
                    },
                },
                'data_and_runtime_speed': {
                    'upstash': {
                        'configured': upstash_ready,
                        'role': 'serverless Redis cache, queue, and rate limit acceleration',
                        'env': ['UPSTASH_REDIS_REST_URL', 'UPSTASH_REDIS_REST_TOKEN'],
                    },
                    'neon': {
                        'configured': neon_ready,
                        'role': 'autoscaling serverless Postgres for bursty workloads',
                        'env': ['NEON_DATABASE_URL'],
                    },
                    'uploadthing': {
                        'configured': uploadthing_ready,
                        'role': 'fast direct-to-storage uploads and media ingress',
                        'env': ['UPLOADTHING_TOKEN', 'UPLOADTHING_APP_ID'],
                    },
                },
                'observability_and_ai_ops': {
                    'posthog': {
                        'configured': posthog_ready,
                        'role': 'product analytics, feature flags, and session replay',
                    },
                    'sentry': {
                        'configured': sentry_ready,
                        'role': 'error + performance monitoring (dedupes sentry and sentry performance)',
                        'env': ['SENTRY_DSN', 'SENTRY_TRACES_SAMPLE_RATE'],
                    },
                    'langsmith': {
                        'configured': langsmith_ready,
                        'role': 'LLM chain debugging and evals',
                        'env': ['LANGSMITH_API_KEY', 'LANGCHAIN_TRACING_V2', 'LANGCHAIN_PROJECT'],
                    },
                    'langfuse': {
                        'configured': langfuse_ready,
                        'role': 'prompt and generation tracing with cost visibility',
                        'env': ['LANGFUSE_PUBLIC_KEY', 'LANGFUSE_SECRET_KEY', 'LANGFUSE_HOST'],
                    },
                    'grafana': {
                        'configured': grafana_ready,
                        'role': 'metrics dashboards and alerting',
                        'env': ['GRAFANA_URL', 'GRAFANA_API_KEY'],
                    },
                    'open_telemetry': {
                        'configured': otel_ready,
                        'role': 'vendor-neutral distributed tracing',
                        'env': ['OTEL_EXPORTER_OTLP_ENDPOINT', 'OTEL_SERVICE_NAME'],
                    },
                    'better_stack': {
                        'configured': betterstack_ready,
                        'role': 'logs, uptime, and incident response automation',
                        'env': ['BETTER_STACK_SOURCE_TOKEN'],
                    },
                    'agentops': {
                        'configured': agentops_ready,
                        'role': 'agent execution observability and guardrails',
                        'env': ['AGENTOPS_API_KEY'],
                    },
                },
                'ai_data_enrichment': {
                    'firecrawl': {
                        'configured': firecrawl_ready,
                        'role': 'turn websites into clean AI-ingestion markdown and JSON',
                        'env': ['FIRECRAWL_API_KEY'],
                    },
                },
                'frontend_and_api_architecture': {
                    'frontend_speed_toggles': {
                        'million_js': {'enabled': frontend_acceleration_enabled['million_js']},
                        'partytown': {'enabled': frontend_acceleration_enabled['partytown']},
                        'zustand': {'enabled': frontend_acceleration_enabled['zustand']},
                    },
                    'api_stack_choices': {
                        'hono_js': {'enabled': api_architecture_selected['hono']},
                        'trpc': {'enabled': api_architecture_selected['trpc']},
                        'drizzle_orm': {'enabled': api_architecture_selected['drizzle']},
                        'zod': {'enabled': api_architecture_selected['zod']},
                    },
                },
            },
            'frontier_reasoning_and_multi_agent_intelligence': {
                'providers': {
                    'openai': {'configured': openai_ready, 'role': 'strongest general reasoning + tool calling'},
                    'anthropic': {'configured': anthropic_ready, 'role': 'long-context + structured reasoning'},
                    'cohere': {'configured': cohere_ready, 'role': 'enterprise embeddings + RAG'},
                },
                'orchestration': {
                    'crewai': {'available': crewai_ready, 'role_based_ai_teams': True},
                    'langgraph': {'available': langgraph_ready, 'persistent_workflows': True},
                },
                'summary': {'paid_providers_configured': paid_providers_configured},
            },
            'long_term_memory_and_knowledge': {
                'vector_memory': {
                    'pinecone': {'configured': pinecone_ready},
                    'weaviate': {'configured': weaviate_ready},
                },
                'graph_memory': {'neo4j': {'configured': neo4j_ready, 'relationship_reasoning': True}},
                'realtime_memory': {'redis': {'configured': redis_ready}},
                'recommendation': 'combine vector + graph memory for higher-context reasoning',
            },
            'multimodal_perception': {
                'providers': {
                    'openai_vision_speech': {'configured': openai_ready},
                    'google_deepmind_gemini': {'configured': gemini_ready},
                    'assemblyai': {'configured': bool(os.getenv('ASSEMBLYAI_API_KEY', '').strip())},
                    'runway': {'configured': bool(os.getenv('RUNWAY_API_KEY', '').strip())},
                },
                'enables': [
                    'meeting_audio_and_video_analysis',
                    'screenshot_and_ui_understanding',
                    'automated_content_pipeline_generation',
                ],
            },
            'autonomous_tool_execution_layer': {
                'automation': {
                    'n8n': {'enabled': True, 'note': 'kept as primary automation layer'},
                    'zapier': {'available': bool(os.getenv('ZAPIER_WEBHOOK_URL', '').strip())},
                    'make': {'available': bool(os.getenv('MAKE_WEBHOOK_URL', '').strip())},
                },
                'durable_workflows': {
                    'temporal': {
                        'available': temporal_ready,
                        'free_or_open_source': True,
                        'benefits': ['retries', 'state_persistence', 'complex_multi_step_automation'],
                    }
                },
            },
            'advanced_rag': {
                'frameworks': {
                    'llamaindex': {'available': _module_available('llama_index')},
                    'haystack': {'available': _module_available('haystack')},
                },
                'techniques': ['hybrid_search', 'query_rewriting', 'multi_hop_reasoning', 'context_compression'],
            },
            'continuous_learning_and_evaluation': {
                'platforms': {
                    'weights_and_biases': {'configured': bool(os.getenv('WANDB_API_KEY', '').strip())},
                    'langsmith': {'configured': bool(os.getenv('LANGCHAIN_API_KEY', '').strip())},
                    'humanloop': {'configured': bool(os.getenv('HUMANLOOP_API_KEY', '').strip())},
                },
                'enables': ['feedback_loops', 'auto_optimization', 'task_level_performance_tracking'],
            },
            'guardrails_and_ai_safety': {
                'guardrails_ai': {'available': _module_available('guardrails')},
                'rebuff': {'available': _module_available('rebuff')},
                'prevents': ['hallucinations', 'prompt_injection_attacks', 'unsafe_actions'],
            },
            'high_performance_compute_and_scaling': {
                'clouds': ['aws', 'gcp', 'azure'],
                'accelerators': ['nvidia'],
            },
            'deep_enterprise_integrations': {
                'salesforce': {'configured': bool(os.getenv('SALESFORCE_CLIENT_ID', '').strip())},
                'slack': {'configured': bool(os.getenv('SLACK_BOT_TOKEN', '').strip())},
                'notion': {'configured': bool(os.getenv('NOTION_API_KEY', '').strip())},
                'google_workspace': {'configured': bool(os.getenv('GOOGLE_WORKSPACE_CLIENT_ID', '').strip())},
            },
            'god_like_ingredients': [
                'multi_agent_systems_planner_executor_critic',
                'persistent_memory_across_users_tasks_history',
                'reliable_tool_mastery_and_api_execution',
                'self_improvement_feedback_logs_failures',
                'multimodal_awareness_text_audio_video_ui',
            ],
            'hard_truths': [
                'true_autonomy_requires_tight_constraints',
                'edge_cases_will_break_flows_without_guarded_fallbacks',
                'costs_can_explode_without_quotas_and_budget_controls',
                'reliability_is_the_hardest_problem',
            ],
        }

    def _frontier_recommended_stack(payload: IRAFrontierPlanRequest) -> dict[str, Any]:
        if payload.include_free_open_source_only:
            brain = ['llama (ollama)', 'mistral (ollama)']
            agents = ['langgraph', 'native_secure_loop']
            memory = ['weaviate or pgvector', 'neo4j' if payload.require_graph_memory else 'postgres', 'redis']
            rag = ['llamaindex or haystack']
            workflows = ['temporal (oss)', 'n8n (oss)']
        else:
            brain = ['openai', 'anthropic', 'cohere_embeddings_for_rag']
            agents = ['crewai', 'langgraph']
            memory = ['pinecone', 'neo4j' if payload.require_graph_memory else 'weaviate', 'redis']
            rag = ['llamaindex', 'hybrid_vector_keyword_retrieval', 'query_rewriting', 'context_compression']
            workflows = ['temporal', 'n8n', 'zapier_or_make_for_external_actions']

        multimodal = ['openai_vision_speech', 'gemini_multimodal'] if payload.require_multimodal else ['text_only_mode']
        observability = ['langsmith', 'langfuse', 'posthog', 'sentry', 'open_telemetry', 'grafana', 'better_stack', 'weights_and_biases']
        safety = ['guardrails_ai', 'rebuff', 'human_approval_for_high_impact_actions']

        return {
            'brain': brain,
            'agents': agents,
            'memory': memory,
            'multimodal': multimodal,
            'rag': rag,
            'workflows': workflows,
            'observability': observability,
            'safety': safety,
            'platform_acceleration': [
                'cloudflare',
                'vercel_with_analytics',
                'fly_io',
                'upstash',
                'neon',
                'uploadthing',
                'firecrawl',
                'agentops',
                'million_js',
                'partytown',
                'zustand',
                'hono_js',
                'zod',
                'trpc',
                'drizzle_orm',
            ],
            'enterprise_integrations': ['salesforce', 'slack', 'notion', 'google_workspace'],
        }

    def _frontier_readiness_summary(stack: dict[str, Any]) -> dict[str, Any]:
        signals_total = 0
        signals_ready = 0
        missing_signals: list[str] = []

        def _walk(value: Any, path: str) -> None:
            nonlocal signals_total, signals_ready
            if isinstance(value, dict):
                value_map = cast(dict[str, Any], value)
                for signal_name in ('configured', 'available', 'enabled'):
                    if signal_name in value_map and isinstance(value_map[signal_name], bool):
                        signals_total += 1
                        signal_path = f'{path}.{signal_name}' if path else signal_name
                        if bool(value_map[signal_name]):
                            signals_ready += 1
                        else:
                            missing_signals.append(signal_path)
                for key, nested in value_map.items():
                    next_path = f'{path}.{key}' if path else str(key)
                    _walk(nested, next_path)
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    _walk(item, f'{path}[{index}]')

        _walk(stack, '')
        readiness_score = 0
        if signals_total > 0:
            readiness_score = int(round((signals_ready / signals_total) * 100))

        readiness_state = 'low'
        if readiness_score >= 75:
            readiness_state = 'high'
        elif readiness_score >= 40:
            readiness_state = 'medium'
        return {
            'score_pct': readiness_score,
            'state': readiness_state,
            'signals_ready': signals_ready,
            'signals_total': signals_total,
            'missing_signals': missing_signals[:30],
        }

    def _frontier_env_template(readiness: dict[str, Any]) -> dict[str, Any]:
        signal_to_env: dict[str, list[str]] = {
            'frontier_reasoning_and_multi_agent_intelligence.providers.openai.configured': ['OPENAI_API_KEY=', 'OPENAI_MODEL=gpt-4.1-mini'],
            'frontier_reasoning_and_multi_agent_intelligence.providers.anthropic.configured': ['ANTHROPIC_API_KEY=', 'ANTHROPIC_MODEL=claude-3-5-sonnet-latest'],
            'frontier_reasoning_and_multi_agent_intelligence.providers.cohere.configured': ['COHERE_API_KEY=', 'COHERE_MODEL=command-r-plus'],
            'frontier_reasoning_and_multi_agent_intelligence.orchestration.crewai.available': ['IRA_ENABLE_CREWAI=1', 'IRA_CREWAI_SECURE_MODE=1'],
            'long_term_memory_and_knowledge.vector_memory.pinecone.configured': ['PINECONE_API_KEY=', 'PINECONE_INDEX_HOST=', 'PINECONE_NAMESPACE=ira-memory'],
            'long_term_memory_and_knowledge.vector_memory.weaviate.configured': ['WEAVIATE_URL=', 'WEAVIATE_API_KEY=', 'WEAVIATE_CLASS_NAME=IraMemoryChunk'],
            'long_term_memory_and_knowledge.graph_memory.neo4j.configured': ['NEO4J_URI=', 'NEO4J_USERNAME=', 'NEO4J_PASSWORD='],
            'long_term_memory_and_knowledge.realtime_memory.redis.configured': ['REDIS_HOST=', 'REDIS_PORT=6379', 'REDIS_PASSWORD=', 'REDIS_DB=0'],
            'multimodal_perception.providers.google_deepmind_gemini.configured': ['GOOGLE_VERTEX_API_KEY=', 'GOOGLE_VERTEX_PROJECT_ID=', 'GOOGLE_VERTEX_MODEL=gemini-2.0-flash', 'GOOGLE_VERTEX_LOCATION=us-central1'],
            'multimodal_perception.providers.assemblyai.configured': ['ASSEMBLYAI_API_KEY='],
            'multimodal_perception.providers.runway.configured': ['RUNWAY_API_KEY='],
            'autonomous_tool_execution_layer.automation.zapier.available': ['ZAPIER_WEBHOOK_URL='],
            'autonomous_tool_execution_layer.automation.make.available': ['MAKE_WEBHOOK_URL='],
            'continuous_learning_and_evaluation.platforms.weights_and_biases.configured': ['WANDB_API_KEY='],
            'continuous_learning_and_evaluation.platforms.langsmith.configured': ['LANGCHAIN_API_KEY=', 'LANGCHAIN_TRACING_V2=true', 'LANGCHAIN_PROJECT=nuxtron-ira'],
            'continuous_learning_and_evaluation.platforms.humanloop.configured': ['HUMANLOOP_API_KEY='],
            'platform_acceleration_best_of.delivery_and_edge.cloudflare.configured': ['CLOUDFLARE_API_TOKEN=', 'CLOUDFLARE_ZONE_ID='],
            'platform_acceleration_best_of.delivery_and_edge.vercel.configured': ['VERCEL_TOKEN=', 'VERCEL_PROJECT_ID=', 'NEXT_PUBLIC_VERCEL_ANALYTICS_ID='],
            'platform_acceleration_best_of.delivery_and_edge.fly_io.configured': ['FLY_API_TOKEN=', 'FLY_APP_NAME='],
            'platform_acceleration_best_of.data_and_runtime_speed.upstash.configured': ['UPSTASH_REDIS_REST_URL=', 'UPSTASH_REDIS_REST_TOKEN='],
            'platform_acceleration_best_of.data_and_runtime_speed.neon.configured': ['NEON_DATABASE_URL='],
            'platform_acceleration_best_of.data_and_runtime_speed.uploadthing.configured': ['UPLOADTHING_TOKEN=', 'UPLOADTHING_APP_ID='],
            'platform_acceleration_best_of.observability_and_ai_ops.sentry.configured': ['SENTRY_DSN=', 'SENTRY_TRACES_SAMPLE_RATE=0.2'],
            'platform_acceleration_best_of.observability_and_ai_ops.langsmith.configured': ['LANGSMITH_API_KEY=', 'LANGCHAIN_TRACING_V2=true', 'LANGCHAIN_PROJECT=nuxtron-ira'],
            'platform_acceleration_best_of.observability_and_ai_ops.langfuse.configured': ['LANGFUSE_PUBLIC_KEY=', 'LANGFUSE_SECRET_KEY=', 'LANGFUSE_HOST=https://cloud.langfuse.com'],
            'platform_acceleration_best_of.observability_and_ai_ops.grafana.configured': ['GRAFANA_URL=', 'GRAFANA_API_KEY='],
            'platform_acceleration_best_of.observability_and_ai_ops.open_telemetry.configured': ['OTEL_EXPORTER_OTLP_ENDPOINT=', 'OTEL_SERVICE_NAME=nuxtron-fastapi'],
            'platform_acceleration_best_of.observability_and_ai_ops.better_stack.configured': ['BETTER_STACK_SOURCE_TOKEN='],
            'platform_acceleration_best_of.observability_and_ai_ops.agentops.configured': ['AGENTOPS_API_KEY='],
            'platform_acceleration_best_of.ai_data_enrichment.firecrawl.configured': ['FIRECRAWL_API_KEY='],
            'platform_acceleration_best_of.frontend_and_api_architecture.frontend_speed_toggles.million_js.enabled': ['NEXT_PUBLIC_ENABLE_MILLION=1'],
            'platform_acceleration_best_of.frontend_and_api_architecture.frontend_speed_toggles.partytown.enabled': ['NEXT_PUBLIC_ENABLE_PARTYTOWN=1'],
            'platform_acceleration_best_of.frontend_and_api_architecture.frontend_speed_toggles.zustand.enabled': ['NEXT_PUBLIC_ENABLE_ZUSTAND=1'],
            'platform_acceleration_best_of.frontend_and_api_architecture.api_stack_choices.hono_js.enabled': ['API_BFF_FRAMEWORK=hono'],
            'platform_acceleration_best_of.frontend_and_api_architecture.api_stack_choices.trpc.enabled': ['API_TRANSPORT=trpc'],
            'platform_acceleration_best_of.frontend_and_api_architecture.api_stack_choices.drizzle_orm.enabled': ['DATABASE_ORM=drizzle'],
            'platform_acceleration_best_of.frontend_and_api_architecture.api_stack_choices.zod.enabled': ['API_SCHEMA_VALIDATION=zod'],
            'deep_enterprise_integrations.salesforce.configured': ['SALESFORCE_CLIENT_ID=', 'SALESFORCE_CLIENT_SECRET=', 'SALESFORCE_USERNAME=', 'SALESFORCE_PASSWORD='],
            'deep_enterprise_integrations.slack.configured': ['SLACK_BOT_TOKEN=', 'SLACK_SIGNING_SECRET='],
            'deep_enterprise_integrations.notion.configured': ['NOTION_API_KEY='],
            'deep_enterprise_integrations.google_workspace.configured': ['GOOGLE_WORKSPACE_CLIENT_ID=', 'GOOGLE_WORKSPACE_CLIENT_SECRET='],
        }

        missing = cast(list[str], readiness.get('missing_signals', [])) if isinstance(readiness.get('missing_signals'), list) else []
        lines: list[str] = []
        seen: set[str] = set()

        for signal in missing:
            env_lines = signal_to_env.get(signal, [])
            for line in env_lines:
                if line not in seen:
                    seen.add(line)
                    lines.append(line)

        required = [line for line in lines if line.endswith('=')]
        defaults = [line for line in lines if not line.endswith('=')]

        template_sections = [
            '# Frontier AI Stack generated template',
            '# Fill required values below, keep defaults unless needed.',
            '',
            '# Required values',
            *required,
            '',
            '# Recommended defaults',
            *defaults,
        ]

        return {
            'required_env_count': len(required),
            'recommended_defaults_count': len(defaults),
            'required_env': required,
            'recommended_defaults': defaults,
            'template': '\n'.join(template_sections).strip(),
        }

    def _validate_env_target_filename(value: str) -> tuple[bool, str]:
        candidate = value.strip()
        if not candidate:
            return False, 'target_file must not be empty.'
        if '/' in candidate or '\\' in candidate or '..' in candidate:
            return False, 'target_file must be a plain filename without path traversal.'
        if not candidate.startswith('.env'):
            return False, 'target_file must start with .env'
        return True, candidate

    def _split_env_assignment(line: str) -> tuple[str, str] | None:
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            return None
        if '=' not in stripped:
            return None
        key, value = stripped.split('=', 1)
        env_key = key.strip()
        if not env_key:
            return None
        return env_key, value

    def _merge_env_file_non_destructive(existing_content: str, generated_lines: list[str]) -> tuple[str, dict[str, int]]:
        existing_lines = existing_content.splitlines()
        existing_key_to_index: dict[str, int] = {}

        for index, line in enumerate(existing_lines):
            parsed = _split_env_assignment(line)
            if parsed is None:
                continue
            existing_key_to_index[parsed[0]] = index

        updated_existing_empty = 0
        kept_existing_non_empty = 0
        appended_missing = 0

        for raw_line in generated_lines:
            parsed_generated = _split_env_assignment(raw_line)
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
            parsed_current = _split_env_assignment(current_line)
            current_value = parsed_current[1] if parsed_current is not None else ''
            if current_value.strip():
                kept_existing_non_empty += 1
                continue

            if generated_value.strip():
                existing_lines[existing_index] = raw_line
                updated_existing_empty += 1

        merged_content = '\n'.join(existing_lines).strip()
        if merged_content:
            merged_content += '\n'
        return merged_content, {
            'updated_existing_empty': updated_existing_empty,
            'kept_existing_non_empty': kept_existing_non_empty,
            'appended_missing': appended_missing,
        }

    def _copilot_catalog() -> dict[str, Any]:
        return {
            'a_to_z': {
                'A': 'Agent mode (task loops, multi-step execution)',
                'B': 'Bring your own models through provider routing',
                'C': 'Chat with repository context and codebase grounding',
                'D': 'Documentation generation and summarization workflows',
                'E': 'Enterprise policy controls and governance gates',
                'F': 'Fix suggestions and code actions',
                'G': 'Git-aware PR review and commit-aware assistance',
                'H': 'Hybrid search: semantic + lexical retrieval',
                'I': 'Inline completions and suggestion ranking',
                'J': 'Just-in-time command and terminal assistance',
                'K': 'Knowledge retrieval from local docs and runbooks',
                'L': 'Long-context reasoning with tool contracts',
                'M': 'MCP-style tool integrations and function-calling',
                'N': 'Natural language to code/query transformations',
                'O': 'Observability signals, traces, and usage analytics',
                'P': 'Prompt templates and reusable workflows',
                'Q': 'Quality gates with tests/lint/type checks',
                'R': 'Refactoring orchestration and safe edits',
                'S': 'Security posture checks and safe defaults',
                'T': 'Task planning, decomposition, and execution phases',
                'U': 'User memory and session memory continuity',
                'V': 'Version-aware migrations and API compatibility',
                'W': 'Workspace-aware code navigation',
                'X': 'eXternal system connectors (GitHub, CI, tickets)',
                'Y': 'Yield optimization for speed/cost/reliability tradeoffs',
                'Z': 'Zero-trust guardrails for high-impact actions',
            },
            'feature_families': {
                'chat': [
                    'multi-turn chat',
                    'context carryover',
                    'repo-grounded answers',
                    'explain-code mode',
                    'generate-code mode',
                ],
                'coding': [
                    'inline completion',
                    'test generation',
                    'refactor proposals',
                    'error-aware fixes',
                    'safe patch suggestions',
                ],
                'agent': [
                    'plan tool',
                    'multi-step execution',
                    'terminal + file operations',
                    'live validation loops',
                    'bounded retries and safeguards',
                ],
                'security_compliance': [
                    'policy-gated actions',
                    'audit events',
                    'approval requirements for risky paths',
                    'secret-safe handling patterns',
                ],
                'developer_experience': [
                    'symbol navigation',
                    'usage lookup',
                    'rename actions',
                    'problem diagnostics integration',
                    'test run integration',
                ],
            },
        }

    def _copilot_readiness() -> dict[str, Any]:
        model_routing = os.getenv('IRA_COPILOT_MODEL_ROUTING', 'github_auto').strip().lower()
        require_models_token = model_routing in {'github_models', 'direct_models_api'}
        signals: dict[str, bool] = {
            'github_token_configured': bool(os.getenv('GITHUB_TOKEN', '').strip()),
            'github_models_token_configured': bool(os.getenv('GITHUB_MODELS_TOKEN', '').strip()) if require_models_token else True,
            'github_org_configured': bool(os.getenv('GITHUB_ORG', '').strip()),
            'github_repo_configured': bool(os.getenv('GITHUB_REPO', '').strip()),
            'copilot_chat_enabled_flag': os.getenv('IRA_ENABLE_COPILOT_CHAT', '0').strip() == '1',
            'copilot_agent_enabled_flag': os.getenv('IRA_ENABLE_COPILOT_AGENT', '0').strip() == '1',
            'copilot_telemetry_enabled_flag': os.getenv('IRA_ENABLE_COPILOT_TELEMETRY', '1').strip() == '1',
            'copilot_policy_lock_flag': os.getenv('IRA_COPILOT_POLICY_LOCK', '1').strip() == '1',
        }
        total = len(signals)
        ready = sum(1 for value in signals.values() if value)
        score = int((ready / total) * 100) if total else 0
        missing = [key for key, value in signals.items() if not value]
        state: Literal['low', 'medium', 'high'] = 'low'
        if score >= 75:
            state = 'high'
        elif score >= 40:
            state = 'medium'
        return {
            'score_pct': score,
            'state': state,
            'signals_ready': ready,
            'signals_total': total,
            'signals': signals,
            'missing_signals': missing,
            'model_routing': model_routing,
            'models_token_required': require_models_token,
        }

    def _copilot_env_template() -> dict[str, Any]:
        required_env = [
            'GITHUB_TOKEN=',
            'GITHUB_ORG=',
            'GITHUB_REPO=',
            'IRA_COPILOT_MODEL_ROUTING=github_auto',
            'IRA_ENABLE_COPILOT_CHAT=1',
            'IRA_ENABLE_COPILOT_AGENT=1',
        ]
        recommended_env = [
            'GITHUB_MODELS_TOKEN=',
            'IRA_ENABLE_COPILOT_TELEMETRY=1',
            'IRA_COPILOT_POLICY_LOCK=1',
            'IRA_COPILOT_MAX_ITERATIONS=6',
            'IRA_COPILOT_DEFAULT_MODEL=gpt-4.1',
            'IRA_COPILOT_FALLBACK_MODEL=gpt-4.1-mini',
            'IRA_COPILOT_AUDIT_RETENTION_DAYS=90',
            'IRA_COPILOT_APPROVAL_REQUIRED_FOR_HIGH_IMPACT=1',
            'IRA_COPILOT_ALLOWED_TOOLS=file_edit,terminal,tests,diagnostics',
        ]
        lines = [
            '# GitHub Copilot platform integration template',
            '# Required settings',
            *required_env,
            '',
            '# Recommended settings',
            *recommended_env,
        ]
        return {
            'required_env_count': len(required_env),
            'recommended_env_count': len(recommended_env),
            'required_env': required_env,
            'recommended_env': recommended_env,
            'template': '\n'.join(lines).strip(),
        }

    def _copilot_health_check() -> dict[str, Any]:
        model_routing = os.getenv('IRA_COPILOT_MODEL_ROUTING', 'github_auto').strip().lower()
        token = os.getenv('GITHUB_TOKEN', '').strip()
        if not token:
            if model_routing == 'github_auto':
                return {
                    'status': 'auto_mode',
                    'github_api': {
                        'reachable': False,
                        'detail': 'GITHUB_TOKEN is not configured; running in github_auto mode without direct GitHub API verification.',
                    },
                    'model_routing': model_routing,
                }
            return {
                'status': 'not_configured',
                'github_api': {'reachable': False, 'detail': 'GITHUB_TOKEN is not configured'},
                'model_routing': model_routing,
            }
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(
                    'https://api.github.com/rate_limit',
                    headers={
                        'Authorization': f'Bearer {token}',
                        'Accept': 'application/vnd.github+json',
                        'X-GitHub-Api-Version': '2022-11-28',
                    },
                )
            if response.is_success:
                payload = cast(dict[str, Any], response.json())
                resources_raw = payload.get('resources', {})
                resources = cast(dict[str, Any], resources_raw) if isinstance(resources_raw, dict) else {}
                return {
                    'status': 'ok',
                    'github_api': {
                        'reachable': True,
                        'http_status': response.status_code,
                        'rate_limit_resources': resources,
                    },
                    'model_routing': model_routing,
                }
            return {
                'status': 'error',
                'github_api': {
                    'reachable': False,
                    'http_status': response.status_code,
                    'detail': response.text[:300],
                },
                'model_routing': model_routing,
            }
        except Exception as ex:
            return {
                'status': 'error',
                'github_api': {
                    'reachable': False,
                    'detail': str(ex),
                },
                'model_routing': model_routing,
            }

    def _embed_texts(values: list[str]) -> tuple[str, list[list[float]]]:
        capabilities = _ml_capabilities()
        active_backend = str(capabilities['embeddings']['active_backend'])

        if active_backend == 'sentence_transformers' and bool(capabilities['frameworks']['sentence_transformers']):
            try:
                model_name = str(capabilities['embeddings']['sentence_transformer_model'])
                model = sentence_transformer_cache.get(model_name)
                if model is None:
                    sentence_transformers_module = importlib.import_module('sentence_transformers')
                    sentence_transformer_class = sentence_transformers_module.SentenceTransformer
                    model = sentence_transformer_class(model_name)
                    sentence_transformer_cache[model_name] = model
                embeddings = model.encode(values, normalize_embeddings=True)
                normalized_rows: list[list[float]] = []
                for row in cast(list[Any], embeddings):
                    normalized_rows.append([float(entry) for entry in cast(list[Any], row)])
                if len(normalized_rows) == len(values):
                    return 'sentence_transformers', normalized_rows
            except Exception:
                pass

        if active_backend == 'openai' and bool(capabilities['fine_tuning']['openai']['configured']):
            try:
                api_key = os.getenv('OPENAI_API_KEY', '').strip()
                model_name = str(capabilities['embeddings']['openai_model'])
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(
                        'https://api.openai.com/v1/embeddings',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': APPLICATION_JSON,
                        },
                        json={'model': model_name, 'input': values},
                    )
                if response.is_success:
                    payload = cast(dict[str, Any], response.json())
                    raw_data = payload.get('data')
                    data: list[Any] = []
                    if isinstance(raw_data, list):
                        for entry in raw_data:
                            data.append(entry)
                    if len(data) == len(values):
                        rows: list[list[float]] = []
                        for raw_item in data:
                            row_item = cast(dict[str, Any], raw_item) if isinstance(raw_item, dict) else {}
                            embedding = row_item.get('embedding')
                            if isinstance(embedding, list):
                                rows.append([float(entry) for entry in embedding])
                        if len(rows) == len(values):
                            return 'openai', rows
            except Exception:
                pass

        return 'local_hash', [_local_hash_embedding(value) for value in values]

    memory_system = IRAMemorySystem(
        db_dsn_fn=_db_dsn,
        now_iso_fn=_now_iso,
        short_term_store=ira_sessions_memory,
        long_term_store=ira_ml_knowledge_memory,
        structured_store=ira_structured_memory,
        embed_texts=_embed_texts,
    )
    ai_brain = AIBrainModelLayer(now_iso_fn=_now_iso)

    def _ml_summary(tenant_id: str) -> dict[str, Any]:
        tenant_knowledge = [item for item in ira_ml_knowledge_memory if item.get('tenant_id') == tenant_id]
        tenant_jobs = [item for item in ira_ml_jobs_memory if item.get('tenant_id') == tenant_id]
        tenant_models = [item for item in ira_ml_models_memory if item.get('tenant_id') == tenant_id]
        document_ids = {str(item.get('document_id', '')).strip() for item in tenant_knowledge if str(item.get('document_id', '')).strip()}
        active_jobs = [item for item in tenant_jobs if str(item.get('status', '')).lower() in {'queued', 'submitted', 'running'}]
        memory_overview = memory_system.overview(tenant_id)
        return {
            'documents': len(document_ids),
            'knowledge_chunks': len(tenant_knowledge),
            'jobs': len(tenant_jobs),
            'active_jobs': len(active_jobs),
            'models': len(tenant_models),
            'capabilities': _ml_capabilities(),
            'memory_system': {
                'short_term_messages': int(memory_overview['summary']['short_term_messages']),
                'structured_records': int(memory_overview['summary']['structured_records']),
                'active_short_term_backend': str(memory_overview['summary']['active_short_term_backend']),
                'active_long_term_backend': str(memory_overview['summary']['active_long_term_backend']),
                'active_structured_backend': str(memory_overview['summary']['active_structured_backend']),
            },
        }

    def _register_model_record(*, tenant_id: str, model_type: str, model_name: str, provider: str, source_job_id: str, status: str, metadata: dict[str, Any]) -> dict[str, Any]:
        existing = next(
            (
                item for item in ira_ml_models_memory
                if item.get('tenant_id') == tenant_id and item.get('source_job_id') == source_job_id and item.get('model_type') == model_type
            ),
            None,
        )
        if existing is not None:
            existing['model_name'] = model_name
            existing['provider'] = provider
            existing['status'] = status
            existing['metadata'] = metadata
            existing['updated_at'] = _now_iso()
            return existing

        record: dict[str, Any] = {
            'id': len(ira_ml_models_memory) + 1,
            'tenant_id': tenant_id,
            'model_type': model_type,
            'model_name': model_name,
            'provider': provider,
            'source_job_id': source_job_id,
            'status': status,
            'metadata': metadata,
            'created_at': _now_iso(),
            'updated_at': _now_iso(),
        }
        ira_ml_models_memory.append(record)
        return record

    def _choose_pipeline_framework(payload: IRATrainingPipelineRequest) -> tuple[str, bool, str]:
        capabilities = _ml_capabilities()['frameworks']
        if payload.framework != 'auto':
            is_available = bool(capabilities.get(payload.framework, False))
            reason = 'requested framework is installed' if is_available else 'requested runtime is not installed yet'
            return payload.framework, is_available, reason

        if payload.pipeline_type == 'rag' and bool(capabilities.get('sentence_transformers', False)):
            return 'sentence_transformers', True, 'best local retrieval stack available'
        if bool(capabilities.get('pytorch', False)):
            return 'pytorch', True, 'best available general-purpose training runtime'
        if bool(capabilities.get('tensorflow', False)):
            return 'tensorflow', True, 'tensorflow runtime available'
        return 'sentence_transformers' if payload.pipeline_type == 'rag' else 'pytorch', False, 'managed orchestration only until local runtime is installed'

    def _tenant_revenue_snapshot(tenant_id: str) -> dict[str, float]:
        return compute_tenant_revenue_snapshot(
            tenant_id=tenant_id,
            invoices_memory=invoices_memory,
            credit_ledger_memory=credit_ledger_memory,
        )

    def _tenant_suspicious_signal(tenant_id: str) -> dict[str, Any]:
        return compute_tenant_suspicious_signal(
            tenant_id=tenant_id,
            stripe_events_memory=stripe_events_memory,
            revenue_conversions_memory=revenue_conversions_memory,
            api_usage_audit_memory=api_usage_audit_memory,
            ai_security_usage_memory=ai_security_usage_memory,
        )

    def _retrieve_knowledge_context(tenant_id: str, query: str, *, top_k: int = 3, min_score: float = 0.12) -> list[dict[str, Any]]:
        _, results = memory_system.query_long_term_memory(
            tenant_id=tenant_id,
            query=query,
            top_k=top_k,
            min_score=min_score,
            fallback_items=[item for item in ira_ml_knowledge_memory if item.get('tenant_id') == tenant_id],
        )
        return results

    def _agent_runtime_for_tenant(tenant_id: str) -> IRAAgentRuntime:
        def _tenant_auto_framework_preference(tenant_id_value: str) -> str | None:
            prefer_tenant_memory = os.getenv('IRA_AGENT_PREFER_TENANT_MEMORY', '1').strip() == '1'
            if prefer_tenant_memory:
                records = memory_system.list_structured_memory(tenant_id_value, memory_type='preference')
                record = next((item for item in records if item.get('memory_key') == 'agent_framework_auto'), None)
                if isinstance(record, dict):
                    payload = record.get('payload')
                    if isinstance(payload, dict):
                        payload_map = cast(dict[str, Any], payload)
                        framework_value = str(payload_map.get('framework', '')).strip().lower()
                        if framework_value in {'langchain', 'semantic_kernel', 'native_secure_loop'}:
                            return framework_value

            env_preference = os.getenv('IRA_AGENT_AUTO_FRAMEWORK', '').strip().lower()
            if env_preference in {'langchain', 'semantic_kernel', 'native_secure_loop'}:
                return env_preference
            return None

        return IRAAgentRuntime(
            now_iso_fn=_now_iso,
            retrieve_knowledge=lambda query, top_k, min_score: _retrieve_knowledge_context(
                tenant_id=tenant_id,
                query=query,
                top_k=top_k,
                min_score=min_score,
            ),
            upsert_structured_memory=lambda memory_type, memory_key, payload: memory_system.upsert_structured_memory(
                tenant_id=tenant_id,
                memory_type=memory_type,
                memory_key=memory_key,
                payload=payload,
            ),
            get_short_term_messages=lambda tenant_id_value, limit: memory_system.get_short_term_messages(tenant_id_value, limit=limit),
            compose_response=lambda message, knowledge_hits: _ira_response('operator', 'chat', message, knowledge_hits=knowledge_hits),
            brain_reason=lambda prompt, provider, tools: ai_brain.reason(
                prompt=prompt,
                provider=_normalize_brain_provider(provider),
                tools=tools,
            ),
            get_auto_framework_preference=_tenant_auto_framework_preference,
        )

    def _classify_chat_intent(*, message: str, recent_history: list[dict[str, Any]] | None = None) -> tuple[str, str, float]:
        message_text = message.strip().lower()
        history_text = ' '.join(str(item.get('content', '')) for item in (recent_history or [])[-8:]).lower()
        combined = f'{message_text} {history_text}'.strip()

        if any(token in combined for token in ('refund', 'invoice', 'billing', 'charge', 'credit', 'dispute')):
            return ('financial_ops', 'billing', 0.86)
        if any(token in combined for token in ('breach', 'incident', 'security', 'threat', 'siem', 'risk')):
            return ('security_ops', 'security', 0.88)
        if any(token in combined for token in ('campaign', 'roas', 'cac', 'ads', 'paid', 'creative')):
            return ('growth_ads', 'ads', 0.82)
        if any(token in combined for token in ('seo', 'keyword', 'backlink', 'ranking', 'technical audit', 'core web')):
            return ('growth_seo', 'seo', 0.83)
        if any(token in combined for token in ('social', 'post', 'linkedin', 'instagram', 'tiktok', 'youtube', 'calendar')):
            return ('growth_social', 'social', 0.8)
        if any(token in combined for token in ('ticket', 'support', 'customer', 'onboarding', 'issue', 'help')):
            return ('customer_support', 'support', 0.78)
        return ('general_ops', 'general', 0.62)

    def _chat_risk_assessment(message: str) -> dict[str, Any]:
        lowered = message.lower()
        suspicious_markers = (
            'ignore previous instructions',
            'bypass policy',
            'disable security',
            'exfiltrate',
            'leak key',
            'steal token',
            'override approval',
        )
        matched = [marker for marker in suspicious_markers if marker in lowered]
        return {
            'risk_level': 'high' if matched else 'low',
            'prompt_injection_markers': matched,
            'needs_manual_review': bool(matched),
        }

    def _build_chat_action_plan(*, intent: str, domain: str, risk: dict[str, Any]) -> IRAChatActionPlan:
        requires_human_validation = bool(risk.get('needs_manual_review', False)) or domain in {'billing', 'security'}
        requires_explicit_approval = domain in {'billing', 'security'}

        recommended_actions: list[dict[str, Any]] = [
            {
                'label': 'Create IRA autonomous run plan',
                'endpoint': '/ira/agent/run',
                'method': 'POST',
                'dry_run': True,
                'priority': 'high',
            },
            {
                'label': 'Persist operator intent to structured memory',
                'endpoint': '/ira/memory/structured/upsert',
                'method': 'POST',
                'dry_run': True,
                'priority': 'medium',
            },
        ]

        if domain in {'billing', 'security'}:
            recommended_actions.append({
                'label': 'Execute guarded action with approvals',
                'endpoint': '/ira/actions',
                'method': 'POST',
                'dry_run': True,
                'priority': 'high',
            })
        else:
            recommended_actions.append({
                'label': 'Execute low-risk operational action',
                'endpoint': '/ira/actions',
                'method': 'POST',
                'dry_run': True,
                'priority': 'medium',
            })

        return IRAChatActionPlan(
            intent=intent,
            domain=domain,
            requires_human_validation=requires_human_validation,
            requires_explicit_approval=requires_explicit_approval,
            recommended_actions=recommended_actions,
        )

    def _ira_response(role: str, channel: str, message: str, *, knowledge_hits: list[dict[str, Any]] | None = None, recent_history: list[dict[str, Any]] | None = None) -> tuple[str, float]:
        """Return (response_text, confidence: 0.0-1.0)"""
        role_prefix = {
            'customer': 'IRA Customer Care',
            'admin': 'IRA Platform Ops',
            'operator': 'IRA Control Tower',
        }.get(role, 'IRA')
        channel_hint = {
            'chat': 'chat response',
            'email': 'email draft',
            'ticket': 'ticket resolution update',
            'webhook': 'automation callback response',
        }.get(channel, 'response')
        message_text = message.strip()
        lower_message = message_text.lower()

        def _contains(*tokens: str) -> bool:
            return any(token in lower_message for token in tokens)

        # Confidence scoring: starts at 0.4 base
        confidence = 0.4
        
        # For short confirmations/continuations, derive context from recent conversation history
        _short_confirms = {'yes', 'no', 'ok', 'okay', 'sure', 'do it', 'go', 'proceed', 'confirm',
                           'start', 'run', 'execute', 'do', 'do this', 'sounds good', 'great', 'perfect', 'please'}
        is_short_confirm = lower_message in _short_confirms or len(message_text.split()) <= 3

        if is_short_confirm and recent_history:
            # Scan last few messages for a topic keyword
            history_text = ' '.join(
                str(m.get('content', '')) for m in recent_history[-6:]
            ).lower()

            def _hist_contains(*tokens: str) -> bool:
                return any(token in history_text for token in tokens)

            if _hist_contains('seo', 'ranking', 'keyword', 'backlink', 'technical audit', 'core web'):
                lower_message = lower_message + ' seo'
                confidence += 0.2  # +0.2 for history context
            elif _hist_contains('ads', 'campaign', 'cac', 'roas', 'creative', 'paid'):
                lower_message = lower_message + ' ads'
                confidence += 0.2
            elif _hist_contains('social', 'instagram', 'tiktok', 'linkedin', 'content calendar', 'post'):
                lower_message = lower_message + ' social'
                confidence += 0.2
            elif _hist_contains('billing', 'invoice', 'payment', 'refund', 'dispute', 'credit'):
                lower_message = lower_message + ' billing'
                confidence += 0.2
            elif _hist_contains('security', 'breach', 'siem', 'threat', 'incident', 'risk'):
                lower_message = lower_message + ' security'
                confidence += 0.2
            elif _hist_contains('support', 'customer', 'onboarding', 'help', 'issue', 'ticket'):
                lower_message = lower_message + ' support'
                confidence += 0.2

        if _contains('seo', 'ranking', 'keyword', 'backlink', 'core web vitals', 'technical audit'):
            task_brief = (
                'SEO workflow selected: I can run technical crawl checks, cluster target keywords, '
                'and queue a backlink + internal-linking plan with weekly rank delta tracking.'
            )
            confidence += 0.1  # +0.1 for explicit topic match
        elif _contains('ads', 'campaign', 'cac', 'roas', 'creative', 'paid'):
            task_brief = (
                'Ads workflow selected: I can propose creatives, launch audience split tests, '
                'and rebalance budget toward best CAC/ROAS performers on a 48-hour cadence.'
            )
            confidence += 0.1
        elif _contains('social', 'content calendar', 'post', 'instagram', 'linkedin', 'tiktok', 'youtube'):
            task_brief = (
                'Social workflow selected: I can generate a 30-day content calendar, '
                'create multi-format variants, and schedule per-platform peak windows.'
            )
            confidence += 0.1
        elif _contains('billing', 'invoice', 'payment', 'refund', 'dispute', 'credit'):
            task_brief = (
                'Billing workflow selected: I can investigate ledger and invoice context, '
                'then prepare a compliant action path with approvals for refund/dispute steps.'
            )
            confidence += 0.1
        elif _contains('security', 'incident', 'breach', 'siem', 'threat', 'risk'):
            task_brief = (
                'Security workflow selected: I can assemble risk signals, correlate events, '
                'and generate a guarded incident-response sequence with audit checkpoints.'
            )
            confidence += 0.1
        elif _contains('support', 'customer', 'onboarding', 'help', 'issue', 'ticket'):
            task_brief = (
                'Support workflow selected: I can draft a customer-safe resolution plan, '
                'route handoffs to the right queue, and keep full conversation audit trace.'
            )
            confidence += 0.1
        else:
            task_brief = (
                'General workflow selected: I can break this into safe executable steps, '
                'request approvals where required, and keep full operational audit logging.'
            )

        base_response = (
            f'{role_prefix}: {channel_hint} ready for "{message_text[:220]}". '
            f'{task_brief}'
        )

        # Add confidence for knowledge hits: +0.15 per hit (max +0.3)
        if knowledge_hits:
            confidence += min(len(knowledge_hits) * 0.15, 0.3)
            grounded_points = [
                f"{str(hit.get('title', 'Knowledge'))}: {str(hit.get('content', ''))[:160]}"
                for hit in knowledge_hits[:2]
            ]
            response_text = (
                f'{base_response} '
                'Grounded knowledge highlights: '
                f"{' '.join(grounded_points)}"
            )
        else:
            response_text = base_response

        # Cap confidence at 1.0
        confidence = min(confidence, 1.0)
        return (response_text, confidence)

    def _deliver_email(*, tenant_id: str, connector: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        """Send email via configured connector using integration layer."""
        subject = str(payload.get('subject', 'IRA automated email')).strip() or 'IRA automated email'
        body = str(payload.get('body', payload.get('message', ''))).strip() or 'IRA automated email.'
        recipient = str(payload.get('to', payload.get('recipient', 'ops@nuxtron.local'))).strip() or 'ops@nuxtron.local'
        
        result = dispatch_via_ira_connector(
            channel='email',
            ira_connector=connector,
            recipient=recipient,
            subject=subject,
            body=body,
        )
        
        # Queue in memory if not sent
        if result['delivery_status'] in ('queued', 'failed'):
            queued: dict[str, Any] = {
                'id': len(resend_messages_memory) + 1,
                'tenant_id': tenant_id,
                'provider': result.get('provider', 'unknown'),
                'to': recipient,
                'subject': subject,
                'body': body,
                'status': 'queued',
                'created_at': _now_iso(),
            }
            resend_messages_memory.append(queued)
            return {**result, 'message_id': queued['id']}
        
        return result

    def _deliver_slack(*, tenant_id: str, connector: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        """Send Slack message via configured connector using integration layer."""
        text = str(payload.get('message', payload.get('body', payload.get('subject', 'IRA action')))).strip() or 'IRA action'
        title = str(payload.get('title', '')).strip()
        
        result = dispatch_via_ira_connector(
            channel='slack',
            ira_connector=connector,
            message=text,
            title=title,
        )
        
        # Queue in memory if not sent
        if result['delivery_status'] in ('queued', 'failed'):
            queued: dict[str, Any] = {
                'id': len(slack_messages_memory) + 1,
                'tenant_id': tenant_id,
                'provider': result.get('provider', 'unknown'),
                'channel': result.get('channel', '#general'),
                'text_preview': text[:120],
                'status': 'queued',
                'created_at': _now_iso(),
            }
            slack_messages_memory.append(queued)
            return {**result, 'message_id': queued['id']}
        
        return result

    def _deliver_whatsapp(*, tenant_id: str, connector: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        """Send WhatsApp message via Twilio connector using integration layer."""
        body = str(payload.get('message', payload.get('body', payload.get('subject', 'IRA customer support update')))).strip() or 'IRA customer support update'
        recipient = str(payload.get('to', payload.get('recipient', ''))).strip()
        
        result = dispatch_via_ira_connector(
            channel='whatsapp',
            ira_connector=connector,
            recipient=recipient,
            body=body,
        )
        
        # Queue in memory if not sent
        if result['delivery_status'] in ('queued', 'failed'):
            queued: dict[str, Any] = {
                'id': len(twilio_messages_memory) + 1,
                'tenant_id': tenant_id,
                'provider': result.get('provider', 'unknown'),
                'to': recipient,
                'body': body,
                'status': 'queued',
                'created_at': _now_iso(),
            }
            twilio_messages_memory.append(queued)
            return {**result, 'message_id': queued['id']}
        
        return result

    def _record_cost(tenant_id: str, action_type: str, units: int = 1, unit_cost_pence: float = 0.5, *, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Record cost per IRA decision/action for cost tracking."""
        total_cost_pence = round(units * unit_cost_pence, 4)
        entry: dict[str, Any] = {
            'id': len(ira_cost_ledger_memory) + 1,
            'tenant_id': tenant_id,
            'action_type': action_type,
            'units': units,
            'unit_cost_pence': unit_cost_pence,
            'total_cost_pence': total_cost_pence,
            'metadata': metadata or {},
            'created_at': _now_iso(),
        }
        ira_cost_ledger_memory.append(entry)
        return entry

    def _notify_ops_email(
        *,
        tenant_id: str,
        subject: str,
        body: str,
        priority: str = 'normal',
        event_type: str = 'ira_notification',
    ) -> None:
        """Send an ops notification email via resend/email connector, with fallback to memory queue."""
        resend_api_key = os.getenv('RESEND_API_KEY', '').strip()
        ops_email = os.getenv('OPS_NOTIFICATION_EMAIL', '').strip()
        if not ops_email:
            ops_email = 'ops@nuxtron.local'

        # Queue in resend memory (actual dispatch handled by connector)
        queued: dict[str, Any] = {
            'id': len(resend_messages_memory) + 1,
            'tenant_id': tenant_id,
            'provider': 'resend' if resend_api_key else 'internal_queue',
            'to': ops_email,
            'subject': f'[IRA-{priority.upper()}] {subject}',
            'html': f'<p>{body}</p><p><small>Tenant: {tenant_id} | Event: {event_type}</small></p>',
            'status': 'queued',
            'created_at': _now_iso(),
        }
        resend_messages_memory.append(queued)

        # If Resend is configured, attempt actual delivery
        if resend_api_key:
            try:
                httpx.post(
                    'https://api.resend.com/emails',
                    json={
                        'from': 'IRA Notifications <noreply@nuxtron.local>',
                        'to': [ops_email],
                        'subject': queued['subject'],
                        'html': queued['html'],
                    },
                    headers={'Authorization': f'Bearer {resend_api_key}'},
                    timeout=4,
                )
                queued['status'] = 'sent'
            except Exception:
                queued['status'] = 'queued'  # stays queued on failure

    def _notify_ops_slack(
        *,
        tenant_id: str,
        text: str,
        title: str = 'IRA Alert',
        priority: str = 'normal',
        event_type: str = 'ira_notification',
    ) -> None:
        """Post an ops alert to Slack via webhook, with fallback to memory queue."""
        webhook_url = os.getenv('SLACK_OPS_WEBHOOK_URL', '').strip()
        queued: dict[str, Any] = {
            'id': len(slack_messages_memory) + 1,
            'tenant_id': tenant_id,
            'provider': 'slack_webhook',
            'channel': '#ira-alerts',
            'text_preview': text[:240],
            'event_type': event_type,
            'status': 'queued',
            'created_at': _now_iso(),
        }
        slack_messages_memory.append(queued)

        if not webhook_url:
            return  # No webhook configured — stays queued for later

        payload_body: dict[str, Any] = {
            'text': f'*[IRA-{priority.upper()}] {title}*\n{text}',
            'blocks': [
                {
                    'type': 'section',
                    'text': {'type': 'mrkdwn', 'text': f'*[IRA-{priority.upper()}] {title}*'},
                },
                {
                    'type': 'section',
                    'text': {'type': 'mrkdwn', 'text': text[:2000]},
                },
                {
                    'type': 'context',
                    'elements': [{'type': 'mrkdwn', 'text': f'Tenant: `{tenant_id}` | Event: `{event_type}`'}],
                },
            ],
        }
        try:
            httpx.post(webhook_url, json=payload_body, timeout=4)
            queued['status'] = 'sent'
        except Exception:
            queued['status'] = 'queued'

    def _record_performance(
        tenant_id: str,
        action_type: str,
        *,
        latency_ms: float = 0.0,
        confidence: float = 0.5,
        outcome: str = 'success',
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a performance data point for analytics."""
        ira_performance_log_memory.append({
            'id': len(ira_performance_log_memory) + 1,
            'tenant_id': tenant_id,
            'action_type': action_type,
            'latency_ms': round(latency_ms, 2),
            'confidence': round(confidence, 3),
            'outcome': outcome,
            'metadata': metadata or {},
            'created_at': _now_iso(),
        })

    @router.get('/status')
    def ira_status(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:status', 120, 60)
        with lock:
            control = _get_or_create_control(auth.tenant_id).copy()
            recent_events = [item.copy() for item in ira_events_memory if item.get('tenant_id') == auth.tenant_id][-20:]
            connectors = [_get_or_create_connector(auth.tenant_id, channel).copy() for channel in CONNECTOR_CHANNELS]
        brain_capabilities = cast(dict[str, Any], ai_brain.capabilities())
        brain_providers = cast(dict[str, Any], brain_capabilities.get('providers', {}) or {})

        def _provider_readiness(key: str, fallback_label: str, fallback_model: str) -> dict[str, Any]:
            provider = cast(dict[str, Any], brain_providers.get(key, {}) or {})
            configured = bool(provider.get('configured', False))
            reason = str(
                provider.get('reason')
                or provider.get('status_reason')
                or provider.get('unavailable_reason')
                or provider.get('error')
                or provider.get('error_detail')
                or ''
            ).strip()
            if not reason:
                reason = 'Configured and available' if configured else 'Missing provider credentials/configuration'
            return {
                'key': key,
                'label': str(provider.get('label', fallback_label) or fallback_label),
                'configured': configured,
                'model': str(provider.get('model', fallback_model) or fallback_model),
                'route': key,
                'reason': reason,
            }

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'ira_name': 'IRA',
            'always_on': True,
            'autonomy': control,
            'connectors': connectors,
            'finance_health': _tenant_revenue_snapshot(auth.tenant_id),
            'risk_signal': _tenant_suspicious_signal(auth.tenant_id),
            'recent_events': recent_events,
            'provider_readiness': {
                'internal': {
                    'key': 'internal',
                    'label': 'Internal IRA',
                    'configured': True,
                    'model': 'rule_based',
                    'route': 'internal',
                    'reason': 'Built-in guarded fallback route',
                },
                'openai': _provider_readiness('openai', 'OpenAI', 'gpt-4.1-mini'),
                'anthropic': _provider_readiness('anthropic', 'Anthropic', 'claude-3-5-sonnet-latest'),
            },
            'capabilities': {
                'customer_support': True,
                'admin_assist': True,
                'email_handling': True,
                'chat_handling': True,
                'credit_monitoring': True,
                'payment_monitoring': True,
                'damage_containment': True,
                'provider_connectors': True,
                'feature_adoption_guidance': True,
                'lead_conversion_assist': True,
                'human_validation_gate': True,
                'rbac_enforced': True,
                'abac_enforced': True,
                'provider_routing': True,
                'training_layer': True,
                'rag_retrieval': True,
                'fine_tuning_orchestration': True,
            },
            'ml_training_layer': _ml_summary(auth.tenant_id),
            'policy': {
                'requires_super_admin_for_autonomy': bool(control.get('require_super_admin', True)),
                'dashboard_scope': 'super_admin_dashboard',
                'compliance_requires_human_validation': True,
                'bulk_messages_require_human_validation': True,
                'tickets_require_human_validation': True,
                'all_disputes_require_human_validation': True,
                'strict_policy_lock': bool(control.get('strict_policy_lock', True)),
                'max_dispute_auto_resolution_gbp': float(control.get('max_dispute_auto_resolution_gbp', 50.0)),
                'blocked_autonomous_actions': list(DEFAULT_BLOCKED_ACTIONS),
            },
        }

    @router.get('/playbook')
    def ira_playbook(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:playbook', 120, 60)
        with lock:
            control = _get_or_create_control(auth.tenant_id).copy()
            sessions_count = len([item for item in ira_sessions_memory if item.get('tenant_id') == auth.tenant_id])
            events_count = len([item for item in ira_events_memory if item.get('tenant_id') == auth.tenant_id])
            connectors = [_get_or_create_connector(auth.tenant_id, channel).copy() for channel in CONNECTOR_CHANNELS]

        finance = _tenant_revenue_snapshot(auth.tenant_id)
        risk_signal = _tenant_suspicious_signal(auth.tenant_id)
        min_margin = float(control.get('min_profit_margin_pct', 70.0))
        current_margin = float(finance.get('profit_margin_pct', 0.0))
        suspicious_score = float(risk_signal.get('score', 0.0))

        milestones: list[dict[str, Any]] = [
            {
                'key': 'first_session',
                'label': 'First IRA session',
                'target': 'Week 1',
                'achieved': sessions_count >= 1,
                'detail': f'Sessions observed: {sessions_count}',
            },
            {
                'key': 'first_event',
                'label': 'First automation event',
                'target': 'Week 1',
                'achieved': events_count >= 1,
                'detail': f'Events observed: {events_count}',
            },
            {
                'key': 'autonomy_enabled',
                'label': 'Autonomy enabled',
                'target': 'Week 2',
                'achieved': bool(control.get('autonomy_enabled', True)),
                'detail': f"Autonomy state: {'enabled' if bool(control.get('autonomy_enabled', True)) else 'disabled'}",
            },
            {
                'key': 'connectors_online',
                'label': 'Core connectors online',
                'target': 'Week 2',
                'achieved': all(bool(item.get('enabled', False)) for item in connectors if str(item.get('channel', '')) in {'chat', 'email', 'ticket'}),
                'detail': 'Chat, email, and ticket connector readiness',
            },
            {
                'key': 'profit_guard',
                'label': 'Profit margin target met',
                'target': 'Week 4',
                'achieved': current_margin >= min_margin,
                'detail': f'Margin {current_margin:.2f}% vs target {min_margin:.2f}%',
            },
            {
                'key': 'risk_guard',
                'label': 'Risk signal within threshold',
                'target': 'Week 4',
                'achieved': suspicious_score <= float(control.get('suspicious_signal_threshold', 0.75)),
                'detail': f"Risk score {suspicious_score:.3f} vs threshold {float(control.get('suspicious_signal_threshold', 0.75)):.3f}",
            },
        ]

        achieved_count = len([item for item in milestones if bool(item.get('achieved', False))])
        total_count = len(milestones)
        completion_pct = 0.0 if total_count <= 0 else round((achieved_count / total_count) * 100.0, 2)

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'generated_at': _now_iso(),
            'completion_chart': {
                'achieved': achieved_count,
                'total': total_count,
                'percentage': completion_pct,
            },
            'milestones': milestones,
            'decision_tree': list(IRA_PLAYBOOK_DECISION_TREE),
        }

    @router.get('/frontier/stack')
    def ira_frontier_stack(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:frontier:stack', 120, 60)
        stack = _frontier_stack_catalog()
        readiness = _frontier_readiness_summary(stack)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'frontier': stack,
            'readiness': readiness,
            'env_template': _frontier_env_template(readiness),
            'god_stack_example': {
                'brain': 'OpenAI / Anthropic',
                'agents': 'CrewAI + LangGraph',
                'memory': 'Pinecone + Neo4j + Redis',
                'rag': 'LlamaIndex (hybrid retrieval)',
                'workflows': 'Temporal + n8n',
                'observability': 'LangSmith + Weights & Biases',
            },
        }

    @router.post('/frontier/plan')
    def ira_frontier_plan(payload: IRAFrontierPlanRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:frontier:plan', 60, 60)
        stack = _frontier_recommended_stack(payload)
        readiness = _frontier_readiness_summary(_frontier_stack_catalog())
        phases: list[dict[str, Any]] = [
            {
                'phase': 1,
                'name': 'Reliability Foundation',
                'deliverables': ['guardrails', 'approval gates', 'budget controls', 'failure telemetry'],
            },
            {
                'phase': 2,
                'name': 'Memory + RAG Intelligence',
                'deliverables': ['vector_memory', 'graph_memory', 'hybrid_retrieval', 'context_compression'],
            },
            {
                'phase': 3,
                'name': 'Multi-Agent Workforce',
                'deliverables': ['planner_executor_critic_roles', 'durable_workflow_state', 'tool_retry_policy'],
            },
            {
                'phase': 4,
                'name': 'Multimodal + Enterprise Ops',
                'deliverables': ['audio_video_ui_analysis', 'slack_notion_salesforce_workspace_actions'],
            },
        ]

        execution_jobs: list[dict[str, Any]] = []
        if payload.create_execution_tasks:
            for phase in phases:
                phase_number = int(phase.get('phase', 0) or 0)
                job: dict[str, Any] = {
                    'id': len(ira_ml_jobs_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'job_type': 'frontier_execution_phase',
                    'name': f'frontier_phase_{phase_number}',
                    'objective': payload.objective,
                    'framework': ','.join(cast(list[str], stack.get('agents', []))),
                    'priority': payload.priority,
                    'phase': phase_number,
                    'phase_name': str(phase.get('name', '')),
                    'deliverables': phase.get('deliverables', []),
                    'status': 'planned',
                    'dry_run': True,
                    'created_at': _now_iso(),
                    'updated_at': _now_iso(),
                }
                ira_ml_jobs_memory.append(job)
                execution_jobs.append(job)

        event = _append_ira_event(auth.tenant_id, 'frontier_plan_generated', {
            'priority': payload.priority,
            'objective_preview': payload.objective[:140],
            'open_source_only': payload.include_free_open_source_only,
            'create_execution_tasks': payload.create_execution_tasks,
        })
        _audit(auth.tenant_id, 'ira_frontier_plan_generated', {'event_id': event['id']})
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'objective': payload.objective,
            'priority': payload.priority,
            'recommended_stack': stack,
            'current_readiness': readiness,
            'implementation_phases': phases,
            'execution_jobs': execution_jobs,
            'event_id': event['id'],
        }

    @router.get('/frontier/env-template')
    def ira_frontier_env_template(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:frontier:env-template', 120, 60)
        stack = _frontier_stack_catalog()
        readiness = _frontier_readiness_summary(stack)
        template = _frontier_env_template(readiness)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'readiness': readiness,
            'env_template': template,
        }

    @router.post('/frontier/env-template/apply-draft', responses={422: {'description': 'Invalid draft filename or template generation failure'}, 500: {'description': 'Unable to write draft file'}})
    def ira_frontier_env_template_apply_draft(
        payload: IRAFrontierEnvTemplateApplyRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:frontier:env-template:apply', 30, 60)
        is_valid_target, validated_target_or_error = _validate_env_target_filename(payload.target_file)
        if not is_valid_target:
            raise HTTPException(status_code=422, detail=validated_target_or_error)
        target_file = validated_target_or_error
        stack = _frontier_stack_catalog()
        readiness = _frontier_readiness_summary(stack)
        env_template = _frontier_env_template(readiness)
        rendered_template = str(env_template.get('template', '')).strip()
        if not rendered_template:
            raise HTTPException(status_code=422, detail='Unable to render environment template from readiness state.')

        generated_lines: list[str] = []
        for entry in cast(list[Any], env_template.get('required_env', [])):
            if isinstance(entry, str) and entry.strip():
                generated_lines.append(entry.strip())
        for entry in cast(list[Any], env_template.get('recommended_defaults', [])):
            if isinstance(entry, str) and entry.strip():
                generated_lines.append(entry.strip())

        mode = payload.mode

        file_content = (
            '# Generated by IRA Frontier Stack\n'
            f'# tenant: {auth.tenant_id}\n'
            f'# generated_at: {_now_iso()}\n\n'
            f'{rendered_template}\n'
        )
        target_path = os.path.abspath(target_file)
        should_merge_non_destructive = mode in {'merge_non_destructive', 'merge_and_backup'}
        should_create_backup = mode == 'merge_and_backup'

        existing_content = ''
        if should_merge_non_destructive and os.path.exists(target_path):
            try:
                with open(target_path, encoding='utf-8') as handle:
                    existing_content = handle.read()
            except Exception as ex:
                raise HTTPException(status_code=500, detail=f'Failed reading existing env file: {ex}') from ex

        merge_stats: dict[str, int] = {
            'updated_existing_empty': 0,
            'kept_existing_non_empty': 0,
            'appended_missing': 0,
        }
        if should_merge_non_destructive:
            file_content, merge_stats = _merge_env_file_non_destructive(existing_content, generated_lines)

        backup_path = ''
        if should_create_backup and os.path.exists(target_path):
            timestamp = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
            backup_path = f'{target_path}.bak-{timestamp}-{uuid.uuid4().hex[:8]}'
            try:
                with open(backup_path, 'w', encoding='utf-8', newline='\n') as backup_handle:
                    backup_handle.write(existing_content)
            except Exception as ex:
                raise HTTPException(status_code=500, detail=f'Failed writing backup env file: {ex}') from ex

        try:
            with open(target_path, 'w', encoding='utf-8', newline='\n') as handle:
                handle.write(file_content)
        except Exception as ex:
            raise HTTPException(status_code=500, detail=f'Failed writing draft env file: {ex}') from ex

        event = _append_ira_event(auth.tenant_id, 'frontier_env_template_draft_applied', {
            'target_file': target_file,
            'readiness_score': readiness.get('score_pct', 0),
            'mode': mode,
        })
        _audit(auth.tenant_id, 'ira_frontier_env_template_draft_applied', {'event_id': event['id'], 'target_file': target_file})
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'target_file': target_file,
            'target_path': target_path,
            'mode': mode,
            'backup_path': backup_path,
            'bytes_written': len(file_content.encode('utf-8')),
            'merge_stats': merge_stats,
            'readiness': readiness,
            'event_id': event['id'],
        }

    @router.get('/copilot/catalog')
    def ira_copilot_catalog(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:copilot:catalog', 120, 60)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'copilot': _copilot_catalog(),
            'readiness': _copilot_readiness(),
            'env_template': _copilot_env_template(),
        }

    @router.get('/copilot/health')
    def ira_copilot_health(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:copilot:health', 120, 60)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'health': _copilot_health_check(),
            'readiness': _copilot_readiness(),
        }

    @router.get('/copilot/env-template')
    def ira_copilot_env_template(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:copilot:env-template', 120, 60)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'env_template': _copilot_env_template(),
        }

    @router.post('/copilot/plan')
    def ira_copilot_plan(payload: IRACopilotPlanRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:copilot:plan', 60, 60)
        readiness = _copilot_readiness()
        phases: list[dict[str, Any]] = [
            {
                'phase': 1,
                'name': 'Foundation + Access',
                'deliverables': ['token_setup', 'org_repo_binding', 'chat_flag_enablement', 'policy_lock_defaults'],
            },
            {
                'phase': 2,
                'name': 'Feature Enablement',
                'deliverables': ['chat_surface', 'code_actions', 'diagnostics', 'test_runner_flows', 'context_routing'],
            },
            {
                'phase': 3,
                'name': 'Agent Workflows',
                'deliverables': ['task_planning', 'tool_execution', 'bounded_iterations', 'approval_gates_for_high_impact'],
            },
            {
                'phase': 4,
                'name': 'Enterprise Ops + Telemetry',
                'deliverables': ['audit_trails', 'usage_analytics', 'security_controls', 'rollout_playbook', 'runbooks'],
            },
        ]
        if not payload.include_agent_mode:
            phases = [phase for phase in phases if int(phase.get('phase', 0) or 0) != 3]

        event = _append_ira_event(auth.tenant_id, 'copilot_plan_generated', {
            'priority': payload.priority,
            'objective_preview': payload.objective[:140],
            'include_enterprise_controls': payload.include_enterprise_controls,
            'include_telemetry': payload.include_telemetry,
            'include_agent_mode': payload.include_agent_mode,
        })
        _audit(auth.tenant_id, 'ira_copilot_plan_generated', {'event_id': event['id']})
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'objective': payload.objective,
            'priority': payload.priority,
            'implementation_phases': phases,
            'readiness': readiness,
            'catalog': _copilot_catalog(),
            'env_template': _copilot_env_template(),
            'event_id': event['id'],
        }

    @router.get('/ml/overview')
    def ira_ml_overview(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:ml:overview', 120, 60)
        knowledge = [item.copy() for item in ira_ml_knowledge_memory if item.get('tenant_id') == auth.tenant_id]
        jobs = [item.copy() for item in ira_ml_jobs_memory if item.get('tenant_id') == auth.tenant_id][-20:]
        models = [item.copy() for item in ira_ml_models_memory if item.get('tenant_id') == auth.tenant_id][-20:]
        documents: dict[str, dict[str, Any]] = {}
        for item in knowledge:
            document_id = str(item.get('document_id', '')).strip()
            if not document_id:
                continue
            existing = documents.get(document_id)
            if existing is None:
                documents[document_id] = {
                    'document_id': document_id,
                    'title': item.get('title', ''),
                    'source': item.get('source', ''),
                    'tags': item.get('tags', []),
                    'chunk_count': 1,
                    'embedding_backend': item.get('embedding_backend', 'local_hash'),
                    'updated_at': item.get('updated_at', item.get('created_at', '')),
                }
            else:
                existing['chunk_count'] = int(existing.get('chunk_count', 0) or 0) + 1
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'summary': _ml_summary(auth.tenant_id),
            'memory': memory_system.overview(auth.tenant_id),
            'documents': list(documents.values())[-25:],
            'jobs': jobs,
            'models': models,
        }

    @router.get('/memory/overview')
    def ira_memory_overview(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:memory:overview', 120, 60)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'memory': memory_system.overview(auth.tenant_id),
        }

    @router.get('/memory/short-term')
    def ira_short_term_memory(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:memory:short-term', 120, 60)
        messages = memory_system.get_short_term_messages(auth.tenant_id, limit=20)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'messages': messages}

    @router.get('/memory/structured')
    def ira_structured_memory_list(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:memory:structured:list', 120, 60)
        records = memory_system.list_structured_memory(auth.tenant_id)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'records': records}

    @router.post('/memory/structured/upsert')
    def ira_structured_memory_upsert(payload: IRAStructuredMemoryUpsertRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:memory:structured:upsert', 60, 60)
        record = memory_system.upsert_structured_memory(
            tenant_id=auth.tenant_id,
            memory_type=payload.memory_type,
            memory_key=payload.memory_key,
            payload=payload.payload,
        )
        event = _append_ira_event(auth.tenant_id, 'structured_memory_upserted', {
            'memory_type': payload.memory_type,
            'memory_key': payload.memory_key,
            'source': record.get('source', 'in_memory'),
        })
        _audit(auth.tenant_id, 'ira_structured_memory_upserted', {'event_id': event['id'], 'memory_key': payload.memory_key})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'record': record, 'event_id': event['id']}

    @router.get('/agent/frameworks')
    def ira_agent_frameworks(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:agent:frameworks', 120, 60)
        runtime = _agent_runtime_for_tenant(auth.tenant_id)

        records = memory_system.list_structured_memory(auth.tenant_id, memory_type='preference')
        record = next((item for item in records if item.get('memory_key') == 'agent_framework_auto'), None)
        tenant_auto_framework = 'auto'
        if isinstance(record, dict):
            payload = record.get('payload')
            if isinstance(payload, dict):
                payload_map = cast(dict[str, Any], payload)
                framework_value = str(payload_map.get('framework', '')).strip().lower()
                if framework_value in {'langchain', 'semantic_kernel', 'native_secure_loop'}:
                    tenant_auto_framework = framework_value

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'frameworks': runtime.framework_status(),
            'brain': ai_brain.capabilities(),
            'auto_policy': {
                'env_default': os.getenv('IRA_AGENT_AUTO_FRAMEWORK', '').strip().lower() or 'auto',
                'prefer_tenant_memory': os.getenv('IRA_AGENT_PREFER_TENANT_MEMORY', '1').strip() == '1',
                'tenant_override': tenant_auto_framework,
            },
        }

    @router.get('/agent/brain/capabilities')
    def ira_agent_brain_capabilities(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:agent:brain:capabilities', 120, 60)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'brain': ai_brain.capabilities(),
        }

    @router.post('/agent/brain/reason')
    def ira_agent_brain_reason(payload: IRAAgentBrainReasonRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:agent:brain:reason', 60, 60)
        output = ai_brain.reason(
            prompt=payload.prompt,
            provider=payload.provider,
            tools=[cast(dict[str, Any], item) for item in payload.tools if isinstance(item, dict)],
            temperature=payload.temperature,
            max_tokens=payload.max_tokens,
        )
        reasoning = cast(dict[str, Any], output.get('reasoning', {}))
        event = _append_ira_event(auth.tenant_id, 'agent_brain_reasoned', {
            'provider': reasoning.get('provider', 'fallback_stub'),
            'status': output.get('status', 'fallback'),
        })
        _audit(auth.tenant_id, 'ira_agent_brain_reasoned', {'event_id': event['id']})
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'brain': output,
            'event_id': event['id'],
        }

    @router.post('/agent/preferences', responses={403: {'description': 'Super admin required'}})
    def ira_agent_preferences_update(
        payload: IRAAgentPreferenceUpdateRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:agent:preferences:update', 60, 60)

        with lock:
            control = _get_or_create_control(auth.tenant_id)
            _require_super_admin_for_control(
                control=control,
                x_super_admin_key=x_super_admin_key,
                detail='IRA agent preference updates are restricted to super admin sessions.',
            )

        if payload.auto_framework == 'auto':
            preference_payload = {'framework': '', 'mode': 'auto'}
        else:
            preference_payload = {'framework': payload.auto_framework, 'mode': 'tenant_override'}

        record = memory_system.upsert_structured_memory(
            tenant_id=auth.tenant_id,
            memory_type='preference',
            memory_key='agent_framework_auto',
            payload=preference_payload,
        )
        event = _append_ira_event(auth.tenant_id, 'agent_preference_updated', {
            'auto_framework': payload.auto_framework,
            'source': record.get('source', 'in_memory'),
        })
        _audit(auth.tenant_id, 'ira_agent_preference_updated', {'event_id': event['id'], 'auto_framework': payload.auto_framework})

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'record': record,
            'event_id': event['id'],
        }

    @router.post('/agent/run', responses={403: {'description': 'Super admin required'}, 422: {'description': 'IRA autonomy disabled'}})
    def ira_agent_run(
        payload: IRAAgentRunRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:agent:run', 60, 60)

        with lock:
            control = _get_or_create_control(auth.tenant_id)
            _require_super_admin_for_control(
                control=control,
                x_super_admin_key=x_super_admin_key,
                detail='IRA agent execution is restricted to super admin sessions.',
            )
            if not bool(control.get('autonomy_enabled', True)):
                raise HTTPException(status_code=422, detail=AUTONOMY_DISABLED_DETAIL)

        runtime = _agent_runtime_for_tenant(auth.tenant_id)
        memory_key = payload.memory_key.strip() or f"agent_{_slugify(payload.goal, fallback='run')}_{uuid.uuid4().hex[:8]}"
        run_result = runtime.run(
            tenant_id=auth.tenant_id,
            goal=payload.goal,
            requested_framework=payload.framework,
            max_iterations=payload.max_iterations,
            dry_run=payload.dry_run,
            memory_key=memory_key,
        )

        job: dict[str, Any] = {
            'id': len(ira_ml_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'job_type': 'agent_run',
            'name': str(run_result.get('run_id', '')),
            'objective': payload.goal,
            'framework': str(run_result.get('framework_selected', 'native_secure_loop')),
            'framework_reason': str(run_result.get('framework_reason', '')),
            'iterations_executed': int(run_result.get('iterations_executed', 0)),
            'max_iterations': payload.max_iterations,
            'dry_run': payload.dry_run,
            'status': str(run_result.get('status', 'completed')),
            'created_at': _now_iso(),
            'updated_at': _now_iso(),
        }
        ira_ml_jobs_memory.append(job)

        event = _append_ira_event(auth.tenant_id, 'agent_run_completed', {
            'run_id': run_result.get('run_id', ''),
            'framework_selected': run_result.get('framework_selected', 'native_secure_loop'),
            'iterations_executed': run_result.get('iterations_executed', 0),
            'dry_run': payload.dry_run,
        })
        _audit(auth.tenant_id, 'ira_agent_run_completed', {'event_id': event['id'], 'run_id': run_result.get('run_id', '')})

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'run': run_result,
            'job': job,
            'event_id': event['id'],
        }

    @router.post('/ml/knowledge/upsert')
    def ira_ml_upsert_knowledge(payload: IRAKnowledgeDocumentRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:ml:knowledge:upsert', 60, 60)
        document_id = payload.document_id.strip() or f"doc_{_slugify(payload.title, fallback='knowledge')}_{uuid.uuid4().hex[:8]}"
        chunks = _chunk_text(
            payload.content,
            chunk_size=payload.chunk_size_chars,
            chunk_overlap=min(payload.chunk_overlap_chars, max(0, payload.chunk_size_chars - 20)),
        )
        embedding_backend, vectors = _embed_texts(chunks)
        cleaned_tags = sorted({tag.strip().lower() for tag in payload.tags if tag.strip()})
        created_at = _now_iso()

        with lock:
            ira_ml_knowledge_memory[:] = [
                item for item in ira_ml_knowledge_memory
                if not (item.get('tenant_id') == auth.tenant_id and item.get('document_id') == document_id)
            ]
            for index, chunk in enumerate(chunks):
                vector = vectors[index] if index < len(vectors) else _local_hash_embedding(chunk)
                ira_ml_knowledge_memory.append({
                    'id': len(ira_ml_knowledge_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'document_id': document_id,
                    'chunk_id': f'{document_id}:chunk:{index + 1}',
                    'title': payload.title,
                    'source': payload.source,
                    'tags': cleaned_tags,
                    'metadata': payload.metadata,
                    'content': chunk,
                    'chunk_index': index,
                    'token_count': len(_tokenize_text(chunk)),
                    'chunk_count': len(chunks),
                    'embedding_backend': embedding_backend,
                    'embedding': vector,
                    'tokens': _tokenize_text(chunk),
                    'created_at': created_at,
                    'updated_at': created_at,
                })

        event = _append_ira_event(auth.tenant_id, 'ml_knowledge_upserted', {
            'document_id': document_id,
            'title': payload.title,
            'chunk_count': len(chunks),
            'embedding_backend': embedding_backend,
        })
        sync_result = memory_system.sync_long_term_memory(
            tenant_id=auth.tenant_id,
            records=[item for item in ira_ml_knowledge_memory if item.get('tenant_id') == auth.tenant_id and item.get('document_id') == document_id],
        )
        _audit(auth.tenant_id, 'ira_ml_knowledge_upserted', {'event_id': event['id'], 'document_id': document_id, 'chunk_count': len(chunks)})
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'document': {
                'document_id': document_id,
                'title': payload.title,
                'chunk_count': len(chunks),
                'embedding_backend': embedding_backend,
                'tags': cleaned_tags,
                'source': payload.source,
                'created_at': created_at,
            },
            'memory_sync': sync_result,
            'event_id': event['id'],
        }

    @router.post('/ml/retrieval/query')
    def ira_ml_retrieval_query(payload: IRARetrievalQueryRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:ml:retrieval:query', 120, 60)
        query_tokens = _tokenize_text(payload.query)
        query_backend, query_vectors = _embed_texts([payload.query])
        query_vector = query_vectors[0] if query_vectors else _local_hash_embedding(payload.query)
        tenant_chunks = [item for item in ira_ml_knowledge_memory if item.get('tenant_id') == auth.tenant_id]

        scored_results: list[dict[str, Any]] = []
        for item in tenant_chunks:
            candidate_vector = cast(list[float], item.get('embedding', [])) if isinstance(item.get('embedding'), list) else []
            candidate_tokens = cast(list[str], item.get('tokens', [])) if isinstance(item.get('tokens'), list) else []
            vector_score = _cosine_similarity(query_vector, candidate_vector) if str(item.get('embedding_backend', '')) == query_backend else 0.0
            lexical_score = _lexical_overlap_score(query_tokens, candidate_tokens)
            total_score = round(max(0.0, (vector_score * 0.72) + (lexical_score * 0.28)), 4)
            if total_score < payload.min_score:
                continue
            scored_results.append({
                'document_id': item.get('document_id', ''),
                'chunk_id': item.get('chunk_id', ''),
                'title': item.get('title', ''),
                'source': item.get('source', ''),
                'tags': item.get('tags', []),
                'content': item.get('content', ''),
                'score': total_score,
                'signals': {
                    'vector_score': round(vector_score, 4),
                    'lexical_score': round(lexical_score, 4),
                    'embedding_backend': item.get('embedding_backend', 'local_hash'),
                },
            })

        scored_results.sort(key=lambda item: (-float(item.get('score', 0.0)), str(item.get('chunk_id', ''))))
        top_results = scored_results[:payload.top_k]
        if top_results:
            synthesis = 'IRA RAG synthesis: ' + ' '.join(
                f"[{result.get('title', 'Knowledge')}] {str(result.get('content', ''))[:180]}"
                for result in top_results[:3]
            )
        else:
            synthesis = 'IRA RAG synthesis: no relevant training knowledge is indexed yet. Load source documents before querying.'

        event = _append_ira_event(auth.tenant_id, 'ml_retrieval_query', {
            'query': payload.query[:240],
            'top_k': payload.top_k,
            'result_count': len(top_results),
            'embedding_backend': query_backend,
        })
        _audit(auth.tenant_id, 'ira_ml_retrieval_query', {'event_id': event['id'], 'result_count': len(top_results)})
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'query': payload.query,
            'embedding_backend': query_backend,
            'memory_backend': top_results[0].get('provider', 'in_memory') if top_results else 'in_memory',
            'results': top_results,
            'synthesis': synthesis,
            'event_id': event['id'],
        }

    @router.post('/ml/fine-tuning/jobs', responses={403: {'description': 'Super admin required'}, 422: {'description': 'Provider configuration missing'}})
    def ira_ml_create_fine_tuning_job(
        payload: IRAFineTuningJobRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:ml:fine-tuning:create', 30, 60)
        control = _get_or_create_control(auth.tenant_id)
        _require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail='IRA ML fine-tuning jobs are restricted to super admin sessions.',
        )

        provider_job_id = ''
        provider_response: dict[str, Any] = {}
        status = 'draft'
        endpoint = payload.endpoint_url.strip()

        if not payload.dry_run:
            if payload.provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY', '').strip()
                if not api_key:
                    raise HTTPException(status_code=422, detail='OpenAI fine-tuning requires OPENAI_API_KEY.')
                if not payload.training_file_id.strip():
                    raise HTTPException(status_code=422, detail='OpenAI fine-tuning requires training_file_id.')
                try:
                    with httpx.Client(timeout=30.0) as client:
                        response = client.post(
                            'https://api.openai.com/v1/fine_tuning/jobs',
                            headers={
                                'Authorization': f'Bearer {api_key}',
                                'Content-Type': APPLICATION_JSON,
                            },
                            json={
                                'model': payload.base_model,
                                'training_file': payload.training_file_id,
                                'validation_file': payload.validation_file_id or None,
                                'suffix': payload.suffix or None,
                                'hyperparameters': payload.hyperparameters or None,
                                'metadata': payload.metadata or None,
                            },
                        )
                    provider_response = cast(dict[str, Any], response.json()) if response.headers.get('content-type', '').startswith(APPLICATION_JSON) else {'detail': response.text}
                    if not response.is_success:
                        raise HTTPException(status_code=422, detail=f'OpenAI fine-tuning rejected the job: {provider_response}')
                    provider_job_id = str(provider_response.get('id', '')).strip()
                    status = str(provider_response.get('status', 'submitted')).strip() or 'submitted'
                except HTTPException:
                    raise
                except Exception as ex:
                    raise HTTPException(status_code=422, detail=f'OpenAI fine-tuning dispatch failed: {ex}') from ex
            else:
                endpoint = endpoint or os.getenv('IRA_CUSTOM_FINETUNE_ENDPOINT', '').strip()
                if not endpoint:
                    raise HTTPException(status_code=422, detail='Custom fine-tuning requires endpoint_url or IRA_CUSTOM_FINETUNE_ENDPOINT.')
                headers = {'Content-Type': APPLICATION_JSON}
                bearer_token = os.getenv('IRA_CUSTOM_FINETUNE_BEARER_TOKEN', '').strip()
                if bearer_token:
                    headers['Authorization'] = f'Bearer {bearer_token}'
                try:
                    with httpx.Client(timeout=30.0) as client:
                        response = client.post(
                            endpoint,
                            headers=headers,
                            json={
                                'base_model': payload.base_model,
                                'training_file_id': payload.training_file_id,
                                'validation_file_id': payload.validation_file_id,
                                'suffix': payload.suffix,
                                'hyperparameters': payload.hyperparameters,
                                'metadata': payload.metadata,
                            },
                        )
                    provider_response = cast(dict[str, Any], response.json()) if response.headers.get('content-type', '').startswith(APPLICATION_JSON) else {'detail': response.text}
                    if not response.is_success:
                        raise HTTPException(status_code=422, detail=f'Custom fine-tuning rejected the job: {provider_response}')
                    provider_job_id = str(provider_response.get('id', '') or provider_response.get('job_id', '')).strip()
                    status = str(provider_response.get('status', 'submitted')).strip() or 'submitted'
                except HTTPException:
                    raise
                except Exception as ex:
                    raise HTTPException(status_code=422, detail=f'Custom fine-tuning dispatch failed: {ex}') from ex

        job: dict[str, Any] = {
            'id': len(ira_ml_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'job_type': 'fine_tuning',
            'provider': payload.provider,
            'base_model': payload.base_model,
            'training_file_id': payload.training_file_id,
            'validation_file_id': payload.validation_file_id,
            'suffix': payload.suffix,
            'hyperparameters': payload.hyperparameters,
            'metadata': payload.metadata,
            'status': status,
            'dry_run': payload.dry_run,
            'provider_job_id': provider_job_id,
            'endpoint_url': endpoint,
            'created_at': _now_iso(),
            'updated_at': _now_iso(),
        }
        ira_ml_jobs_memory.append(job)
        model_record = _register_model_record(
            tenant_id=auth.tenant_id,
            model_type='fine_tuned_model',
            model_name=payload.suffix.strip() or payload.base_model,
            provider=payload.provider,
            source_job_id=str(job['id']),
            status='draft' if payload.dry_run else status,
            metadata={'base_model': payload.base_model, 'provider_job_id': provider_job_id},
        )

        event = _append_ira_event(auth.tenant_id, 'ml_fine_tuning_job_created', {
            'job_id': job['id'],
            'provider': payload.provider,
            'dry_run': payload.dry_run,
            'status': status,
        })
        _audit(auth.tenant_id, 'ira_ml_fine_tuning_job_created', {'event_id': event['id'], 'job_id': job['id'], 'provider': payload.provider})
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'job': job,
            'model': model_record,
            'provider_response': provider_response,
            'event_id': event['id'],
        }

    @router.post('/ml/pipelines', responses={403: {'description': 'Super admin required'}})
    def ira_ml_create_pipeline(
        payload: IRATrainingPipelineRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:ml:pipelines:create', 30, 60)
        control = _get_or_create_control(auth.tenant_id)
        _require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail='IRA ML pipeline creation is restricted to super admin sessions.',
        )

        selected_framework, runtime_ready, framework_reason = _choose_pipeline_framework(payload)
        document_set = {str(item.get('document_id', '')).strip() for item in ira_ml_knowledge_memory if item.get('tenant_id') == auth.tenant_id}
        selected_documents = [document_id for document_id in payload.dataset_document_ids if document_id in document_set]
        plan_steps = [
            'Validate dataset coverage and schema.',
            'Prepare train/validation split and feature pipeline.',
            f'Execute {payload.pipeline_type} workflow on {selected_framework}.',
            'Run offline evaluation and human review gates.',
            'Register promoted model and expose retrieval/fine-tune telemetry.',
        ]
        if payload.dry_run:
            status = 'planned'
        elif runtime_ready:
            status = 'queued'
        else:
            status = 'waiting_for_runtime'

        job: dict[str, Any] = {
            'id': len(ira_ml_jobs_memory) + 1,
            'tenant_id': auth.tenant_id,
            'job_type': 'pipeline',
            'name': payload.name,
            'objective': payload.objective,
            'pipeline_type': payload.pipeline_type,
            'framework': selected_framework,
            'runtime_ready': runtime_ready,
            'framework_reason': framework_reason,
            'dataset_document_ids': selected_documents,
            'requested_document_ids': payload.dataset_document_ids,
            'model_name': payload.model_name,
            'epochs': payload.epochs,
            'learning_rate': payload.learning_rate,
            'batch_size': payload.batch_size,
            'dry_run': payload.dry_run,
            'plan_steps': plan_steps,
            'status': status,
            'created_at': _now_iso(),
            'updated_at': _now_iso(),
        }
        ira_ml_jobs_memory.append(job)
        model_record = _register_model_record(
            tenant_id=auth.tenant_id,
            model_type=f'{payload.pipeline_type}_pipeline',
            model_name=payload.model_name.strip() or payload.name,
            provider=selected_framework,
            source_job_id=str(job['id']),
            status=status,
            metadata={'objective': payload.objective, 'dataset_document_count': len(selected_documents)},
        )
        event = _append_ira_event(auth.tenant_id, 'ml_pipeline_created', {
            'job_id': job['id'],
            'pipeline_type': payload.pipeline_type,
            'framework': selected_framework,
            'runtime_ready': runtime_ready,
            'dry_run': payload.dry_run,
        })
        _audit(auth.tenant_id, 'ira_ml_pipeline_created', {'event_id': event['id'], 'job_id': job['id'], 'framework': selected_framework})
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'job': job,
            'model': model_record,
            'event_id': event['id'],
        }

    @router.post('/chat', responses={422: {'description': 'IRA autonomy or connector is disabled'}})
    def ira_chat(payload: IRAMessageRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:chat', 1000, 60)
        with lock:
            control = _get_or_create_control(auth.tenant_id)
            if not bool(control.get('autonomy_enabled', True)):
                raise HTTPException(status_code=422, detail=AUTONOMY_DISABLED_DETAIL)
            if not _connector_enabled(auth.tenant_id, payload.channel):
                raise HTTPException(status_code=422, detail=f'IRA connector for channel {payload.channel} is disabled.')
            session: dict[str, Any] = {
                'id': len(ira_sessions_memory) + 1,
                'tenant_id': auth.tenant_id,
                'role': payload.role,
                'channel': payload.channel,
                'user_message': payload.message,
                'context': payload.context,
                'created_at': _now_iso(),
            }
            ira_sessions_memory.append(session)
        memory_system.append_short_term_message(
            tenant_id=auth.tenant_id,
            role=payload.role,
            channel=payload.channel,
            content=payload.message,
            context=payload.context,
        )
        knowledge_hits = _retrieve_knowledge_context(auth.tenant_id, payload.message, top_k=3)
        # Pull recent conversation history to provide context for short replies like "yes"/"do it"
        recent_history = memory_system.get_short_term_messages(auth.tenant_id, limit=6)
        intent, domain, intent_confidence = _classify_chat_intent(message=payload.message, recent_history=recent_history)
        risk = _chat_risk_assessment(payload.message)
        action_plan = _build_chat_action_plan(intent=intent, domain=domain, risk=risk)
        provider_routing = _extract_chat_provider_routing(payload.context)
        requested_provider = str(provider_routing['requested_provider'])
        selected_brain_provider = cast(str | None, provider_routing['brain_provider'])
        provider_catalog = cast(dict[str, Any], ai_brain.capabilities().get('providers', {}))
        provider_info = cast(dict[str, Any], provider_catalog.get(selected_brain_provider or '', {}) or {})

        provider_requested = requested_provider
        provider_used = 'internal_rule_engine'
        provider_model = 'rule_based'
        provider_status = 'internal_default' if requested_provider == 'auto' else 'internal_forced'
        provider_reasoning = 'IRA internal guarded response path'

        if selected_brain_provider and bool(provider_info.get('configured', False)):
            reasoning = ai_brain.reason(
                prompt=_build_chat_reasoning_prompt(
                    role=payload.role,
                    channel=payload.channel,
                    message=payload.message,
                    intent=intent,
                    domain=domain,
                    risk=risk,
                    action_plan=action_plan,
                    knowledge_hits=knowledge_hits,
                    recent_history=recent_history,
                ),
                provider=cast(Literal['auto', 'openai', 'anthropic', 'google_deepmind', 'deepseek', 'llama', 'mistral'], selected_brain_provider),
                tools=[],
            )
            reasoning_payload = cast(dict[str, Any], reasoning.get('reasoning', {}) or {})
            output_text = str(reasoning_payload.get('output_text', '')).strip()
            provider_model = str(reasoning_payload.get('model', '')).strip() or provider_model

            if reasoning.get('status') == 'ok' and output_text:
                response_text = output_text
                confidence = min(1.0, max(intent_confidence, 0.78))
                provider_used = str(reasoning_payload.get('provider', selected_brain_provider) or selected_brain_provider)
                provider_status = 'external_ok'
                provider_reasoning = 'IRA external reasoning path'
            else:
                response_text, confidence = _ira_response(
                    payload.role,
                    payload.channel,
                    payload.message,
                    knowledge_hits=knowledge_hits,
                    recent_history=recent_history,
                )
                provider_status = 'fell_back_to_internal'
                provider_reasoning = 'Requested external provider returned no usable response'
        else:
            response_text, confidence = _ira_response(
                payload.role,
                payload.channel,
                payload.message,
                knowledge_hits=knowledge_hits,
                recent_history=recent_history,
            )
            if selected_brain_provider:
                provider_status = 'requested_provider_not_configured'
                provider_model = str(provider_info.get('model', '')).strip() or provider_model
                provider_reasoning = 'Requested external provider is not configured; using internal route'
            elif requested_provider not in {'auto', 'internal'}:
                provider_status = 'unsupported_provider_preference'
                provider_reasoning = 'Unsupported provider preference; using internal route'

        confidence = min(1.0, max(confidence, intent_confidence))
        memory_system.append_short_term_message(
            tenant_id=auth.tenant_id,
            role='assistant',
            channel=payload.channel,
            content=response_text,
            context={
                'knowledge_hit_count': len(knowledge_hits),
                'confidence': confidence,
                'intent': intent,
                'domain': domain,
                'provider_requested': provider_requested,
                'provider_used': provider_used,
                'provider_status': provider_status,
            },
        )
        event = _append_ira_event(auth.tenant_id, 'chat_handled', {
            'role': payload.role,
            'channel': payload.channel,
            'session_id': session['id'],
            'knowledge_hit_count': len(knowledge_hits),
            'confidence': round(confidence, 3),
            'intent': intent,
            'domain': domain,
            'risk_level': risk.get('risk_level', 'low'),
            'knowledge_documents': [str(hit.get('document_id', '')) for hit in knowledge_hits],
            'provider_requested': provider_requested,
            'provider_used': provider_used,
            'provider_status': provider_status,
        })
        _audit(auth.tenant_id, 'ira_chat_handled', {'session_id': session['id'], 'event_id': event['id'], 'confidence': round(confidence, 3)})
        # Cost tracking: 0.5p per chat interaction
        _record_cost(
            auth.tenant_id,
            'ira_chat',
            units=1,
            unit_cost_pence=0.5,
            metadata={
                'session_id': session['id'],
                'confidence': round(confidence, 3),
                'provider_requested': provider_requested,
                'provider_used': provider_used,
                'provider_status': provider_status,
            },
        )
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'ira': {
                'name': 'IRA',
                'response': response_text,
                'confidence': round(confidence, 3),
                'session_id': session['id'],
                'knowledge_hits': knowledge_hits,
                'intent': intent,
                'domain': domain,
                'risk_assessment': risk,
                'action_plan': action_plan.model_dump(),
                'provider_requested': provider_requested,
                'provider_used': provider_used,
                'provider_model': provider_model,
                'provider_status': provider_status,
                'provider_reasoning': provider_reasoning,
            },
        }

    @router.post('/actions', responses={403: {'description': 'High-impact actions blocked by policy'}, 422: {'description': 'IRA autonomy/connector disabled'}, 423: {'description': 'Protection mode active'}})
    def ira_execute_action(
        payload: IRAActionRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:action', 120, 60)
        with lock:
            control = _get_or_create_control(auth.tenant_id)
            _require_super_admin_for_control(
                control=control,
                x_super_admin_key=x_super_admin_key,
                detail='IRA autonomous execution is restricted to super admin sessions.',
            )
            if not bool(control.get('autonomy_enabled', True)):
                raise HTTPException(status_code=422, detail=AUTONOMY_DISABLED_DETAIL)
            _validate_rbac_abac(payload=payload, auth=auth, verified_super_admin=_is_super_admin(x_super_admin_key))

            if payload.target in HIGH_IMPACT_TARGETS and not bool(control.get('allow_high_impact_actions', False)):
                raise HTTPException(status_code=403, detail='IRA high-impact actions require explicit allow_high_impact_actions=true.')
            if bool(control.get('protection_mode', False)) and payload.target in HIGH_IMPACT_TARGETS:
                raise HTTPException(status_code=423, detail='IRA protection mode is active. High-impact actions are temporarily blocked.')

            if not payload.dry_run and not payload.user_consent:
                raise HTTPException(status_code=422, detail='IRA action requires explicit user consent for execution.')
            if not payload.dry_run and not payload.consent_reference.strip():
                raise HTTPException(status_code=422, detail='IRA action requires consent_reference for auditability.')
            if not payload.dry_run and not payload.risk_analysis_approved:
                raise HTTPException(status_code=422, detail='IRA action requires approved risk analysis before consented execution.')

            if _requires_explicit_approval(payload) and not payload.explicit_approval:
                raise HTTPException(status_code=403, detail='This command is blocked for autonomous mode without explicit approval.')

            requires_human_validation = _requires_human_validation(payload)
            if payload.target in HIGH_IMPACT_TARGETS and not payload.human_validation_approved and not payload.dry_run:
                raise HTTPException(status_code=422, detail='High-impact financial/security operations require human validation approval.')
            if requires_human_validation and not payload.human_validation_approved and not payload.dry_run:
                raise HTTPException(status_code=422, detail='This action requires human validation before execution.')

            dispute_amount = float(payload.payload.get('dispute_amount_gbp', 0.0) or 0.0)
            dispute_mode = bool(payload.payload.get('is_dispute', False)) or ('dispute' in payload.command.strip().lower())
            max_dispute = float(control.get('max_dispute_auto_resolution_gbp', 50.0))
            if dispute_mode and not payload.human_validation_approved and not payload.dry_run:
                raise HTTPException(status_code=422, detail='All dispute operations require human validation approval.')

            if payload.target in {'admin', 'billing', 'credits', 'security'}:
                connector_channel = 'admin'
            elif payload.target == 'email':
                connector_channel = 'email'
            elif payload.target == 'customer_support':
                connector_channel = 'customer_support'
            else:
                connector_channel = 'chat'

            if not payload.dry_run and not _connector_enabled(auth.tenant_id, connector_channel):
                raise HTTPException(status_code=422, detail=f'IRA connector for channel {connector_channel} is disabled.')

            connector = _get_or_create_connector(auth.tenant_id, connector_channel)
            result: dict[str, Any] = {
                'target': payload.target,
                'command': payload.command,
                'dry_run': payload.dry_run,
                'executed': not payload.dry_run,
                'consent_reference': payload.consent_reference,
                'human_validation_required': requires_human_validation,
                'dashboard_scope': payload.dashboard_scope,
            }

            if payload.target in {'customers', 'chats'} and not payload.dry_run:
                chatbot_conversations_memory.append({
                    'id': len(chatbot_conversations_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'chatbot_id': 0,
                    'session_id': f'ira-{len(chatbot_conversations_memory) + 1}',
                    'user_message': str(payload.payload.get('message', payload.command)),
                    'assistant_message': 'Handled by IRA autonomous operations.',
                    'created_at': _now_iso(),
                })
                result['channel'] = 'chat'
                if str(connector.get('provider', 'internal')).strip().lower() == 'slack':
                    result['provider_result'] = _deliver_slack(tenant_id=auth.tenant_id, connector=connector, payload=payload.payload)

            if payload.target == 'email' and not payload.dry_run:
                ticket_id = len(tickets_memory) + 1
                tickets_memory.append({
                    'id': ticket_id,
                    'tenant_id': auth.tenant_id,
                    'subject': str(payload.payload.get('subject', 'IRA automated email action')),
                    'description': str(payload.payload.get('body', payload.command)),
                    'status': 'queued_for_human_validation' if requires_human_validation else 'resolved',
                    'priority': 'normal',
                    'channel': 'email',
                    'created_at': _now_iso(),
                    'updated_at': _now_iso(),
                })
                result['ticket_id'] = ticket_id
                result['provider_result'] = _deliver_email(tenant_id=auth.tenant_id, connector=connector, payload=payload.payload)

            if payload.target in {'admin', 'billing', 'credits', 'security'} and not payload.dry_run:
                result['provider_result'] = _deliver_slack(tenant_id=auth.tenant_id, connector=connector, payload=payload.payload)
                result['requires_review'] = True

            if payload.target == 'customer_support' and not payload.dry_run:
                provider = str(connector.get('provider', 'internal')).strip().lower()
                if provider == 'twilio_whatsapp':
                    result['provider_result'] = _deliver_whatsapp(tenant_id=auth.tenant_id, connector=connector, payload=payload.payload)
                else:
                    ticket_id = len(tickets_memory) + 1
                    tickets_memory.append({
                        'id': ticket_id,
                        'tenant_id': auth.tenant_id,
                        'subject': str(payload.payload.get('subject', 'IRA customer support case')),
                        'description': str(payload.payload.get('body', payload.command)),
                        'status': 'queued_for_human_validation' if requires_human_validation else 'open',
                        'priority': 'high',
                        'channel': 'api',
                        'created_at': _now_iso(),
                        'updated_at': _now_iso(),
                    })
                    result['ticket_id'] = ticket_id
                    result['provider_result'] = {'provider': provider or 'ticket', 'delivery_status': 'ticket_opened'}

            if dispute_mode and not payload.dry_run:
                result['dispute_policy'] = {
                    'auto_resolution_cap_gbp': max_dispute,
                    'amount_gbp': dispute_amount,
                    'human_validation_required': True,
                }
                if dispute_amount <= max_dispute:
                    result['retention_guidance'] = 'Offer credit-first resolution, empathy, and value recap before refund path.'

            if payload.target == 'customers':
                result['lead_support'] = {
                    'lead_capture_enabled': True,
                    'recommended_next_step': 'Collect intent, budget, timeline, and preferred channel before handoff.',
                }

            result['feature_adoption_help'] = {
                'enabled': True,
                'message': 'IRA can guide users through all platform features with role-aware recommendations.',
            }

        event = _append_ira_event(auth.tenant_id, 'action_executed', {
            'target': payload.target,
            'command': payload.command,
            'dry_run': payload.dry_run,
            'high_impact': payload.target in HIGH_IMPACT_TARGETS,
            'consent_reference': payload.consent_reference,
            'human_validation_required': requires_human_validation,
            'explicit_approval': payload.explicit_approval,
        })
        
        # Calculate action confidence: 0.5 base + bonuses for safety gates
        action_confidence = 0.5
        if requires_human_validation:
            action_confidence += 0.2  # human validation increases confidence
        if payload.human_validation_approved and not payload.dry_run:
            action_confidence += 0.15  # explicit approval further increases it
        if payload.dry_run:
            action_confidence -= 0.1  # dry-run lowers confidence (no real impact)
        action_confidence = min(max(action_confidence, 0.0), 1.0)  # clamp to [0, 1]
        
        # Store action snapshot for rollback (only if executed, not dry-run)
        if not payload.dry_run:
            snapshot: dict[str, Any] = {
                'id': len(ira_action_snapshots_memory) + 1,
                'tenant_id': auth.tenant_id,
                'event_id': event['id'],
                'target': payload.target,
                'command': payload.command,
                'before_state': payload.payload.get('before_state', {}),
                'after_state': payload.payload.get('after_state', result),
                'confidence': round(action_confidence, 3),
                'rollback_enabled': payload.target not in {'admin', 'security'},  # some targets can't be rolled back
                'created_at': _now_iso(),
            }
            ira_action_snapshots_memory.append(snapshot)
            result['action_snapshot_id'] = snapshot['id']
        
        _audit(auth.tenant_id, 'ira_action_executed', {
            'event_id': event['id'],
            'target': payload.target,
            'dry_run': payload.dry_run,
            'confidence': round(action_confidence, 3),
            'snapshot_id': result.get('action_snapshot_id'),
        })
        # Cost tracking: 2p for high-impact, 1p for standard actions (dry-runs are free)
        if not payload.dry_run:
            unit_cost = 2.0 if payload.target in HIGH_IMPACT_TARGETS else 1.0
            _record_cost(auth.tenant_id, f'ira_action_{payload.target}', units=1, unit_cost_pence=unit_cost, metadata={'event_id': event['id'], 'target': payload.target})
        # Email notifications for sensitive (non-dry-run) high-impact actions
        if not payload.dry_run and payload.target in HIGH_IMPACT_TARGETS:
            _notify_ops_email(
                tenant_id=auth.tenant_id,
                subject=f'IRA executed {payload.target} action',
                body=(
                    f'IRA executed a high-impact action on target <b>{payload.target}</b>.<br>'
                    f'Command: {payload.command}<br>'
                    f'Confidence: {round(action_confidence * 100, 1)}%<br>'
                    f'Consent reference: {payload.consent_reference}<br>'
                    f'Event ID: {event["id"]}'
                ),
                priority='high',
                event_type='ira_high_impact_action',
            )
            _notify_ops_slack(
                tenant_id=auth.tenant_id,
                title=f'IRA High-Impact Action: {payload.target}',
                text=(
                    f'Target: `{payload.target}` | Command: `{payload.command}`\n'
                    f'Confidence: *{round(action_confidence * 100, 1)}%* | Event: `{event["id"]}`\n'
                    f'Consent ref: `{payload.consent_reference}`'
                ),
                priority='high',
                event_type='ira_high_impact_action',
            )
        # Performance log for every real action
        if not payload.dry_run:
            _record_performance(
                auth.tenant_id, f'action_{payload.target}',
                confidence=action_confidence,
                outcome='success',
                metadata={'event_id': event['id'], 'target': payload.target},
            )
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'result': result,
            'confidence': round(action_confidence, 3),
            'event_id': event['id'],
        }

    @router.post('/actions/{action_snapshot_id}/rollback', responses={403: {'description': 'Super admin required'}, 404: {'description': 'Snapshot not found'}, 422: {'description': 'Rollback not possible'}})
    def ira_rollback_action(
        action_snapshot_id: int,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """Rollback an IRA action to its before_state snapshot"""
        enforce_rate_limit(f'{auth.tenant_id}:ira:rollback', 60, 60)
        with lock:
            control = _get_or_create_control(auth.tenant_id)
            _require_super_admin_for_control(
                control=control,
                x_super_admin_key=x_super_admin_key,
                detail='IRA rollback is restricted to super admin sessions.',
            )
            
            snapshot = next(
                (s for s in ira_action_snapshots_memory if s.get('id') == action_snapshot_id and s.get('tenant_id') == auth.tenant_id),
                None,
            )
            if snapshot is None:
                raise HTTPException(status_code=404, detail=f'Action snapshot {action_snapshot_id} not found.')
            if not snapshot.get('rollback_enabled', False):
                raise HTTPException(status_code=422, detail=f"Target '{snapshot.get('target')}' does not support rollback.")
            
            # Create rollback event
            rollback_event = _append_ira_event(auth.tenant_id, 'action_rolled_back', {
                'original_event_id': snapshot.get('event_id'),
                'snapshot_id': action_snapshot_id,
                'target': snapshot.get('target'),
                'restored_state': snapshot.get('before_state', {}),
            })
            
            _audit(auth.tenant_id, 'ira_rollback_executed', {
                'event_id': rollback_event['id'],
                'snapshot_id': action_snapshot_id,
                'target': snapshot.get('target'),
            })
            
            return {
                'status': 'ok',
                'tenant_id': auth.tenant_id,
                'snapshot_id': action_snapshot_id,
                'rollback_event_id': rollback_event['id'],
                'message': f"Rollback initiated for {snapshot.get('target')} action. System will restore to previous state.",
            }

    @router.get('/monitor')
    def ira_monitor(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """Dashboard endpoint: Real-time IRA activity summary"""
        enforce_rate_limit(f'{auth.tenant_id}:ira:monitor', 300, 60)
        
        # Filter for this tenant only
        tenant_events = [e for e in ira_events_memory if e.get('tenant_id') == auth.tenant_id]
        tenant_sessions = [s for s in ira_sessions_memory if s.get('tenant_id') == auth.tenant_id]
        tenant_snapshots = [sn for sn in ira_action_snapshots_memory if sn.get('tenant_id') == auth.tenant_id]
        tenant_costs = [c for c in ira_cost_ledger_memory if c.get('tenant_id') == auth.tenant_id]
        
        # Calculate stats
        total_chats = len([e for e in tenant_events if e.get('event_type') == 'chat_handled'])
        total_actions = len([e for e in tenant_events if e.get('event_type') in ('action_executed', 'batch_action_executed')])
        failed_actions = len([e for e in tenant_events if e.get('event_type') == 'action_executed' and e.get('payload', {}).get('dry_run')])
        
        # Calculate average confidence from snapshots
        confidences = [float(sn.get('confidence', 0.5)) for sn in tenant_snapshots if sn.get('confidence')]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        total_cost_pence = sum(float(c.get('total_cost_pence', 0)) for c in tenant_costs)
        
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'recent_events': sorted(tenant_events, key=lambda e: e.get('created_at', ''), reverse=True)[:20],
            'recent_sessions': sorted(tenant_sessions, key=lambda s: s.get('created_at', ''), reverse=True)[:20],
            'recent_snapshots': sorted(tenant_snapshots, key=lambda sn: sn.get('created_at', ''), reverse=True)[:20],
            'stats': {
                'avg_confidence': round(avg_confidence, 3),
                'total_chats': total_chats,
                'total_actions': total_actions,
                'failed_actions': failed_actions,
                'total_cost_pence': round(total_cost_pence, 4),
                'total_cost_gbp': round(total_cost_pence / 100, 6),
            },
        }

    @router.post('/actions/batch', responses={422: {'description': 'IRA autonomy disabled or validation failed'}})
    def ira_batch_actions(
        payload: IRABatchActionsRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """Execute up to 100 IRA actions in a single batch request."""
        enforce_rate_limit(f'{auth.tenant_id}:ira:batch', 20, 60)
        with lock:
            control = _get_or_create_control(auth.tenant_id)
            _require_super_admin_for_control(
                control=control,
                x_super_admin_key=x_super_admin_key,
                detail='IRA batch actions are restricted to super admin sessions.',
            )
            if not bool(control.get('autonomy_enabled', True)):
                raise HTTPException(status_code=422, detail=AUTONOMY_DISABLED_DETAIL)

        results: list[dict[str, Any]] = []
        total_cost_pence = 0.0
        high_impact_count = 0

        for idx, item in enumerate(payload.actions):
            item_dry_run = payload.dry_run or item.dry_run
            is_high_impact = item.target in HIGH_IMPACT_TARGETS

            if is_high_impact and not payload.human_validation_approved:
                results.append({
                    'index': idx,
                    'target': item.target,
                    'command': item.command,
                    'status': 'skipped',
                    'reason': 'High-impact target requires human_validation_approved=true',
                })
                continue

            item_confidence = 0.6  # batch items start at moderate confidence
            if payload.human_validation_approved:
                item_confidence += 0.15
            if payload.risk_analysis_approved:
                item_confidence += 0.1
            if item_dry_run:
                item_confidence -= 0.1
            item_confidence = min(max(item_confidence, 0.0), 1.0)

            # Log event
            event = _append_ira_event(auth.tenant_id, 'batch_action_executed', {
                'batch_index': idx,
                'target': item.target,
                'command': item.command,
                'dry_run': item_dry_run,
                'confidence': round(item_confidence, 3),
                'consent_reference': payload.consent_reference,
            })

            # Track cost (1p standard, 2p high-impact; free if dry-run)
            if not item_dry_run:
                unit_cost = 2.0 if is_high_impact else 1.0
                total_cost_pence += unit_cost
                _record_cost(auth.tenant_id, f'ira_batch_{item.target}', units=1, unit_cost_pence=unit_cost, metadata={'batch_index': idx})
                if is_high_impact:
                    high_impact_count += 1

            # Store snapshot if executed
            if not item_dry_run:
                snap: dict[str, Any] = {
                    'id': len(ira_action_snapshots_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'event_id': event['id'],
                    'target': item.target,
                    'command': item.command,
                    'before_state': item.payload.get('before_state', {}),
                    'after_state': {},
                    'confidence': round(item_confidence, 3),
                    'rollback_enabled': item.target not in {'admin', 'security'},
                    'created_at': _now_iso(),
                }
                ira_action_snapshots_memory.append(snap)

            results.append({
                'index': idx,
                'target': item.target,
                'command': item.command,
                'status': 'dry_run' if item_dry_run else 'executed',
                'confidence': round(item_confidence, 3),
                'event_id': event['id'],
            })

        _audit(auth.tenant_id, 'ira_batch_executed', {
            'total': len(payload.actions),
            'executed': sum(1 for r in results if r.get('status') == 'executed'),
            'skipped': sum(1 for r in results if r.get('status') == 'skipped'),
            'total_cost_pence': round(total_cost_pence, 4),
        })

        # Notify ops if batch had real high-impact actions
        if high_impact_count > 0:
            _notify_ops_email(
                tenant_id=auth.tenant_id,
                subject=f'IRA batch executed {high_impact_count} high-impact actions',
                body=(
                    f'IRA batch completed with <b>{high_impact_count} high-impact actions</b>.<br>'
                    f'Total actions: {len(payload.actions)}<br>'
                    f'Total estimated cost: {round(total_cost_pence / 100, 4)} GBP<br>'
                    f'Consent reference: {payload.consent_reference}'
                ),
                priority='high',
                event_type='ira_batch_high_impact',
            )
            _notify_ops_slack(
                tenant_id=auth.tenant_id,
                title=f'IRA Batch: {high_impact_count} High-Impact Actions',
                text=(
                    f'Batch completed: *{len(payload.actions)} total* | *{high_impact_count} high-impact*\n'
                    f'Cost: *£{round(total_cost_pence / 100, 4)}* | Consent: `{payload.consent_reference}`'
                ),
                priority='high',
                event_type='ira_batch_high_impact',
            )
        # Performance log for the entire batch
        _record_performance(
            auth.tenant_id, 'batch_action',
            confidence=0.7,
            outcome='success',
            metadata={'total': len(payload.actions), 'executed': sum(1 for r in results if r.get('status') == 'executed')},
        )

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'total': len(payload.actions),
            'executed': sum(1 for r in results if r.get('status') == 'executed'),
            'skipped': sum(1 for r in results if r.get('status') == 'skipped'),
            'total_cost_pence': round(total_cost_pence, 4),
            'total_cost_gbp': round(total_cost_pence / 100, 6),
            'results': results,
        }

    @router.get('/costs')
    def ira_cost_summary(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """Cost tracking summary — total spend per action type for this tenant."""
        enforce_rate_limit(f'{auth.tenant_id}:ira:costs', 120, 60)
        tenant_costs = [c for c in ira_cost_ledger_memory if c.get('tenant_id') == auth.tenant_id]

        # Aggregate by action_type
        by_type: dict[str, dict[str, Any]] = {}
        for entry in tenant_costs:
            atype = str(entry.get('action_type', 'unknown'))
            if atype not in by_type:
                by_type[atype] = {'count': 0, 'total_cost_pence': 0.0}
            by_type[atype]['count'] += int(entry.get('units', 1))
            by_type[atype]['total_cost_pence'] = round(by_type[atype]['total_cost_pence'] + float(entry.get('total_cost_pence', 0)), 4)

        total_pence = sum(c.get('total_cost_pence', 0.0) for c in tenant_costs)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'total_cost_pence': round(total_pence, 4),
            'total_cost_gbp': round(total_pence / 100, 6),
            'by_action_type': by_type,
            'recent_ledger': sorted(tenant_costs, key=lambda c: c.get('created_at', ''), reverse=True)[:20],
        }

    @router.get('/performance')
    def ira_performance_analytics(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """Performance analytics — latency, confidence trends, outcome rates per action type."""
        enforce_rate_limit(f'{auth.tenant_id}:ira:performance', 120, 60)
        logs = [p for p in ira_performance_log_memory if p.get('tenant_id') == auth.tenant_id]

        # Aggregate by action_type
        by_type: dict[str, dict[str, Any]] = {}
        for entry in logs:
            atype = str(entry.get('action_type', 'unknown'))
            if atype not in by_type:
                by_type[atype] = {'count': 0, 'success': 0, 'failure': 0, 'total_confidence': 0.0, 'total_latency_ms': 0.0}
            by_type[atype]['count'] += 1
            outcome = str(entry.get('outcome', 'success'))
            if outcome == 'success':
                by_type[atype]['success'] += 1
            elif outcome == 'failure':
                by_type[atype]['failure'] += 1
            by_type[atype]['total_confidence'] += float(entry.get('confidence', 0.5))
            by_type[atype]['total_latency_ms'] += float(entry.get('latency_ms', 0.0))

        # Compute averages
        summary: dict[str, Any] = {}
        for atype, stats in by_type.items():
            count = stats['count']
            summary[atype] = {
                'count': count,
                'success_rate': round(stats['success'] / count, 3) if count else 0.0,
                'failure_rate': round(stats['failure'] / count, 3) if count else 0.0,
                'avg_confidence': round(stats['total_confidence'] / count, 3) if count else 0.0,
                'avg_latency_ms': round(stats['total_latency_ms'] / count, 2) if count else 0.0,
            }

        overall_success = sum(1 for p in logs if p.get('outcome') == 'success')
        overall_confidence = sum(float(p.get('confidence', 0.5)) for p in logs)
        total = len(logs)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'total_data_points': total,
            'overall_success_rate': round(overall_success / total, 3) if total else 0.0,
            'overall_avg_confidence': round(overall_confidence / total, 3) if total else 0.0,
            'by_action_type': summary,
            'recent': sorted(logs, key=lambda p: p.get('created_at', ''), reverse=True)[:20],
        }

    @router.post('/ab-tests', responses={422: {'description': 'Traffic split must sum to 1.0 and match variant count'}})
    def ira_create_ab_test(payload: IRAAbTestCreateRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """Create a new A/B test to compare IRA decision variants."""
        enforce_rate_limit(f'{auth.tenant_id}:ira:abtest', 60, 60)

        if payload.traffic_split and len(payload.traffic_split) != len(payload.variants):
            raise HTTPException(status_code=422, detail='traffic_split length must match variants length.')
        if payload.traffic_split:
            total_split = sum(payload.traffic_split)
            if abs(total_split - 1.0) > 0.01:
                raise HTTPException(status_code=422, detail=f'traffic_split must sum to 1.0, got {round(total_split, 4)}.')

        # Even split if not provided
        split = payload.traffic_split if payload.traffic_split else [round(1.0 / len(payload.variants), 4)] * len(payload.variants)

        test: dict[str, Any] = {
            'id': len(ira_ab_tests_memory) + 1,
            'tenant_id': auth.tenant_id,
            'name': payload.name,
            'description': payload.description,
            'variants': payload.variants,
            'traffic_split': split,
            'metric': payload.metric,
            'target_scope': payload.target_scope,
            'status': 'running',
            'results': {v: {'impressions': 0, 'successes': 0, 'failures': 0, 'total_value': 0.0} for v in payload.variants},
            'created_at': _now_iso(),
            'updated_at': _now_iso(),
        }
        ira_ab_tests_memory.append(test)
        _audit(auth.tenant_id, 'ira_ab_test_created', {'test_id': test['id'], 'name': payload.name, 'variants': payload.variants})
        _record_performance(auth.tenant_id, 'ab_test_created', confidence=0.5, metadata={'test_id': test['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'test': test}

    @router.post('/ab-tests/record', responses={404: {'description': 'Test not found'}, 422: {'description': 'Unknown variant or test not running'}})
    def ira_record_ab_result(payload: IRAAbTestRecordRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """Record an outcome for a variant in a running A/B test."""
        enforce_rate_limit(f'{auth.tenant_id}:ira:abtest:record', 600, 60)
        test = next(
            (t for t in ira_ab_tests_memory if t.get('id') == payload.test_id and t.get('tenant_id') == auth.tenant_id),
            None,
        )
        if test is None:
            raise HTTPException(status_code=404, detail=f'A/B test {payload.test_id} not found.')
        if test.get('status') != 'running':
            raise HTTPException(status_code=422, detail='A/B test is not in running state.')
        if payload.variant not in test.get('variants', []):
            raise HTTPException(status_code=422, detail=f"Variant '{payload.variant}' not in test variants {test['variants']}.")

        variant_stats = test['results'][payload.variant]
        variant_stats['impressions'] += 1
        variant_stats['total_value'] = round(variant_stats['total_value'] + payload.value, 4)
        if payload.outcome == 'success':
            variant_stats['successes'] += 1
        elif payload.outcome == 'failure':
            variant_stats['failures'] += 1
        test['updated_at'] = _now_iso()

        return {'status': 'ok', 'test_id': payload.test_id, 'variant': payload.variant, 'variant_stats': variant_stats}

    @router.get('/ab-tests')
    def ira_list_ab_tests(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        """List all A/B tests for this tenant with computed winner analysis."""
        enforce_rate_limit(f'{auth.tenant_id}:ira:abtest:list', 120, 60)
        tests = [t for t in ira_ab_tests_memory if t.get('tenant_id') == auth.tenant_id]

        enriched: list[dict[str, Any]] = []
        for test in tests:
            analysis: dict[str, Any] = {'winner': None, 'confidence': 0.0, 'by_variant': {}}
            best_rate = -1.0
            for variant, stats in test.get('results', {}).items():
                impressions = int(stats.get('impressions', 0))
                successes = int(stats.get('successes', 0))
                rate = round(successes / impressions, 4) if impressions else 0.0
                avg_value = round(float(stats.get('total_value', 0)) / impressions, 4) if impressions else 0.0
                analysis['by_variant'][variant] = {
                    'impressions': impressions,
                    'success_rate': rate,
                    'avg_value': avg_value,
                }
                if rate > best_rate:
                    best_rate = rate
                    analysis['winner'] = variant
                    # Simple confidence: how far ahead is winner vs closest challenger
                    rates = [s.get('successes', 0) / max(s.get('impressions', 1), 1) for s in test['results'].values()]
                    rates_sorted = sorted(rates, reverse=True)
                    gap = rates_sorted[0] - rates_sorted[1] if len(rates_sorted) > 1 else 0.0
                    analysis['confidence'] = round(min(gap * 10 + 0.5, 1.0), 3)
            enriched.append({**test, 'analysis': analysis})

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'total': len(tests),
            'tests': sorted(enriched, key=lambda t: t.get('created_at', ''), reverse=True),
        }

    @router.post('/control/config', responses={403: {'description': 'Super admin required'}, 422: {'description': 'Policy validation failed'}})
    def update_ira_control(
        payload: IRAAutonomyUpdateRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:control', 60, 60)
        with lock:
            control = _get_or_create_control(auth.tenant_id)
            _require_super_admin_for_control(
                control=control,
                x_super_admin_key=x_super_admin_key,
                detail='IRA control updates are restricted to super admin sessions.',
            )
            if not payload.policy_change_human_validation:
                raise HTTPException(status_code=422, detail='Policy updates require human validation confirmation.')

            strict_policy_lock = bool(control.get('strict_policy_lock', True))
            if strict_policy_lock:
                if payload.allow_high_impact_actions:
                    raise HTTPException(status_code=422, detail='Strict policy lock prevents enabling high-impact autonomous actions.')
                if not payload.require_super_admin:
                    raise HTTPException(status_code=422, detail='Strict policy lock prevents disabling super-admin requirement.')

            control['autonomy_enabled'] = payload.autonomy_enabled
            control['allow_high_impact_actions'] = payload.allow_high_impact_actions
            control['min_profit_margin_pct'] = payload.min_profit_margin_pct
            control['suspicious_signal_threshold'] = payload.suspicious_signal_threshold
            control['require_super_admin'] = payload.require_super_admin
            control['max_dispute_auto_resolution_gbp'] = payload.max_dispute_auto_resolution_gbp
            control['strict_policy_lock'] = payload.strict_policy_lock
            control['updated_at'] = _now_iso()
        event = _append_ira_event(auth.tenant_id, 'control_updated', {
            'autonomy_enabled': payload.autonomy_enabled,
            'allow_high_impact_actions': payload.allow_high_impact_actions,
            'min_profit_margin_pct': payload.min_profit_margin_pct,
            'suspicious_signal_threshold': payload.suspicious_signal_threshold,
            'require_super_admin': payload.require_super_admin,
            'max_dispute_auto_resolution_gbp': payload.max_dispute_auto_resolution_gbp,
            'strict_policy_lock': payload.strict_policy_lock,
        })
        _audit(auth.tenant_id, 'ira_control_updated', {'event_id': event['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'control': control, 'event_id': event['id']}

    @router.get('/connectors')
    def list_ira_connectors(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:connectors:list', 120, 60)
        with lock:
            connectors = [_get_or_create_connector(auth.tenant_id, channel).copy() for channel in CONNECTOR_CHANNELS]
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(connectors), 'connectors': connectors}

    @router.post('/connectors/upsert', responses={403: {'description': 'Super admin required'}})
    def upsert_ira_connector(
        payload: IRAConnectorUpsertRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:connectors:upsert', 60, 60)
        with lock:
            control = _get_or_create_control(auth.tenant_id)
            _require_super_admin_for_control(
                control=control,
                x_super_admin_key=x_super_admin_key,
                detail='IRA connector updates are restricted to super admin sessions.',
            )
            connector = _get_or_create_connector(auth.tenant_id, payload.channel)
            connector['enabled'] = payload.enabled
            connector['provider'] = payload.provider
            connector['config'] = payload.config
            connector['updated_at'] = _now_iso()
        event = _append_ira_event(auth.tenant_id, 'connector_updated', {'channel': payload.channel, 'enabled': payload.enabled, 'provider': payload.provider})
        _audit(auth.tenant_id, 'ira_connector_updated', {'event_id': event['id'], 'channel': payload.channel, 'enabled': payload.enabled})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'connector': connector, 'event_id': event['id']}

    @router.get('/finance/health')
    def ira_finance_health(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:finance:health', 120, 60)
        control = _get_or_create_control(auth.tenant_id)
        snapshot = _tenant_revenue_snapshot(auth.tenant_id)
        suspicious_signal = _tenant_suspicious_signal(auth.tenant_id)
        risky = snapshot['profit_margin_pct'] < float(control.get('min_profit_margin_pct', 70.0))
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'finance': snapshot,
            'suspicious_signal': suspicious_signal,
            'thresholds': {'min_profit_margin_pct': control.get('min_profit_margin_pct', 70.0)},
            'risk_state': 'at_risk' if risky else 'healthy',
            'protection_mode': bool(control.get('protection_mode', False)),
        }

    @router.get('/risk/score')
    def ira_risk_score(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:risk:score', 120, 60)
        control = _get_or_create_control(auth.tenant_id)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'risk_signal': _tenant_suspicious_signal(auth.tenant_id),
            'thresholds': {'suspicious_signal_threshold': float(control.get('suspicious_signal_threshold', 0.75))},
            'protection_mode': bool(control.get('protection_mode', False)),
        }

    @router.post('/finance/ingest')
    def ira_ingest_finance_sample(payload: IRAFinanceSampleRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:finance:ingest', 120, 60)
        control = _get_or_create_control(auth.tenant_id)
        total_cost = payload.cogs + payload.credits_cost
        profit_margin_pct = 0.0 if payload.revenue <= 0 else round(((payload.revenue - total_cost) / payload.revenue) * 100.0, 2)
        below_profit_target = profit_margin_pct < float(control.get('min_profit_margin_pct', 70.0))
        suspicious = payload.suspicious_signal_score >= float(control.get('suspicious_signal_threshold', 0.75))
        sample_event = _append_ira_event(auth.tenant_id, 'finance_sample_ingested', {
            'revenue': payload.revenue,
            'cogs': payload.cogs,
            'credits_cost': payload.credits_cost,
            'profit_margin_pct': profit_margin_pct,
            'suspicious_signal_score': payload.suspicious_signal_score,
            'note': payload.note,
        })
        activation_event = None
        if below_profit_target or suspicious:
            control['protection_mode'] = True
            control['blocked_actions'] = list(DEFAULT_BLOCKED_ACTIONS)
            control['updated_at'] = _now_iso()
            activation_event = _append_ira_event(auth.tenant_id, 'protection_mode_activated', {
                'reason': 'profit_below_target' if below_profit_target else 'suspicious_signal',
                'blocked_actions': control['blocked_actions'],
                'metrics': {
                    'profit_margin_pct': profit_margin_pct,
                    'min_profit_margin_pct': control.get('min_profit_margin_pct', 70.0),
                    'suspicious_signal_score': payload.suspicious_signal_score,
                    'suspicious_signal_threshold': control.get('suspicious_signal_threshold', 0.75),
                },
            })
        _audit(auth.tenant_id, 'ira_finance_sample_ingested', {'event_id': sample_event['id'], 'profit_margin_pct': profit_margin_pct, 'protection_mode': bool(control.get('protection_mode', False))})
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'profit_margin_pct': profit_margin_pct,
            'below_profit_target': below_profit_target,
            'suspicious_signal': suspicious,
            'protection_mode': bool(control.get('protection_mode', False)),
            'activation_event_id': activation_event['id'] if activation_event else None,
        }

    @router.post('/control/disable-protection', responses={403: {'description': 'Super admin required'}})
    def disable_protection_mode(
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:control:disable-protection', 30, 60)
        control = _get_or_create_control(auth.tenant_id)
        _require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail='Disabling IRA protection mode is restricted to super admin sessions.',
        )
        control['protection_mode'] = False
        control['blocked_actions'] = []
        control['updated_at'] = _now_iso()
        event = _append_ira_event(auth.tenant_id, 'protection_mode_disabled', {})
        _audit(auth.tenant_id, 'ira_protection_mode_disabled', {'event_id': event['id']})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'protection_mode': False, 'event_id': event['id']}

    @router.post('/learning/feedback')
    def collect_ira_feedback(payload: IRAFeedbackRequest, auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:learning:feedback', 180, 60)
        event = _append_ira_event(auth.tenant_id, 'learning_feedback_collected', {
            'category': payload.category,
            'rating': payload.rating,
            'comment': payload.comment,
            'action_ref': payload.action_ref,
            'actor_role': payload.actor_role,
        })
        _audit(auth.tenant_id, 'ira_learning_feedback_collected', {'event_id': event['id'], 'category': payload.category, 'rating': payload.rating})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'event_id': event['id']}

    @router.get('/disputes/dashboard')
    def ira_disputes_dashboard(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:disputes:dashboard', 120, 60)
        relevant_events = [
            item for item in ira_events_memory
            if item.get('tenant_id') == auth.tenant_id and (
                'dispute' in str(item.get('event_type', '')).lower()
                or bool(item.get('payload', {}).get('is_dispute', False))
            )
        ]
        dispute_tickets = [
            item for item in tickets_memory
            if item.get('tenant_id') == auth.tenant_id and (
                'dispute' in str(item.get('subject', '')).lower()
                or 'dispute' in str(item.get('description', '')).lower()
            )
        ]
        open_items = [item for item in dispute_tickets if str(item.get('status', '')).lower() in {'open', 'queued_for_human_validation'}]
        queued_items = [item for item in dispute_tickets if str(item.get('status', '')).lower() == 'queued_for_human_validation']
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'summary': {
                'total_dispute_events': len(relevant_events),
                'total_dispute_tickets': len(dispute_tickets),
                'open_dispute_tickets': len(open_items),
                'queued_for_human_validation': len(queued_items),
                'human_approval_required_for_all_disputes': True,
            },
            'tickets': dispute_tickets[-50:],
            'recent_dispute_events': relevant_events[-50:],
            'reputation_guardrail': 'Use fair, transparent, and non-coercive retention guidance before any refund refusal path.',
        }

    @router.get('/crm/hybrid-recommendation')
    def ira_crm_hybrid_recommendation(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:crm:hybrid-recommendation', 60, 60)
        control = _get_or_create_control(auth.tenant_id)
        # Keep this read path non-blocking even when Postgres is unavailable.
        governance = control.get('crm_feature_governance')
        if not isinstance(governance, dict):
            governance = _default_crm_governance_map()
            control['crm_feature_governance'] = governance
        connector_health = _probe_crm_connectors()
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'target': 'PostgreSQL-based, open-source, SaaS-friendly CRM with maximum coverage',
            'recommended_hybrid': 'Corteza CRM + Odoo CRM Community',
            'ratings': {
                'corteza_overall': {'score': 90, 'percent': 90},
                'odoo_community_overall': {'score': 88, 'percent': 88},
                'hybrid_overall': {'score': 95, 'percent': 95},
            },
            'hybrid_dimensions': {
                'core_crm_sales': {'score': 96, 'percent': 96},
                'saas_architecture_fit': {'score': 97, 'percent': 97},
                'postgresql_alignment': {'score': 100, 'percent': 100},
                'automation_workflows': {'score': 95, 'percent': 95},
                'integrations_extensibility': {'score': 96, 'percent': 96},
                'security_governance': {'score': 94, 'percent': 94},
                'operational_complexity': {'score': 82, 'percent': 82},
            },
            'platform_integration': {
                'required_stack': ['PostgreSQL', 'Keycloak', 'Kong', 'WAF', 'SIEM'],
                'recommendation': 'Use Corteza for multi-tenant core and low-code objects; use Odoo for sales/ERP-adjacent modules.',
                'connector_health': connector_health,
            },
            'duplication_governance': {
                'policy': 'Keep one source-of-truth per feature and disable duplicates in secondary system via configuration.',
                'ownership': governance,
            },
        }

    @router.get('/crm/connectors/status')
    def ira_crm_connectors_status(auth: AuthDep) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:crm:connectors:status', 60, 60)
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'connectors': _probe_crm_connectors()}

    @router.post('/crm/feature-governance', responses={403: {'description': 'Super admin required'}, 422: {'description': 'Policy validation failed'}})
    def update_crm_feature_governance(
        payload: IRACrmGovernanceUpdateRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:crm:feature-governance', 60, 60)
        with lock:
            control = _get_or_create_control(auth.tenant_id)
            _require_super_admin_for_control(
                control=control,
                x_super_admin_key=x_super_admin_key,
                detail='CRM feature governance updates are restricted to super admin sessions.',
            )
            if not payload.policy_change_human_validation:
                raise HTTPException(status_code=422, detail='CRM governance policy updates require human validation confirmation.')
            if bool(control.get('strict_policy_lock', True)) and not payload.disable_duplicate_in_secondary:
                raise HTTPException(status_code=422, detail='Strict policy lock requires duplicate features to stay disabled in secondary system.')

            governance = _load_crm_governance(auth.tenant_id, control)
            row: dict[str, Any] = {
                'feature': payload.feature,
                'owner': payload.owner,
                'duplicate_disabled': payload.disable_duplicate_in_secondary,
                'secondary_disabled_for': 'odoo' if payload.owner == 'corteza' else 'corteza',
                'notes': payload.notes,
                'updated_at': _now_iso(),
            }
            governance[payload.feature] = row
            control['crm_feature_governance'] = governance
            _persist_crm_governance_row(auth.tenant_id, row)

        event = _append_ira_event(auth.tenant_id, 'crm_feature_governance_updated', {
            'feature': payload.feature,
            'owner': payload.owner,
            'duplicate_disabled': payload.disable_duplicate_in_secondary,
            'notes': payload.notes,
        })
        _audit(auth.tenant_id, 'ira_crm_feature_governance_updated', {'event_id': event['id'], 'feature': payload.feature})
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'governance': control.get('crm_feature_governance', {}), 'event_id': event['id']}

    @router.post('/advisor/recommendations', responses={403: {'description': 'Super admin required'}})
    def get_ira_recommendations(
        payload: IRAAdviceRequest,
        auth: AuthDep,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> dict[str, Any]:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:ira:advisor:recommendations', 90, 60)
        control = _get_or_create_control(auth.tenant_id)
        _require_super_admin_for_control(
            control=control,
            x_super_admin_key=x_super_admin_key,
            detail='IRA advisor recommendations are restricted to super admin sessions.',
        )

        feedback_events = [
            item for item in ira_events_memory
            if item.get('tenant_id') == auth.tenant_id and item.get('event_type') == 'learning_feedback_collected'
        ]
        ratings = [int(item.get('payload', {}).get('rating', 0) or 0) for item in feedback_events]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0

        snapshot = _tenant_revenue_snapshot(auth.tenant_id)
        risk_signal = _tenant_suspicious_signal(auth.tenant_id)
        recommendations: list[dict[str, Any]] = [
            {
                'id': 'guardrail-1',
                'title': 'Keep strict financial guardrails',
                'reason': 'Autonomous billing changes, credit burns, and external transfers stay blocked without explicit approval.',
                'category': 'safety',
            },
            {
                'id': 'growth-1',
                'title': 'Convert conversations into qualified leads',
                'reason': 'Capture intent, budget, timeline, and preferred channel for every customer action request.',
                'category': 'revenue',
            },
            {
                'id': 'adoption-1',
                'title': 'Guide users feature-by-feature',
                'reason': 'Use IRA chat to provide role-aware onboarding for all platform modules.',
                'category': 'feature_adoption',
            },
        ]

        if risk_signal.get('score', 0.0) >= float(control.get('suspicious_signal_threshold', 0.75)):
            recommendations.append({
                'id': 'risk-1',
                'title': 'Increase human validation frequency',
                'reason': 'Current suspicious signal is elevated; keep bulk/ticket/compliance workflows human-approved.',
                'category': 'risk',
            })

        if snapshot.get('profit_margin_pct', 0.0) < float(control.get('min_profit_margin_pct', 70.0)):
            recommendations.append({
                'id': 'margin-1',
                'title': 'Prioritize retention scripts before refunds',
                'reason': 'Margin is below threshold. For disputes <= GBP 50, offer value-preserving alternatives first.',
                'category': 'revenue',
            })

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'objective': payload.objective,
            'horizon_days': payload.horizon_days,
            'metrics': {
                'avg_feedback_rating': avg_rating,
                'feedback_count': len(feedback_events),
                'profit_margin_pct': snapshot.get('profit_margin_pct', 0.0),
                'risk_score': risk_signal.get('score', 0.0),
            },
            'recommendations': recommendations,
            'limits': {
                'dashboard_scope': 'super_admin_dashboard',
                'require_super_admin': bool(control.get('require_super_admin', True)),
                'blocked_autonomous_actions': list(DEFAULT_BLOCKED_ACTIONS),
                'max_dispute_auto_resolution_gbp': float(control.get('max_dispute_auto_resolution_gbp', 50.0)),
            },
        }

    return router
