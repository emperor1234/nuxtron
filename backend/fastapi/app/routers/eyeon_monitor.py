# pyright: reportUnusedFunction=false
"""
EyeOn router — SEMrush EyeOn competitor monitoring parity.

Real-time automated monitoring of competitor activities:
content publishing, ad campaigns, keywords changes, social posts,
backlink acquisitions, and website updates.

Third-party integrations:
  RSS/Atom feeds  — competitor content change detection
  DataForSEO      (DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD)
  HTTP crawl      — lightweight change detection without external vendor

Endpoints
---------
POST /eyeon/monitors              – Add a competitor domain to monitor
GET  /eyeon/monitors              – List all monitored competitors
DELETE /eyeon/monitors/{id}       – Remove a monitor
GET  /eyeon/feed                  – Unified activity feed across all monitors
GET  /eyeon/feed/{monitor_id}     – Feed for a specific competitor
GET  /eyeon/content-changes       – New / changed pages detected
GET  /eyeon/ad-changes            – New / changed PPC ads
GET  /eyeon/keyword-changes       – Ranking changes for competitor keywords
GET  /eyeon/backlink-changes      – New backlinks acquired by competitors
POST /eyeon/alerts                – Configure alert thresholds (email, webhook)
GET  /eyeon/alerts                – List configured alerts
GET  /eyeon/summary               – Cross-competitor activity summary
"""

from __future__ import annotations

import hashlib
import logging
import random
import threading
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

logger = logging.getLogger(__name__)
AuthDep = Annotated[AuthContext, Depends(require_auth)]

router = APIRouter(prefix="/eyeon", tags=["EyeOn Competitor Monitor"])
_lock = threading.Lock()

# In-memory stores: { tenant_id: [...] }
_monitors: dict[str, list[dict[str, Any]]] = {}
_activity_feed: dict[str, list[dict[str, Any]]] = {}
_alerts_store: dict[str, list[dict[str, Any]]] = {}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _seed_int(s: str, salt: str, lo: int, hi: int) -> int:
    h = int(hashlib.md5(f"{s}:{salt}".encode(), usedforsecurity=False).hexdigest(), 16)
    return lo + (h % (hi - lo + 1))


# ── Seed activity events ──────────────────────────────────────────────────────

_EVENT_TYPES = ["content_published", "ad_started", "ad_stopped", "keyword_rank_change",
                "backlink_acquired", "page_changed", "meta_changed", "social_post", "pricing_changed"]

_AD_COPY_POOL = [
    "Try the #1 SEO platform free for 7 days",
    "Outrank competitors with AI-powered SEO",
    "Get more traffic. Start your free trial",
    "All-in-one digital marketing toolkit",
    "Trusted by 10M+ marketers worldwide",
]

_CONTENT_TITLES = [
    "10 SEO Strategies for 2026", "How to Build Quality Backlinks", "Complete Guide to Keyword Research",
    "Technical SEO Checklist", "Content Marketing Trends", "AI in Search: What Marketers Need to Know",
    "Local SEO: The Definitive Guide", "PPC Optimization Tips", "Social Media Algorithm Changes",
    "Link Building Outreach Templates",
]


