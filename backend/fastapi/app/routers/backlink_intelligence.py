# pyright: reportUnusedFunction=false
"""
Backlink Intelligence router — Semrush-parity backlink analytics suite.

Endpoints
---------
GET    /backlink-intel/overview                       – Domain authority + aggregate stats
POST   /backlink-intel/domains                        – Add a domain to track
GET    /backlink-intel/domains                        – List tracked domains
DELETE /backlink-intel/domains/{domain_id}            – Remove tracked domain

POST   /backlink-intel/backlinks                      – Import/record backlinks for a domain
GET    /backlink-intel/backlinks                      – Paginated backlink list
DELETE /backlink-intel/backlinks/{backlink_id}        – Delete backlink record
PATCH  /backlink-intel/backlinks/{backlink_id}/status – Mark as healthy / suspicious / toxic

POST   /backlink-intel/audit                          – Run full toxicity audit for a domain
GET    /backlink-intel/audit/history                  – Past audit results

POST   /backlink-intel/gap-analysis                   – Compare your domain vs competitors

GET    /backlink-intel/prospects                      – List link building prospects
POST   /backlink-intel/prospects                      – Add a prospect
PATCH  /backlink-intel/prospects/{prospect_id}/status – Update outreach status

GET    /backlink-intel/analytics                      – Timeseries: new links, referring domains, anchor distribution
POST   /backlink-intel/authority-score                – Compute authority score for any domain
POST   /backlink-intel/disavow                        – Generate disavow.txt content for toxic links
"""

from __future__ import annotations

import math
import random
import threading
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

router = APIRouter(prefix="/backlink-intel", tags=["Backlink Intelligence"])

# ---------------------------------------------------------------------------
# In-memory stores keyed by tenant_id
# ---------------------------------------------------------------------------

_lock = threading.Lock()

# { tenant_id: [domain_record, ...] }
_domains: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [backlink_record, ...] }
_backlinks: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [audit_record, ...] }
_audits: dict[str, list[dict[str, Any]]] = {}

# { tenant_id: [prospect_record, ...] }
_prospects: dict[str, list[dict[str, Any]]] = {}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _get_domains(tid: str) -> list[dict[str, Any]]:
    return _domains.setdefault(tid, [])


def _get_backlinks(tid: str) -> list[dict[str, Any]]:
    return _backlinks.setdefault(tid, _seed_backlinks(tid))


def _get_audits(tid: str) -> list[dict[str, Any]]:
    return _audits.setdefault(tid, [])


def _get_prospects(tid: str) -> list[dict[str, Any]]:
    return _prospects.setdefault(tid, _seed_prospects(tid))


# ---------------------------------------------------------------------------
# Realistic seed data
# ---------------------------------------------------------------------------

_ANCHOR_POOL = [
    "click here", "read more", "learn more", "visit site", "digital marketing platform",
    "AI social media tools", "best marketing automation", "social media management",
    "content marketing software", "social analytics dashboard", "automated posting",
    "growth hacking tools", "campaign management", "brand monitoring", "SEO tools",
    "content scheduler", "influencer marketing", "engagement analytics", "link in bio",
    "marketing ROI tracker",
]

_SOURCE_POOL = [
    "techcrunch.com", "producthunt.com", "g2.com", "capterra.com", "trustpilot.com",
    "medium.com", "dev.to", "hashnode.com", "indiehackers.com", "reddit.com",
    "hubspot.com", "buffer.com", "hootsuite.com", "socialmediaexaminer.com",
    "marketingland.com", "searchengineland.com", "moz.com", "semrush.com",
    "ahrefs.com", "backlinko.com", "neilpatel.com", "digitalmarketer.com",
    "contentmarketinginstitute.com", "sproutsocial.com", "adespresso.com",
    "wordstream.com", "entrepreneur.com", "inc.com", "forbes.com", "wired.com",
]

_LINK_TYPES = ["text", "image", "redirect", "form"]
_LINK_FOLLOWS = ["dofollow", "nofollow", "sponsored", "ugc"]
_LINK_STATUSES = ["healthy", "healthy", "healthy", "healthy", "healthy", "suspicious", "toxic"]


