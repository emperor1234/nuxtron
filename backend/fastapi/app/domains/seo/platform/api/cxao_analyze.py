"""Seo/Platform HTTP adapters beginning with cxao analyze."""

from typing import Annotated

from fastapi import APIRouter, Depends

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_performance_service import PERFORMANCE_UNAVAILABLE_501_RESPONSE
from ..operations.ahrefs_parity import execute_performance_browser_profiles
from ..operations.ecommerce_seo import (
    execute_ecommerce_seo,
    execute_performance_capabilities,
    execute_performance_vendors,
)
from ..operations.local_seo_optimize import (
    execute_cxao_analyze,
    execute_programmatic_seo,
    execute_seo_ab_testing_analyze,
)
from ..operations.save_analysis import execute_performance_test_locations
from ..runtime import ContextRuntime
from ..schemas import CxaoReq, EcommerceSEOReq, ProgrammaticSEOReq, SeoAbTestingReq


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/cxao/analyze")
    async def cxao_analyze(req: CxaoReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_cxao_analyze(runtime, req, auth)

    @router.post("/seo-ab-testing/analyze")
    async def seo_ab_testing_analyze(req: SeoAbTestingReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_seo_ab_testing_analyze(runtime, req, auth)

    @router.post(
        "/programmatic/generate",
        responses={501: {"description": "Server-side generation is unavailable until tenant-scoped evidence and reviewable publishing controls exist."}},
    )
    async def programmatic_seo(req: ProgrammaticSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_programmatic_seo(runtime, req, auth)

    @router.post("/ecommerce/optimize")
    async def ecommerce_seo(req: EcommerceSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_ecommerce_seo(runtime, req, auth)

    @router.get("/performance/capabilities", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_capabilities(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_capabilities(runtime, auth)

    @router.get("/performance/vendors", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_vendors(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_vendors(runtime, auth)

    @router.get("/performance/test-locations", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_test_locations(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_test_locations(runtime, auth)

    @router.get("/performance/browser-profiles", status_code=501, response_model=None, responses=PERFORMANCE_UNAVAILABLE_501_RESPONSE)
    async def performance_browser_profiles(auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_performance_browser_profiles(runtime, auth)