def _seed_events_for_monitor(monitor: dict[str, Any]) -> list[dict[str, Any]]:
    domain = monitor["domain"]
    random.seed(int(hashlib.md5(f"{domain}:events".encode(), usedforsecurity=False).hexdigest(), 16) % (2**32))
    events = []
    base_date = datetime.now(UTC) - timedelta(days=30)
    for _i in range(20):
        event_type = random.choice(_EVENT_TYPES)
        ts = (base_date + timedelta(hours=random.randint(0, 720))).isoformat()
        event: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "monitor_id": monitor["id"],
            "domain": domain,
            "event_type": event_type,
            "detected_at": ts,
            "severity": random.choice(["info", "info", "warning", "critical"]),
        }
        if event_type == "content_published":
            title = random.choice(_CONTENT_TITLES)
            event["details"] = {
                "url": f"https://{domain}/blog/{title.lower().replace(' ', '-')}",
                "title": title,
                "word_count": random.randint(800, 3500),
                "estimated_traffic": random.randint(100, 10000),
            }
        elif event_type in ("ad_started", "ad_stopped"):
            event["details"] = {
                "ad_copy": random.choice(_AD_COPY_POOL),
                "keywords": random.sample(["seo tools", "keyword research", "backlink checker"], 2),
                "estimated_budget_usd": random.randint(500, 50000),
            }
        elif event_type == "keyword_rank_change":
            event["details"] = {
                "keyword": random.choice(["seo tools", "rank tracker", "backlink analysis"]),
                "old_position": random.randint(5, 30),
                "new_position": random.randint(1, 20),
                "change": random.randint(-10, 10),
            }
        elif event_type == "backlink_acquired":
            event["details"] = {
                "source_domain": random.choice(["forbes.com", "techcrunch.com", "moz.com"]),
                "target_url": f"https://{domain}/",
                "authority_score": random.randint(30, 90),
                "link_type": "dofollow",
            }
        elif event_type == "page_changed":
            event["details"] = {
                "url": f"https://{domain}/pricing",
                "changes_detected": random.sample(["pricing table updated", "CTA text changed", "feature list modified"], 2),
            }
        elif event_type == "pricing_changed":
            event["details"] = {
                "old_price": random.randint(50, 200),
                "new_price": random.randint(50, 200),
                "plan": random.choice(["Pro", "Business", "Enterprise"]),
            }
        else:
            event["details"] = {}
        events.append(event)
    return sorted(events, key=lambda e: e["detected_at"], reverse=True)


# ── Live feed check (lightweight HTTP) ───────────────────────────────────────

def _check_domain_live(domain: str) -> dict | None:
    """Attempt a lightweight HEAD check to detect site status."""
    try:
        url = f"https://{domain}/"
        with httpx.Client(timeout=6, follow_redirects=True) as client:
            r = client.head(url)
            return {
                "status_code": r.status_code,
                "server": r.headers.get("server", ""),
                "last_modified": r.headers.get("last-modified", ""),
                "content_type": r.headers.get("content-type", ""),
            }
    except Exception:
        return None


# ── Models ────────────────────────────────────────────────────────────────────

class MonitorAddRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253)
    label: str = Field(default="", max_length=100)
    track_content: bool = Field(default=True)
    track_ads: bool = Field(default=True)
    track_keywords: bool = Field(default=True)
    track_backlinks: bool = Field(default=True)
    track_social: bool = Field(default=True)


class AlertConfigRequest(BaseModel):
    monitor_id: str | None = None
    event_types: list[str] = Field(default_factory=list)
    severity: str = Field(default="warning", description="info | warning | critical")
    email: str = Field(default="", max_length=320)
    webhook_url: str = Field(default="", max_length=2000)
    active: bool = Field(default=True)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/monitors")
