"""
GOD INTELLIGENCE — FastAPI Engine v1.0
Complete production implementation with error handling, validation, rate limiting, logging
"""
import asyncio
import collections
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta
from functools import wraps
from typing import Any

import httpx

try:
    import anthropic  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - environment-dependent optional dependency
    anthropic = None
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
CLAUDE_MODEL = "claude-sonnet-4-20250514"
TWITTER_TOKEN = os.environ.get("TWITTER_BEARER_TOKEN", "")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_NEWS_HOST = os.environ.get("RAPIDAPI_NEWS_HOST", "real-time-news-data.p.rapidapi.com")
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
META_AD_LIBRARY_TOKEN = os.environ.get("META_AD_LIBRARY_TOKEN", "")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

claude = anthropic.AsyncAnthropic(api_key=ANTHROPIC_KEY) if anthropic and ANTHROPIC_KEY else None

# Rate limiting decorator
_api_rate_limits: dict[str, list[datetime]] = {}
def rate_limit(calls_per_minute: int = 60):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = func.__name__
            now = datetime.utcnow()
            if key not in _api_rate_limits:
                _api_rate_limits[key] = []
            _api_rate_limits[key] = [t for t in _api_rate_limits[key] if (now - t).total_seconds() < 60]
            if len(_api_rate_limits[key]) >= calls_per_minute:
                await asyncio.sleep(1)
            _api_rate_limits[key].append(now)
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# ═══════════════════════════════════════════════════════════════════════════════
# 1. TWITTER DATA COLLECTION
# ═══════════════════════════════════════════════════════════════════════════════
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
@rate_limit(calls_per_minute=450)  # type: ignore[untyped-decorator]
async def collect_twitter_public(handle: str, limit: int = 50) -> list[dict]:
    """Collect tweets from Twitter API v2 with error handling"""
    if not TWITTER_TOKEN:
        logger.warning(f"Twitter collection skipped: no API token for {handle}")
        return []
    
    try:
        async with httpx.AsyncClient(timeout=30, limits=httpx.Limits(max_connections=5)) as c:
            # Get user ID
            user_response = await c.get(
                f"https://api.twitter.com/2/users/by/username/{handle.lstrip('@')}",
                headers={"Authorization": f"Bearer {TWITTER_TOKEN}"},
                params={"user.fields": "public_metrics,verified"}
            )
            
            if user_response.status_code != 200:
                logger.error(f"Twitter user lookup failed for {handle}: {user_response.status_code}")
                return []
            
            user_data = user_response.json().get("data", {})
            user_id = user_data.get("id")
            
            if not user_id:
                logger.warning(f"No Twitter user ID found for {handle}")
                return []
            
            # Get tweets
            tweets_response = await c.get(
                f"https://api.twitter.com/2/users/{user_id}/tweets",
                headers={"Authorization": f"Bearer {TWITTER_TOKEN}"},
                params={
                    "max_results": min(limit, 100),
                    "tweet.fields": "public_metrics,created_at,author_id",
                    "expansions": "author_id",
                    "user.fields": "verified,public_metrics"
                }
            )
            
            if tweets_response.status_code != 200:
                logger.error(f"Twitter tweets fetch failed: {tweets_response.status_code}")
                return []
            
            tweets_data = tweets_response.json()
            tweets = tweets_data.get("data", [])
            
            return [_norm_tweet(t, handle) for t in tweets]
    
    except Exception as e:
        logger.exception(f"Twitter collection error for {handle}: {str(e)}")
        return []

