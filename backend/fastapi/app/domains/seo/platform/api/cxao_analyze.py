"""Seo/Platform HTTP adapters beginning with cxao analyze."""

from .....deps import AuthContext
from .....deps import require_auth
from ..operations.ahrefs_parity import execute_performance_browser_profiles
from ..operations.ecommerce_seo import execute_ecommerce_seo
from ..operations.ecommerce_seo import execute_performance_capabilities
from ..operations.ecommerce_seo import execute_performance_vendors
from ..operations.local_seo_optimize import execute_cxao_analyze
from ..operations.local_seo_optimize import execute_programmatic_seo
from ..operations.local_seo_optimize import execute_seo_ab_testing_analyze
from ..operations.save_analysis import execute_performance_test_locations
from ..runtime import ContextRuntime
from ..schemas import CxaoReq
from ..schemas import EcommerceSEOReq
from ..schemas import ProgrammaticSEOReq
from ..schemas import SeoAbTestingReq
from fastapi import APIRouter
from fastapi import Depends
from typing import Annotated


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/cxao/analyze")
    async def cxao_analyze(req: CxaoReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_cxao_analyze(runtime, req, auth)

    @router.post("/seo-ab-testing/analyze")
    async def seo_ab_testing_analyze(req: SeoAbTestingReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_seo_ab_testing_analyze(runtime, req, auth)

    @router.post("/programmatic/generate")
    async def programmatic_seo(req: ProgrammaticSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_programmatic_seo(runtime, req, auth)

    @router.post("/ecommerce/optimize")
    async def ecommerce_seo(req: EcommerceSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_ecommerce_seo(runtime, req, auth)

    @router.get("/performance/capabilities")
    async def performance_capabilities(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_capabilities(runtime, auth)

    @router.get("/performance/vendors")
    async def performance_vendors(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_vendors(runtime, auth)

    @router.get("/performance/test-locations")
    async def performance_test_locations(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_test_locations(runtime, auth)

    @router.get("/performance/browser-profiles")
    async def performance_browser_profiles(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_browser_profiles(runtime, auth)
