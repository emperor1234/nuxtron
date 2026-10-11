"""Social HTTP adapters: create social automation feed."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import AutomationFeedCreateRequest
from ....domains.social.schemas import AutomationFeedStatusRequest
from ....domains.social.schemas import AutomationFeedSyncRequest
from ....domains.social.schemas import AutomationRuleCreateRequest
from ....domains.social.schemas import AutomationRuleStatusRequest
from ....domains.social.schemas import PauseAllRequest
from ..constants import AuthDep
from ..operations.create_social_automation_rule import operation_create_social_automation_rule
from ..operations.create_social_automation_rule import operation_get_social_automation_queue
from ..operations.create_social_automation_rule import operation_list_social_inbox
from ..operations.create_social_automation_rule import operation_set_social_pause_all
from ..operations.create_social_automation_rule import operation_update_social_automation_rule
from ..operations.list_social_ai_agent_templates import operation_create_social_automation_feed
from ..operations.list_social_ai_agent_templates import operation_sync_social_automation_feed
from ..operations.list_social_ai_agent_templates import operation_update_social_automation_feed
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.post("/social/automation/feeds")
    def create_social_automation_feed(payload: AutomationFeedCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_social_automation_feed(st, router, payload, auth)

    @router.patch("/social/automation/feeds/{feed_id}", responses={404: {"description": "Automation feed not found"}})
    def update_social_automation_feed(
        feed_id: int, payload: AutomationFeedStatusRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return operation_update_social_automation_feed(st, router, feed_id, payload, auth)

    @router.post(
        "/social/automation/feeds/{feed_id}/sync", responses={404: {"description": "Automation feed not found"}}
    )
    def sync_social_automation_feed(feed_id: int, payload: AutomationFeedSyncRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_sync_social_automation_feed(st, router, feed_id, payload, auth)

    @router.post("/social/automation/rules")
    def create_social_automation_rule(payload: AutomationRuleCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_social_automation_rule(st, router, payload, auth)

    @router.patch("/social/automation/rules/{rule_id}", responses={404: {"description": "Automation rule not found"}})
    def update_social_automation_rule(
        rule_id: int, payload: AutomationRuleStatusRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return operation_update_social_automation_rule(st, router, rule_id, payload, auth)

    @router.get("/social/automation/queue")
    def get_social_automation_queue(auth: AuthDep) -> dict[str, Any]:
        return operation_get_social_automation_queue(st, router, auth)

    @router.post("/social/automation/pause-all")
    def set_social_pause_all(payload: PauseAllRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_set_social_pause_all(st, router, payload, auth)

    @router.get("/social/inbox")
    def list_social_inbox(unread_only: bool = False, *, auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_inbox(st, router, unread_only, auth=auth)