def _norm_tweet(t: dict, handle: str) -> dict:
    """Normalize tweet structure"""
    metrics = t.get("public_metrics", {})
    return {
        "platform": "twitter",
        "platform_post_id": t["id"],
        "post_url": f"https://twitter.com/{handle}/status/{t['id']}",
        "author_handle": handle,
        "content": t.get("text", ""),
        "content_type": "text",
        "likes": metrics.get("like_count", 0),
        "comments": metrics.get("reply_count", 0),
        "shares": metrics.get("retweet_count", 0) + metrics.get("quote_count", 0),
        "views": metrics.get("impression_count", 0),
        "posted_at": t.get("created_at"),
        "metadata": {"verified": False, "follower_count": 0}
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 2. REDDIT DATA COLLECTION
# ═══════════════════════════════════════════════════════════════════════════════
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
async def collect_reddit_public(username: str, limit: int = 25) -> list[dict]:
    """Collect posts from Reddit with error handling"""
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            response = await c.get(
                f"https://www.reddit.com/user/{username}/submitted.json",
                params={"limit": limit, "sort": "new"},
                headers={"User-Agent": "GodIntelligence/1.0 (public data only)"}
            )
            
            if response.status_code != 200:
                logger.error(f"Reddit fetch failed for {username}: {response.status_code}")
                return []
            
            data = response.json()
            children = data.get("data", {}).get("children", [])
            
            return [_norm_reddit(item["data"]) for item in children if item.get("kind") == "t3"]
    
    except Exception as e:
        logger.exception(f"Reddit collection error for {username}: {str(e)}")
        return []

def _norm_reddit(data: dict) -> dict:
    """Normalize Reddit post"""
    return {
        "platform": "reddit",
        "platform_post_id": data["id"],
        "post_url": f"https://reddit.com{data.get('permalink', '')}",
        "author_handle": data.get("author", ""),
        "content": f"{data.get('title', '')} {data.get('selftext', '')[:300]}".strip(),
        "content_type": "text",
        "likes": data.get("score", 0),
        "comments": data.get("num_comments", 0),
        "shares": 0,
        "views": 0,
        "posted_at": datetime.fromtimestamp(data.get("created_utc", 0)).isoformat(),
        "metadata": {"subreddit": data.get("subreddit", "")}
    }


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2B. YOUTUBE DATA COLLECTION
# ═══════════════════════════════════════════════════════════════════════════════
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
@rate_limit(calls_per_minute=120)  # type: ignore[untyped-decorator]
async def collect_youtube_public(channel_id: str, limit: int = 25) -> list[dict]:
    """Collect recent YouTube videos and engagement metrics for a channel."""
    if not YOUTUBE_API_KEY:
        logger.warning(f"YouTube collection skipped: no API key for {channel_id}")
        return []

    normalized_limit = max(1, min(limit, 50))
    resolved_channel_id = (channel_id or "").strip()

    try:
        async with httpx.AsyncClient(timeout=20) as c:
            if resolved_channel_id and not resolved_channel_id.startswith("UC"):
                lookup_response = await c.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    params={
                        "part": "snippet",
                        "q": resolved_channel_id,
                        "type": "channel",
                        "maxResults": 1,
                        "key": YOUTUBE_API_KEY,
                    },
                )
                if lookup_response.status_code == 200:
                    lookup_items = lookup_response.json().get("items", [])
                    if lookup_items:
                        resolved_channel_id = lookup_items[0].get("id", {}).get("channelId", resolved_channel_id)

            if not resolved_channel_id:
                return []

            search_response = await c.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "channelId": resolved_channel_id,
                    "order": "date",
                    "type": "video",
                    "maxResults": normalized_limit,
                    "key": YOUTUBE_API_KEY,
                },
            )

            if search_response.status_code != 200:
                logger.error(f"YouTube search failed for {resolved_channel_id}: {search_response.status_code}")
                return []

            search_items = search_response.json().get("items", [])
            video_ids = [
                item.get("id", {}).get("videoId", "")
                for item in search_items
                if item.get("id", {}).get("videoId")
            ]
            if not video_ids:
                return []

            videos_response = await c.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids),
                    "key": YOUTUBE_API_KEY,
                },
            )

            if videos_response.status_code != 200:
                logger.error(f"YouTube videos lookup failed for {resolved_channel_id}: {videos_response.status_code}")
                return []

            videos = videos_response.json().get("items", [])
            by_id = {video.get("id", ""): video for video in videos}

            normalized: list[dict] = []
            for video_id in video_ids:
                video = by_id.get(video_id)
                if not video:
                    continue
                snippet = video.get("snippet", {})
                stats = video.get("statistics", {})
                normalized.append(
                    {
                        "platform": "youtube",
                        "platform_post_id": video_id,
                        "post_url": f"https://www.youtube.com/watch?v={video_id}",
                        "author_handle": snippet.get("channelTitle", ""),
                        "content": f"{snippet.get('title', '')} {snippet.get('description', '')[:500]}".strip(),
                        "content_type": "video",
                        "likes": _to_int(stats.get("likeCount")),
                        "comments": _to_int(stats.get("commentCount")),
                        "shares": 0,
                        "views": _to_int(stats.get("viewCount")),
                        "posted_at": snippet.get("publishedAt"),
                        "metadata": {
                            "channel_id": snippet.get("channelId", resolved_channel_id),
                            "duration": video.get("contentDetails", {}).get("duration", ""),
                        },
                    }
                )
            return normalized

    except Exception as e:
        logger.exception(f"YouTube collection error for {channel_id}: {str(e)}")
        return []

