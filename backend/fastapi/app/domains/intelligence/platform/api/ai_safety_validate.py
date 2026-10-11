"""Intelligence/Platform HTTP adapters beginning with ai safety validate."""

from __future__ import annotations
from ..constants import AuthDep
from ..operations.log import execute_ai_safety_audit_log
from ..operations.log import execute_ai_safety_validate
from ..operations.log import execute_create_prompt_version
from ..operations.log import execute_data_lineage
from ..operations.log import execute_list_models
from ..operations.log import execute_list_prompt_versions
from ..operations.log import execute_platform_metrics
from ..operations.log import execute_record_lineage_event
from ..runtime import ContextRuntime
from ..schemas import AIValidateRequest
from ..schemas import PromptVersionCreateRequest
from fastapi import APIRouter
from fastapi import Query
from typing import Any


def register(router: APIRouter, runtime: ContextRuntime):

    @router.post("/ai-safety/validate", summary="Module 32 — AI output safety & hallucination validation")
    async def ai_safety_validate(req: AIValidateRequest, auth: AuthDep) -> dict[str, Any]:
        return await execute_ai_safety_validate(runtime, req, auth)

    @router.get("/ai-safety/audit-log", summary="Module 32 — retrieve AI safety audit events for this tenant")
    def ai_safety_audit_log(auth: AuthDep, limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
        return execute_ai_safety_audit_log(runtime, auth, limit)

    @router.get("/models", summary="Module 33 — list active AI models and pool status")
    def list_models(auth: AuthDep) -> dict[str, Any]:
        return execute_list_models(runtime, auth)

    @router.post("/models/prompt-versions", summary="Module 33 — register a new prompt version")
    def create_prompt_version(req: PromptVersionCreateRequest, auth: AuthDep) -> dict[str, Any]:
        return execute_create_prompt_version(runtime, req, auth)

    @router.get("/models/prompt-versions", summary="Module 33 — list registered prompt versions")
    def list_prompt_versions(
        auth: AuthDep, module: str | None = Query(default=None), active_only: bool = Query(default=False)
    ) -> dict[str, Any]:
        return execute_list_prompt_versions(runtime, auth, module, active_only)

    @router.get("/data/lineage", summary="Module 34 — query data lineage events")
    def data_lineage(
        auth: AuthDep,
        source: str | None = Query(default=None, description="Filter by source system"),
        destination: str | None = Query(default=None, description="Filter by destination system"),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> dict[str, Any]:
        return execute_data_lineage(runtime, auth, source, destination, limit)

    @router.post("/data/lineage", summary="Module 34 — record a manual lineage event")
    def record_lineage_event(
        auth: AuthDep,
        source: str = Query(..., min_length=1, max_length=200),
        destination: str = Query(..., min_length=1, max_length=200),
        transformation: str = Query(default="manual", max_length=200),
    ) -> dict[str, Any]:
        return execute_record_lineage_event(runtime, auth, source, destination, transformation)

    @router.get("/metrics", summary="Module 35 — full platform metrics snapshot")
    def platform_metrics(auth: AuthDep) -> dict[str, Any]:
        return execute_platform_metrics(runtime, auth)
