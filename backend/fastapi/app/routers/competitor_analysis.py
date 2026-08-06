# pyright: reportUnusedFunction=false
"""
Competitor Analysis router — Ad spy, performance tracking, benchmarking.

Endpoints:
---------
POST   /competitors/add-domain              – Track competitor domain
GET    /competitors/list                    – List tracked competitors
POST   /competitors/{id}/ads                – Fetch competitor ads (ad spy)
GET    /competitors/{id}/performance        – Competitor ad performance
GET    /competitors/{id}/benchmarks         – Benchmark against competitors
"""

from __future__ import annotations

import os
import threading
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

router = APIRouter(prefix="/competitors", tags=["Competitor Analysis"])

# ---------------------------------------------------------------------------
# In-memory stores
# ---------------------------------------------------------------------------

_lock = threading.Lock()

# { tenant_id: [competitor, ...] }
_competitors: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [competitor_ad, ...] }
_competitor_ads: dict[str, list[dict[str, Any]]] = {}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class AddCompetitorRequest(BaseModel):
    domain: str = Field(..., description="Competitor domain (e.g., competitor.com)")
    name: str | None = Field(None, description="Competitor name")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(UTC).isoformat()

def _get_competitors(tid: str) -> list[dict[str, Any]]:
    with _lock:
        return _competitors.setdefault(tid, [])

def _get_competitor_ads(tid: str) -> list[dict[str, Any]]:
    with _lock:
        return _competitor_ads.setdefault(tid, [])

def _fetch_competitor_ads(domain: str, limit: int = 10) -> list[dict[str, Any]]:
    """Fetch competitor ads from a configured intelligence source."""
    endpoint = os.getenv("COMPETITOR_INTELLIGENCE_ENDPOINT", "").strip()
    if not endpoint:
        raise HTTPException(status_code=503, detail="Competitor intelligence source not configured")

    api_key = os.getenv("COMPETITOR_INTELLIGENCE_API_KEY", "").strip()
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    timeout_sec = float(os.getenv("COMPETITOR_INTELLIGENCE_HTTP_TIMEOUT_SECONDS", "15.0"))
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            response = client.get(endpoint, params={"domain": domain, "limit": limit}, headers=headers)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Competitor intelligence timeout") from exc
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=f"Competitor intelligence error: {exc}") from exc

    ads = payload.get("ads") if isinstance(payload, dict) else payload
    if not isinstance(ads, list):
        raise HTTPException(status_code=502, detail="Competitor intelligence response missing ads list")
    return ads

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/add-domain")
def add_competitor_domain(payload: AddCompetitorRequest, auth: AuthDep) -> dict[str, Any]:
    """Track a competitor domain for ad spying."""
    competitor = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "domain": payload.domain,
        "name": payload.name or payload.domain.split(".")[0].title(),
        "added_at": _now(),
        "status": "tracking",
        "ads_found": 0,
        "last_scan": None,
    }
    
    with _lock:
        _competitors.setdefault(auth.tenant_id, []).append(competitor)
    
    ads = _fetch_competitor_ads(payload.domain, limit=10)
    with _lock:
        _competitor_ads.setdefault(auth.tenant_id, []).extend([
            {**ad, "tenant_id": auth.tenant_id, "competitor_id": competitor["id"]}
            for ad in ads
        ])
    
    competitor["ads_found"] = len(ads)
    
    return {
        "success": True,
        "competitor": competitor,
        "ads_found": len(ads)
    }

@router.get("/list")
def list_competitors(auth: AuthDep) -> dict[str, Any]:
    """List all tracked competitors."""
    competitors = _get_competitors(auth.tenant_id)
    total_ads = len(_get_competitor_ads(auth.tenant_id))
    
    return {
        "competitors": competitors,
        "total": len(competitors),
        "total_ads_tracked": total_ads,
        "tenant_id": auth.tenant_id
    }

@router.get("/{competitor_id}/ads")
def get_competitor_ads(
    competitor_id: str,
    auth: AuthDep,
    limit: int = Query(50, ge=1, le=500),
    sort_by: str = Query("found_at", pattern="^(found_at|impressions|engagement_rate|cpc)$")
) -> dict[str, Any]:
    """Fetch competitor ad feed (ad spy)."""
    competitors = _get_competitors(auth.tenant_id)
    competitor = next((c for c in competitors if c["id"] == competitor_id), None)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    all_ads = _get_competitor_ads(auth.tenant_id)
    ads = [a for a in all_ads if a["competitor_id"] == competitor_id]
    
    # Sort
    if sort_by == "impressions":
        ads.sort(key=lambda a: a.get("estimated_impressions", 0), reverse=True)
    elif sort_by == "engagement_rate":
        ads.sort(key=lambda a: a.get("estimated_engagement_rate", 0), reverse=True)
    elif sort_by == "cpc":
        ads.sort(key=lambda a: a.get("estimated_cpc", 0))
    else:
        ads.sort(key=lambda a: a.get("found_at", ""), reverse=True)
    
    return {
        "competitor_domain": competitor["domain"],
        "competitor_name": competitor["name"],
        "ads": ads[-limit:],
        "total": len(ads),
        "top_performing": sorted(ads, key=lambda a: a.get("estimated_impressions", 0), reverse=True)[:3]
    }