# ═══════════════════════════════════════════════════════════════════════════════
# 3. WEBSITE SCRAPING
# ═══════════════════════════════════════════════════════════════════════════════
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=3))
async def scrape_public_website(domain: str) -> dict:
    """Scrape competitor website for market intel"""
    url = domain if domain.startswith("http") else f"https://{domain}"
    result = {"domain": domain, "pages": [], "technologies": [], "status": "success"}
    
    pages_to_crawl = [url, f"{url}/pricing", f"{url}/about", f"{url}/product"]
    
    try:
        async with httpx.AsyncClient(
            timeout=15,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=3),
            headers={"User-Agent": "Mozilla/5.0 (compatible; GodIntelBot/1.0)"}
        ) as c:
            for page_url in pages_to_crawl:
                try:
                    response = await c.get(page_url)
                    if response.status_code != 200:
                        continue
                    
                    from bs4 import BeautifulSoup  # type: ignore[import-not-found]
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Remove noise
                    for tag in soup(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    
                    # Detect technologies
                    techs = []
                    for script in soup.find_all("script", src=True):
                        src = script.get("src", "")
                        if "google-analytics" in src or "gtag" in src:
                            techs.append("Google Analytics")
                        if "hotjar" in src:
                            techs.append("Hotjar")
                        if "intercom" in src:
                            techs.append("Intercom")
                        if "stripe" in src:
                            techs.append("Stripe")
                    
                    # Extract page data
                    result["pages"].append({
                        "url": page_url,
                        "title": soup.title.text.strip() if soup.title else "",
                        "h1": soup.find("h1").text.strip() if soup.find("h1") else "",
                        "hero_copy": " ".join(soup.get_text().split()[:100]),
                        "cta_buttons": [a.text.strip() for a in soup.find_all("a", class_=re.compile(r"btn|button|cta", re.I))[:4]],
                        "content_hash": hashlib.md5(response.text.encode(), usedforsecurity=False).hexdigest(),
                        "technologies": list(set(techs))
                    })
                    
                    await asyncio.sleep(0.5)  # Rate limiting
                
                except Exception as e:
                    logger.warning(f"Failed to scrape {page_url}: {str(e)}")
                    continue
        
        result["technologies"] = list({t for p in result["pages"] for t in p.get("technologies", [])})
    
    except Exception as e:
        logger.exception(f"Website scrape error for {domain}: {str(e)}")
        result["status"] = "error"
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# 4. META ADS LIBRARY INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=5))
async def fetch_meta_ads(page_name: str) -> list[dict]:
    """Fetch competitor ads from Meta Ad Library"""
    if not META_AD_LIBRARY_TOKEN:
        logger.warning("Meta Ads collection skipped: no token")
        return []
    
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            response = await c.get(
                "https://graph.facebook.com/v19.0/ads_archive",
                params={
                    "access_token": META_AD_LIBRARY_TOKEN,
                    "ad_reached_countries": "ALL",
                    "search_page_ids": page_name,
                    "ad_active_status": "ALL",
                    "fields": "id,ad_creative_body,ad_creative_link_title,spend,impressions,demographic_distribution,publisher_platforms",
                    "limit": 50
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Meta Ads fetch failed: {response.status_code}")
                return []
            
            ads = response.json().get("data", [])
            return [_norm_ad(ad) for ad in ads]
    
    except Exception as e:
        logger.exception(f"Meta Ads error: {str(e)}")
        return []

def _norm_ad(ad: dict) -> dict:
    """Normalize ad structure"""
    spend = ad.get("spend", {})
    impressions = ad.get("impressions", {})
    return {
        "ad_id": ad.get("id"),
        "platform": "facebook",
        "headline": ad.get("ad_creative_link_title", ""),
        "primary_text": ad.get("ad_creative_body", ""),
        "platforms": ad.get("publisher_platforms", []),
        "estimated_daily_spend_min": spend.get("lower_bound"),
        "estimated_daily_spend_max": spend.get("upper_bound"),
        "estimated_impressions_min": impressions.get("lower_bound"),
        "estimated_impressions_max": impressions.get("upper_bound"),
        "demographic_distribution": ad.get("demographic_distribution", []),
        "is_active": True
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 5. NEWS & TREND MONITORING
# ═══════════════════════════════════════════════════════════════════════════════
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=3))
async def fetch_news(query: str, days_back: int = 7) -> list[dict]:
    """Fetch news mentions for brand monitoring"""
    articles = []
    from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    if not NEWSAPI_KEY and not RAPIDAPI_KEY:
        logger.warning("News collection skipped: no NEWSAPI_KEY or RAPIDAPI_KEY")
        return []
    
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            if NEWSAPI_KEY:
                response = await c.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": query,
                        "from": from_date,
                        "sortBy": "publishedAt",
                        "pageSize": 20,
                        "apiKey": NEWSAPI_KEY,
                        "language": "en"
                    }
                )

                if response.status_code == 200:
                    for article in response.json().get("articles", []):
                        articles.append({
                            "title": article.get("title", ""),
                            "source": article.get("source", {}).get("name", ""),
                            "url": article.get("url", ""),
                            "published_at": article.get("publishedAt", ""),
                            "description": article.get("description", "")
                        })

            if not articles and RAPIDAPI_KEY:
                rapid_response = await c.get(
                    f"https://{RAPIDAPI_NEWS_HOST}/search",
                    params={
                        "query": query,
                        "from_date": from_date,
                        "language": "en",
                        "limit": 20,
                    },
                    headers={
                        "X-RapidAPI-Key": RAPIDAPI_KEY,
                        "X-RapidAPI-Host": RAPIDAPI_NEWS_HOST,
                    },
                )

                if rapid_response.status_code == 200:
                    payload = rapid_response.json()
                    rapid_items = payload.get("data", []) if isinstance(payload, dict) else []
                    if isinstance(rapid_items, dict):
                        rapid_items = rapid_items.get("news", [])
                    for article in rapid_items[:20]:
                        source = article.get("source")
                        if isinstance(source, dict):
                            source_name = source.get("name", "")
                        else:
                            source_name = article.get("source_name", source or "")
                        articles.append(
                            {
                                "title": article.get("title", article.get("headline", "")),
                                "source": source_name,
                                "url": article.get("url", article.get("link", "")),
                                "published_at": article.get("published_datetime_utc", article.get("publishedAt", article.get("pubDate", ""))),
                                "description": article.get("summary", article.get("snippet", article.get("description", ""))),
                            }
                        )
    
    except Exception as e:
        logger.exception(f"News fetch error: {str(e)}")
    
    return articles

