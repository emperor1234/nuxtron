"""Seo/Platform use cases: review reputation analyze."""

from ..services import extract_waterfall as provider_ollama_json
from functools import partial
from .....deps import AuthContext
from .....deps import require_auth
from .....domains.seo.seo_module_registry import audit_seo_module_registry
from .....domains.seo.services.seo_backlink_intelligence_service import analyze_backlink_intelligence
from .....domains.seo.services.seo_brand_voice_service import rewrite_brand_voice
from .....domains.seo.services.seo_content_creation_blogging_service import plan_content_creation_blogging
from .....domains.seo.services.seo_planner_service import default_planner_workflow
from .....domains.seo.services.seo_planner_service import execute_planner
from .....domains.seo.services.seo_planner_service import execute_planner_all_modules
from .....domains.seo.services.seo_rank_tracking_service import analyze_rank_tracking
from .....domains.seo.services.seo_reviews_service import analyze_review_reputation
from ..constants import _BACKLINK_INTELLIGENCE_SYS
from ..constants import _BRAND_VOICE_SYS
from ..constants import _CONTENT_CREATION_BLOGGING_SYS
from ..constants import _RANK_TRACKING_SYS
from ..constants import _REVIEW_REPUTATION_SYS
from ..runtime import ContextRuntime
from ..schemas import BacklinkIntelligenceReq
from ..schemas import BrandVoiceReq
from ..schemas import ContentCreationBloggingReq
from ..schemas import PlannerExecuteAllReq
from ..schemas import PlannerExecuteReq
from ..schemas import RankTrackingReq
from ..schemas import ReviewReputationReq
from ..services.get_shared_job_store import _clean
from .save_analysis import helper_list_analyses
from .save_analysis import helper_list_modules
from .save_analysis import helper_save_analysis
from .sync_job_store import helper_db_available
from .sync_job_store import helper_find_cached_analysis
from .sync_job_store import helper_get_analysis
from .sync_job_store import helper_log
from datetime import UTC
from datetime import datetime
from fastapi import Depends
from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from typing import Annotated
from typing import Any
import uuid


