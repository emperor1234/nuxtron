"""Seo/Platform HTTP adapters beginning with local seo optimize."""

from typing import Annotated

from fastapi import APIRouter, Depends

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_local_seo_service import LOCAL_SEO_501_RESPONSE
from ..operations.local_seo_optimize import (
    execute_growth_playbooks_analyze,
    execute_international_multilingual_analyze,
    execute_local_seo_optimize,
    execute_multi_channel_activation_analyze,
    execute_revenue_attribution_analyze,
    execute_site_migration_analyze,
    execute_trust_risk_governance_analyze,
    execute_video_seo_optimize,
)
from ..runtime import ContextRuntime
from ..schemas import (
    GrowthPlaybooksReq,
    InternationalMultilingualReq,
    LocalSEOReq,
    MultiChannelActivationReq,
    RevenueAttributionReq,
    SiteMigrationReq,
    TrustRiskGovernanceReq,
    VideoSEOReq,
)


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/local/optimize", status_code=501, response_model=None, responses={501: LOCAL_SEO_501_RESPONSE})
    async def local_seo_optimize(req: LocalSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_local_seo_optimize(runtime, req, auth)

    @router.post("/video/optimize")
    async def video_seo_optimize(req: VideoSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_video_seo_optimize(runtime, req, auth)

    @router.post(
        "/international-multilingual/analyze",
        responses={501: {"description": "Server-side locale analysis is unavailable until tenant-scoped crawl and reciprocal hreflang evidence are verified."}},
    )
    async def international_multilingual_analyze(
        req: InternationalMultilingualReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_international_multilingual_analyze(runtime, req, auth)

    @router.post("/site-migration/analyze")
    async def site_migration_analyze(req: SiteMigrationReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_site_migration_analyze(runtime, req, auth)

    @router.post("/revenue-attribution/analyze")
    async def revenue_attribution_analyze(
        req: RevenueAttributionReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_revenue_attribution_analyze(runtime, req, auth)

    @router.post("/growth-playbooks/analyze")
    async def growth_playbooks_analyze(req: GrowthPlaybooksReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_growth_playbooks_analyze(runtime, req, auth)

    @router.post("/trust-risk-governance/analyze")
    async def trust_risk_governance_analyze(
        req: TrustRiskGovernanceReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_trust_risk_governance_analyze(runtime, req, auth)

    @router.post("/multi-channel-activation/analyze")
    async def multi_channel_activation_analyze(
        req: MultiChannelActivationReq, auth: Annotated[AuthContext, Depends(require_auth)]
    ):
        return await execute_multi_channel_activation_analyze(runtime, req, auth)
