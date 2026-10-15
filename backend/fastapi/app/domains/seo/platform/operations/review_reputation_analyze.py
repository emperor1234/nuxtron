"""Seo/Platform use cases: review reputation analyze."""

import uuid
from datetime import UTC, datetime
from functools import partial
from typing import Annotated

from fastapi import Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_backlink_intelligence_service import analyze_backlink_intelligence
from .....domains.seo.services.seo_brand_voice_service import rewrite_brand_voice
from .....domains.seo.services.seo_content_creation_blogging_service import plan_content_creation_blogging
from .....domains.seo.services.seo_planner_service import default_planner_workflow, execute_planner
from .....domains.seo.services.seo_rank_tracking_service import raise_rank_tracking_unavailable
from .....domains.seo.services.seo_reviews_service import raise_review_reputation_unavailable
from ..constants import (
    _BACKLINK_INTELLIGENCE_SYS,
    _BRAND_VOICE_SYS,
    _CONTENT_CREATION_BLOGGING_SYS,
)
from ..runtime import ContextRuntime
from ..schemas import (
    BacklinkIntelligenceReq,
    BrandVoiceReq,
    ContentCreationBloggingReq,
    PlannerExecuteAllReq,
    PlannerExecuteReq,
    RankTrackingReq,
    ReviewReputationReq,
)
from ..services import extract_waterfall as provider_ollama_json
from ..services.get_shared_job_store import _clean
from .save_analysis import helper_list_analyses, helper_save_analysis
from .sync_job_store import helper_db_available, helper_find_cached_analysis, helper_get_analysis, helper_log


