"""Social HTTP adapters: get publishing queue."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import ConditionalRuleEvaluationRequest
from ....domains.social.schemas import LinkShortenRequest
from ..constants import AuthDep
from ..constants import SCHEDULED_POST_NOT_FOUND
from ..extended_schemas import CalendarAutoPostRequest
from ..extended_schemas import CalendarMoveRequest
from ..extended_schemas import QueueReorderRequest
from ..operations.list_hashtag_groups import operation_evaluate_conditional_rules
from ..operations.list_hashtag_groups import operation_get_publishing_queue
from ..operations.list_hashtag_groups import operation_list_calendar_events
from ..operations.list_hashtag_groups import operation_list_short_links
from ..operations.list_hashtag_groups import operation_move_calendar_event
from ..operations.list_hashtag_groups import operation_reorder_queue
from ..operations.list_hashtag_groups import operation_set_calendar_event_auto_post
from ..operations.list_hashtag_groups import operation_shorten_social_link
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/queue")
    def get_publishing_queue(
        auth: AuthDep, status: str = "scheduled", network: str | None = None, limit: int = 50
    ) -> dict[str, Any]:
        return operation_get_publishing_queue(st, router, auth, status, network, limit)

    @router.post("/social/queue/reorder")
    def reorder_queue(payload: QueueReorderRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_reorder_queue(st, router, payload, auth)

    @router.get("/social/calendar")
    def list_calendar_events(auth: AuthDep, month: int | None = None, year: int | None = None) -> dict[str, Any]:
        return operation_list_calendar_events(st, router, auth, month, year)

    @router.put("/social/calendar/{item_id}/move", responses={404: {"description": SCHEDULED_POST_NOT_FOUND}})
    def move_calendar_event(item_id: str, payload: CalendarMoveRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_move_calendar_event(st, router, item_id, payload, auth)

    @router.put("/social/calendar/{item_id}/auto-post", responses={404: {"description": SCHEDULED_POST_NOT_FOUND}})
    def set_calendar_event_auto_post(item_id: str, payload: CalendarAutoPostRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_set_calendar_event_auto_post(st, router, item_id, payload, auth)

    @router.post("/social/links/shorten")
    def shorten_social_link(payload: LinkShortenRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_shorten_social_link(st, router, payload, auth)

    @router.get("/social/links")
    def list_short_links(auth: AuthDep, limit: int = 100) -> dict[str, Any]:
        return operation_list_short_links(st, router, auth, limit)

    @router.post("/social/automation/conditions/evaluate")
    def evaluate_conditional_rules(payload: ConditionalRuleEvaluationRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_evaluate_conditional_rules(st, router, payload, auth)
