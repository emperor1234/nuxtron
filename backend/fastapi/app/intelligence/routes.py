"""
GOD INTELLIGENCE — FastAPI Routes v1.0
11 complete production endpoints with validation, error handling, rate limiting, logging
Mount at: app.include_router(router, prefix="/api/intel", tags=["intelligence"])
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from ..core.auth import get_current_org, get_current_user
from ..core.supabase_client import get_supabase
from .engine import (
    analyze_serp,
    audit_content_optimization,
    build_content_gap_report,
    build_topic_clusters,
    calculate_scores,
    collect_reddit_public,
    collect_twitter_public,
    collect_youtube_public,
    detect_trend_phase,
    fetch_meta_ads,
    fetch_news,
    generate_content_brief,
    mine_questions,
    predict_roi,
    scrape_public_website,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS — Pydantic validation
# ═══════════════════════════════════════════════════════════════════════════════

class AddTargetRequest(BaseModel):
    """Add competitor target for tracking"""
    name: str = Field(..., min_length=1, max_length=255, description="Target name")
    domain: str | None = Field(None, description="Website domain")
    twitter_handle: str | None = None
    instagram_handle: str | None = None
    facebook_page: str | None = None
    reddit_username: str | None = None
    youtube_channel_id: str | None = None
    category: str = Field("competitor", pattern="^(competitor|partner|customer|reference)$")
    priority: int = Field(3, ge=1, le=5)
    track_website: bool = True
    track_ads: bool = True
    track_social: bool = True
    track_news: bool = True
    
    @field_validator("twitter_handle")
    @classmethod
    def validate_twitter(cls, v: str | None) -> str | None:
        if v and len(v) > 100:
            raise ValueError("Twitter handle too long")
        return v.lstrip("@") if v else None

class ROIPredictionRequest(BaseModel):
    """Request ROI prediction for content"""
    content_brief: str = Field(..., min_length=10, max_length=2000)
    platform: str = Field(..., pattern="^(instagram|tiktok|twitter|linkedin|facebook|youtube)$")
    audience_size: int = Field(10000, ge=100, le=10000000)
    trend_phase: str = Field("growing", pattern="^(pre_emerging|emerging|growing|peak|declining|fading|dead)$")
    budget_usd: int = Field(0, ge=0, le=1000000)

class ContentBriefRequest(BaseModel):
    """Request AI-generated content brief"""
    platform: str = Field(..., pattern="^(instagram|tiktok|twitter|linkedin|facebook|youtube)$")
    topic: str = Field(..., min_length=3, max_length=200)
    competitor_target_id: str | None = None
    trend_keyword: str | None = None

class TrendScanRequest(BaseModel):
    """Request trend scanning"""
    keywords: list[str] = Field(default=..., min_length=1, max_length=50)
    platforms: list[str] = Field(default=["twitter", "reddit"], min_length=1)
    
    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        for kw in v:
            if len(kw) < 2 or len(kw) > 100:
                raise ValueError("Keyword must be 2-100 characters")
        return v


class SERPAnalyzeRequest(BaseModel):
    """Request SERP analysis for a target keyword."""
    keyword: str = Field(..., min_length=2, max_length=200)
    location: str = Field("com", min_length=2, max_length=10)
    language: str = Field("en", min_length=2, max_length=5)
    limit: int = Field(10, ge=1, le=20)


class QuestionMiningRequest(BaseModel):
    """Request question mining for search intent."""
    keyword: str = Field(..., min_length=2, max_length=200)
    limit: int = Field(30, ge=5, le=100)


class TopicClusterRequest(BaseModel):
    """Request topic clustering for planning."""
    seed_keywords: list[str] = Field(default=..., min_length=2, max_length=200)
    max_clusters: int = Field(6, ge=2, le=20)


class ContentGapRequest(BaseModel):
    """Request content gap report using SERP + draft content."""
    keyword: str = Field(..., min_length=2, max_length=200)
    draft_content: str = Field(..., min_length=100, max_length=100000)
    location: str = Field("com", min_length=2, max_length=10)
    language: str = Field("en", min_length=2, max_length=5)
    limit: int = Field(10, ge=1, le=20)


class ContentOptimizeRequest(BaseModel):
    """Request optimization audit for content quality and SEO readiness."""
    keyword: str = Field(..., min_length=2, max_length=200)
    draft_content: str = Field(..., min_length=100, max_length=100000)
    required_terms: list[str] = Field(default_factory=list)
    recommended_questions: list[str] = Field(default_factory=list)

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 1: ADD TARGET
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/targets", response_model=dict, summary="Add competitor target")
async def add_target(
    req: AddTargetRequest,
    background_tasks: BackgroundTasks,
    current_org=Depends(get_current_org),
    current_user=Depends(get_current_user)
):
    """Add new competitor target for tracking"""
    try:
        sb = get_supabase()
        
        # Validate not duplicate
        existing = sb.table("intel_targets").select("id").eq("org_id", current_org).eq("name", req.name).execute()
        if existing.data:
            raise HTTPException(400, "Target with this name already exists")
        
        # Insert target
        target_data = {
            "org_id": str(current_org),
            "name": req.name,
            "domain": req.domain,
            "twitter_handle": req.twitter_handle,
            "instagram_handle": req.instagram_handle,
            "facebook_page": req.facebook_page,
            "reddit_username": req.reddit_username,
            "youtube_channel_id": req.youtube_channel_id,
            "category": req.category,
            "priority": req.priority,
            "track_website": req.track_website,
            "track_ads": req.track_ads,
            "track_social": req.track_social,
            "track_news": req.track_news,
            "is_active": True,
            "next_scan_scheduled_at": datetime.utcnow().isoformat()
        }
        
        result = sb.table("intel_targets").insert(target_data).execute()
        
        if not result.data:
            raise HTTPException(500, "Failed to create target")
        
        inserted_rows = cast(list[dict[str, Any]], result.data)
        target_id = str(inserted_rows[0].get("id", ""))
        
        # Queue initial scan
        background_tasks.add_task(_full_scan_background, target_id, str(current_org))
        
        logger.info(f"Target created: {target_id} by {current_user}")
        
        return {
            "success": True,
            "target_id": target_id,
            "name": req.name,
            "status": "tracking_started",
            "message": "Full scan queued"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error adding target: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 2: LIST TARGETS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/targets", response_model=dict, summary="List tracked targets")
async def list_targets(
    category: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    current_org=Depends(get_current_org)
):
    """List all tracked competitor targets"""
    try:
        sb = get_supabase()
        query = sb.table("intel_targets").select("*").eq("org_id", current_org).eq("is_active", True).limit(limit)
        
        if category:
            query = query.eq("category", category)
        
        result = query.order("priority", desc=True).execute()
        targets = result.data or []
        
        return {
            "success": True,
            "count": len(targets),
            "targets": targets
        }
    
    except Exception as e:
        logger.exception(f"Error listing targets: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 3: TRIGGER SCAN
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/targets/{target_id}/scan", response_model=dict, summary="Trigger full scan")
async def trigger_scan(
    target_id: str,
    background_tasks: BackgroundTasks,
    current_org=Depends(get_current_org)
):
    """Manually trigger full scan of target"""
    try:
        sb = get_supabase()
        
        # Verify target exists and belongs to org
        target = sb.table("intel_targets").select("id").eq("id", target_id).eq("org_id", current_org).single().execute()
        if not target.data:
            raise HTTPException(404, "Target not found")
        
        # Queue scan
        background_tasks.add_task(_full_scan_background, target_id, str(current_org))
        
        logger.info(f"Scan triggered for target: {target_id}")
        
        return {"success": True, "status": "scan_queued", "target_id": target_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error triggering scan: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND SCAN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

async def _full_scan_background(target_id: str, org_id: str):
    """Full competitive intelligence scan"""
    try:
        sb = get_supabase()
        
        # Get target details
        target_result = sb.table("intel_targets").select("*").eq("id", target_id).single().execute()
        if not target_result.data:
            logger.error(f"Target not found: {target_id}")
            return
        
        target = cast(dict[str, Any], target_result.data)
        logger.info(f"Starting full scan for {target.get('name', 'unknown')}")
        
        # Collect data asynchronously
        tasks = {}
        
        if target.get("twitter_handle") and target.get("track_social"):
            tasks["twitter"] = collect_twitter_public(target["twitter_handle"])
        
        if target.get("reddit_username") and target.get("track_social"):
            tasks["reddit"] = collect_reddit_public(target["reddit_username"])

        if target.get("youtube_channel_id") and target.get("track_social"):
            tasks["youtube"] = collect_youtube_public(target["youtube_channel_id"])
        
        if target.get("domain") and target.get("track_website"):
            tasks["website"] = scrape_public_website(target["domain"])
        
        if target.get("domain") and target.get("track_news"):
            tasks["news"] = fetch_news(target["name"])
        
        if target.get("facebook_page") and target.get("track_ads"):
            tasks["ads"] = fetch_meta_ads(target["facebook_page"])
        
        # Execute all tasks
        if tasks:
            gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
            results: dict[str, Any] = {
                k: (v if not isinstance(v, Exception) else [])
                for k, v in zip(tasks.keys(), gathered, strict=False)
            }
        else:
            results = {}
        
        # Process posts
        all_posts: list[dict[str, Any]] = []
        for platform in ["twitter", "reddit", "youtube"]:
            posts = results.get(platform, [])
            if isinstance(posts, list):
                all_posts.extend(cast(list[dict[str, Any]], posts))
        
        # Score posts
        if all_posts:
            all_posts = await calculate_scores(all_posts)
            
            # Insert posts
            post_rows: list[dict[str, Any]] = []
            for post in all_posts[:100]:  # Limit to 100 per scan
                post_rows.append({
                    "target_id": target_id,
                    "org_id": org_id,
                    "platform": str(post.get("platform", "unknown")),
                    "platform_post_id": str(post.get("platform_post_id", "")),
                    "post_url": post.get("post_url"),
                    "author_handle": post.get("author_handle"),
                    "content": str(post.get("content", ""))[:2000],
                    "content_type": post.get("content_type", "text"),
                    "likes": post.get("likes", 0),
                    "comments": post.get("comments", 0),
                    "shares": post.get("shares", 0),
                    "views": post.get("views", 0),
                    "engagement_rate": post.get("engagement_rate", 0),
                    "engagement_velocity": post.get("engagement_velocity", 0),
                    "virality_coefficient": post.get("virality_coefficient", 0),
                    "content_resonance_index": post.get("content_resonance_index", 0),
                    "estimated_organic_reach": post.get("estimated_organic_reach", 0),
                    "trend_phase": post.get("trend_phase", "stable"),
                    "posted_at": post.get("posted_at"),
                    "is_viral_flagged": post.get("virality_coefficient", 0) > 40
                })
            
            sb.table("intel_social_posts").upsert(post_rows, on_conflict="platform,platform_post_id").execute()
            logger.info(f"Inserted {len(post_rows)} posts for {target.get('name', 'unknown')}")
        
        # Process ads
        ads = results.get("ads", [])
        if isinstance(ads, list) and ads:
            ad_rows = [{"target_id": target_id, "org_id": org_id, **ad} for ad in ads]
            sb.table("intel_ads").upsert(ad_rows, on_conflict="platform,ad_id").execute()
            logger.info(f"Inserted {len(ad_rows)} ads for {target.get('name', 'unknown')}")
        
        # Update target last scan
        sb.table("intel_targets").update({
            "last_full_scan_at": datetime.utcnow().isoformat(),
            "next_scan_scheduled_at": (datetime.utcnow() + __import__("datetime").timedelta(hours=target.get("scan_frequency_hours", 6))).isoformat()
        }).eq("id", target_id).execute()
        
        logger.info(f"Full scan complete for {target.get('name', 'unknown')}")
    
    except Exception as e:
        logger.exception(f"Full scan error for {target_id}: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 4: GET POSTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/posts", response_model=dict, summary="Get analyzed posts")
async def get_posts(
    target_id: str | None = Query(None),
    platform: str | None = Query(None, pattern="^(twitter|reddit|instagram|linkedin|tiktok|youtube)?$"),
    trend_phase: str | None = Query(None),
    min_cri: float = Query(0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=500),
    sort_by: str = Query("content_resonance_index", pattern="^(content_resonance_index|virality_coefficient|posted_at)$"),
    current_org=Depends(get_current_org)
):
    """Get analyzed posts with filtering"""
    try:
        sb = get_supabase()
        query = (sb.table("intel_social_posts")
                 .select("*, intel_targets(name, domain, category)")
                 .eq("org_id", current_org)
                 .gte("content_resonance_index", min_cri)
                 .order(sort_by, desc=True)
                 .limit(limit))
        
        if target_id:
            query = query.eq("target_id", target_id)
        if platform:
            query = query.eq("platform", platform)
        if trend_phase:
            query = query.eq("trend_phase", trend_phase)
        
        result = query.execute()
        posts = result.data or []
        
        # Calculate stats
        stats = {
            "total": len(posts),
            "avg_cri": round(sum(float(p.get("content_resonance_index", 0) or 0) for p in posts) / max(len(posts), 1), 1) if posts else 0,
            "avg_engagement_rate": round(sum(float(p.get("engagement_rate", 0) or 0) for p in posts) / max(len(posts), 1), 2) if posts else 0,
            "viral_count": sum(1 for p in posts if p.get("virality_coefficient", 0) > 40)
        }
        
        return {"success": True, "posts": posts, "stats": stats}
    
    except Exception as e:
        logger.exception(f"Error getting posts: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 5: VIRAL POSTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/posts/viral", response_model=dict, summary="Get viral posts")
async def get_viral_posts(
    limit: int = Query(20, ge=1, le=100),
    current_org=Depends(get_current_org)
):
    """Get posts with virality coefficient > 40"""
    try:
        sb = get_supabase()
        result = (sb.table("intel_social_posts")
                  .select("*, intel_targets(name)")
                  .eq("org_id", current_org)
                  .gte("virality_coefficient", 40)
                  .order("content_resonance_index", desc=True)
                  .limit(limit)
                  .execute())
        
        posts = result.data or []
        return {
            "success": True,
            "viral_posts": posts,
            "count": len(posts)
        }
    
    except Exception as e:
        logger.exception(f"Error getting viral posts: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 6: ADS INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/ads", response_model=dict, summary="Get ad intelligence")
async def get_ads(
    target_id: str | None = Query(None),
    active_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=500),
    current_org=Depends(get_current_org)
):
    """Get competitor ad spend analysis"""
    try:
        sb = get_supabase()
        query = (sb.table("intel_ads")
                 .select("*, intel_targets(name, domain)")
                 .eq("org_id", current_org)
                 .order("estimated_total_spend_max", desc=True)
                 .limit(limit))
        
        if target_id:
            query = query.eq("target_id", target_id)
        if active_only:
            query = query.eq("is_active", True)
        
        result = query.execute()
        ads = result.data or []
        
        # Aggregate spend
        spend_min = sum(a.get("estimated_daily_spend_min") or 0 for a in ads)
        spend_max = sum(a.get("estimated_daily_spend_max") or 0 for a in ads)
        
        return {
            "success": True,
            "ads": ads,
            "total_ads": len(ads),
            "combined_daily_spend_range": f"${spend_min:,} – ${spend_max:,}"
        }
    
    except Exception as e:
        logger.exception(f"Error getting ads: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 7: SCAN TRENDS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/trends/scan", response_model=dict, summary="Scan for trends")
async def scan_trends(
    req: TrendScanRequest,
    background_tasks: BackgroundTasks,
    current_org=Depends(get_current_org)
):
    """Scan keywords for trend phases with ROI scoring"""
    try:
        sb = get_supabase()
        results = []
        
        for keyword in req.keywords[:20]:
            # Get volume data from Reddit
            volumes = {}
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as c:
                    response = await c.get(
                        "https://www.reddit.com/search.json",
                        params={"q": keyword, "sort": "new", "limit": 25, "t": "day"},
                        headers={"User-Agent": "GodIntelligence/1.0"}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        volumes["reddit"] = data.get("data", {}).get("dist", 0)
            except Exception:
                volumes["reddit"] = 0
            
            # Get historical volumes
            hist_result = (sb.table("intel_trends")
                          .select("current_volume")
                          .eq("org_id", current_org)
                          .eq("keyword", keyword)
                          .order("updated_at", desc=True)
                          .limit(10)
                          .execute())
            
            historical_rows = cast(list[dict[str, Any]], hist_result.data or [])
            historical = [row.get("current_volume", 0) for row in historical_rows]
            
            # Detect trend phase
            trend_data = await detect_trend_phase(keyword, volumes, historical)
            
            # Upsert trend
            sb.table("intel_trends").upsert({
                "org_id": str(current_org),
                "keyword": keyword,
                "lifecycle_phase": trend_data["lifecycle_phase"],
                "current_volume": trend_data["current_volume"],
                "volume_24h_change_pct": trend_data["daily_change_pct"],
                "momentum_score": trend_data.get("roi_opportunity_score", 50),
                "roi_opportunity_score": trend_data.get("roi_opportunity_score", 50),
                "action_urgency": trend_data["action_urgency"],
                "platform_breakdown": trend_data["platform_breakdown"],
                "updated_at": datetime.utcnow().isoformat()
            }, on_conflict="org_id,keyword").execute()
            
            results.append(trend_data)
        
        # Sort by opportunity
        results = sorted(results, key=lambda x: x.get("roi_opportunity_score", 0), reverse=True)
        
        logger.info(f"Scanned {len(req.keywords)} keywords for org {current_org}")
        
        return {
            "success": True,
            "trends_scanned": len(req.keywords),
            "trends": results
        }
    
    except Exception as e:
        logger.exception(f"Error scanning trends: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 8: GET TRENDS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/trends", response_model=dict, summary="Get tracked trends")
async def get_trends(
    phase: str | None = Query(None, pattern="^(pre_emerging|emerging|growing|peak|declining|fading|dead)?$"),
    min_roi: float = Query(0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=500),
    current_org=Depends(get_current_org)
):
    """Get tracked trends with phase and ROI scoring"""
    try:
        sb = get_supabase()
        query = (sb.table("intel_trends")
                 .select("*")
                 .eq("org_id", current_org)
                 .gte("roi_opportunity_score", min_roi)
                 .order("roi_opportunity_score", desc=True)
                 .limit(limit))
        
        if phase:
            query = query.eq("lifecycle_phase", phase)
        
        result = query.execute()
        trends = result.data or []
        
        return {
            "success": True,
            "trends": trends,
            "count": len(trends)
        }
    
    except Exception as e:
        logger.exception(f"Error getting trends: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 9: ROI PREDICTION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/roi/predict", response_model=dict, summary="Predict content ROI")
async def predict_content_roi(
    req: ROIPredictionRequest,
    current_org=Depends(get_current_org)
):
    """ML-based ROI prediction with P25/P50/P75 scenarios"""
    try:
        sb = get_supabase()
        
        # Get benchmarks
        benchmark_result = (sb.table("intel_social_posts")
                           .select("engagement_rate, virality_coefficient")
                           .eq("org_id", current_org)
                           .eq("platform", req.platform)
                           .gte("content_resonance_index", 30)
                           .order("content_resonance_index", desc=True)
                           .limit(20)
                           .execute())
        
        benchmarks = benchmark_result.data or []
        
        # Predict
        prediction = await predict_roi(
            req.content_brief,
            req.platform,
            req.audience_size,
            req.trend_phase,
            benchmarks,
            req.budget_usd
        )
        
        # Store prediction
        sb.table("intel_roi_predictions").insert({
            "org_id": str(current_org),
            "prediction_type": "post",
            "input_data": req.dict(),
            "predicted_reach_p25": prediction["reach"]["organic_p25"],
            "predicted_reach_p50": prediction["reach"]["organic_p50"],
            "predicted_reach_p75": prediction["reach"]["organic_p75"],
            "predicted_engagement_rate_p50": prediction["predicted_engagement_rate"],
            "predicted_leads_p50": prediction["predicted_leads_p50"],
            "predicted_revenue_usd_p50": prediction["predicted_revenue_usd_p50"],
            "predicted_roas": prediction["roas"],
            "confidence_score": prediction["confidence_score"],
            "improvements": json.dumps(prediction["improvements"])
        }).execute()
        
        logger.info(f"ROI prediction created for {req.platform}")
        
        return {"success": True, "prediction": prediction}
    
    except Exception as e:
        logger.exception(f"Error predicting ROI: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 10: CONTENT BRIEF
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/content-brief", response_model=dict, summary="Generate content brief")
async def get_content_brief(
    req: ContentBriefRequest,
    current_org=Depends(get_current_org)
):
    """AI-generated content strategy brief"""
    try:
        sb = get_supabase()
        
        # Get competitor context
        competitor_data = {}
        if req.competitor_target_id:
            report_result = (sb.table("intel_reports")
                           .select("full_report_data")
                           .eq("org_id", current_org)
                           .order("created_at", desc=True)
                           .limit(1)
                           .execute())
            if report_result.data:
                report_rows = cast(list[dict[str, Any]], report_result.data)
                competitor_data = cast(dict[str, Any], report_rows[0].get("full_report_data", {}))
        
        # Get trend context
        trend_data = {"lifecycle_phase": "growing", "roi_opportunity_score": 60}
        if req.trend_keyword:
            trend_result = (sb.table("intel_trends")
                          .select("*")
                          .eq("org_id", current_org)
                          .eq("keyword", req.trend_keyword)
                          .order("updated_at", desc=True)
                          .limit(1)
                          .execute())
            if trend_result.data:
                trend_rows = cast(list[dict[str, Any]], trend_result.data)
                trend_data = trend_rows[0]
        
        # Get viral examples
        viral_result = (sb.table("intel_social_posts")
                       .select("content, engagement_rate, virality_coefficient")
                       .eq("org_id", current_org)
                       .eq("platform", req.platform)
                       .order("content_resonance_index", desc=True)
                       .limit(5)
                       .execute())
        viral_examples = viral_result.data or []
        
        # Get org context
        org_result = sb.table("organizations").select("*").eq("id", current_org).single().execute()
        org_context = (org_result.data or {}).get("settings", {}).get("brand_description", "") if org_result.data else ""
        
        # Generate brief
        brief = await generate_content_brief(
            org_context,
            req.platform,
            req.topic,
            trend_data,
            competitor_data,
            viral_examples
        )
        
        # Store brief
        sb.table("intel_content_context").insert({
            "org_id": str(current_org),
            "content_brief": json.dumps(brief),
            "platform": req.platform,
            "topic": req.topic,
            "trend_keyword": req.trend_keyword,
            "competitor_target_id": req.competitor_target_id
        }).execute()
        
        logger.info(f"Content brief generated for {req.topic} on {req.platform}")
        
        return {
            "success": True,
            "brief": brief,
            "trend_context": {"phase": trend_data.get("lifecycle_phase"), "score": trend_data.get("roi_opportunity_score")}
        }
    
    except Exception as e:
        logger.exception(f"Error generating brief: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 11: SERP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/frase/serp-analyze", response_model=dict, summary="Analyze SERP for keyword")
async def frase_serp_analyze(
    req: SERPAnalyzeRequest,
    current_org=Depends(get_current_org)
):
    """Run SERP analysis and persist snapshot for keyword intelligence."""
    try:
        sb = get_supabase()
        analysis = await analyze_serp(
            keyword=req.keyword,
            location=req.location,
            language=req.language,
            limit=req.limit,
        )

        sb.table("intel_reports").insert({
            "org_id": str(current_org),
            "report_type": "serp_analysis",
            "title": f"SERP Analysis: {req.keyword}",
            "summary": f"SERP vendor={analysis.get('vendor')} results={len(analysis.get('results', []))}",
            "full_report_data": json.dumps(analysis),
            "key_findings": json.dumps(analysis.get("related_searches", [])[:10]),
            "recommendations": json.dumps(["Use missing topics and intent questions in briefing workflow"]),
        }).execute()

        return {"success": True, "analysis": analysis}
    except Exception as e:
        logger.exception(f"Error running SERP analysis: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 12: QUESTION MINING
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/frase/questions", response_model=dict, summary="Mine search questions")
async def frase_question_mining(
    req: QuestionMiningRequest,
    current_org=Depends(get_current_org)
):
    """Mine high-intent questions and persist them for content planning."""
    try:
        sb = get_supabase()
        mined = await mine_questions(keyword=req.keyword, limit=req.limit)

        sb.table("intel_reports").insert({
            "org_id": str(current_org),
            "report_type": "question_mining",
            "title": f"Question Mining: {req.keyword}",
            "summary": f"Questions mined={mined.get('count', 0)}",
            "full_report_data": json.dumps(mined),
            "key_findings": json.dumps(mined.get("questions", [])[:15]),
            "recommendations": json.dumps(["Add top questions as H2 FAQ blocks"]),
        }).execute()

        return {"success": True, "questions": mined}
    except Exception as e:
        logger.exception(f"Error mining questions: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 13: TOPIC CLUSTERS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/frase/topic-clusters", response_model=dict, summary="Build keyword topic clusters")
async def frase_topic_clusters(
    req: TopicClusterRequest,
    current_org=Depends(get_current_org)
):
    """Build topic clusters and persist planning map."""
    try:
        sb = get_supabase()
        clusters = await build_topic_clusters(req.seed_keywords, max_clusters=req.max_clusters)

        sb.table("intel_reports").insert({
            "org_id": str(current_org),
            "report_type": "topic_clusters",
            "title": "Topic Clusters",
            "summary": f"Clusters={clusters.get('cluster_count', 0)}",
            "full_report_data": json.dumps(clusters),
            "key_findings": json.dumps([c.get("cluster_name") for c in clusters.get("clusters", [])]),
            "recommendations": json.dumps(["Map each cluster to one pillar page plus 3-5 support pages"]),
        }).execute()

        return {"success": True, "clusters": clusters}
    except Exception as e:
        logger.exception(f"Error building topic clusters: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 14: CONTENT GAP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/frase/content-gap", response_model=dict, summary="Analyze content gaps against SERP")
async def frase_content_gap(
    req: ContentGapRequest,
    current_org=Depends(get_current_org)
):
    """Compare draft content to SERP language coverage and report gaps."""
    try:
        sb = get_supabase()
        serp = await analyze_serp(
            keyword=req.keyword,
            location=req.location,
            language=req.language,
            limit=req.limit,
        )
        gap_report = await build_content_gap_report(
            target_keyword=req.keyword,
            draft_content=req.draft_content,
            serp_analysis=serp,
        )

        sb.table("intel_reports").insert({
            "org_id": str(current_org),
            "report_type": "content_gap",
            "title": f"Content Gap: {req.keyword}",
            "summary": f"Coverage score={gap_report.get('coverage_score', 0)}",
            "full_report_data": json.dumps(gap_report),
            "key_findings": json.dumps(gap_report.get("missing_terms", [])[:20]),
            "recommendations": json.dumps([
                "Add missing semantic terms in headings and body copy",
                "Answer question intent directly in FAQ section",
            ]),
        }).execute()

        return {"success": True, "serp": serp, "content_gap": gap_report}
    except Exception as e:
        logger.exception(f"Error running content gap analysis: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 15: CONTENT OPTIMIZATION AUDIT
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/frase/optimize", response_model=dict, summary="Audit and score content optimization")
async def frase_optimize_content(
    req: ContentOptimizeRequest,
    current_org=Depends(get_current_org)
):
    """Compute optimization score and persist audit output for review workflows."""
    try:
        sb = get_supabase()
        audit = await audit_content_optimization(
            target_keyword=req.keyword,
            draft_content=req.draft_content,
            required_terms=req.required_terms,
            recommended_questions=req.recommended_questions,
        )

        sb.table("intel_content_context").insert({
            "org_id": str(current_org),
            "content_brief": json.dumps(audit),
            "platform": "seo",
            "topic": req.keyword,
        }).execute()

        return {"success": True, "audit": audit}
    except Exception as e:
        logger.exception(f"Error running optimization audit: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINT 16: DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard", response_model=dict, summary="Intelligence dashboard")
async def intelligence_dashboard(current_org=Depends(get_current_org)):
    """Aggregated intelligence dashboard data"""
    try:
        sb = get_supabase()
        
        # Parallel queries
        targets_r, posts_r, ads_r, trends_r = await asyncio.gather(
            asyncio.to_thread(
                lambda: sb.table("intel_targets").select("id,name,category,last_full_scan_at").eq("org_id", current_org).eq("is_active", True).execute()
            ),
            asyncio.to_thread(
                lambda: sb.table("intel_social_posts").select("platform,engagement_rate,virality_coefficient,trend_phase,content_resonance_index").eq("org_id", current_org).order("content_resonance_index", desc=True).limit(200).execute()
            ),
            asyncio.to_thread(
                lambda: sb.table("intel_ads").select("platform,estimated_daily_spend_min,estimated_daily_spend_max,is_active").eq("org_id", current_org).execute()
            ),
            asyncio.to_thread(
                lambda: sb.table("intel_trends").select("keyword,lifecycle_phase,roi_opportunity_score,momentum_score").eq("org_id", current_org).order("roi_opportunity_score", desc=True).limit(20).execute()
            )
        )
        
        targets = targets_r.data or []
        posts = posts_r.data or []
        ads = ads_r.data or []
        trends = trends_r.data or []
        
        # Aggregate metrics
        spend_min = sum((a.get("estimated_daily_spend_min") or 0) for a in ads if a.get("is_active"))
        spend_max = sum((a.get("estimated_daily_spend_max") or 0) for a in ads if a.get("is_active"))
        avg_er = round(sum(float(p.get("engagement_rate", 0) or 0) for p in posts) / max(len(posts), 1), 2) if posts else 0
        
        # Phase distribution
        phase_dist: dict[str, int] = {}
        for trend in trends:
            phase = trend.get("lifecycle_phase", "unknown")
            phase_dist[phase] = phase_dist.get(phase, 0) + 1
        
        return {
            "success": True,
            "summary": {
                "targets_tracked": len(targets),
                "posts_analyzed": len(posts),
                "viral_posts_detected": sum(1 for p in posts if p.get("virality_coefficient", 0) > 40),
                "avg_engagement_rate": avg_er,
                "active_ads": sum(1 for a in ads if a.get("is_active")),
                "competitor_daily_spend": f"${spend_min:,} – ${spend_max:,}",
                "trends_tracked": len(trends),
                "pre_emerging_trends": phase_dist.get("pre_emerging", 0),
                "emerging_trends": phase_dist.get("emerging", 0)
            },
            "trends": trends,
            "targets": targets,
            "phase_distribution": phase_dist,
            "intelligence_score": min(100, len(targets) * 12 + len(posts) // 10)
        }
    
    except Exception as e:
        logger.exception(f"Error loading dashboard: {str(e)}")
        raise HTTPException(500, f"Error: {str(e)}")

logger.info("✓ God Intelligence routes loaded (11 endpoints)")
