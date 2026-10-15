"""Seo/Platform use cases: local seo optimize."""

from datetime import UTC, datetime
from functools import partial
from typing import Annotated

from fastapi import Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from .....deps import AuthContext, require_auth
from .....domains.seo.services.seo_ab_testing_service import analyze_seo_ab_testing
from .....domains.seo.services.seo_cxao_service import analyze_cxao_experience
from .....domains.seo.services.seo_growth_playbooks_service import analyze_growth_playbooks
from .....domains.seo.services.seo_international_multilingual_service import (
    raise_international_multilingual_unavailable,
)
from .....domains.seo.services.seo_local_seo_service import raise_local_seo_unavailable
from .....domains.seo.services.seo_multi_channel_activation_service import analyze_multi_channel_activation
from .....domains.seo.services.seo_performance_service import raise_performance_unavailable
from .....domains.seo.services.seo_programmatic_service import raise_programmatic_seo_unavailable
from .....domains.seo.services.seo_site_migration_service import analyze_site_migration
from .....domains.seo.services.seo_video_seo_service import optimize_video_seo
from ..constants import (
    _CXAO_SYS,
    _GROWTH_PLAYBOOKS_SYS,
    _MULTI_CHANNEL_ACTIVATION_SYS,
    _SEO_AB_TESTING_SYS,
    _SITE_MIGRATION_SYS,
    _VIDEO_SYS,
)
from ..runtime import ContextRuntime
from ..schemas import (
    CxaoReq,
    GrowthPlaybooksReq,
    InternationalMultilingualReq,
    LocalSEOReq,
    MultiChannelActivationReq,
    PerformanceAuditReq,
    ProgrammaticSEOReq,
    RevenueAttributionReq,
    SeoAbTestingReq,
    SiteMigrationReq,
    TrustRiskGovernanceReq,
    VideoSEOReq,
)
from ..services import extract_waterfall as provider_ollama_json
from ..services.get_shared_job_store import _clean
from .save_analysis import helper_save_analysis
from .sync_job_store import helper_find_cached_analysis, helper_log


