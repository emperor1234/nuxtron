"""Social HTTP adapters: get competitor insights."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import CompetitorTrackRequest
from ....domains.social.schemas import ListeningAlertDismissRequest
from ....domains.social.schemas import ListeningKeywordRequest
from ..constants import AuthDep
from ..operations.get_competitor_insights import operation_create_listening_keyword
from ..operations.get_competitor_insights import operation_delete_listening_keyword
from ..operations.get_competitor_insights import operation_dismiss_listening_alert
from ..operations.get_competitor_insights import operation_get_competitor_insights
from ..operations.get_competitor_insights import operation_get_listening_sentiment
from ..operations.get_competitor_insights import operation_list_listening_keywords
from ..operations.get_competitor_insights import operation_list_listening_mentions
from ..operations.get_competitor_insights import operation_track_competitor
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.get("/social/competitors/insights")
    def get_competitor_insights(auth: AuthDep) -> list[dict[str, Any]]:
        return operation_get_competitor_insights(st, router, auth)

    @router.post("/social/competitors/track")
    def track_competitor(payload: CompetitorTrackRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_track_competitor(st, router, payload, auth)

    @router.get("/social/listening/keywords")
    def list_listening_keywords(auth: AuthDep) -> dict[str, Any]:
        return operation_list_listening_keywords(st, router, auth)

    @router.post("/social/listening/keywords")
    def create_listening_keyword(payload: ListeningKeywordRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_listening_keyword(st, router, payload, auth)

    @router.delete("/social/listening/keywords/{keyword_id}", responses={404: {"description": "Keyword not found"}})
    def delete_listening_keyword(keyword_id: int, auth: AuthDep) -> dict[str, Any]:
        return operation_delete_listening_keyword(st, router, keyword_id, auth)

    @router.get("/social/listening/mentions")
    def list_listening_mentions(crisis_only: bool = False, *, auth: AuthDep) -> dict[str, Any]:
        return operation_list_listening_mentions(st, router, crisis_only, auth=auth)

    @router.patch(
        "/social/listening/mentions/{mention_id}/dismiss", responses={404: {"description": "Mention not found"}}
    )
    def dismiss_listening_alert(
        mention_id: int, payload: ListeningAlertDismissRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return operation_dismiss_listening_alert(st, router, mention_id, payload, auth)

    @router.get("/social/listening/sentiment")
    def get_listening_sentiment(auth: AuthDep) -> dict[str, Any]:
        return operation_get_listening_sentiment(st, router, auth)
