"""
Programmatic SEO Engine — phase-b module 3.

Generates scaled page templates from topic, variable matrix, and URL/title patterns.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import itertools
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger(__name__)

_BRACKET_SLOT_RE = re.compile(r"\[([a-zA-Z0-9_]+)\]")
_VAGUE_TOPIC_RE = re.compile(r"\b(stuff|things|misc|general)\b", re.IGNORECASE)
_THIN_META_RE = re.compile(r"^\s*.{0,40}\s*$", re.DOTALL)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "page"


def _substitute(template: str, values: dict[str, str]) -> str:
    out = template
    for key, val in values.items():
        out = out.replace(f"[{key}]", val)
        out = out.replace(f"{{{key}}}", val)
    return re.sub(r"\s+", " ", out).strip()


def _variable_sets_from_matrix(variables: dict[str, list[str]], max_pages: int) -> list[dict[str, str]]:
    keys = [k for k, v in variables.items() if k.strip() and v]
    if not keys:
        return []
    combos = list(itertools.product(*[[str(x).strip() for x in variables[k] if str(x).strip()] for k in keys]))
    sets: list[dict[str, str]] = []
    for combo in combos[:max_pages]:
        sets.append({keys[i]: combo[i] for i in range(len(keys))})
    return sets


def parse_programmatic_inputs(
    *,
    template_topic: str,
    variable_sets: list[dict[str, str]],
    page_count: int,
    url_template: str = "",
    title_template: str = "",
    meta_description_template: str = "",
    variables: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Normalize API payloads from legacy and frontend shapes."""
    url_t = url_template.strip()
    title_t = title_template.strip()
    meta_t = meta_description_template.strip()
    topic = template_topic.strip() or title_t or url_t or "programmatic pages"

    sets = [dict(v) for v in variable_sets if isinstance(v, dict) and v]
    if variables:
        matrix_sets = _variable_sets_from_matrix(variables, page_count)
        if matrix_sets:
            sets = matrix_sets

    if not sets:
        sets = [{"example": "value"}]

    count = min(page_count, max(1, len(sets)))
    sets = sets[:count]

    return {
        "template_topic": topic,
        "url_template": url_t or "/[example]",
        "title_template": title_t or f"Best {topic} — [example]",
        "meta_description_template": meta_t or f"Complete guide to {topic} for [example].",
        "variable_sets": sets,
        "page_count": count,
    }


def _title_similarity(titles: list[str]) -> float:
    if len(titles) < 2:
        return 0.0
    tokens = [set(re.findall(r"\b\w+\b", t.lower())) for t in titles]
    overlaps = []
    for i in range(len(tokens)):
        for j in range(i + 1, len(tokens)):
            union = tokens[i] | tokens[j]
            if not union:
                continue
            overlaps.append(len(tokens[i] & tokens[j]) / len(union))
    return sum(overlaps) / len(overlaps) if overlaps else 0.0


