"""Workflow HTTP operations: list workflow approval policies."""

from ..constants import AuthDep
from ..constants import EXECUTION_NOT_FOUND
from ..runtime import WorkflowRuntime
from ..schemas import ApprovalDecisionRequest
from ..schemas import ApprovalRequestCreateRequest
from ..schemas import WorkflowConnectorMaintenanceWindowRequest
from ..schemas import WorkflowConnectorTemplateApplyRequest
from ..schemas import WorkflowConnectorTemplateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.list_workflow_approval_policies import execute_list_workflow_approval_policies
from ..operations.list_workflow_approval_policies import execute_create_approval_request
from ..operations.list_workflow_approval_policies import execute_decide_approval_request
from ..operations.list_workflow_approval_policies import execute_list_approval_requests
from ..operations.list_workflow_approval_policies import execute_create_connector_template
from ..operations.list_workflow_approval_policies import execute_list_connector_templates
from ..operations.list_workflow_approval_policies import execute_apply_connector_template
from ..operations.list_workflow_approval_policies import execute_create_maintenance_window


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.get("/workflows/approval-policies", summary="List workflow approval policies")
    def list_workflow_approval_policies(auth: AuthDep) -> dict[str, Any]:
        return execute_list_workflow_approval_policies(runtime, auth)

    @router.post("/workflows/approval-requests", summary="Create manual approval request for workflow execution")
    def create_approval_request(payload: ApprovalRequestCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_approval_request(runtime, payload, auth)

    @router.post(
        "/workflows/approval-requests/{request_id}/decision", responses={404: {"description": EXECUTION_NOT_FOUND}}
    )
    def decide_approval_request(request_id: int, payload: ApprovalDecisionRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_decide_approval_request(runtime, request_id, payload, auth)

    @router.get("/workflows/approval-requests", summary="List workflow approval requests")
    def list_approval_requests(auth: AuthDep, limit: Annotated[int, Query(ge=1, le=200)] = 50) -> dict[str, Any]:
        return execute_list_approval_requests(runtime, auth, limit)

    @router.post("/workflow-connector-templates", summary="Create connector reliability template")
    def create_connector_template(payload: WorkflowConnectorTemplateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_connector_template(runtime, payload, auth)

    @router.get("/workflow-connector-templates", summary="List connector reliability templates")
    def list_connector_templates(auth: AuthDep) -> dict[str, Any]:
        return execute_list_connector_templates(runtime, auth)

    @router.post(
        "/workflow-connector-templates/{template_id}/apply", summary="Apply reliability template to connectors"
    )
    def apply_connector_template(
        template_id: int, payload: WorkflowConnectorTemplateApplyRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_apply_connector_template(runtime, template_id, payload, auth)

    @router.post("/workflow-connector-maintenance-windows", summary="Create connector maintenance window")
    def create_maintenance_window(payload: WorkflowConnectorMaintenanceWindowRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_maintenance_window(runtime, payload, auth)
