"""Workflow HTTP operations: workflow."""

from ..constants import AuthDep
from ..constants import WORKFLOW_NOT_FOUND
from ..runtime import WorkflowRuntime
from ..schemas import WorkflowCreateRequest
from ..schemas import WorkflowGraphValidateRequest
from ..schemas import WorkflowTemplateCreateRequest
from ..schemas import WorkflowTemplateInstantiateRequest
from ..schemas import WorkflowWebhookTriggerRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.workflow import execute_create_workflow
from ..operations.workflow import execute_validate_workflow_graph
from ..operations.workflow import execute_create_workflow_template
from ..operations.workflow import execute_list_workflow_templates
from ..operations.workflow import execute_instantiate_workflow_template
from ..operations.workflow import execute_trigger_workflows_webhook
from ..operations.workflow import execute_list_workflows
from ..operations.workflow import execute_get_workflow


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.post("/workflows", summary="Create workflow", responses={422: {"description": "Invalid workflow graph."}})
    def create_workflow(payload: WorkflowCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_workflow(runtime, payload, auth)

    @router.post("/workflows/validate-graph", summary="Validate workflow graph and execution path")
    def validate_workflow_graph(payload: WorkflowGraphValidateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_validate_workflow_graph(runtime, payload, auth)

    @router.post(
        "/workflows/templates",
        summary="Create reusable workflow template",
        responses={422: {"description": "Invalid workflow template graph."}},
    )
    def create_workflow_template(payload: WorkflowTemplateCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_workflow_template(runtime, payload, auth)

    @router.get("/workflows/templates", summary="List workflow templates")
    def list_workflow_templates(
        auth: AuthDep, category: Annotated[str | None, Query(max_length=60)] = None
    ) -> dict[str, Any]:
        return execute_list_workflow_templates(runtime, auth, category)

    @router.post(
        "/workflows/templates/{template_id}/instantiate",
        summary="Instantiate workflow from template",
        responses={404: {"description": "Workflow template not found."}},
    )
    def instantiate_workflow_template(
        template_id: int, payload: WorkflowTemplateInstantiateRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_instantiate_workflow_template(runtime, template_id, payload, auth)

    @router.post(
        "/workflows/triggers/webhook",
        summary="Trigger workflows using webhook event payload",
        responses={422: {"description": "Unsupported webhook trigger type."}},
    )
    def trigger_workflows_webhook(payload: WorkflowWebhookTriggerRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_trigger_workflows_webhook(runtime, payload, auth)

    @router.get("/workflows", summary="List workflows")
    def list_workflows(
        auth: AuthDep,
        trigger_type: Annotated[str | None, Query(max_length=40)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_workflows(runtime, auth, trigger_type, limit, offset)

    @router.get("/workflows/{workflow_id}", responses={404: {"description": WORKFLOW_NOT_FOUND}})
    def get_workflow(workflow_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_get_workflow(runtime, workflow_id, auth)
