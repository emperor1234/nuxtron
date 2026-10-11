"""Canonical workflow HTTP composition; compatibility callers retain the factory interface."""

import threading
from collections.abc import Callable
from typing import Any
from fastapi import APIRouter
from .runtime import WorkflowRuntime
from .api import (
    workflow,
    toggle_workflow,
    list_workflow_approval_policies,
    list_maintenance_windows,
    assign_runbook_operator,
    list_connector_postmortems,
    decide_postmortem_closure_request,
    process_postmortem_escalation_cadence,
    owner_workload,
    coverage_gaps,
    stability_score,
    readiness_forecast,
    owner_relief_plan,
    ownership_stability_forecast,
    continuity_readiness_index,
    remediation_balance_index,
    remediation_pressure_index,
    escalation_steadiness_index,
    escalation_alignment_index,
    escalation_focus_index,
    remediation_orchestration_forecast,
    escalation_harmony_index,
    remediation_cadence_forecast,
    connector_health_check,
    replay_connector_queue_item,
)


def create_workflows_router(
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
    """Compose workflow route groups with a single explicitly owned runtime."""
    router = APIRouter()
    _lock = threading.RLock()
    _approval_policies_memory = approval_policies_memory if approval_policies_memory is not None else []
    _approval_requests_memory = approval_requests_memory if approval_requests_memory is not None else []
    _connectors_memory = connectors_memory if connectors_memory is not None else []
    _connector_replay_queue_memory = connector_replay_queue_memory if connector_replay_queue_memory is not None else []
    _connector_sla_alerts_memory = connector_sla_alerts_memory if connector_sla_alerts_memory is not None else []
    _connector_policy_templates_memory = (
        connector_policy_templates_memory if connector_policy_templates_memory is not None else []
    )
    _connector_maintenance_windows_memory = (
        connector_maintenance_windows_memory if connector_maintenance_windows_memory is not None else []
    )
    _connector_escalation_rules_memory = (
        connector_escalation_rules_memory if connector_escalation_rules_memory is not None else []
    )
    _connector_escalation_events_memory = (
        connector_escalation_events_memory if connector_escalation_events_memory is not None else []
    )
    _connector_runbooks_memory = connector_runbooks_memory if connector_runbooks_memory is not None else []
    _connector_runbook_assignments_memory = (
        connector_runbook_assignments_memory if connector_runbook_assignments_memory is not None else []
    )
    _connector_postmortems_memory = connector_postmortems_memory if connector_postmortems_memory is not None else []
    _connector_postmortem_templates_memory = (
        connector_postmortem_templates_memory if connector_postmortem_templates_memory is not None else []
    )
    _connector_postmortem_closure_policies_memory = (
        connector_postmortem_closure_policies_memory if connector_postmortem_closure_policies_memory is not None else []
    )
    _connector_postmortem_closure_requests_memory = (
        connector_postmortem_closure_requests_memory if connector_postmortem_closure_requests_memory is not None else []
    )
    _connector_postmortem_action_item_escalations_memory = (
        connector_postmortem_action_item_escalations_memory
        if connector_postmortem_action_item_escalations_memory is not None
        else []
    )
    _connector_postmortem_escalation_routing_policies_memory = (
        connector_postmortem_escalation_routing_policies_memory
        if connector_postmortem_escalation_routing_policies_memory is not None
        else []
    )
    _connector_postmortem_escalation_cadence_policies_memory = (
        connector_postmortem_escalation_cadence_policies_memory
        if connector_postmortem_escalation_cadence_policies_memory is not None
        else []
    )
    _workflow_templates_memory = workflow_templates_memory if workflow_templates_memory is not None else []
    _workflow_webhook_events_memory = (
        workflow_webhook_events_memory if workflow_webhook_events_memory is not None else []
    )
    runtime = WorkflowRuntime(
        approval_policies=_approval_policies_memory,
        approval_requests=_approval_requests_memory,
        connector_escalation_events=_connector_escalation_events_memory,
        connector_escalation_rules=_connector_escalation_rules_memory,
        connector_maintenance_windows=_connector_maintenance_windows_memory,
        connector_policy_templates=_connector_policy_templates_memory,
        connector_postmortem_action_item_escalations=_connector_postmortem_action_item_escalations_memory,
        connector_postmortem_closure_policies=_connector_postmortem_closure_policies_memory,
        connector_postmortem_closure_requests=_connector_postmortem_closure_requests_memory,
        connector_postmortem_escalation_cadence_policies=_connector_postmortem_escalation_cadence_policies_memory,
        connector_postmortem_escalation_routing_policies=_connector_postmortem_escalation_routing_policies_memory,
        connector_postmortem_templates=_connector_postmortem_templates_memory,
        connector_postmortems=_connector_postmortems_memory,
        connector_replay_queue=_connector_replay_queue_memory,
        connector_runbook_assignments=_connector_runbook_assignments_memory,
        connector_runbooks=_connector_runbooks_memory,
        connector_sla_alerts=_connector_sla_alerts_memory,
        connectors=_connectors_memory,
        lock=_lock,
        workflow_templates=_workflow_templates_memory,
        workflow_webhook_events=_workflow_webhook_events_memory,
        audit_log=audit_log_memory,
        enforce_rate_limit=enforce_rate_limit,
        workflow_executions=workflow_executions_memory,
        workflow_step_logs=workflow_step_logs_memory,
        workflows=workflows_memory,
    )
    workflow.register(router, runtime)
    toggle_workflow.register(router, runtime)
    list_workflow_approval_policies.register(router, runtime)
    list_maintenance_windows.register(router, runtime)
    assign_runbook_operator.register(router, runtime)
    list_connector_postmortems.register(router, runtime)
    decide_postmortem_closure_request.register(router, runtime)
    process_postmortem_escalation_cadence.register(router, runtime)
    owner_workload.register(router, runtime)
    coverage_gaps.register(router, runtime)
    stability_score.register(router, runtime)
    readiness_forecast.register(router, runtime)
    owner_relief_plan.register(router, runtime)
    ownership_stability_forecast.register(router, runtime)
    continuity_readiness_index.register(router, runtime)
    remediation_balance_index.register(router, runtime)
    remediation_pressure_index.register(router, runtime)
    escalation_steadiness_index.register(router, runtime)
    escalation_alignment_index.register(router, runtime)
    escalation_focus_index.register(router, runtime)
    remediation_orchestration_forecast.register(router, runtime)
    escalation_harmony_index.register(router, runtime)
    remediation_cadence_forecast.register(router, runtime)
    connector_health_check.register(router, runtime)
    replay_connector_queue_item.register(router, runtime)
    return router
