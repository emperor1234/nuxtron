"""Social HTTP adapters: update social review status."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import InfluencerAdvocacyBridgeRequest
from ....domains.social.schemas import InfluencerSearchRequest
from ....domains.social.schemas import InfluencerShortlistRequest
from ....domains.social.schemas import ReviewCaseCreateRequest
from ....domains.social.schemas import ReviewStatusRequest
from ..constants import AuthDep
from ..operations.bulk_social_inbox_action import operation_bridge_influencer_to_advocacy
from ..operations.bulk_social_inbox_action import operation_create_social_care_case
from ..operations.bulk_social_inbox_action import operation_list_social_advocacy_assets
from ..operations.bulk_social_inbox_action import operation_list_social_care_cases
from ..operations.bulk_social_inbox_action import operation_list_social_influencers
from ..operations.bulk_social_inbox_action import operation_search_social_influencers
from ..operations.bulk_social_inbox_action import operation_shortlist_social_influencer
from ..operations.bulk_social_inbox_action import operation_update_social_review_status
from fastapi import APIRouter
from typing import Any


def register(st: _SocialWorkspaceState, router: APIRouter):

    @router.patch("/social/reviews/{review_id}/status", responses={404: {"description": "Review not found"}})
    def update_social_review_status(review_id: int, payload: ReviewStatusRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_update_social_review_status(st, router, review_id, payload, auth)

    @router.get("/social/care/cases")
    def list_social_care_cases(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_care_cases(st, router, auth)

    @router.post("/social/care/cases", responses={404: {"description": "Review not found"}})
    def create_social_care_case(payload: ReviewCaseCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_create_social_care_case(st, router, payload, auth)

    @router.get("/social/influencers")
    def list_social_influencers(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_influencers(st, router, auth)

    @router.post("/social/influencers/search")
    def search_social_influencers(payload: InfluencerSearchRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_search_social_influencers(st, router, payload, auth)

    @router.post("/social/influencers/shortlist", responses={404: {"description": "Influencer not found"}})
    def shortlist_social_influencer(payload: InfluencerShortlistRequest, auth: AuthDep) -> dict[str, Any]:
        return operation_shortlist_social_influencer(st, router, payload, auth)

    @router.post(
        "/social/influencers/{influencer_id}/advocacy-asset", responses={404: {"description": "Influencer not found"}}
    )
    def bridge_influencer_to_advocacy(
        influencer_id: str, payload: InfluencerAdvocacyBridgeRequest, auth: AuthDep
    ) -> dict[str, Any]:
        return operation_bridge_influencer_to_advocacy(st, router, influencer_id, payload, auth)

    @router.get("/social/advocacy/assets")
    def list_social_advocacy_assets(auth: AuthDep) -> dict[str, Any]:
        return operation_list_social_advocacy_assets(st, router, auth)
