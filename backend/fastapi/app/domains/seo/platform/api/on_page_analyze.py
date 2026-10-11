"""Seo/Platform HTTP adapters beginning with on page analyze."""

from .....deps import AuthContext
from .....deps import require_auth
from ..operations.ahrefs_parity import execute_generate_schema
from ..operations.ahrefs_parity import execute_generate_schema_async
from ..operations.ahrefs_parity import execute_get_async_job_status
from ..operations.ahrefs_parity import execute_on_page_analyze
from ..operations.ahrefs_parity import execute_on_page_analyze_async
from ..operations.ahrefs_parity import execute_schema_types
from ..operations.ahrefs_parity import execute_technical_audit
from ..operations.ahrefs_parity import execute_technical_audit_async
from ..runtime import ContextRuntime
from ..schemas import OnPageReq
from ..schemas import SchemaGenReq
from ..schemas import TechnicalAuditReq
from fastapi import APIRouter
from fastapi import Depends
from typing import Annotated


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/on-page/analyze")
    async def on_page_analyze(req: OnPageReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_on_page_analyze(runtime, req, auth)

    @router.post("/on-page/analyze/async")
    async def on_page_analyze_async(req: OnPageReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_on_page_analyze_async(runtime, req, auth)

    @router.post("/technical/audit")
    async def technical_audit(req: TechnicalAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_technical_audit(runtime, req, auth)

    @router.post("/technical/audit/async")
    async def technical_audit_async(req: TechnicalAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_technical_audit_async(runtime, req, auth)

    @router.get("/jobs/{job_id}")
    async def get_async_job_status(job_id: str, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_get_async_job_status(runtime, job_id, auth)

    @router.post("/schemas/generate")
    async def generate_schema(req: SchemaGenReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_generate_schema(runtime, req, auth)

    @router.post("/schemas/generate/async")
    async def generate_schema_async(req: SchemaGenReq, auth: Annotated[AuthContext, Depends(require_auth)]):
        return await execute_generate_schema_async(runtime, req, auth)

    @router.get("/schemas/types")
    async def schema_types():
        return await execute_schema_types()