async def execute_review_reputation_analyze(
    runtime: ContextRuntime, req: ReviewReputationReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not invent review totals, ratings, themes, or provider coverage."""
    raise_review_reputation_unavailable()


async def execute_brand_voice_rewrite(
    runtime: ContextRuntime, req: BrandVoiceReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Rewrite content to match brand voice and tone while preserving SEO."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:brandvoice", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "brand_voice", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "brand_voice_rewrite",
            {"brand_name": req.brand_name, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await rewrite_brand_voice(
        content=req.content,
        brand_name=req.brand_name,
        tone=req.tone,
        target_audience=req.target_audience,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_BRAND_VOICE_SYS,
        clean_text_fn=_clean,
    )
    result["brand_name"] = req.brand_name
    result["tone"] = req.tone
    result["rewritten_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "brand_voice", payload, result
    )
    helper_log(
        runtime,
        auth.tenant_id,
        "brand_voice_rewrite",
        {"brand_name": req.brand_name, "tone": req.tone, "cached": False},
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_planner_execute(
    runtime: ContextRuntime, req: PlannerExecuteReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Create a review-only SEO workflow draft; this operation does not run tasks."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:planner_draft", limit=8, window_seconds=60)
    plan_id = str(uuid.uuid4())
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "planner_workflow_draft", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "planner_workflow_draft",
            {"goal": req.goal, "plan_id": plan_id, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    planner_meta = await execute_planner(
        goal=req.goal,
        domain=req.domain,
        primary_keyword=req.primary_keyword,
        market=req.market,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=(
            "You create review-only SEO workflow drafts from the user-provided brief. "
            "Do not claim to inspect live rankings, analytics, crawl data, or competitors; do not claim to execute work. "
            "Return strict JSON with concise priorities, potential risks, and next_actions only."
        ),
        clean_text_fn=_clean,
    )
    result = {
        "plan_id": plan_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "draft",
        "goal": req.goal,
        "domain": req.domain,
        "primary_keyword": req.primary_keyword,
        "market": req.market,
        "workflow": default_planner_workflow(),
        "priorities": planner_meta.get("priorities", []),
        "risks": planner_meta.get("risks", []),
        "analysis_mode": planner_meta.get("analysis_mode", "heuristic"),
        "ai_available": planner_meta.get("ai_available", False),
        "next_actions": planner_meta.get("next_actions") or [
            "Validate each suggestion against current search and site evidence before approving work.",
            "Assign an owner and review date to every action you choose to take.",
            "Use the linked tools to review or draft each step; this page does not publish or run tasks.",
        ],
    }
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "planner_workflow_draft", payload, result
    )
    helper_log(
        runtime,
        auth.tenant_id,
        "planner_workflow_draft",
        {"goal": req.goal, "plan_id": plan_id, "cached": False},
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_planner_execute_all_modules(
    _runtime: ContextRuntime, _req: PlannerExecuteAllReq, _auth: AuthContext
):
    """Reject orchestration until durable, authorized execution jobs exist."""
    raise HTTPException(
        status_code=501,
        detail={
            "code": "NOT_IMPLEMENTED",
            "message": (
                "Automated SEO module orchestration is not implemented. "
                "This endpoint did not dispatch or apply any work; use SEO Workflow Planner for a reviewable draft."
            ),
        },
    )


async def execute_backlink_intelligence_analyze(
    runtime: ContextRuntime, req: BacklinkIntelligenceReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Advanced backlink analysis with link graph, topical clusters, and Neo4j-ready intelligence."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:backlink_intelligence", limit=12, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "backlink_intelligence", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "backlink_intelligence_analyze",
            {"domain": req.domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_backlink_intelligence(
        domain=req.domain,
        competitor_domains=req.competitor_domains,
        link_analysis_depth=req.link_analysis_depth,
        include_topical_clusters=req.include_topical_clusters,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_BACKLINK_INTELLIGENCE_SYS,
        clean_text_fn=_clean,
        llm_timeout_seconds=16,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "backlink_intelligence", payload, result
    )
    helper_log(runtime, auth.tenant_id, "backlink_intelligence_analyze", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_rank_tracking_analyze(
    runtime: ContextRuntime, req: RankTrackingReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not present unverified model-generated positions as measured rankings."""
    raise_rank_tracking_unavailable()


async def execute_content_creation_blogging_plan(
    runtime: ContextRuntime, req: ContentCreationBloggingReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Comprehensive content strategy with blogging calendar, SEO briefs, and multimedia planning."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:content_creation_blogging", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "content_creation_blogging", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "content_creation_blogging_plan",
            {"topic": req.topic, "analysis_id": cached["id"], "cached": True},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await plan_content_creation_blogging(
        topic=req.topic,
        content_pillars=req.content_pillars,
        target_keywords=req.target_keywords,
        ai_model=req.ai_model,
        word_count_target=req.word_count_target,
        include_multimedia_plan=req.include_multimedia_plan,
        publication_frequency=req.publication_frequency,
        seo_brief=req.seo_brief,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_CONTENT_CREATION_BLOGGING_SYS,
        clean_text_fn=_clean,
        llm_timeout_seconds=16,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "content_creation_blogging", payload, result
    )
    helper_log(
        runtime,
        auth.tenant_id,
        "content_creation_blogging_plan",
        {"topic": req.topic, "ai_model": req.ai_model, "cached": False},
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_list_analyses(
    runtime: ContextRuntime,
    auth: Annotated[AuthContext, Depends(require_auth)],
    module: str | None = None,
    limit: int = 50,
):
    """List SEO analyses for the current tenant."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:list", limit=60, window_seconds=60)
    items = helper_list_analyses(runtime, auth.tenant_id, module, limit)
    return {
        "analyses": items,
        "total": len(items),
        "persistence": "postgres" if helper_db_available(runtime) else "memory",
    }


async def execute_get_analysis(
    runtime: ContextRuntime, analysis_id: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Get a specific SEO analysis by ID."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:get", limit=120, window_seconds=60)
    item = helper_get_analysis(runtime, auth.tenant_id, analysis_id)
    if item is not None:
        return item
    raise HTTPException(status_code=404, detail="Analysis not found.")
