"""Explicit per-application workflow state; no module-level business stores."""

from dataclasses import dataclass
from collections.abc import Callable
from typing import Any


@dataclass
class WorkflowRuntime:
    """Shared adapters owned by one application instance, not one route module."""

    approval_policies: list[dict[str, Any]]
    approval_requests: list[dict[str, Any]]
    connector_escalation_events: list[dict[str, Any]]
    connector_escalation_rules: list[dict[str, Any]]
    connector_maintenance_windows: list[dict[str, Any]]
    connector_policy_templates: list[dict[str, Any]]
    connector_postmortem_action_item_escalations: list[dict[str, Any]]
    connector_postmortem_closure_policies: list[dict[str, Any]]
    connector_postmortem_closure_requests: list[dict[str, Any]]
    connector_postmortem_escalation_cadence_policies: list[dict[str, Any]]
    connector_postmortem_escalation_routing_policies: list[dict[str, Any]]
    connector_postmortem_templates: list[dict[str, Any]]
    connector_postmortems: list[dict[str, Any]]
    connector_replay_queue: list[dict[str, Any]]
    connector_runbook_assignments: list[dict[str, Any]]
    connector_runbooks: list[dict[str, Any]]
    connector_sla_alerts: list[dict[str, Any]]
    connectors: list[dict[str, Any]]
    lock: Any
    workflow_templates: list[dict[str, Any]]
    workflow_webhook_events: list[dict[str, Any]]
    audit_log: list[dict[str, Any]]
    enforce_rate_limit: Callable[[str, int, int], None]
    workflow_executions: list[dict[str, Any]]
    workflow_step_logs: list[dict[str, Any]]
    workflows: list[dict[str, Any]]
