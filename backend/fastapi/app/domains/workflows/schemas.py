"""Workflow request contracts and validation limits."""

from pydantic import BaseModel
from pydantic import Field
from typing import Any


class WorkflowStepModel(BaseModel):
    step_id: str = Field(min_length=1, max_length=50)
    action_type: str = Field(min_length=1, max_length=40)
    config: dict[str, Any] = Field(default_factory=dict)
    next_step_id: str = Field(default="", max_length=50)
    branch_yes: str = Field(default="", max_length=50)
    branch_no: str = Field(default="", max_length=50)
    delay_hours: int = Field(default=0, ge=0, le=8760)


class WorkflowTrigger(BaseModel):
    trigger_type: str = Field(min_length=1, max_length=40)
    conditions: list[dict[str, Any]] = Field(default_factory=list, max_length=20)


class WorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    trigger: WorkflowTrigger
    steps: list[WorkflowStepModel] = Field(default_factory=list, max_length=50)
    re_enrollment: bool = False
    re_enrollment_days: int = Field(default=0, ge=0, le=365)


class ManualEnrollRequest(BaseModel):
    contact_id: str = Field(min_length=1, max_length=100)
    contact_email: str = Field(default="", max_length=200)


class WorkflowTemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    category: str = Field(default="general", max_length=60)
    trigger_type: str = Field(default="manual", max_length=40)
    steps: list[WorkflowStepModel] = Field(default_factory=list, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=25)


class WorkflowTemplateInstantiateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    trigger_conditions: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    re_enrollment: bool = False
    re_enrollment_days: int = Field(default=0, ge=0, le=365)


class WorkflowGraphValidateRequest(BaseModel):
    steps: list[WorkflowStepModel] = Field(default_factory=list, max_length=100)
    start_step_id: str = Field(default="", max_length=50)


class WorkflowWebhookTriggerRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    external_event_id: str = Field(default="", max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)


class WorkflowApprovalPolicyRequest(BaseModel):
    workflow_id: int = Field(gt=0)
    enabled: bool = True
    required_approvals: int = Field(default=1, ge=1, le=5)
    approver_roles: list[str] = Field(default_factory=list, max_length=10)
    enforce_for_high_risk_only: bool = True


class ApprovalRequestCreateRequest(BaseModel):
    workflow_id: int = Field(gt=0)
    contact_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(default="", max_length=600)


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=20)
    reviewer: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=500)


class WorkflowConnectorUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    vendor: str = Field(min_length=1, max_length=100)
    auth_type: str = Field(default="oauth2", max_length=40)
    capabilities: list[str] = Field(default_factory=list, max_length=25)
    rate_limit_per_minute: int = Field(default=120, ge=10, le=10000)
    error_budget_pct: float = Field(default=1.0, ge=0.0, le=100.0)


class WorkflowConnectorReliabilityPolicyRequest(BaseModel):
    max_retries: int = Field(default=3, ge=0, le=10)
    base_backoff_ms: int = Field(default=250, ge=50, le=30000)
    circuit_failure_threshold: int = Field(default=5, ge=1, le=100)
    circuit_cooldown_seconds: int = Field(default=120, ge=10, le=86400)
    slo_availability_target_pct: float = Field(default=99.9, ge=50.0, le=100.0)
    slo_latency_p95_target_ms: int = Field(default=500, ge=50, le=60000)
    replay_enabled: bool = True


class WorkflowConnectorFailureSimulationRequest(BaseModel):
    failure_type: str = Field(default="timeout", max_length=40)
    operation_ref: str = Field(default="", max_length=120)


class WorkflowConnectorReplayRequest(BaseModel):
    force_success: bool = False


class WorkflowConnectorReplayProcessorRequest(BaseModel):
    connector_id: int | None = Field(default=None, ge=1)
    limit: int = Field(default=25, ge=1, le=200)
    force_success: bool = False
    include_not_due: bool = False


class WorkflowConnectorTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)
    max_retries: int = Field(default=3, ge=0, le=10)
    base_backoff_ms: int = Field(default=250, ge=50, le=30000)
    circuit_failure_threshold: int = Field(default=5, ge=1, le=100)
    circuit_cooldown_seconds: int = Field(default=120, ge=10, le=86400)
    slo_availability_target_pct: float = Field(default=99.9, ge=50.0, le=100.0)
    slo_latency_p95_target_ms: int = Field(default=500, ge=50, le=60000)
    replay_enabled: bool = True


class WorkflowConnectorTemplateApplyRequest(BaseModel):
    connector_ids: list[int] = Field(default_factory=list, max_length=200)


class WorkflowConnectorMaintenanceWindowRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    start_hour_utc: int = Field(ge=0, le=23)
    end_hour_utc: int = Field(ge=0, le=23)
    connector_ids: list[int] = Field(default_factory=list, max_length=200)
    enabled: bool = True


class WorkflowConnectorEscalationRuleRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    min_breach_count: int = Field(default=1, ge=1, le=100)
    channels: list[str] = Field(default_factory=list, max_length=10)
    notify_recipients: list[str] = Field(default_factory=list, max_length=20)
    enabled: bool = True


class WorkflowConnectorEscalationAcknowledgeRequest(BaseModel):
    acknowledged_by: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=500)


class WorkflowConnectorRunbookRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)
    connector_ids: list[int] = Field(default_factory=list, max_length=200)
    steps: list[str] = Field(default_factory=list, max_length=50)
    enabled: bool = True


class WorkflowConnectorRunbookAssignmentRequest(BaseModel):
    operator: str = Field(min_length=1, max_length=120)
    role: str = Field(default="oncall", max_length=60)
    note: str = Field(default="", max_length=300)


class WorkflowConnectorPostmortemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(default="", max_length=2000)
    incident_event_ids: list[int] = Field(default_factory=list, max_length=200)
    action_items: list[str] = Field(default_factory=list, max_length=50)


class WorkflowConnectorPostmortemTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    summary_template: str = Field(default="", max_length=2000)
    default_action_items: list[str] = Field(default_factory=list, max_length=50)
    closure_sla_hours: int = Field(default=24, ge=1, le=720)
    enabled: bool = True


class WorkflowConnectorPostmortemTemplateApplyRequest(BaseModel):
    connector_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=160)
    incident_event_ids: list[int] = Field(default_factory=list, max_length=200)


class WorkflowConnectorPostmortemActionItemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    owner: str = Field(default="", max_length=120)
    due_in_hours: int = Field(default=24, ge=1, le=720)


class WorkflowConnectorPostmortemActionItemUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=24)
    note: str = Field(default="", max_length=400)


class WorkflowConnectorPostmortemCloseRequest(BaseModel):
    closed_by: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=500)
    require_action_items_resolved: bool = True


class WorkflowConnectorPostmortemClosurePolicyRequest(BaseModel):
    enabled: bool = True
    required_approvals: int = Field(default=1, ge=1, le=5)
    approver_roles: list[str] = Field(default_factory=list, max_length=10)
    enforce_for_breached_sla_only: bool = False


class WorkflowConnectorPostmortemClosureDecisionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=20)
    reviewer: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=500)


class WorkflowConnectorOverdueEscalationProcessRequest(BaseModel):
    connector_id: int | None = Field(default=None, ge=1)
    limit: int = Field(default=50, ge=1, le=500)
    include_not_due: bool = False


class WorkflowConnectorEscalationRoutingPolicyRequest(BaseModel):
    enabled: bool = True
    paging_start_hour_utc: int = Field(default=8, ge=0, le=23)
    paging_end_hour_utc: int = Field(default=20, ge=0, le=23)
    in_window_channel: str = Field(default="pagerduty", max_length=40)
    off_window_channel: str = Field(default="email", max_length=40)
    medium_threshold_hours: int = Field(default=1, ge=1, le=720)
    high_threshold_hours: int = Field(default=24, ge=1, le=720)
    critical_threshold_hours: int = Field(default=72, ge=1, le=720)
    medium_recipients: list[str] = Field(default_factory=list, max_length=20)
    high_recipients: list[str] = Field(default_factory=list, max_length=20)
    critical_recipients: list[str] = Field(default_factory=list, max_length=20)


class WorkflowConnectorEscalationCadencePolicyRequest(BaseModel):
    enabled: bool = True
    l2_after_minutes: int = Field(default=30, ge=0, le=10080)
    l3_after_minutes: int = Field(default=90, ge=0, le=10080)
    repage_interval_minutes: int = Field(default=30, ge=0, le=1440)
    max_repages: int = Field(default=8, ge=1, le=200)
    suppression_ttl_minutes: int = Field(default=240, ge=0, le=10080)
    reopen_on_reoverdue: bool = True
    l1_recipients: list[str] = Field(default_factory=list, max_length=20)
    l2_recipients: list[str] = Field(default_factory=list, max_length=20)
    l3_recipients: list[str] = Field(default_factory=list, max_length=20)


class WorkflowConnectorEscalationCadenceProcessRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)


class WorkflowConnectorEscalationSuppressionProcessRequest(BaseModel):
    limit: int = Field(default=100, ge=1, le=500)


class WorkflowConnectorEscalationAcknowledgeAdminRequest(BaseModel):
    acknowledged_by: str = Field(min_length=1, max_length=120)
    note: str = Field(default="", max_length=500)


class WorkflowConnectorActionItemRebalanceRequest(BaseModel):
    max_open_items_per_owner: int = Field(default=3, ge=1, le=100)
    include_unassigned: bool = True
    limit: int = Field(default=25, ge=1, le=200)
