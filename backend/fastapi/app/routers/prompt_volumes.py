"""Prompt Volumes API Routes.

REST endpoints for keyword tracking and analysis
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

from backend.fastapi.app.deps import AuthContext, require_auth
from backend.fastapi.app.persistence.ai_visibility_store import get_ai_visibility_store
from backend.fastapi.app.prompt_volumes.core import (
    KeywordType,
    PromptVolumesCollector,
    prompt_volumes_collector,
)
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter(prefix='/api/v1/prompt-volumes', tags=['Prompt Volumes'])
logger = logging.getLogger(__name__)

def _collector_from_store(
    tenant_id: str,
    period_start: datetime,
    period_end: datetime,
    brand_name: str | None = None,
) -> PromptVolumesCollector:
    store = get_ai_visibility_store()
    collector = PromptVolumesCollector()  # type: ignore[no-untyped-call]
    events = store.get_prompt_events(
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
        brand_name=brand_name,
    )
    for event in events:
        observed_at = datetime.fromisoformat(str(event.get('observed_at_iso') or datetime.now(UTC).isoformat()).replace('Z', '+00:00'))
        collector.record_prompt(
            tenant_id=tenant_id,
            keyword=str(event.get('keyword') or ''),
            sources=[str(source) for source in list(event.get('sources') or [])],
            brand_name=str(event.get('brand_name') or ''),
            context=str(event.get('context') or '') or None,
            observed_at=observed_at,
        )
    return collector

@router.post("/record-prompt")
async def record_prompt(
    keyword: Annotated[str, Query(min_length=1)],
    sources: Annotated[list[str], Query(min_length=1)],
    auth: Annotated[AuthContext, Depends(require_auth)],
    brand_name: Annotated[str | None, Query()] = None,
    context: Annotated[str | None, Query()] = None,
) -> dict:
    """Record a search prompt/keyword."""

    try:
        tenant_id = auth.tenant_id

        if not keyword or len(keyword.strip()) == 0:
            raise HTTPException(status_code=400, detail="keyword is required")

        if not sources or len(sources) == 0:
            raise HTTPException(status_code=400, detail="sources is required")

        prompt_volumes_collector.record_prompt(
            tenant_id=tenant_id,
            keyword=keyword,
            sources=sources,
            brand_name=brand_name or "",
            context=context,
        )

        store = get_ai_visibility_store()
        keyword_type = KeywordType.INDUSTRY
        try:
            key = f"{tenant_id}:{keyword}"
            keyword_type = prompt_volumes_collector.volumes[key].keyword_type
            relevance = float(prompt_volumes_collector.volumes[key].relevance_score)
        except Exception:
            relevance = 0.5

        store.record_prompt_event(
            tenant_id=tenant_id,
            keyword=keyword,
            keyword_type=keyword_type.value,
            sources=sources,
            brand_name=brand_name or "",
            context=context,
            relevance_score=relevance,
            observed_at_iso=datetime.now(UTC).isoformat(),
        )

        return {
            "status": "recorded",
            "keyword": keyword,
            "sources": sources,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to record prompt.")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/analysis")
async def get_analysis(
    auth: Annotated[AuthContext, Depends(require_auth)],
    brand_name: str | None = None,
    days: int = Query(7, ge=1, le=90),
    top_n: int = Query(20, ge=5, le=50),
) -> dict:
    """Get prompt volume analysis."""
    try:
        tenant_id = auth.tenant_id
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=days)

        collector = _collector_from_store(tenant_id, period_start, period_end, brand_name or None)
        analysis = collector.get_analysis(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            brand_name=brand_name or "",
            top_n=top_n,
        )
        
        return {
            "period_days": days,
            "total_unique_keywords": analysis.total_unique_keywords,
            "total_prompt_volume": analysis.total_prompt_volume,
            "trending_count": analysis.trending_keywords_count,
            "question_keywords": analysis.question_keywords,
            "long_tail_keywords": analysis.long_tail_keywords,
            "branded_keywords": analysis.branded_keywords,
            "competitor_keywords": analysis.competitor_keywords,
            "trending": analysis.trending_keywords,
            "emerging": analysis.emerging_keywords,
            "by_source": analysis.keywords_by_source,
            "top_words": analysis.top_words,
        }
    
    except Exception as exc:
        logger.exception('Failed to get analysis.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/trending")
async def get_trending_keywords(
    auth: Annotated[AuthContext, Depends(require_auth)],
    limit: int = Query(20, le=50),
) -> dict:
    """Get currently trending keywords."""
    try:
        tenant_id = auth.tenant_id
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=7)

        collector = _collector_from_store(tenant_id, period_start, period_end, None)
        analysis = collector.get_analysis(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            top_n=limit,
        )
        
        return {
            "trending": analysis.trending_keywords[:limit],
            "count": len(analysis.trending_keywords),
        }
    
    except Exception as exc:
        logger.exception('Failed to get trending keywords.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/opportunities")
async def get_opportunities(
    auth: Annotated[AuthContext, Depends(require_auth)],
    brand_name: str | None = None,
    min_volume: int = Query(10, ge=1),
    limit: int = Query(50, le=100),
) -> dict:
    """Get keyword opportunities (trending, not yet optimized for)."""
    try:
        tenant_id = auth.tenant_id
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=90)
        collector = _collector_from_store(tenant_id, period_start, period_end, brand_name or None)
        opportunities = collector.get_opportunities(
            tenant_id=tenant_id,
            brand_name=brand_name or "",
            min_volume=min_volume,
        )
        
        return {
            "opportunities": opportunities[:limit],
            "count": len(opportunities),
        }
    
    except Exception as exc:
        logger.exception('Failed to get opportunities.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/by-type/{keyword_type}")
async def get_by_type(
    keyword_type: str,
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, le=50),
) -> dict:
    """Get keywords by type."""
    try:
        tenant_id = auth.tenant_id
        # Validate keyword type
        try:
            ktype = KeywordType(keyword_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid keyword_type. Must be one of: {', '.join([kt.value for kt in KeywordType])}"
            )
        
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=days)

        collector = _collector_from_store(tenant_id, period_start, period_end, None)
        analysis = collector.get_analysis(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            top_n=limit,
        )
        
        # Return appropriate list based on type
        if ktype == KeywordType.QUESTION:
            keywords = analysis.question_keywords
        elif ktype == KeywordType.LONG_TAIL:
            keywords = analysis.long_tail_keywords
        elif ktype == KeywordType.BRANDED:
            keywords = analysis.branded_keywords
        elif ktype == KeywordType.COMPETITOR:
            keywords = analysis.competitor_keywords
        else:
            keywords = []
        
        return {
            "type": keyword_type,
            "keywords": keywords[:limit],
            "count": len(keywords),
        }
    
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception('Failed to get keywords by type.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/sources")
async def get_by_source(
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: int = Query(7, ge=1, le=90),
) -> dict:
    """Get keyword volume breakdown by source."""
    try:
        tenant_id = auth.tenant_id
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=days)

        collector = _collector_from_store(tenant_id, period_start, period_end, None)
        analysis = collector.get_analysis(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )
        
        sources = [
            {"source": source, "volume": volume}
            for source, volume in sorted(
                analysis.keywords_by_source.items(),
                key=lambda x: x[1],
                reverse=True
            )
        ]
        
        return {
            "sources": sources,
            "total_volume": sum(s["volume"] for s in sources),
        }
    
    except Exception as exc:
        logger.exception('Failed to get keyword sources.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/top-words")
async def get_top_words(
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, le=100),
) -> dict:
    """Get most frequently appearing words in prompts."""
    try:
        tenant_id = auth.tenant_id
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=days)

        collector = _collector_from_store(tenant_id, period_start, period_end, None)
        analysis = collector.get_analysis(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            top_n=limit,
        )
        
        return {
            "top_words": analysis.top_words[:limit],
            "count": len(analysis.top_words),
        }
    
    except Exception as exc:
        logger.exception('Failed to get top words.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@router.get("/comparison")
async def compare_periods(
    auth: Annotated[AuthContext, Depends(require_auth)],
    days: int = Query(7, ge=1, le=90),
) -> dict:
    """Compare keyword volume between periods."""
    try:
        tenant_id = auth.tenant_id
        period_end = datetime.now(UTC)
        period_start = period_end - timedelta(days=days)
        previous_period_end = period_start
        previous_period_start = previous_period_end - timedelta(days=days)
        
        current_collector = _collector_from_store(tenant_id, period_start, period_end, None)
        current = current_collector.get_analysis(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
        )

        previous_collector = _collector_from_store(tenant_id, previous_period_start, previous_period_end, None)
        previous = previous_collector.get_analysis(
            tenant_id=tenant_id,
            period_start=previous_period_start,
            period_end=previous_period_end,
        )
        
        volume_change = current.total_prompt_volume - previous.total_prompt_volume
        volume_change_pct = (
            (volume_change / previous.total_prompt_volume * 100)
            if previous.total_prompt_volume > 0
            else (100 if volume_change > 0 else 0)
        )
        
        return {
            "current_period": {
                "volume": current.total_prompt_volume,
                "unique_keywords": current.total_unique_keywords,
            },
            "previous_period": {
                "volume": previous.total_prompt_volume,
                "unique_keywords": previous.total_unique_keywords,
            },
            "change": {
                "volume_absolute": volume_change,
                "volume_percent": round(volume_change_pct, 1),
                "trend": "up" if volume_change > 0 else "down" if volume_change < 0 else "stable",
            }
        }
    
    except Exception as exc:
        logger.exception('Failed to compare periods.')
        raise HTTPException(status_code=500, detail=str(exc)) from exc
