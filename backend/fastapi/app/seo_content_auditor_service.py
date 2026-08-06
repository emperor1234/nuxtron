"""Content Quality & Hallucination Auditor — phase-e module 2."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any

_NUMERIC_CLAIM_RE = re.compile(r"\b\d+(?:\.\d+)?%|\b\d{4}\b|\$\d")
_ABSOLUTE_RE = re.compile(r"\b(always|never|guaranteed|100%|best|worst|only)\b", re.IGNORECASE)
_CITATION_RE = re.compile(r"\b(according to|source:|citation|\[\d+\]|https?://)", re.IGNORECASE)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _map_verdict(verdict: str) -> str:
    v = verdict.strip().lower()
    if v in {"supported", "verified", "true"}:
        return "verified"
    if v in {"contradicted", "risky", "false"}:
        return "risky"
    return "unverified"


def analyze_content_auditor_signals(
    *,
    content: str,
    source_url: str,
    topic: str,
    target_model: str,
    notes: str,
) -> dict[str, Any]:
    text = content.strip()
    url = source_url.strip()
    topic_text = topic.strip()
    words = len(re.findall(r"\b\w+\b", text))
    numeric_hits = _NUMERIC_CLAIM_RE.findall(text)
    absolute_hits = _ABSOLUTE_RE.findall(text)
    citation_hits = len(_CITATION_RE.findall(text))

    quality_score = 34
    quality_score += min(20, words // 25)
    quality_score += min(12, citation_hits * 4)
    quality_score += 6 if url else 0
    quality_score += 4 if topic_text else 0
    quality_score -= min(18, len(numeric_hits) * 3)
    quality_score -= min(10, len(absolute_hits) * 2)
    quality_score = _clamp(quality_score)

    uncited = [m.group(0) for m in _NUMERIC_CLAIM_RE.finditer(text)][:4]
    fact_checks = []
    for claim in uncited[:3]:
        fact_checks.append(
            {
                "claim": f"Numeric or statistical claim involving {claim}",
                "verdict": "uncertain",
                "confidence": 0.58,
                "evidence_hint": "No inline citation detected near claim",
            }
        )
    if not fact_checks and words > 40:
        fact_checks.append(
            {
                "claim": text[:120] + ("..." if len(text) > 120 else ""),
                "verdict": "supported" if citation_hits else "uncertain",
                "confidence": 0.72 if citation_hits else 0.55,
                "evidence_hint": "Review primary sources for key assertions",
            }
        )

    risk_score = len(numeric_hits) - citation_hits + len(absolute_hits)
    hallucination_risk = "high" if risk_score >= 4 else ("medium" if risk_score >= 2 else "low")

    citation_coverage_pct = _clamp(min(85, 20 + citation_hits * 12 + (8 if url else 0)))

    eeat_base = _clamp(quality_score - 8)
    eeat_signals = {
        "expertise": eeat_base,
        "experience": _clamp(eeat_base - 4),
        "authority": _clamp(eeat_base - 2),
        "trust": _clamp(eeat_base + 4),
    }

    rewrite_recommendations = []
    if numeric_hits:
        rewrite_recommendations.append(
            {"issue": "Uncited numerical claims", "fix": "Attach source links and publication dates", "priority": "high"}
        )
    if absolute_hits:
        rewrite_recommendations.append(
            {"issue": "Absolute phrasing without qualification", "fix": "Use scoped language and conditions", "priority": "medium"}
        )

    frontend_fact_checks = [
        {
            "claim": fc["claim"],
            "verdict": _map_verdict(str(fc.get("verdict", "uncertain"))),
            "confidence": float(fc.get("confidence", 0.6)),
            "evidence_hint": fc.get("evidence_hint", ""),
        }
        for fc in fact_checks
    ]

    return {
        "quality_score": quality_score,
        "hallucination_risk": hallucination_risk,
        "fact_checks": fact_checks,
        "eeat_signals": eeat_signals,
        "citation_coverage_pct": citation_coverage_pct,
        "rewrite_recommendations": rewrite_recommendations,
        "risky_sections": ["Opening summary"] if numeric_hits else [],
        "quick_wins": ["Add citations to every numeric claim", "Include author credentials and updated date"],
        "recommended_tools": ["perplexity_fact_check", "google_scholar", "crossref"],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "_frontend_fact_checks": frontend_fact_checks,
    }


def normalize_content_auditor_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error", "_frontend_fact_checks")}
    try:
        out["quality_score"] = _clamp(int(float(out.get("quality_score", 50))))
    except (TypeError, ValueError):
        out["quality_score"] = 50
    try:
        out["citation_coverage_pct"] = _clamp(int(float(out.get("citation_coverage_pct", 50))))
    except (TypeError, ValueError):
        out["citation_coverage_pct"] = 50
    risk = str(out.get("hallucination_risk", "medium")).lower()
    out["hallucination_risk"] = risk if risk in {"low", "medium", "high"} else "medium"
    if not isinstance(out.get("eeat_signals"), dict):
        out["eeat_signals"] = {"expertise": 50, "experience": 50, "authority": 50, "trust": 50}
    for list_key in ("fact_checks", "rewrite_recommendations", "risky_sections", "quick_wins", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


def enrich_content_auditor_frontend(out: dict[str, Any]) -> dict[str, Any]:
    """Map API fact_checks to frontend verdict labels when needed."""
    mapped = []
    for fc in out.get("fact_checks") or []:
        if not isinstance(fc, dict):
            continue
        verdict = str(fc.get("verdict", "uncertain"))
        if verdict in {"verified", "unverified", "risky"}:
            front_verdict = verdict
        else:
            front_verdict = _map_verdict(verdict)
        mapped.append({**fc, "verdict": front_verdict})
    out["fact_checks"] = mapped
    return out


async def analyze_content_auditor(
    *,
    content: str,
    source_url: str,
    topic: str,
    target_model: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Source URL: {clean_text_fn(source_url, 500)}. Topic: {clean_text_fn(topic, 200)}. "
        f"Target model: {clean_text_fn(target_model, 200)}. Notes: {clean_text_fn(notes, 500)}. "
        f"Content: {clean_text_fn(content, 5000)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("quality_score") is not None or llm.get("fact_checks"):
            out = normalize_content_auditor_result(llm, analysis_mode="llm", ai_available=True)
            return enrich_content_auditor_frontend(out)
    heur = analyze_content_auditor_signals(
        content=content, source_url=source_url, topic=topic, target_model=target_model, notes=notes,
    )
    frontend_checks = heur.pop("_frontend_fact_checks", None)
    out = normalize_content_auditor_result(heur, analysis_mode="heuristic", ai_available=False)
    if frontend_checks:
        out["fact_checks"] = frontend_checks
    return enrich_content_auditor_frontend(out)
