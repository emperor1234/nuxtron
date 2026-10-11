"""Workflow HTTP operations: toggle workflow."""

from ..constants import AuthDep
from ..constants import WORKFLOW_NOT_FOUND
from ..runtime import WorkflowRuntime
from ..schemas import ManualEnrollRequest
from ..schemas import WorkflowApprovalPolicyRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any
from ..operations.toggle_workflow import execute_toggle_workflow
from ..operations.toggle_workflow import execute_enroll_contact
from ..operations.toggle_workflow import execute_list_executions
from ..operations.toggle_workflow import execute_workflow_analytics
from ..operations.toggle_workflow import execute_workflow_production_readiness
from ..operations.toggle_workflow import execute_workflow_platform_completion_chart
from ..operations.toggle_workflow import execute_delete_workflow
from ..operations.toggle_workflow import execute_upsert_workflow_approval_policy


def register(router: APIRouter, runtime: WorkflowRuntime):

    @router.patch("/workflows/{workflow_id}/toggle", responses={404: {"description": WORKFLOW_NOT_FOUND}})
    def toggle_workflow(workflow_id: int, auth: AuthDep, active: Annotated[bool, Query()]) -> dict[str, Any]:
        return execute_toggle_workflow(runtime, workflow_id, auth, active)

    @router.post(
        "/workflows/{workflow_id}/enroll",
        responses={404: {"description": WORKFLOW_NOT_FOUND}, 409: {"description": "Workflow is not active."}},
    )
    def enroll_contact(workflow_id: int, payload: ManualEnrollRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_enroll_contact(runtime, workflow_id, payload, auth)

    @router.get("/workflows/{workflow_id}/executions", responses={404: {"description": WORKFLOW_NOT_FOUND}})
    def list_executions(
        workflow_id: int,
        auth: AuthDep,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_executions(runtime, workflow_id, auth, limit, offset)

    @router.get("/workflows/{workflow_id}/analytics", responses={404: {"description": WORKFLOW_NOT_FOUND}})
    def workflow_analytics(workflow_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_workflow_analytics(runtime, workflow_id, auth)

    @router.get("/workflow-platform/production-readiness", summary="Workflow production-readiness matrix")
    def workflow_production_readiness(auth: AuthDep) -> dict[str, Any]:
        return execute_workflow_production_readiness(runtime, auth)

    @router.get("/workflow-platform/completion-chart", summary="Workflow platform completion chart for dashboards")
    def workflow_platform_completion_chart(auth: AuthDep) -> dict[str, Any]:
        return execute_workflow_platform_completion_chart(runtime, auth)

    @router.delete("/workflows/{workflow_id}", responses={404: {"description": WORKFLOW_NOT_FOUND}})
    def delete_workflow(workflow_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_delete_workflow(runtime, workflow_id, auth)

    @router.post("/workflows/approval-policies", summary="Upsert workflow approval policy")
    def upsert_workflow_approval_policy(payload: WorkflowApprovalPolicyRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_upsert_workflow_approval_policy(runtime, payload, auth)