@router.get("/{competitor_id}/performance")
def get_competitor_performance(competitor_id: str, auth: AuthDep) -> dict[str, Any]:
    """Get competitor ad performance metrics."""
    competitors = _get_competitors(auth.tenant_id)
    competitor = next((c for c in competitors if c["id"] == competitor_id), None)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    all_ads = _get_competitor_ads(auth.tenant_id)
    ads = [a for a in all_ads if a["competitor_id"] == competitor_id]
    
    total_impressions = sum(a.get("estimated_impressions", 0) for a in ads)
    avg_engagement = sum(a.get("estimated_engagement_rate", 0) for a in ads) / max(1, len(ads))
    avg_cpc = sum(a.get("estimated_cpc", 0) for a in ads) / max(1, len(ads))
    
    by_platform = {}
    for ad in ads:
        platform = ad.get("platform", "unknown")
        if platform not in by_platform:
            by_platform[platform] = {"count": 0, "impressions": 0}
        by_platform[platform]["count"] += 1
        by_platform[platform]["impressions"] += ad.get("estimated_impressions", 0)
    
    return {
        "competitor_domain": competitor["domain"],
        "competitor_name": competitor["name"],
        "total_ads_tracked": len(ads),
        "total_estimated_impressions": total_impressions,
        "average_engagement_rate": round(avg_engagement, 2),
        "average_cpc": round(avg_cpc, 2),
        "ads_by_platform": by_platform,
        "most_used_format": max(
            {a.get("format", "image") for a in ads},
            key=lambda f: sum(1 for a in ads if a.get("format") == f)
        ) if ads else "image",
        "top_cta": max(
            {a.get("cta", "Shop Now") for a in ads},
            key=lambda c: sum(1 for a in ads if a.get("cta") == c)
        ) if ads else "Shop Now",
    }

@router.get("/{competitor_id}/benchmarks")
def get_benchmarks(
    competitor_id: str,
    auth: AuthDep
) -> dict[str, Any]:
    """Benchmark against competitor — compare metrics."""
    competitors = _get_competitors(auth.tenant_id)
    competitor = next((c for c in competitors if c["id"] == competitor_id), None)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    
    all_ads = _get_competitor_ads(auth.tenant_id)
    competitor_ads = [a for a in all_ads if a["competitor_id"] == competitor_id]
    
    avg_engagement_competitor = sum(a.get("estimated_engagement_rate", 0) for a in competitor_ads) / max(1, len(competitor_ads))
    avg_cpc_competitor = sum(a.get("estimated_cpc", 0) for a in competitor_ads) / max(1, len(competitor_ads))
    
    # Simulate industry benchmarks
    industry_avg_engagement = 3.5
    industry_avg_cpc = 1.2
    
    competitor_vs_industry = {
        "engagement_difference": round(avg_engagement_competitor - industry_avg_engagement, 2),
        "engagement_percentile": min(100, max(0, int((avg_engagement_competitor / industry_avg_engagement) * 100))),
        "cpc_difference": round(avg_cpc_competitor - industry_avg_cpc, 2),
        "cpc_efficiency": round((industry_avg_cpc / max(0.1, avg_cpc_competitor)) * 100, 2),  # % efficiency
    }
    
    return {
        "competitor_domain": competitor["domain"],
        "competitor_metrics": {
            "average_engagement_rate": round(avg_engagement_competitor, 2),
            "average_cpc": round(avg_cpc_competitor, 2),
            "estimated_roas": round(1.5 + (avg_engagement_competitor / 100), 2),
        },
        "industry_benchmarks": {
            "average_engagement_rate": industry_avg_engagement,
            "average_cpc": industry_avg_cpc,
        },
        "competitive_advantage": competitor_vs_industry,
        "recommendation": (
            "Competitor is above industry average in engagement and CPC efficiency."
            if competitor_vs_industry["engagement_percentile"] > 50 else
            "You have an opportunity to outperform competitor's average engagement."
        )
    }