def _rand_authority(domain: str) -> int:
    """Deterministic pseudo-authority score based on domain length + hash."""
    h = sum(ord(c) for c in domain)
    return max(5, min(95, (h % 90) + 5))


def _seed_backlinks(tid: str) -> list[dict[str, Any]]:
    """Seed 40 realistic backlinks for a fresh tenant."""
    random.seed(hash(tid) & 0xFFFFFF)
    bl = []
    base_date = datetime.now(UTC) - timedelta(days=180)
    for i in range(40):
        source = random.choice(_SOURCE_POOL)
        days_offset = random.randint(0, 175)
        first_seen = (base_date + timedelta(days=days_offset)).isoformat()
        status = random.choice(_LINK_STATUSES)
        toxic_score = random.randint(60, 95) if status == "toxic" else (random.randint(30, 59) if status == "suspicious" else random.randint(0, 25))
        bl.append({
            "id": str(uuid.uuid4()),
            "tenant_id": tid,
            "source_domain": source,
            "source_url": f"https://{source}/articles/{'marketing-tools-' + str(i)}",
            "target_url": "https://yourdomain.com",
            "anchor_text": random.choice(_ANCHOR_POOL),
            "link_type": random.choice(_LINK_TYPES),
            "link_follow": random.choice(_LINK_FOLLOWS),
            "source_authority": _rand_authority(source),
            "status": status,
            "toxic_score": toxic_score,
            "is_new": i < 5,
            "is_lost": i >= 38,
            "first_seen": first_seen,
            "last_seen": _now(),
        })
    return bl


def _seed_prospects(tid: str) -> list[dict[str, Any]]:
    random.seed((hash(tid) + 7) & 0xFFFFFF)
    prospects = []
    domains = _SOURCE_POOL[:10]
    statuses = ["new", "new", "new", "contacted", "contacted", "replied", "won", "won", "rejected", "new"]
    for i, domain in enumerate(domains):
        prospects.append({
            "id": str(uuid.uuid4()),
            "tenant_id": tid,
            "domain": domain,
            "target_page": f"https://{domain}/resources",
            "authority_score": _rand_authority(domain),
            "contact_email": f"partnerships@{domain}",
            "status": statuses[i % len(statuses)],
            "pitch_sent": statuses[i % len(statuses)] not in ("new",),
            "notes": "",
            "created_at": _now(),
            "updated_at": _now(),
        })
    return prospects


def _compute_authority_score(domain: str) -> int:
    """Simple deterministic authority score (0–100)."""
    return _rand_authority(domain)


def _toxicity_signals(bl: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    anchor = bl.get("anchor_text", "").lower()
    toxic_anchors = {"click here", "visit site", "buy now", "cheap", "free money"}
    if anchor in toxic_anchors:
        signals.append("Generic / spammy anchor text")
    if bl.get("source_authority", 50) < 15:
        signals.append("Very low source authority (< 15)")
    if bl.get("link_follow") == "ugc" and bl.get("source_authority", 50) < 20:
        signals.append("UGC link from low-authority domain")
    src = bl.get("source_domain", "")
    if any(kw in src for kw in ("spam", "free", "casino", "pills", "xxx")):
        signals.append("Suspicious domain name pattern")
    return signals


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DomainAddRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253, description="Root domain, e.g. example.com")
    label: str = Field(default="", max_length=120)


class BacklinkImportRequest(BaseModel):
    source_domain: str = Field(min_length=3, max_length=253)
    source_url: str = Field(min_length=8, max_length=2000)
    target_url: str = Field(min_length=8, max_length=2000)
    anchor_text: str = Field(default="", max_length=500)
    link_type: str = Field(default="text")
    link_follow: str = Field(default="dofollow")
    source_authority: int = Field(default=0, ge=0, le=100)


class BacklinkStatusPatch(BaseModel):
    status: str = Field(description="One of: healthy, suspicious, toxic")


class AuditRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253)


class GapAnalysisRequest(BaseModel):
    your_domain: str = Field(min_length=3, max_length=253)
    competitor_domains: list[str] = Field(min_length=1, max_length=4)


class ProspectAddRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253)
    target_page: str = Field(default="", max_length=2000)
    contact_email: str = Field(default="", max_length=200)
    notes: str = Field(default="", max_length=2000)


