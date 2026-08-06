"""
SEO-AI core analysis — production implementation (module 1).

Uses LLM (Ollama) when available; otherwise deterministic heuristics from
domain page signals and operator inputs. Does not emit fake perfect scores.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

_PAGE_FETCH_TIMEOUT = 12.0
_MAX_HTML_BYTES = 500_000

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
_META_DESC_ALT_RE = re.compile(
    r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']description["\']',
    re.IGNORECASE,
)
_H1_RE = re.compile(r"<h1\b", re.IGNORECASE)
_CANONICAL_RE = re.compile(r'rel=["\']canonical["\']', re.IGNORECASE)
_ROBOTS_NOINDEX_RE = re.compile(r"<meta[^>]+name=[\"']robots[\"'][^>]+content=[\"'][^\"']*noindex", re.IGNORECASE)

def normalize_domain(domain: str) -> str:
    text = domain.strip().lower()
    if text.startswith("http://") or text.startswith("https://"):
        parsed = urlparse(text)
        host = parsed.netloc or parsed.path
        return host.split("/")[0]
    return text.split("/")[0]


def build_page_url(domain: str) -> str:
    host = normalize_domain(domain)
    if not host:
        return ""
    if host.startswith("http://") or host.startswith("https://"):
        return host
    return f"https://{host}/"


async def fetch_page_signals(domain: str) -> dict[str, Any]:
    """Fetch lightweight on-page signals from the site homepage."""
    url = build_page_url(domain)
    if not url:
        return {"fetch_ok": False, "url": "", "error": "invalid_domain"}

    try:
        async with httpx.AsyncClient(
            timeout=_PAGE_FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "NuxtronSEO-AI/1.0 (+https://nuxtron.io/bot)"},
        ) as client:
            response = await client.get(url)
        html = response.text[:_MAX_HTML_BYTES] if response.text else ""
        title_match = _TITLE_RE.search(html)
        title = re.sub(r"\s+", " ", title_match.group(1)).strip() if title_match else ""
        meta_match = _META_DESC_RE.search(html) or _META_DESC_ALT_RE.search(html)
        meta_description = meta_match.group(1).strip() if meta_match else ""
        text_only = re.sub(r"<[^>]+>", " ", html)
        word_count = len(re.findall(r"\b\w+\b", text_only))

        return {
            "fetch_ok": response.status_code == 200,
            "url": str(response.url),
            "status_code": response.status_code,
            "title": title[:300],
            "meta_description": meta_description[:500],
            "h1_count": len(_H1_RE.findall(html)),
            "has_canonical": bool(_CANONICAL_RE.search(html)),
            "robots_noindex": bool(_ROBOTS_NOINDEX_RE.search(html)),
            "word_count": word_count,
            "error": None if response.status_code == 200 else f"http_{response.status_code}",
        }
    except Exception as exc:
        logger.info("SEO-AI page fetch skipped for %s: %s", domain, exc)
        return {"fetch_ok": False, "url": url, "error": str(exc)}


def _keyword_variants(primary_keyword: str) -> list[dict[str, str]]:
    kw = primary_keyword.strip()
    if not kw:
        return []
    base = kw.lower()
    variants = [
        (kw, "informational", "high"),
        (f"how to {kw}", "informational", "high"),
        (f"best {kw}", "commercial", "medium"),
        (f"{kw} guide", "informational", "medium"),
    ]
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for keyword, intent, priority in variants:
        key = keyword.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append({"keyword": keyword, "intent": intent, "priority": priority})
    return out


def heuristic_seo_ai_analysis(
    *,
    domain: str,
    primary_keyword: str,
    business_goal: str,
    content_excerpt: str,
    notes: str,
    page: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic analysis from real inputs — no placeholder perfect scores."""
    kw_lower = primary_keyword.lower()
    excerpt_lower = content_excerpt.lower()
    title_lower = str(page.get("title") or "").lower()

    score = 38
    if kw_lower and kw_lower in excerpt_lower:
        score += 14
    elif kw_lower and kw_lower in title_lower:
        score += 10
    if len(content_excerpt.strip()) >= 200:
        score += 8
    if page.get("fetch_ok"):
        score += 10
        if page.get("h1_count", 0) >= 1:
            score += 4
        if page.get("meta_description"):
            score += 4
        if page.get("has_canonical"):
            score += 3
    if business_goal.strip():
        score += 4
    if page.get("robots_noindex"):
        score -= 15
    score = max(22, min(88, score))

    technical: list[dict[str, str]] = []
    if page.get("fetch_ok"):
        if page.get("h1_count", 0) == 0:
            technical.append(
                {
                    "issue": "Missing H1 on homepage",
                    "impact": "high",
                    "fix": "Add a single keyword-aligned H1 on the primary landing page.",
                }
            )
        if not page.get("meta_description"):
            technical.append(
                {
                    "issue": "Missing meta description",
                    "impact": "medium",
                    "fix": "Write a 140–160 character meta description including the primary keyword.",
                }
            )
        if not page.get("has_canonical"):
            technical.append(
                {
                    "issue": "Missing canonical tag",
                    "impact": "medium",
                    "fix": "Add rel=canonical on indexable templates to reduce duplicate signals.",
                }
            )
        if page.get("robots_noindex"):
            technical.append(
                {
                    "issue": "Homepage blocked by noindex",
                    "impact": "critical",
                    "fix": "Remove noindex from pages intended to rank in organic search.",
                }
            )
    else:
        technical.append(
            {
                "issue": "Homepage could not be crawled",
                "impact": "high",
                "fix": "Verify DNS, TLS, and that the domain resolves publicly before SEO optimization.",
            }
        )

    if not content_excerpt.strip():
        technical.append(
            {
                "issue": "No content excerpt provided for on-page review",
                "impact": "medium",
                "fix": "Paste a representative page excerpt so on-page relevance can be scored.",
            }
        )

    content_priorities: list[dict[str, str]] = []
    if len(content_excerpt.strip()) < 200:
        content_priorities.append(
            {
                "topic": f"Pillar page: {primary_keyword}",
                "reason": "Thin or missing excerpt — expand core landing content.",
                "expected_lift": "Improved topical relevance and crawl clarity",
            }
        )
    else:
        content_priorities.append(
            {
                "topic": f"Refresh and internal-link hub for {primary_keyword}",
                "reason": "Excerpt present — deepen clusters and FAQ sections around intent.",
                "expected_lift": "Higher engagement and snippet eligibility",
            }
        )

    serp_surface = "featured_snippet" if "how" in kw_lower or "what" in kw_lower else "standard_organic"
    next_actions = [
        f"Align homepage title and H1 with '{primary_keyword}'",
        "Publish 3 supporting articles mapped to high-priority keyword variants",
        "Fix technical issues flagged in this report before scaling content",
    ]
    if notes.strip():
        next_actions.append(f"Operator note: {notes.strip()[:200]}")

    return {
        "seo_ai_score": score,
        "keyword_opportunities": _keyword_variants(primary_keyword),
        "content_priorities": content_priorities,
        "technical_priorities": technical,
        "serp_strategy": {
            "primary_surface": serp_surface,
            "ctr_focus": "Clear H1 + meta match to search intent",
            "snippet_angle": "Definition block plus numbered steps in the first 120 words",
        },
        "next_actions": next_actions,
        "analysis_mode": "heuristic",
        "ai_available": False,
        "page_signals": {
            "url": page.get("url"),
            "fetch_ok": page.get("fetch_ok"),
            "status_code": page.get("status_code"),
            "title": page.get("title"),
            "word_count": page.get("word_count"),
        },
    }