async def execute_review_reputation_analyze(
    runtime: ContextRuntime, req: ReviewReputationReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Mine reviews, analyze sentiment, and generate reputation response workflows."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:reviews", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "reviews", payload)
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "review_reputation_analyze",
            {"brand": req.brand, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_review_reputation(
        brand=req.brand,
        reviews_text=req.reviews_text,
        platforms=req.platforms,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_REVIEW_REPUTATION_SYS,
        clean_text_fn=_clean,
    )
    result["brand"] = req.brand
    result["platforms"] = req.platforms
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "reviews", payload, result
    )
    helper_log(runtime, auth.tenant_id, "review_reputation_analyze", {"brand": req.brand, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


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
    """Create a chained SEO execution workflow across modules."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:planner", limit=8, window_seconds=60)
    plan_id = str(uuid.uuid4())
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "planner_execute", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "planner_execute",
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
        system_prompt="You are an SEO operations strategist. Respond only JSON with keys priorities, risks, and planner_score.",
        clean_text_fn=_clean,
    )
    result = {
        "plan_id": plan_id,
        "created_at": datetime.now(UTC).isoformat(),
        "status": "planned",
        "goal": req.goal,
        "domain": req.domain,
        "primary_keyword": req.primary_keyword,
        "market": req.market,
        "workflow": default_planner_workflow(),
        "priorities": planner_meta.get("priorities", []),
        "risks": planner_meta.get("risks", []),
        "planner_score": planner_meta.get("planner_score", 55),
        "analysis_mode": planner_meta.get("analysis_mode", "heuristic"),
        "ai_available": planner_meta.get("ai_available", False),
        "next_actions": [
            "Run keyword research and validate clusters",
            "Generate content brief and publish first draft",
            "Apply schema and technical fixes",
            "Monitor history and iterate weekly",
        ],
    }
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "planner_execute", payload, result
    )
    helper_log(runtime, auth.tenant_id, "planner_execute", {"goal": req.goal, "plan_id": plan_id, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_planner_execute_all_modules(
    runtime: ContextRuntime, req: PlannerExecuteAllReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """
    Build a full autonomous execution graph across the complete SEO module registry.
    This endpoint is intentionally strict: it validates registry integrity before plan creation.
    """
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:planner_all", limit=6, window_seconds=60)
    modules = helper_list_modules(runtime)
    audit = audit_seo_module_registry(modules)
    if audit.get("duplicate_keys") or audit.get("duplicate_routes") or audit.get("missing_required"):
        raise HTTPException(
            status_code=409, detail={"message": "SEO module registry failed integrity checks.", "audit": audit}
        )
    include_groups = {group.strip() for group in req.include_groups if str(group).strip()}
    exclude_keys = {key.strip() for key in req.exclude_module_keys if str(key).strip()}
    selected_modules: list[dict[str, Any]] = []
    for module in modules:
        key = str(module.get("key", "")).strip()
        group = str(module.get("group", "")).strip()
        if key in exclude_keys:
            continue
        if include_groups and group not in include_groups:
            continue
        selected_modules.append(module)
    selected_modules.sort(key=lambda m: (str(m.get("group", "")), str(m.get("key", ""))))
    run_id = str(uuid.uuid4())
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "planner_execute_all_modules", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "planner_execute_all_modules",
            {
                "run_id": run_id,
                "selected_module_count": len(selected_modules),
                "cached": True,
                "analysis_id": cached["id"],
            },
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    workflow: list[dict[str, Any]] = []
    for index, module in enumerate(selected_modules, start=1):
        workflow.append(
            {
                "step": index,
                "module_key": str(module.get("key", "")),
                "module_name": str(module.get("display_name", "")),
                "group": str(module.get("group", "")),
                "route_path": str(module.get("route_path", "")),
                "objective": str(module.get("description", "")),
                "autonomy_controls": (module.get("automation_features") or [])[:4],
                "analytics_controls": (module.get("analytics_features") or [])[:4],
                "enterprise_controls": (module.get("enterprise_features") or [])[:4],
            }
        )
    planner_meta = await execute_planner_all_modules(
        goal=req.goal,
        domain=req.domain,
        primary_keyword=req.primary_keyword,
        market=req.market,
        selected_module_count=len(selected_modules),
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt="You are a principal SEO operations architect. Output strict JSON only.",
        clean_text_fn=_clean,
    )
    result = {
        "run_id": run_id,
        "status": "planned",
        "created_at": datetime.now(UTC).isoformat(),
        "goal": req.goal,
        "domain": req.domain,
        "primary_keyword": req.primary_keyword,
        "market": req.market,
        "registry_audit": audit,
        "selected_module_count": len(selected_modules),
        "workflow": workflow,
        "mission": planner_meta.get("mission", "Autonomous full-funnel SEO execution"),
        "priorities": planner_meta.get("priorities", []),
        "risks": planner_meta.get("risks", []),
        "escalation_rules": planner_meta.get("escalation_rules", []),
        "planner_score": planner_meta.get("planner_score", 55),
        "analysis_mode": planner_meta.get("analysis_mode", "heuristic"),
        "ai_available": planner_meta.get("ai_available", False),
        "next_actions": [
            "Execute top-priority modules in parallel workers",
            "Continuously reconcile KPIs against target thresholds",
            "Escalate high-risk deviations to human approval queue",
        ],
    }
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "planner_execute_all_modules", payload, result
    )
    helper_log(
        runtime,
        auth.tenant_id,
        "planner_execute_all_modules",
        {"run_id": run_id, "selected_module_count": len(selected_modules), "goal": req.goal, "cached": False},
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


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
    """Time-series ranking analysis with volatility detection, competitor tracking, and forecasting."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:rank_tracking", limit=12, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "rank_tracking", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "rank_tracking_analyze",
            {"domain": req.domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_rank_tracking(
        domain=req.domain,
        tracked_keywords=req.tracked_keywords,
        historical_lookback_days=req.historical_lookback_days,
        include_competitor_tracking=req.include_competitor_tracking,
        competitor_domains=req.competitor_domains,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_RANK_TRACKING_SYS,
        clean_text_fn=_clean,
        llm_timeout_seconds=16,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "rank_tracking", payload, result
    )
    helper_log(runtime, auth.tenant_id, "rank_tracking_analyze", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


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