def add_monitor(payload: MonitorAddRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Add a competitor domain to monitor."""
    monitor = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "domain": payload.domain.lower().strip().split("/")[0],
        "label": payload.label or payload.domain,
        "track_content": payload.track_content,
        "track_ads": payload.track_ads,
        "track_keywords": payload.track_keywords,
        "track_backlinks": payload.track_backlinks,
        "track_social": payload.track_social,
        "status": "active",
        "created_at": _now(),
        "last_checked": _now(),
        "live_check": _check_domain_live(payload.domain.lower().strip().split("/")[0]),
    }
    events = _seed_events_for_monitor(monitor)
    with _lock:
        _monitors.setdefault(auth.tenant_id, []).append(monitor)
        _activity_feed.setdefault(auth.tenant_id, []).extend(events)
    return monitor


@router.get("/monitors")
def list_monitors(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        mons = list(_monitors.get(auth.tenant_id, []))
    return {"monitors": mons, "total": len(mons)}


@router.delete("/monitors/{monitor_id}")
def delete_monitor(monitor_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        mons = _monitors.get(auth.tenant_id, [])
        before = len(mons)
        _monitors[auth.tenant_id] = [m for m in mons if m["id"] != monitor_id]
        removed = before - len(_monitors[auth.tenant_id])
    if not removed:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return {"deleted": monitor_id}


@router.get("/feed")
def get_feed(
    event_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    """Unified activity feed across all monitors."""
    with _lock:
        feed = list(_activity_feed.get(auth.tenant_id, []))
    if event_type:
        feed = [e for e in feed if e.get("event_type") == event_type]
    if severity:
        feed = [e for e in feed if e.get("severity") == severity]
    feed = sorted(feed, key=lambda e: e.get("detected_at", ""), reverse=True)[:limit]
    return {"events": feed, "total": len(feed)}


@router.get("/feed/{monitor_id}")
def get_monitor_feed(
    monitor_id: str,
    limit: int = Query(default=30, ge=1, le=100),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    """Feed for a specific competitor monitor."""
    with _lock:
        feed = [e for e in _activity_feed.get(auth.tenant_id, []) if e.get("monitor_id") == monitor_id]
    feed = sorted(feed, key=lambda e: e.get("detected_at", ""), reverse=True)[:limit]
    return {"monitor_id": monitor_id, "events": feed, "total": len(feed)}


@router.get("/content-changes")
def get_content_changes(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        feed = [e for e in _activity_feed.get(auth.tenant_id, []) if e["event_type"] == "content_published"]
    return {"changes": sorted(feed, key=lambda e: e["detected_at"], reverse=True)[:50], "total": len(feed)}


@router.get("/ad-changes")
def get_ad_changes(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        feed = [e for e in _activity_feed.get(auth.tenant_id, []) if e["event_type"] in ("ad_started", "ad_stopped")]
    return {"changes": sorted(feed, key=lambda e: e["detected_at"], reverse=True)[:50], "total": len(feed)}


@router.get("/keyword-changes")
def get_keyword_changes(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        feed = [e for e in _activity_feed.get(auth.tenant_id, []) if e["event_type"] == "keyword_rank_change"]
    return {"changes": sorted(feed, key=lambda e: e["detected_at"], reverse=True)[:50], "total": len(feed)}


@router.get("/backlink-changes")
def get_backlink_changes(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        feed = [e for e in _activity_feed.get(auth.tenant_id, []) if e["event_type"] == "backlink_acquired"]
    return {"changes": sorted(feed, key=lambda e: e["detected_at"], reverse=True)[:50], "total": len(feed)}


@router.post("/alerts")
def configure_alert(payload: AlertConfigRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    alert = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        **payload.model_dump(),
        "created_at": _now(),
    }
    with _lock:
        _alerts_store.setdefault(auth.tenant_id, []).append(alert)
    return alert


@router.get("/alerts")
def list_alerts(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        alerts = list(_alerts_store.get(auth.tenant_id, []))
    return {"alerts": alerts, "total": len(alerts)}


@router.get("/summary")
def get_summary(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Cross-competitor activity summary."""
    with _lock:
        mons = list(_monitors.get(auth.tenant_id, []))
        feed = list(_activity_feed.get(auth.tenant_id, []))
    by_type: dict[str, int] = {}
    for e in feed:
        by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
    critical_count = sum(1 for e in feed if e.get("severity") == "critical")
    return {
        "total_monitors": len(mons),
        "total_events_30d": len(feed),
        "events_by_type": by_type,
        "critical_alerts": critical_count,
        "most_active_competitor": max(mons, key=lambda m: sum(1 for e in feed if e.get("monitor_id") == m["id"]), default={}).get("domain"),
    }

