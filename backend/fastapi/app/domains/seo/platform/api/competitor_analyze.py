"""Seo/Platform HTTP adapters beginning with competitor analyze."""

from .....deps import AuthContext
from .....deps import require_auth
from ..operations.performance_report_shared import execute_internal_linking_suggest
from ..operations.ux_conversion_audit import execute_analytics_reporting
from ..operations.ux_conversion_audit import execute_competitor_analyze
from ..operations.ux_conversion_audit import execute_content_auditor_analyze
from ..operations.ux_conversion_audit import execute_crawl_budget_analyze
from ..operations.ux_conversion_audit import execute_knowledge_graph_analyze
from ..operations.ux_conversion_audit import execute_news_discover_analyze
from ..operations.ux_conversion_audit import execute_realtime_monitor
from ..runtime import ContextRuntime
from ..schemas import CompetitorIntelReq
from ..schemas import ContentAuditorReq
from ..schemas import CrawlBudgetReq
from ..schemas import InternalLinkingReq
from ..schemas import KnowledgeGraphReq
from ..schemas import NewsDiscoverReq
from ..schemas import PlannerExecuteReq
from ..schemas import RealtimeMonitoringReq
from fastapi import APIRouter
from fastapi import Depends
from typing import Annotated


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post(
        "/competitor/analyze",
        responses={501: {"description": "Verified SERP and competitor evidence sources are not connected."}},
    )
    async def competitor_analyze(req: CompetitorIntelReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_competitor_analyze(runtime, req, auth)

    @router.post("/realtime/monitor")
    async def realtime_monitor(req: RealtimeMonitoringReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_realtime_monitor(runtime, req, auth)

    @router.post("/content-auditor/analyze")
    async def content_auditor_analyze(req: ContentAuditorReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_content_auditor_analyze(runtime, req, auth)

    @router.post("/knowledge-graph/analyze")
    async def knowledge_graph_analyze(req: KnowledgeGraphReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_knowledge_graph_analyze(runtime, req, auth)

    @router.post("/internal-linking/suggest")
    async def internal_linking_suggest(req: InternalLinkingReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_internal_linking_suggest(runtime, req, auth)

    @router.post("/crawl-budget/analyze")
    async def crawl_budget_analyze(req: CrawlBudgetReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_crawl_budget_analyze(runtime, req, auth)

    @router.post("/news-discover/analyze")
    async def news_discover_analyze(req: NewsDiscoverReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_news_discover_analyze(runtime, req, auth)

    @router.post("/analytics/report")
    async def analytics_reporting(req: PlannerExecuteReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_analytics_reporting(runtime, req, auth)