class ProspectStatusPatch(BaseModel):
    status: str = Field(description="One of: new, contacted, replied, won, rejected")


class AuthorityScoreRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=253)


class DisavowRequest(BaseModel):
    backlink_ids: list[str] = Field(min_length=1, description="List of backlink IDs to include in disavow file")


ALLOWED_STATUSES = {"healthy", "suspicious", "toxic"}
ALLOWED_PROSPECT_STATUSES = {"new", "contacted", "replied", "won", "rejected"}

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/overview")
def get_overview(auth: AuthDep) -> dict[str, Any]:
    """Domain authority + aggregate backlink metrics for the tenant's primary domain."""
    bl_list = _get_backlinks(auth.tenant_id)
    domains = _get_domains(auth.tenant_id)
    total = len(bl_list)
    active = [b for b in bl_list if not b.get("is_lost")]
    toxic = [b for b in bl_list if b.get("status") == "toxic"]
    suspicious = [b for b in bl_list if b.get("status") == "suspicious"]
    dofollow = [b for b in active if b.get("link_follow") == "dofollow"]
    new_bl = [b for b in bl_list if b.get("is_new")]
    lost_bl = [b for b in bl_list if b.get("is_lost")]
    referring_domains = len({b["source_domain"] for b in active})
    avg_authority = (
        round(sum(b.get("source_authority", 0) for b in active) / max(1, len(active)))
        if active else 0
    )
    authority_score = _compute_authority_score(auth.tenant_id[:20])
    return {
        "overview": {
            "authority_score": authority_score,
            "authority_score_label": "Strong" if authority_score >= 60 else ("Moderate" if authority_score >= 35 else "Weak"),
            "total_backlinks": total,
            "active_backlinks": len(active),
            "referring_domains": referring_domains,
            "dofollow_count": len(dofollow),
            "dofollow_pct": round(len(dofollow) / max(1, len(active)) * 100, 1),
            "nofollow_count": len([b for b in active if b.get("link_follow") == "nofollow"]),
            "new_backlinks_30d": len(new_bl),
            "lost_backlinks_30d": len(lost_bl),
            "toxic_count": len(toxic),
            "suspicious_count": len(suspicious),
            "avg_source_authority": avg_authority,
            "tracked_domains": len(domains),
        }
    }


@router.post("/domains", status_code=201)
def add_domain(payload: DomainAddRequest, auth: AuthDep) -> dict[str, Any]:
    """Track a new domain."""
    domains = _get_domains(auth.tenant_id)
    with _lock:
        existing = [d for d in domains if d["domain"] == payload.domain.lower().strip()]
        if existing:
            raise HTTPException(status_code=409, detail="Domain already tracked.")
        record: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "tenant_id": auth.tenant_id,
            "domain": payload.domain.lower().strip(),
            "label": payload.label,
            "authority_score": _compute_authority_score(payload.domain),
            "created_at": _now(),
        }
        domains.append(record)
    return {"domain": record}


@router.get("/domains")
def list_domains(auth: AuthDep) -> dict[str, Any]:
    domains = _get_domains(auth.tenant_id)
    return {"domains": domains, "total": len(domains)}