def analyze_programmatic_signals(
    *,
    template_topic: str,
    variable_sets: list[dict[str, str]],
    page_count: int,
    url_template: str = "",
    title_template: str = "",
    meta_description_template: str = "",
    variables: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Deterministic programmatic SEO template generation."""
    parsed = parse_programmatic_inputs(
        template_topic=template_topic,
        variable_sets=variable_sets,
        page_count=page_count,
        url_template=url_template,
        title_template=title_template,
        meta_description_template=meta_description_template,
        variables=variables,
    )
    topic = parsed["template_topic"]
    sets = parsed["variable_sets"]
    url_t = parsed["url_template"]
    title_t = parsed["title_template"]
    meta_t = parsed["meta_description_template"]
    count = parsed["page_count"]

    slot_keys = set(_BRACKET_SLOT_RE.findall(url_t + title_t + meta_t))
    matrix_keys = set()
    for var_set in sets:
        matrix_keys.update(var_set.keys())
    slot_coverage = len(slot_keys & matrix_keys) / max(1, len(slot_keys)) if slot_keys else 1.0

    template_quality_score = 40
    template_quality_score += min(20, int(slot_coverage * 20))
    template_quality_score += min(12, len(matrix_keys) * 3)
    template_quality_score += 8 if len(meta_t) >= 80 else 0
    template_quality_score += 6 if not _VAGUE_TOPIC_RE.search(topic) else 0
    template_quality_score -= 10 if _THIN_META_RE.match(meta_t) and meta_t else 0
    template_quality_score = _clamp(template_quality_score)

    page_templates: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    seen_slugs: set[str] = set()
    deduplication_applied = 0

    for var_set in sets:
        title = _substitute(title_t, var_set)
        meta = _substitute(meta_t, var_set)
        slug_path = _substitute(url_t, var_set)
        url_slug = _slugify(slug_path.lstrip("/"))
        if url_slug in seen_slugs:
            deduplication_applied += 1
            url_slug = f"{url_slug}-{len(seen_slugs)}"
        seen_slugs.add(url_slug)

        primary_val = next(iter(var_set.values()), topic)
        target_keyword = f"{primary_val} {topic}".strip()[:120]
        traffic_est = min(2500, 120 + len(target_keyword) * 3 + len(var_set) * 40)

        outline = [
            "Introduction",
            f"Why {primary_val} matters for {topic}",
            "Key benefits and proof points",
            "How to get started",
            "FAQ",
        ]
        page_templates.append(
            {
                "title": title,
                "meta_description": meta,
                "h1": title.split("|")[0].strip(),
                "content_outline": outline,
            }
        )
        pages.append(
            {
                "url_slug": f"/{url_slug}",
                "title": title,
                "meta_description": meta,
                "target_keyword": target_keyword,
                "estimated_traffic": traffic_est,
            }
        )

    titles = [p["title"] for p in pages]
    similarity = _title_similarity(titles)
    if similarity >= 0.72:
        cannibalization_risk = "high"
    elif similarity >= 0.45:
        cannibalization_risk = "medium"
    else:
        cannibalization_risk = "low"

    seo_coverage_estimate = _clamp(int(round(slot_coverage * 70 + min(25, len(matrix_keys) * 5))))

    recommendations = [
        "Add unique proof points per variable combination to avoid thin duplicate pages.",
        "Link hub pillar to all programmatic children with descriptive anchor text.",
    ]
    if cannibalization_risk != "low":
        recommendations.append("Reduce title pattern overlap or merge low-intent variants into faceted hubs.")
    if deduplication_applied:
        recommendations.append(f"Deduplicated {deduplication_applied} slug collisions — review URL template tokens.")

    return {
        "template_quality_score": template_quality_score,
        "programmatic_score": template_quality_score,
        "template_score": template_quality_score,
        "pages_generated": len(pages),
        "total_pages_generated": len(pages),
        "page_templates": page_templates,
        "pages": pages,
        "seo_coverage_estimate": seo_coverage_estimate,
        "cannibalization_risk": cannibalization_risk,
        "deduplication_applied": deduplication_applied,
        "recommendations": recommendations,
        "internal_linking_strategy": "Hub-and-spoke: pillar page links to all variants; variants link back to pillar and 2 sibling pages max.",
        "indexing_considerations": [
            "Submit segmented sitemaps by template cluster",
            "Noindex ultra-thin variants until unique content blocks ship",
            "Monitor crawl budget when page_count exceeds 500",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "variable_set_count": len(sets),
            "slot_coverage_pct": round(slot_coverage * 100, 1),
            "matrix_key_count": len(matrix_keys),
        },
    }


def normalize_programmatic_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    score_raw = out.get("template_quality_score", out.get("programmatic_score", out.get("template_score", 50)))
    try:
        score = _clamp(int(float(score_raw)))
    except (TypeError, ValueError):
        score = 50
    out["template_quality_score"] = score
    out["programmatic_score"] = score
    out["template_score"] = score

    if not isinstance(out.get("page_templates"), list):
        out["page_templates"] = []
    if not isinstance(out.get("pages"), list):
        out["pages"] = []
    if not isinstance(out.get("recommendations"), list):
        recs = out.get("indexing_considerations")
        out["recommendations"] = recs if isinstance(recs, list) else []

    try:
        pages_gen = int(float(out.get("pages_generated", out.get("total_pages_generated", len(out["pages"])))))
    except (TypeError, ValueError):
        pages_gen = len(out["pages"])
    out["pages_generated"] = pages_gen
    out["total_pages_generated"] = pages_gen

    if not out.get("seo_coverage_estimate"):
        out["seo_coverage_estimate"] = _clamp(score - 5)
    if not out.get("cannibalization_risk"):
        out["cannibalization_risk"] = "medium"
    if out.get("deduplication_applied") is None:
        out["deduplication_applied"] = 0

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def generate_programmatic_seo(
    *,
    template_topic: str,
    variable_sets: list[dict[str, str]],
    page_count: int,
    url_template: str = "",
    title_template: str = "",
    meta_description_template: str = "",
    variables: dict[str, list[str]] | None = None,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run programmatic SEO generation."""
    parsed = parse_programmatic_inputs(
        template_topic=template_topic,
        variable_sets=variable_sets,
        page_count=page_count,
        url_template=url_template,
        title_template=title_template,
        meta_description_template=meta_description_template,
        variables=variables,
    )

    prompt = (
        f"Create programmatic SEO templates for: '{clean_text_fn(parsed['template_topic'], 300)}'.\n"
        f"URL template: {clean_text_fn(parsed['url_template'], 300)}.\n"
        f"Title template: {clean_text_fn(parsed['title_template'], 300)}.\n"
        f"Meta template: {clean_text_fn(parsed['meta_description_template'], 500)}.\n"
        f"Variable sets: {parsed['variable_sets'][:8]}.\n"
        f"Pages to generate: {parsed['page_count']}.\n"
        "Create title/meta/H1 templates with variable substitution slots. "
        "Outline content structure for each page type. "
        "Provide internal linking strategy and indexing considerations. "
        "Do not use bracket placeholders without variable names."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("page_templates") or llm_result.get("template_quality_score") is not None:
            return normalize_programmatic_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_programmatic_signals(
        template_topic=template_topic,
        variable_sets=variable_sets,
        page_count=page_count,
        url_template=url_template,
        title_template=title_template,
        meta_description_template=meta_description_template,
        variables=variables,
    )
    return normalize_programmatic_result(heuristic, analysis_mode="heuristic", ai_available=False)
