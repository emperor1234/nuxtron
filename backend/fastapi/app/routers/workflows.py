# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnknownMemberType=false, reportUnusedFunction=false
"""
Marketing Automation / Workflows (HubSpot Marketing Hub §3.2)
NEW: Visual workflow builder — enrollment triggers, condition branches,
action steps (send email, update CRM, add tag, notify rep, webhook, delay).
"""
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..database import get_db_session
from ..deps import AuthContext, require_auth
from ..models import WorkflowExecution, WorkflowRule

AuthDep = Annotated[AuthContext, Depends(require_auth)]

WORKFLOW_NOT_FOUND = 'Workflow not found.'
EXECUTION_NOT_FOUND = 'Workflow execution not found.'
TRIGGER_TYPES = {'contact_created', 'deal_stage_changed', 'form_submitted', 'ticket_created',
                 'survey_response', 'date_based', 'manual', 'tag_added', 'property_changed',
                 'webhook', 'api_event'}
ACTION_TYPES = {'send_email', 'update_property', 'add_tag', 'remove_tag', 'notify_rep',
                'create_task', 'send_webhook', 'delay', 'branch_condition', 'enroll_sequence',
                'create_ticket', 'add_to_list'}
HIGH_RISK_ACTIONS = {'send_webhook', 'update_property', 'create_ticket'}


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


class WorkflowStepModel(BaseModel):
    step_id: str = Field(min_length=1, max_length=50)
    action_type: str = Field(min_length=1, max_length=40)
    config: dict[str, Any] = Field(default_factory=dict)
    next_step_id: str = Field(default='', max_length=50)
    branch_yes: str = Field(default='', max_length=50)   # for branch_condition
    branch_no: str = Field(default='', max_length=50)    # for branch_condition
    delay_hours: int = Field(default=0, ge=0, le=8760)


class WorkflowTrigger(BaseModel):
    trigger_type: str = Field(min_length=1, max_length=40)
    conditions: list[dict[str, Any]] = Field(default_factory=list, max_length=20)


class WorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=1000)
    trigger: WorkflowTrigger
    steps: list[WorkflowStepModel] = Field(default_factory=list, max_length=50)
    re_enrollment: bool = False
    re_enrollment_days: int = Field(default=0, ge=0, le=365)


class ManualEnrollRequest(BaseModel):
    contact_id: str = Field(min_length=1, max_length=100)
    contact_email: str = Field(default='', max_length=200)


class WorkflowTemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=1000)
    category: str = Field(default='general', max_length=60)
    trigger_type: str = Field(default='manual', max_length=40)
    steps: list[WorkflowStepModel] = Field(default_factory=list, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=25)


class WorkflowTemplateInstantiateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=1000)
    trigger_conditions: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    re_enrollment: bool = False
    re_enrollment_days: int = Field(default=0, ge=0, le=365)


class WorkflowGraphValidateRequest(BaseModel):
    steps: list[WorkflowStepModel] = Field(default_factory=list, max_length=100)
    start_step_id: str = Field(default='', max_length=50)


class WorkflowWebhookTriggerRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    external_event_id: str = Field(default='', max_length=120)
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
    reason: str = Field(default='', max_length=600)


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=20)
    reviewer: str = Field(min_length=1, max_length=120)
    note: str = Field(default='', max_length=500)


class WorkflowConnectorUpsertRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    vendor: str = Field(min_length=1, max_length=100)
    auth_type: str = Field(default='oauth2', max_length=40)
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
    failure_type: str = Field(default='timeout', max_length=40)
    operation_ref: str = Field(default='', max_length=120)


class WorkflowConnectorReplayRequest(BaseModel):
    force_success: bool = False


class WorkflowConnectorReplayProcessorRequest(BaseModel):
    connector_id: int | None = Field(default=None, ge=1)
    limit: int = Field(default=25, ge=1, le=200)
    force_success: bool = False
    include_not_due: bool = False


class WorkflowConnectorTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=600)
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
    note: str = Field(default='', max_length=500)


class WorkflowConnectorRunbookRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default='', max_length=600)
    connector_ids: list[int] = Field(default_factory=list, max_length=200)
    steps: list[str] = Field(default_factory=list, max_length=50)
    enabled: bool = True


class WorkflowConnectorRunbookAssignmentRequest(BaseModel):
    operator: str = Field(min_length=1, max_length=120)
    role: str = Field(default='oncall', max_length=60)
    note: str = Field(default='', max_length=300)


class WorkflowConnectorPostmortemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(default='', max_length=2000)
    incident_event_ids: list[int] = Field(default_factory=list, max_length=200)
    action_items: list[str] = Field(default_factory=list, max_length=50)


class WorkflowConnectorPostmortemTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    summary_template: str = Field(default='', max_length=2000)
    default_action_items: list[str] = Field(default_factory=list, max_length=50)
    closure_sla_hours: int = Field(default=24, ge=1, le=720)
    enabled: bool = True


class WorkflowConnectorPostmortemTemplateApplyRequest(BaseModel):
    connector_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=160)
    incident_event_ids: list[int] = Field(default_factory=list, max_length=200)


class WorkflowConnectorPostmortemActionItemRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    owner: str = Field(default='', max_length=120)
    due_in_hours: int = Field(default=24, ge=1, le=720)


class WorkflowConnectorPostmortemActionItemUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=24)
    note: str = Field(default='', max_length=400)


class WorkflowConnectorPostmortemCloseRequest(BaseModel):
    closed_by: str = Field(min_length=1, max_length=120)
    note: str = Field(default='', max_length=500)
    require_action_items_resolved: bool = True


class WorkflowConnectorPostmortemClosurePolicyRequest(BaseModel):
    enabled: bool = True
    required_approvals: int = Field(default=1, ge=1, le=5)
    approver_roles: list[str] = Field(default_factory=list, max_length=10)
    enforce_for_breached_sla_only: bool = False


class WorkflowConnectorPostmortemClosureDecisionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=20)
    reviewer: str = Field(min_length=1, max_length=120)
    note: str = Field(default='', max_length=500)


class WorkflowConnectorOverdueEscalationProcessRequest(BaseModel):
    connector_id: int | None = Field(default=None, ge=1)
    limit: int = Field(default=50, ge=1, le=500)
    include_not_due: bool = False


class WorkflowConnectorEscalationRoutingPolicyRequest(BaseModel):
    enabled: bool = True
    paging_start_hour_utc: int = Field(default=8, ge=0, le=23)
    paging_end_hour_utc: int = Field(default=20, ge=0, le=23)
    in_window_channel: str = Field(default='pagerduty', max_length=40)
    off_window_channel: str = Field(default='email', max_length=40)
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
    note: str = Field(default='', max_length=500)


class WorkflowConnectorActionItemRebalanceRequest(BaseModel):
    max_open_items_per_owner: int = Field(default=3, ge=1, le=100)
    include_unassigned: bool = True
    limit: int = Field(default=25, ge=1, le=200)