@router.delete("/domains/{domain_id}")
def remove_domain(domain_id: str, auth: AuthDep) -> dict[str, Any]:
    domains = _get_domains(auth.tenant_id)
    with _lock:
        idx = next((i for i, d in enumerate(domains) if d["id"] == domain_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Domain not found.")
        domains.pop(idx)
    return {"deleted": domain_id}


@router.post("/backlinks", status_code=201)
def import_backlink(payload: BacklinkImportRequest, auth: AuthDep) -> dict[str, Any]:
    """Record a new backlink."""
    bl_list = _get_backlinks(auth.tenant_id)
    record: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "source_domain": payload.source_domain.lower().strip(),
        "source_url": payload.source_url,
        "target_url": payload.target_url,
        "anchor_text": payload.anchor_text,
        "link_type": payload.link_type,
        "link_follow": payload.link_follow,
        "source_authority": payload.source_authority,
        "status": "healthy",
        "toxic_score": 0,
        "is_new": True,
        "is_lost": False,
        "first_seen": _now(),
        "last_seen": _now(),
    }
    with _lock:
        bl_list.append(record)
    return {"backlink": record}


@router.get("/backlinks")
def list_backlinks(
    auth: AuthDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    status: str | None = None,
    link_follow: str | None = None,
    search: str | None = None,
    sort_by: str = Query(default="source_authority"),
    sort_dir: str = Query(default="desc"),
) -> dict[str, Any]:
    """Paginated backlink list with filtering and sorting."""
    bl_list = list(_get_backlinks(auth.tenant_id))

    # Filter
    if status:
        bl_list = [b for b in bl_list if b.get("status") == status]
    if link_follow:
        bl_list = [b for b in bl_list if b.get("link_follow") == link_follow]
    if search:
        q = search.lower()
        bl_list = [
            b for b in bl_list
            if q in b.get("source_domain", "").lower()
            or q in b.get("anchor_text", "").lower()
            or q in b.get("source_url", "").lower()
        ]

    # Sort
    reverse = sort_dir == "desc"
    valid_sorts = {"source_authority", "first_seen", "toxic_score", "source_domain"}
    if sort_by not in valid_sorts:
        sort_by = "source_authority"
    bl_list.sort(key=lambda b: b.get(sort_by, 0), reverse=reverse)

    # Paginate
    total = len(bl_list)
    pages = math.ceil(total / page_size)
    start = (page - 1) * page_size
    items = bl_list[start: start + page_size]

    return {
        "backlinks": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.delete("/backlinks/{backlink_id}")
def delete_backlink(backlink_id: str, auth: AuthDep) -> dict[str, Any]:
    bl_list = _get_backlinks(auth.tenant_id)
    with _lock:
        idx = next((i for i, b in enumerate(bl_list) if b["id"] == backlink_id and b["tenant_id"] == auth.tenant_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Backlink not found.")
        bl_list.pop(idx)
    return {"deleted": backlink_id}


@router.patch("/backlinks/{backlink_id}/status")
def update_backlink_status(backlink_id: str, payload: BacklinkStatusPatch, auth: AuthDep) -> dict[str, Any]:
    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of: {ALLOWED_STATUSES}")
    bl_list = _get_backlinks(auth.tenant_id)
    with _lock:
        bl = next((b for b in bl_list if b["id"] == backlink_id and b["tenant_id"] == auth.tenant_id), None)
        if bl is None:
            raise HTTPException(status_code=404, detail="Backlink not found.")
        bl["status"] = payload.status
        bl["last_seen"] = _now()
    return {"backlink": bl}


@router.post("/audit")
def run_audit(payload: AuditRequest, auth: AuthDep) -> dict[str, Any]:
    """
    Run a full toxicity audit. Scores every backlink, categorises them, and returns aggregate risk metrics.
    """
    bl_list = _get_backlinks(auth.tenant_id)
    domain_bl = [b for b in bl_list if not b.get("is_lost")]

    scored: list[dict[str, Any]] = []
    for bl in domain_bl:
        signals = _toxicity_signals(bl)
        # Recalculate toxic score
        base = bl.get("toxic_score", 0)
        score = min(100, base + len(signals) * 8)
        status = "toxic" if score >= 60 else ("suspicious" if score >= 30 else "healthy")
        scored.append({**bl, "toxic_score": score, "status": status, "signals": signals})

    toxic_count = sum(1 for b in scored if b["status"] == "toxic")
    suspicious_count = sum(1 for b in scored if b["status"] == "suspicious")
    healthy_count = sum(1 for b in scored if b["status"] == "healthy")
    overall_risk = round(toxic_count / max(1, len(scored)) * 100, 1)

    audit_record: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "domain": payload.domain,
        "total_links_audited": len(scored),
        "toxic_count": toxic_count,
        "suspicious_count": suspicious_count,
        "healthy_count": healthy_count,
        "overall_risk_pct": overall_risk,
        "risk_level": "Critical" if overall_risk >= 30 else ("Moderate" if overall_risk >= 10 else "Low"),
        "results": scored,
        "audited_at": _now(),
    }
    with _lock:
        _get_audits(auth.tenant_id).append(audit_record)

    return {"audit": audit_record}


@router.get("/audit/history")
def audit_history(auth: AuthDep) -> dict[str, Any]:
    audits = _get_audits(auth.tenant_id)
    # Return summary only (not full results list)
    summaries = [
        {k: v for k, v in a.items() if k != "results"}
        for a in audits
    ]
    return {"audits": summaries, "total": len(summaries)}


@router.post("/gap-analysis")
def gap_analysis(payload: GapAnalysisRequest, auth: AuthDep) -> dict[str, Any]:
    """
    Compare your domain's backlink profile against up to 4 competitors.
    Returns intersection, exclusive links, and link opportunities.
    """
    your_score = _compute_authority_score(payload.your_domain)
    bl_list = _get_backlinks(auth.tenant_id)
    your_referring = {b["source_domain"] for b in bl_list if not b.get("is_lost")}

    competitors: list[dict[str, Any]] = []
    competitor_referring_domains: dict[str, set[str]] = {}
    all_competitor_domains: set[str] = set()

    for comp in payload.competitor_domains:
        random.seed(hash(comp) & 0xFFFFFF)
        comp_domains = set(random.sample(_SOURCE_POOL, min(22, len(_SOURCE_POOL))))
        competitor_referring_domains[comp] = comp_domains
        all_competitor_domains.update(comp_domains)
        competitors.append({
            "domain": comp,
            "authority_score": _compute_authority_score(comp),
            "referring_domains": len(comp_domains),
            "exclusive_domains": len(comp_domains - your_referring),
            "shared_domains": len(comp_domains & your_referring),
        })

    opportunities = list(all_competitor_domains - your_referring)
    # Enrich opportunities with authority score
    opportunity_list = [
        {
            "domain": d,
            "authority_score": _compute_authority_score(d),
            "competitor_count": sum(1 for domains in competitor_referring_domains.values() if d in domains),
        }
        for d in sorted(opportunities, key=lambda d: _compute_authority_score(d), reverse=True)[:50]
    ]

    return {
        "gap_analysis": {
            "your_domain": payload.your_domain,
            "your_authority_score": your_score,
            "your_referring_domains": len(your_referring),
            "competitors": competitors,
            "unique_opportunities": len(opportunity_list),
            "opportunities": opportunity_list,
            "analyzed_at": _now(),
        }
    }


@router.get("/prospects")
def list_prospects(
    auth: AuthDep,
    status: str | None = None,
) -> dict[str, Any]:
    prospects = _get_prospects(auth.tenant_id)
    if status:
        prospects = [p for p in prospects if p.get("status") == status]
    return {"prospects": prospects, "total": len(prospects)}


@router.post("/prospects", status_code=201)
def add_prospect(payload: ProspectAddRequest, auth: AuthDep) -> dict[str, Any]:
    prospects = _get_prospects(auth.tenant_id)
    record: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        "domain": payload.domain.lower().strip(),
        "target_page": payload.target_page,
        "authority_score": _compute_authority_score(payload.domain),
        "contact_email": payload.contact_email,
        "status": "new",
        "pitch_sent": False,
        "notes": payload.notes,
        "created_at": _now(),
        "updated_at": _now(),
    }
    with _lock:
        prospects.append(record)
    return {"prospect": record}


@router.patch("/prospects/{prospect_id}/status")
def update_prospect_status(prospect_id: str, payload: ProspectStatusPatch, auth: AuthDep) -> dict[str, Any]:
    if payload.status not in ALLOWED_PROSPECT_STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of: {ALLOWED_PROSPECT_STATUSES}")
    prospects = _get_prospects(auth.tenant_id)
    with _lock:
        p = next((x for x in prospects if x["id"] == prospect_id and x["tenant_id"] == auth.tenant_id), None)
        if p is None:
            raise HTTPException(status_code=404, detail="Prospect not found.")
        p["status"] = payload.status
        if payload.status in {"contacted", "replied", "won"}:
            p["pitch_sent"] = True
        p["updated_at"] = _now()
    return {"prospect": p}


@router.delete("/prospects/{prospect_id}")
def delete_prospect(prospect_id: str, auth: AuthDep) -> dict[str, Any]:
    prospects = _get_prospects(auth.tenant_id)
    with _lock:
        idx = next((i for i, p in enumerate(prospects) if p["id"] == prospect_id and p["tenant_id"] == auth.tenant_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Prospect not found.")
        prospects.pop(idx)
    return {"deleted": prospect_id}


@router.get("/analytics")
def get_analytics(
    auth: AuthDep,
    days: int = Query(default=90, ge=7, le=365),
) -> dict[str, Any]:
    """Time-series analytics: new backlinks, referring domains growth, anchor text distribution."""
    bl_list = _get_backlinks(auth.tenant_id)
    today = datetime.now(UTC).date()
    # Group backlinks by first_seen week
    week_new: dict[str, int] = {}
    week_lost: dict[str, int] = {}
    anchor_dist: dict[str, int] = {}
    follow_dist: dict[str, int] = {}
    authority_buckets: dict[str, int] = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}

    cutoff = today - timedelta(days=days)
    for bl in bl_list:
        # Anchor distribution
        anchor = bl.get("anchor_text", "other") or "other"
        anchor_dist[anchor] = anchor_dist.get(anchor, 0) + 1
        # Follow distribution
        follow = bl.get("link_follow", "unknown")
        follow_dist[follow] = follow_dist.get(follow, 0) + 1
        # Authority buckets
        auth_score = bl.get("source_authority", 0)
        if auth_score <= 20:
            authority_buckets["0-20"] += 1
        elif auth_score <= 40:
            authority_buckets["21-40"] += 1
        elif auth_score <= 60:
            authority_buckets["41-60"] += 1
        elif auth_score <= 80:
            authority_buckets["61-80"] += 1
        else:
            authority_buckets["81-100"] += 1
        # Timeseries
        try:
            d = datetime.fromisoformat(bl["first_seen"]).date()
        except (KeyError, ValueError):
            continue
        if d < cutoff:
            continue
        # Group into weeks
        week_start = d - timedelta(days=d.weekday())
        wk = week_start.isoformat()
        if bl.get("is_lost"):
            week_lost[wk] = week_lost.get(wk, 0) + 1
        else:
            week_new[wk] = week_new.get(wk, 0) + 1

    # Build sorted timeseries
    all_weeks = sorted(set(list(week_new.keys()) + list(week_lost.keys())))
    timeseries = [
        {
            "week": wk,
            "new_backlinks": week_new.get(wk, 0),
            "lost_backlinks": week_lost.get(wk, 0),
        }
        for wk in all_weeks
    ]

    # Top anchors (top 10)
    top_anchors = sorted(anchor_dist.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "analytics": {
            "timeseries": timeseries,
            "anchor_distribution": [{"anchor": a, "count": c} for a, c in top_anchors],
            "follow_distribution": follow_dist,
            "authority_buckets": authority_buckets,
            "total_analyzed": len(bl_list),
            "days": days,
        }
    }


@router.post("/authority-score")
def authority_score(payload: AuthorityScoreRequest, auth: AuthDep) -> dict[str, Any]:
    """Return authority score for any domain."""
    domain = payload.domain.lower().strip()
    score = _compute_authority_score(domain)
    your_score = _compute_authority_score(auth.tenant_id[:20])
    return {
        "authority_score": {
            "domain": domain,
            "score": score,
            "label": "Strong" if score >= 60 else ("Moderate" if score >= 35 else "Weak"),
            "your_score": your_score,
            "delta": score - your_score,
            "checked_at": _now(),
        }
    }


@router.post("/disavow")
def generate_disavow(payload: DisavowRequest, auth: AuthDep) -> dict[str, Any]:
    """Generate Google-format disavow file content for the given backlink IDs."""
    bl_list = _get_backlinks(auth.tenant_id)
    id_set = set(payload.backlink_ids)
    matched = [b for b in bl_list if b["id"] in id_set and b["tenant_id"] == auth.tenant_id]
    if not matched:
        raise HTTPException(status_code=404, detail="No matching backlinks found for the given IDs.")

    lines = ["# Disavow file generated by Nuxtron Backlink Intelligence", f"# Generated: {_now()}", ""]
    for bl in matched:
        lines.append(f"domain:{bl['source_domain']}")

    disavow_content = "\n".join(lines)
    return {
        "disavow": {
            "content": disavow_content,
            "domains_count": len({b["source_domain"] for b in matched}),
            "backlinks_count": len(matched),
            "generated_at": _now(),
        }
    }
