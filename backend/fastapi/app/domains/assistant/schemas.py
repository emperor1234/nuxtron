"""Assistant request contracts."""

from dataclasses import dataclass
from pydantic import BaseModel
from pydantic import Field
from typing import Any
from typing import Literal


class IRAMessageRequest(BaseModel):
    role: Literal["customer", "admin", "operator"] = "customer"
    channel: Literal["chat", "email", "ticket", "webhook"] = "chat"
    message: str = Field(min_length=1, max_length=4000)
    context: dict[str, Any] = Field(default_factory=dict)


class IRAActionRequest(BaseModel):
    target: Literal["customers", "admin", "email", "chats", "billing", "credits", "security", "customer_support"]
    command: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    dashboard_scope: Literal["super_admin_dashboard"] = "super_admin_dashboard"
    actor_role: Literal["super_admin", "admin", "operator", "customer"] = "super_admin"
    actor_attributes: dict[str, Any] = Field(default_factory=dict)
    user_consent: bool = False
    consent_reference: str = Field(default="", max_length=160)
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
    category: Literal["quality", "safety", "usability", "revenue", "feature_adoption"] = "quality"
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=4000)
    action_ref: str = Field(default="", max_length=120)
    actor_role: Literal["super_admin", "admin", "operator", "customer"] = "customer"


class IRAAdviceRequest(BaseModel):
    objective: str = Field(default="growth", min_length=1, max_length=160)
    horizon_days: int = Field(default=30, ge=1, le=365)
    include_feature_adoption: bool = True


class IRACrmGovernanceUpdateRequest(BaseModel):
    feature: Literal[
        "multi_tenancy",
        "low_code_objects",
        "sales_pipeline_and_erp_adjacent",
        "cross_platform_workflow_orchestration",
        "ecosystem_modules",
    ]
    owner: Literal["corteza", "odoo"]
    disable_duplicate_in_secondary: bool = True
    policy_change_human_validation: bool = False
    notes: str = Field(default="", max_length=500)


class IRAFinanceSampleRequest(BaseModel):
    revenue: float = Field(ge=0.0)
    cogs: float = Field(default=0.0, ge=0.0)
    credits_cost: float = Field(default=0.0, ge=0.0)
    suspicious_signal_score: float = Field(default=0.0, ge=0.0, le=1.0)
    note: str = Field(default="", max_length=300)


class IRAConnectorUpsertRequest(BaseModel):
    channel: Literal["chat", "email", "ticket", "webhook", "admin", "customer_support"]
    enabled: bool = True
    provider: str = Field(default="internal", max_length=80)
    config: dict[str, Any] = Field(default_factory=dict)


class IRAKnowledgeDocumentRequest(BaseModel):
    document_id: str = Field(default="", max_length=120)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=200000)
    source: str = Field(default="internal", max_length=240)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_size_chars: int = Field(default=900, ge=200, le=4000)
    chunk_overlap_chars: int = Field(default=120, ge=0, le=500)


class IRARetrievalQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=12)
    min_score: float = Field(default=0.12, ge=0.0, le=1.0)


class IRAFineTuningJobRequest(BaseModel):
    provider: Literal["openai", "custom_http"] = "openai"
    base_model: str = Field(min_length=1, max_length=160)
    training_file_id: str = Field(default="", max_length=160)
    validation_file_id: str = Field(default="", max_length=160)
    suffix: str = Field(default="", max_length=64)
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    endpoint_url: str = Field(default="", max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class IRATrainingPipelineRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    objective: str = Field(min_length=1, max_length=500)
    pipeline_type: Literal["rag", "fine_tuning", "embedding", "custom"] = "rag"
    framework: Literal["auto", "pytorch", "tensorflow", "sentence_transformers"] = "auto"
    dataset_document_ids: list[str] = Field(default_factory=list)
    model_name: str = Field(default="", max_length=160)
    epochs: int = Field(default=3, ge=1, le=100)
    learning_rate: float = Field(default=0.0001, gt=0.0, le=1.0)
    batch_size: int = Field(default=16, ge=1, le=2048)
    dry_run: bool = True


class IRAStructuredMemoryUpsertRequest(BaseModel):
    memory_type: Literal["user_profile", "task", "preference", "workflow_state"] = "user_profile"
    memory_key: str = Field(min_length=1, max_length=160)
    payload: dict[str, Any] = Field(default_factory=dict)


class IRAAgentRunRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)
    framework: Literal["auto", "langchain", "semantic_kernel", "autogpt", "crewai", "native_secure_loop"] = "auto"
    max_iterations: int = Field(default=4, ge=1, le=12)
    dry_run: bool = True
    memory_key: str = Field(default="", max_length=160)


class IRABatchActionItem(BaseModel):
    target: Literal["customers", "admin", "email", "chats", "billing", "credits", "security", "customer_support"]
    command: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


class IRABatchActionsRequest(BaseModel):
    actions: list[IRABatchActionItem] = Field(min_length=1, max_length=100)
    dry_run: bool = True
    consent_reference: str = Field(default="", max_length=160)
    human_validation_approved: bool = False
    risk_analysis_approved: bool = False


class IRAAbTestCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    variants: list[str] = Field(min_length=2, max_length=10)
    metric: str = Field(default="conversion_rate", max_length=80)
    traffic_split: list[float] = Field(default_factory=list)
    target_scope: str = Field(default="all", max_length=80)


class IRAAbTestRecordRequest(BaseModel):
    test_id: int
    variant: str = Field(min_length=1, max_length=80)
    outcome: Literal["success", "failure", "neutral"] = "neutral"
    value: float = Field(default=1.0, ge=0.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IRAAgentPreferenceUpdateRequest(BaseModel):
    auto_framework: Literal["auto", "langchain", "semantic_kernel", "native_secure_loop"] = "auto"


class IRAAgentBrainReasonRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=12000)
    provider: Literal["auto", "openai", "anthropic", "google_deepmind", "deepseek", "llama", "mistral"] = "auto"
    tools: list[Any] = Field(default_factory=list)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    max_tokens: int = Field(default=800, ge=64, le=4096)


class IRAFrontierPlanRequest(BaseModel):
    objective: str = Field(
        default="Build an AI workforce with reliable autonomous execution.", min_length=8, max_length=600
    )
    priority: Literal["reliability", "cost", "speed"] = "reliability"
    include_free_open_source_only: bool = False
    require_multimodal: bool = True
    require_graph_memory: bool = True
    create_execution_tasks: bool = True


class IRAFrontierEnvTemplateApplyRequest(BaseModel):
    target_file: str = Field(default=".env.frontier.draft", min_length=1, max_length=80)
    mode: Literal["overwrite", "merge_non_destructive", "merge_and_backup"] = "overwrite"


class IRACopilotPlanRequest(BaseModel):
    objective: str = Field(
        default="Integrate GitHub Copilot chat and agent workflows into the IRA platform.", min_length=8, max_length=600
    )
    priority: Literal["reliability", "cost", "speed"] = "reliability"
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
