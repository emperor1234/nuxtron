"""Seo/Platform use cases: ai article writer."""

from ..services import extract_waterfall as provider_ollama_json
from functools import partial
from .....deps import AuthContext
from .....deps import require_auth
from .....domains.seo.services.seo_aeo_service import analyze_aeo_optimize
from .....domains.seo.services.seo_aio_service import analyze_aio_score
from .....domains.seo.services.seo_content_writer_service import write_seo_article
from .....domains.seo.services.seo_daeo_service import analyze_daeo_readiness
from .....domains.seo.services.seo_eeat_service import analyze_eeat_score
from .....domains.seo.services.seo_entity_service import analyze_entity_seo
from .....domains.seo.services.seo_geo_service import analyze_geo_optimize
from .....domains.seo.services.seo_gxo_service import analyze_gxo_optimize
from .....domains.seo.services.seo_llmo_service import analyze_llmo_brand
from .....domains.seo.services.seo_msvo_service import analyze_msvo_visibility
from .....domains.seo.services.seo_peao_service import analyze_peao_forecast
from .....domains.seo.services.seo_sageo_service import analyze_sageo_plan
from .....domains.seo.services.seo_sxo_service import analyze_sxo_experience
from .....domains.seo.services.seo_vso_service import analyze_vso_optimize
from ..constants import _AEO_SYS
from ..constants import _AIO_SYS
from ..constants import _DAEO_SYS
from ..constants import _EEAT_SYS
from ..constants import _ENTITY_SYS
from ..constants import _GEO_SYS
from ..constants import _GXO_SYS
from ..constants import _LLMO_SYS
from ..constants import _MSVO_SYS
from ..constants import _PEAO_SYS
from ..constants import _SAGEO_SYS
from ..constants import _SXO_SYS
from ..constants import _VSO_SYS
from ..constants import _WRITER_SYS
from ..runtime import ContextRuntime
from ..schemas import AEOReq
from ..schemas import AIOReq
from ..schemas import AIWriterReq
from ..schemas import DaeoReq
from ..schemas import EEATReq
from ..schemas import EntityReq
from ..schemas import GEOReq
from ..schemas import GXOReq
from ..schemas import LLMOReq
from ..schemas import MsvoReq
from ..schemas import PeaoReq
from ..schemas import SXOReq
from ..schemas import SageoReq
from ..schemas import VSOReq
from ..services.get_shared_job_store import _clean
from .save_analysis import helper_save_analysis
from .sync_job_store import helper_find_cached_analysis
from .sync_job_store import helper_log
from fastapi import Depends
from starlette.concurrency import run_in_threadpool
from typing import Annotated


