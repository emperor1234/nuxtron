"""Workflow HTTP operations: assign runbook operator."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowConnectorPostmortemRequest
from ..schemas import WorkflowConnectorPostmortemTemplateApplyRequest
from ..schemas import WorkflowConnectorPostmortemTemplateRequest
from ..schemas import WorkflowConnectorRunbookAssignmentRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.assign_runbook_operator import execute_assign_runbook_operator
from ..operations.assign_runbook_operator import execute_list_runbook_assignments
from ..operations.assign_runbook_operator import execute_get_connector_incident_timeline
from ..operations.assign_runbook_operator import execute_get_connector_sli_trends
from ..operations.assign_runbook_operator import execute_create_postmortem_template
from ..operations.assign_runbook_operator import execute_list_postmortem_templates
from ..operations.assign_runbook_operator import execute_apply_postmortem_template
from ..operations.assign_runbook_operator import execute_create_connector_postmortem


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.post("/workflow-connector-runbooks/{runbook_id}/assignments", summary="Assign operator to runbook")
    def assign_runbook_operator(
        runbook_id: int, payload: WorkflowConnectorRunbookAssignmentRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_assign_runbook_operator(runtime, runbook_id, payload, auth)

    @router.get("/workflow-connector-runbooks/{runbook_id}/assignments", summary="List runbook assignments")
    def list_runbook_assignments(runbook_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_list_runbook_assignments(runtime, runbook_id, auth)

    @router.get(
        "/workflow-connectors/{connector_id}/incident-timeline", responses={404: {"description": EXECUTION_NOT_FOUND}}
    )
    def get_connector_incident_timeline(
        connector_id: int, auth: AuthDep, limit: Annotated[int, Query(ge=1, le=300)] = 100
    ) -> dict[str, Any]:
        return execute_get_connector_incident_timeline(runtime, connector_id, auth, limit)

    @router.get("/workflow-connectors/{connector_id}/sli-trends", responses={404: {"description": EXECUTION_NOT_FOUND}})
    def get_connector_sli_trends(
        connector_id: int, auth: AuthDep, buckets: Annotated[int, Query(ge=4, le=72)] = 12
    ) -> dict[str, Any]:
        return execute_get_connector_sli_trends(runtime, connector_id, auth, buckets)

    @router.post("/workflow-connectors/postmortem-templates", summary="Create postmortem template")
    def create_postmortem_template(
        payload: WorkflowConnectorPostmortemTemplateRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_create_postmortem_template(runtime, payload, auth)

    @router.get("/workflow-connectors/postmortem-templates", summary="List postmortem templates")
    def list_postmortem_templates(auth: AuthDep) -> dict[str, Any]:
        return execute_list_postmortem_templates(runtime, auth)

    @router.post("/workflow-connectors/postmortem-templates/{template_id}/apply", summary="Apply postmortem template")
    def apply_postmortem_template(
        template_id: int, payload: WorkflowConnectorPostmortemTemplateApplyRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_apply_postmortem_template(runtime, template_id, payload, auth)

    @router.post(
        "/workflow-connectors/{connector_id}/postmortems", responses={404: {"description": EXECUTION_NOT_FOUND}}
    )
    def create_connector_postmortem(
        connector_id: int, payload: WorkflowConnectorPostmortemRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_create_connector_postmortem(runtime, connector_id, payload, auth)
