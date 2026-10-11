"""Assistant HTTP adapters beginning with ira status."""

from ..constants import AuthDep
from ..operations.ira_response import execute_ira_frontier_env_template
from ..operations.ira_response import execute_ira_frontier_stack
from ..operations.ira_status import execute_ira_copilot_catalog
from ..operations.ira_status import execute_ira_copilot_health
from ..operations.ira_status import execute_ira_frontier_env_template_apply_draft
from ..operations.ira_status import execute_ira_frontier_plan
from ..operations.ira_status import execute_ira_playbook
from ..operations.ira_status import execute_ira_status
from ..runtime import ContextRuntime
from ..schemas import IRAFrontierEnvTemplateApplyRequest
from ..schemas import IRAFrontierPlanRequest
from fastapi import APIRouter
from typing import Any


def register(router: APIRouter, context_runtime: ContextRuntime):

    @router.get("/status")
    def ira_status(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_status(context_runtime, auth)

    @router.get("/playbook")
    def ira_playbook(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_playbook(context_runtime, auth)

    @router.get("/frontier/stack")
    def ira_frontier_stack(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_frontier_stack(context_runtime, auth)

    @router.post("/frontier/plan")
    def ira_frontier_plan(payload: IRAFrontierPlanRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_ira_frontier_plan(context_runtime, payload, auth)

    @router.get("/frontier/env-template")
    def ira_frontier_env_template(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_frontier_env_template(context_runtime, auth)

    @router.post(
        "/frontier/env-template/apply-draft",
        responses={
            422: {"description": "Invalid draft filename or template generation failure"},
            500: {"description": "Unable to write draft file"},
        },
    )
    def ira_frontier_env_template_apply_draft(
        payload: IRAFrontierEnvTemplateApplyRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return execute_ira_frontier_env_template_apply_draft(context_runtime, payload, auth)

    @router.get("/copilot/catalog")
    def ira_copilot_catalog(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_copilot_catalog(context_runtime, auth)

    @router.get("/copilot/health")
    def ira_copilot_health(auth: AuthDep) -> dict[str, Any]:
        return execute_ira_copilot_health(context_runtime, auth)
