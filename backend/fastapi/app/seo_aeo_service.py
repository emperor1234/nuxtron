"""AEO (Answer Engine Optimization) — phase-k module 2."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_aeo_signals(
    *,
    topic: str,
    content: str,
    target_questions: list[str],
    entity_targets: list[str],
    schema_types: list[str],
    use_openlens: bool,
    use_playwright_validation: bool,
    retrieval_framework: str,
) -> dict[str, Any]:
    subject = topic.strip()
    text = content.strip()
    questions = [q.strip() for q in target_questions if q.strip()] or [f"What is {subject}?"]
    entities = [e.strip() for e in entity_targets if e.strip()]
    schemas = schema_types or ["FAQPage", "HowTo"]
    primary_q = questions[0]

    aeo_score = 44
    aeo_score += min(14, len(questions) * 3)
    aeo_score += min(10, len(entities) * 2)
    aeo_score += min(10, len(text) // 200)
    aeo_score += 4 if use_openlens else 0
    aeo_score += 4 if use_playwright_validation else 0
    aeo_score = _clamp(aeo_score)

    voice = _clamp(aeo_score - 8)
    coverage_pct = _clamp(min(95, 20 + len(questions) * 12))

    return {
        "aeo_score": aeo_score,
        "snippet_probability": round(min(0.85, 0.35 + aeo_score / 140), 2),
        "voice_readiness_score": voice,
        "paa_coverage": {
            "covered": questions[: max(1, len(questions) // 2)],
            "missing": [f"How does {subject} work?", "What are the benefits?"][:2],
            "coverage_pct": coverage_pct,
        },
        "snippet_opportunities": [
            {
                "question": primary_q,
                "answer": f"{subject} is a concise topic answer grounded in first-party expertise.",
                "format": "paragraph",
                "snippet_probability": round(min(0.8, 0.4 + aeo_score / 120), 2),
                "current_holder": "none",
                "word_count_target": 42,
                "schema_type": schemas[0],
                "entity_targets": entities[:3],
                "urgency": "high" if aeo_score >= 55 else "medium",
            }
        ],
        "faq_section": [
            {
                "question": primary_q,
                "answer": f"{subject} helps teams improve answer-surface visibility with structured, direct responses.",
                "schema_ready": True,
                "voice_optimized": voice >= 55,
            }
        ],
        "schema_implementation": {
            "recommended_types": schemas[:3],
            "missing_from_page": ["SpeakableSpecification"] if voice < 60 else [],
            "validation_url": "https://validator.schema.org",
        },
        "serp_feature_map": [
            {"feature": "featured_snippet", "your_presence": aeo_score >= 60, "opportunity_score": aeo_score},
            {"feature": "people_also_ask", "your_presence": len(questions) >= 2, "opportunity_score": _clamp(aeo_score - 5)},
        ],
        "zero_click_risk": {
            "level": "medium" if aeo_score < 65 else "low",
            "affected_queries": max(1, 4 - len(questions)),
            "mitigation": "Optimize branded queries that require navigation intent",
        },
        "voice_improvements": [
            "Use conversational sentences under 30 words for voice answers",
            "Begin answers with a direct declarative statement",
        ],
        "entity_salience_score": _clamp(aeo_score - 3 + len(entities) * 2),
        "quick_wins": [
            "Add FAQPage schema to key landing pages",
            "Format how-to answers as numbered lists under 60 words per step",
        ],
        "implementation_stack": {
            "openlens": use_openlens,
            "playwright": use_playwright_validation,
            "retrieval_framework": retrieval_framework.strip() or "llamaindex",
            "schema_types": schemas,
        },
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_aeo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["aeo_score"] = _clamp(int(float(out.get("aeo_score", 50))))
    except (TypeError, ValueError):
        out["aeo_score"] = 50
    for score_key in ("voice_readiness_score", "entity_salience_score"):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, out["aeo_score"] - 6))))
        except (TypeError, ValueError):
            out[score_key] = _clamp(out["aeo_score"] - 6)
    for list_key in ("snippet_opportunities", "faq_section", "quick_wins"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("paa_coverage"), dict):
        out["paa_coverage"] = {"covered": [], "missing": [], "coverage_pct": 0}
    if not isinstance(out.get("schema_implementation"), dict):
        out["schema_implementation"] = {"recommended_types": [], "missing_from_page": [], "validation_url": ""}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_aeo_optimize(
    *,
    topic: str,
    content: str,
    target_questions: list[str],
    entity_targets: list[str],
    schema_types: list[str],
    use_openlens: bool,
    use_playwright_validation: bool,
    retrieval_framework: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Optimize for Answer Engine (AEO). Topic: {clean_text_fn(topic, 300)}. "
        f"Target questions: {target_questions[:10]}. Entity targets: {entity_targets[:12]}. "
        f"Schema types: {schema_types[:6]}. Content:\n{clean_text_fn(content, 3000)}"
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("aeo_score") is not None or llm.get("snippet_opportunities"):
            return normalize_aeo_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_aeo_signals(
        topic=topic,
        content=content,
        target_questions=target_questions,
        entity_targets=entity_targets,
        schema_types=schema_types,
        use_openlens=use_openlens,
        use_playwright_validation=use_playwright_validation,
        retrieval_framework=retrieval_framework,
    )
    return normalize_aeo_result(heur, analysis_mode="heuristic", ai_available=False)
