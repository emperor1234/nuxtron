"""Social HTTP adapters: list social ai agent templates."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import AIAgentWorkflowExecuteRequest
from ....domains.social.schemas import SocialIdeaCreateRequest
from ....domains.social.schemas import SocialIdeaQueueRequest
from ..constants import AuthDep
from ..operations.list_social_ai_agent_templates import operation_create_social_idea
from ..operations.list_social_ai_agent_templates import operation_execute_social_ai_agent_workflow
from ..operations.list_social_ai_agent_templates import operation_list_social_ai_agent_templates
from ..operations.list_social_ai_agent_templates import operation_list_social_automation_feeds
from ..operations.list_social_ai_agent_templates import operation_list_social_automation_rules
from ..operations.list_social_ai_agent_templates import operation_list_social_ideas
from ..operations.list_social_ai_agent_templates import operation_list_social_integration_catalog
from ..operations.list_social_ai_agent_templates import operation_queue_social_idea
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/ai-agents/templates")
    def list_social_ai_agent_templates(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_ai_agent_templates(st, router, auth)

    @router.get("/social/integrations/catalog")
    def list_social_integration_catalog(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_integration_catalog(st, router, auth)

    @router.post("/social/ai-agents/workflows/execute")
    def execute_social_ai_agent_workflow(payload: AIAgentWorkflowExecuteRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_execute_social_ai_agent_workflow(st, router, payload, auth)

    @router.get("/social/ideas")
    def list_social_ideas(status: str | None = None, *, auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_ideas(st, router, status, auth=auth)

    @router.post("/social/ideas")
    def create_social_idea(payload: SocialIdeaCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_social_idea(st, router, payload, auth)

    @router.post("/social/ideas/{idea_id}/queue", responses={404: {"description": "Idea not found"}})
    def queue_social_idea(idea_id: int, payload: SocialIdeaQueueRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_queue_social_idea(st, router, idea_id, payload, auth)

    @router.get("/social/automation/rules")
    def list_social_automation_rules(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_automation_rules(st, router, auth)

    @router.get("/social/automation/feeds")
    def list_social_automation_feeds(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_automation_feeds(st, router, auth)
