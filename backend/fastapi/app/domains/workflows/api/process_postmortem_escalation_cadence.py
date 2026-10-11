"""Workflow HTTP operations: process postmortem escalation cadence."""

from ..constants import AuthDep
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorEscalationCadenceProcessRequest
from ..schemas import WorkflowConnectorEscalationSuppressionProcessRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.process_postmortem_escalation_cadence import execute_process_postmortem_escalation_cadence
from ..operations.process_postmortem_escalation_cadence import execute_process_postmortem_escalation_suppression
from ..operations.process_postmortem_escalation_cadence import execute_get_postmortem_escalation_aging_dashboard
from ..operations.process_postmortem_escalation_cadence import execute_get_postmortem_action_item_breach_forecast
from ..operations.process_postmortem_escalation_cadence import execute_get_postmortem_escalation_priority_queue


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.post(
        "/workflow-connectors/postmortems/action-items/escalations/process-cadence",
        summary="Process L1/L2/L3 escalation cadence and re-page schedule",
    )
    def process_postmortem_escalation_cadence(
        payload: WorkflowConnectorEscalationCadenceProcessRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_process_postmortem_escalation_cadence(runtime, payload, auth)

    @router.post(
        "/workflow-connectors/postmortems/action-items/escalations/process-suppression",
        summary="Process suppressed escalations and reopen when still overdue",
    )
    def process_postmortem_escalation_suppression(
        payload: WorkflowConnectorEscalationSuppressionProcessRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_process_postmortem_escalation_suppression(runtime, payload, auth)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalations/aging-dashboard",
        summary="Escalation aging SLO dashboard",
    )
    def get_postmortem_escalation_aging_dashboard(
        auth: AuthDep,
        ack_slo_minutes: Annotated[int, Query(ge=5, le=2880)] = 60,
        lookback_hours: Annotated[int, Query(ge=1, le=720)] = 168,
    ) -> dict[str, Any]:
        return execute_get_postmortem_escalation_aging_dashboard(runtime, auth, ack_slo_minutes, lookback_hours)

    @router.get(
        "/workflow-connectors/postmortems/action-items/breach-forecast",
        summary="Forecast action items at risk of SLA breach",
    )
    def get_postmortem_action_item_breach_forecast(
        auth: AuthDep,
        window_hours: Annotated[int, Query(ge=1, le=168)] = 24,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> dict[str, Any]:
        return execute_get_postmortem_action_item_breach_forecast(runtime, auth, window_hours, limit)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalations/priority-queue",
        summary="Priority queue for overdue action-item escalations",
    )
    def get_postmortem_escalation_priority_queue(
        auth: AuthDep, limit: Annotated[int, Query(ge=1, le=500)] = 100, include_suppressed: bool = True
    ) -> dict[str, Any]:
        return execute_get_postmortem_escalation_priority_queue(runtime, auth, limit, include_suppressed)
