# pyright: reportUnusedFunction=false
"""
Domain Overview router — SEMrush-parity domain intelligence.

Real third-party integration: DataForSEO API (https://dataforseo.com/)
  DATAFORSEO_LOGIN  – DataForSEO account login (email)
  DATAFORSEO_PASSWORD – DataForSEO account password

Endpoints
---------
GET  /domain-overview/summary                   – Full domain metrics snapshot
GET  /domain-overview/organic-keywords          – Top organic keywords for domain
GET  /domain-overview/paid-keywords             – Top paid/PPC keywords for domain
GET  /domain-overview/backlinks-snapshot        – Quick backlink count + authority
GET  /domain-overview/competitors               – Organic competitors list
GET  /domain-overview/traffic-trend             – 12-month organic traffic estimate
POST /domain-overview/bulk                      – Bulk domain compare (up to 5 domains)

Data vendors: DataForSEO (primary), deterministic seed fallback.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import random
import threading
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

logger = logging.getLogger(__name__)

AuthDep = Annotated[AuthContext, Depends(require_auth)]

router = APIRouter(prefix="/domain-overview", tags=["Domain Overview"])

_lock = threading.Lock()

# ── DataForSEO helpers ────────────────────────────────────────────────────────

def _dataforseo_auth() -> str | None:
    login = os.getenv("DATAFORSEO_LOGIN", "").strip()
    password = os.getenv("DATAFORSEO_PASSWORD", "").strip()
    if login and password:
        token = base64.b64encode(f"{login}:{password}".encode()).decode()
        return f"Basic {token}"
    return None


def _dataforseo_request(path: str, payload: list[dict]) -> dict | None:
    auth = _dataforseo_auth()
    if not auth:
        return None
    url = f"https://api.dataforseo.com{path}"
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(url, headers={"Authorization": auth, "Content-Type": "application/json"}, json=payload)
            r.raise_for_status()
            data = r.json()
            if data.get("status_code") == 20000:
                return data
    except Exception as exc:
        logger.warning("DataForSEO request failed: %s", exc)
    return None


# ── Seed helpers ──────────────────────────────────────────────────────────────

def _seed_int(domain: str, salt: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(f"{domain}:{salt}".encode(), usedforsecurity=False).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


def _seed_float(domain: str, salt: str, lo: float, hi: float, decimals: int = 2) -> float:
    h = int(hashlib.md5(f"{domain}:{salt}".encode(), usedforsecurity=False).hexdigest(), 16) % 10000
    return round(lo + (h / 10000) * (hi - lo), decimals)


_KEYWORD_POOL = [
    "digital marketing tools", "seo software", "social media management", "content marketing platform",
    "marketing automation", "rank tracking tool", "backlink checker", "keyword research",
    "ai writing assistant", "brand monitoring", "competitor analysis", "site audit tool",
    "ppc management", "email marketing", "landing page builder", "crm software",
    "influencer marketing", "link building service", "local seo tools", "web analytics",
]

_COMPETITOR_POOL = [
    "ahrefs.com", "moz.com", "hubspot.com", "mailchimp.com", "sproutsocial.com",
    "hootsuite.com", "buffer.com", "similarweb.com", "serpstat.com", "majestic.com",
    "wordstream.com", "conductor.com", "brightedge.com", "searchmetrics.com",
]


def _make_domain_summary(domain: str) -> dict[str, Any]:
    authority = _seed_int(domain, "auth", 5, 95)
    organic_traffic = _seed_int(domain, "traffic", 1000, 5_000_000)
    keywords_organic = _seed_int(domain, "kworg", 500, 500_000)
    keywords_paid = _seed_int(domain, "kwpaid", 0, 50_000)
    backlinks = _seed_int(domain, "bl", 100, 10_000_000)
    referring_domains = _seed_int(domain, "rd", 50, 500_000)
    paid_traffic = _seed_int(domain, "ptraffic", 0, 200_000)
    adwords_budget = _seed_float(domain, "budget", 0, 500_000)
    return {
        "domain": domain,
        "authority_score": authority,
        "organic_traffic_monthly": organic_traffic,
        "organic_keywords": keywords_organic,
        "paid_keywords": keywords_paid,
        "paid_traffic_monthly": paid_traffic,
        "adwords_budget_usd": adwords_budget,
        "backlinks_total": backlinks,
        "referring_domains": referring_domains,
        "spam_score": _seed_int(domain, "spam", 0, 30),
        "indexed_pages": _seed_int(domain, "pages", 100, 5_000_000),
        "country_top": "US",
        "traffic_cost_usd": _seed_float(domain, "tcost", 0, 5_000_000),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _make_organic_keywords(domain: str, limit: int = 20) -> list[dict[str, Any]]:
    random.seed(int(hashlib.md5(f"{domain}:kworg_list".encode(), usedforsecurity=False).hexdigest(), 16) % (2**32))
    sample = random.sample(_KEYWORD_POOL, min(limit, len(_KEYWORD_POOL)))
    results = []
    for kw in sample:
        pos = random.randint(1, 50)
        vol = random.randint(500, 80000)
        results.append({
            "keyword": kw,
            "position": pos,
            "search_volume": vol,
            "traffic": int(vol * 0.25 * max(0.01, (101 - pos) / 100)),
            "traffic_pct": round(random.uniform(0.1, 5.0), 2),
            "keyword_difficulty": random.randint(10, 90),
            "cpc_usd": round(random.uniform(0.10, 15.00), 2),
            "url": f"https://{domain}/",
            "serp_features": random.sample(["featured_snippet", "image_pack", "people_also_ask", "video", "local_pack"], k=random.randint(0, 2)),
        })
    return results


def _make_paid_keywords(domain: str, limit: int = 20) -> list[dict[str, Any]]:
    random.seed(int(hashlib.md5(f"{domain}:kwpaid_list".encode(), usedforsecurity=False).hexdigest(), 16) % (2**32))
    sample = random.sample(_KEYWORD_POOL, min(limit, len(_KEYWORD_POOL)))
    results = []
    for kw in sample:
        pos = random.randint(1, 4)
        vol = random.randint(200, 50000)
        results.append({
            "keyword": kw,
            "ad_position": pos,
            "search_volume": vol,
            "traffic": int(vol * 0.15),
            "cpc_usd": round(random.uniform(0.50, 25.00), 2),
            "competition": round(random.uniform(0.1, 1.0), 2),
            "ad_title": f"Best {kw.title()} Tool | Try Free",
            "ad_description": f"Powerful {kw} software. Get insights in minutes. Start free trial today.",
        })
    return results


def _make_competitors(domain: str, limit: int = 10) -> list[dict[str, Any]]:
    random.seed(int(hashlib.md5(f"{domain}:comps".encode(), usedforsecurity=False).hexdigest(), 16) % (2**32))
    sample = random.sample(_COMPETITOR_POOL, min(limit, len(_COMPETITOR_POOL)))
    return [
        {
            "domain": c,
            "common_keywords": random.randint(100, 50000),
            "organic_traffic": random.randint(5000, 3_000_000),
            "paid_keywords": random.randint(0, 20000),
            "authority_score": random.randint(20, 90),
            "competition_level": round(random.uniform(0.1, 1.0), 2),
        }
        for c in sample
    ]


def _make_traffic_trend(domain: str) -> list[dict[str, Any]]:
    base = _seed_int(domain, "trendbase", 5000, 500_000)
    trend = []
    for i in range(12):
        dt = (datetime.now(UTC) - timedelta(days=30 * (11 - i))).strftime("%Y-%m")
        variation = _seed_float(domain, f"trend{i}", 0.8, 1.2)
        trend.append({"month": dt, "organic_traffic": int(base * variation)})
    return trend


# ── DataForSEO live integration ───────────────────────────────────────────────

def _live_domain_summary(domain: str) -> dict[str, Any] | None:
    payload = [{"target": domain, "location_code": 2840, "language_code": "en"}]
    data = _dataforseo_request("/v3/dataforseo_labs/google/domain_rank_overview/live", payload)
    if not data:
        return None
    try:
        item = data["tasks"][0]["result"][0]["items"][0]
        metrics = item.get("metrics", {}).get("organic", {})
        return {
            "domain": domain,
            "authority_score": item.get("domain_rank", 0),
            "organic_traffic_monthly": metrics.get("etv", 0),
            "organic_keywords": metrics.get("count", 0),
            "paid_keywords": item.get("metrics", {}).get("paid", {}).get("count", 0),
            "paid_traffic_monthly": item.get("metrics", {}).get("paid", {}).get("etv", 0),
            "adwords_budget_usd": 0,
            "backlinks_total": 0,
            "referring_domains": 0,
            "spam_score": 0,
            "indexed_pages": 0,
            "country_top": "US",
            "traffic_cost_usd": metrics.get("estimated_paid_traffic_cost", 0),
            "generated_at": datetime.now(UTC).isoformat(),
            "_source": "dataforseo",
        }
    except (KeyError, IndexError):
        return None


def _live_organic_keywords(domain: str, limit: int = 20) -> list[dict] | None:
    payload = [{"target": domain, "location_code": 2840, "language_code": "en", "limit": limit}]
    data = _dataforseo_request("/v3/dataforseo_labs/google/ranked_keywords/live", payload)
    if not data:
        return None
    try:
        items = data["tasks"][0]["result"][0]["items"]
        return [
            {
                "keyword": it["keyword_data"]["keyword"],
                "position": it["ranked_serp_element"]["serp_item"].get("rank_absolute", 0),
                "search_volume": it["keyword_data"]["keyword_info"].get("search_volume", 0),
                "traffic": it["ranked_serp_element"]["serp_item"].get("etv", 0),
                "traffic_pct": 0,
                "keyword_difficulty": it["keyword_data"]["keyword_properties"].get("keyword_difficulty", 0),
                "cpc_usd": it["keyword_data"]["keyword_info"].get("cpc", 0),
                "url": it["ranked_serp_element"]["serp_item"].get("relative_url", ""),
                "serp_features": [],
                "_source": "dataforseo",
            }
            for it in items[:limit]
        ]
    except (KeyError, IndexError):
        return None


# ── Models ────────────────────────────────────────────────────────────────────

class BulkCompareRequest(BaseModel):
    domains: list[str] = Field(min_length=1, max_length=5, description="Up to 5 domains to compare")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_domain_summary(
    domain: str = Query(min_length=3, max_length=253, description="Domain, e.g. example.com"),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    """Full domain metrics snapshot — DataForSEO live, seed fallback."""
    domain = domain.lower().strip().removeprefix("https://").removeprefix("http://").split("/")[0]
    live = _live_domain_summary(domain)
    if live:
        return live
    return _make_domain_summary(domain)


@router.get("/organic-keywords")
def get_organic_keywords(
    domain: str = Query(min_length=3, max_length=253),
    limit: int = Query(default=20, ge=1, le=100),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    """Top organic keywords for domain."""
    domain = domain.lower().strip().split("/")[0]
    live = _live_organic_keywords(domain, limit)
    if live is not None:
        return {"domain": domain, "keywords": live, "total": len(live), "_source": "dataforseo"}
    kws = _make_organic_keywords(domain, limit)
    return {"domain": domain, "keywords": kws, "total": len(kws), "_source": "seed"}


@router.get("/paid-keywords")
def get_paid_keywords(
    domain: str = Query(min_length=3, max_length=253),
    limit: int = Query(default=20, ge=1, le=100),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    """Top PPC/paid keywords for domain."""
    domain = domain.lower().strip().split("/")[0]
    kws = _make_paid_keywords(domain, limit)
    return {"domain": domain, "keywords": kws, "total": len(kws), "_source": "seed"}


@router.get("/backlinks-snapshot")
def get_backlinks_snapshot(
    domain: str = Query(min_length=3, max_length=253),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    """Quick backlink count + authority via DataForSEO backlinks summary."""
    domain = domain.lower().strip().split("/")[0]
    # Try DataForSEO backlinks summary
    payload = [{"target": domain, "limit": 1}]
    data = _dataforseo_request("/v3/backlinks/summary/live", payload)
    if data:
        try:
            item = data["tasks"][0]["result"][0]
            return {
                "domain": domain,
                "total_backlinks": item.get("total_count", 0),
                "referring_domains": item.get("referring_domains", 0),
                "dofollow": item.get("referring_links_types", {}).get("follow", 0),
                "nofollow": item.get("referring_links_types", {}).get("nofollow", 0),
                "authority_score": item.get("rank", 0),
                "_source": "dataforseo",
            }
        except (KeyError, IndexError):
            pass
    # Seed
    return {
        "domain": domain,
        "total_backlinks": _seed_int(domain, "bl", 100, 5_000_000),
        "referring_domains": _seed_int(domain, "rd", 50, 300_000),
        "dofollow": _seed_int(domain, "df", 50, 3_000_000),
        "nofollow": _seed_int(domain, "nf", 10, 500_000),
        "authority_score": _seed_int(domain, "auth", 5, 95),
        "_source": "seed",
    }


@router.get("/competitors")
def get_domain_competitors(
    domain: str = Query(min_length=3, max_length=253),
    limit: int = Query(default=10, ge=1, le=20),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    """Organic competitor domains."""
    domain = domain.lower().strip().split("/")[0]
    # Try DataForSEO
    payload = [{"target": domain, "location_code": 2840, "language_code": "en", "limit": limit}]
    data = _dataforseo_request("/v3/dataforseo_labs/google/competitors_domain/live", payload)
    if data:
        try:
            items = data["tasks"][0]["result"][0]["items"]
            comps = [
                {
                    "domain": it["domain"],
                    "common_keywords": it.get("intersections", 0),
                    "organic_traffic": it.get("metrics", {}).get("organic", {}).get("etv", 0),
                    "authority_score": it.get("domain_rank", 0),
                    "competition_level": it.get("competition_level", 0),
                }
                for it in items[:limit]
            ]
            return {"domain": domain, "competitors": comps, "total": len(comps), "_source": "dataforseo"}
        except (KeyError, IndexError):
            pass
    comps = _make_competitors(domain, limit)
    return {"domain": domain, "competitors": comps, "total": len(comps), "_source": "seed"}


@router.get("/traffic-trend")
def get_traffic_trend(
    domain: str = Query(min_length=3, max_length=253),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    """12-month organic traffic trend."""
    domain = domain.lower().strip().split("/")[0]
    trend = _make_traffic_trend(domain)
    return {"domain": domain, "trend": trend, "months": len(trend), "_source": "seed"}


@router.post("/bulk")
def bulk_compare(
    payload: BulkCompareRequest,
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    """Bulk domain compare — up to 5 domains side-by-side."""
    results = []
    for domain in payload.domains:
        domain = domain.lower().strip().split("/")[0]
        live = _live_domain_summary(domain)
        results.append(live if live else _make_domain_summary(domain))
    return {"domains": payload.domains, "results": results, "count": len(results)}