async def execute_ai_article_writer(
    runtime: ContextRuntime, req: AIWriterReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Generate a full SEO-optimized article (human-quality)."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:writer", limit=5, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "ai_writer", payload
    )
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "ai_writer", {"topic": req.topic, "analysis_id": cached["id"], "cached": True}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await write_seo_article(
        topic=req.topic,
        keywords=req.keywords,
        word_count=req.word_count,
        tone=req.tone,
        brief=req.brief,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_WRITER_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "ai_writer", payload, result
    )
    helper_log(
        runtime, auth.tenant_id, "ai_writer", {"topic": req.topic, "word_count": req.word_count, "cached": False}
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_geo_optimize(
    runtime: ContextRuntime, req: GEOReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Optimize content for citation by ChatGPT, Perplexity, Gemini, and AI Overviews."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:geo", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "geo", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "geo_optimize", {"topic": req.topic, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_geo_optimize(
        topic=req.topic,
        content=req.content,
        target_engines=req.target_engines,
        ai_model=req.ai_model,
        rag_enabled=req.rag_enabled,
        serp_context=req.serp_context,
        site_content_context=req.site_content_context,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_GEO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "geo", payload, result
    )
    helper_log(runtime, auth.tenant_id, "geo_optimize", {"topic": req.topic, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_aeo_optimize(
    runtime: ContextRuntime, req: AEOReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Optimize for featured snippets, PAA boxes, and voice answers."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:aeo", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "aeo", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "aeo_optimize", {"topic": req.topic, "analysis_id": cached["id"], "cached": True}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_aeo_optimize(
        topic=req.topic,
        content=req.content,
        target_questions=req.target_questions,
        entity_targets=req.entity_targets,
        schema_types=req.schema_types,
        use_openlens=req.use_openlens,
        use_playwright_validation=req.use_playwright_validation,
        retrieval_framework=req.retrieval_framework,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_AEO_SYS,
        clean_text_fn=_clean,
    )
    result["implementation_stack"] = {
        "openlens": req.use_openlens,
        "playwright": req.use_playwright_validation,
        "retrieval_framework": req.retrieval_framework,
        "schema_types": req.schema_types,
    }
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "aeo", payload, result
    )
    helper_log(runtime, auth.tenant_id, "aeo_optimize", {"topic": req.topic, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_aio_score(runtime: ContextRuntime, req: AIOReq, auth: Annotated[AuthContext, Depends(require_auth)]):
    """Score content for AI machine-readability and extractability."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:aio", limit=20, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "aio", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "aio_score", {"topic": req.topic, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_aio_score(
        topic=req.topic,
        content=req.content,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_AIO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "aio", payload, result
    )
    helper_log(runtime, auth.tenant_id, "aio_score", {"topic": req.topic, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_llmo_analyze(
    runtime: ContextRuntime, req: LLMOReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Analyze and optimize brand representation across AI models."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:llmo", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "llmo", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "llmo_analyze", {"brand": req.brand, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_llmo_brand(
        brand=req.brand,
        domain=req.domain,
        key_claims=req.key_claims,
        competitors=req.competitors,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_LLMO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "llmo", payload, result
    )
    helper_log(runtime, auth.tenant_id, "llmo_analyze", {"brand": req.brand, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_sageo_analyze(
    runtime: ContextRuntime, req: SageoReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Plan search-augmented generative SEO coverage for a topic."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:sageo", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "sageo", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "sageo_analyze", {"topic": req.topic, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_sageo_plan(
        topic=req.topic,
        search_intent=req.search_intent,
        source_material=req.source_material,
        target_engines=req.target_engines,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_SAGEO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "sageo", payload, result
    )
    helper_log(runtime, auth.tenant_id, "sageo_analyze", {"topic": req.topic, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_vso_optimize(
    runtime: ContextRuntime, req: VSOReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Optimize for Siri, Google Assistant, Alexa, and Cortana voice queries."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:vso", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "vso", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "vso_optimize", {"topic": req.topic, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_vso_optimize(
        topic=req.topic,
        content=req.content,
        local_area=req.local_area,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_VSO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "vso", payload, result
    )
    helper_log(runtime, auth.tenant_id, "vso_optimize", {"topic": req.topic, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_sxo_analyze(
    runtime: ContextRuntime, req: SXOReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Analyze search experience: dwell time, CTR, UX signals, pogo-sticking risk."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:sxo", limit=20, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "sxo", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "sxo_analyze", {"url": req.url, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_sxo_experience(
        url=req.url,
        content=req.content,
        keywords=req.keywords,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_SXO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "sxo", payload, result
    )
    helper_log(runtime, auth.tenant_id, "sxo_analyze", {"url": req.url, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_gxo_optimize(
    runtime: ContextRuntime, req: GXOReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Optimize for Google AI Overviews (SGE) citations and structured data."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:gxo", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "gxo", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "gxo_optimize", {"topic": req.topic, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_gxo_optimize(
        topic=req.topic,
        content=req.content,
        url=req.url,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_GXO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "gxo", payload, result
    )
    helper_log(runtime, auth.tenant_id, "gxo_optimize", {"topic": req.topic, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_eeat_score(
    runtime: ContextRuntime, req: EEATReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Score content on Experience, Expertise, Authoritativeness, and Trustworthiness."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:eeat", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "eeat", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "eeat_score", {"domain": req.domain, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_eeat_score(
        content=req.content,
        author_bio=req.author_bio,
        domain=req.domain,
        niche=req.niche,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_EEAT_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "eeat", payload, result
    )
    helper_log(runtime, auth.tenant_id, "eeat_score", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_entity_analyze(
    runtime: ContextRuntime, req: EntityReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Extract and analyze named entities for Knowledge Graph optimization."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:entity", limit=20, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "entity", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "entity_analyze", {"topic": req.topic, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_entity_seo(
        content=req.content,
        topic=req.topic,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_ENTITY_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "entity", payload, result
    )
    helper_log(runtime, auth.tenant_id, "entity_analyze", {"topic": req.topic, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_peao_analyze(
    runtime: ContextRuntime, req: PeaoReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Forecast ranking and algorithm volatility risks for a target keyword."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:peao", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "peao", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "peao_analyze", {"domain": req.domain, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_peao_forecast(
        domain=req.domain,
        primary_keyword=req.primary_keyword,
        recent_signals=req.recent_signals,
        forecast_horizon_days=req.forecast_horizon_days,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_PEAO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "peao", payload, result
    )
    helper_log(
        runtime, auth.tenant_id, "peao_analyze", {"domain": req.domain, "keyword": req.primary_keyword, "cached": False}
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_msvo_analyze(
    runtime: ContextRuntime, req: MsvoReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Assess visibility across search, AI, and owned distribution surfaces."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:msvo", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "msvo", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "msvo_analyze", {"brand": req.brand, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_msvo_visibility(
        brand=req.brand,
        topic=req.topic,
        target_surfaces=req.target_surfaces,
        owned_channels=req.owned_channels,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_MSVO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "msvo", payload, result
    )
    helper_log(runtime, auth.tenant_id, "msvo_analyze", {"brand": req.brand, "topic": req.topic, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_daeo_analyze(
    runtime: ContextRuntime, req: DaeoReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Assess decentralized answer engine readiness for self-hosted and federated discovery."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:daeo", limit=15, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "daeo", payload)
    if cached is not None:
        helper_log(
            runtime, auth.tenant_id, "daeo_analyze", {"domain": req.domain, "cached": True, "analysis_id": cached["id"]}
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_daeo_readiness(
        domain=req.domain,
        protocol_targets=req.protocol_targets,
        canonical_facts=req.canonical_facts,
        federation_notes=req.federation_notes,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_DAEO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "daeo", payload, result
    )
    helper_log(runtime, auth.tenant_id, "daeo_analyze", {"domain": req.domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}