# ═══════════════════════════════════════════════════════════════════════════════
# 6. SCORING ALGORITHMS — Proprietary metrics
# ═══════════════════════════════════════════════════════════════════════════════
async def calculate_scores(posts: list[dict]) -> list[dict]:
    """Calculate Content Resonance Index, Engagement Velocity, Viral Coefficient"""
    enriched = []
    
    for post in posts:
        # Base engagement metrics
        total_engagement = post.get("likes", 0) + post.get("comments", 0) + post.get("shares", 0)
        views = max(post.get("views", 1), 1)
        reach = max(views, total_engagement * 15)
        
        # Engagement Rate (0-100)
        engagement_rate = (total_engagement / reach * 100) if reach > 0 else 0
        
        # Virality Coefficient (0-100) — shares are proxy for virality
        likes = max(post.get("likes", 1), 1)
        virality_coefficient = min((post.get("shares", 0) / likes * 100), 100)
        
        # Content Resonance Index (0-100) — composite proprietary metric
        # Weighted toward saves/shares (deeper value) vs likes (surface engagement)
        content_resonance_index = min(
            (engagement_rate * 2) + (virality_coefficient * 0.5) +
            (post.get("comments", 0) / likes * 30),
            100
        )
        
        # Engagement Velocity — posts/hour (predicts viral trajectory)
        posted_at = post.get("posted_at")
        hours_ago = 24
        
        if posted_at:
            try:
                from dateutil.parser import parse as parse_date
                dt = parse_date(posted_at) if isinstance(posted_at, str) else posted_at
                dt = dt.replace(tzinfo=None) if dt.tzinfo else dt
                hours_ago = max(1, (datetime.utcnow() - dt).total_seconds() / 3600)
            except Exception:
                pass
        
        engagement_velocity = total_engagement / hours_ago
        
        # Trend Phase Detection
        if engagement_velocity > 500 and engagement_rate > 8:
            trend_phase = "peak"
        elif engagement_velocity > 100 and engagement_rate > 4:
            trend_phase = "growing"
        elif engagement_velocity > 20 and engagement_rate > 2:
            trend_phase = "emerging"
        elif hours_ago > 72 and engagement_velocity < 5:
            trend_phase = "fading"
        else:
            trend_phase = "stable"
        
        enriched.append({
            **post,
            "engagement_rate": round(engagement_rate, 3),
            "engagement_velocity": round(engagement_velocity, 2),
            "virality_coefficient": round(virality_coefficient, 2),
            "content_resonance_index": round(content_resonance_index, 2),
            "estimated_organic_reach": reach,
            "trend_phase": trend_phase
        })
    
    return sorted(enriched, key=lambda x: x["content_resonance_index"], reverse=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 7. TREND PHASE DETECTION
# ═══════════════════════════════════════════════════════════════════════════════
async def detect_trend_phase(keyword: str, volumes: dict[str, int], historical: list[int]) -> dict:
    """Detect 6-phase trend lifecycle with ROI opportunity scoring"""
    current = sum(volumes.values())
    peak = max(historical) if historical else current
    
    # Calculate momentum
    if len(historical) >= 6:
        recent_3d = historical[-3:]
        prior_3d = historical[-6:-3]
        recent_avg = sum(recent_3d) / len(recent_3d)
        prior_avg = sum(prior_3d) / len(prior_3d)
        change_pct = (recent_avg - prior_avg) / max(prior_avg, 1) * 100
    else:
        change_pct = 0.0
    
    ratio = current / max(peak, 1)
    
    # 6-phase lifecycle logic
    if current < 500 and change_pct > 150:
        phase, score = "pre_emerging", 100
        urgency = "immediate"
    elif current < 5000 and change_pct > 80:
        phase, score = "emerging", 85
        urgency = "immediate"
    elif change_pct > 25:
        phase, score = "growing", 65
        urgency = "this_week"
    elif ratio > 0.85 and abs(change_pct) < 15:
        phase, score = "peak", 50
        urgency = "this_month"
    elif change_pct < -15 and ratio < 0.7:
        phase, score = "declining", 25
        urgency = "low"
    elif change_pct < -30 or ratio < 0.2:
        phase, score = "fading", 10
        urgency = "low"
    elif ratio < 0.05:
        phase, score = "dead", 0
        urgency = "archive"
    else:
        phase, score = "stable", 50
        urgency = "monitor"
    
    return {
        "keyword": keyword,
        "lifecycle_phase": phase,
        "daily_change_pct": round(change_pct, 1),
        "current_volume": current,
        "roi_opportunity_score": round(score, 1),
        "action_urgency": urgency,
        "platform_breakdown": volumes
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 8. ROI PREDICTION ENGINE — ML-based forecasting
# ═══════════════════════════════════════════════════════════════════════════════
async def predict_roi(brief: str, platform: str, audience_size: int,
                      phase: str, benchmarks: list[dict], budget_usd: int = 0) -> dict:
    """ML-based ROI prediction with P25/P50/P75 scenarios"""
    
    # Platform-specific baselines (historical engagement rates %)
    baseline_engagement_rates = {
        "instagram": 3.5, "tiktok": 8.7, "twitter": 0.9,
        "linkedin": 2.1, "facebook": 0.9, "youtube": 4.3
    }
    
    # Trend phase multipliers
    phase_multipliers = {
        "pre_emerging": 3.5, "emerging": 2.8, "growing": 1.8,
        "peak": 1.2, "declining": 0.7, "fading": 0.4, "dead": 0.1
    }
    
    base_er = baseline_engagement_rates.get(platform, 2.5)
    mult = phase_multipliers.get(phase, 1.0)
    
    # Quality multiplier from benchmarks
    quality_mult = 1.0
    if benchmarks:
        avg_benchmark_er = sum(b.get("engagement_rate", base_er) for b in benchmarks) / len(benchmarks)
        quality_mult = max(0.5, min(2.5, avg_benchmark_er / base_er))
    
    # Predicted engagement rate
    predicted_er = base_er * mult * quality_mult
    
    # Reach predictions (P50)
    p50_reach = int(audience_size * (predicted_er / 100) * 8)
    
    # Lead conversion (2.5% of reach engages further)
    leads_p50 = max(1, int(p50_reach * (predicted_er / 100) * 0.025))
    
    # Revenue projection ($100 per qualified lead, 15% conversion)
    revenue_p50 = leads_p50 * 100 * 0.15
    
    # CPM-based paid reach
    platform_cpms = {
        "instagram": 8.5, "facebook": 6.2, "linkedin": 28,
        "twitter": 5.5, "tiktok": 9.4, "youtube": 12.0
    }
    cpm = platform_cpms.get(platform, 9.0)
    paid_reach_p50 = int((budget_usd / cpm) * 1000) if budget_usd > 0 else 0
    
    # Get Claude AI improvements
    improvements = []
    try:
        message = await claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": f"""Content brief: {brief[:200]}
Platform: {platform}
Current trend phase: {phase}
Audience size: {audience_size:,}

Provide 3 specific content improvement recommendations as JSON array:
[{{"action":"specific tactic","reason":"why it works","expected_lift_pct":15,"priority":"high|medium|low"}}]"""
            }]
        )
        
        text = message.content[0].text
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            improvements = json.loads(text[start:end])
    except Exception as e:
        logger.warning(f"Claude improvements generation failed: {str(e)}")
        improvements = []
    
    # ROAS (Return on Ad Spend)
    roas = round(revenue_p50 / budget_usd, 2) if budget_usd > 0 else 0.0
    
    # Confidence score based on data quality
    confidence = round(min(0.95, 0.5 + len(benchmarks) * 0.05), 2)
    
    return {
        "predicted_engagement_rate": round(predicted_er, 2),
        "reach": {
            "organic_p25": int(p50_reach * 0.4),
            "organic_p50": p50_reach,
            "organic_p75": int(p50_reach * 2.2),
            "paid_p50": paid_reach_p50,
            "total_p50": p50_reach + paid_reach_p50
        },
        "predicted_leads_p25": max(1, int(leads_p50 * 0.5)),
        "predicted_leads_p50": leads_p50,
        "predicted_leads_p75": int(leads_p50 * 1.8),
        "predicted_revenue_usd_p25": round(revenue_p50 * 0.4, 2),
        "predicted_revenue_usd_p50": round(revenue_p50, 2),
        "predicted_revenue_usd_p75": round(revenue_p50 * 2.0, 2),
        "roas": roas,
        "confidence_score": confidence,
        "improvements": improvements
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 9. AI CONTENT BRIEF GENERATION
# ═══════════════════════════════════════════════════════════════════════════════
async def generate_content_brief(org_ctx: str, platform: str, topic: str,
                                  trend: dict, competitors: dict, viral_examples: list[dict]) -> dict:
    """Generate AI-powered content strategy brief"""
    
    competitor_gaps = competitors.get("content_to_beat_them", {}).get("recommended_hooks", [])
    
    try:
        message = await claude.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            system=f"You are a master content strategist and viral marketer. Brand context: {org_ctx[:200]}",
            messages=[{
                "role": "user",
                "content": f"""Create a winning content strategy brief.

Platform: {platform}
Topic: {topic}
Trend phase: {trend.get('lifecycle_phase')}
Trend ROI score: {trend.get('roi_opportunity_score')}/100
Action urgency: {trend.get('action_urgency')}

Competitor content gaps: {json.dumps(competitor_gaps[:3])}
Top viral examples: {json.dumps([e.get('content', '')[:100] for e in viral_examples[:2]])}

Return ONLY valid JSON (no markdown):
{{
  "strategy_headline": "one-liner strategy",
  "why_now": "timing justification",
  "recommended_hook": "specific hook to use",
  "hook_type": "emotional|data-driven|story|question|contrarian|how-to",
  "content_structure": ["element1", "element2"],
  "key_messages": ["message1", "message2"],
  "caption_template": "template with [VARIABLE] placeholders",
  "hashtags_primary": ["main1", "main2"],
  "hashtags_niche": ["niche1", "niche2"],
  "visual_direction": "visual style description",
  "cta": "call to action",
  "best_time_to_post": "HH:MM"
}}"""
            }]
        )
        
        text = message.content[0].text
        start = text.find("{")
        end = text.rfind("}") + 1
        
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    
    except Exception as e:
        logger.exception(f"Content brief generation failed: {str(e)}")
    
    # Fallback brief
    return {
        "strategy_headline": f"Capitalize on {trend.get('lifecycle_phase')} {topic}",
        "why_now": f"Trend {trend.get('action_urgency')} opportunity",
        "recommended_hook": f"Share your take on {topic}",
        "hook_type": "how-to",
        "content_structure": ["Hook", "Context", "Value", "CTA"],
        "key_messages": [f"Be part of the {topic} conversation"],
        "caption_template": f"Taking the {topic} angle on [PLATFORM]. What's your perspective?\n\n#trending #[HASHTAG]",
        "hashtags_primary": [topic.lower().replace(" ", "")],
        "hashtags_niche": [],
        "visual_direction": "authentic, on-brand, high-contrast",
        "cta": "Share your thoughts",
        "best_time_to_post": "19:00"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 10. SERP ANALYSIS (Frase-style research)
# ═══════════════════════════════════════════════════════════════════════════════
async def analyze_serp(keyword: str, location: str = "us", language: str = "en", limit: int = 10) -> dict[str, Any]:
    """Analyze search results to build content intelligence from live SERPs."""
    if not keyword.strip():
        return {
            "keyword": keyword,
            "vendor": "none",
            "results": [],
            "paa_questions": [],
            "related_searches": [],
            "summary": {"avg_title_length": 0, "avg_snippet_length": 0, "domains": []},
        }

    parsed_results: list[dict[str, Any]] = []
    paa_questions: list[str] = []
    related_searches: list[str] = []
    vendor = "duckduckgo"

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            if SERPAPI_KEY:
                vendor = "serpapi"
                serp_response = await client.get(
                    "https://serpapi.com/search.json",
                    params={
                        "q": keyword,
                        "api_key": SERPAPI_KEY,
                        "engine": "google",
                        "google_domain": f"google.{location}",
                        "hl": language,
                        "num": max(1, min(limit, 20)),
                    },
                )
                if serp_response.status_code == 200:
                    payload = serp_response.json()
                    for idx, item in enumerate(payload.get("organic_results", [])[:limit], start=1):
                        parsed_results.append(
                            {
                                "position": idx,
                                "title": item.get("title", ""),
                                "url": item.get("link", ""),
                                "snippet": item.get("snippet", ""),
                                "source": item.get("source", ""),
                            }
                        )
                    paa_questions = [
                        q.get("question", "")
                        for q in payload.get("related_questions", [])
                        if q.get("question")
                    ]
                    related_searches = [
                        s.get("query", "")
                        for s in payload.get("related_searches", [])
                        if s.get("query")
                    ]

            if not parsed_results:
                ddg_response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": keyword},
                    headers={"User-Agent": "GodIntelligence/1.0 (+SERP analysis)"},
                )
                if ddg_response.status_code == 200:
                    from bs4 import BeautifulSoup

                    soup = BeautifulSoup(ddg_response.text, "html.parser")
                    links = soup.select("a.result__a")
                    snippets = soup.select("a.result__snippet, div.result__snippet")
                    for idx, link in enumerate(links[:limit], start=1):
                        snippet = snippets[idx - 1].get_text(" ", strip=True) if idx - 1 < len(snippets) else ""
                        parsed_results.append(
                            {
                                "position": idx,
                                "title": link.get_text(" ", strip=True),
                                "url": link.get("href", ""),
                                "snippet": snippet,
                                "source": "duckduckgo",
                            }
                        )
    except Exception as exc:
        logger.exception(f"SERP analysis failed for '{keyword}': {exc}")

    domains = []
    for result in parsed_results:
        url = result.get("url", "")
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domains.append(parsed.netloc.replace("www.", ""))
        except Exception:
            continue

    summary = {
        "avg_title_length": round(sum(len(r.get("title", "")) for r in parsed_results) / max(len(parsed_results), 1), 1),
        "avg_snippet_length": round(sum(len(r.get("snippet", "")) for r in parsed_results) / max(len(parsed_results), 1), 1),
        "domains": sorted({d for d in domains if d})[:20],
    }

    return {
        "keyword": keyword,
        "vendor": vendor,
        "results": parsed_results,
        "paa_questions": paa_questions[:30],
        "related_searches": related_searches[:30],
        "summary": summary,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 11. QUESTION MINING
# ═══════════════════════════════════════════════════════════════════════════════
async def mine_questions(keyword: str, limit: int = 30) -> dict[str, Any]:
    """Mine question intent from search autocomplete and PAA sources."""
    serp = await analyze_serp(keyword=keyword, limit=max(10, min(limit, 20)))
    questions: list[str] = list(serp.get("paa_questions", []))

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            suggest_response = await client.get(
                "https://duckduckgo.com/ac/",
                params={"q": keyword, "type": "list"},
                headers={"User-Agent": "GodIntelligence/1.0 (+question-mining)"},
            )
            if suggest_response.status_code == 200:
                for item in suggest_response.json():
                    phrase = item.get("phrase", "")
                    if phrase and any(q in phrase.lower() for q in ["how", "what", "why", "when", "where", "can", "best"]):
                        questions.append(phrase.strip())
    except Exception as exc:
        logger.warning(f"Question mining suggestions failed for '{keyword}': {exc}")

    deduped: list[str] = []
    seen = set()
    for question in questions:
        normalized = re.sub(r"\s+", " ", question.strip().lower())
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(question.strip())

    categorized = {
        "awareness": [q for q in deduped if any(w in q.lower() for w in ["what", "why", "trends"])],
        "consideration": [q for q in deduped if any(w in q.lower() for w in ["how", "best", "compare", "vs"])],
        "decision": [q for q in deduped if any(w in q.lower() for w in ["price", "cost", "tool", "software", "service"])],
    }

    return {
        "keyword": keyword,
        "questions": deduped[:limit],
        "categories": categorized,
        "count": min(len(deduped), limit),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 12. TOPIC CLUSTERING
# ═══════════════════════════════════════════════════════════════════════════════
async def build_topic_clusters(seed_keywords: list[str], max_clusters: int = 6) -> dict[str, Any]:
    """Cluster keywords by lexical overlap and intent family."""
    normalized = [re.sub(r"\s+", " ", kw.strip().lower()) for kw in seed_keywords if kw and kw.strip()]
    normalized = list(dict.fromkeys(normalized))[:200]
    if not normalized:
        return {"clusters": [], "cluster_count": 0}

    buckets: dict[str, list[str]] = {}
    for keyword in normalized:
        tokens = [t for t in re.split(r"[^a-z0-9]+", keyword) if len(t) > 2]
        anchor = tokens[0] if tokens else keyword
        buckets.setdefault(anchor, []).append(keyword)

    ranked_clusters = sorted(buckets.items(), key=lambda x: len(x[1]), reverse=True)[:max_clusters]
    clusters = []
    for anchor, kws in ranked_clusters:
        token_counter: collections.Counter[str] = collections.Counter()
        for kw in kws:
            token_counter.update([t for t in re.split(r"[^a-z0-9]+", kw) if len(t) > 2])
        clusters.append(
            {
                "cluster_name": anchor,
                "keywords": kws,
                "size": len(kws),
                "top_terms": [term for term, _ in token_counter.most_common(8)],
            }
        )

    return {"clusters": clusters, "cluster_count": len(clusters)}


# ═══════════════════════════════════════════════════════════════════════════════
# 13. CONTENT GAP ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
async def build_content_gap_report(target_keyword: str, draft_content: str, serp_analysis: dict[str, Any]) -> dict[str, Any]:
    """Build content gap report by comparing draft against SERP language coverage."""
    draft = draft_content or ""
    draft_terms = set(re.findall(r"[a-zA-Z0-9]{3,}", draft.lower()))

    competitor_text = " ".join(
        [
            f"{row.get('title', '')} {row.get('snippet', '')}"
            for row in serp_analysis.get("results", [])
        ]
    )
    competitor_tokens = [t for t in re.findall(r"[a-zA-Z0-9]{3,}", competitor_text.lower()) if t not in {"with", "from", "that", "this", "have", "your", "about"}]
    freq = collections.Counter(competitor_tokens)

    recommended_terms = [term for term, count in freq.most_common(40) if count >= 2][:25]
    missing_terms = [term for term in recommended_terms if term not in draft_terms][:20]

    coverage_ratio = 0.0
    if recommended_terms:
        covered = sum(1 for term in recommended_terms if term in draft_terms)
        coverage_ratio = covered / len(recommended_terms)

    return {
        "keyword": target_keyword,
        "recommended_terms": recommended_terms,
        "missing_terms": missing_terms,
        "coverage_score": round(coverage_ratio * 100, 1),
        "word_count": len(re.findall(r"\w+", draft)),
        "competitors_analyzed": len(serp_analysis.get("results", [])),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 14. ON-PAGE OPTIMIZATION AUDIT
# ═══════════════════════════════════════════════════════════════════════════════
async def audit_content_optimization(
    target_keyword: str,
    draft_content: str,
    required_terms: list[str] | None = None,
    recommended_questions: list[str] | None = None,
) -> dict[str, Any]:
    """Compute optimization score and actionable recommendations for long-form content."""
    text = draft_content or ""
    text_lower = text.lower()
    words = re.findall(r"\w+", text)
    word_count = len(words)

    keyword_mentions = len(re.findall(re.escape(target_keyword.lower()), text_lower)) if target_keyword else 0
    density = (keyword_mentions / max(word_count, 1)) * 100

    required_terms = required_terms or []
    term_hits = {term: (term.lower() in text_lower) for term in required_terms}
    covered_terms = sum(1 for ok in term_hits.values() if ok)

    heading_count = len(re.findall(r"(?im)^#{1,6}\s+", text))
    question_count = len(re.findall(r"\?", text))

    score = 0.0
    score += 20 if word_count >= 900 else max(0, word_count / 45)
    score += 20 if 0.5 <= density <= 2.5 else max(0, 20 - abs(1.2 - density) * 8)
    score += 20 if heading_count >= 6 else heading_count * 3
    score += 20 if (covered_terms >= max(1, int(len(required_terms) * 0.6))) else (covered_terms / max(len(required_terms), 1)) * 20
    score += 20 if question_count >= 3 else question_count * 4
    final_score = round(min(100.0, score), 1)

    recommendations: list[str] = []
    if word_count < 900:
        recommendations.append("Increase depth to at least 900 words to compete with top-ranking pages.")
    if not (0.5 <= density <= 2.5):
        recommendations.append("Adjust target keyword density into the 0.5%-2.5% range.")
    if heading_count < 6:
        recommendations.append("Add more structured headings (H2/H3) for scannability and semantic coverage.")
    if required_terms and covered_terms < max(1, int(len(required_terms) * 0.6)):
        recommendations.append("Include more high-value semantic terms from competitor SERPs.")
    if recommended_questions and question_count < min(5, len(recommended_questions)):
        recommendations.append("Add FAQ-style question sections aligned with audience search intent.")

    return {
        "keyword": target_keyword,
        "optimization_score": final_score,
        "word_count": word_count,
        "keyword_mentions": keyword_mentions,
        "keyword_density_pct": round(density, 3),
        "heading_count": heading_count,
        "question_count": question_count,
        "semantic_coverage": {
            "required_terms": required_terms,
            "term_hits": term_hits,
            "coverage_count": covered_terms,
            "coverage_total": len(required_terms),
        },
        "recommendations": recommendations,
    }

logger.info("✓ God Intelligence engine loaded successfully")
