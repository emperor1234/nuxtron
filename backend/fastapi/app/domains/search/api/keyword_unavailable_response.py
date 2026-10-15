"""OpenAPI response metadata for unavailable provider-backed keyword features."""

from ....domains.seo.services.seo_keyword_research_service import KEYWORD_RESEARCH_UNAVAILABLE_DETAIL

KEYWORD_RESEARCH_501_RESPONSE = {
    "description": "This operation is unavailable until verified keyword provider data is connected.",
    "content": {"application/json": {"example": {"detail": KEYWORD_RESEARCH_UNAVAILABLE_DETAIL}}},
}
