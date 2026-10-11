"""Workflow HTTP operations: decide postmortem closure request."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorEscalationAcknowledgeAdminRequest
from ..schemas import WorkflowConnectorEscalationCadencePolicyRequest
from ..schemas import WorkflowConnectorEscalationRoutingPolicyRequest
from ..schemas import WorkflowConnectorOverdueEscalationProcessRequest
from ..schemas import WorkflowConnectorPostmortemClosureDecisionRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.decide_postmortem_closure_request import execute_decide_postmortem_closure_request
from ..operations.decide_postmortem_closure_request import execute_process_overdue_postmortem_action_items
from ..operations.decide_postmortem_closure_request import execute_list_postmortem_action_item_escalations
from ..operations.decide_postmortem_closure_request import execute_acknowledge_action_item_escalation
from ..operations.decide_postmortem_closure_request import execute_upsert_postmortem_escalation_routing_policy
from ..operations.decide_postmortem_closure_request import execute_get_postmortem_escalation_routing_policy
from ..operations.decide_postmortem_closure_request import execute_upsert_postmortem_escalation_cadence_policy
from ..operations.decide_postmortem_closure_request import execute_get_postmortem_escalation_cadence_policy


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.post(
        "/workflow-connectors/{connector_id}/postmortems/{postmortem_id}/closure-requests/{request_id}/decision",
        responses={404: {"description": EXECUTION_NOT_FOUND}},
    )
    def decide_postmortem_closure_request(
        connector_id: int,
        postmortem_id: int,
        request_id: int,
        payload: WorkflowConnectorPostmortemClosureDecisionRequest,
        auth: AuthDep,
    ) -> dict[str, Any]:
        return execute_decide_postmortem_closure_request(
            runtime, connector_id, postmortem_id, request_id, payload, auth
        )

    @router.post(
        "/workflow-connectors/postmortems/action-items/process-overdue",
        summary="Escalate overdue postmortem action items",
    )
    def process_overdue_postmortem_action_items(
        payload: WorkflowConnectorOverdueEscalationProcessRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_process_overdue_postmortem_action_items(runtime, payload, auth)

    @router.get(
        "/workflow-connectors/postmortems/action-items/escalations", summary="List overdue action-item escalations"
    )
    def list_postmortem_action_item_escalations(
        auth: AuthDep, limit: Annotated[int, Query(ge=1, le=500)] = 100
    ) -> dict[str, Any]:
        return execute_list_postmortem_action_item_escalations(runtime, auth, limit)

    @router.post(
        "/workflow-connectors/postmortems/action-items/escalations/{escalation_id}/acknowledge",
        summary="Acknowledge and close overdue action-item escalation",
    )
    def acknowledge_action_item_escalation(
        escalation_id: int, payload: WorkflowConnectorEscalationAcknowledgeAdminRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_acknowledge_action_item_escalation(runtime, escalation_id, payload, auth)

    @router.post(
        "/workflow-connectors/postmortems/escalation-routing-policy",
        summary="Upsert overdue action-item escalation routing policy",
    )
    def upsert_postmortem_escalation_routing_policy(
        payload: WorkflowConnectorEscalationRoutingPolicyRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_upsert_postmortem_escalation_routing_policy(runtime, payload, auth)

    @router.get(
        "/workflow-connectors/postmortems/escalation-routing-policy",
        summary="Get overdue action-item escalation routing policy",
    )
    def get_postmortem_escalation_routing_policy(auth: AuthDep) -> dict[str, Any]:
        return execute_get_postmortem_escalation_routing_policy(runtime, auth)

    @router.post(
        "/workflow-connectors/postmortems/escalation-cadence-policy",
        summary="Upsert escalation cadence policy for L1/L2/L3 handoffs",
    )
    def upsert_postmortem_escalation_cadence_policy(
        payload: WorkflowConnectorEscalationCadencePolicyRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_upsert_postmortem_escalation_cadence_policy(runtime, payload, auth)

    @router.get(
        "/workflow-connectors/postmortems/escalation-cadence-policy",
        summary="Get escalation cadence policy for L1/L2/L3 handoffs",
    )
    def get_postmortem_escalation_cadence_policy(auth: AuthDep) -> dict[str, Any]:
        return execute_get_postmortem_escalation_cadence_policy(runtime, auth)
