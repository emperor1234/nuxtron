"""Seo/Platform HTTP adapters beginning with local seo optimize."""

from .....deps import AuthContext
from .....deps import require_auth
from ..operations.local_seo_optimize import execute_growth_playbooks_analyze
from ..operations.local_seo_optimize import execute_international_multilingual_analyze
from ..operations.local_seo_optimize import execute_local_seo_optimize
from ..operations.local_seo_optimize import execute_multi_channel_activation_analyze
from ..operations.local_seo_optimize import execute_revenue_attribution_analyze
from ..operations.local_seo_optimize import execute_site_migration_analyze
from ..operations.local_seo_optimize import execute_trust_risk_governance_analyze
from ..operations.local_seo_optimize import execute_video_seo_optimize
from ..runtime import ContextRuntime
from ..schemas import GrowthPlaybooksReq
from ..schemas import InternationalMultilingualReq
from ..schemas import LocalSEOReq
from ..schemas import MultiChannelActivationReq
from ..schemas import RevenueAttributionReq
from ..schemas import SiteMigrationReq
from ..schemas import TrustRiskGovernanceReq
from ..schemas import VideoSEOReq
from fastapi import APIRouter
from fastapi import Depends
from typing import Annotated


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/local/optimize")
    async def local_seo_optimize(req: LocalSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_local_seo_optimize(runtime, req, auth)

    @router.post("/video/optimize")
    async def video_seo_optimize(req: VideoSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_video_seo_optimize(runtime, req, auth)

    @router.post("/international-multilingual/analyze")
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