async def execute_local_seo_optimize(
    runtime: ContextRuntime, req: LocalSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Do not manufacture listing scores, search volumes, or citation evidence."""
    raise_local_seo_unavailable()


async def execute_video_seo_optimize(
    runtime: ContextRuntime, req: VideoSEOReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Optimize YouTube / video content: title, description, tags, chapters, schema."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:video", limit=20, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "video_seo", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "video_seo_optimize",
            {"title": req.title, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await optimize_video_seo(
        title=req.title,
        description=req.description,
        transcript=req.transcript,
        platform=req.platform,
        keywords=req.keywords,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_VIDEO_SYS,
        clean_text_fn=_clean,
    )
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "video_seo", payload, result
    )
    helper_log(runtime, auth.tenant_id, "video_seo_optimize", {"title": req.title, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_international_multilingual_analyze(
    runtime: ContextRuntime, req: InternationalMultilingualReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Reject server-derived readiness claims until verified locale evidence is connected."""
    raise_international_multilingual_unavailable()


async def execute_site_migration_analyze(
    runtime: ContextRuntime, req: SiteMigrationReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Assess SEO migration readiness, redirect planning quality, and launch risk controls."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:site_migration", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "site_migration", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "site_migration_analyze",
            {"source_domain": req.source_domain, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_site_migration(
        source_domain=req.source_domain,
        target_domain=req.target_domain,
        sample_urls=req.sample_urls,
        launch_window=req.launch_window,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_SITE_MIGRATION_SYS,
        clean_text_fn=_clean,
    )
    result["source_domain"] = req.source_domain
    result["target_domain"] = req.target_domain
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "site_migration", payload, result
    )
    helper_log(runtime, auth.tenant_id, "site_migration_analyze", {"source_domain": req.source_domain, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


_REVENUE_ATTRIBUTION_ANALYZE_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "This analysis endpoint does not read workspace conversion or touchpoint records. Generated pipeline values "
        "and revenue estimates are disabled; use the authenticated recorded-event report instead."
    ),
}


async def execute_revenue_attribution_analyze(
    runtime: ContextRuntime, req: RevenueAttributionReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Reject unsupported revenue estimates that are not derived from recorded workspace events."""
    raise HTTPException(status_code=501, detail=_REVENUE_ATTRIBUTION_ANALYZE_UNAVAILABLE)


async def execute_growth_playbooks_analyze(
    runtime: ContextRuntime, req: GrowthPlaybooksReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Automate growth playbook planning, sequencing, and KPI measurement."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:growth_playbooks", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "growth_playbooks", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "growth_playbooks_analyze",
            {"objective": req.objective, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_growth_playbooks(
        objective=req.objective,
        domain=req.domain,
        target_channels=req.target_channels,
        weekly_capacity_hours=req.weekly_capacity_hours,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_GROWTH_PLAYBOOKS_SYS,
        clean_text_fn=_clean,
    )
    result["objective"] = req.objective
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "growth_playbooks", payload, result
    )
    helper_log(runtime, auth.tenant_id, "growth_playbooks_analyze", {"objective": req.objective, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


_TRUST_RISK_GOVERNANCE_UNAVAILABLE = {
    "code": "NOT_IMPLEMENTED",
    "message": (
        "Verified policy inventories, control states, incident records, and auditable evidence are not connected. "
        "Governance/compliance scores, risk classifications, and recommendations are disabled; this API cannot "
        "certify a workspace's posture."
    ),
}


async def execute_trust_risk_governance_analyze(
    runtime: ContextRuntime, req: TrustRiskGovernanceReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Keep unsupported governance assessments fail-closed until verified evidence sources exist."""
    raise HTTPException(status_code=501, detail=_TRUST_RISK_GOVERNANCE_UNAVAILABLE)


async def execute_multi_channel_activation_analyze(
    runtime: ContextRuntime, req: MultiChannelActivationReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Plan cross-channel activation and closed-loop optimization across search, social, and lifecycle surfaces."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:multi_channel_activation", limit=10, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "multi_channel_activation", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "multi_channel_activation_analyze",
            {"campaign_name": req.campaign_name, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_multi_channel_activation(
        campaign_name=req.campaign_name,
        primary_offer=req.primary_offer,
        channels=req.channels,
        audience_segments=req.audience_segments,
        notes=req.notes,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_MULTI_CHANNEL_ACTIVATION_SYS,
        clean_text_fn=_clean,
    )
    result["campaign_name"] = req.campaign_name
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "multi_channel_activation", payload, result
    )
    helper_log(
        runtime,
        auth.tenant_id,
        "multi_channel_activation_analyze",
        {"campaign_name": req.campaign_name, "cached": False},
    )
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_cxao_analyze(
    runtime: ContextRuntime, req: CxaoReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Optimize conversational answer quality and user journey outcomes for assistant surfaces."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:cxao", limit=12, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(partial(helper_find_cached_analysis, runtime), auth.tenant_id, "cxao", payload)
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "cxao_analyze",
            {"assistant_surface": req.assistant_surface, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_cxao_experience(
        assistant_surface=req.assistant_surface,
        primary_intent=req.primary_intent,
        conversation_context=req.conversation_context,
        success_criteria=req.success_criteria,
        ai_model=req.ai_model,
        rag_enabled=req.rag_enabled,
        chat_ui_framework=req.chat_ui_framework,
        posthog_enabled=req.posthog_enabled,
        posthog_events=req.posthog_events,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_CXAO_SYS,
        clean_text_fn=_clean,
    )
    result["implementation_stack"] = {
        "ai_model": req.ai_model,
        "rag_enabled": req.rag_enabled,
        "chat_ui_framework": req.chat_ui_framework,
        "posthog_enabled": req.posthog_enabled,
        "posthog_events": req.posthog_events,
    }
    result["assistant_surface"] = req.assistant_surface
    result["primary_intent"] = req.primary_intent
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "cxao", payload, result
    )
    helper_log(runtime, auth.tenant_id, "cxao_analyze", {"assistant_surface": req.assistant_surface, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_seo_ab_testing_analyze(
    runtime: ContextRuntime, req: SeoAbTestingReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    """Design SEO + UX A/B tests with sample size guidance, guardrails, and measurement plans."""
    runtime.enforce_rate_limit(f"{auth.tenant_id}:seo:seo_ab_testing", limit=12, window_seconds=60)
    payload = req.model_dump()
    cached = await run_in_threadpool(
        partial(helper_find_cached_analysis, runtime), auth.tenant_id, "seo_ab_testing", payload
    )
    if cached is not None:
        helper_log(
            runtime,
            auth.tenant_id,
            "seo_ab_testing_analyze",
            {"url": req.url, "cached": True, "analysis_id": cached["id"]},
        )
        return {
            "analysis_id": cached["id"],
            "cached": True,
            **(cached["result"] if isinstance(cached["result"], dict) else {}),
        }
    result = await analyze_seo_ab_testing(
        url=req.url,
        hypothesis=req.hypothesis,
        primary_metric=req.primary_metric,
        variant_a=req.variant_a,
        variant_b=req.variant_b,
        test_duration_days=req.test_duration_days,
        notes=req.notes,
        feature_flag_provider=req.feature_flag_provider,
        experiment_platform=req.experiment_platform,
        ai_analyst_model=req.ai_analyst_model,
        variant_payloads=req.variant_payloads,
        ollama_json_fn=provider_ollama_json._ollama_json,
        system_prompt=_SEO_AB_TESTING_SYS,
        clean_text_fn=_clean,
    )
    result["implementation_stack"] = {
        "feature_flag_provider": req.feature_flag_provider,
        "experiment_platform": req.experiment_platform,
        "ai_analyst_model": req.ai_analyst_model,
        "variant_payload_count": len(req.variant_payloads),
    }
    result["url"] = req.url
    result["hypothesis"] = req.hypothesis
    result["analyzed_at"] = datetime.now(UTC).isoformat()
    analysis_id = await run_in_threadpool(
        partial(helper_save_analysis, runtime), auth.tenant_id, "seo_ab_testing", payload, result
    )
    helper_log(runtime, auth.tenant_id, "seo_ab_testing_analyze", {"url": req.url, "cached": False})
    return {"analysis_id": analysis_id, "cached": False, **result}


async def execute_programmatic_seo(
    _runtime: ContextRuntime, _req: ProgrammaticSEOReq, _auth: Annotated[AuthContext, Depends(require_auth)]
) -> None:
    """Reject synthetic server-side generation until evidence and publishing controls exist."""
    raise_programmatic_seo_unavailable()


async def execute_performance_audit(
    runtime: ContextRuntime, req: PerformanceAuditReq, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()


async def execute_performance_rum_summary(
    runtime: ContextRuntime, url: str, auth: Annotated[AuthContext, Depends(require_auth)]
):
    raise_performance_unavailable()
