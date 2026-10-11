"""Crm HTTP adapters beginning with list workflow rules."""

from ..constants import AuthDep
from ..constants import PROJECT_NOT_FOUND
from ..constants import WORKFLOW_NOT_FOUND
from ..operations.create_workflow_rule import execute_create_custom_entity_type
from ..operations.create_workflow_rule import execute_create_project
from ..operations.create_workflow_rule import execute_list_custom_entity_types
from ..operations.create_workflow_rule import execute_list_projects
from ..operations.create_workflow_rule import execute_list_workflow_rules
from ..operations.create_workflow_rule import execute_projects_board
from ..operations.create_workflow_rule import execute_trigger_workflow_rule
from ..operations.create_workflow_rule import execute_update_project
from ..runtime import ContextRuntime
from ..schemas import CustomEntityTypeCreateRequest
from ..schemas import ProjectCreateRequest
from ..schemas import ProjectUpdateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Annotated
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.get("/crm/workflow-rules")
    def list_workflow_rules(auth: AuthDep) -> dict[str, Any]:
        return execute_list_workflow_rules(runtime, auth)

    @router.post("/crm/workflow-rules/{rule_id}/trigger", responses={404: {"description": WORKFLOW_NOT_FOUND}})
    def trigger_workflow_rule(rule_id: int, auth: AuthDep) -> dict[str, Any]:
        return execute_trigger_workflow_rule(runtime, rule_id, auth)

    @router.post("/crm/projects")
    def create_project(payload: ProjectCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_project(runtime, payload, auth)

    @router.get("/crm/projects")
    def list_projects(
        auth: AuthDep,
        status: Annotated[str | None, Query(max_length=40)] = None,
        owner: Annotated[str | None, Query(max_length=120)] = None,
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, Any]:
        return execute_list_projects(runtime, auth, status, owner, limit, offset)

    @router.patch("/crm/projects/{project_id}", responses={404: {"description": PROJECT_NOT_FOUND}})
    def update_project(project_id: int, payload: ProjectUpdateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_update_project(runtime, project_id, payload, auth)

    @router.get("/crm/projects/board")
    def projects_board(auth: AuthDep) -> dict[str, Any]:
        return execute_projects_board(runtime, auth)

    @router.post("/crm/custom-entities/types")
    def create_custom_entity_type(payload: CustomEntityTypeCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_custom_entity_type(runtime, payload, auth)

    @router.get("/crm/custom-entities/types")
    def list_custom_entity_types(auth: AuthDep) -> dict[str, Any]:
        return execute_list_custom_entity_types(runtime, auth)
