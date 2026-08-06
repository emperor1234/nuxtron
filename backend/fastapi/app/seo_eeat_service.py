"""
E-E-A-T Scorer — module 9.

Scores Experience, Expertise, Authoritativeness, and Trust from content and author signals.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_EXPERIENCE_RE = re.compile(
    r"\b(i tested|i tried|in my experience|we tested|hands-on|case study|first-hand|firsthand)\b",
    re.IGNORECASE,
)
_EXPERTISE_RE = re.compile(
    r"\b(certified|phd|md|cpa|engineer|research|study|methodology|analysis|expert)\b",
    re.IGNORECASE,
)
_AUTHORITY_RE = re.compile(r"https?://[^\s]+|\[[^\]]+\]\([^)]+\)", re.IGNORECASE)
_TRUST_RE = re.compile(
    r"\b(privacy policy|terms of service|contact us|editorial policy|fact-check|updated on|reviewed by)\b",
    re.IGNORECASE,
)
_CREDENTIAL_RE = re.compile(
    r"\b(\d+\+?\s*years?|certified|cpa|md|phd|professor|director|founder|lead)\b",
    re.IGNORECASE,
)
_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_YMYL_NICHES = {
    "health": "health",
    "medical": "health",
    "finance": "finance",
    "financial": "finance",
    "legal": "legal",
    "law": "legal",
    "news": "news",
    "ecommerce": "ecommerce",
}


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def _quality_tier(score: int) -> str:
    if score >= 85:
        return "Highest"
    if score >= 70:
        return "High"
    if score >= 55:
        return "Medium"
    if score >= 40:
        return "Low"
    return "Lowest"


def _ymyl_category(niche: str) -> tuple[bool, str]:
    niche_lower = niche.strip().lower()
    for token, category in _YMYL_NICHES.items():
        if token in niche_lower:
            return True, category
    return False, "none"


def analyze_eeat_signals(*, content: str, author_bio: str, domain: str, niche: str) -> dict[str, Any]:
    """Deterministic E-E-A-T scoring from author and content trust signals."""
    body = content.strip()
    bio = author_bio.strip()
    site = domain.strip()
    niche_clean = niche.strip()

    word_count = _word_count(body)
    experience_hits = len(_EXPERIENCE_RE.findall(body))
    expertise_hits = len(_EXPERTISE_RE.findall(body)) + len(_EXPERTISE_RE.findall(bio))
    authority_links = len(_AUTHORITY_RE.findall(body))
    trust_hits = len(_TRUST_RE.findall(body))
    credential_hits = len(_CREDENTIAL_RE.findall(bio))
    bracket_count = len(_BRACKET_RE.findall(body))

    parsed = urlparse(site if "://" in site else f"https://{site}") if site else None
    https_ok = bool(parsed and parsed.scheme == "https")

    experience_score = 34
    if experience_hits >= 2:
        experience_score += 22
    elif experience_hits == 1:
        experience_score += 12
    if word_count >= 200:
        experience_score += 8
    experience_score = _clamp(experience_score)

    expertise_score = 32
    if credential_hits >= 2:
        expertise_score += 22
    elif credential_hits == 1:
        expertise_score += 12
    if expertise_hits >= 2:
        expertise_score += 14
    elif expertise_hits == 1:
        expertise_score += 8
    if bio:
        expertise_score += 6
    expertise_score -= min(10, bracket_count * 3)
    expertise_score = _clamp(expertise_score)

    authority_score = 30
    if authority_links >= 3:
        authority_score += 24
    elif authority_links >= 1:
        authority_score += 12
    if site:
        authority_score += 8
    if word_count >= 300:
        authority_score += 8
    authority_score = _clamp(authority_score)

    trust_score = 34
    if https_ok:
        trust_score += 12
    if trust_hits >= 2:
        trust_score += 16
    elif trust_hits == 1:
        trust_score += 8
    if bio and credential_hits >= 1:
        trust_score += 10
    trust_score = _clamp(trust_score)

    is_ymyl, ymyl_category = _ymyl_category(niche_clean)
    if is_ymyl:
        penalty = 8 if trust_score < 60 else 4
        experience_score = _clamp(experience_score - penalty)
        expertise_score = _clamp(expertise_score - penalty)
        trust_score = _clamp(trust_score - penalty)

    eeat_score = _clamp(int(round((experience_score + expertise_score + authority_score + trust_score) / 4)))

    critical_gaps: list[dict[str, Any]] = []
    if not bio:
        critical_gaps.append(
            {
                "signal": "expertise",
                "gap": "No author bio with credentials or first-hand experience.",
                "severity": "critical" if is_ymyl else "high",
                "fix": "Add an author box with role, credentials, and relevant experience.",
                "effort": "low",
            }
        )
    if authority_links < 2:
        critical_gaps.append(
            {
                "signal": "authority",
                "gap": "Insufficient outbound citations to authoritative sources.",
                "severity": "high",
                "fix": "Cite at least two primary or industry sources for key claims.",
                "effort": "medium",
            }
        )
    if experience_hits == 0:
        critical_gaps.append(
            {
                "signal": "experience",
                "gap": "No first-hand experience language detected in content.",
                "severity": "medium",
                "fix": "Add case examples or tested outcomes using first-person experience phrasing.",
                "effort": "medium",
            }
        )
    if not https_ok and site:
        critical_gaps.append(
            {
                "signal": "trust",
                "gap": "Domain is not indicated as HTTPS.",
                "severity": "high",
                "fix": "Publish over HTTPS and surface privacy/contact policies.",
                "effort": "medium",
            }
        )

    improvements: list[dict[str, Any]] = [
        {
            "signal": "trust",
            "action": "Add visible last-updated date and reviewer attribution on the page.",
            "impact": 78,
            "implementation": "Place date + reviewer line under the title.",
            "timeline_days": 7,
        },
        {
            "signal": "authority",
            "action": "Link to two authoritative references supporting core claims.",
            "impact": 72,
            "implementation": "Use inline citations with outbound links.",
            "timeline_days": 10,
        },
    ]
    if not bio:
        improvements.insert(
            0,
            {
                "signal": "expertise",
                "action": "Publish a detailed author bio with credentials and publication history.",
                "impact": 85,
                "implementation": "Add author schema and bio block.",
                "timeline_days": 5,
            },
        )

    author_bio_audit = {
        "has_bio": bool(bio),
        "credential_signals_present": credential_hits >= 1,
        "first_hand_experience_present": experience_hits >= 1 or bool(re.search(r"\b(i|we)\b", bio, re.IGNORECASE)),
        "recommended_elements": [],
    }
    author_bio_suggestions: list[str] = []
    if not bio:
        author_bio_suggestions.append("Add professional title and years of experience.")
    if credential_hits == 0:
        author_bio_suggestions.append("Include verifiable credentials relevant to the niche.")
        author_bio_audit["recommended_elements"].append("professional_title")
    if not author_bio_audit["first_hand_experience_present"]:
        author_bio_suggestions.append("Mention first-hand work, testing, or client outcomes.")
        author_bio_audit["recommended_elements"].append("first_hand_experience")
    if authority_links == 0:
        author_bio_suggestions.append("Link to published works, profiles, or certifications.")
        author_bio_audit["recommended_elements"].append("publication_links")

    trust_signals_present: list[str] = []
    if https_ok:
        trust_signals_present.append("ssl")
    if re.search(r"privacy", body, re.IGNORECASE):
        trust_signals_present.append("privacy_policy")

    trust_signals_missing = [
        signal
        for signal, present in (
            ("editorial_policy", bool(re.search(r"editorial", body, re.IGNORECASE))),
            ("fact_check_process", bool(re.search(r"fact[- ]check", body, re.IGNORECASE))),
            ("corrections_policy", bool(re.search(r"correction", body, re.IGNORECASE))),
            ("expert_review_badge", bool(re.search(r"reviewed by|medically reviewed", body, re.IGNORECASE))),
        )
        if not present
    ]

    return {
        "eeat_score": eeat_score,
        "experience_score": experience_score,
        "expertise_score": expertise_score,
        "authority_score": authority_score,
        "trust_score": trust_score,
        "quality_tier": _quality_tier(eeat_score),
        "critical_gaps": critical_gaps,
        "improvements": improvements,
        "author_bio_audit": author_bio_audit,
        "author_bio_suggestions": author_bio_suggestions,
        "trust_signals_present": trust_signals_present,
        "trust_signals_missing": trust_signals_missing,
        "ymyl_assessment": {
            "is_ymyl": is_ymyl,
            "ymyl_category": ymyl_category,
            "heightened_eeat_required": is_ymyl,
        },
        "authority_builders": [
            {
                "action": "Earn mentions from niche publications or directories.",
                "source_type": "publication",
                "authority_gain": "high",
            }
        ],
        "benchmark": {
            "industry_avg_eeat": 58,
            "your_gap": max(-20, eeat_score - 58),
            "top_competitor_eeat": min(92, eeat_score + 14),
            "gap_to_leader": max(0, min(92, eeat_score + 14) - eeat_score),
        },
        "quick_wins": [
            "Add author byline with credentials above the fold.",
            "Cite two authoritative sources for key claims.",
            "Show last-updated date near the title.",
        ],
        "30_day_eeat_roadmap": [
            {
                "week": 1,
                "actions": ["Publish author bio", "Add citations to core claims"],
                "expected_score_gain": 5,
            },
            {
                "week": 2,
                "actions": ["Add editorial or review policy page", "Include first-hand examples"],
                "expected_score_gain": 4,
            },
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "word_count": word_count,
            "experience_hits": experience_hits,
            "authority_links": authority_links,
            "credential_hits": credential_hits,
            "ymyl": is_ymyl,
        },
    }


def normalize_eeat_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    for score_key in (
        "eeat_score",
        "experience_score",
        "expertise_score",
        "authority_score",
        "trust_score",
    ):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, 50))))
        except (TypeError, ValueError):
            out[score_key] = 50

    if not out.get("quality_tier"):
        out["quality_tier"] = _quality_tier(out["eeat_score"])

    for list_key in (
        "critical_gaps",
        "improvements",
        "trust_signals_present",
        "trust_signals_missing",
        "quick_wins",
        "30_day_eeat_roadmap",
        "authority_builders",
    ):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []

    if not isinstance(out.get("author_bio_audit"), dict):
        out["author_bio_audit"] = {}

    if not isinstance(out.get("author_bio_suggestions"), list):
        audit = out.get("author_bio_audit") or {}
        recommended = audit.get("recommended_elements")
        if isinstance(recommended, list) and recommended:
            out["author_bio_suggestions"] = [f"Add {item.replace('_', ' ')}" for item in recommended]
        else:
            out["author_bio_suggestions"] = []

    if not isinstance(out.get("ymyl_assessment"), dict):
        out["ymyl_assessment"] = {"is_ymyl": False, "ymyl_category": "none", "heightened_eeat_required": False}

    if not isinstance(out.get("benchmark"), dict):
        out["benchmark"] = {"industry_avg_eeat": 58, "your_gap": 0, "top_competitor_eeat": 82, "gap_to_leader": 0}

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_eeat_score(
    *,
    content: str,
    author_bio: str,
    domain: str,
    niche: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run E-E-A-T scoring."""
    prompt = (
        f"Score E-E-A-T for domain: {clean_text_fn(domain, 200)} in niche: {clean_text_fn(niche, 120)}.\n"
        f"Author bio: {clean_text_fn(author_bio, 500)}.\n"
        f"Content:\n{clean_text_fn(content, 3000)}\n\n"
        "Score all four dimensions, identify gaps, and suggest trust improvements. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("eeat_score") is not None or llm_result.get("experience_score") is not None:
            return normalize_eeat_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_eeat_signals(content=content, author_bio=author_bio, domain=domain, niche=niche)
    return normalize_eeat_result(heuristic, analysis_mode="heuristic", ai_available=False)