def create_workflows_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    workflows_memory: list[dict[str, Any]],
    workflow_executions_memory: list[dict[str, Any]],
    workflow_step_logs_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
    approval_policies_memory: list[dict[str, Any]] | None = None,
    approval_requests_memory: list[dict[str, Any]] | None = None,
    connectors_memory: list[dict[str, Any]] | None = None,
    connector_replay_queue_memory: list[dict[str, Any]] | None = None,
    connector_sla_alerts_memory: list[dict[str, Any]] | None = None,
    connector_policy_templates_memory: list[dict[str, Any]] | None = None,
    connector_maintenance_windows_memory: list[dict[str, Any]] | None = None,
    connector_escalation_rules_memory: list[dict[str, Any]] | None = None,
    connector_escalation_events_memory: list[dict[str, Any]] | None = None,
    connector_runbooks_memory: list[dict[str, Any]] | None = None,
    connector_runbook_assignments_memory: list[dict[str, Any]] | None = None,
    connector_postmortems_memory: list[dict[str, Any]] | None = None,
    connector_postmortem_templates_memory: list[dict[str, Any]] | None = None,
    connector_postmortem_closure_policies_memory: list[dict[str, Any]] | None = None,
    connector_postmortem_closure_requests_memory: list[dict[str, Any]] | None = None,
    connector_postmortem_action_item_escalations_memory: list[dict[str, Any]] | None = None,
    connector_postmortem_escalation_routing_policies_memory: list[dict[str, Any]] | None = None,
    connector_postmortem_escalation_cadence_policies_memory: list[dict[str, Any]] | None = None,
    workflow_templates_memory: list[dict[str, Any]] | None = None,
    workflow_webhook_events_memory: list[dict[str, Any]] | None = None,
) -> APIRouter:
    """NEW: Marketing automation workflows router — HubSpot Marketing Hub §3.2."""
    router = APIRouter()
    _lock = threading.RLock()
    _approval_policies_memory = approval_policies_memory if approval_policies_memory is not None else []
    _approval_requests_memory = approval_requests_memory if approval_requests_memory is not None else []
    _connectors_memory = connectors_memory if connectors_memory is not None else []
    _connector_replay_queue_memory = connector_replay_queue_memory if connector_replay_queue_memory is not None else []
    _connector_sla_alerts_memory = connector_sla_alerts_memory if connector_sla_alerts_memory is not None else []
    _connector_policy_templates_memory = connector_policy_templates_memory if connector_policy_templates_memory is not None else []
    _connector_maintenance_windows_memory = connector_maintenance_windows_memory if connector_maintenance_windows_memory is not None else []
    _connector_escalation_rules_memory = connector_escalation_rules_memory if connector_escalation_rules_memory is not None else []
    _connector_escalation_events_memory = connector_escalation_events_memory if connector_escalation_events_memory is not None else []
    _connector_runbooks_memory = connector_runbooks_memory if connector_runbooks_memory is not None else []
    _connector_runbook_assignments_memory = connector_runbook_assignments_memory if connector_runbook_assignments_memory is not None else []
    _connector_postmortems_memory = connector_postmortems_memory if connector_postmortems_memory is not None else []
    _connector_postmortem_templates_memory = connector_postmortem_templates_memory if connector_postmortem_templates_memory is not None else []
    _connector_postmortem_closure_policies_memory = connector_postmortem_closure_policies_memory if connector_postmortem_closure_policies_memory is not None else []
    _connector_postmortem_closure_requests_memory = connector_postmortem_closure_requests_memory if connector_postmortem_closure_requests_memory is not None else []
    _connector_postmortem_action_item_escalations_memory = connector_postmortem_action_item_escalations_memory if connector_postmortem_action_item_escalations_memory is not None else []
    _connector_postmortem_escalation_routing_policies_memory = connector_postmortem_escalation_routing_policies_memory if connector_postmortem_escalation_routing_policies_memory is not None else []
    _connector_postmortem_escalation_cadence_policies_memory = connector_postmortem_escalation_cadence_policies_memory if connector_postmortem_escalation_cadence_policies_memory is not None else []
    _workflow_templates_memory = workflow_templates_memory if workflow_templates_memory is not None else []
    _workflow_webhook_events_memory = workflow_webhook_events_memory if workflow_webhook_events_memory is not None else []

    def _db_persistence_enabled() -> bool:
        raw = str(__import__('os').getenv('WORKFLOWS_DB_PERSISTENCE', 'true')).strip().lower()
        return raw not in {'0', 'false', 'no', 'off'}

    def _workflow_rule_to_payload(obj: WorkflowRule) -> dict[str, Any]:
        data = dict(obj.data or {})
        actions = dict(obj.actions or {})
        steps = actions.get('steps') if isinstance(actions.get('steps'), list) else []
        return {
            'id': int(obj.id),
            'tenant_id': obj.tenant_id,
            'name': obj.name,
            'description': str(data.get('description', '')),
            'trigger': {
                'trigger_type': obj.trigger,
                'conditions': obj.conditions if isinstance(obj.conditions, list) else [],
            },
            'steps': steps,
            'step_count': int(data.get('step_count', len(steps))),
            're_enrollment': bool(data.get('re_enrollment', False)),
            're_enrollment_days': int(data.get('re_enrollment_days', 0)),
            'status': 'active' if bool(obj.enabled) else 'paused',
            'enrollment_count': int(data.get('enrollment_count', 0)),
            'execution_count': int(data.get('execution_count', 0)),
            'created_at': obj.created_at.isoformat(),
            'updated_at': obj.updated_at.isoformat(),
        }

    def _db_get_workflow(workflow_id: int, tenant_id: str) -> dict[str, Any] | None:
        if not _db_persistence_enabled():
            return None
        try:
            with get_db_session() as session:
                obj = (
                    session.query(WorkflowRule)
                    .filter(WorkflowRule.id == workflow_id, WorkflowRule.tenant_id == tenant_id)
                    .first()
                )
                if obj is None:
                    return None
                return _workflow_rule_to_payload(obj)
        except Exception:
            return None

    def _db_create_workflow(tenant_id: str, payload: WorkflowCreateRequest, steps: list[dict[str, Any]], trigger_type: str) -> dict[str, Any] | None:
        if not _db_persistence_enabled():
            return None
        try:
            with get_db_session() as session:
                obj = WorkflowRule(
                    tenant_id=tenant_id,
                    name=payload.name,
                    enabled=True,
                    trigger=trigger_type,
                    conditions=payload.trigger.conditions,
                    actions={'steps': steps},
                    data={
                        'description': payload.description,
                        'step_count': len(steps),
                        're_enrollment': payload.re_enrollment,
                        're_enrollment_days': payload.re_enrollment_days,
                        'enrollment_count': 0,
                        'execution_count': 0,
                    },
                )
                session.add(obj)
                session.commit()
                session.refresh(obj)
                return _workflow_rule_to_payload(obj)
        except Exception:
            return None

    def _db_list_workflows(tenant_id: str) -> list[dict[str, Any]] | None:
        if not _db_persistence_enabled():
            return None
        try:
            with get_db_session() as session:
                rows = (
                    session.query(WorkflowRule)
                    .filter(WorkflowRule.tenant_id == tenant_id)
                    .order_by(WorkflowRule.created_at.desc())
                    .all()
                )
                return [_workflow_rule_to_payload(row) for row in rows]
        except Exception:
            return None

    def _db_toggle_workflow(workflow_id: int, tenant_id: str, active: bool) -> dict[str, Any] | None:
        if not _db_persistence_enabled():
            return None
        try:
            with get_db_session() as session:
                obj = (
                    session.query(WorkflowRule)
                    .filter(WorkflowRule.id == workflow_id, WorkflowRule.tenant_id == tenant_id)
                    .first()
                )
                if obj is None:
                    return None
                obj.enabled = bool(active)
                session.commit()
                session.refresh(obj)
                return _workflow_rule_to_payload(obj)
        except Exception:
            return None

    def _db_increment_workflow_counts(workflow_id: int, tenant_id: str, *, enroll_delta: int = 0, execution_delta: int = 0) -> None:
        if not _db_persistence_enabled():
            return
        try:
            with get_db_session() as session:
                obj = (
                    session.query(WorkflowRule)
                    .filter(WorkflowRule.id == workflow_id, WorkflowRule.tenant_id == tenant_id)
                    .first()
                )
                if obj is None:
                    return
                data = dict(obj.data or {})
                data['enrollment_count'] = int(data.get('enrollment_count', 0)) + int(enroll_delta)
                data['execution_count'] = int(data.get('execution_count', 0)) + int(execution_delta)
                obj.data = data
                session.commit()
        except Exception:
            return

    def _execution_model_to_payload(obj: WorkflowExecution, workflow_name: str = '') -> dict[str, Any]:
        data = dict(obj.data or {})
        return {
            'id': int(obj.id),
            'tenant_id': obj.tenant_id,
            'workflow_id': int(obj.workflow_id or 0),
            'workflow_name': str(data.get('workflow_name', workflow_name)),
            'contact_id': str(data.get('contact_id', '')),
            'contact_email': str(data.get('contact_email', '')),
            'status': obj.status,
            'steps_executed': len(obj.steps_executed or []),
            'started_at': obj.started_at.isoformat(),
            'completed_at': obj.completed_at.isoformat() if obj.completed_at else None,
            'trigger_source': str(data.get('trigger_source', 'manual')),
            'trigger_event_type': obj.trigger_type,
        }

    def _db_create_execution(
        *,
        tenant_id: str,
        workflow_id: int,
        workflow_name: str,
        contact_id: str,
        contact_email: str,
        trigger_source: str,
        trigger_event_type: str,
        step_logs: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not _db_persistence_enabled():
            return None
        now = datetime.now(UTC)
        try:
            with get_db_session() as session:
                obj = WorkflowExecution(
                    tenant_id=tenant_id,
                    workflow_id=workflow_id,
                    trigger_type=trigger_event_type,
                    trigger_entity_id=None,
                    status='completed',
                    started_at=now,
                    completed_at=now,
                    steps_executed=step_logs,
                    current_step_id=str(step_logs[-1].get('step_id', '')) if step_logs else None,
                    result={'steps_executed': len(step_logs)},
                    error_message=None,
                    data={
                        'workflow_name': workflow_name,
                        'contact_id': contact_id,
                        'contact_email': contact_email,
                        'trigger_source': trigger_source,
                    },
                )
                session.add(obj)
                session.commit()
                session.refresh(obj)
                return _execution_model_to_payload(obj, workflow_name)
        except Exception:
            return None

    def _db_list_executions(tenant_id: str, workflow_id: int) -> list[dict[str, Any]] | None:
        if not _db_persistence_enabled():
            return None
        try:
            with get_db_session() as session:
                rows = (
                    session.query(WorkflowExecution)
                    .filter(
                        WorkflowExecution.tenant_id == tenant_id,
                        WorkflowExecution.workflow_id == workflow_id,
                    )
                    .order_by(WorkflowExecution.started_at.desc())
                    .all()
                )
                return [_execution_model_to_payload(row) for row in rows]
        except Exception:
            return None

    def _default_reliability_policy() -> dict[str, Any]:
        return {
            'max_retries': 3,
            'base_backoff_ms': 250,
            'circuit_failure_threshold': 5,
            'circuit_cooldown_seconds': 120,
            'slo_availability_target_pct': 99.9,
            'slo_latency_p95_target_ms': 500,
            'replay_enabled': True,
        }

    def _ensure_reliability_fields(connector: dict[str, Any]) -> None:
        connector.setdefault('reliability_policy', _default_reliability_policy())
        connector.setdefault(
            'reliability_stats',
            {
                'total_requests': 0,
                'failed_requests': 0,
                'retries_attempted': 0,
                'replay_enqueued': 0,
                'replay_success': 0,
                'replay_failed': 0,
            },
        )
        connector.setdefault(
            'circuit_breaker',
            {
                'state': 'closed',
                'consecutive_failures': 0,
                'opened_at': None,
                'cooldown_seconds': 120,
            },
        )

    def _is_retryable_failure(failure_type: str) -> bool:
        return failure_type in {'timeout', 'http_5xx', 'network'}

    def _compute_reliability_snapshot(connector: dict[str, Any]) -> dict[str, Any]:
        _ensure_reliability_fields(connector)
        stats = connector.get('reliability_stats', {})
        policy = connector.get('reliability_policy', {})
        total_requests = int(stats.get('total_requests', 0))
        failed_requests = int(stats.get('failed_requests', 0))
        availability_pct = round(((total_requests - failed_requests) / total_requests) * 100, 2) if total_requests else 100.0
        p95_latency_ms = 120 if connector.get('status') == 'healthy' else 480
        return {
            'availability_pct_rolling': availability_pct,
            'availability_target_pct': float(policy.get('slo_availability_target_pct', 99.9)),
            'availability_breached': availability_pct < float(policy.get('slo_availability_target_pct', 99.9)),
            'latency_p95_ms': p95_latency_ms,
            'latency_target_p95_ms': int(policy.get('slo_latency_p95_target_ms', 500)),
            'latency_breached': p95_latency_ms > int(policy.get('slo_latency_p95_target_ms', 500)),
            'error_budget_pct': float(connector.get('error_budget_pct', 1.0)),
            'error_rate_pct': round((failed_requests / total_requests) * 100, 2) if total_requests else 0.0,
        }

    def _record_sla_alert(tenant_id: str, connector: dict[str, Any], reliability: dict[str, Any]) -> None:
        if not (bool(reliability.get('availability_breached')) or bool(reliability.get('latency_breached'))):
            return
        alert_type = 'availability' if bool(reliability.get('availability_breached')) else 'latency'
        with _lock:
            existing_open = next(
                (
                    a for a in _connector_sla_alerts_memory
                    if a.get('tenant_id') == tenant_id
                    and a.get('connector_id') == connector.get('id')
                    and a.get('type') == alert_type
                    and a.get('status') == 'open'
                ),
                None,
            )
            if existing_open is not None:
                existing_open['last_seen_at'] = datetime.now(UTC).isoformat()
                existing_open['snapshot'] = reliability
                existing_open['breach_count'] = int(existing_open.get('breach_count', 1)) + 1
                _evaluate_alert_escalation(existing_open)
                return
            _connector_sla_alerts_memory.append(
                {
                    'id': len(_connector_sla_alerts_memory) + 1,
                    'tenant_id': tenant_id,
                    'connector_id': connector.get('id'),
                    'connector_name': connector.get('name'),
                    'type': alert_type,
                    'status': 'open',
                    'message': 'SLA target breached for connector reliability.',
                    'snapshot': reliability,
                    'breach_count': 1,
                    'escalated_rule_ids': [],
                    'created_at': datetime.now(UTC).isoformat(),
                    'last_seen_at': datetime.now(UTC).isoformat(),
                }
            )
            _evaluate_alert_escalation(_connector_sla_alerts_memory[-1])

    def _evaluate_alert_escalation(alert: dict[str, Any]) -> None:
        tenant_id = str(alert.get('tenant_id', ''))
        connector_id = int(alert.get('connector_id', 0))
        breach_count = int(alert.get('breach_count', 1))
        already_escalated = set(alert.get('escalated_rule_ids') or [])
        for rule in _connector_escalation_rules_memory:
            if rule.get('tenant_id') != tenant_id or not bool(rule.get('enabled', True)):
                continue
            min_breach = int(rule.get('min_breach_count', 1))
            rule_id = int(rule.get('id', 0))
            if breach_count < min_breach or rule_id in already_escalated:
                continue
            _connector_escalation_events_memory.append(
                {
                    'id': len(_connector_escalation_events_memory) + 1,
                    'tenant_id': tenant_id,
                    'connector_id': connector_id,
                    'alert_id': alert.get('id'),
                    'rule_id': rule_id,
                    'rule_name': rule.get('name'),
                    'channels': rule.get('channels', []),
                    'notify_recipients': rule.get('notify_recipients', []),
                    'status': 'triggered',
                    'created_at': datetime.now(UTC).isoformat(),
                }
            )
            escalated_ids = alert.setdefault('escalated_rule_ids', [])
            escalated_ids.append(rule_id)

    def _close_sla_alerts_if_recovered(tenant_id: str, connector_id: int, reliability: dict[str, Any]) -> None:
        recovered = not bool(reliability.get('availability_breached')) and not bool(reliability.get('latency_breached'))
        if not recovered:
            return
        with _lock:
            for alert in _connector_sla_alerts_memory:
                if (
                    alert.get('tenant_id') == tenant_id
                    and int(alert.get('connector_id', 0)) == connector_id
                    and alert.get('status') == 'open'
                ):
                    alert['status'] = 'resolved'
                    alert['resolved_at'] = datetime.now(UTC).isoformat()

    def _next_retry_at(when: datetime, attempts: int, base_backoff_ms: int) -> str:
        backoff_ms = base_backoff_ms * (2 ** max(attempts - 1, 0))
        return (when + timedelta(milliseconds=backoff_ms)).isoformat()

    def _is_in_maintenance_window(tenant_id: str, connector_id: int, now: datetime) -> bool:
        current_hour = now.hour
        for window in _connector_maintenance_windows_memory:
            if window.get('tenant_id') != tenant_id or not bool(window.get('enabled', True)):
                continue
            connector_ids = window.get('connector_ids') or []
            if connector_ids and connector_id not in connector_ids:
                continue
            start_hour = int(window.get('start_hour_utc', 0))
            end_hour = int(window.get('end_hour_utc', 0))
            if start_hour == end_hour:
                return True
            if start_hour < end_hour:
                if start_hour <= current_hour < end_hour:
                    return True
            else:
                if current_hour >= start_hour or current_hour < end_hour:
                    return True
        return False

    def _process_replay_item_locked(
        *,
        connector: dict[str, Any],
        item: dict[str, Any],
        force_success: bool,
    ) -> dict[str, Any]:
        _ensure_reliability_fields(connector)
        stats = connector['reliability_stats']
        circuit = connector['circuit_breaker']
        policy = connector['reliability_policy']

        item['attempts'] = int(item.get('attempts', 0)) + 1
        success = bool(force_success) or connector.get('status') == 'healthy'
        now = datetime.now(UTC)
        if success:
            item['status'] = 'succeeded'
            item['updated_at'] = now.isoformat()
            item['next_retry_at'] = None
            stats['replay_success'] = int(stats.get('replay_success', 0)) + 1
            circuit['state'] = 'closed'
            circuit['consecutive_failures'] = 0
            circuit['opened_at'] = None
            connector['status'] = 'healthy'
        else:
            max_retries = int(policy.get('max_retries', 0))
            if int(item.get('attempts', 0)) > max_retries:
                item['status'] = 'failed'
                item['next_retry_at'] = None
                stats['replay_failed'] = int(stats.get('replay_failed', 0)) + 1
            else:
                item['status'] = 'pending'
                item['next_retry_at'] = _next_retry_at(
                    now,
                    int(item.get('attempts', 0)),
                    int(policy.get('base_backoff_ms', 250)),
                )
            item['updated_at'] = now.isoformat()
            circuit['consecutive_failures'] = int(circuit.get('consecutive_failures', 0)) + 1
            if int(circuit['consecutive_failures']) >= int(policy.get('circuit_failure_threshold', 5)):
                circuit['state'] = 'open'
                circuit['opened_at'] = now.isoformat()
            connector['status'] = 'degraded'

        connector['updated_at'] = now.isoformat()
        reliability = _compute_reliability_snapshot(connector)
        return {'item': item, 'connector': connector, 'slo': reliability}

    def _is_high_risk(workflow: dict[str, Any]) -> bool:
        steps = workflow.get('steps', [])
        return any(str(step.get('action_type', '')).strip().lower() in HIGH_RISK_ACTIONS for step in steps)

    def _get_policy(workflow_id: int, tenant_id: str) -> dict[str, Any] | None:
        with _lock:
            return next(
                (
                    p for p in _approval_policies_memory
                    if p.get('workflow_id') == workflow_id and p.get('tenant_id') == tenant_id and p.get('enabled')
                ),
                None,
            )

    def _count_approvals(request: dict[str, Any]) -> int:
        return len(request.get('approved_by') or [])

    def _append_audit(tenant_id: str, action: str, ref_id: int | None = None) -> None:
        with _lock:
            audit_log_memory.append({
                'id': len(audit_log_memory) + 1,
                'tenant_id': tenant_id,
                'action': action,
                'ref_id': ref_id,
                'created_at': datetime.now(UTC).isoformat(),
                'source': 'workflows-router',
            })

    def _parse_iso(value: Any) -> datetime:
        if not value:
            return datetime.fromtimestamp(0, tz=UTC)
        try:
            parsed = datetime.fromisoformat(str(value))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed
        except ValueError:
            return datetime.fromtimestamp(0, tz=UTC)

    def _build_incident_timeline(*, tenant_id: str, connector_id: int, limit: int) -> list[dict[str, Any]]:
        timeline: list[dict[str, Any]] = []
        for alert in _connector_sla_alerts_memory:
            if alert.get('tenant_id') != tenant_id or int(alert.get('connector_id', 0)) != connector_id:
                continue
            timeline.append(
                {
                    'type': 'sla_alert',
                    'ref_id': int(alert.get('id', 0)),
                    'status': alert.get('status', 'unknown'),
                    'occurred_at': alert.get('last_seen_at') or alert.get('created_at'),
                    'details': {
                        'alert_type': alert.get('type'),
                        'breach_count': int(alert.get('breach_count', 1)),
                    },
                }
            )
        for event in _connector_escalation_events_memory:
            if event.get('tenant_id') != tenant_id or int(event.get('connector_id', 0)) != connector_id:
                continue
            timeline.append(
                {
                    'type': 'escalation_event',
                    'ref_id': int(event.get('id', 0)),
                    'status': event.get('status', 'unknown'),
                    'occurred_at': event.get('resolved_at') or event.get('acknowledged_at') or event.get('created_at'),
                    'details': {
                        'rule_name': event.get('rule_name'),
                        'channels': event.get('channels', []),
                    },
                }
            )
        for replay_item in _connector_replay_queue_memory:
            if replay_item.get('tenant_id') != tenant_id or int(replay_item.get('connector_id', 0)) != connector_id:
                continue
            timeline.append(
                {
                    'type': 'replay_attempt',
                    'ref_id': int(replay_item.get('id', 0)),
                    'status': replay_item.get('status', 'unknown'),
                    'occurred_at': replay_item.get('updated_at') or replay_item.get('created_at'),
                    'details': {
                        'failure_type': replay_item.get('failure_type'),
                        'attempts': int(replay_item.get('attempts', 0)),
                    },
                }
            )

        timeline.sort(key=lambda item: _parse_iso(item.get('occurred_at')), reverse=True)
        return timeline[:limit]

    def _simulate_execution(
        workflow: dict[str, Any],
        contact_id: str,
        contact_email: str,
        tenant_id: str,
    ) -> dict[str, Any]:
        """Simulate executing a workflow — logs each step."""
        steps = workflow.get('steps', [])
        step_logs = []
        for step in steps:
            action_type = str(step.get('action_type', 'unknown'))
            log = {
                'id': len(workflow_step_logs_memory) + 1,
                'tenant_id': tenant_id,
                'step_id': step.get('step_id'),
                'action_type': action_type,
                'contact_id': contact_id,
                'status': 'completed',
                'result': f'Action {action_type} executed for {contact_email or contact_id}',
                'executed_at': datetime.now(UTC).isoformat(),
            }
            step_logs.append(log)
            with _lock:
                workflow_step_logs_memory.append(log)
        return {'steps_executed': len(step_logs), 'step_logs': step_logs}

    def _normalized_steps(steps: list[WorkflowStepModel]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for s in steps:
            normalized.append(
                {
                    'step_id': s.step_id,
                    'action_type': s.action_type.strip().lower(),
                    'config': s.config,
                    'next_step_id': s.next_step_id,
                    'branch_yes': s.branch_yes,
                    'branch_no': s.branch_no,
                    'delay_hours': s.delay_hours,
                }
            )
        return normalized

    def _validate_steps(steps: list[dict[str, Any]]) -> dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []
        step_ids = [str(step.get('step_id', '')).strip() for step in steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append('Duplicate step_id values are not allowed.')

        step_id_set = set(step_ids)
        for step in steps:
            step_id = str(step.get('step_id', '')).strip()
            action = str(step.get('action_type', '')).strip().lower()
            if action not in ACTION_TYPES:
                errors.append(f'Unsupported action_type for step {step_id}: {action}')

            next_step = str(step.get('next_step_id', '')).strip()
            if next_step and next_step not in step_id_set:
                errors.append(f'next_step_id not found for step {step_id}: {next_step}')

            if action == 'branch_condition':
                branch_yes = str(step.get('branch_yes', '')).strip()
                branch_no = str(step.get('branch_no', '')).strip()
                if not branch_yes or not branch_no:
                    errors.append(f'branch_condition requires branch_yes and branch_no for step {step_id}')
                if branch_yes and branch_yes not in step_id_set:
                    errors.append(f'branch_yes target not found for step {step_id}: {branch_yes}')
                if branch_no and branch_no not in step_id_set:
                    errors.append(f'branch_no target not found for step {step_id}: {branch_no}')

            if action == 'delay' and int(step.get('delay_hours', 0)) == 0:
                warnings.append(f'delay step {step_id} has delay_hours=0 and behaves like a passthrough step.')

        return {'errors': errors, 'warnings': warnings}

    def _simulate_graph_path(
        steps: list[dict[str, Any]],
        start_step_id: str,
        max_steps: int = 100,
    ) -> dict[str, Any]:
        if not steps:
            return {'visited': [], 'halt_reason': 'empty'}
        step_map = {str(step.get('step_id', '')): step for step in steps}
        current = start_step_id or str(steps[0].get('step_id', ''))
        visited: list[str] = []
        seen_count: dict[str, int] = {}

        while current:
            if current not in step_map:
                return {'visited': visited, 'halt_reason': f'unknown_step:{current}'}
            if len(visited) >= max_steps:
                return {'visited': visited, 'halt_reason': 'max_steps_exceeded'}
            visited.append(current)
            seen_count[current] = seen_count.get(current, 0) + 1
            if seen_count[current] > 2:
                return {'visited': visited, 'halt_reason': f'cycle_detected:{current}'}

            step = step_map[current]
            action = str(step.get('action_type', '')).strip().lower()
            if action == 'branch_condition':
                current = str(step.get('branch_yes', '')).strip()
            else:
                current = str(step.get('next_step_id', '')).strip()

        return {'visited': visited, 'halt_reason': 'terminal'}

    @router.post('/workflows', summary='Create workflow', responses={422: {'description': 'Invalid workflow graph.'}})
    def create_workflow(payload: WorkflowCreateRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Create a marketing automation workflow."""
        enforce_rate_limit(f'{auth.tenant_id}:workflows:create', 30, 60)
        trigger_type = payload.trigger.trigger_type.strip().lower()
        if trigger_type not in TRIGGER_TYPES:
            trigger_type = 'manual'
        steps = _normalized_steps(payload.steps)
        validation = _validate_steps(steps)
        if validation['errors']:
            raise HTTPException(status_code=422, detail={'errors': validation['errors'], 'warnings': validation['warnings']})
        with _lock:
            workflow = {
                'id': len(workflows_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'description': payload.description,
                'trigger': {
                    'trigger_type': trigger_type,
                    'conditions': payload.trigger.conditions,
                },
                'steps': steps,
                'step_count': len(steps),
                're_enrollment': payload.re_enrollment,
                're_enrollment_days': payload.re_enrollment_days,
                'status': 'active',
                'enrollment_count': 0,
                'execution_count': 0,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            workflows_memory.append(workflow)
        persisted = _db_create_workflow(auth.tenant_id, payload, steps, trigger_type)
        if isinstance(persisted, dict) and persisted:
            workflow = persisted
            with _lock:
                if not any(_coerce_int(w.get('id', 0)) == _coerce_int(workflow.get('id', 0)) and w.get('tenant_id') == auth.tenant_id for w in workflows_memory):
                    workflows_memory.append(workflow.copy())
        _append_audit(auth.tenant_id, 'workflow_created', workflow['id'])
        return {'status': 'ok', 'workflow': workflow}

    @router.post('/workflows/validate-graph', summary='Validate workflow graph and execution path')
    def validate_workflow_graph(payload: WorkflowGraphValidateRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:validate-graph', 120, 60)
        steps = _normalized_steps(payload.steps)
        validation = _validate_steps(steps)
        path = _simulate_graph_path(steps, payload.start_step_id)
        return {
            'status': 'ok',
            'valid': len(validation['errors']) == 0,
            'errors': validation['errors'],
            'warnings': validation['warnings'],
            'path_preview': path,
            'step_count': len(steps),
        }

    @router.post('/workflows/templates', summary='Create reusable workflow template', responses={422: {'description': 'Invalid workflow template graph.'}})
    def create_workflow_template(payload: WorkflowTemplateCreateRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:templates:create', 40, 60)
        trigger_type = payload.trigger_type.strip().lower()
        if trigger_type not in TRIGGER_TYPES:
            trigger_type = 'manual'
        steps = _normalized_steps(payload.steps)
        validation = _validate_steps(steps)
        if validation['errors']:
            raise HTTPException(status_code=422, detail={'errors': validation['errors'], 'warnings': validation['warnings']})
        with _lock:
            template = {
                'id': len(_workflow_templates_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'description': payload.description,
                'category': payload.category,
                'trigger_type': trigger_type,
                'steps': steps,
                'step_count': len(steps),
                'tags': payload.tags,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            _workflow_templates_memory.append(template)
        _append_audit(auth.tenant_id, 'workflow_template_created', _coerce_int(template.get('id')))
        return {'status': 'ok', 'template': template, 'validation_warnings': validation['warnings']}

    @router.get('/workflows/templates', summary='List workflow templates')
    def list_workflow_templates(
        auth: AuthDep,
        category: Annotated[str | None, Query(max_length=60)] = None,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:templates:list', 120, 60)
        with _lock:
            items = [t.copy() for t in _workflow_templates_memory if t.get('tenant_id') == auth.tenant_id]
        if category:
            items = [item for item in items if str(item.get('category', '')).strip().lower() == category.strip().lower()]
        items.sort(key=lambda item: _parse_iso(item.get('created_at')), reverse=True)
        return {'status': 'ok', 'templates': items, 'total': len(items)}

    @router.post('/workflows/templates/{template_id}/instantiate', summary='Instantiate workflow from template', responses={404: {'description': 'Workflow template not found.'}})
    def instantiate_workflow_template(
        template_id: int,
        payload: WorkflowTemplateInstantiateRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:templates:instantiate', 60, 60)
        with _lock:
            template = next(
                (
                    t for t in _workflow_templates_memory
                    if int(t.get('id', 0)) == template_id and t.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if template is None:
                raise HTTPException(status_code=404, detail='Workflow template not found.')
            workflow = {
                'id': len(workflows_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'description': payload.description or str(template.get('description', '')),
                'trigger': {
                    'trigger_type': template.get('trigger_type', 'manual'),
                    'conditions': payload.trigger_conditions,
                },
                'steps': list(template.get('steps') or []),
                'step_count': int(template.get('step_count', 0)),
                're_enrollment': payload.re_enrollment,
                're_enrollment_days': payload.re_enrollment_days,
                'status': 'active',
                'enrollment_count': 0,
                'execution_count': 0,
                'template_id': int(template.get('id', 0)),
                'template_name': template.get('name', ''),
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            workflows_memory.append(workflow)
        _append_audit(auth.tenant_id, 'workflow_template_instantiated', int(workflow['id']))
        return {'status': 'ok', 'workflow': workflow}

    @router.post('/workflows/triggers/webhook', summary='Trigger workflows using webhook event payload', responses={422: {'description': 'Unsupported webhook trigger type.'}})
    def trigger_workflows_webhook(payload: WorkflowWebhookTriggerRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:webhook:trigger', 240, 60)
        event_type = payload.event_type.strip().lower()
        if event_type not in TRIGGER_TYPES:
            raise HTTPException(status_code=422, detail='Unsupported webhook trigger type.')

        with _lock:
            if payload.external_event_id:
                existing_event = next(
                    (
                        event for event in _workflow_webhook_events_memory
                        if event.get('tenant_id') == auth.tenant_id and event.get('external_event_id') == payload.external_event_id
                    ),
                    None,
                )
                if existing_event is not None:
                    return {
                        'status': 'ok',
                        'duplicate': True,
                        'external_event_id': payload.external_event_id,
                        'execution_ids': existing_event.get('execution_ids', []),
                    }

            candidates = [
                workflow for workflow in workflows_memory
                if workflow.get('tenant_id') == auth.tenant_id
                and workflow.get('status') == 'active'
                and workflow.get('trigger', {}).get('trigger_type') == event_type
            ]

        def _conditions_match(workflow: dict[str, Any]) -> bool:
            conditions = workflow.get('trigger', {}).get('conditions') or []
            for condition in conditions:
                field = str(condition.get('field', '')).strip()
                expected = condition.get('value')
                if not field:
                    continue
                if payload.payload.get(field) != expected:
                    return False
            return True

        matched = [workflow for workflow in candidates if _conditions_match(workflow)]
        execution_ids: list[int] = []
        executions: list[dict[str, Any]] = []
        contact_id = str(payload.payload.get('contact_id') or payload.payload.get('id') or 'webhook-contact')
        contact_email = str(payload.payload.get('contact_email') or payload.payload.get('email') or '')

        with _lock:
            for workflow in matched:
                result = _simulate_execution(workflow, contact_id, contact_email, auth.tenant_id)
                execution = {
                    'id': len(workflow_executions_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'workflow_id': int(workflow.get('id', 0)),
                    'workflow_name': workflow.get('name', ''),
                    'contact_id': contact_id,
                    'contact_email': contact_email,
                    'status': 'completed',
                    'steps_executed': result['steps_executed'],
                    'started_at': datetime.now(UTC).isoformat(),
                    'completed_at': datetime.now(UTC).isoformat(),
                    'trigger_source': 'webhook',
                    'trigger_event_type': event_type,
                }
                workflow_executions_memory.append(execution)
                workflow['enrollment_count'] = int(workflow.get('enrollment_count', 0)) + 1
                workflow['execution_count'] = int(workflow.get('execution_count', 0)) + 1
                executions.append(execution)
                execution_ids.append(int(execution['id']))

            _workflow_webhook_events_memory.append(
                {
                    'id': len(_workflow_webhook_events_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'event_type': event_type,
                    'external_event_id': payload.external_event_id,
                    'payload': payload.payload,
                    'matched_workflow_ids': [int(w.get('id', 0)) for w in matched],
                    'execution_ids': execution_ids,
                    'created_at': datetime.now(UTC).isoformat(),
                }
            )

        _append_audit(auth.tenant_id, 'workflow_webhook_trigger_processed', len(execution_ids))
        return {
            'status': 'ok',
            'duplicate': False,
            'event_type': event_type,
            'matched_workflows': len(matched),
            'executed': len(executions),
            'execution_ids': execution_ids,
            'executions': executions,
        }

    @router.get('/workflows', summary='List workflows')
    def list_workflows(
        auth: AuthDep,
        trigger_type: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List automation workflows."""
        enforce_rate_limit(f'{auth.tenant_id}:workflows:list', 120, 60)
        items = _db_list_workflows(auth.tenant_id) or []
        if not items:
            with _lock:
                items = [w.copy() for w in workflows_memory if w.get('tenant_id') == auth.tenant_id]
        if trigger_type:
            items = [w for w in items if w.get('trigger', {}).get('trigger_type') == trigger_type]
        return {'status': 'ok', 'workflows': items[offset:offset + limit], 'total': len(items)}

    @router.get('/workflows/{workflow_id}', responses={404: {'description': WORKFLOW_NOT_FOUND}})
    def get_workflow(workflow_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Get a single workflow with all steps."""
        enforce_rate_limit(f'{auth.tenant_id}:workflows:get', 120, 60)
        with _lock:
            wf = next((w.copy() for w in workflows_memory
                       if w.get('id') == workflow_id and w.get('tenant_id') == auth.tenant_id), None)
        if wf is None:
            wf = _db_get_workflow(workflow_id, auth.tenant_id)
        if wf is None:
            raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
        return {'status': 'ok', 'workflow': wf}

    @router.patch('/workflows/{workflow_id}/toggle', responses={404: {'description': WORKFLOW_NOT_FOUND}})
    def toggle_workflow(
        workflow_id: int,
        auth: AuthDep,
        active: Annotated[bool, Query()],
    ) -> dict[str, Any]:
        """NEW: Activate or pause a workflow."""
        enforce_rate_limit(f'{auth.tenant_id}:workflows:toggle', 60, 60)
        with _lock:
            wf = next((w for w in workflows_memory
                       if w.get('id') == workflow_id and w.get('tenant_id') == auth.tenant_id), None)
            if wf is not None:
                wf['status'] = 'active' if active else 'paused'
                wf['updated_at'] = datetime.now(UTC).isoformat()
        persisted = _db_toggle_workflow(workflow_id, auth.tenant_id, active)
        if wf is None and persisted is None:
            raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
        if isinstance(persisted, dict) and persisted:
            wf = persisted
        _append_audit(auth.tenant_id, f'workflow_{"activated" if active else "paused"}', workflow_id)
        return {'status': 'ok', 'workflow': wf.copy() if isinstance(wf, dict) else wf}

    @router.post('/workflows/{workflow_id}/enroll', responses={404: {'description': WORKFLOW_NOT_FOUND}, 409: {'description': 'Workflow is not active.'}})
    def enroll_contact(workflow_id: int, payload: ManualEnrollRequest, auth: AuthDep) -> dict[str, Any]:
        """NEW: Manually enroll a contact into a workflow."""
        enforce_rate_limit(f'{auth.tenant_id}:workflows:enroll', 120, 60)
        with _lock:
            wf = next((w for w in workflows_memory
                       if w.get('id') == workflow_id and w.get('tenant_id') == auth.tenant_id), None)
        if wf is None:
            persisted = _db_get_workflow(workflow_id, auth.tenant_id)
            if isinstance(persisted, dict) and persisted:
                wf = persisted
        if wf is None:
            raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
        if wf.get('status') != 'active':
            raise HTTPException(status_code=409, detail='Workflow is not active.')
        policy = _get_policy(workflow_id, auth.tenant_id)
        if policy is not None:
            high_risk_workflow = _is_high_risk(wf)
            enforce_for_high_risk_only = bool(policy.get('enforce_for_high_risk_only', True))
            should_enforce = high_risk_workflow if enforce_for_high_risk_only else True
            if should_enforce:
                with _lock:
                    matching_requests = [
                        r for r in _approval_requests_memory
                        if r.get('tenant_id') == auth.tenant_id
                        and r.get('workflow_id') == workflow_id
                        and r.get('contact_id') == payload.contact_id
                    ]
                approved = any(
                    r.get('status') == 'approved' and _count_approvals(r) >= int(policy.get('required_approvals', 1))
                    for r in matching_requests
                )
                if not approved:
                    raise HTTPException(
                        status_code=409,
                        detail='Approval required before enrollment for this workflow/contact.',
                    )
        # Simulate execution
        result = _simulate_execution(wf, payload.contact_id, payload.contact_email, auth.tenant_id)
        with _lock:
            execution = {
                'id': len(workflow_executions_memory) + 1,
                'tenant_id': auth.tenant_id,
                'workflow_id': workflow_id,
                'workflow_name': wf.get('name', ''),
                'contact_id': payload.contact_id,
                'contact_email': payload.contact_email,
                'status': 'completed',
                'steps_executed': result['steps_executed'],
                'started_at': datetime.now(UTC).isoformat(),
                'completed_at': datetime.now(UTC).isoformat(),
            }
            workflow_executions_memory.append(execution)
            wf['enrollment_count'] = wf.get('enrollment_count', 0) + 1
            wf['execution_count'] = wf.get('execution_count', 0) + 1
        persisted_execution = _db_create_execution(
            tenant_id=auth.tenant_id,
            workflow_id=workflow_id,
            workflow_name=str(wf.get('name', '')),
            contact_id=payload.contact_id,
            contact_email=payload.contact_email,
            trigger_source='manual_enroll',
            trigger_event_type=str(wf.get('trigger', {}).get('trigger_type', 'manual')),
            step_logs=result['step_logs'],
        )
        _db_increment_workflow_counts(workflow_id, auth.tenant_id, enroll_delta=1, execution_delta=1)
        if isinstance(persisted_execution, dict) and persisted_execution:
            execution = persisted_execution
        _append_audit(auth.tenant_id, 'workflow_contact_enrolled', execution['id'])
        return {'status': 'ok', 'execution': execution}

    @router.get('/workflows/{workflow_id}/executions', responses={404: {'description': WORKFLOW_NOT_FOUND}})
    def list_executions(
        workflow_id: int,
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        """NEW: List workflow execution history."""
        enforce_rate_limit(f'{auth.tenant_id}:workflows:executions', 60, 60)
        with _lock:
            wf = next((w for w in workflows_memory
                       if w.get('id') == workflow_id and w.get('tenant_id') == auth.tenant_id), None)
            execs = [e.copy() for e in workflow_executions_memory if e.get('workflow_id') == workflow_id]
        if wf is None:
            wf = _db_get_workflow(workflow_id, auth.tenant_id)
        if wf is None:
            raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
        persisted_execs = _db_list_executions(auth.tenant_id, workflow_id)
        if isinstance(persisted_execs, list) and persisted_execs:
            execs = persisted_execs
        return {'status': 'ok', 'executions': execs[offset:offset + limit], 'total': len(execs)}

    @router.get('/workflows/{workflow_id}/analytics', responses={404: {'description': WORKFLOW_NOT_FOUND}})
    def workflow_analytics(workflow_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Workflow performance analytics."""
        enforce_rate_limit(f'{auth.tenant_id}:workflows:analytics', 60, 60)
        with _lock:
            wf = next((w.copy() for w in workflows_memory
                       if w.get('id') == workflow_id and w.get('tenant_id') == auth.tenant_id), None)
            execs = [e for e in workflow_executions_memory if e.get('workflow_id') == workflow_id]
        if wf is None:
            wf = _db_get_workflow(workflow_id, auth.tenant_id)
        if wf is None:
            raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
        persisted_execs = _db_list_executions(auth.tenant_id, workflow_id)
        if isinstance(persisted_execs, list) and persisted_execs:
            execs = persisted_execs
        completed = sum(1 for e in execs if e.get('status') == 'completed')
        failed = sum(1 for e in execs if e.get('status') == 'failed')
        step_counts = [int(e.get('steps_executed', 0)) for e in execs]
        return {
            'status': 'ok',
            'workflow_id': workflow_id,
            'workflow_name': wf.get('name', ''),
            'total_enrollments': len(execs),
            'completed': completed,
            'failed': failed,
            'completion_rate': round(completed / len(execs) * 100, 1) if execs else 0,
            'avg_steps_executed': round(sum(step_counts) / len(step_counts), 1) if step_counts else 0,
        }

    def _workflow_platform_readiness_payload(tenant_id: str) -> dict[str, Any]:
        with _lock:
            tenant_workflows = [w for w in workflows_memory if w.get('tenant_id') == tenant_id]
            tenant_templates = [t for t in _workflow_templates_memory if t.get('tenant_id') == tenant_id]
            tenant_connectors = [c for c in _connectors_memory if c.get('tenant_id') == tenant_id]
            tenant_executions = [e for e in workflow_executions_memory if e.get('tenant_id') == tenant_id]
            tenant_webhook_events = [e for e in _workflow_webhook_events_memory if e.get('tenant_id') == tenant_id]

        matrix = [
            {'feature': 'workflow_crud', 'implemented': True},
            {'feature': 'graph_validation', 'implemented': True},
            {'feature': 'template_library', 'implemented': True},
            {'feature': 'template_instantiation', 'implemented': True},
            {'feature': 'manual_enrollment', 'implemented': True},
            {'feature': 'webhook_trigger_ingestion', 'implemented': True},
            {'feature': 'execution_history', 'implemented': True},
            {'feature': 'approval_gates', 'implemented': True},
            {'feature': 'connector_reliability', 'implemented': True},
            {'feature': 'incident_escalation', 'implemented': True},
            {'feature': 'postmortem_governance', 'implemented': True},
        ]
        implemented_count = sum(1 for item in matrix if bool(item.get('implemented')))
        total_count = len(matrix)
        completion_pct = round((implemented_count / total_count) * 100, 1) if total_count else 0.0

        return {
            'status': 'ok',
            'completion_pct': completion_pct,
            'implemented_count': implemented_count,
            'total_count': total_count,
            'matrix': matrix,
            'tenant_stats': {
                'workflows': len(tenant_workflows),
                'templates': len(tenant_templates),
                'connectors': len(tenant_connectors),
                'executions': len(tenant_executions),
                'webhook_events': len(tenant_webhook_events),
            },
            'vendors': [
                {'name': 'OpenAI', 'usage': 'LLM reasoning and generation', 'integration': 'AI gateway / provider SDK'},
                {'name': 'Anthropic', 'usage': 'LLM reasoning fallback', 'integration': 'AI gateway / provider SDK'},
                {'name': 'Slack', 'usage': 'Notifications and human approvals', 'integration': 'Slack Web API'},
                {'name': 'Google Analytics', 'usage': 'Attribution and analytics', 'integration': 'Google Analytics Data API'},
                {'name': 'Google Search Console', 'usage': 'SEO signals', 'integration': 'Search Console API'},
                {'name': 'X (Twitter)', 'usage': 'Social publishing', 'integration': 'X API v2'},
                {'name': 'Meta Graph', 'usage': 'Facebook/Instagram/Threads publishing', 'integration': 'Graph API'},
                {'name': 'TikTok', 'usage': 'Video publishing', 'integration': 'TikTok API'},
                {'name': 'YouTube', 'usage': 'Video distribution', 'integration': 'YouTube Data API v3'},
                {'name': 'Prometheus + Grafana', 'usage': 'Metrics and dashboards', 'integration': 'Observability stack'},
            ],
        }

    @router.get('/workflow-platform/production-readiness', summary='Workflow production-readiness matrix')
    def workflow_production_readiness(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:production-readiness', 120, 60)
        return _workflow_platform_readiness_payload(auth.tenant_id)

    @router.get('/workflow-platform/completion-chart', summary='Workflow platform completion chart for dashboards')
    def workflow_platform_completion_chart(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:completion-chart', 120, 60)
        payload = _workflow_platform_readiness_payload(auth.tenant_id)
        matrix = payload.get('matrix', [])
        implemented_count = int(payload.get('implemented_count', 0))
        total_count = int(payload.get('total_count', 0))
        completion_pct = float(payload.get('completion_pct', 0.0))
        return {
            'status': 'ok',
            'as_of': datetime.now(UTC).isoformat(),
            'completion_pct': completion_pct,
            'implemented_count': implemented_count,
            'total_count': total_count,
            'chart': {
                'summary': {
                    'done': implemented_count,
                    'remaining': max(0, total_count - implemented_count),
                    'percent': completion_pct,
                },
                'features': matrix,
            },
            'tenant_stats': payload.get('tenant_stats', {}),
            'vendors': payload.get('vendors', []),
        }

    @router.delete('/workflows/{workflow_id}', responses={404: {'description': WORKFLOW_NOT_FOUND}})
    def delete_workflow(workflow_id: int, auth: AuthDep) -> dict[str, Any]:
        """NEW: Delete a workflow."""
        enforce_rate_limit(f'{auth.tenant_id}:workflows:delete', 30, 60)
        with _lock:
            idx = next((i for i, w in enumerate(workflows_memory)
                        if w.get('id') == workflow_id and w.get('tenant_id') == auth.tenant_id), None)
            if idx is None:
                raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
            removed = workflows_memory.pop(idx)
        _append_audit(auth.tenant_id, 'workflow_deleted', workflow_id)
        return {'status': 'ok', 'deleted': True, 'workflow': removed}

    @router.post('/workflows/approval-policies', summary='Upsert workflow approval policy')
    def upsert_workflow_approval_policy(payload: WorkflowApprovalPolicyRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:approval-policy:upsert', 40, 60)
        with _lock:
            wf = next((w for w in workflows_memory if w.get('id') == payload.workflow_id and w.get('tenant_id') == auth.tenant_id), None)
            if wf is None:
                raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
            existing = next(
                (
                    p for p in _approval_policies_memory
                    if p.get('workflow_id') == payload.workflow_id and p.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            now = datetime.now(UTC).isoformat()
            if existing is None:
                policy = {
                    'id': len(_approval_policies_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'workflow_id': payload.workflow_id,
                    'enabled': payload.enabled,
                    'required_approvals': payload.required_approvals,
                    'approver_roles': payload.approver_roles,
                    'enforce_for_high_risk_only': payload.enforce_for_high_risk_only,
                    'created_at': now,
                    'updated_at': now,
                }
                _approval_policies_memory.append(policy)
            else:
                existing['enabled'] = payload.enabled
                existing['required_approvals'] = payload.required_approvals
                existing['approver_roles'] = payload.approver_roles
                existing['enforce_for_high_risk_only'] = payload.enforce_for_high_risk_only
                existing['updated_at'] = now
                policy = existing
        _append_audit(auth.tenant_id, 'workflow_approval_policy_upserted', payload.workflow_id)
        return {'status': 'ok', 'policy': policy}

    @router.get('/workflows/approval-policies', summary='List workflow approval policies')
    def list_workflow_approval_policies(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:approval-policy:list', 120, 60)
        with _lock:
            policies = [p.copy() for p in _approval_policies_memory if p.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'policies': policies, 'total': len(policies)}

    @router.post('/workflows/approval-requests', summary='Create manual approval request for workflow execution')
    def create_approval_request(payload: ApprovalRequestCreateRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:approval-request:create', 60, 60)
        with _lock:
            wf = next((w for w in workflows_memory if w.get('id') == payload.workflow_id and w.get('tenant_id') == auth.tenant_id), None)
            if wf is None:
                raise HTTPException(status_code=404, detail=WORKFLOW_NOT_FOUND)
            request: dict[str, Any] = {
                'id': len(_approval_requests_memory) + 1,
                'tenant_id': auth.tenant_id,
                'workflow_id': payload.workflow_id,
                'workflow_name': wf.get('name'),
                'contact_id': payload.contact_id,
                'reason': payload.reason,
                'status': 'pending',
                'approved_by': [],
                'rejected_by': [],
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            _approval_requests_memory.append(request)
        _append_audit(auth.tenant_id, 'workflow_approval_requested', request['id'])
        return {'status': 'ok', 'approval_request': request}

    @router.post('/workflows/approval-requests/{request_id}/decision', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def decide_approval_request(request_id: int, payload: ApprovalDecisionRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:approval-request:decision', 120, 60)
        decision = payload.decision.strip().lower()
        if decision not in {'approve', 'reject'}:
            raise HTTPException(status_code=422, detail='decision must be approve or reject')
        with _lock:
            req = next(
                (
                    r for r in _approval_requests_memory
                    if r.get('id') == request_id and r.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if req is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
            if req.get('status') == 'rejected':
                raise HTTPException(status_code=409, detail='Approval request already rejected.')

            if decision == 'approve':
                approved_by = req.setdefault('approved_by', [])
                if payload.reviewer not in approved_by:
                    approved_by.append(payload.reviewer)
                policy = _get_policy(int(req.get('workflow_id', 0)), auth.tenant_id)
                required_approvals = int((policy or {}).get('required_approvals', 1))
                req['status'] = 'approved' if _count_approvals(req) >= required_approvals else 'pending'
            else:
                rejected_by = req.setdefault('rejected_by', [])
                if payload.reviewer not in rejected_by:
                    rejected_by.append(payload.reviewer)
                req['status'] = 'rejected'
            req['last_note'] = payload.note
            req['updated_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'workflow_approval_decided', request_id)
        return {'status': 'ok', 'approval_request': req}

    @router.get('/workflows/approval-requests', summary='List workflow approval requests')
    def list_approval_requests(auth: AuthDep, limit: Annotated[int, Query(ge=1, le=200)] = 50) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:approval-request:list', 120, 60)
        with _lock:
            requests = [r.copy() for r in _approval_requests_memory if r.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'approval_requests': requests[:limit], 'total': len(requests)}

    @router.post('/workflow-connector-templates', summary='Create connector reliability template')
    def create_connector_template(payload: WorkflowConnectorTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:templates:create', 40, 60)
        with _lock:
            template = {
                'id': len(_connector_policy_templates_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'description': payload.description,
                'policy': {
                    'max_retries': payload.max_retries,
                    'base_backoff_ms': payload.base_backoff_ms,
                    'circuit_failure_threshold': payload.circuit_failure_threshold,
                    'circuit_cooldown_seconds': payload.circuit_cooldown_seconds,
                    'slo_availability_target_pct': payload.slo_availability_target_pct,
                    'slo_latency_p95_target_ms': payload.slo_latency_p95_target_ms,
                    'replay_enabled': payload.replay_enabled,
                },
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            _connector_policy_templates_memory.append(template)
        _append_audit(auth.tenant_id, 'workflow_connector_template_created', _coerce_int(template.get('id')))
        return {'status': 'ok', 'template': template}

    @router.get('/workflow-connector-templates', summary='List connector reliability templates')
    def list_connector_templates(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:templates:list', 120, 60)
        with _lock:
            templates = [t.copy() for t in _connector_policy_templates_memory if t.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'templates': templates, 'total': len(templates)}

    @router.post('/workflow-connector-templates/{template_id}/apply', summary='Apply reliability template to connectors')
    def apply_connector_template(template_id: int, payload: WorkflowConnectorTemplateApplyRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:templates:apply', 60, 60)
        with _lock:
            template = next(
                (
                    t for t in _connector_policy_templates_memory
                    if int(t.get('id', 0)) == template_id and t.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if template is None:
                raise HTTPException(status_code=404, detail='Connector template not found.')

            target_ids = payload.connector_ids
            connectors = [c for c in _connectors_memory if c.get('tenant_id') == auth.tenant_id]
            if target_ids:
                connectors = [c for c in connectors if int(c.get('id', 0)) in target_ids]

            updated: list[int] = []
            for connector in connectors:
                _ensure_reliability_fields(connector)
                connector['reliability_policy'] = dict(template.get('policy', {}))
                connector['circuit_breaker']['cooldown_seconds'] = int(
                    connector['reliability_policy'].get('circuit_cooldown_seconds', 120)
                )
                connector['updated_at'] = datetime.now(UTC).isoformat()
                updated.append(int(connector.get('id', 0)))

        _append_audit(auth.tenant_id, 'workflow_connector_template_applied', template_id)
        return {'status': 'ok', 'template_id': template_id, 'updated_connector_ids': updated, 'count': len(updated)}

    @router.post('/workflow-connector-maintenance-windows', summary='Create connector maintenance window')
    def create_maintenance_window(payload: WorkflowConnectorMaintenanceWindowRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:maintenance:create', 60, 60)
        with _lock:
            window = {
                'id': len(_connector_maintenance_windows_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'start_hour_utc': payload.start_hour_utc,
                'end_hour_utc': payload.end_hour_utc,
                'connector_ids': payload.connector_ids,
                'enabled': payload.enabled,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            _connector_maintenance_windows_memory.append(window)
        _append_audit(auth.tenant_id, 'workflow_connector_maintenance_window_created', _coerce_int(window.get('id')))
        return {'status': 'ok', 'window': window}

    @router.get('/workflow-connector-maintenance-windows', summary='List connector maintenance windows')
    def list_maintenance_windows(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:maintenance:list', 120, 60)
        with _lock:
            windows = [w.copy() for w in _connector_maintenance_windows_memory if w.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'windows': windows, 'total': len(windows)}

    @router.post('/workflow-connector-escalation-rules', summary='Create connector escalation rule')
    def create_escalation_rule(payload: WorkflowConnectorEscalationRuleRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:escalation-rules:create', 60, 60)
        with _lock:
            rule = {
                'id': len(_connector_escalation_rules_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'min_breach_count': payload.min_breach_count,
                'channels': payload.channels,
                'notify_recipients': payload.notify_recipients,
                'enabled': payload.enabled,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            _connector_escalation_rules_memory.append(rule)
        _append_audit(auth.tenant_id, 'workflow_connector_escalation_rule_created', _coerce_int(rule.get('id')))
        return {'status': 'ok', 'rule': rule}

    @router.get('/workflow-connector-escalation-rules', summary='List connector escalation rules')
    def list_escalation_rules(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:escalation-rules:list', 120, 60)
        with _lock:
            rules = [r.copy() for r in _connector_escalation_rules_memory if r.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'rules': rules, 'total': len(rules)}

    @router.get('/workflow-connector-escalation-events', summary='List connector escalation events')
    def list_escalation_events(auth: AuthDep, limit: Annotated[int, Query(ge=1, le=200)] = 100) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:escalation-events:list', 120, 60)
        with _lock:
            events = [e.copy() for e in _connector_escalation_events_memory if e.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'events': events[:limit], 'total': len(events)}

    @router.post('/workflow-connector-escalation-events/{event_id}/acknowledge', summary='Acknowledge escalation event')
    def acknowledge_escalation_event(
        event_id: int,
        payload: WorkflowConnectorEscalationAcknowledgeRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:escalation-events:ack', 120, 60)
        with _lock:
            event = next(
                (
                    e for e in _connector_escalation_events_memory
                    if int(e.get('id', 0)) == event_id and e.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if event is None:
                raise HTTPException(status_code=404, detail='Escalation event not found.')
            event['status'] = 'acknowledged'
            event['acknowledged_by'] = payload.acknowledged_by
            event['acknowledged_note'] = payload.note
            event['acknowledged_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'workflow_connector_escalation_event_acknowledged', event_id)
        return {'status': 'ok', 'event': event}

    @router.post('/workflow-connector-escalation-events/auto-resolve', summary='Auto-resolve escalations and alerts for recovered connectors')
    def auto_resolve_escalations(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:escalation-events:auto-resolve', 60, 60)
        resolved_alert_ids: list[int] = []
        resolved_event_ids: list[int] = []
        now = datetime.now(UTC).isoformat()
        with _lock:
            for alert in _connector_sla_alerts_memory:
                if alert.get('tenant_id') != auth.tenant_id or alert.get('status') != 'open':
                    continue
                connector_id = int(alert.get('connector_id', 0))
                connector = next(
                    (
                        c for c in _connectors_memory
                        if int(c.get('id', 0)) == connector_id and c.get('tenant_id') == auth.tenant_id
                    ),
                    None,
                )
                if connector is None:
                    continue
                reliability = _compute_reliability_snapshot(connector)
                recovered = not bool(reliability.get('availability_breached')) and not bool(reliability.get('latency_breached'))
                if not recovered:
                    continue

                alert['status'] = 'resolved'
                alert['resolved_at'] = now
                resolved_alert_ids.append(int(alert.get('id', 0)))

                for event in _connector_escalation_events_memory:
                    if (
                        event.get('tenant_id') == auth.tenant_id
                        and int(event.get('alert_id', 0)) == int(alert.get('id', 0))
                        and event.get('status') in {'triggered', 'acknowledged'}
                    ):
                        event['status'] = 'resolved'
                        event['resolved_at'] = now
                        resolved_event_ids.append(int(event.get('id', 0)))

            # Resolve any lingering triggered/acknowledged events if their backing alert
            # is already resolved (or absent), so escalation state does not drift.
            for event in _connector_escalation_events_memory:
                if event.get('tenant_id') != auth.tenant_id or event.get('status') not in {'triggered', 'acknowledged'}:
                    continue
                alert_id = int(event.get('alert_id', 0))
                linked_alert = next(
                    (
                        a for a in _connector_sla_alerts_memory
                        if int(a.get('id', 0)) == alert_id and a.get('tenant_id') == auth.tenant_id
                    ),
                    None,
                )
                if linked_alert is not None and linked_alert.get('status') == 'open':
                    continue
                event['status'] = 'resolved'
                event['resolved_at'] = now
                event_id = int(event.get('id', 0))
                if event_id not in resolved_event_ids:
                    resolved_event_ids.append(event_id)

        _append_audit(auth.tenant_id, 'workflow_connector_escalations_auto_resolved', len(resolved_event_ids))
        return {
            'status': 'ok',
            'resolved_alert_ids': resolved_alert_ids,
            'resolved_event_ids': resolved_event_ids,
            'alerts_resolved': len(resolved_alert_ids),
            'events_resolved': len(resolved_event_ids),
        }

    @router.post('/workflow-connector-runbooks', summary='Create connector runbook')
    def create_connector_runbook(payload: WorkflowConnectorRunbookRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:runbooks:create', 60, 60)
        with _lock:
            runbook = {
                'id': len(_connector_runbooks_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'description': payload.description,
                'connector_ids': payload.connector_ids,
                'steps': payload.steps,
                'enabled': payload.enabled,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            _connector_runbooks_memory.append(runbook)
        _append_audit(auth.tenant_id, 'workflow_connector_runbook_created', _coerce_int(runbook.get('id')))
        return {'status': 'ok', 'runbook': runbook}

    @router.get('/workflow-connector-runbooks', summary='List connector runbooks')
    def list_connector_runbooks(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:runbooks:list', 120, 60)
        with _lock:
            runbooks = [r.copy() for r in _connector_runbooks_memory if r.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'runbooks': runbooks, 'total': len(runbooks)}

    @router.post('/workflow-connector-runbooks/{runbook_id}/assignments', summary='Assign operator to runbook')
    def assign_runbook_operator(
        runbook_id: int,
        payload: WorkflowConnectorRunbookAssignmentRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:runbooks:assign', 120, 60)
        with _lock:
            runbook = next(
                (
                    r for r in _connector_runbooks_memory
                    if int(r.get('id', 0)) == runbook_id and r.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if runbook is None:
                raise HTTPException(status_code=404, detail='Runbook not found.')

            assignment = {
                'id': len(_connector_runbook_assignments_memory) + 1,
                'tenant_id': auth.tenant_id,
                'runbook_id': runbook_id,
                'runbook_name': runbook.get('name'),
                'operator': payload.operator,
                'role': payload.role,
                'note': payload.note,
                'status': 'assigned',
                'created_at': datetime.now(UTC).isoformat(),
            }
            _connector_runbook_assignments_memory.append(assignment)
        _append_audit(auth.tenant_id, 'workflow_connector_runbook_operator_assigned', int(assignment['id']))
        return {'status': 'ok', 'assignment': assignment}

    @router.get('/workflow-connector-runbooks/{runbook_id}/assignments', summary='List runbook assignments')
    def list_runbook_assignments(runbook_id: int, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:runbooks:assignments:list', 120, 60)
        with _lock:
            assignments = [
                a.copy() for a in _connector_runbook_assignments_memory
                if a.get('tenant_id') == auth.tenant_id and int(a.get('runbook_id', 0)) == runbook_id
            ]
        return {'status': 'ok', 'assignments': assignments, 'total': len(assignments)}

    @router.get('/workflow-connectors/{connector_id}/incident-timeline', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def get_connector_incident_timeline(
        connector_id: int,
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=300)] = 100,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:incident-timeline:list', 120, 60)
        with _lock:
            connector = next(
                (
                    c for c in _connectors_memory
                    if int(c.get('id', 0)) == connector_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
            timeline = _build_incident_timeline(tenant_id=auth.tenant_id, connector_id=connector_id, limit=limit)
        return {'status': 'ok', 'connector_id': connector_id, 'timeline': timeline, 'total': len(timeline)}

    @router.get('/workflow-connectors/{connector_id}/sli-trends', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def get_connector_sli_trends(
        connector_id: int,
        auth: AuthDep,
        buckets: Annotated[int, Query(ge=4, le=72)] = 12,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:sli-trends:list', 120, 60)
        with _lock:
            connector = next(
                (
                    c for c in _connectors_memory
                    if int(c.get('id', 0)) == connector_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)

            reliability = _compute_reliability_snapshot(connector)
            open_alerts = len(
                [
                    alert for alert in _connector_sla_alerts_memory
                    if alert.get('tenant_id') == auth.tenant_id
                    and int(alert.get('connector_id', 0)) == connector_id
                    and alert.get('status') == 'open'
                ]
            )
            pending_replay = len(
                [
                    item for item in _connector_replay_queue_memory
                    if item.get('tenant_id') == auth.tenant_id
                    and int(item.get('connector_id', 0)) == connector_id
                    and item.get('status') == 'pending'
                ]
            )

        now = datetime.now(UTC)
        points: list[dict[str, Any]] = []
        base_availability = float(reliability.get('availability_pct_rolling', 100.0))
        base_latency = int(reliability.get('latency_p95_ms', 120))
        pressure = min(10.0, open_alerts * 0.8 + pending_replay * 0.3)
        for idx in range(buckets):
            hours_ago = buckets - idx - 1
            drift = (hours_ago % 3) * 0.09
            availability = max(50.0, min(100.0, base_availability - pressure + drift))
            latency = max(50, base_latency + int(open_alerts * 9 + pending_replay * 4 + (hours_ago % 5) * 5))
            points.append(
                {
                    'bucket_start': (now - timedelta(hours=hours_ago)).isoformat(),
                    'availability_pct': round(availability, 2),
                    'latency_p95_ms': latency,
                }
            )

        return {
            'status': 'ok',
            'connector_id': connector_id,
            'buckets': buckets,
            'points': points,
            'targets': {
                'availability_target_pct': float(reliability.get('availability_target_pct', 99.9)),
                'latency_target_p95_ms': int(reliability.get('latency_target_p95_ms', 500)),
            },
        }

    @router.post('/workflow-connectors/postmortem-templates', summary='Create postmortem template')
    def create_postmortem_template(payload: WorkflowConnectorPostmortemTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:templates:create', 60, 60)
        with _lock:
            template = {
                'id': len(_connector_postmortem_templates_memory) + 1,
                'tenant_id': auth.tenant_id,
                'name': payload.name,
                'summary_template': payload.summary_template,
                'default_action_items': payload.default_action_items,
                'closure_sla_hours': payload.closure_sla_hours,
                'enabled': payload.enabled,
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            _connector_postmortem_templates_memory.append(template)
        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_template_created', _coerce_int(template.get('id')))
        return {'status': 'ok', 'template': template}

    @router.get('/workflow-connectors/postmortem-templates', summary='List postmortem templates')
    def list_postmortem_templates(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:templates:list', 120, 60)
        with _lock:
            templates = [
                template.copy() for template in _connector_postmortem_templates_memory
                if template.get('tenant_id') == auth.tenant_id
            ]
        templates.sort(key=lambda item: _parse_iso(item.get('created_at')), reverse=True)
        return {'status': 'ok', 'templates': templates, 'total': len(templates)}

    @router.post('/workflow-connectors/postmortem-templates/{template_id}/apply', summary='Apply postmortem template')
    def apply_postmortem_template(
        template_id: int,
        payload: WorkflowConnectorPostmortemTemplateApplyRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:templates:apply', 60, 60)
        with _lock:
            template = next(
                (
                    t for t in _connector_postmortem_templates_memory
                    if int(t.get('id', 0)) == template_id and t.get('tenant_id') == auth.tenant_id and bool(t.get('enabled', True))
                ),
                None,
            )
            if template is None:
                raise HTTPException(status_code=404, detail='Postmortem template not found.')

            connector = next(
                (
                    c for c in _connectors_memory
                    if int(c.get('id', 0)) == payload.connector_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)

            valid_event_ids = {
                int(event.get('id', 0)) for event in _connector_escalation_events_memory
                if event.get('tenant_id') == auth.tenant_id and int(event.get('connector_id', 0)) == payload.connector_id
            }
            incident_event_ids = [event_id for event_id in payload.incident_event_ids if event_id in valid_event_ids]
            now = datetime.now(UTC)
            closure_sla_hours = int(template.get('closure_sla_hours', 24))
            postmortem = {
                'id': len(_connector_postmortems_memory) + 1,
                'tenant_id': auth.tenant_id,
                'connector_id': payload.connector_id,
                'connector_name': connector.get('name'),
                'title': payload.title,
                'summary': template.get('summary_template', ''),
                'incident_event_ids': incident_event_ids,
                'action_items': list(template.get('default_action_items') or []),
                'action_items_detailed': [],
                'status': 'open',
                'closure_sla_hours': closure_sla_hours,
                'target_close_by': (now + timedelta(hours=closure_sla_hours)).isoformat(),
                'created_at': now.isoformat(),
                'updated_at': now.isoformat(),
                'template_id': template_id,
                'template_name': template.get('name'),
            }
            _connector_postmortems_memory.append(postmortem)

            for item_title in list(template.get('default_action_items') or []):
                detailed = {
                    'id': len(postmortem['action_items_detailed']) + 1,
                    'title': item_title,
                    'owner': '',
                    'status': 'open',
                    'note': '',
                    'due_at': (now + timedelta(hours=closure_sla_hours)).isoformat(),
                    'created_at': now.isoformat(),
                    'updated_at': now.isoformat(),
                }
                postmortem['action_items_detailed'].append(detailed)

        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_template_applied', int(postmortem['id']))
        return {'status': 'ok', 'postmortem': postmortem}

    @router.post('/workflow-connectors/{connector_id}/postmortems', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def create_connector_postmortem(
        connector_id: int,
        payload: WorkflowConnectorPostmortemRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:create', 60, 60)
        with _lock:
            connector = next(
                (
                    c for c in _connectors_memory
                    if int(c.get('id', 0)) == connector_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)

            valid_event_ids = {
                int(event.get('id', 0)) for event in _connector_escalation_events_memory
                if event.get('tenant_id') == auth.tenant_id and int(event.get('connector_id', 0)) == connector_id
            }
            incident_event_ids = [event_id for event_id in payload.incident_event_ids if event_id in valid_event_ids]
            postmortem = {
                'id': len(_connector_postmortems_memory) + 1,
                'tenant_id': auth.tenant_id,
                'connector_id': connector_id,
                'connector_name': connector.get('name'),
                'title': payload.title,
                'summary': payload.summary,
                'incident_event_ids': incident_event_ids,
                'action_items': payload.action_items,
                'action_items_detailed': [],
                'status': 'open',
                'closure_sla_hours': 24,
                'target_close_by': (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            _connector_postmortems_memory.append(postmortem)

        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_created', int(postmortem['id']))
        return {'status': 'ok', 'postmortem': postmortem}

    @router.get('/workflow-connectors/{connector_id}/postmortems', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def list_connector_postmortems(connector_id: int, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:list', 120, 60)
        with _lock:
            connector = next(
                (
                    c for c in _connectors_memory
                    if int(c.get('id', 0)) == connector_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
            postmortems = [
                postmortem.copy() for postmortem in _connector_postmortems_memory
                if postmortem.get('tenant_id') == auth.tenant_id and int(postmortem.get('connector_id', 0)) == connector_id
            ]

        postmortems.sort(key=lambda item: _parse_iso(item.get('created_at')), reverse=True)
        return {'status': 'ok', 'connector_id': connector_id, 'postmortems': postmortems, 'total': len(postmortems)}

    @router.post('/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def create_postmortem_action_item(
        connector_id: int,
        postmortem_id: int,
        payload: WorkflowConnectorPostmortemActionItemRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:create', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            postmortem = next(
                (
                    p for p in _connector_postmortems_memory
                    if int(p.get('id', 0)) == postmortem_id
                    and int(p.get('connector_id', 0)) == connector_id
                    and p.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if postmortem is None:
                raise HTTPException(status_code=404, detail='Postmortem not found.')
            action_items = postmortem.setdefault('action_items_detailed', [])
            action_item = {
                'id': len(action_items) + 1,
                'title': payload.title,
                'owner': payload.owner,
                'status': 'open',
                'note': '',
                'due_at': (now + timedelta(hours=payload.due_in_hours)).isoformat(),
                'created_at': now.isoformat(),
                'updated_at': now.isoformat(),
            }
            action_items.append(action_item)
            postmortem['updated_at'] = now.isoformat()
        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_action_item_created', _coerce_int(action_item.get('id')))
        return {'status': 'ok', 'action_item': action_item}

    @router.get('/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def list_postmortem_action_items(connector_id: int, postmortem_id: int, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:list', 120, 60)
        with _lock:
            postmortem = next(
                (
                    p for p in _connector_postmortems_memory
                    if int(p.get('id', 0)) == postmortem_id
                    and int(p.get('connector_id', 0)) == connector_id
                    and p.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if postmortem is None:
                raise HTTPException(status_code=404, detail='Postmortem not found.')
            action_items = [item.copy() for item in (postmortem.get('action_items_detailed') or [])]
        return {'status': 'ok', 'connector_id': connector_id, 'postmortem_id': postmortem_id, 'action_items': action_items, 'total': len(action_items)}

    @router.patch('/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/action-items/{action_item_id}', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def update_postmortem_action_item(
        connector_id: int,
        postmortem_id: int,
        action_item_id: int,
        payload: WorkflowConnectorPostmortemActionItemUpdateRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:update', 120, 60)
        normalized_status = payload.status.strip().lower()
        if normalized_status not in {'open', 'in_progress', 'done', 'blocked'}:
            raise HTTPException(status_code=422, detail='Invalid action item status.')
        with _lock:
            postmortem = next(
                (
                    p for p in _connector_postmortems_memory
                    if int(p.get('id', 0)) == postmortem_id
                    and int(p.get('connector_id', 0)) == connector_id
                    and p.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if postmortem is None:
                raise HTTPException(status_code=404, detail='Postmortem not found.')
            action_item = next(
                (item for item in (postmortem.get('action_items_detailed') or []) if int(item.get('id', 0)) == action_item_id),
                None,
            )
            if action_item is None:
                raise HTTPException(status_code=404, detail='Action item not found.')
            action_item['status'] = normalized_status
            action_item['note'] = payload.note
            action_item['updated_at'] = datetime.now(UTC).isoformat()
            postmortem['updated_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_action_item_updated', action_item_id)
        return {'status': 'ok', 'action_item': action_item}

    @router.post('/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/close', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def close_postmortem(
        connector_id: int,
        postmortem_id: int,
        payload: WorkflowConnectorPostmortemCloseRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:close', 60, 60)
        with _lock:
            postmortem = next(
                (
                    p for p in _connector_postmortems_memory
                    if int(p.get('id', 0)) == postmortem_id
                    and int(p.get('connector_id', 0)) == connector_id
                    and p.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if postmortem is None:
                raise HTTPException(status_code=404, detail='Postmortem not found.')

            action_items = list(postmortem.get('action_items_detailed') or [])
            open_items = [item for item in action_items if str(item.get('status', '')).lower() != 'done']
            if payload.require_action_items_resolved and open_items:
                raise HTTPException(status_code=409, detail='Action items must be completed before closure.')

            policy = next(
                (
                    p for p in _connector_postmortem_closure_policies_memory
                    if p.get('tenant_id') == auth.tenant_id and bool(p.get('enabled', False))
                ),
                None,
            )
            if policy is not None:
                enforce_for_breached_only = bool(policy.get('enforce_for_breached_sla_only', False))
                needs_approval = True
                if enforce_for_breached_only:
                    needs_approval = str(postmortem.get('closure_sla_status', '')).lower() == 'breached'
                if needs_approval:
                    required_approvals = int(policy.get('required_approvals', 1))
                    approved_request = next(
                        (
                            r for r in _connector_postmortem_closure_requests_memory
                            if r.get('tenant_id') == auth.tenant_id
                            and int(r.get('postmortem_id', 0)) == postmortem_id
                            and r.get('status') == 'approved'
                            and len(r.get('approved_by') or []) >= required_approvals
                        ),
                        None,
                    )
                    if approved_request is None:
                        raise HTTPException(status_code=409, detail='Approved postmortem closure request required by policy.')

            now = datetime.now(UTC)
            target_close_by = _parse_iso(postmortem.get('target_close_by'))
            postmortem['status'] = 'closed'
            postmortem['closed_at'] = now.isoformat()
            postmortem['closed_by'] = payload.closed_by
            postmortem['closure_note'] = payload.note
            postmortem['closure_sla_status'] = 'met' if now <= target_close_by else 'breached'
            postmortem['updated_at'] = now.isoformat()

        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_closed', postmortem_id)
        return {'status': 'ok', 'postmortem': postmortem}

    @router.post('/workflow-connectors/postmortems/closure-policy', summary='Upsert postmortem closure approval policy')
    def upsert_postmortem_closure_policy(
        payload: WorkflowConnectorPostmortemClosurePolicyRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:closure-policy:upsert', 60, 60)
        with _lock:
            policy = next((p for p in _connector_postmortem_closure_policies_memory if p.get('tenant_id') == auth.tenant_id), None)
            if policy is None:
                policy = {
                    'id': len(_connector_postmortem_closure_policies_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'enabled': payload.enabled,
                    'required_approvals': payload.required_approvals,
                    'approver_roles': payload.approver_roles,
                    'enforce_for_breached_sla_only': payload.enforce_for_breached_sla_only,
                    'created_at': datetime.now(UTC).isoformat(),
                    'updated_at': datetime.now(UTC).isoformat(),
                }
                _connector_postmortem_closure_policies_memory.append(policy)
            else:
                policy['enabled'] = payload.enabled
                policy['required_approvals'] = payload.required_approvals
                policy['approver_roles'] = payload.approver_roles
                policy['enforce_for_breached_sla_only'] = payload.enforce_for_breached_sla_only
                policy['updated_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_closure_policy_upserted', int(policy['id']))
        return {'status': 'ok', 'policy': policy}

    @router.get('/workflow-connectors/postmortems/closure-policy', summary='Get postmortem closure approval policy')
    def get_postmortem_closure_policy(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:closure-policy:get', 120, 60)
        with _lock:
            policy = next((p.copy() for p in _connector_postmortem_closure_policies_memory if p.get('tenant_id') == auth.tenant_id), None)
        if policy is None:
            return {
                'status': 'ok',
                'policy': {
                    'enabled': False,
                    'required_approvals': 1,
                    'approver_roles': [],
                    'enforce_for_breached_sla_only': False,
                },
            }
        return {'status': 'ok', 'policy': policy}

    @router.post('/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/closure-requests', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def create_postmortem_closure_request(connector_id: int, postmortem_id: int, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:closure-requests:create', 90, 60)
        with _lock:
            postmortem = next(
                (
                    p for p in _connector_postmortems_memory
                    if int(p.get('id', 0)) == postmortem_id
                    and int(p.get('connector_id', 0)) == connector_id
                    and p.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if postmortem is None:
                raise HTTPException(status_code=404, detail='Postmortem not found.')
            existing = next(
                (
                    r for r in _connector_postmortem_closure_requests_memory
                    if r.get('tenant_id') == auth.tenant_id
                    and int(r.get('postmortem_id', 0)) == postmortem_id
                    and r.get('status') == 'pending'
                ),
                None,
            )
            if existing is not None:
                return {'status': 'ok', 'closure_request': existing, 'reused': True}

            policy = next((p for p in _connector_postmortem_closure_policies_memory if p.get('tenant_id') == auth.tenant_id), None)
            required_approvals = int((policy or {}).get('required_approvals', 1))
            closure_request = {
                'id': len(_connector_postmortem_closure_requests_memory) + 1,
                'tenant_id': auth.tenant_id,
                'connector_id': connector_id,
                'postmortem_id': postmortem_id,
                'status': 'pending',
                'required_approvals': required_approvals,
                'approved_by': [],
                'rejected_by': [],
                'created_at': datetime.now(UTC).isoformat(),
                'updated_at': datetime.now(UTC).isoformat(),
            }
            _connector_postmortem_closure_requests_memory.append(closure_request)
        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_closure_request_created', _coerce_int(closure_request.get('id')))
        return {'status': 'ok', 'closure_request': closure_request, 'reused': False}

    @router.post('/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/closure-requests/{request_id}/decision', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def decide_postmortem_closure_request(
        connector_id: int,
        postmortem_id: int,
        request_id: int,
        payload: WorkflowConnectorPostmortemClosureDecisionRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:closure-requests:decision', 120, 60)
        decision = payload.decision.strip().lower()
        if decision not in {'approve', 'reject'}:
            raise HTTPException(status_code=422, detail='Invalid decision.')
        with _lock:
            closure_request = next(
                (
                    r for r in _connector_postmortem_closure_requests_memory
                    if int(r.get('id', 0)) == request_id
                    and int(r.get('connector_id', 0)) == connector_id
                    and int(r.get('postmortem_id', 0)) == postmortem_id
                    and r.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if closure_request is None:
                raise HTTPException(status_code=404, detail='Closure request not found.')
            if closure_request.get('status') not in {'pending', 'approved'}:
                raise HTTPException(status_code=409, detail='Closure request is not active.')

            if decision == 'approve':
                approved_by = closure_request.setdefault('approved_by', [])
                if payload.reviewer not in approved_by:
                    approved_by.append(payload.reviewer)
                required_approvals = int(closure_request.get('required_approvals', 1))
                closure_request['status'] = 'approved' if len(approved_by) >= required_approvals else 'pending'
            else:
                rejected_by = closure_request.setdefault('rejected_by', [])
                if payload.reviewer not in rejected_by:
                    rejected_by.append(payload.reviewer)
                closure_request['status'] = 'rejected'
            closure_request['last_decision'] = {
                'decision': decision,
                'reviewer': payload.reviewer,
                'note': payload.note,
                'decided_at': datetime.now(UTC).isoformat(),
            }
            closure_request['updated_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_closure_request_decided', request_id)
        return {'status': 'ok', 'closure_request': closure_request}

    @router.post('/workflow-connectors/postmortems/action-items/process-overdue', summary='Escalate overdue postmortem action items')
    def process_overdue_postmortem_action_items(
        payload: WorkflowConnectorOverdueEscalationProcessRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:overdue:process', 60, 60)
        processed: list[dict[str, Any]] = []
        now = datetime.now(UTC)
        with _lock:
            for postmortem in _connector_postmortems_memory:
                if postmortem.get('tenant_id') != auth.tenant_id:
                    continue
                connector_id = int(postmortem.get('connector_id', 0))
                if payload.connector_id is not None and connector_id != payload.connector_id:
                    continue
                if postmortem.get('status') == 'closed':
                    continue
                for action_item in (postmortem.get('action_items_detailed') or []):
                    if str(action_item.get('status', '')).lower() == 'done':
                        continue
                    due_at = _parse_iso(action_item.get('due_at'))
                    if due_at > now and not payload.include_not_due:
                        continue
                    overdue_hours = max(0, int((now - due_at).total_seconds() // 3600))
                    policy = next(
                        (
                            p for p in _connector_postmortem_escalation_routing_policies_memory
                            if p.get('tenant_id') == auth.tenant_id and bool(p.get('enabled', True))
                        ),
                        None,
                    )
                    if policy is None:
                        policy = {
                            'medium_threshold_hours': 1,
                            'high_threshold_hours': 24,
                            'critical_threshold_hours': 72,
                            'paging_start_hour_utc': 8,
                            'paging_end_hour_utc': 20,
                            'in_window_channel': 'pagerduty',
                            'off_window_channel': 'email',
                            'medium_recipients': [],
                            'high_recipients': [],
                            'critical_recipients': [],
                        }
                    medium_threshold = int(policy.get('medium_threshold_hours', 1))
                    high_threshold = int(policy.get('high_threshold_hours', 24))
                    critical_threshold = int(policy.get('critical_threshold_hours', 72))
                    if overdue_hours >= critical_threshold:
                        severity = 'critical'
                    elif overdue_hours >= high_threshold:
                        severity = 'high'
                    elif overdue_hours >= medium_threshold:
                        severity = 'medium'
                    else:
                        severity = 'medium'

                    start_hour = int(policy.get('paging_start_hour_utc', 8))
                    end_hour = int(policy.get('paging_end_hour_utc', 20))
                    hour = now.hour
                    if start_hour == end_hour:
                        in_window = True
                    elif start_hour < end_hour:
                        in_window = start_hour <= hour < end_hour
                    else:
                        in_window = hour >= start_hour or hour < end_hour
                    channel = str(policy.get('in_window_channel', 'pagerduty')) if in_window else str(policy.get('off_window_channel', 'email'))
                    recipients = list(policy.get(f'{severity}_recipients', []))

                    already_escalated = any(
                        int(escalation.get('postmortem_id', 0)) == int(postmortem.get('id', 0))
                        and int(escalation.get('action_item_id', 0)) == int(action_item.get('id', 0))
                        and escalation.get('status') == 'open'
                        for escalation in _connector_postmortem_action_item_escalations_memory
                        if escalation.get('tenant_id') == auth.tenant_id
                    )
                    if already_escalated:
                        continue
                    escalation = {
                        'id': len(_connector_postmortem_action_item_escalations_memory) + 1,
                        'tenant_id': auth.tenant_id,
                        'connector_id': connector_id,
                        'postmortem_id': int(postmortem.get('id', 0)),
                        'action_item_id': int(action_item.get('id', 0)),
                        'owner': action_item.get('owner', ''),
                        'status': 'open',
                        'reason': 'action_item_overdue',
                        'severity': severity,
                        'channel': channel,
                        'in_paging_window': in_window,
                        'notify_recipients': recipients,
                        'overdue_hours': overdue_hours,
                        'tier': 'l1',
                        'repage_count': 0,
                        'first_paged_at': now.isoformat(),
                        'last_paged_at': now.isoformat(),
                        'next_repage_at': now.isoformat(),
                        'created_at': now.isoformat(),
                    }
                    _connector_postmortem_action_item_escalations_memory.append(escalation)
                    action_item['status'] = 'blocked'
                    action_item['updated_at'] = now.isoformat()
                    processed.append(escalation)
                    if len(processed) >= payload.limit:
                        break
                if len(processed) >= payload.limit:
                    break

        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_overdue_action_items_processed', len(processed))
        return {'status': 'ok', 'processed': processed, 'count': len(processed)}

    @router.get('/workflow-connectors/postmortems/action-items/escalations', summary='List overdue action-item escalations')
    def list_postmortem_action_item_escalations(
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:overdue:list', 120, 60)
        with _lock:
            escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id
            ]
        escalations.sort(key=lambda item: _parse_iso(item.get('created_at')), reverse=True)
        return {'status': 'ok', 'escalations': escalations[:limit], 'total': len(escalations)}

    @router.post('/workflow-connectors/postmortems/action-items/escalations/{escalation_id}/acknowledge', summary='Acknowledge and close overdue action-item escalation')
    def acknowledge_action_item_escalation(
        escalation_id: int,
        payload: WorkflowConnectorEscalationAcknowledgeAdminRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalations:ack', 120, 60)
        with _lock:
            escalation = next(
                (
                    item for item in _connector_postmortem_action_item_escalations_memory
                    if int(item.get('id', 0)) == escalation_id and item.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if escalation is None:
                raise HTTPException(status_code=404, detail='Escalation not found.')
            escalation['status'] = 'acknowledged'
            escalation['acknowledged_by'] = payload.acknowledged_by
            escalation['acknowledged_note'] = payload.note
            escalation['acknowledged_at'] = datetime.now(UTC).isoformat()

        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_action_item_escalation_acknowledged', escalation_id)
        return {'status': 'ok', 'escalation': escalation}

    @router.post('/workflow-connectors/postmortems/escalation-routing-policy', summary='Upsert overdue action-item escalation routing policy')
    def upsert_postmortem_escalation_routing_policy(
        payload: WorkflowConnectorEscalationRoutingPolicyRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:escalation-routing:upsert', 60, 60)
        with _lock:
            policy = next(
                (p for p in _connector_postmortem_escalation_routing_policies_memory if p.get('tenant_id') == auth.tenant_id),
                None,
            )
            if policy is None:
                policy = {
                    'id': len(_connector_postmortem_escalation_routing_policies_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'created_at': datetime.now(UTC).isoformat(),
                }
                _connector_postmortem_escalation_routing_policies_memory.append(policy)

            policy.update(
                {
                    'enabled': payload.enabled,
                    'paging_start_hour_utc': payload.paging_start_hour_utc,
                    'paging_end_hour_utc': payload.paging_end_hour_utc,
                    'in_window_channel': payload.in_window_channel,
                    'off_window_channel': payload.off_window_channel,
                    'medium_threshold_hours': payload.medium_threshold_hours,
                    'high_threshold_hours': payload.high_threshold_hours,
                    'critical_threshold_hours': payload.critical_threshold_hours,
                    'medium_recipients': payload.medium_recipients,
                    'high_recipients': payload.high_recipients,
                    'critical_recipients': payload.critical_recipients,
                    'updated_at': datetime.now(UTC).isoformat(),
                }
            )

        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_escalation_routing_policy_upserted', int(policy['id']))
        return {'status': 'ok', 'policy': policy}

    @router.get('/workflow-connectors/postmortems/escalation-routing-policy', summary='Get overdue action-item escalation routing policy')
    def get_postmortem_escalation_routing_policy(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:escalation-routing:get', 120, 60)
        with _lock:
            policy = next(
                (p.copy() for p in _connector_postmortem_escalation_routing_policies_memory if p.get('tenant_id') == auth.tenant_id),
                None,
            )
        if policy is None:
            return {
                'status': 'ok',
                'policy': {
                    'enabled': False,
                    'paging_start_hour_utc': 8,
                    'paging_end_hour_utc': 20,
                    'in_window_channel': 'pagerduty',
                    'off_window_channel': 'email',
                    'medium_threshold_hours': 1,
                    'high_threshold_hours': 24,
                    'critical_threshold_hours': 72,
                    'medium_recipients': [],
                    'high_recipients': [],
                    'critical_recipients': [],
                },
            }
        return {'status': 'ok', 'policy': policy}

    @router.post('/workflow-connectors/postmortems/escalation-cadence-policy', summary='Upsert escalation cadence policy for L1/L2/L3 handoffs')
    def upsert_postmortem_escalation_cadence_policy(
        payload: WorkflowConnectorEscalationCadencePolicyRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:escalation-cadence:upsert', 60, 60)
        with _lock:
            policy = next(
                (p for p in _connector_postmortem_escalation_cadence_policies_memory if p.get('tenant_id') == auth.tenant_id),
                None,
            )
            if policy is None:
                policy = {
                    'id': len(_connector_postmortem_escalation_cadence_policies_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'created_at': datetime.now(UTC).isoformat(),
                }
                _connector_postmortem_escalation_cadence_policies_memory.append(policy)

            policy.update(
                {
                    'enabled': payload.enabled,
                    'l2_after_minutes': payload.l2_after_minutes,
                    'l3_after_minutes': payload.l3_after_minutes,
                    'repage_interval_minutes': payload.repage_interval_minutes,
                    'max_repages': payload.max_repages,
                    'suppression_ttl_minutes': payload.suppression_ttl_minutes,
                    'reopen_on_reoverdue': payload.reopen_on_reoverdue,
                    'l1_recipients': payload.l1_recipients,
                    'l2_recipients': payload.l2_recipients,
                    'l3_recipients': payload.l3_recipients,
                    'updated_at': datetime.now(UTC).isoformat(),
                }
            )

        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_escalation_cadence_policy_upserted', int(policy['id']))
        return {'status': 'ok', 'policy': policy}

    @router.get('/workflow-connectors/postmortems/escalation-cadence-policy', summary='Get escalation cadence policy for L1/L2/L3 handoffs')
    def get_postmortem_escalation_cadence_policy(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:escalation-cadence:get', 120, 60)
        with _lock:
            policy = next(
                (p.copy() for p in _connector_postmortem_escalation_cadence_policies_memory if p.get('tenant_id') == auth.tenant_id),
                None,
            )
        if policy is None:
            return {
                'status': 'ok',
                'policy': {
                    'enabled': False,
                    'l2_after_minutes': 30,
                    'l3_after_minutes': 90,
                    'repage_interval_minutes': 30,
                    'max_repages': 8,
                    'suppression_ttl_minutes': 240,
                    'reopen_on_reoverdue': True,
                    'l1_recipients': [],
                    'l2_recipients': [],
                    'l3_recipients': [],
                },
            }
        return {'status': 'ok', 'policy': policy}

    @router.post('/workflow-connectors/postmortems/action-items/escalations/process-cadence', summary='Process L1/L2/L3 escalation cadence and re-page schedule')
    def process_postmortem_escalation_cadence(
        payload: WorkflowConnectorEscalationCadenceProcessRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:escalation-cadence:process', 60, 60)
        now = datetime.now(UTC)
        processed: list[dict[str, Any]] = []
        with _lock:
            policy = next(
                (
                    p for p in _connector_postmortem_escalation_cadence_policies_memory
                    if p.get('tenant_id') == auth.tenant_id and bool(p.get('enabled', False))
                ),
                None,
            )
            if policy is None:
                return {'status': 'ok', 'processed': [], 'count': 0}

            l2_after = int(policy.get('l2_after_minutes', 30))
            l3_after = int(policy.get('l3_after_minutes', 90))
            repage_interval = int(policy.get('repage_interval_minutes', 30))
            max_repages = int(policy.get('max_repages', 8))
            suppression_ttl_minutes = int(policy.get('suppression_ttl_minutes', 240))
            l1_recipients = list(policy.get('l1_recipients', []))
            l2_recipients = list(policy.get('l2_recipients', []))
            l3_recipients = list(policy.get('l3_recipients', []))

            for escalation in _connector_postmortem_action_item_escalations_memory:
                if escalation.get('tenant_id') != auth.tenant_id or escalation.get('status') != 'open':
                    continue
                next_repage_at = _parse_iso(escalation.get('next_repage_at'))
                if next_repage_at > now:
                    continue

                created_at = _parse_iso(escalation.get('created_at'))
                elapsed_minutes = max(0, int((now - created_at).total_seconds() // 60))
                current_tier = str(escalation.get('tier', 'l1')).lower()
                target_tier = current_tier
                if elapsed_minutes >= l3_after:
                    target_tier = 'l3'
                elif elapsed_minutes >= l2_after and current_tier == 'l1':
                    target_tier = 'l2'

                if target_tier == 'l1':
                    recipients = l1_recipients
                elif target_tier == 'l2':
                    recipients = l2_recipients
                else:
                    recipients = l3_recipients

                repage_count = int(escalation.get('repage_count', 0)) + 1
                escalation['tier'] = target_tier
                escalation['notify_recipients'] = recipients
                escalation['repage_count'] = repage_count
                escalation['last_paged_at'] = now.isoformat()
                escalation['next_repage_at'] = (now + timedelta(minutes=repage_interval)).isoformat()
                if repage_count >= max_repages:
                    escalation['status'] = 'suppressed'
                    escalation['suppressed_at'] = now.isoformat()
                    escalation['suppressed_until'] = (now + timedelta(minutes=suppression_ttl_minutes)).isoformat()
                processed.append(escalation.copy())
                if len(processed) >= payload.limit:
                    break

        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_escalation_cadence_processed', len(processed))
        return {'status': 'ok', 'processed': processed, 'count': len(processed)}

    @router.post('/workflow-connectors/postmortems/action-items/escalations/process-suppression', summary='Process suppressed escalations and reopen when still overdue')
    def process_postmortem_escalation_suppression(
        payload: WorkflowConnectorEscalationSuppressionProcessRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:escalation-suppression:process', 60, 60)
        now = datetime.now(UTC)
        reopened: list[dict[str, Any]] = []
        with _lock:
            policy = next(
                (
                    p for p in _connector_postmortem_escalation_cadence_policies_memory
                    if p.get('tenant_id') == auth.tenant_id and bool(p.get('enabled', False))
                ),
                None,
            )
            if policy is None or not bool(policy.get('reopen_on_reoverdue', True)):
                return {'status': 'ok', 'reopened': [], 'count': 0}

            for escalation in _connector_postmortem_action_item_escalations_memory:
                if escalation.get('tenant_id') != auth.tenant_id or escalation.get('status') != 'suppressed':
                    continue
                suppressed_until = _parse_iso(escalation.get('suppressed_until'))
                if suppressed_until > now:
                    continue

                postmortem = next(
                    (
                        p for p in _connector_postmortems_memory
                        if int(p.get('id', 0)) == int(escalation.get('postmortem_id', 0))
                        and p.get('tenant_id') == auth.tenant_id
                    ),
                    None,
                )
                if postmortem is None:
                    continue
                action_item = next(
                    (
                        item for item in (postmortem.get('action_items_detailed') or [])
                        if int(item.get('id', 0)) == int(escalation.get('action_item_id', 0))
                    ),
                    None,
                )
                if action_item is None:
                    continue
                if str(action_item.get('status', '')).lower() == 'done':
                    escalation['status'] = 'closed'
                    escalation['closed_at'] = now.isoformat()
                    continue

                escalation['status'] = 'open'
                escalation['tier'] = 'l1'
                escalation['reopened_at'] = now.isoformat()
                escalation['next_repage_at'] = now.isoformat()
                reopened.append(escalation.copy())
                if len(reopened) >= payload.limit:
                    break

        _append_audit(auth.tenant_id, 'workflow_connector_postmortem_escalation_suppression_processed', len(reopened))
        return {'status': 'ok', 'reopened': reopened, 'count': len(reopened)}

    @router.get('/workflow-connectors/postmortems/action-items/escalations/aging-dashboard', summary='Escalation aging SLO dashboard')
    def get_postmortem_escalation_aging_dashboard(
        auth: AuthDep,
        ack_slo_minutes: Annotated[int, Query(ge=5, le=2880)] = 60,
        lookback_hours: Annotated[int, Query(ge=1, le=720)] = 168,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:escalation-aging:get', 120, 60)
        now = datetime.now(UTC)
        lookback_start = now - timedelta(hours=lookback_hours)
        with _lock:
            escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and _parse_iso(item.get('created_at')) >= lookback_start
            ]

        open_escalations = [item for item in escalations if item.get('status') == 'open']
        acknowledged_escalations = [item for item in escalations if item.get('status') in {'acknowledged', 'closed'} and item.get('acknowledged_at')]
        ack_within_slo = 0
        for item in acknowledged_escalations:
            created_at = _parse_iso(item.get('created_at'))
            acknowledged_at = _parse_iso(item.get('acknowledged_at'))
            ack_minutes = int((acknowledged_at - created_at).total_seconds() // 60)
            if ack_minutes <= ack_slo_minutes:
                ack_within_slo += 1

        age_0_30 = 0
        age_31_120 = 0
        age_121_plus = 0
        for item in open_escalations:
            age_minutes = int((now - _parse_iso(item.get('created_at'))).total_seconds() // 60)
            if age_minutes <= 30:
                age_0_30 += 1
            elif age_minutes <= 120:
                age_31_120 += 1
            else:
                age_121_plus += 1

        ack_slo_compliance_pct = round((ack_within_slo / len(acknowledged_escalations)) * 100, 2) if acknowledged_escalations else 100.0
        return {
            'status': 'ok',
            'ack_slo_minutes': ack_slo_minutes,
            'lookback_hours': lookback_hours,
            'total_escalations': len(escalations),
            'open_escalations': len(open_escalations),
            'acknowledged_escalations': len(acknowledged_escalations),
            'ack_slo_compliance_pct': ack_slo_compliance_pct,
            'age_buckets': {
                '0_30_minutes': age_0_30,
                '31_120_minutes': age_31_120,
                '121_plus_minutes': age_121_plus,
            },
        }

    @router.get('/workflow-connectors/postmortems/action-items/breach-forecast', summary='Forecast action items at risk of SLA breach')
    def get_postmortem_action_item_breach_forecast(
        auth: AuthDep,
        window_hours: Annotated[int, Query(ge=1, le=168)] = 24,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:breach-forecast:get', 120, 60)
        now = datetime.now(UTC)
        window_end = now + timedelta(hours=window_hours)
        at_risk_items: list[dict[str, Any]] = []
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id
            ]

        escalation_by_action_item: dict[tuple[int, int], dict[str, Any]] = {}
        for escalation in escalations:
            key = (int(escalation.get('postmortem_id', 0)), int(escalation.get('action_item_id', 0)))
            existing = escalation_by_action_item.get(key)
            if existing is None or _parse_iso(escalation.get('created_at')) > _parse_iso(existing.get('created_at')):
                escalation_by_action_item[key] = escalation

        for postmortem in tenant_postmortems:
            if str(postmortem.get('status', '')).lower() == 'closed':
                continue
            connector_id = int(postmortem.get('connector_id', 0))
            for action_item in (postmortem.get('action_items_detailed') or []):
                action_status = str(action_item.get('status', '')).lower()
                if action_status == 'done':
                    continue
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at > window_end and due_at >= now:
                    continue

                minutes_to_due = int((due_at - now).total_seconds() // 60)
                if due_at < now:
                    risk_level = 'breached'
                elif minutes_to_due <= 60:
                    risk_level = 'critical_soon'
                elif minutes_to_due <= 240:
                    risk_level = 'high_soon'
                else:
                    risk_level = 'due_soon'

                escalation: dict[str, Any] | None = escalation_by_action_item.get((_coerce_int(postmortem.get('id', 0)), _coerce_int(action_item.get('id', 0))))
                at_risk_items.append(
                    {
                        'connector_id': connector_id,
                        'postmortem_id': int(postmortem.get('id', 0)),
                        'action_item_id': int(action_item.get('id', 0)),
                        'action_item_title': action_item.get('title', ''),
                        'action_item_status': action_item.get('status', ''),
                        'owner': action_item.get('owner', ''),
                        'due_at': due_at.isoformat(),
                        'minutes_to_due': minutes_to_due,
                        'risk_level': risk_level,
                        'escalation_status': escalation.get('status') if escalation else None,
                        'escalation_tier': escalation.get('tier') if escalation else None,
                    }
                )

        risk_order = {'breached': 0, 'critical_soon': 1, 'high_soon': 2, 'due_soon': 3}
        at_risk_items.sort(
            key=lambda item: (
                risk_order.get(str(item.get('risk_level', 'due_soon')), 9),
                int(item.get('minutes_to_due', 0)),
            )
        )
        trimmed = at_risk_items[:limit]
        breached_count = len([item for item in trimmed if item.get('risk_level') == 'breached'])
        return {
            'status': 'ok',
            'window_hours': window_hours,
            'total_candidates': len(at_risk_items),
            'at_risk_total': len(trimmed),
            'breached_count': breached_count,
            'items': trimmed,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalations/priority-queue', summary='Priority queue for overdue action-item escalations')
    def get_postmortem_escalation_priority_queue(
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        include_suppressed: bool = True,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalations:priority-queue:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            candidates = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id
                and str(item.get('status', '')) in ({'open', 'acknowledged', 'suppressed'} if include_suppressed else {'open', 'acknowledged'})
            ]

        severity_weights = {'critical': 4, 'high': 3, 'medium': 2}
        tier_boost = {'l3': 25, 'l2': 15, 'l1': 5}
        queue_items: list[dict[str, Any]] = []
        for escalation in candidates:
            created_at = _parse_iso(escalation.get('created_at'))
            age_minutes = max(0, int((now - created_at).total_seconds() // 60))
            severity = str(escalation.get('severity', 'medium')).lower()
            tier = str(escalation.get('tier', 'l1')).lower()
            repage_count = int(escalation.get('repage_count', 0))
            status = str(escalation.get('status', 'open')).lower()
            status_penalty = 10 if status == 'acknowledged' else 0
            suppression_boost = 30 if status == 'suppressed' else 0
            priority_score = (
                severity_weights.get(severity, 1) * 100
                + tier_boost.get(tier, 0)
                + min(age_minutes, 720)
                + repage_count * 5
                + suppression_boost
                - status_penalty
            )
            if status == 'suppressed':
                recommended_action = 'process_suppression'
            elif tier == 'l3':
                recommended_action = 'exec_page'
            elif repage_count >= 3:
                recommended_action = 'incident_command_review'
            elif status == 'acknowledged':
                recommended_action = 'follow_up_owner'
            else:
                recommended_action = 'repage_or_ack'

            queue_items.append(
                {
                    **escalation,
                    'age_minutes': age_minutes,
                    'priority_score': priority_score,
                    'recommended_action': recommended_action,
                }
            )

        queue_items.sort(key=lambda item: int(item.get('priority_score', 0)), reverse=True)
        ranked = []
        for idx, item in enumerate(queue_items[:limit], start=1):
            item_with_rank = item.copy()
            item_with_rank['rank'] = idx
            ranked.append(item_with_rank)

        return {
            'status': 'ok',
            'include_suppressed': include_suppressed,
            'total_candidates': len(queue_items),
            'queue': ranked,
            'count': len(ranked),
        }

    @router.get('/workflow-connectors/postmortems/action-items/owner-workload', summary='Owner workload dashboard for action-item governance')
    def get_postmortem_action_item_owner_workload(
        auth: AuthDep,
        include_done: bool = False,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:owner-workload:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            tenant_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id
            ]

        action_item_owner: dict[tuple[int, int], str] = {}
        owner_stats: dict[str, dict[str, Any]] = {}
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                status = str(action_item.get('status', 'open')).lower()
                if not include_done and status == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                stats = owner_stats.setdefault(
                    owner,
                    {
                        'owner': owner,
                        'open_action_items': 0,
                        'blocked_action_items': 0,
                        'overdue_open_items': 0,
                        'open_escalations': 0,
                        'acknowledged_escalations': 0,
                        'suppressed_escalations': 0,
                    },
                )
                if status in {'open', 'blocked'}:
                    stats['open_action_items'] = int(stats['open_action_items']) + 1
                if status == 'blocked':
                    stats['blocked_action_items'] = int(stats['blocked_action_items']) + 1
                if status != 'done' and _parse_iso(action_item.get('due_at')) < now:
                    stats['overdue_open_items'] = int(stats['overdue_open_items']) + 1
                action_item_owner[(int(postmortem.get('id', 0)), int(action_item.get('id', 0)))] = owner

        for escalation in tenant_escalations:
            owner = action_item_owner.get(
                (int(escalation.get('postmortem_id', 0)), int(escalation.get('action_item_id', 0))),
                'unassigned',
            )
            stats = owner_stats.setdefault(
                owner,
                {
                    'owner': owner,
                    'open_action_items': 0,
                    'blocked_action_items': 0,
                    'overdue_open_items': 0,
                    'open_escalations': 0,
                    'acknowledged_escalations': 0,
                    'suppressed_escalations': 0,
                },
            )
            escalation_status = str(escalation.get('status', 'open')).lower()
            if escalation_status == 'open':
                stats['open_escalations'] = int(stats['open_escalations']) + 1
            elif escalation_status == 'acknowledged':
                stats['acknowledged_escalations'] = int(stats['acknowledged_escalations']) + 1
            elif escalation_status == 'suppressed':
                stats['suppressed_escalations'] = int(stats['suppressed_escalations']) + 1

        owners: list[dict[str, Any]] = []
        for stats in owner_stats.values():
            workload_score = (
                int(stats.get('open_action_items', 0)) * 3
                + int(stats.get('overdue_open_items', 0)) * 5
                + int(stats.get('open_escalations', 0)) * 8
                + int(stats.get('suppressed_escalations', 0)) * 4
            )
            row = stats.copy()
            row['workload_score'] = workload_score
            owners.append(row)

        owners.sort(key=lambda item: int(item.get('workload_score', 0)), reverse=True)
        total_open_items = sum(int(item.get('open_action_items', 0)) for item in owners)
        total_open_escalations = sum(int(item.get('open_escalations', 0)) for item in owners)
        return {
            'status': 'ok',
            'include_done': include_done,
            'owners': owners,
            'total_owners': len(owners),
            'total_open_action_items': total_open_items,
            'total_open_escalations': total_open_escalations,
        }

    @router.post('/workflow-connectors/postmortems/action-items/rebalance-suggestions', summary='Recommend owner rebalance suggestions for open action items')
    def get_postmortem_action_item_rebalance_suggestions(
        payload: WorkflowConnectorActionItemRebalanceRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:rebalance-suggestions:get', 60, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]

        owner_open_counts: dict[str, int] = {}
        candidate_items: list[dict[str, Any]] = []
        for postmortem in tenant_postmortems:
            postmortem_id = int(postmortem.get('id', 0))
            connector_id = int(postmortem.get('connector_id', 0))
            for action_item in (postmortem.get('action_items_detailed') or []):
                status = str(action_item.get('status', 'open')).lower()
                if status == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_counts[owner] = int(owner_open_counts.get(owner, 0)) + 1
                due_at = _parse_iso(action_item.get('due_at'))
                candidate_items.append(
                    {
                        'connector_id': connector_id,
                        'postmortem_id': postmortem_id,
                        'action_item_id': int(action_item.get('id', 0)),
                        'action_item_title': action_item.get('title', ''),
                        'from_owner': owner,
                        'due_at': due_at.isoformat(),
                        'minutes_overdue': max(0, int((now - due_at).total_seconds() // 60)),
                    }
                )

        max_open = int(payload.max_open_items_per_owner)
        overloaded = [
            owner for owner, count in owner_open_counts.items()
            if count > max_open and (payload.include_unassigned or owner != 'unassigned')
        ]
        underloaded = [
            owner for owner, count in owner_open_counts.items()
            if owner != 'unassigned' and count < max_open
        ]

        if not underloaded:
            return {
                'status': 'ok',
                'max_open_items_per_owner': max_open,
                'suggestions': [],
                'count': 0,
                'reason': 'No underloaded owners available for reassignment.',
            }

        candidate_items.sort(
            key=lambda item: (
                0 if int(item.get('minutes_overdue', 0)) > 0 else 1,
                -int(item.get('minutes_overdue', 0)),
            )
        )

        suggestions: list[dict[str, Any]] = []
        for item in candidate_items:
            from_owner = str(item.get('from_owner', 'unassigned'))
            if from_owner not in overloaded:
                continue
            underloaded.sort(key=lambda owner: int(owner_open_counts.get(owner, 0)))
            to_owner = underloaded[0]
            if from_owner == to_owner:
                continue
            suggestions.append(
                {
                    **item,
                    'to_owner': to_owner,
                    'reason': 'source_owner_over_capacity',
                }
            )
            owner_open_counts[from_owner] = int(owner_open_counts.get(from_owner, 0)) - 1
            owner_open_counts[to_owner] = int(owner_open_counts.get(to_owner, 0)) + 1
            if owner_open_counts[from_owner] <= max_open and from_owner in overloaded:
                overloaded.remove(from_owner)
            if owner_open_counts[to_owner] >= max_open and to_owner in underloaded:
                underloaded.remove(to_owner)
            if len(suggestions) >= payload.limit or not overloaded or not underloaded:
                break

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open,
            'suggestions': suggestions,
            'count': len(suggestions),
        }

    @router.get('/workflow-connectors/postmortems/action-items/workload-hotspots', summary='Owner workload hotspots dashboard')
    def get_postmortem_action_item_workload_hotspots(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
        max_overdue_items_per_owner: Annotated[int, Query(ge=0, le=100)] = 1,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:workload-hotspots:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            tenant_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id
            ]

        owner_stats: dict[str, dict[str, Any]] = {}
        action_item_owner: dict[tuple[int, int], str] = {}
        for postmortem in tenant_postmortems:
            postmortem_id = int(postmortem.get('id', 0))
            for action_item in (postmortem.get('action_items_detailed') or []):
                status = str(action_item.get('status', 'open')).lower()
                if status == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                due_at = _parse_iso(action_item.get('due_at'))
                stats = owner_stats.setdefault(
                    owner,
                    {
                        'owner': owner,
                        'open_action_items': 0,
                        'overdue_open_items': 0,
                        'open_escalations': 0,
                    },
                )
                stats['open_action_items'] = int(stats['open_action_items']) + 1
                if due_at < now:
                    stats['overdue_open_items'] = int(stats['overdue_open_items']) + 1
                action_item_owner[(postmortem_id, int(action_item.get('id', 0)))] = owner

        for escalation in tenant_escalations:
            if str(escalation.get('status', 'open')).lower() != 'open':
                continue
            owner = action_item_owner.get((int(escalation.get('postmortem_id', 0)), int(escalation.get('action_item_id', 0))), 'unassigned')
            stats = owner_stats.setdefault(
                owner,
                {
                    'owner': owner,
                    'open_action_items': 0,
                    'overdue_open_items': 0,
                    'open_escalations': 0,
                },
            )
            stats['open_escalations'] = int(stats['open_escalations']) + 1

        hotspots: list[dict[str, Any]] = []
        for stats in owner_stats.values():
            open_items = int(stats.get('open_action_items', 0))
            overdue_items = int(stats.get('overdue_open_items', 0))
            open_escalations = int(stats.get('open_escalations', 0))
            overloaded = open_items > max_open_items_per_owner
            overdue_breached = overdue_items > max_overdue_items_per_owner
            if not overloaded and not overdue_breached and open_escalations == 0:
                continue
            severity = 'critical' if (overdue_breached or open_escalations >= 2) else 'high'
            hotspots.append(
                {
                    **stats,
                    'over_capacity': overloaded,
                    'overdue_threshold_breached': overdue_breached,
                    'severity': severity,
                }
            )

        hotspots.sort(
            key=lambda item: (
                0 if str(item.get('severity')) == 'critical' else 1,
                -(int(item.get('overdue_open_items', 0)) + int(item.get('open_escalations', 0))),
                -int(item.get('open_action_items', 0)),
            )
        )
        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'max_overdue_items_per_owner': max_overdue_items_per_owner,
            'hotspots': hotspots,
            'count': len(hotspots),
        }

    @router.get('/workflow-connectors/postmortems/action-items/surge-alerts', summary='Owner surge alerts for escalating workload')
    def get_postmortem_action_item_surge_alerts(
        auth: AuthDep,
        lookback_hours: Annotated[int, Query(ge=1, le=720)] = 24,
        min_new_open_escalations: Annotated[int, Query(ge=1, le=50)] = 1,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:surge-alerts:get', 120, 60)
        now = datetime.now(UTC)
        lookback_start = now - timedelta(hours=lookback_hours)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and _parse_iso(item.get('created_at')) >= lookback_start
            ]

        action_item_owner: dict[tuple[int, int], str] = {}
        action_item_due: dict[tuple[int, int], datetime] = {}
        for postmortem in tenant_postmortems:
            postmortem_id = int(postmortem.get('id', 0))
            for action_item in (postmortem.get('action_items_detailed') or []):
                item_id = int(action_item.get('id', 0))
                action_item_owner[(postmortem_id, item_id)] = str(action_item.get('owner', '')).strip() or 'unassigned'
                action_item_due[(postmortem_id, item_id)] = _parse_iso(action_item.get('due_at'))

        owner_alerts: dict[str, dict[str, Any]] = {}
        for escalation in escalations:
            if str(escalation.get('status', 'open')).lower() != 'open':
                continue
            key = (int(escalation.get('postmortem_id', 0)), int(escalation.get('action_item_id', 0)))
            owner = action_item_owner.get(key, 'unassigned')
            alert = owner_alerts.setdefault(
                owner,
                {
                    'owner': owner,
                    'new_open_escalations': 0,
                    'new_critical_escalations': 0,
                    'new_overdue_items': 0,
                    'lookback_hours': lookback_hours,
                },
            )
            alert['new_open_escalations'] = int(alert['new_open_escalations']) + 1
            if str(escalation.get('severity', '')).lower() == 'critical':
                alert['new_critical_escalations'] = int(alert['new_critical_escalations']) + 1
            due_at = action_item_due.get(key)
            if due_at is not None and due_at < now:
                alert['new_overdue_items'] = int(alert['new_overdue_items']) + 1

        alerts: list[dict[str, Any]] = []
        for alert in owner_alerts.values():
            if int(alert.get('new_open_escalations', 0)) < min_new_open_escalations:
                continue
            critical = int(alert.get('new_critical_escalations', 0))
            if critical >= 1:
                severity = 'critical'
            elif int(alert.get('new_open_escalations', 0)) >= 2:
                severity = 'high'
            else:
                severity = 'medium'
            alerts.append({**alert, 'severity': severity})

        alerts.sort(
            key=lambda item: (
                0 if str(item.get('severity')) == 'critical' else (1 if str(item.get('severity')) == 'high' else 2),
                -int(item.get('new_open_escalations', 0)),
            )
        )
        return {
            'status': 'ok',
            'lookback_hours': lookback_hours,
            'min_new_open_escalations': min_new_open_escalations,
            'alerts': alerts,
            'count': len(alerts),
        }

    @router.get('/workflow-connectors/postmortems/action-items/balance-index', summary='Balance index for owner action-item distribution')
    def get_postmortem_action_item_balance_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:balance-index:get', 120, 60)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            tenant_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_counts: dict[str, int] = {}
        total_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_counts[owner] = int(owner_open_counts.get(owner, 0)) + 1
                total_open_items += 1

        owner_counts_sorted = sorted(owner_open_counts.values(), reverse=True)
        top_owner_count = owner_counts_sorted[0] if owner_counts_sorted else 0
        top_two_count = sum(owner_counts_sorted[:2]) if owner_counts_sorted else 0
        max_owner_share_pct = round((top_owner_count / total_open_items) * 100, 2) if total_open_items else 0.0
        top_two_share_pct = round((top_two_count / total_open_items) * 100, 2) if total_open_items else 0.0
        overloaded_owner_count = len([count for count in owner_counts_sorted if count > max_open_items_per_owner])
        balance_index = round(max(0.0, 100.0 - max_owner_share_pct), 2)
        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'total_open_action_items': total_open_items,
            'owners_with_open_items': len(owner_open_counts),
            'open_escalations': len(tenant_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'max_owner_share_pct': max_owner_share_pct,
            'top_two_owner_share_pct': top_two_share_pct,
            'balance_index': balance_index,
        }

    @router.get('/workflow-connectors/postmortems/action-items/coverage-gaps', summary='Coverage gaps in action-item ownership and capacity')
    def get_postmortem_action_item_coverage_gaps(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:coverage-gaps:get', 120, 60)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]

        owner_open_counts: dict[str, int] = {}
        total_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_counts[owner] = int(owner_open_counts.get(owner, 0)) + 1
                total_open_items += 1

        unassigned_open_items = int(owner_open_counts.get('unassigned', 0))
        overloaded_owners = [
            {'owner': owner, 'open_action_items': count}
            for owner, count in owner_open_counts.items()
            if owner != 'unassigned' and count > max_open_items_per_owner
        ]
        overload_count = len(overloaded_owners)
        max_owner_share_pct = round((max(owner_open_counts.values()) / total_open_items) * 100, 2) if total_open_items else 0.0

        gaps: list[dict[str, Any]] = []
        if unassigned_open_items > 0:
            gaps.append(
                {
                    'code': 'unassigned_items',
                    'severity': 'high' if unassigned_open_items >= 2 else 'medium',
                    'count': unassigned_open_items,
                    'message': 'Open action items are unassigned.',
                }
            )
        if overload_count > 0:
            gaps.append(
                {
                    'code': 'overloaded_owner',
                    'severity': 'high' if overload_count >= 2 else 'medium',
                    'count': overload_count,
                    'message': 'One or more owners exceed open-item capacity threshold.',
                }
            )
        if max_owner_share_pct >= 70.0 and total_open_items >= 3:
            gaps.append(
                {
                    'code': 'single_owner_concentration',
                    'severity': 'high',
                    'count': 1,
                    'message': 'A single owner carries most open action items.',
                }
            )

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'total_open_action_items': total_open_items,
            'unassigned_open_items': unassigned_open_items,
            'overloaded_owners': overloaded_owners,
            'max_owner_share_pct': max_owner_share_pct,
            'gaps': gaps,
            'count': len(gaps),
        }

    @router.get('/workflow-connectors/postmortems/action-items/handoff-readiness', summary='Owner handoff readiness for active incident action items')
    def get_postmortem_action_item_handoff_readiness(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
        critical_open_escalations_threshold: Annotated[int, Query(ge=1, le=20)] = 1,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:handoff-readiness:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            tenant_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id
            ]

        owner_stats: dict[str, dict[str, Any]] = {}
        action_item_owner: dict[tuple[int, int], str] = {}
        for postmortem in tenant_postmortems:
            postmortem_id = int(postmortem.get('id', 0))
            for action_item in (postmortem.get('action_items_detailed') or []):
                status = str(action_item.get('status', 'open')).lower()
                if status == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                stats = owner_stats.setdefault(
                    owner,
                    {
                        'owner': owner,
                        'open_action_items': 0,
                        'overdue_open_items': 0,
                        'open_escalations': 0,
                        'critical_open_escalations': 0,
                        'acknowledged_escalations': 0,
                    },
                )
                stats['open_action_items'] = int(stats['open_action_items']) + 1
                if _parse_iso(action_item.get('due_at')) < now:
                    stats['overdue_open_items'] = int(stats['overdue_open_items']) + 1
                action_item_owner[(postmortem_id, int(action_item.get('id', 0)))] = owner

        for escalation in tenant_escalations:
            owner = action_item_owner.get((int(escalation.get('postmortem_id', 0)), int(escalation.get('action_item_id', 0))), 'unassigned')
            stats = owner_stats.setdefault(
                owner,
                {
                    'owner': owner,
                    'open_action_items': 0,
                    'overdue_open_items': 0,
                    'open_escalations': 0,
                    'critical_open_escalations': 0,
                    'acknowledged_escalations': 0,
                },
            )
            escalation_status = str(escalation.get('status', 'open')).lower()
            if escalation_status == 'open':
                stats['open_escalations'] = int(stats['open_escalations']) + 1
                if str(escalation.get('severity', '')).lower() == 'critical':
                    stats['critical_open_escalations'] = int(stats['critical_open_escalations']) + 1
            elif escalation_status == 'acknowledged':
                stats['acknowledged_escalations'] = int(stats['acknowledged_escalations']) + 1

        readiness: list[dict[str, Any]] = []
        for stats in owner_stats.values():
            open_items = int(stats.get('open_action_items', 0))
            overdue_items = int(stats.get('overdue_open_items', 0))
            critical_open_escalations = int(stats.get('critical_open_escalations', 0))
            open_escalations = int(stats.get('open_escalations', 0))
            if critical_open_escalations >= critical_open_escalations_threshold:
                readiness_status = 'blocked'
            elif open_items > max_open_items_per_owner or overdue_items > 0 or open_escalations > 0:
                readiness_status = 'at_risk'
            else:
                readiness_status = 'ready'
            handoff_score = max(
                0,
                100
                - open_items * 12
                - overdue_items * 15
                - open_escalations * 20
                - critical_open_escalations * 25,
            )
            readiness.append(
                {
                    **stats,
                    'handoff_readiness_status': readiness_status,
                    'handoff_readiness_score': handoff_score,
                    'backup_recommended': readiness_status != 'ready',
                }
            )

        readiness.sort(
            key=lambda item: (
                0 if str(item.get('handoff_readiness_status')) == 'blocked' else (1 if str(item.get('handoff_readiness_status')) == 'at_risk' else 2),
                int(item.get('handoff_readiness_score', 0)),
            )
        )
        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'critical_open_escalations_threshold': critical_open_escalations_threshold,
            'owners': readiness,
            'count': len(readiness),
        }

    @router.get('/workflow-connectors/postmortems/action-items/continuity-risks', summary='Continuity risks for owner concentration on active incident work')
    def get_postmortem_action_item_continuity_risks(
        auth: AuthDep,
        min_single_owner_items: Annotated[int, Query(ge=1, le=100)] = 2,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:continuity-risks:get', 120, 60)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            tenant_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        connector_owner_counts: dict[int, dict[str, int]] = {}
        connector_totals: dict[int, int] = {}
        action_item_owner: dict[tuple[int, int], str] = {}
        postmortem_connector: dict[int, int] = {}
        for postmortem in tenant_postmortems:
            postmortem_id = int(postmortem.get('id', 0))
            connector_id = int(postmortem.get('connector_id', 0))
            postmortem_connector[postmortem_id] = connector_id
            owner_counts = connector_owner_counts.setdefault(connector_id, {})
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_counts[owner] = int(owner_counts.get(owner, 0)) + 1
                connector_totals[connector_id] = int(connector_totals.get(connector_id, 0)) + 1
                action_item_owner[(postmortem_id, int(action_item.get('id', 0)))] = owner

        owner_open_escalations: dict[str, int] = {}
        for escalation in tenant_escalations:
            owner = action_item_owner.get((int(escalation.get('postmortem_id', 0)), int(escalation.get('action_item_id', 0))), 'unassigned')
            owner_open_escalations[owner] = int(owner_open_escalations.get(owner, 0)) + 1

        risks: list[dict[str, Any]] = []
        for connector_id, owner_counts in connector_owner_counts.items():
            total = int(connector_totals.get(connector_id, 0))
            if total <= 0:
                continue
            dominant_owner, dominant_count = max(owner_counts.items(), key=lambda item: int(item[1]))
            dominant_share = round((int(dominant_count) / total) * 100, 2)
            if int(dominant_count) >= min_single_owner_items and dominant_share >= 70.0:
                severity = 'critical' if dominant_share >= 85.0 else 'high'
                risks.append(
                    {
                        'code': 'single_owner_connector_dependency',
                        'severity': severity,
                        'connector_id': connector_id,
                        'owner': dominant_owner,
                        'owner_open_items': int(dominant_count),
                        'owner_share_pct': dominant_share,
                        'message': 'Connector incident actions are heavily concentrated on one owner.',
                    }
                )

        for owner, open_escalations in owner_open_escalations.items():
            if open_escalations < 2:
                continue
            risks.append(
                {
                    'code': 'escalation_concentration',
                    'severity': 'high' if open_escalations < 4 else 'critical',
                    'owner': owner,
                    'open_escalations': int(open_escalations),
                    'message': 'Owner has concentrated open escalations requiring continuity planning.',
                }
            )

        risks.sort(
            key=lambda item: (
                0 if str(item.get('severity')) == 'critical' else 1,
                -int(item.get('owner_open_items', item.get('open_escalations', 0))),
            )
        )
        return {
            'status': 'ok',
            'min_single_owner_items': min_single_owner_items,
            'risks': risks,
            'count': len(risks),
        }

    @router.get('/workflow-connectors/postmortems/action-items/ownership-churn', summary='Ownership churn indicators for active connector incident work')
    def get_postmortem_action_item_ownership_churn(
        auth: AuthDep,
        min_owner_switch_risk_items: Annotated[int, Query(ge=1, le=100)] = 2,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:ownership-churn:get', 120, 60)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            tenant_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() in {'open', 'acknowledged'}
            ]

        connector_owner_counts: dict[int, dict[str, int]] = {}
        connector_open_item_totals: dict[int, int] = {}
        action_item_owner: dict[tuple[int, int], str] = {}
        postmortem_connector: dict[int, int] = {}

        for postmortem in tenant_postmortems:
            connector_id = int(postmortem.get('connector_id', 0))
            postmortem_id = int(postmortem.get('id', 0))
            postmortem_connector[postmortem_id] = connector_id
            owner_counts = connector_owner_counts.setdefault(connector_id, {})
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_counts[owner] = int(owner_counts.get(owner, 0)) + 1
                connector_open_item_totals[connector_id] = int(connector_open_item_totals.get(connector_id, 0)) + 1
                action_item_owner[(postmortem_id, int(action_item.get('id', 0)))] = owner

        connector_open_escalation_owners: dict[int, set[str]] = {}
        for escalation in tenant_escalations:
            postmortem_id = int(escalation.get('postmortem_id', 0))
            connector_id = int(postmortem_connector.get(postmortem_id, 0))
            owner = action_item_owner.get((postmortem_id, int(escalation.get('action_item_id', 0))), 'unassigned')
            connector_open_escalation_owners.setdefault(connector_id, set()).add(owner)

        churn_rows: list[dict[str, Any]] = []
        for connector_id, owner_counts in connector_owner_counts.items():
            total_items = int(connector_open_item_totals.get(connector_id, 0))
            if total_items <= 0:
                continue
            distinct_owners = len(owner_counts)
            unassigned_items = int(owner_counts.get('unassigned', 0))
            top_owner_count = max(owner_counts.values()) if owner_counts else 0
            top_owner_share_pct = round((int(top_owner_count) / total_items) * 100, 2)
            escalation_owners = connector_open_escalation_owners.get(connector_id, set())

            owner_switch_risk_items = sum(1 for count in owner_counts.values() if int(count) == 1)
            churn_index = round(
                min(
                    100.0,
                    distinct_owners * 12
                    + len(escalation_owners) * 14
                    + unassigned_items * 18
                    + (40.0 if 35.0 <= top_owner_share_pct <= 75.0 else 0.0),
                ),
                2,
            )

            if churn_index >= 70.0:
                severity = 'high'
            elif churn_index >= 40.0:
                severity = 'medium'
            else:
                severity = 'low'

            churn_rows.append(
                {
                    'connector_id': connector_id,
                    'open_action_items': total_items,
                    'distinct_active_owners': distinct_owners,
                    'unassigned_open_items': unassigned_items,
                    'top_owner_share_pct': top_owner_share_pct,
                    'open_escalation_owners': len(escalation_owners),
                    'owner_switch_risk_items': owner_switch_risk_items,
                    'churn_index': churn_index,
                    'severity': severity,
                    'needs_assignment_normalization': owner_switch_risk_items >= min_owner_switch_risk_items,
                }
            )

        churn_rows.sort(key=lambda item: float(item.get('churn_index', 0.0)), reverse=True)
        return {
            'status': 'ok',
            'min_owner_switch_risk_items': min_owner_switch_risk_items,
            'connectors': churn_rows,
            'count': len(churn_rows),
        }

    @router.get('/workflow-connectors/postmortems/action-items/stability-score', summary='Ownership stability score for active incident operations')
    def get_postmortem_action_item_stability_score(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:stability-score:get', 120, 60)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            tenant_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        action_item_owner: dict[tuple[int, int], str] = {}
        for postmortem in tenant_postmortems:
            postmortem_id = int(postmortem.get('id', 0))
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                action_item_owner[(postmortem_id, int(action_item.get('id', 0)))] = owner

        owner_open_escalations: dict[str, int] = {}
        for escalation in tenant_escalations:
            owner = action_item_owner.get((int(escalation.get('postmortem_id', 0)), int(escalation.get('action_item_id', 0))), 'unassigned')
            owner_open_escalations[owner] = int(owner_open_escalations.get(owner, 0)) + 1

        total_open_items = sum(owner_open_items.values())
        unassigned_items = int(owner_open_items.get('unassigned', 0))
        overloaded_owners = [
            owner for owner, count in owner_open_items.items()
            if owner != 'unassigned' and int(count) > max_open_items_per_owner
        ]
        escalation_concentration = len([owner for owner, count in owner_open_escalations.items() if int(count) >= 2])
        top_owner_share_pct = round((max(owner_open_items.values()) / total_open_items) * 100, 2) if total_open_items else 0.0

        score = 100.0
        score -= unassigned_items * 10
        score -= len(overloaded_owners) * 12
        score -= escalation_concentration * 14
        if top_owner_share_pct >= 80.0:
            score -= 20
        elif top_owner_share_pct >= 65.0:
            score -= 10
        stability_score = round(max(0.0, score), 2)

        if stability_score >= 80:
            stability_band = 'stable'
        elif stability_score >= 50:
            stability_band = 'watch'
        else:
            stability_band = 'unstable'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'stability_score': stability_score,
            'stability_band': stability_band,
            'total_open_action_items': total_open_items,
            'unassigned_open_items': unassigned_items,
            'overloaded_owner_count': len(overloaded_owners),
            'escalation_concentration_count': escalation_concentration,
            'top_owner_share_pct': top_owner_share_pct,
        }

    @router.get('/workflow-connectors/postmortems/action-items/handoff-plan', summary='Handoff plan recommendations for active owner risk')
    def get_postmortem_action_item_handoff_plan(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:handoff-plan:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            tenant_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() in {'open', 'acknowledged'}
            ]

        owner_stats: dict[str, dict[str, Any]] = {}
        action_item_owner: dict[tuple[int, int], str] = {}
        for postmortem in tenant_postmortems:
            postmortem_id = int(postmortem.get('id', 0))
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                stats = owner_stats.setdefault(
                    owner,
                    {
                        'owner': owner,
                        'open_action_items': 0,
                        'overdue_open_items': 0,
                        'open_escalations': 0,
                        'critical_open_escalations': 0,
                    },
                )
                stats['open_action_items'] = int(stats['open_action_items']) + 1
                if _parse_iso(action_item.get('due_at')) < now:
                    stats['overdue_open_items'] = int(stats['overdue_open_items']) + 1
                action_item_owner[(postmortem_id, int(action_item.get('id', 0)))] = owner

        for escalation in tenant_escalations:
            owner = action_item_owner.get((int(escalation.get('postmortem_id', 0)), int(escalation.get('action_item_id', 0))), 'unassigned')
            stats = owner_stats.setdefault(
                owner,
                {
                    'owner': owner,
                    'open_action_items': 0,
                    'overdue_open_items': 0,
                    'open_escalations': 0,
                    'critical_open_escalations': 0,
                },
            )
            if str(escalation.get('status', 'open')).lower() == 'open':
                stats['open_escalations'] = int(stats['open_escalations']) + 1
                if str(escalation.get('severity', '')).lower() == 'critical':
                    stats['critical_open_escalations'] = int(stats['critical_open_escalations']) + 1

        plans: list[dict[str, Any]] = []
        for stats in owner_stats.values():
            owner = str(stats.get('owner', 'unassigned'))
            open_items = int(stats.get('open_action_items', 0))
            overdue_items = int(stats.get('overdue_open_items', 0))
            open_escalations = int(stats.get('open_escalations', 0))
            critical_open = int(stats.get('critical_open_escalations', 0))
            if owner == 'unassigned':
                continue
            if open_items <= max_open_items_per_owner and overdue_items == 0 and open_escalations == 0:
                continue

            if critical_open > 0:
                priority = 'critical'
            elif overdue_items > 0 or open_escalations >= 2:
                priority = 'high'
            else:
                priority = 'medium'

            backup_slots = max(1, (open_items - max_open_items_per_owner) if open_items > max_open_items_per_owner else 1)
            recommendations: list[str] = []
            if open_items > max_open_items_per_owner:
                recommendations.append('Reassign low-context action items to backup owner.')
            if overdue_items > 0:
                recommendations.append('Transfer overdue items to secondary responder.')
            if open_escalations > 0:
                recommendations.append('Assign co-owner for active escalations.')
            if not recommendations:
                recommendations.append('Add documented backup owner for continuity.')

            plans.append(
                {
                    'owner': owner,
                    'priority': priority,
                    'backup_owner_slots_needed': backup_slots,
                    'open_action_items': open_items,
                    'overdue_open_items': overdue_items,
                    'open_escalations': open_escalations,
                    'critical_open_escalations': critical_open,
                    'recommendations': recommendations,
                }
            )

        plans.sort(
            key=lambda item: (
                0 if str(item.get('priority')) == 'critical' else (1 if str(item.get('priority')) == 'high' else 2),
                -int(item.get('open_action_items', 0)),
            )
        )
        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'plans': plans,
            'count': len(plans),
        }

    @router.get('/workflow-connectors/postmortems/action-items/resilience-snapshot', summary='Operational resilience snapshot for active action-item governance')
    def get_postmortem_action_item_resilience_snapshot(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:resilience-snapshot:get', 120, 60)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )
        top_owner_share_pct = round((max(owner_open_items.values()) / total_open_items) * 100, 2) if total_open_items else 0.0

        resilience_score = 100.0
        resilience_score -= unassigned_open_items * 12
        resilience_score -= overloaded_owner_count * 10
        resilience_score -= len(open_escalations) * 8
        if top_owner_share_pct >= 80.0:
            resilience_score -= 18
        elif top_owner_share_pct >= 65.0:
            resilience_score -= 9
        resilience_score = round(max(0.0, resilience_score), 2)

        if resilience_score >= 80:
            resilience_band = 'strong'
        elif resilience_score >= 55:
            resilience_band = 'watch'
        else:
            resilience_band = 'fragile'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'resilience_score': resilience_score,
            'resilience_band': resilience_band,
            'total_open_action_items': total_open_items,
            'open_escalations': len(open_escalations),
            'unassigned_open_items': unassigned_open_items,
            'overloaded_owner_count': overloaded_owner_count,
            'top_owner_share_pct': top_owner_share_pct,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-queue', summary='Prioritized remediation queue for ownership resilience actions')
    def get_postmortem_action_item_remediation_queue(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-queue:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            tenant_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_stats: dict[str, dict[str, Any]] = {}
        action_item_owner: dict[tuple[int, int], str] = {}
        for postmortem in tenant_postmortems:
            postmortem_id = int(postmortem.get('id', 0))
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                stats = owner_stats.setdefault(
                    owner,
                    {
                        'open_action_items': 0,
                        'overdue_open_items': 0,
                        'open_escalations': 0,
                    },
                )
                stats['open_action_items'] = int(stats['open_action_items']) + 1
                if _parse_iso(action_item.get('due_at')) < now:
                    stats['overdue_open_items'] = int(stats['overdue_open_items']) + 1
                action_item_owner[(postmortem_id, int(action_item.get('id', 0)))] = owner

        for escalation in tenant_escalations:
            owner = action_item_owner.get((int(escalation.get('postmortem_id', 0)), int(escalation.get('action_item_id', 0))), 'unassigned')
            stats = owner_stats.setdefault(owner, {'open_action_items': 0, 'overdue_open_items': 0, 'open_escalations': 0})
            stats['open_escalations'] = int(stats['open_escalations']) + 1

        queue: list[dict[str, Any]] = []
        for owner, stats in owner_stats.items():
            open_items = int(stats.get('open_action_items', 0))
            overdue_items = int(stats.get('overdue_open_items', 0))
            open_escalations = int(stats.get('open_escalations', 0))
            if owner != 'unassigned' and open_items <= max_open_items_per_owner and overdue_items == 0 and open_escalations == 0:
                continue

            priority_score = (
                overdue_items * 100
                + open_escalations * 80
                + max(0, open_items - max_open_items_per_owner) * 60
                + (120 if owner == 'unassigned' else 0)
            )

            if owner == 'unassigned':
                action = 'assign_owner'
                reason = 'Open action items have no owner.'
            elif overdue_items > 0:
                action = 'reassign_overdue'
                reason = 'Owner has overdue open action items.'
            elif open_escalations > 0:
                action = 'add_co_owner'
                reason = 'Owner has active escalations requiring backup.'
            else:
                action = 'rebalance_load'
                reason = 'Owner exceeds configured open-item capacity.'

            queue.append(
                {
                    'owner': owner,
                    'action': action,
                    'reason': reason,
                    'priority_score': priority_score,
                    'open_action_items': open_items,
                    'overdue_open_items': overdue_items,
                    'open_escalations': open_escalations,
                }
            )

        queue.sort(key=lambda item: int(item.get('priority_score', 0)), reverse=True)
        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'queue': queue[:limit],
            'count': min(len(queue), limit),
            'total_candidates': len(queue),
        }

    @router.get('/workflow-connectors/postmortems/action-items/readiness-forecast', summary='Readiness forecast based on current ownership and escalation pressure')
    def get_postmortem_action_item_readiness_forecast(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:readiness-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )
        top_owner_share_pct = round((max(owner_open_items.values()) / total_open_items) * 100, 2) if total_open_items else 0.0

        readiness_forecast_score = 100.0
        readiness_forecast_score -= overdue_open_items * 10
        readiness_forecast_score -= due_within_24h * 4
        readiness_forecast_score -= unassigned_open_items * 12
        readiness_forecast_score -= len(open_escalations) * 7
        readiness_forecast_score -= overloaded_owner_count * 9
        if top_owner_share_pct >= 80.0:
            readiness_forecast_score -= 15
        elif top_owner_share_pct >= 65.0:
            readiness_forecast_score -= 8
        readiness_forecast_score = round(max(0.0, readiness_forecast_score), 2)

        if readiness_forecast_score >= 80:
            forecast_band = 'ready'
        elif readiness_forecast_score >= 55:
            forecast_band = 'watch'
        else:
            forecast_band = 'risk'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'readiness_forecast_score': readiness_forecast_score,
            'forecast_band': forecast_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-throughput', summary='Daily remediation throughput required to stabilize action-item risk')
    def get_postmortem_action_item_remediation_throughput(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-throughput:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )

        risk_load_units = (
            total_open_items
            + (overdue_open_items * 2)
            + (len(open_escalations) * 3)
            + (unassigned_open_items * 2)
            + (overloaded_owner_count * 2)
        )
        required_daily_remediations = (risk_load_units + days_horizon - 1) // days_horizon if risk_load_units > 0 else 0

        if required_daily_remediations <= 2:
            throughput_band = 'sustainable'
        elif required_daily_remediations <= 5:
            throughput_band = 'stretched'
        else:
            throughput_band = 'critical'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'days_horizon': days_horizon,
            'required_daily_remediations': required_daily_remediations,
            'throughput_band': throughput_band,
            'risk_load_units': risk_load_units,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
        }

    @router.get('/workflow-connectors/postmortems/action-items/risk-burndown', summary='Risk burndown targets for postmortem action-item governance')
    def get_postmortem_action_item_risk_burndown(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:risk-burndown:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_items += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    overdue_open_items += 1
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                if owner == 'unassigned':
                    unassigned_open_items += 1

        critical_backlog = overdue_open_items + len(open_escalations)
        high_backlog = max(0, open_items - critical_backlog)

        recommended_daily_critical_closures = (critical_backlog + days_horizon - 1) // days_horizon if critical_backlog > 0 else 0
        recommended_daily_high_closures = (high_backlog + days_horizon - 1) // days_horizon if high_backlog > 0 else 0
        recommended_daily_owner_assignments = (unassigned_open_items + days_horizon - 1) // days_horizon if unassigned_open_items > 0 else 0

        risk_burndown_index = 100.0
        risk_burndown_index -= critical_backlog * 12
        risk_burndown_index -= high_backlog * 4
        risk_burndown_index -= unassigned_open_items * 10
        risk_burndown_index = round(max(0.0, risk_burndown_index), 2)

        if risk_burndown_index >= 80:
            burndown_band = 'on-track'
        elif risk_burndown_index >= 55:
            burndown_band = 'needs-focus'
        else:
            burndown_band = 'off-track'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'risk_burndown_index': risk_burndown_index,
            'burndown_band': burndown_band,
            'recommended_daily_critical_closures': recommended_daily_critical_closures,
            'recommended_daily_high_closures': recommended_daily_high_closures,
            'recommended_daily_owner_assignments': recommended_daily_owner_assignments,
            'critical_backlog': critical_backlog,
            'high_backlog': high_backlog,
            'unassigned_open_items': unassigned_open_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/capacity-scenarios', summary='Capacity planning scenarios for action-item remediation')
    def get_postmortem_action_item_capacity_scenarios(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:capacity-scenarios:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    overdue_open_items += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )
        risk_load_units = (
            total_open_items
            + (overdue_open_items * 2)
            + (len(open_escalations) * 3)
            + (unassigned_open_items * 2)
            + (overloaded_owner_count * 2)
        )

        scenarios = [
            {'name': 'stabilize', 'risk_units_per_day': 1.0},
            {'name': 'accelerate', 'risk_units_per_day': 1.35},
            {'name': 'constrained', 'risk_units_per_day': 0.75},
        ]
        scenario_rows: list[dict[str, Any]] = []
        for scenario in scenarios:
            units_per_day = float(scenario['risk_units_per_day'])
            required_daily_actions = int((risk_load_units / max(units_per_day, 0.1) + days_horizon - 1) // days_horizon) if risk_load_units > 0 else 0
            if required_daily_actions <= 2:
                capacity_band = 'comfortable'
            elif required_daily_actions <= 5:
                capacity_band = 'tight'
            else:
                capacity_band = 'overloaded'
            scenario_rows.append(
                {
                    'scenario': scenario['name'],
                    'required_daily_actions': required_daily_actions,
                    'capacity_band': capacity_band,
                }
            )

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'max_open_items_per_owner': max_open_items_per_owner,
            'risk_load_units': risk_load_units,
            'scenarios': scenario_rows,
            'count': len(scenario_rows),
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-sla', summary='Remediation SLA adherence score for open action-item backlog')
    def get_postmortem_action_item_remediation_sla(
        auth: AuthDep,
        sla_hours: Annotated[int, Query(ge=1, le=168)] = 24,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-sla:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        total_open_items = 0
        within_sla_count = 0
        overdue_count = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                hours_to_due = (due_at - now).total_seconds() / 3600
                if hours_to_due >= 0:
                    within_sla_count += 1
                else:
                    overdue_count += 1

        sla_adherence_pct = round((within_sla_count / total_open_items) * 100, 2) if total_open_items else 100.0
        remediation_sla_score = round(max(0.0, sla_adherence_pct - (len(open_escalations) * 4)), 2)
        if remediation_sla_score >= 85:
            sla_band = 'healthy'
        elif remediation_sla_score >= 60:
            sla_band = 'watch'
        else:
            sla_band = 'breach'

        return {
            'status': 'ok',
            'sla_hours': sla_hours,
            'remediation_sla_score': remediation_sla_score,
            'sla_band': sla_band,
            'sla_adherence_pct': sla_adherence_pct,
            'total_open_action_items': total_open_items,
            'within_sla_count': within_sla_count,
            'overdue_count': overdue_count,
            'open_escalations': len(open_escalations),
        }

    @router.get('/workflow-connectors/postmortems/action-items/owner-relief-plan', summary='Owner relief plan to reduce overloaded action-item queues')
    def get_postmortem_action_item_owner_relief_plan(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:owner-relief-plan:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_stats: dict[str, dict[str, int]] = {}
        action_item_owner: dict[tuple[int, int], str] = {}
        for postmortem in tenant_postmortems:
            postmortem_id = int(postmortem.get('id', 0))
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                stats = owner_stats.setdefault(owner, {'open_action_items': 0, 'overdue_open_items': 0, 'open_escalations': 0})
                stats['open_action_items'] += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    stats['overdue_open_items'] += 1
                action_item_owner[(postmortem_id, int(action_item.get('id', 0)))] = owner

        for escalation in open_escalations:
            owner = action_item_owner.get((int(escalation.get('postmortem_id', 0)), int(escalation.get('action_item_id', 0))), 'unassigned')
            stats = owner_stats.setdefault(owner, {'open_action_items': 0, 'overdue_open_items': 0, 'open_escalations': 0})
            stats['open_escalations'] += 1

        plans: list[dict[str, Any]] = []
        for owner, stats in owner_stats.items():
            open_items = int(stats.get('open_action_items', 0))
            overdue_items = int(stats.get('overdue_open_items', 0))
            open_escalation_count = int(stats.get('open_escalations', 0))
            overload = max(0, open_items - max_open_items_per_owner)
            if owner != 'unassigned' and overload == 0 and overdue_items == 0 and open_escalation_count == 0:
                continue

            relief_actions = overload + overdue_items + open_escalation_count
            if owner == 'unassigned':
                priority = 'critical'
                recommendation = 'Assign owner to unassigned action items and add backup coverage.'
            elif overdue_items > 0 or open_escalation_count > 0:
                priority = 'high'
                recommendation = 'Shift overdue and escalated items to secondary responders.'
            elif overload > 0:
                priority = 'medium'
                recommendation = 'Rebalance low-context tasks across available owners.'
            else:
                priority = 'low'
                recommendation = 'Document fallback owner for continuity.'

            plans.append(
                {
                    'owner': owner,
                    'priority': priority,
                    'recommended_relief_actions': max(1, relief_actions),
                    'open_action_items': open_items,
                    'overdue_open_items': overdue_items,
                    'open_escalations': open_escalation_count,
                    'recommendation': recommendation,
                }
            )

        plans.sort(
            key=lambda item: (
                0 if str(item.get('priority')) == 'critical' else (1 if str(item.get('priority')) == 'high' else (2 if str(item.get('priority')) == 'medium' else 3)),
                -int(item.get('recommended_relief_actions', 0)),
            )
        )
        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'plans': plans,
            'count': len(plans),
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-clearance-eta', summary='Estimated days to clear current escalation backlog')
    def get_postmortem_action_item_escalation_clearance_eta(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-clearance-eta:get', 120, 60)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        now = datetime.now(UTC)
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    overdue_open_items += 1

        clearance_load = len(open_escalations) + overdue_open_items
        if clearance_load <= 0:
            clearance_eta_days = 0
        else:
            daily_capacity = max(1, (open_action_items // max(1, days_horizon)) + 1)
            clearance_eta_days = (clearance_load + daily_capacity - 1) // daily_capacity

        if clearance_eta_days <= 1:
            eta_band = 'immediate'
        elif clearance_eta_days <= days_horizon:
            eta_band = 'manageable'
        else:
            eta_band = 'backlog-risk'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'clearance_eta_days': clearance_eta_days,
            'eta_band': eta_band,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'clearance_load': clearance_load,
        }

    @router.get('/workflow-connectors/postmortems/action-items/mitigation-readiness', summary='Mitigation readiness score for active action-item backlog')
    def get_postmortem_action_item_mitigation_readiness(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:mitigation-readiness:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    overdue_open_items += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )

        mitigation_readiness_score = 100.0
        mitigation_readiness_score -= overdue_open_items * 9
        mitigation_readiness_score -= unassigned_open_items * 12
        mitigation_readiness_score -= len(open_escalations) * 8
        mitigation_readiness_score -= overloaded_owner_count * 7
        mitigation_readiness_score = round(max(0.0, mitigation_readiness_score), 2)

        if mitigation_readiness_score >= 80:
            readiness_band = 'ready'
        elif mitigation_readiness_score >= 55:
            readiness_band = 'watch'
        else:
            readiness_band = 'at-risk'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'mitigation_readiness_score': mitigation_readiness_score,
            'readiness_band': readiness_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
        }

    @router.get('/workflow-connectors/postmortems/action-items/owner-coverage-forecast', summary='Owner coverage forecast for near-term remediation continuity')
    def get_postmortem_action_item_owner_coverage_forecast(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:owner-coverage-forecast:get', 120, 60)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        active_named_owners = len([owner for owner in owner_open_items if owner != 'unassigned'])
        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )
        top_owner_share_pct = round((max(owner_open_items.values()) / total_open_items) * 100, 2) if total_open_items else 0.0

        owner_coverage_score = 100.0
        owner_coverage_score -= unassigned_open_items * 10
        owner_coverage_score -= overloaded_owner_count * 8
        owner_coverage_score -= len(open_escalations) * 6
        if top_owner_share_pct >= 80.0:
            owner_coverage_score -= 14
        elif top_owner_share_pct >= 65.0:
            owner_coverage_score -= 7
        owner_coverage_score = round(max(0.0, owner_coverage_score), 2)

        if owner_coverage_score >= 80:
            coverage_band = 'strong'
        elif owner_coverage_score >= 55:
            coverage_band = 'watch'
        else:
            coverage_band = 'fragile'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'owner_coverage_score': owner_coverage_score,
            'coverage_band': coverage_band,
            'active_named_owners': active_named_owners,
            'total_open_action_items': total_open_items,
            'unassigned_open_items': unassigned_open_items,
            'overloaded_owner_count': overloaded_owner_count,
            'open_escalations': len(open_escalations),
            'top_owner_share_pct': top_owner_share_pct,
        }

    @router.get('/workflow-connectors/postmortems/action-items/handoff-pressure', summary='Handoff pressure score across active action-item ownership lanes')
    def get_postmortem_action_item_handoff_pressure(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:handoff-pressure:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )
        top_owner_share_pct = round((max(owner_open_items.values()) / total_open_items) * 100, 2) if total_open_items else 0.0

        handoff_pressure_score = 100.0
        handoff_pressure_score -= overdue_open_items * 8
        handoff_pressure_score -= due_within_24h * 4
        handoff_pressure_score -= unassigned_open_items * 10
        handoff_pressure_score -= len(open_escalations) * 7
        handoff_pressure_score -= overloaded_owner_count * 6
        if top_owner_share_pct >= 80.0:
            handoff_pressure_score -= 12
        elif top_owner_share_pct >= 65.0:
            handoff_pressure_score -= 6
        handoff_pressure_score = round(max(0.0, handoff_pressure_score), 2)

        if handoff_pressure_score >= 80:
            pressure_band = 'steady'
        elif handoff_pressure_score >= 55:
            pressure_band = 'elevated'
        else:
            pressure_band = 'critical'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'handoff_pressure_score': handoff_pressure_score,
            'pressure_band': pressure_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'top_owner_share_pct': top_owner_share_pct,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-momentum', summary='Remediation momentum score for current action-item backlog dynamics')
    def get_postmortem_action_item_remediation_momentum(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-momentum:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1

        momentum_load = open_action_items + (overdue_open_items * 2) + due_within_24h + (len(open_escalations) * 2)
        target_daily_closures = (momentum_load + days_horizon - 1) // days_horizon if momentum_load > 0 else 0

        remediation_momentum_score = 100.0
        remediation_momentum_score -= overdue_open_items * 9
        remediation_momentum_score -= due_within_24h * 5
        remediation_momentum_score -= len(open_escalations) * 8
        remediation_momentum_score -= target_daily_closures * 3
        remediation_momentum_score = round(max(0.0, remediation_momentum_score), 2)

        if remediation_momentum_score >= 80:
            momentum_band = 'on-track'
        elif remediation_momentum_score >= 55:
            momentum_band = 'watch'
        else:
            momentum_band = 'stalled'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_momentum_score': remediation_momentum_score,
            'momentum_band': momentum_band,
            'target_daily_closures': target_daily_closures,
            'open_action_items': open_action_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'open_escalations': len(open_escalations),
            'momentum_load': momentum_load,
        }

    @router.get('/workflow-connectors/postmortems/action-items/ownership-stability-forecast', summary='Ownership stability forecast for active remediation continuity')
    def get_postmortem_action_item_ownership_stability_forecast(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:ownership-stability-forecast:get', 120, 60)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )
        top_owner_share_pct = round((max(owner_open_items.values()) / total_open_items) * 100, 2) if total_open_items else 0.0
        active_named_owners = len([owner for owner in owner_open_items if owner != 'unassigned'])

        ownership_stability_score = 100.0
        ownership_stability_score -= unassigned_open_items * 10
        ownership_stability_score -= overloaded_owner_count * 8
        ownership_stability_score -= len(open_escalations) * 6
        if top_owner_share_pct >= 80.0:
            ownership_stability_score -= 14
        elif top_owner_share_pct >= 65.0:
            ownership_stability_score -= 7
        if active_named_owners <= 1 and total_open_items > 0:
            ownership_stability_score -= 12
        ownership_stability_score = round(max(0.0, ownership_stability_score), 2)

        if ownership_stability_score >= 80:
            stability_band = 'stable'
        elif ownership_stability_score >= 55:
            stability_band = 'watch'
        else:
            stability_band = 'fragile'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'ownership_stability_score': ownership_stability_score,
            'stability_band': stability_band,
            'active_named_owners': active_named_owners,
            'total_open_action_items': total_open_items,
            'unassigned_open_items': unassigned_open_items,
            'overloaded_owner_count': overloaded_owner_count,
            'open_escalations': len(open_escalations),
            'top_owner_share_pct': top_owner_share_pct,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-burn-rate', summary='Escalation burn-rate guidance for short-horizon backlog reduction')
    def get_postmortem_action_item_escalation_burn_rate(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-burn-rate:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        overdue_open_items = 0
        open_action_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    overdue_open_items += 1

        burn_load = len(open_escalations) + overdue_open_items
        target_daily_burn = (burn_load + days_horizon - 1) // days_horizon if burn_load > 0 else 0
        escalation_pressure_index = round(max(0.0, 100.0 - (burn_load * 10) - (target_daily_burn * 4)), 2)

        if target_daily_burn <= 1:
            burn_band = 'low'
        elif target_daily_burn <= 3:
            burn_band = 'managed'
        else:
            burn_band = 'high'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'target_daily_burn': target_daily_burn,
            'burn_band': burn_band,
            'escalation_pressure_index': escalation_pressure_index,
            'burn_load': burn_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/handoff-resilience-forecast', summary='Handoff resilience forecast for open remediation ownership')
    def get_postmortem_action_item_handoff_resilience_forecast(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:handoff-resilience-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )
        top_owner_share_pct = round((max(owner_open_items.values()) / total_open_items) * 100, 2) if total_open_items else 0.0

        handoff_resilience_score = 100.0
        handoff_resilience_score -= overdue_open_items * 9
        handoff_resilience_score -= due_within_24h * 4
        handoff_resilience_score -= unassigned_open_items * 11
        handoff_resilience_score -= len(open_escalations) * 7
        handoff_resilience_score -= overloaded_owner_count * 6
        if top_owner_share_pct >= 80.0:
            handoff_resilience_score -= 12
        elif top_owner_share_pct >= 65.0:
            handoff_resilience_score -= 6
        handoff_resilience_score = round(max(0.0, handoff_resilience_score), 2)

        if handoff_resilience_score >= 80:
            resilience_band = 'resilient'
        elif handoff_resilience_score >= 55:
            resilience_band = 'watch'
        else:
            resilience_band = 'fragile'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'handoff_resilience_score': handoff_resilience_score,
            'resilience_band': resilience_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'top_owner_share_pct': top_owner_share_pct,
        }

    @router.get('/workflow-connectors/postmortems/action-items/backlog-clearance-confidence', summary='Backlog clearance confidence over the selected horizon')
    def get_postmortem_action_item_backlog_clearance_confidence(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:backlog-clearance-confidence:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1

        clearance_load = open_action_items + (overdue_open_items * 2) + due_within_24h + (len(open_escalations) * 2)
        required_daily_closures = (clearance_load + days_horizon - 1) // days_horizon if clearance_load > 0 else 0

        backlog_clearance_confidence = 100.0
        backlog_clearance_confidence -= overdue_open_items * 9
        backlog_clearance_confidence -= due_within_24h * 4
        backlog_clearance_confidence -= len(open_escalations) * 8
        backlog_clearance_confidence -= required_daily_closures * 3
        backlog_clearance_confidence = round(max(0.0, backlog_clearance_confidence), 2)

        if backlog_clearance_confidence >= 80:
            confidence_band = 'high'
        elif backlog_clearance_confidence >= 55:
            confidence_band = 'moderate'
        else:
            confidence_band = 'low'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'backlog_clearance_confidence': backlog_clearance_confidence,
            'confidence_band': confidence_band,
            'required_daily_closures': required_daily_closures,
            'clearance_load': clearance_load,
            'open_action_items': open_action_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'open_escalations': len(open_escalations),
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-velocity-forecast', summary='Remediation velocity forecast for open action-item backlog')
    def get_postmortem_action_item_remediation_velocity_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-velocity-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1

        velocity_load = open_action_items + (overdue_open_items * 2) + due_within_24h + (len(open_escalations) * 2)
        target_daily_velocity = (velocity_load + days_horizon - 1) // days_horizon if velocity_load > 0 else 0

        remediation_velocity_score = 100.0
        remediation_velocity_score -= overdue_open_items * 8
        remediation_velocity_score -= due_within_24h * 4
        remediation_velocity_score -= len(open_escalations) * 7
        remediation_velocity_score -= target_daily_velocity * 3
        remediation_velocity_score = round(max(0.0, remediation_velocity_score), 2)

        if remediation_velocity_score >= 80:
            velocity_band = 'fast'
        elif remediation_velocity_score >= 55:
            velocity_band = 'steady'
        else:
            velocity_band = 'lagging'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_velocity_score': remediation_velocity_score,
            'velocity_band': velocity_band,
            'target_daily_velocity': target_daily_velocity,
            'velocity_load': velocity_load,
            'open_action_items': open_action_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'open_escalations': len(open_escalations),
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-recovery-readiness', summary='Escalation recovery readiness for near-term stabilization')
    def get_postmortem_action_item_escalation_recovery_readiness(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-recovery-readiness:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    overdue_open_items += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )

        escalation_recovery_score = 100.0
        escalation_recovery_score -= len(open_escalations) * 9
        escalation_recovery_score -= overdue_open_items * 7
        escalation_recovery_score -= unassigned_open_items * 10
        escalation_recovery_score -= overloaded_owner_count * 6
        escalation_recovery_score = round(max(0.0, escalation_recovery_score), 2)

        if escalation_recovery_score >= 80:
            recovery_band = 'ready'
        elif escalation_recovery_score >= 55:
            recovery_band = 'watch'
        else:
            recovery_band = 'risk'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_recovery_score': escalation_recovery_score,
            'recovery_band': recovery_band,
            'total_open_action_items': total_open_items,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'unassigned_open_items': unassigned_open_items,
            'overloaded_owner_count': overloaded_owner_count,
        }

    @router.get('/workflow-connectors/postmortems/action-items/continuity-readiness-index', summary='Continuity readiness index for ongoing remediation ownership')
    def get_postmortem_action_item_continuity_readiness_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:continuity-readiness-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )
        top_owner_share_pct = round((max(owner_open_items.values()) / total_open_items) * 100, 2) if total_open_items else 0.0

        continuity_readiness_index = 100.0
        continuity_readiness_index -= overdue_open_items * 8
        continuity_readiness_index -= due_within_24h * 4
        continuity_readiness_index -= unassigned_open_items * 10
        continuity_readiness_index -= len(open_escalations) * 7
        continuity_readiness_index -= overloaded_owner_count * 6
        if top_owner_share_pct >= 80.0:
            continuity_readiness_index -= 12
        elif top_owner_share_pct >= 65.0:
            continuity_readiness_index -= 6
        continuity_readiness_index = round(max(0.0, continuity_readiness_index), 2)

        if continuity_readiness_index >= 80:
            continuity_band = 'ready'
        elif continuity_readiness_index >= 55:
            continuity_band = 'watch'
        else:
            continuity_band = 'fragile'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'continuity_readiness_index': continuity_readiness_index,
            'continuity_band': continuity_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'top_owner_share_pct': top_owner_share_pct,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-drain-forecast', summary='Escalation drain forecast for short-horizon backlog reduction')
    def get_postmortem_action_item_escalation_drain_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-drain-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    overdue_open_items += 1

        drain_load = len(open_escalations) + overdue_open_items
        required_daily_drain = (drain_load + days_horizon - 1) // days_horizon if drain_load > 0 else 0
        drain_confidence_score = round(max(0.0, 100.0 - (drain_load * 10) - (required_daily_drain * 4)), 2)

        if required_daily_drain <= 1:
            drain_band = 'light'
        elif required_daily_drain <= 3:
            drain_band = 'moderate'
        else:
            drain_band = 'heavy'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'required_daily_drain': required_daily_drain,
            'drain_band': drain_band,
            'drain_confidence_score': drain_confidence_score,
            'drain_load': drain_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-confidence-forecast', summary='Remediation confidence forecast for short-horizon backlog execution')
    def get_postmortem_action_item_remediation_confidence_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-confidence-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1

        forecast_load = open_action_items + (overdue_open_items * 2) + due_within_24h + (len(open_escalations) * 2)
        required_daily_throughput = (forecast_load + days_horizon - 1) // days_horizon if forecast_load > 0 else 0

        remediation_confidence_score = 100.0
        remediation_confidence_score -= overdue_open_items * 8
        remediation_confidence_score -= due_within_24h * 4
        remediation_confidence_score -= len(open_escalations) * 8
        remediation_confidence_score -= required_daily_throughput * 3
        remediation_confidence_score = round(max(0.0, remediation_confidence_score), 2)

        if remediation_confidence_score >= 80:
            confidence_band = 'high'
        elif remediation_confidence_score >= 55:
            confidence_band = 'moderate'
        else:
            confidence_band = 'low'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_confidence_score': remediation_confidence_score,
            'confidence_band': confidence_band,
            'required_daily_throughput': required_daily_throughput,
            'forecast_load': forecast_load,
            'open_action_items': open_action_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'open_escalations': len(open_escalations),
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-stabilization-index', summary='Escalation stabilization index for active remediation backlog')
    def get_postmortem_action_item_escalation_stabilization_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-stabilization-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    overdue_open_items += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )

        escalation_stabilization_index = 100.0
        escalation_stabilization_index -= len(open_escalations) * 9
        escalation_stabilization_index -= overdue_open_items * 7
        escalation_stabilization_index -= unassigned_open_items * 9
        escalation_stabilization_index -= overloaded_owner_count * 6
        escalation_stabilization_index = round(max(0.0, escalation_stabilization_index), 2)

        if escalation_stabilization_index >= 80:
            stabilization_band = 'stable'
        elif escalation_stabilization_index >= 55:
            stabilization_band = 'watch'
        else:
            stabilization_band = 'unstable'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_stabilization_index': escalation_stabilization_index,
            'stabilization_band': stabilization_band,
            'total_open_action_items': total_open_items,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'unassigned_open_items': unassigned_open_items,
            'overloaded_owner_count': overloaded_owner_count,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-posture-score', summary='Remediation posture score for active action-item backlog')
    def get_postmortem_action_item_remediation_posture_score(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-posture-score:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        overloaded_owner_count = len(
            [owner for owner, count in owner_open_items.items() if owner != 'unassigned' and int(count) > max_open_items_per_owner]
        )
        top_owner_share_pct = round((max(owner_open_items.values()) / total_open_items) * 100, 2) if total_open_items else 0.0

        remediation_posture_score = 100.0
        remediation_posture_score -= overdue_open_items * 8
        remediation_posture_score -= due_within_24h * 4
        remediation_posture_score -= unassigned_open_items * 10
        remediation_posture_score -= len(open_escalations) * 7
        remediation_posture_score -= overloaded_owner_count * 6
        if top_owner_share_pct >= 80.0:
            remediation_posture_score -= 12
        elif top_owner_share_pct >= 65.0:
            remediation_posture_score -= 6
        remediation_posture_score = round(max(0.0, remediation_posture_score), 2)

        if remediation_posture_score >= 80:
            posture_band = 'strong'
        elif remediation_posture_score >= 55:
            posture_band = 'watch'
        else:
            posture_band = 'weak'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'remediation_posture_score': remediation_posture_score,
            'posture_band': posture_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'top_owner_share_pct': top_owner_share_pct,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-runway-forecast', summary='Escalation runway forecast for near-term backlog stability')
    def get_postmortem_action_item_escalation_runway_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-runway-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1

        runway_load = len(open_escalations) + overdue_open_items + due_within_24h
        required_daily_runway_actions = (runway_load + days_horizon - 1) // days_horizon if runway_load > 0 else 0
        escalation_runway_score = round(max(0.0, 100.0 - (runway_load * 9) - (required_daily_runway_actions * 4)), 2)

        if required_daily_runway_actions <= 1:
            runway_band = 'comfortable'
        elif required_daily_runway_actions <= 3:
            runway_band = 'tight'
        else:
            runway_band = 'critical'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'required_daily_runway_actions': required_daily_runway_actions,
            'runway_band': runway_band,
            'escalation_runway_score': escalation_runway_score,
            'runway_load': runway_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-balance-index', summary='Remediation balance index across active owners and action-item backlog')
    def get_postmortem_action_item_remediation_balance_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-balance-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    overdue_open_items += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        top_owner_share_pct = round((max(named_owner_counts) / total_open_items) * 100, 2) if named_owner_counts and total_open_items else 0.0

        remediation_balance_index = 100.0
        remediation_balance_index -= overdue_open_items * 7
        remediation_balance_index -= unassigned_open_items * 10
        remediation_balance_index -= len(open_escalations) * 7
        remediation_balance_index -= overloaded_owner_count * 8
        if top_owner_share_pct >= 80.0:
            remediation_balance_index -= 14
        elif top_owner_share_pct >= 60.0:
            remediation_balance_index -= 7
        remediation_balance_index = round(max(0.0, remediation_balance_index), 2)

        if remediation_balance_index >= 80:
            balance_band = 'balanced'
        elif remediation_balance_index >= 55:
            balance_band = 'watch'
        else:
            balance_band = 'imbalanced'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'remediation_balance_index': remediation_balance_index,
            'balance_band': balance_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'top_owner_share_pct': top_owner_share_pct,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-pressure-forecast', summary='Escalation pressure forecast for near-term action-item execution load')
    def get_postmortem_action_item_escalation_pressure_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-pressure-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        forecast_pressure_units = (len(open_escalations) * 2) + (overdue_open_items * 2) + due_within_24h + unassigned_open_items
        required_daily_pressure_actions = (forecast_pressure_units + days_horizon - 1) // days_horizon if forecast_pressure_units > 0 else 0
        escalation_pressure_score = round(max(0.0, 100.0 - (forecast_pressure_units * 8) - (required_daily_pressure_actions * 4)), 2)

        if escalation_pressure_score >= 80:
            pressure_band = 'contained'
        elif escalation_pressure_score >= 55:
            pressure_band = 'elevated'
        else:
            pressure_band = 'critical'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'escalation_pressure_score': escalation_pressure_score,
            'pressure_band': pressure_band,
            'required_daily_pressure_actions': required_daily_pressure_actions,
            'forecast_pressure_units': forecast_pressure_units,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-concentration-forecast', summary='Remediation concentration forecast for active owner distribution')
    def get_postmortem_action_item_remediation_concentration_forecast(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-concentration-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                if _parse_iso(action_item.get('due_at')) < now:
                    overdue_open_items += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        top_owner_open_items = max(named_owner_counts) if named_owner_counts else 0
        concentration_share_pct = round((top_owner_open_items / total_open_items) * 100, 2) if total_open_items else 0.0
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])

        remediation_concentration_score = 100.0
        remediation_concentration_score -= overdue_open_items * 7
        remediation_concentration_score -= unassigned_open_items * 9
        remediation_concentration_score -= len(open_escalations) * 6
        remediation_concentration_score -= overloaded_owner_count * 8
        if concentration_share_pct >= 80.0:
            remediation_concentration_score -= 15
        elif concentration_share_pct >= 60.0:
            remediation_concentration_score -= 8
        remediation_concentration_score = round(max(0.0, remediation_concentration_score), 2)

        if remediation_concentration_score >= 80:
            concentration_band = 'distributed'
        elif remediation_concentration_score >= 55:
            concentration_band = 'watch'
        else:
            concentration_band = 'concentrated'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'remediation_concentration_score': remediation_concentration_score,
            'concentration_band': concentration_band,
            'concentration_share_pct': concentration_share_pct,
            'top_owner_open_items': top_owner_open_items,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-containment-index', summary='Escalation containment index for short-horizon remediation stability')
    def get_postmortem_action_item_escalation_containment_index(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-containment-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        containment_load = (len(open_escalations) * 2) + overdue_open_items + due_within_24h + unassigned_open_items
        required_daily_containment_actions = (containment_load + days_horizon - 1) // days_horizon if containment_load > 0 else 0
        escalation_containment_index = round(max(0.0, 100.0 - (containment_load * 8) - (required_daily_containment_actions * 4)), 2)

        if escalation_containment_index >= 80:
            containment_band = 'contained'
        elif escalation_containment_index >= 55:
            containment_band = 'watch'
        else:
            containment_band = 'breach-risk'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'escalation_containment_index': escalation_containment_index,
            'containment_band': containment_band,
            'required_daily_containment_actions': required_daily_containment_actions,
            'containment_load': containment_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-readiness-balance', summary='Remediation readiness balance across active action-item owners')
    def get_postmortem_action_item_remediation_readiness_balance(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-readiness-balance:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_distribution_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        remediation_readiness_balance = 100.0
        remediation_readiness_balance -= overdue_open_items * 7
        remediation_readiness_balance -= due_within_24h * 4
        remediation_readiness_balance -= unassigned_open_items * 9
        remediation_readiness_balance -= len(open_escalations) * 6
        remediation_readiness_balance -= overloaded_owner_count * 8
        remediation_readiness_balance -= owner_distribution_gap * 4
        remediation_readiness_balance = round(max(0.0, remediation_readiness_balance), 2)

        if remediation_readiness_balance >= 80:
            readiness_band = 'balanced'
        elif remediation_readiness_balance >= 55:
            readiness_band = 'watch'
        else:
            readiness_band = 'strained'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'remediation_readiness_balance': remediation_readiness_balance,
            'readiness_band': readiness_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_distribution_gap': owner_distribution_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-load-shedding-forecast', summary='Escalation load shedding forecast for short-horizon backlog control')
    def get_postmortem_action_item_escalation_load_shedding_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-load-shedding-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        load_shedding_units = (len(open_escalations) * 2) + (overdue_open_items * 2) + due_within_24h + unassigned_open_items
        required_daily_load_shedding = (load_shedding_units + days_horizon - 1) // days_horizon if load_shedding_units > 0 else 0
        escalation_load_shedding_score = round(max(0.0, 100.0 - (load_shedding_units * 8) - (required_daily_load_shedding * 4)), 2)

        if required_daily_load_shedding <= 1:
            shedding_band = 'light'
        elif required_daily_load_shedding <= 3:
            shedding_band = 'moderate'
        else:
            shedding_band = 'heavy'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'escalation_load_shedding_score': escalation_load_shedding_score,
            'shedding_band': shedding_band,
            'required_daily_load_shedding': required_daily_load_shedding,
            'load_shedding_units': load_shedding_units,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-pressure-index', summary='Remediation pressure index for active owner workload')
    def get_postmortem_action_item_remediation_pressure_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-pressure-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_pressure_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        remediation_pressure_index = 100.0
        remediation_pressure_index -= overdue_open_items * 8
        remediation_pressure_index -= due_within_24h * 4
        remediation_pressure_index -= unassigned_open_items * 9
        remediation_pressure_index -= len(open_escalations) * 6
        remediation_pressure_index -= overloaded_owner_count * 8
        remediation_pressure_index -= owner_pressure_gap * 4
        remediation_pressure_index = round(max(0.0, remediation_pressure_index), 2)

        if remediation_pressure_index >= 80:
            pressure_band = 'relieved'
        elif remediation_pressure_index >= 55:
            pressure_band = 'watch'
        else:
            pressure_band = 'pressured'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'remediation_pressure_index': remediation_pressure_index,
            'pressure_band': pressure_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_pressure_gap': owner_pressure_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-relief-forecast', summary='Escalation relief forecast for short-horizon backlog recovery')
    def get_postmortem_action_item_escalation_relief_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-relief-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1

        relief_units = len(open_escalations) + overdue_open_items + due_within_24h
        required_daily_relief_actions = (relief_units + days_horizon - 1) // days_horizon if relief_units > 0 else 0
        escalation_relief_score = round(max(0.0, 100.0 - (relief_units * 9) - (required_daily_relief_actions * 4)), 2)

        if required_daily_relief_actions <= 1:
            relief_band = 'relievable'
        elif required_daily_relief_actions <= 3:
            relief_band = 'tight'
        else:
            relief_band = 'stretched'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'escalation_relief_score': escalation_relief_score,
            'relief_band': relief_band,
            'required_daily_relief_actions': required_daily_relief_actions,
            'relief_units': relief_units,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-recovery-index', summary='Remediation recovery index for active owner workload')
    def get_postmortem_action_item_remediation_recovery_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-recovery-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_recovery_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        remediation_recovery_index = 100.0
        remediation_recovery_index -= overdue_open_items * 8
        remediation_recovery_index -= due_within_24h * 4
        remediation_recovery_index -= unassigned_open_items * 9
        remediation_recovery_index -= len(open_escalations) * 6
        remediation_recovery_index -= overloaded_owner_count * 8
        remediation_recovery_index -= owner_recovery_gap * 4
        remediation_recovery_index = round(max(0.0, remediation_recovery_index), 2)

        if remediation_recovery_index >= 80:
            recovery_band = 'recovering'
        elif remediation_recovery_index >= 55:
            recovery_band = 'watch'
        else:
            recovery_band = 'delayed'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'remediation_recovery_index': remediation_recovery_index,
            'recovery_band': recovery_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_recovery_gap': owner_recovery_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-recovery-index', summary='Escalation recovery index for short-horizon backlog recovery')
    def get_postmortem_action_item_escalation_recovery_index(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-recovery-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1

        recovery_units = len(open_escalations) + overdue_open_items + due_within_24h
        required_daily_recovery_actions = (recovery_units + days_horizon - 1) // days_horizon if recovery_units > 0 else 0
        escalation_recovery_index = round(max(0.0, 100.0 - (recovery_units * 9) - (required_daily_recovery_actions * 4)), 2)

        if required_daily_recovery_actions <= 1:
            recovery_band = 'recovered'
        elif required_daily_recovery_actions <= 3:
            recovery_band = 'tight'
        else:
            recovery_band = 'lagging'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'escalation_recovery_index': escalation_recovery_index,
            'recovery_band': recovery_band,
            'required_daily_recovery_actions': required_daily_recovery_actions,
            'recovery_units': recovery_units,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-resilience-forecast', summary='Remediation resilience forecast for active owner workload')
    def get_postmortem_action_item_remediation_resilience_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-resilience-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        resilience_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
        required_daily_resilience_actions = (resilience_load + days_horizon - 1) // days_horizon if resilience_load > 0 else 0
        remediation_resilience_score = round(max(0.0, 100.0 - (resilience_load * 8) - (required_daily_resilience_actions * 4)), 2)

        if remediation_resilience_score >= 80:
            resilience_band = 'resilient'
        elif remediation_resilience_score >= 55:
            resilience_band = 'watch'
        else:
            resilience_band = 'fragile'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_resilience_score': remediation_resilience_score,
            'resilience_band': resilience_band,
            'required_daily_resilience_actions': required_daily_resilience_actions,
            'resilience_load': resilience_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-steadiness-forecast', summary='Remediation steadiness forecast for active owner workload')
    def get_postmortem_action_item_remediation_steadiness_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-steadiness-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        steadiness_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
        required_daily_steadiness_actions = (steadiness_load + days_horizon - 1) // days_horizon if steadiness_load > 0 else 0
        remediation_steadiness_score = round(max(0.0, 100.0 - (steadiness_load * 8) - (required_daily_steadiness_actions * 4)), 2)

        if remediation_steadiness_score >= 80:
            steadiness_band = 'steady'
        elif remediation_steadiness_score >= 55:
            steadiness_band = 'watch'
        else:
            steadiness_band = 'shaky'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_steadiness_score': remediation_steadiness_score,
            'steadiness_band': steadiness_band,
            'required_daily_steadiness_actions': required_daily_steadiness_actions,
            'steadiness_load': steadiness_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-steadiness-index', summary='Escalation steadiness index for active owner workload')
    def get_postmortem_action_item_escalation_steadiness_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-steadiness-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_steadiness_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_steadiness_index = 100.0
        escalation_steadiness_index -= overdue_open_items * 8
        escalation_steadiness_index -= due_within_24h * 4
        escalation_steadiness_index -= unassigned_open_items * 9
        escalation_steadiness_index -= len(open_escalations) * 6
        escalation_steadiness_index -= overloaded_owner_count * 8
        escalation_steadiness_index -= owner_steadiness_gap * 4
        escalation_steadiness_index = round(max(0.0, escalation_steadiness_index), 2)

        if escalation_steadiness_index >= 80:
            steadiness_band = 'stable'
        elif escalation_steadiness_index >= 55:
            steadiness_band = 'watch'
        else:
            steadiness_band = 'unstable'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_steadiness_index': escalation_steadiness_index,
            'steadiness_band': steadiness_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_steadiness_gap': owner_steadiness_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-durability-forecast', summary='Remediation durability forecast for active owner workload')
    def get_postmortem_action_item_remediation_durability_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-durability-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        durability_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
        required_daily_durability_actions = (durability_load + days_horizon - 1) // days_horizon if durability_load > 0 else 0
        remediation_durability_score = round(max(0.0, 100.0 - (durability_load * 8) - (required_daily_durability_actions * 4)), 2)

        if remediation_durability_score >= 80:
            durability_band = 'durable'
        elif remediation_durability_score >= 55:
            durability_band = 'watch'
        else:
            durability_band = 'brittle'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_durability_score': remediation_durability_score,
            'durability_band': durability_band,
            'required_daily_durability_actions': required_daily_durability_actions,
            'durability_load': durability_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-durability-index', summary='Escalation durability index for active owner workload')
    def get_postmortem_action_item_escalation_durability_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-durability-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_durability_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_durability_index = 100.0
        escalation_durability_index -= overdue_open_items * 8
        escalation_durability_index -= due_within_24h * 4
        escalation_durability_index -= unassigned_open_items * 9
        escalation_durability_index -= len(open_escalations) * 6
        escalation_durability_index -= overloaded_owner_count * 8
        escalation_durability_index -= owner_durability_gap * 4
        escalation_durability_index = round(max(0.0, escalation_durability_index), 2)

        if escalation_durability_index >= 80:
            durability_band = 'durable'
        elif escalation_durability_index >= 55:
            durability_band = 'watch'
        else:
            durability_band = 'fragile'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_durability_index': escalation_durability_index,
            'durability_band': durability_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_durability_gap': owner_durability_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-consistency-forecast', summary='Remediation consistency forecast for active owner workload')
    def get_postmortem_action_item_remediation_consistency_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-consistency-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        consistency_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
        required_daily_consistency_actions = (consistency_load + days_horizon - 1) // days_horizon if consistency_load > 0 else 0
        remediation_consistency_score = round(max(0.0, 100.0 - (consistency_load * 8) - (required_daily_consistency_actions * 4)), 2)

        if remediation_consistency_score >= 80:
            consistency_band = 'consistent'
        elif remediation_consistency_score >= 55:
            consistency_band = 'watch'
        else:
            consistency_band = 'inconsistent'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_consistency_score': remediation_consistency_score,
            'consistency_band': consistency_band,
            'required_daily_consistency_actions': required_daily_consistency_actions,
            'consistency_load': consistency_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-consistency-index', summary='Escalation consistency index for active owner workload')
    def get_postmortem_action_item_escalation_consistency_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-consistency-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_consistency_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_consistency_index = 100.0
        escalation_consistency_index -= overdue_open_items * 8
        escalation_consistency_index -= due_within_24h * 4
        escalation_consistency_index -= unassigned_open_items * 9
        escalation_consistency_index -= len(open_escalations) * 6
        escalation_consistency_index -= overloaded_owner_count * 8
        escalation_consistency_index -= owner_consistency_gap * 4
        escalation_consistency_index = round(max(0.0, escalation_consistency_index), 2)

        if escalation_consistency_index >= 80:
            consistency_band = 'consistent'
        elif escalation_consistency_index >= 55:
            consistency_band = 'watch'
        else:
            consistency_band = 'volatile'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_consistency_index': escalation_consistency_index,
            'consistency_band': consistency_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_consistency_gap': owner_consistency_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-alignment-forecast', summary='Remediation alignment forecast for active owner workload')
    def get_postmortem_action_item_remediation_alignment_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-alignment-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        alignment_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
        required_daily_alignment_actions = (alignment_load + days_horizon - 1) // days_horizon if alignment_load > 0 else 0
        remediation_alignment_score = round(max(0.0, 100.0 - (alignment_load * 8) - (required_daily_alignment_actions * 4)), 2)

        if remediation_alignment_score >= 80:
            alignment_band = 'aligned'
        elif remediation_alignment_score >= 55:
            alignment_band = 'watch'
        else:
            alignment_band = 'misaligned'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_alignment_score': remediation_alignment_score,
            'alignment_band': alignment_band,
            'required_daily_alignment_actions': required_daily_alignment_actions,
            'alignment_load': alignment_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-alignment-index', summary='Escalation alignment index for active owner workload')
    def get_postmortem_action_item_escalation_alignment_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-alignment-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_alignment_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_alignment_index = 100.0
        escalation_alignment_index -= overdue_open_items * 8
        escalation_alignment_index -= due_within_24h * 4
        escalation_alignment_index -= unassigned_open_items * 9
        escalation_alignment_index -= len(open_escalations) * 6
        escalation_alignment_index -= overloaded_owner_count * 8
        escalation_alignment_index -= owner_alignment_gap * 4
        escalation_alignment_index = round(max(0.0, escalation_alignment_index), 2)

        if escalation_alignment_index >= 80:
            alignment_band = 'aligned'
        elif escalation_alignment_index >= 55:
            alignment_band = 'watch'
        else:
            alignment_band = 'misaligned'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_alignment_index': escalation_alignment_index,
            'alignment_band': alignment_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_alignment_gap': owner_alignment_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-clarity-forecast', summary='Remediation clarity forecast for active owner workload')
    def get_postmortem_action_item_remediation_clarity_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-clarity-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        clarity_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
        required_daily_clarity_actions = (clarity_load + days_horizon - 1) // days_horizon if clarity_load > 0 else 0
        remediation_clarity_score = round(max(0.0, 100.0 - (clarity_load * 8) - (required_daily_clarity_actions * 4)), 2)

        if remediation_clarity_score >= 80:
            clarity_band = 'clear'
        elif remediation_clarity_score >= 55:
            clarity_band = 'watch'
        else:
            clarity_band = 'unclear'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_clarity_score': remediation_clarity_score,
            'clarity_band': clarity_band,
            'required_daily_clarity_actions': required_daily_clarity_actions,
            'clarity_load': clarity_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-clarity-index', summary='Escalation clarity index for active owner workload')
    def get_postmortem_action_item_escalation_clarity_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-clarity-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_clarity_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_clarity_index = 100.0
        escalation_clarity_index -= overdue_open_items * 8
        escalation_clarity_index -= due_within_24h * 4
        escalation_clarity_index -= unassigned_open_items * 9
        escalation_clarity_index -= len(open_escalations) * 6
        escalation_clarity_index -= overloaded_owner_count * 8
        escalation_clarity_index -= owner_clarity_gap * 4
        escalation_clarity_index = round(max(0.0, escalation_clarity_index), 2)

        if escalation_clarity_index >= 80:
            clarity_band = 'clear'
        elif escalation_clarity_index >= 55:
            clarity_band = 'watch'
        else:
            clarity_band = 'unclear'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_clarity_index': escalation_clarity_index,
            'clarity_band': clarity_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_clarity_gap': owner_clarity_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-composure-forecast', summary='Remediation composure forecast for active owner workload')
    def get_postmortem_action_item_remediation_composure_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-composure-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        composure_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
        required_daily_composure_actions = (composure_load + days_horizon - 1) // days_horizon if composure_load > 0 else 0
        remediation_composure_score = round(max(0.0, 100.0 - (composure_load * 8) - (required_daily_composure_actions * 4)), 2)

        if remediation_composure_score >= 80:
            composure_band = 'composed'
        elif remediation_composure_score >= 55:
            composure_band = 'watch'
        else:
            composure_band = 'strained'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_composure_score': remediation_composure_score,
            'composure_band': composure_band,
            'required_daily_composure_actions': required_daily_composure_actions,
            'composure_load': composure_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-composure-index', summary='Escalation composure index for active owner workload')
    def get_postmortem_action_item_escalation_composure_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-composure-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_composure_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_composure_index = 100.0
        escalation_composure_index -= overdue_open_items * 8
        escalation_composure_index -= due_within_24h * 4
        escalation_composure_index -= unassigned_open_items * 9
        escalation_composure_index -= len(open_escalations) * 6
        escalation_composure_index -= overloaded_owner_count * 8
        escalation_composure_index -= owner_composure_gap * 4
        escalation_composure_index = round(max(0.0, escalation_composure_index), 2)

        if escalation_composure_index >= 80:
            composure_band = 'composed'
        elif escalation_composure_index >= 55:
            composure_band = 'watch'
        else:
            composure_band = 'strained'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_composure_index': escalation_composure_index,
            'composure_band': composure_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_composure_gap': owner_composure_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-focus-forecast', summary='Remediation focus forecast for active owner workload')
    def get_postmortem_action_item_remediation_focus_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-focus-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if not str(action_item.get('owner', '')).strip():
                    unassigned_open_items += 1

        focus_load = len(open_escalations) + overdue_open_items + due_within_24h + unassigned_open_items
        required_daily_focus_actions = (focus_load + days_horizon - 1) // days_horizon if focus_load > 0 else 0
        remediation_focus_score = round(max(0.0, 100.0 - (focus_load * 8) - (required_daily_focus_actions * 4)), 2)

        if remediation_focus_score >= 80:
            focus_band = 'focused'
        elif remediation_focus_score >= 55:
            focus_band = 'watch'
        else:
            focus_band = 'scattered'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_focus_score': remediation_focus_score,
            'focus_band': focus_band,
            'required_daily_focus_actions': required_daily_focus_actions,
            'focus_load': focus_load,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-focus-index', summary='Escalation focus index for active owner workload')
    def get_postmortem_action_item_escalation_focus_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-focus-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_focus_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_focus_index = 100.0
        escalation_focus_index -= overdue_open_items * 8
        escalation_focus_index -= due_within_24h * 4
        escalation_focus_index -= unassigned_open_items * 9
        escalation_focus_index -= len(open_escalations) * 6
        escalation_focus_index -= overloaded_owner_count * 8
        escalation_focus_index -= owner_focus_gap * 4
        escalation_focus_index = round(max(0.0, escalation_focus_index), 2)

        if escalation_focus_index >= 80:
            focus_band = 'focused'
        elif escalation_focus_index >= 55:
            focus_band = 'watch'
        else:
            focus_band = 'diffuse'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_focus_index': escalation_focus_index,
            'focus_band': focus_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_focus_gap': owner_focus_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-attention-forecast', summary='Remediation attention forecast for action item ownership discipline')
    def get_postmortem_action_item_remediation_attention_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-attention-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        open_action_items = 0
        assigned_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                open_action_items += 1
                owner = str(action_item.get('owner', '')).strip()
                if owner:
                    assigned_open_items += 1
                else:
                    unassigned_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1

        attention_backlog = overdue_open_items + due_within_24h + (unassigned_open_items * 2) + len(open_escalations)
        required_daily_attention = (attention_backlog + days_horizon - 1) // days_horizon if attention_backlog > 0 else 0
        assigned_coverage_pct = round((assigned_open_items / open_action_items) * 100, 2) if open_action_items else 100.0
        remediation_attention_score = 100.0
        remediation_attention_score -= overdue_open_items * 7
        remediation_attention_score -= due_within_24h * 4
        remediation_attention_score -= unassigned_open_items * 10
        remediation_attention_score -= len(open_escalations) * 6
        remediation_attention_score += min(assigned_coverage_pct / 10, 10)
        remediation_attention_score = round(max(0.0, remediation_attention_score), 2)

        if remediation_attention_score >= 80:
            attention_band = 'attentive'
        elif remediation_attention_score >= 55:
            attention_band = 'watch'
        else:
            attention_band = 'fractured'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_attention_score': remediation_attention_score,
            'attention_band': attention_band,
            'required_daily_attention': required_daily_attention,
            'assigned_coverage_pct': assigned_coverage_pct,
            'attention_backlog': attention_backlog,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-attention-index', summary='Escalation attention index for action item ownership discipline')
    def get_postmortem_action_item_escalation_attention_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-attention-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_attention_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_attention_index = 100.0
        escalation_attention_index -= overdue_open_items * 7
        escalation_attention_index -= due_within_24h * 4
        escalation_attention_index -= unassigned_open_items * 10
        escalation_attention_index -= len(open_escalations) * 7
        escalation_attention_index -= overloaded_owner_count * 8
        escalation_attention_index -= owner_attention_gap * 3
        escalation_attention_index = round(max(0.0, escalation_attention_index), 2)

        if escalation_attention_index >= 80:
            attention_band = 'attentive'
        elif escalation_attention_index >= 55:
            attention_band = 'watch'
        else:
            attention_band = 'distracted'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_attention_index': escalation_attention_index,
            'attention_band': attention_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_attention_gap': owner_attention_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-coordination-forecast', summary='Remediation coordination forecast for action item workload alignment')
    def get_postmortem_action_item_remediation_coordination_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-coordination-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        owner_coordination_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)
        coordination_backlog = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
        required_daily_coordination = (coordination_backlog + days_horizon - 1) // days_horizon if coordination_backlog > 0 else 0

        remediation_coordination_score = 100.0
        remediation_coordination_score -= owner_coordination_gap * 6
        remediation_coordination_score -= overdue_open_items * 7
        remediation_coordination_score -= due_within_24h * 4
        remediation_coordination_score -= unassigned_open_items * 9
        remediation_coordination_score -= len(open_escalations) * 6
        remediation_coordination_score = round(max(0.0, remediation_coordination_score), 2)

        if remediation_coordination_score >= 80:
            coordination_band = 'coordinated'
        elif remediation_coordination_score >= 55:
            coordination_band = 'watch'
        else:
            coordination_band = 'fragmented'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_coordination_score': remediation_coordination_score,
            'coordination_band': coordination_band,
            'required_daily_coordination': required_daily_coordination,
            'coordination_backlog': coordination_backlog,
            'owner_coordination_gap': owner_coordination_gap,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-coordination-index', summary='Escalation coordination index for action item workload alignment')
    def get_postmortem_action_item_escalation_coordination_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-coordination-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_coordination_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_coordination_index = 100.0
        escalation_coordination_index -= owner_coordination_gap * 6
        escalation_coordination_index -= overdue_open_items * 7
        escalation_coordination_index -= due_within_24h * 4
        escalation_coordination_index -= unassigned_open_items * 9
        escalation_coordination_index -= len(open_escalations) * 6
        escalation_coordination_index -= overloaded_owner_count * 8
        escalation_coordination_index = round(max(0.0, escalation_coordination_index), 2)

        if escalation_coordination_index >= 80:
            coordination_band = 'coordinated'
        elif escalation_coordination_index >= 55:
            coordination_band = 'watch'
        else:
            coordination_band = 'fragmented'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_coordination_index': escalation_coordination_index,
            'coordination_band': coordination_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_coordination_gap': owner_coordination_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-orchestration-forecast', summary='Remediation orchestration forecast for action item execution cadence')
    def get_postmortem_action_item_remediation_orchestration_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-orchestration-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        owner_orchestration_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)
        orchestration_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
        required_daily_orchestration = (orchestration_load + days_horizon - 1) // days_horizon if orchestration_load > 0 else 0

        remediation_orchestration_score = 100.0
        remediation_orchestration_score -= owner_orchestration_gap * 5
        remediation_orchestration_score -= overdue_open_items * 7
        remediation_orchestration_score -= due_within_24h * 4
        remediation_orchestration_score -= unassigned_open_items * 9
        remediation_orchestration_score -= len(open_escalations) * 6
        remediation_orchestration_score = round(max(0.0, remediation_orchestration_score), 2)

        if remediation_orchestration_score >= 80:
            orchestration_band = 'orchestrated'
        elif remediation_orchestration_score >= 55:
            orchestration_band = 'watch'
        else:
            orchestration_band = 'disjointed'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_orchestration_score': remediation_orchestration_score,
            'orchestration_band': orchestration_band,
            'required_daily_orchestration': required_daily_orchestration,
            'orchestration_load': orchestration_load,
            'owner_orchestration_gap': owner_orchestration_gap,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-orchestration-index', summary='Escalation orchestration index for action item execution cadence')
    def get_postmortem_action_item_escalation_orchestration_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-orchestration-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_orchestration_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_orchestration_index = 100.0
        escalation_orchestration_index -= owner_orchestration_gap * 5
        escalation_orchestration_index -= overdue_open_items * 7
        escalation_orchestration_index -= due_within_24h * 4
        escalation_orchestration_index -= unassigned_open_items * 9
        escalation_orchestration_index -= len(open_escalations) * 6
        escalation_orchestration_index -= overloaded_owner_count * 8
        escalation_orchestration_index = round(max(0.0, escalation_orchestration_index), 2)

        if escalation_orchestration_index >= 80:
            orchestration_band = 'orchestrated'
        elif escalation_orchestration_index >= 55:
            orchestration_band = 'watch'
        else:
            orchestration_band = 'disjointed'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_orchestration_index': escalation_orchestration_index,
            'orchestration_band': orchestration_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_orchestration_gap': owner_orchestration_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-synchronization-forecast', summary='Remediation synchronization forecast for owner execution alignment')
    def get_postmortem_action_item_remediation_synchronization_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-synchronization-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        owner_synchronization_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)
        synchronization_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
        required_daily_sync_actions = (synchronization_load + days_horizon - 1) // days_horizon if synchronization_load > 0 else 0

        remediation_synchronization_score = 100.0
        remediation_synchronization_score -= owner_synchronization_gap * 5
        remediation_synchronization_score -= overdue_open_items * 7
        remediation_synchronization_score -= due_within_24h * 4
        remediation_synchronization_score -= unassigned_open_items * 9
        remediation_synchronization_score -= len(open_escalations) * 6
        remediation_synchronization_score = round(max(0.0, remediation_synchronization_score), 2)

        if remediation_synchronization_score >= 80:
            synchronization_band = 'synchronized'
        elif remediation_synchronization_score >= 55:
            synchronization_band = 'watch'
        else:
            synchronization_band = 'desynced'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_synchronization_score': remediation_synchronization_score,
            'synchronization_band': synchronization_band,
            'required_daily_sync_actions': required_daily_sync_actions,
            'synchronization_load': synchronization_load,
            'owner_synchronization_gap': owner_synchronization_gap,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-synchronization-index', summary='Escalation synchronization index for owner execution alignment')
    def get_postmortem_action_item_escalation_synchronization_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-synchronization-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_synchronization_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_synchronization_index = 100.0
        escalation_synchronization_index -= owner_synchronization_gap * 5
        escalation_synchronization_index -= overdue_open_items * 7
        escalation_synchronization_index -= due_within_24h * 4
        escalation_synchronization_index -= unassigned_open_items * 9
        escalation_synchronization_index -= len(open_escalations) * 6
        escalation_synchronization_index -= overloaded_owner_count * 8
        escalation_synchronization_index = round(max(0.0, escalation_synchronization_index), 2)

        if escalation_synchronization_index >= 80:
            synchronization_band = 'synchronized'
        elif escalation_synchronization_index >= 55:
            synchronization_band = 'watch'
        else:
            synchronization_band = 'desynced'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_synchronization_index': escalation_synchronization_index,
            'synchronization_band': synchronization_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_synchronization_gap': owner_synchronization_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-harmony-forecast', summary='Remediation harmony forecast for owner workload cohesion')
    def get_postmortem_action_item_remediation_harmony_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-harmony-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        owner_harmony_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)
        harmony_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
        required_daily_harmony_actions = (harmony_load + days_horizon - 1) // days_horizon if harmony_load > 0 else 0

        remediation_harmony_score = 100.0
        remediation_harmony_score -= owner_harmony_gap * 5
        remediation_harmony_score -= overdue_open_items * 7
        remediation_harmony_score -= due_within_24h * 4
        remediation_harmony_score -= unassigned_open_items * 9
        remediation_harmony_score -= len(open_escalations) * 6
        remediation_harmony_score = round(max(0.0, remediation_harmony_score), 2)

        if remediation_harmony_score >= 80:
            harmony_band = 'harmonized'
        elif remediation_harmony_score >= 55:
            harmony_band = 'watch'
        else:
            harmony_band = 'discordant'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_harmony_score': remediation_harmony_score,
            'harmony_band': harmony_band,
            'required_daily_harmony_actions': required_daily_harmony_actions,
            'harmony_load': harmony_load,
            'owner_harmony_gap': owner_harmony_gap,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-harmony-index', summary='Escalation harmony index for owner workload cohesion')
    def get_postmortem_action_item_escalation_harmony_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-harmony-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_harmony_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_harmony_index = 100.0
        escalation_harmony_index -= owner_harmony_gap * 5
        escalation_harmony_index -= overdue_open_items * 7
        escalation_harmony_index -= due_within_24h * 4
        escalation_harmony_index -= unassigned_open_items * 9
        escalation_harmony_index -= len(open_escalations) * 6
        escalation_harmony_index -= overloaded_owner_count * 8
        escalation_harmony_index = round(max(0.0, escalation_harmony_index), 2)

        if escalation_harmony_index >= 80:
            harmony_band = 'harmonized'
        elif escalation_harmony_index >= 55:
            harmony_band = 'watch'
        else:
            harmony_band = 'discordant'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_harmony_index': escalation_harmony_index,
            'harmony_band': harmony_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_harmony_gap': owner_harmony_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-rhythm-forecast', summary='Remediation rhythm forecast for owner execution cadence')
    def get_postmortem_action_item_remediation_rhythm_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-rhythm-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        owner_rhythm_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)
        rhythm_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
        required_daily_rhythm_actions = (rhythm_load + days_horizon - 1) // days_horizon if rhythm_load > 0 else 0

        remediation_rhythm_score = 100.0
        remediation_rhythm_score -= owner_rhythm_gap * 5
        remediation_rhythm_score -= overdue_open_items * 7
        remediation_rhythm_score -= due_within_24h * 4
        remediation_rhythm_score -= unassigned_open_items * 9
        remediation_rhythm_score -= len(open_escalations) * 6
        remediation_rhythm_score = round(max(0.0, remediation_rhythm_score), 2)

        if remediation_rhythm_score >= 80:
            rhythm_band = 'steady'
        elif remediation_rhythm_score >= 55:
            rhythm_band = 'watch'
        else:
            rhythm_band = 'erratic'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_rhythm_score': remediation_rhythm_score,
            'rhythm_band': rhythm_band,
            'required_daily_rhythm_actions': required_daily_rhythm_actions,
            'rhythm_load': rhythm_load,
            'owner_rhythm_gap': owner_rhythm_gap,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-rhythm-index', summary='Escalation rhythm index for owner execution cadence')
    def get_postmortem_action_item_escalation_rhythm_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-rhythm-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_rhythm_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_rhythm_index = 100.0
        escalation_rhythm_index -= owner_rhythm_gap * 5
        escalation_rhythm_index -= overdue_open_items * 7
        escalation_rhythm_index -= due_within_24h * 4
        escalation_rhythm_index -= unassigned_open_items * 9
        escalation_rhythm_index -= len(open_escalations) * 6
        escalation_rhythm_index -= overloaded_owner_count * 8
        escalation_rhythm_index = round(max(0.0, escalation_rhythm_index), 2)

        if escalation_rhythm_index >= 80:
            rhythm_band = 'steady'
        elif escalation_rhythm_index >= 55:
            rhythm_band = 'watch'
        else:
            rhythm_band = 'erratic'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_rhythm_index': escalation_rhythm_index,
            'rhythm_band': rhythm_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_rhythm_gap': owner_rhythm_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-tempo-forecast', summary='Remediation tempo forecast for owner execution pacing')
    def get_postmortem_action_item_remediation_tempo_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-tempo-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        owner_tempo_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)
        tempo_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
        required_daily_tempo_actions = (tempo_load + days_horizon - 1) // days_horizon if tempo_load > 0 else 0

        remediation_tempo_score = 100.0
        remediation_tempo_score -= owner_tempo_gap * 5
        remediation_tempo_score -= overdue_open_items * 7
        remediation_tempo_score -= due_within_24h * 4
        remediation_tempo_score -= unassigned_open_items * 9
        remediation_tempo_score -= len(open_escalations) * 6
        remediation_tempo_score = round(max(0.0, remediation_tempo_score), 2)

        if remediation_tempo_score >= 80:
            tempo_band = 'steady'
        elif remediation_tempo_score >= 55:
            tempo_band = 'watch'
        else:
            tempo_band = 'rushing'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_tempo_score': remediation_tempo_score,
            'tempo_band': tempo_band,
            'required_daily_tempo_actions': required_daily_tempo_actions,
            'tempo_load': tempo_load,
            'owner_tempo_gap': owner_tempo_gap,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-tempo-index', summary='Escalation tempo index for owner execution pacing')
    def get_postmortem_action_item_escalation_tempo_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-tempo-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_tempo_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_tempo_index = 100.0
        escalation_tempo_index -= owner_tempo_gap * 5
        escalation_tempo_index -= overdue_open_items * 7
        escalation_tempo_index -= due_within_24h * 4
        escalation_tempo_index -= unassigned_open_items * 9
        escalation_tempo_index -= len(open_escalations) * 6
        escalation_tempo_index -= overloaded_owner_count * 8
        escalation_tempo_index = round(max(0.0, escalation_tempo_index), 2)

        if escalation_tempo_index >= 80:
            tempo_band = 'steady'
        elif escalation_tempo_index >= 55:
            tempo_band = 'watch'
        else:
            tempo_band = 'rushing'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_tempo_index': escalation_tempo_index,
            'tempo_band': tempo_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_tempo_gap': owner_tempo_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-cadence-forecast', summary='Remediation cadence forecast for owner execution flow')
    def get_postmortem_action_item_remediation_cadence_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-cadence-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        owner_cadence_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)
        cadence_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
        required_daily_cadence_actions = (cadence_load + days_horizon - 1) // days_horizon if cadence_load > 0 else 0

        remediation_cadence_score = 100.0
        remediation_cadence_score -= owner_cadence_gap * 5
        remediation_cadence_score -= overdue_open_items * 7
        remediation_cadence_score -= due_within_24h * 4
        remediation_cadence_score -= unassigned_open_items * 9
        remediation_cadence_score -= len(open_escalations) * 6
        remediation_cadence_score = round(max(0.0, remediation_cadence_score), 2)

        if remediation_cadence_score >= 80:
            cadence_band = 'steady'
        elif remediation_cadence_score >= 55:
            cadence_band = 'watch'
        else:
            cadence_band = 'choppy'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_cadence_score': remediation_cadence_score,
            'cadence_band': cadence_band,
            'required_daily_cadence_actions': required_daily_cadence_actions,
            'cadence_load': cadence_load,
            'owner_cadence_gap': owner_cadence_gap,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-cadence-index', summary='Escalation cadence index for owner execution flow')
    def get_postmortem_action_item_escalation_cadence_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-cadence-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_cadence_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_cadence_index = 100.0
        escalation_cadence_index -= owner_cadence_gap * 5
        escalation_cadence_index -= overdue_open_items * 7
        escalation_cadence_index -= due_within_24h * 4
        escalation_cadence_index -= unassigned_open_items * 9
        escalation_cadence_index -= len(open_escalations) * 6
        escalation_cadence_index -= overloaded_owner_count * 8
        escalation_cadence_index = round(max(0.0, escalation_cadence_index), 2)

        if escalation_cadence_index >= 80:
            cadence_band = 'steady'
        elif escalation_cadence_index >= 55:
            cadence_band = 'watch'
        else:
            cadence_band = 'choppy'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_cadence_index': escalation_cadence_index,
            'cadence_band': cadence_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_cadence_gap': owner_cadence_gap,
        }

    @router.get('/workflow-connectors/postmortems/action-items/remediation-stability-forecast', summary='Remediation stability forecast for owner execution consistency')
    def get_postmortem_action_item_remediation_stability_forecast(
        auth: AuthDep,
        days_horizon: Annotated[int, Query(ge=1, le=30)] = 7,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:remediation-stability-forecast:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        open_action_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                open_action_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        owner_stability_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)
        stability_load = overdue_open_items + due_within_24h + unassigned_open_items + len(open_escalations)
        required_daily_stability_actions = (stability_load + days_horizon - 1) // days_horizon if stability_load > 0 else 0

        remediation_stability_score = 100.0
        remediation_stability_score -= owner_stability_gap * 5
        remediation_stability_score -= overdue_open_items * 7
        remediation_stability_score -= due_within_24h * 4
        remediation_stability_score -= unassigned_open_items * 9
        remediation_stability_score -= len(open_escalations) * 6
        remediation_stability_score = round(max(0.0, remediation_stability_score), 2)

        if remediation_stability_score >= 80:
            stability_band = 'stable'
        elif remediation_stability_score >= 55:
            stability_band = 'watch'
        else:
            stability_band = 'volatile'

        return {
            'status': 'ok',
            'days_horizon': days_horizon,
            'remediation_stability_score': remediation_stability_score,
            'stability_band': stability_band,
            'required_daily_stability_actions': required_daily_stability_actions,
            'stability_load': stability_load,
            'owner_stability_gap': owner_stability_gap,
            'open_escalations': len(open_escalations),
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_action_items': open_action_items,
        }

    @router.get('/workflow-connectors/postmortems/action-items/escalation-stability-index', summary='Escalation stability index for owner execution consistency')
    def get_postmortem_action_item_escalation_stability_index(
        auth: AuthDep,
        max_open_items_per_owner: Annotated[int, Query(ge=1, le=100)] = 3,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:action-items:escalation-stability-index:get', 120, 60)
        now = datetime.now(UTC)
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]
            open_escalations = [
                item.copy() for item in _connector_postmortem_action_item_escalations_memory
                if item.get('tenant_id') == auth.tenant_id and str(item.get('status', 'open')).lower() == 'open'
            ]

        owner_open_items: dict[str, int] = {}
        total_open_items = 0
        overdue_open_items = 0
        due_within_24h = 0
        unassigned_open_items = 0
        for postmortem in tenant_postmortems:
            for action_item in (postmortem.get('action_items_detailed') or []):
                if str(action_item.get('status', 'open')).lower() == 'done':
                    continue
                owner = str(action_item.get('owner', '')).strip() or 'unassigned'
                owner_open_items[owner] = int(owner_open_items.get(owner, 0)) + 1
                total_open_items += 1
                due_at = _parse_iso(action_item.get('due_at'))
                if due_at < now:
                    overdue_open_items += 1
                elif due_at <= now + timedelta(hours=24):
                    due_within_24h += 1
                if owner == 'unassigned':
                    unassigned_open_items += 1

        named_owner_counts = [count for owner, count in owner_open_items.items() if owner != 'unassigned']
        overloaded_owner_count = len([count for count in named_owner_counts if int(count) > max_open_items_per_owner])
        owner_stability_gap = (max(named_owner_counts) - min(named_owner_counts)) if len(named_owner_counts) >= 2 else (named_owner_counts[0] if named_owner_counts else 0)

        escalation_stability_index = 100.0
        escalation_stability_index -= owner_stability_gap * 5
        escalation_stability_index -= overdue_open_items * 7
        escalation_stability_index -= due_within_24h * 4
        escalation_stability_index -= unassigned_open_items * 9
        escalation_stability_index -= len(open_escalations) * 6
        escalation_stability_index -= overloaded_owner_count * 8
        escalation_stability_index = round(max(0.0, escalation_stability_index), 2)

        if escalation_stability_index >= 80:
            stability_band = 'stable'
        elif escalation_stability_index >= 55:
            stability_band = 'watch'
        else:
            stability_band = 'volatile'

        return {
            'status': 'ok',
            'max_open_items_per_owner': max_open_items_per_owner,
            'escalation_stability_index': escalation_stability_index,
            'stability_band': stability_band,
            'total_open_action_items': total_open_items,
            'overdue_open_items': overdue_open_items,
            'due_within_24h': due_within_24h,
            'unassigned_open_items': unassigned_open_items,
            'open_escalations': len(open_escalations),
            'overloaded_owner_count': overloaded_owner_count,
            'owner_stability_gap': owner_stability_gap,
        }

    @router.get('/workflow-connectors/postmortems/compliance-rollups', summary='Weekly postmortem compliance rollups')
    def get_postmortem_compliance_rollups(
        auth: AuthDep,
        weeks: Annotated[int, Query(ge=1, le=26)] = 4,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:postmortems:compliance:rollups', 120, 60)
        now = datetime.now(UTC)
        week_rollups: list[dict[str, Any]] = []
        with _lock:
            tenant_postmortems = [
                p.copy() for p in _connector_postmortems_memory
                if p.get('tenant_id') == auth.tenant_id
            ]

        for idx in range(weeks):
            period_end = now - timedelta(days=idx * 7)
            period_start = period_end - timedelta(days=7)
            created = [
                p for p in tenant_postmortems
                if period_start <= _parse_iso(p.get('created_at')) < period_end
            ]
            closed = [
                p for p in tenant_postmortems
                if p.get('status') == 'closed' and period_start <= _parse_iso(p.get('closed_at')) < period_end
            ]
            closed_within_sla = [p for p in closed if str(p.get('closure_sla_status', '')).lower() == 'met']
            open_overdue_actions = 0
            for p in tenant_postmortems:
                if p.get('status') == 'closed':
                    continue
                for item in (p.get('action_items_detailed') or []):
                    if str(item.get('status', '')).lower() == 'done':
                        continue
                    if _parse_iso(item.get('due_at')) < now:
                        open_overdue_actions += 1

            closure_rate_pct = round((len(closed) / len(created)) * 100, 2) if created else 100.0
            sla_compliance_pct = round((len(closed_within_sla) / len(closed)) * 100, 2) if closed else 100.0
            week_rollups.append(
                {
                    'week_start': period_start.isoformat(),
                    'week_end': period_end.isoformat(),
                    'postmortems_created': len(created),
                    'postmortems_closed': len(closed),
                    'closed_within_sla': len(closed_within_sla),
                    'closure_rate_pct': closure_rate_pct,
                    'sla_compliance_pct': sla_compliance_pct,
                    'open_overdue_action_items': open_overdue_actions,
                }
            )

        week_rollups.sort(key=lambda item: _parse_iso(item.get('week_start')), reverse=True)
        return {'status': 'ok', 'weeks': weeks, 'rollups': week_rollups, 'total': len(week_rollups)}

    @router.post('/workflow-connectors', summary='Register or update workflow connector')
    def upsert_connector(payload: WorkflowConnectorUpsertRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:upsert', 60, 60)
        name_normalized = payload.name.strip().lower()
        now = datetime.now(UTC).isoformat()
        with _lock:
            existing = next(
                (
                    c for c in _connectors_memory
                    if c.get('tenant_id') == auth.tenant_id and str(c.get('name', '')).strip().lower() == name_normalized
                ),
                None,
            )
            if existing is None:
                connector = {
                    'id': len(_connectors_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'name': payload.name,
                    'vendor': payload.vendor,
                    'auth_type': payload.auth_type,
                    'capabilities': payload.capabilities,
                    'rate_limit_per_minute': payload.rate_limit_per_minute,
                    'error_budget_pct': payload.error_budget_pct,
                    'status': 'unknown',
                    'last_checked_at': None,
                    'reliability_policy': _default_reliability_policy(),
                    'reliability_stats': {
                        'total_requests': 0,
                        'failed_requests': 0,
                        'retries_attempted': 0,
                        'replay_enqueued': 0,
                        'replay_success': 0,
                        'replay_failed': 0,
                    },
                    'circuit_breaker': {
                        'state': 'closed',
                        'consecutive_failures': 0,
                        'opened_at': None,
                        'cooldown_seconds': 120,
                    },
                    'created_at': now,
                    'updated_at': now,
                }
                _connectors_memory.append(connector)
            else:
                existing['vendor'] = payload.vendor
                existing['auth_type'] = payload.auth_type
                existing['capabilities'] = payload.capabilities
                existing['rate_limit_per_minute'] = payload.rate_limit_per_minute
                existing['error_budget_pct'] = payload.error_budget_pct
                existing['updated_at'] = now
                _ensure_reliability_fields(existing)
                connector = existing
        _append_audit(auth.tenant_id, 'workflow_connector_upserted', _coerce_int(connector.get('id')))
        return {'status': 'ok', 'connector': connector}

    @router.get('/workflow-connectors', summary='List connectors for workflows')
    def list_connectors(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:list', 120, 60)
        with _lock:
            connectors = [c.copy() for c in _connectors_memory if c.get('tenant_id') == auth.tenant_id]
        return {'status': 'ok', 'connectors': connectors, 'total': len(connectors)}

    @router.post('/workflow-connectors/{connector_id}/health-check', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def connector_health_check(connector_id: int, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:health', 90, 60)
        with _lock:
            connector = next(
                (
                    c for c in _connectors_memory
                    if c.get('id') == connector_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
            _ensure_reliability_fields(connector)
            score_seed = len(str(connector.get('name', ''))) + len(str(connector.get('vendor', '')))
            health = 'healthy' if score_seed % 3 != 0 else 'degraded'
            connector['status'] = health
            connector['last_checked_at'] = datetime.now(UTC).isoformat()
            connector['updated_at'] = datetime.now(UTC).isoformat()
            connector['reliability_stats']['total_requests'] = int(connector['reliability_stats'].get('total_requests', 0)) + 1
            if health != 'healthy':
                connector['reliability_stats']['failed_requests'] = int(connector['reliability_stats'].get('failed_requests', 0)) + 1
        _append_audit(auth.tenant_id, 'workflow_connector_health_checked', connector_id)
        reliability = _compute_reliability_snapshot(connector)
        _record_sla_alert(auth.tenant_id, connector, reliability)
        _close_sla_alerts_if_recovered(auth.tenant_id, connector_id, reliability)
        return {
            'status': 'ok',
            'connector': connector,
            'health': {
                'status': connector['status'],
                'latency_ms_p95': 120 if connector['status'] == 'healthy' else 480,
                'availability_pct_24h': 99.95 if connector['status'] == 'healthy' else 97.1,
            },
            'reliability': reliability,
        }

    @router.patch('/workflow-connectors/{connector_id}/reliability-policy', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def update_connector_reliability_policy(
        connector_id: int,
        payload: WorkflowConnectorReliabilityPolicyRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:policy:update', 60, 60)
        with _lock:
            connector = next(
                (
                    c for c in _connectors_memory
                    if c.get('id') == connector_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
            _ensure_reliability_fields(connector)
            connector['reliability_policy'] = {
                'max_retries': payload.max_retries,
                'base_backoff_ms': payload.base_backoff_ms,
                'circuit_failure_threshold': payload.circuit_failure_threshold,
                'circuit_cooldown_seconds': payload.circuit_cooldown_seconds,
                'slo_availability_target_pct': payload.slo_availability_target_pct,
                'slo_latency_p95_target_ms': payload.slo_latency_p95_target_ms,
                'replay_enabled': payload.replay_enabled,
            }
            connector['circuit_breaker']['cooldown_seconds'] = payload.circuit_cooldown_seconds
            connector['updated_at'] = datetime.now(UTC).isoformat()
        _append_audit(auth.tenant_id, 'workflow_connector_reliability_policy_updated', connector_id)
        return {'status': 'ok', 'connector': connector, 'policy': connector['reliability_policy']}

    @router.get('/workflow-connectors/{connector_id}/reliability', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def get_connector_reliability(connector_id: int, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:reliability:get', 120, 60)
        with _lock:
            connector = next(
                (
                    c for c in _connectors_memory
                    if c.get('id') == connector_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
            _ensure_reliability_fields(connector)
            replay_items = [
                i for i in _connector_replay_queue_memory
                if i.get('tenant_id') == auth.tenant_id and i.get('connector_id') == connector_id
            ]
            reliability = _compute_reliability_snapshot(connector)
            _record_sla_alert(auth.tenant_id, connector, reliability)
            _close_sla_alerts_if_recovered(auth.tenant_id, connector_id, reliability)
        return {
            'status': 'ok',
            'connector': connector,
            'circuit_breaker': connector['circuit_breaker'],
            'policy': connector['reliability_policy'],
            'stats': connector['reliability_stats'],
            'replay_queue': {
                'total': len(replay_items),
                'pending': len([i for i in replay_items if i.get('status') == 'pending']),
                'items': replay_items[:25],
            },
            'slo': reliability,
        }

    @router.post('/workflow-connectors/{connector_id}/simulate-failure', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def simulate_connector_failure(
        connector_id: int,
        payload: WorkflowConnectorFailureSimulationRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:simulate-failure', 60, 60)
        failure_type = payload.failure_type.strip().lower() or 'timeout'
        with _lock:
            connector = next(
                (
                    c for c in _connectors_memory
                    if c.get('id') == connector_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
            _ensure_reliability_fields(connector)
            policy = connector['reliability_policy']
            stats = connector['reliability_stats']
            circuit = connector['circuit_breaker']

            stats['total_requests'] = int(stats.get('total_requests', 0)) + 1
            stats['failed_requests'] = int(stats.get('failed_requests', 0)) + 1
            if _is_retryable_failure(failure_type):
                stats['retries_attempted'] = int(stats.get('retries_attempted', 0)) + int(policy.get('max_retries', 0))

            circuit['consecutive_failures'] = int(circuit.get('consecutive_failures', 0)) + 1
            if int(circuit['consecutive_failures']) >= int(policy.get('circuit_failure_threshold', 5)):
                circuit['state'] = 'open'
                circuit['opened_at'] = datetime.now(UTC).isoformat()
            connector['status'] = 'degraded'

            replay_item = None
            if bool(policy.get('replay_enabled', True)):
                now = datetime.now(UTC)
                replay_item = {
                    'id': len(_connector_replay_queue_memory) + 1,
                    'tenant_id': auth.tenant_id,
                    'connector_id': connector_id,
                    'connector_name': connector.get('name'),
                    'failure_type': failure_type,
                    'operation_ref': payload.operation_ref or f'op-{len(_connector_replay_queue_memory) + 1}',
                    'attempts': 0,
                    'status': 'pending',
                    'created_at': now.isoformat(),
                    'updated_at': now.isoformat(),
                    'next_retry_at': _next_retry_at(now, 1, int(policy.get('base_backoff_ms', 250))),
                }
                _connector_replay_queue_memory.append(replay_item)
                stats['replay_enqueued'] = int(stats.get('replay_enqueued', 0)) + 1
            connector['updated_at'] = datetime.now(UTC).isoformat()

            reliability = _compute_reliability_snapshot(connector)
            _record_sla_alert(auth.tenant_id, connector, reliability)
        _append_audit(auth.tenant_id, 'workflow_connector_failure_simulated', connector_id)
        return {
            'status': 'ok',
            'connector': connector,
            'replay_item': replay_item,
            'slo': reliability,
        }

    @router.get('/workflow-connectors/replay-queue')
    def list_connector_replay_queue(
        auth: AuthDep,
        connector_id: Annotated[int | None, Query(ge=1)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:replay:list', 120, 60)
        with _lock:
            items = [item.copy() for item in _connector_replay_queue_memory if item.get('tenant_id') == auth.tenant_id]
        if connector_id is not None:
            items = [item for item in items if item.get('connector_id') == connector_id]
        return {'status': 'ok', 'items': items[:limit], 'total': len(items)}

    @router.get('/workflow-connectors/sla-alerts')
    def list_connector_sla_alerts(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=20)] = None,
        limit: Annotated[int, Query(ge=1, le=200)] = 100,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:sla-alerts:list', 120, 60)
        with _lock:
            items = [a.copy() for a in _connector_sla_alerts_memory if a.get('tenant_id') == auth.tenant_id]
        if status:
            items = [a for a in items if str(a.get('status', '')).strip().lower() == status.strip().lower()]
        return {'status': 'ok', 'alerts': items[:limit], 'total': len(items)}

    @router.post('/workflow-connectors/reconcile-circuits')
    def reconcile_connector_circuits(auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:circuits:reconcile', 60, 60)
        now = datetime.now(UTC)
        transitioned: list[dict[str, Any]] = []
        with _lock:
            for connector in _connectors_memory:
                if connector.get('tenant_id') != auth.tenant_id:
                    continue
                _ensure_reliability_fields(connector)
                circuit = connector['circuit_breaker']
                state = str(circuit.get('state', 'closed'))
                if state != 'open':
                    continue
                opened_at_raw = circuit.get('opened_at')
                if not opened_at_raw:
                    continue
                opened_at = datetime.fromisoformat(str(opened_at_raw))
                elapsed = (now - opened_at).total_seconds()
                cooldown = int(circuit.get('cooldown_seconds', 120))
                if elapsed >= cooldown:
                    circuit['state'] = 'half_open'
                    circuit['consecutive_failures'] = 0
                    connector['status'] = 'degraded'
                    connector['updated_at'] = now.isoformat()
                    transitioned.append({'connector_id': connector.get('id'), 'state': 'half_open'})
        _append_audit(auth.tenant_id, 'workflow_connector_circuits_reconciled', len(transitioned))
        return {'status': 'ok', 'transitioned': transitioned, 'count': len(transitioned)}

    @router.post('/workflow-connectors/replay-queue/process')
    def process_connector_replay_queue(payload: WorkflowConnectorReplayProcessorRequest, auth: AuthDep) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:replay:process', 60, 60)
        now = datetime.now(UTC)
        processed: list[dict[str, Any]] = []
        with _lock:
            pending = [
                item for item in _connector_replay_queue_memory
                if item.get('tenant_id') == auth.tenant_id and item.get('status') == 'pending'
            ]
            if payload.connector_id is not None:
                pending = [item for item in pending if int(item.get('connector_id', 0)) == payload.connector_id]

            def _is_due(item: dict[str, Any]) -> bool:
                next_retry_at = item.get('next_retry_at')
                if not next_retry_at:
                    return True
                return datetime.fromisoformat(str(next_retry_at)) <= now

            due_items = [item for item in pending if _is_due(item) or payload.include_not_due][: payload.limit]
            for item in due_items:
                connector = next(
                    (
                        c for c in _connectors_memory
                        if int(c.get('id', 0)) == int(item.get('connector_id', 0)) and c.get('tenant_id') == auth.tenant_id
                    ),
                    None,
                )
                if connector is None:
                    item['status'] = 'failed'
                    item['updated_at'] = now.isoformat()
                    item['next_retry_at'] = None
                    processed.append({'item_id': item.get('id'), 'status': 'failed', 'reason': 'connector_not_found'})
                    continue

                if _is_in_maintenance_window(auth.tenant_id, int(connector.get('id', 0)), now):
                    processed.append(
                        {
                            'item_id': item.get('id'),
                            'connector_id': connector.get('id'),
                            'status': item.get('status'),
                            'next_retry_at': item.get('next_retry_at'),
                            'reason': 'maintenance_window_active',
                        }
                    )
                    continue

                result = _process_replay_item_locked(connector=connector, item=item, force_success=payload.force_success)
                reliability = result['slo']
                _record_sla_alert(auth.tenant_id, connector, reliability)
                _close_sla_alerts_if_recovered(auth.tenant_id, int(connector.get('id', 0)), reliability)
                processed.append(
                    {
                        'item_id': item.get('id'),
                        'connector_id': connector.get('id'),
                        'status': item.get('status'),
                        'next_retry_at': item.get('next_retry_at'),
                    }
                )

        _append_audit(auth.tenant_id, 'workflow_connector_replay_queue_processed', len(processed))
        return {'status': 'ok', 'processed': processed, 'count': len(processed)}

    @router.post('/workflow-connectors/{connector_id}/replay-queue/{item_id}/replay', responses={404: {'description': EXECUTION_NOT_FOUND}})
    def replay_connector_queue_item(
        connector_id: int,
        item_id: int,
        payload: WorkflowConnectorReplayRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        enforce_rate_limit(f'{auth.tenant_id}:workflows:connectors:replay:run', 90, 60)
        with _lock:
            connector = next(
                (
                    c for c in _connectors_memory
                    if c.get('id') == connector_id and c.get('tenant_id') == auth.tenant_id
                ),
                None,
            )
            if connector is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
            _ensure_reliability_fields(connector)
            item = next(
                (
                    i for i in _connector_replay_queue_memory
                    if i.get('id') == item_id and i.get('tenant_id') == auth.tenant_id and i.get('connector_id') == connector_id
                ),
                None,
            )
            if item is None:
                raise HTTPException(status_code=404, detail=EXECUTION_NOT_FOUND)
            if item.get('status') != 'pending':
                raise HTTPException(status_code=409, detail='Replay item already processed.')
            result = _process_replay_item_locked(connector=connector, item=item, force_success=payload.force_success)
            reliability = result['slo']
            _record_sla_alert(auth.tenant_id, connector, reliability)
            _close_sla_alerts_if_recovered(auth.tenant_id, connector_id, reliability)
        _append_audit(auth.tenant_id, 'workflow_connector_replay_processed', item_id)
        return {
            'status': 'ok',
            'item': item,
            'connector': connector,
            'slo': reliability,
        }

    return router
