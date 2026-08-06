"""On-Page SEO Optimizer — phase-j module 2."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_on_page_signals(*, url: str, content: str, focus_keyword: str) -> dict[str, Any]:
    page = url.strip()
    text = content.strip()
    keyword = focus_keyword.strip()
    https_ok = page.startswith("https")
    words = len(text.split()) if text else max(120, len(keyword.split()) * 80)

    seo_score = 44
    seo_score += 10 if https_ok else 0
    seo_score += min(14, len(keyword.split()) * 3)
    seo_score += min(12, len(text) // 120)
    seo_score += 6 if keyword.lower() in text.lower() else 0
    seo_score = _clamp(seo_score)

    readability = _clamp(seo_score - 6 + min(8, words // 80))
    density = round(min(3.5, max(0.4, len(keyword.split()) * 0.6 + (1.0 if keyword.lower() in text.lower() else 0.3))), 1)

    signals = [
        {
            "signal": "Title keyword alignment",
            "status": "pass" if seo_score >= 55 else "warn",
            "detail": f"Validate '{keyword}' appears early in the title tag",
            "priority": "high",
        },
        {
            "signal": "HTTPS",
            "status": "pass" if https_ok else "fail",
            "detail": "Page should be served over HTTPS",
            "priority": "high",
        },
        {
            "signal": "Content depth",
            "status": "pass" if words >= 600 else "warn",
            "detail": f"Estimated word count ~{words}",
            "priority": "medium",
        },
    ]

    return {
        "seo_score": seo_score,
        "on_page_score": seo_score,
        "readability_score": readability,
        "keyword_density": density,
        "word_count": words,
        "signals": signals,
        "content_suggestions": [
            {
                "section": "Introduction",
                "suggestion": f"Add a clear definition of {keyword} in the first 100 words",
                "impact": "high",
            }
        ],
        "title_tags": {
            "current": "",
            "recommended": f"{keyword.title()} — Complete Guide",
            "issues": [] if seo_score >= 60 else ["Title may not lead with primary keyword"],
        },
        "meta_description": {
            "current": "",
            "recommended": f"Learn {keyword} with actionable steps, examples, and expert tips.",
            "issues": [] if seo_score >= 58 else ["Meta description should include primary keyword and CTA"],
        },
        "heading_structure": {"h1": [keyword.title()], "h2": ["Overview", "Best Practices"], "h3": []},
        "internal_link_opportunities": ["/related-guide", "/tools"],
        "quick_wins": ["Optimize title tag", "Add keyword to first paragraph", "Increase internal links"],
        "recommendations": [
            {
                "type": "title",
                "priority": "high",
                "suggestion": f"Include '{keyword}' in the first 60 characters of the title",
            }
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_on_page_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    score = out.get("overall_score", out.get("on_page_score", out.get("seo_score", 50)))
    try:
        seo_score = _clamp(int(float(score)))
    except (TypeError, ValueError):
        seo_score = 50
    out["seo_score"] = seo_score
    out["on_page_score"] = seo_score
    try:
        out["readability_score"] = _clamp(int(float(out.get("readability_score", seo_score - 5))))
    except (TypeError, ValueError):
        out["readability_score"] = _clamp(seo_score - 5)
    try:
        out["keyword_density"] = float(out.get("keyword_density", out.get("keyword_usage", {}).get("primary_density", 1.2)))
    except (TypeError, ValueError):
        out["keyword_density"] = 1.2
    try:
        out["word_count"] = int(out.get("word_count", out.get("content_quality", {}).get("word_count", 800)))
    except (TypeError, ValueError):
        out["word_count"] = 800
    for list_key in ("signals", "content_suggestions", "internal_link_opportunities", "quick_wins", "recommendations"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("title_tags"), dict):
        out["title_tags"] = {"current": "", "recommended": "", "issues": []}
    if not isinstance(out.get("meta_description"), dict):
        out["meta_description"] = {"current": "", "recommended": "", "issues": []}
    if not isinstance(out.get("heading_structure"), dict):
        out["heading_structure"] = {"h1": [], "h2": [], "h3": []}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_on_page(
    *,
    url: str,
    content: str,
    focus_keyword: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Analyze on-page SEO for URL: {clean_text_fn(url, 500)}. "
        f"Focus keyword: '{clean_text_fn(focus_keyword, 200)}'. "
        f"Content snippet: {clean_text_fn(content, 2000)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("overall_score") is not None or llm.get("recommendations") or llm.get("seo_score") is not None:
            return normalize_on_page_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_on_page_signals(url=url, content=content, focus_keyword=focus_keyword)
    return normalize_on_page_result(heur, analysis_mode="heuristic", ai_available=False)