def normalize_seo_ai_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    """Validate shape, clamp score, strip internal LLM error keys."""
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    score_raw = out.get("seo_ai_score")
    try:
        score = int(float(score_raw))
    except (TypeError, ValueError):
        score = 50
    out["seo_ai_score"] = max(0, min(100, score))

    if not isinstance(out.get("keyword_opportunities"), list):
        out["keyword_opportunities"] = []
    if not isinstance(out.get("content_priorities"), list):
        out["content_priorities"] = []
    if not isinstance(out.get("technical_priorities"), list):
        out["technical_priorities"] = []
    if not isinstance(out.get("next_actions"), list):
        out["next_actions"] = out.get("next_actions") or []

    serp = out.get("serp_strategy")
    if not isinstance(serp, dict):
        out["serp_strategy"] = {
            "primary_surface": "standard_organic",
            "ctr_focus": "Match title and meta to primary intent",
            "snippet_angle": "Answer the query in the opening paragraph",
        }

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_seo_ai_core(
    *,
    domain: str,
    primary_keyword: str,
    business_goal: str,
    content_excerpt: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """
    Run SEO-AI core analysis. Prefer LLM JSON; fall back to heuristic analysis.
    """
    page = await fetch_page_signals(domain)
    prompt = (
        f"Create a core SEO-AI action plan for domain: {clean_text_fn(domain, 300)}.\n"
        f"Primary keyword: {clean_text_fn(primary_keyword, 200)}.\n"
        f"Business goal: {clean_text_fn(business_goal, 200)}.\n"
        f"Content excerpt:\n{clean_text_fn(content_excerpt, 2500)}\n\n"
        f"Operator notes: {clean_text_fn(notes, 500)}.\n"
        f"Live page signals (homepage): {json.dumps(page, default=str)[:2000]}\n"
        "Prioritize keyword opportunities, content expansion angles, technical fixes, and SERP strategy."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("seo_ai_score") is not None or llm_result.get("keyword_opportunities"):
            normalized = normalize_seo_ai_result(llm_result, analysis_mode="llm", ai_available=True)
            normalized["page_signals"] = {
                "url": page.get("url"),
                "fetch_ok": page.get("fetch_ok"),
                "status_code": page.get("status_code"),
            }
            return normalized

    heuristic = heuristic_seo_ai_analysis(
        domain=domain,
        primary_keyword=primary_keyword,
        business_goal=business_goal,
        content_excerpt=content_excerpt,
        notes=notes,
        page=page,
    )
    return normalize_seo_ai_result(heuristic, analysis_mode="heuristic", ai_available=False)
