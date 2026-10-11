"""Workflow HTTP operations: list maintenance windows."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorEscalationAcknowledgeRequest
from ..schemas import WorkflowConnectorEscalationRuleRequest
from ..schemas import WorkflowConnectorRunbookRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.list_maintenance_windows import execute_list_maintenance_windows
from ..operations.list_maintenance_windows import execute_create_escalation_rule
from ..operations.list_maintenance_windows import execute_list_escalation_rules
from ..operations.list_maintenance_windows import execute_list_escalation_events
from ..operations.list_maintenance_windows import execute_acknowledge_escalation_event
from ..operations.list_maintenance_windows import execute_auto_resolve_escalations
from ..operations.list_maintenance_windows import execute_create_connector_runbook
from ..operations.list_maintenance_windows import execute_list_connector_runbooks


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get("/workflow-connector-maintenance-windows", summary="List connector maintenance windows")
    def list_maintenance_windows(auth: AuthDep) -> dict[str, Any]:
        return execute_list_maintenance_windows(runtime, auth)

    @router.post("/workflow-connector-escalation-rules", summary="Create connector escalation rule")
    def create_escalation_rule(payload: WorkflowConnectorEscalationRuleRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_escalation_rule(runtime, payload, auth)

    @router.get("/workflow-connector-escalation-rules", summary="List connector escalation rules")
    def list_escalation_rules(auth: AuthDep) -> dict[str, Any]:
        return execute_list_escalation_rules(runtime, auth)

    @router.get("/workflow-connector-escalation-events", summary="List connector escalation events")
    def list_escalation_events(auth: AuthDep, limit: Annotated[int, Query(ge=1, le=200)] = 100) -> dict[str, Any]:
        return execute_list_escalation_events(runtime, auth, limit)

    @router.post("/workflow-connector-escalation-events/{event_id}/acknowledge", summary="Acknowledge escalation event")
    def acknowledge_escalation_event(
        event_id: int, payload: WorkflowConnectorEscalationAcknowledgeRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_acknowledge_escalation_event(runtime, event_id, payload, auth)

    @router.post(
        "/workflow-connector-escalation-events/auto-resolve",
        summary="Auto-resolve escalations and alerts for recovered connectors",
    )
    def auto_resolve_escalations(auth: AuthDep) -> dict[str, Any]:
        return execute_auto_resolve_escalations(runtime, auth)

    @router.post("/workflow-connector-runbooks", summary="Create connector runbook")
    def create_connector_runbook(payload: WorkflowConnectorRunbookRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_connector_runbook(runtime, payload, auth)

    @router.get("/workflow-connector-runbooks", summary="List connector runbooks")
    def list_connector_runbooks(auth: AuthDep) -> dict[str, Any]:
        return execute_list_connector_runbooks(runtime, auth)
