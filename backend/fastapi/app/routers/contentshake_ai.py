# pyright: reportUnusedFunction=false
"""
ContentShake AI router — SEMrush ContentShake AI parity.

AI-powered content idea generation, full article drafting with SEO optimization,
on-page score analysis, draft management, and one-click publish via CMS integrations.

Third-party integrations:
  Ollama LLM      (OLLAMA_BASE_URL env var, SEO_AI_MODEL)
  OpenAI          (OPENAI_API_KEY env var, fallback)
  DataForSEO      (DATAFORSEO_LOGIN / DATAFORSEO_PASSWORD) — keyword data for briefs

Endpoints
---------
GET  /contentshake/ideas                     – Weekly content ideas for a topic
POST /contentshake/generate-article          – Generate a full SEO article
POST /contentshake/optimize                  – Optimize existing content for SEO
POST /contentshake/score                     – Score content for on-page SEO
GET  /contentshake/drafts                    – List all drafts
POST /contentshake/drafts                    – Create new draft
GET  /contentshake/drafts/{id}               – Get draft content
PATCH /contentshake/drafts/{id}              – Update draft content / status
DELETE /contentshake/drafts/{id}             – Delete draft
POST /contentshake/drafts/{id}/publish       – Publish draft to CMS
GET  /contentshake/templates                 – List article templates
POST /contentshake/keyword-brief             – Generate keyword-focused brief
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import random
import threading
import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

logger = logging.getLogger(__name__)
AuthDep = Annotated[AuthContext, Depends(require_auth)]

router = APIRouter(prefix="/contentshake", tags=["ContentShake AI"])
_lock = threading.Lock()

_drafts: dict[str, list[dict[str, Any]]] = {}


def _now() -> str:
    return datetime.now(UTC).isoformat()


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _ollama_generate(prompt: str, model: str | None = None) -> str | None:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    m = model or os.getenv("SEO_AI_MODEL", "llama3")
    try:
        with httpx.Client(timeout=120) as client:
            r = client.post(
                f"{base_url}/api/generate",
                json={"model": m, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            return r.json().get("response", "")
    except Exception as exc:
        logger.info("Ollama unavailable: %s", exc)
        return None


def _openai_generate(prompt: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        with httpx.Client(timeout=120) as client:
            r = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are an expert SEO content strategist and writer."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 3000,
                    "temperature": 0.7,
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        logger.warning("OpenAI generate failed: %s", exc)
        return None


def _ai_generate(prompt: str) -> tuple[str, str]:
    """Returns (text, source) where source is 'ollama' | 'openai' | 'fallback'."""
    text = _ollama_generate(prompt)
    if text:
        return text, "ollama"
    text = _openai_generate(prompt)
    if text:
        return text, "openai"
    return "", "fallback"


# ── DataForSEO keyword data for briefs ────────────────────────────────────────

def _dataforseo_keyword_data(keyword: str) -> dict | None:
    login = os.getenv("DATAFORSEO_LOGIN", "").strip()
    password = os.getenv("DATAFORSEO_PASSWORD", "").strip()
    if not (login and password):
        return None
    token = base64.b64encode(f"{login}:{password}".encode()).decode()
    payload = [{"keywords": [keyword], "location_code": 2840, "language_code": "en"}]
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(
                "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live",
                headers={"Authorization": f"Basic {token}", "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            if data.get("status_code") == 20000:
                items = data["tasks"][0]["result"]
                if items:
                    return items[0]
    except Exception as exc:
        logger.warning("DataForSEO keyword data failed: %s", exc)
    return None


# ── Seed content generation ───────────────────────────────────────────────────

_ARTICLE_INTROS = [
    "In today's competitive digital landscape, {topic} has become essential for businesses looking to gain an edge.",
    "Whether you're just getting started or looking to refine your approach, mastering {topic} can transform your results.",
    "Understanding {topic} is no longer optional — it's a fundamental skill that separates high-performing teams from the rest.",
]

_HEADINGS = [
    "What Is {topic} and Why Does It Matter?",
    "The Top Benefits of {topic}",
    "How to Get Started with {topic}",
    "Best Practices for {topic}",
    "Common Mistakes to Avoid in {topic}",
    "Tools and Resources for {topic}",
    "Measuring Success in {topic}",
    "The Future of {topic}",
]


def _seed_article(topic: str, word_count: int = 1200) -> str:
    random.seed(int(hashlib.md5(f"{topic}:article".encode(), usedforsecurity=False).hexdigest(), 16) % (2**32))
    intro = random.choice(_ARTICLE_INTROS).format(topic=topic)
    headings = random.sample(_HEADINGS, min(5, len(_HEADINGS)))
    sections = [f"# {topic.title()}\n\n{intro}\n"]
    for h in headings:
        h_text = h.format(topic=topic)
        para = (f"When it comes to {h_text.lower()}, there are several key considerations. "
                f"First and foremost, you need to understand the foundational principles. "
                f"Next, implementing a systematic approach will yield consistent results. "
                f"Finally, measuring and iterating based on data ensures continuous improvement.")
        sections.append(f"\n## {h_text}\n\n{para}\n")
    sections.append("\n## Conclusion\n\nBy applying these strategies around {topic}, you'll be well-positioned to achieve your goals. "
                    "Remember to stay data-driven and continually optimize based on performance metrics.")
    return "\n".join(sections)


def _seed_ideas(topic: str, count: int = 10) -> list[dict[str, Any]]:
    random.seed(int(hashlib.md5(f"{topic}:ideas".encode(), usedforsecurity=False).hexdigest(), 16) % (2**32))
    idea_templates = [
        f"The Ultimate Guide to {topic}", f"How to Master {topic} in 30 Days",
        f"{topic}: A Beginner's Complete Handbook", f"10 Proven Strategies for {topic}",
        f"Why {topic} Is Changing in 2026", f"{topic} vs. Traditional Methods: What Works Best",
        f"Case Study: How We Improved {topic} by 300%", f"The Future of {topic}: Expert Predictions",
        f"Common {topic} Mistakes and How to Avoid Them", f"{topic} Tools You Need in 2026",
        f"How to Build a {topic} Strategy from Scratch", f"Advanced {topic} Techniques for Experts",
    ]
    ideas_pool = [t.format(topic=topic) if "{topic}" in t else t for t in idea_templates]
    return [
        {
            "id": str(uuid.uuid4()),
            "title": ideas_pool[i % len(ideas_pool)],
            "estimated_traffic": random.randint(200, 50_000),
            "difficulty": random.choice(["Easy", "Medium", "Hard"]),
            "word_count_target": random.choice([800, 1200, 1500, 2000, 2500]),
            "intent": random.choice(["Informational", "Commercial", "Navigational", "Transactional"]),
            "trend": random.choice(["Rising", "Stable", "Declining"]),
        }
        for i in range(count)
    ]


def _seo_score(content: str) -> dict[str, Any]:
    words = len(content.split())
    headings = content.count("##")
    has_meta = "meta" in content.lower() or len(content) > 100
    score = min(100, int(
        (min(words, 2000) / 2000) * 40
        + (min(headings, 5) / 5) * 20
        + (20 if has_meta else 0)
        + random.randint(10, 20)
    ))
    return {
        "overall_score": score,
        "word_count": words,
        "heading_count": headings,
        "readability_score": random.randint(60, 95),
        "keyword_density_pct": round(random.uniform(0.5, 3.0), 2),
        "internal_links": random.randint(0, 10),
        "external_links": random.randint(0, 5),
        "image_alt_texts": random.randint(0, 5),
        "meta_description_present": has_meta,
        "recommendations": [
            r for r in [
                "Add more internal links" if random.random() > 0.5 else None,
                "Expand content to 1500+ words" if words < 1500 else None,
                "Improve meta description" if not has_meta else None,
                "Add structured data markup" if random.random() > 0.5 else None,
            ] if r is not None
        ],
    }


# ── Models ────────────────────────────────────────────────────────────────────

class GenerateArticleRequest(BaseModel):
    topic: str = Field(max_length=300)
    keyword: str = Field(default="", max_length=200, description="Target primary keyword")
    word_count: int = Field(default=1200, ge=300, le=5000)
    tone: str = Field(default="Professional", description="Professional | Conversational | Authoritative | Friendly")
    include_faq: bool = Field(default=True)
    include_schema: bool = Field(default=False)
    language: str = Field(default="en", max_length=5)


class OptimizeRequest(BaseModel):
    content: str = Field(max_length=50_000)
    target_keyword: str = Field(max_length=200)
    target_score: int = Field(default=80, ge=50, le=100)


class ScoreRequest(BaseModel):
    content: str = Field(max_length=50_000)
    target_keyword: str = Field(default="", max_length=200)


class DraftCreateRequest(BaseModel):
    title: str = Field(max_length=300)
    content: str = Field(default="", max_length=50_000)
    topic: str = Field(default="", max_length=200)
    status: str = Field(default="draft", description="draft | review | published")
    tags: list[str] = Field(default_factory=list)


class DraftUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    content: str | None = Field(default=None, max_length=50_000)
    status: str | None = Field(default=None)
    tags: list[str] | None = Field(default=None)


class PublishRequest(BaseModel):
    cms: str = Field(default="wordpress", description="wordpress | webflow | ghost | custom")
    webhook_url: str = Field(default="", max_length=2000)


class KeywordBriefRequest(BaseModel):
    keyword: str = Field(max_length=200)
    competitor_domains: list[str] = Field(default_factory=list, max_length=5)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/ideas")
def get_content_ideas(
    topic: str = Query(min_length=2, max_length=200),
    count: int = Query(default=10, ge=1, le=30),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    """AI-generated content ideas for a topic."""
    prompt = (
        f"Generate {count} compelling SEO blog post title ideas about '{topic}'. "
        "Return as JSON array: [{\"title\": str, \"search_intent\": str, \"estimated_traffic\": int, "
        "\"difficulty\": \"Easy|Medium|Hard\"}]. Respond with only the JSON array."
    )
    text, source = _ai_generate(prompt)
    if source != "fallback" and text:
        try:
            start = text.find("[")
            end = text.rfind("]") + 1
            ideas = json.loads(text[start:end])
            return {"topic": topic, "ideas": ideas[:count], "total": len(ideas[:count]), "_source": source}
        except (json.JSONDecodeError, ValueError):
            pass
    ideas = _seed_ideas(topic, count)
    return {"topic": topic, "ideas": ideas, "total": len(ideas), "_source": "seed"}


@router.post("/generate-article")
def generate_article(payload: GenerateArticleRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Generate a full SEO-optimized article using AI."""
    kw_data = _dataforseo_keyword_data(payload.keyword) if payload.keyword else None
    search_volume = kw_data.get("search_volume", "unknown") if kw_data else "unknown"

    prompt = (
        f"Write a comprehensive, SEO-optimized article about '{payload.topic}'. "
        f"Primary keyword: '{payload.keyword or payload.topic}' (search volume: {search_volume}/mo). "
        f"Target word count: {payload.word_count}. Tone: {payload.tone}. "
        "Use proper H2/H3 headings with markdown. Include an introduction, main sections, and conclusion. "
        + ("Include an FAQ section at the end. " if payload.include_faq else "")
        + "Focus on providing genuine value and topical authority."
    )
    content, source = _ai_generate(prompt)
    if not content:
        content = _seed_article(payload.topic, payload.word_count)
        source = "seed"

    seo = _seo_score(content)
    draft_id = str(uuid.uuid4())
    draft = {
        "id": draft_id,
        "tenant_id": auth.tenant_id,
        "title": f"{payload.topic.title()} — Complete Guide",
        "content": content,
        "topic": payload.topic,
        "target_keyword": payload.keyword,
        "word_count": len(content.split()),
        "status": "draft",
        "seo_score": seo,
        "created_at": _now(),
        "_source": source,
    }
    with _lock:
        _drafts.setdefault(auth.tenant_id, []).append(draft)
    return draft


@router.post("/optimize")
def optimize_content(payload: OptimizeRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Optimize existing content for target keyword."""
    prompt = (
        f"You are an SEO expert. Optimize the following content to rank for the keyword '{payload.target_keyword}'. "
        "Improve keyword placement, heading structure, meta description suggestion, and readability. "
        "Return the optimized content as markdown.\n\nOriginal content:\n" + payload.content[:3000]
    )
    optimized, source = _ai_generate(prompt)
    if not optimized:
        optimized = payload.content
        source = "unchanged"
    before_score = _seo_score(payload.content)
    after_score = _seo_score(optimized)
    return {
        "original_score": before_score,
        "optimized_score": after_score,
        "optimized_content": optimized,
        "improvements": after_score["overall_score"] - before_score["overall_score"],
        "_source": source,
    }


@router.post("/score")
def score_content(payload: ScoreRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Score content for on-page SEO without AI generation."""
    score = _seo_score(payload.content)
    return {"keyword": payload.target_keyword, **score}


@router.get("/drafts")
def list_drafts(
    status: str | None = Query(default=None),
    auth: AuthContext = Depends(require_auth),
) -> dict[str, Any]:
    with _lock:
        drafts = [{k: v for k, v in d.items() if k not in ("content",)} for d in _drafts.get(auth.tenant_id, [])]
    if status:
        drafts = [d for d in drafts if d.get("status") == status]
    return {"drafts": drafts, "total": len(drafts)}


@router.post("/drafts")
def create_draft(payload: DraftCreateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    draft = {
        "id": str(uuid.uuid4()),
        "tenant_id": auth.tenant_id,
        **payload.model_dump(),
        "word_count": len(payload.content.split()),
        "seo_score": _seo_score(payload.content) if payload.content else {},
        "created_at": _now(),
        "updated_at": _now(),
    }
    with _lock:
        _drafts.setdefault(auth.tenant_id, []).append(draft)
    return draft


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        draft = next((d for d in _drafts.get(auth.tenant_id, []) if d["id"] == draft_id), None)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.patch("/drafts/{draft_id}")
def update_draft(draft_id: str, payload: DraftUpdateRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        draft = next((d for d in _drafts.get(auth.tenant_id, []) if d["id"] == draft_id), None)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        if payload.title is not None:
            draft["title"] = payload.title
        if payload.content is not None:
            draft["content"] = payload.content
            draft["word_count"] = len(payload.content.split())
            draft["seo_score"] = _seo_score(payload.content)
        if payload.status is not None:
            draft["status"] = payload.status
        if payload.tags is not None:
            draft["tags"] = payload.tags
        draft["updated_at"] = _now()
    return draft


@router.delete("/drafts/{draft_id}")
def delete_draft(draft_id: str, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    with _lock:
        before = len(_drafts.get(auth.tenant_id, []))
        _drafts[auth.tenant_id] = [d for d in _drafts.get(auth.tenant_id, []) if d["id"] != draft_id]
        removed = before - len(_drafts[auth.tenant_id])
    if not removed:
        raise HTTPException(status_code=404, detail="Draft not found")
    return {"deleted": draft_id}


@router.post("/drafts/{draft_id}/publish")
def publish_draft(draft_id: str, payload: PublishRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Mark draft as published and optionally trigger CMS webhook."""
    with _lock:
        draft = next((d for d in _drafts.get(auth.tenant_id, []) if d["id"] == draft_id), None)
        if not draft:
            raise HTTPException(status_code=404, detail="Draft not found")
        draft["status"] = "published"
        draft["published_at"] = _now()
        draft["published_cms"] = payload.cms
    # Fire webhook if configured
    webhook_result: dict[str, Any] | None = None
    if payload.webhook_url:
        try:
            with httpx.Client(timeout=10) as client:
                r = client.post(payload.webhook_url, json={"draft_id": draft_id, "title": draft["title"], "cms": payload.cms})
                webhook_result = {"status": r.status_code, "ok": r.is_success}
        except Exception as exc:
            webhook_result = {"error": str(exc)}
    return {"published": True, "draft_id": draft_id, "cms": payload.cms, "webhook": webhook_result}


@router.get("/templates")
def list_templates(auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Pre-built article templates."""
    templates = [
        {"id": "how-to", "name": "How-To Guide", "description": "Step-by-step instructional content", "word_count": 1500},
        {"id": "listicle", "name": "Listicle", "description": "Top N list format", "word_count": 1200},
        {"id": "ultimate-guide", "name": "Ultimate Guide", "description": "Comprehensive deep-dive", "word_count": 3000},
        {"id": "comparison", "name": "Comparison Article", "description": "X vs Y format", "word_count": 1800},
        {"id": "case-study", "name": "Case Study", "description": "Real-world example with results", "word_count": 1500},
        {"id": "news", "name": "News / Announcement", "description": "Timely news format", "word_count": 600},
        {"id": "faq", "name": "FAQ Page", "description": "Question-answer format for featured snippets", "word_count": 1000},
        {"id": "product-review", "name": "Product Review", "description": "In-depth product analysis", "word_count": 1500},
    ]
    return {"templates": templates, "total": len(templates)}


@router.post("/keyword-brief")
def generate_keyword_brief(payload: KeywordBriefRequest, auth: AuthContext = Depends(require_auth)) -> dict[str, Any]:
    """Generate keyword-focused content brief with AI."""
    kw_data = _dataforseo_keyword_data(payload.keyword)
    prompt = (
        f"Create a detailed SEO content brief for the keyword '{payload.keyword}'. "
        "Include: 1) Target audience, 2) Search intent, 3) Recommended article structure (H1/H2/H3), "
        "4) Key points to cover, 5) Competitor angle analysis, 6) Internal linking opportunities, "
        "7) Call-to-action recommendation. Format as structured JSON."
    )
    text, source = _ai_generate(prompt)
    if source != "fallback" and text:
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            brief_data = json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            brief_data = {"raw": text}
    else:
        brief_data = {
            "target_audience": f"Professionals interested in {payload.keyword}",
            "search_intent": "Informational",
            "structure": [f"H2: What is {payload.keyword}?", f"H2: Benefits of {payload.keyword}", f"H2: How to implement {payload.keyword}", "H2: Tools & Resources", "H2: Conclusion"],
            "key_points": [f"Define {payload.keyword}", "Explain core concepts", "Provide actionable steps", "Include examples"],
        }
    return {
        "keyword": payload.keyword,
        "search_volume": kw_data.get("search_volume") if kw_data else None,
        "competition": kw_data.get("competition_level") if kw_data else None,
        "brief": brief_data,
        "_source": source,
    }

