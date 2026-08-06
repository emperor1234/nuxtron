"""
LLMO (LLM Brand Optimization) — production implementation (module 4).

Audits brand representation readiness from operator-supplied claims, competitors,
and optional homepage signals. No generic placeholder model narratives.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from .seo_ai_service import fetch_page_signals, normalize_domain

logger = logging.getLogger(__name__)

_MODEL_KEYS = ("gpt4o", "claude_35", "gemini_15", "perplexity", "bing_copilot")
_SPECIFIC_CLAIM_RE = re.compile(
    r"\b\d{4}\b|\b\d+%|\b(founded|since|pricing|customers|users|revenue)\b",
    re.IGNORECASE,
)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _risk_level(score: int, claim_count: int, domain_ok: bool) -> str:
    if score >= 72 and claim_count >= 4 and domain_ok:
        return "low"
    if score >= 52 and claim_count >= 2:
        return "medium"
    return "high"


def analyze_llmo_signals(
    *,
    brand: str,
    domain: str,
    key_claims: list[str],
    competitors: list[str],
    page: dict[str, Any],
) -> dict[str, Any]:
    """Deterministic LLMO audit from brand inputs and crawl signals."""
    brand_clean = brand.strip()
    claims = [c.strip() for c in key_claims if c and c.strip()]
    rivals = [c.strip() for c in competitors if c and c.strip()]
    domain_ok = bool(normalize_domain(domain)) and page.get("fetch_ok")
    specific_claims = sum(1 for c in claims if _SPECIFIC_CLAIM_RE.search(c))

    score = 38
    score += min(24, len(claims) * 5)
    score += min(12, specific_claims * 4)
    if domain_ok:
        score += 12
    if page.get("meta_description"):
        score += 4
    if page.get("has_canonical"):
        score += 3
    if rivals:
        score += min(8, len(rivals) * 2)
    if page.get("robots_noindex"):
        score -= 20
    if not claims:
        score -= 15
    score = _clamp(score)

    consistency = _clamp(score - 4 + min(10, specific_claims * 2))
    risk = _risk_level(score, len(claims), domain_ok)

    model_representations: dict[str, str] = {}
    for index, key in enumerate(_MODEL_KEYS):
        if not brand_clean:
            model_representations[key] = "Brand name required for model-specific audit."
            continue
        if len(claims) >= 4 and domain_ok:
            model_representations[key] = (
                f"{brand_clean} has structured claims and a crawlable domain; "
                f"monitor {key.replace('_', ' ')} for drift on: {claims[0][:80]}."
            )
        elif len(claims) >= 1:
            model_representations[key] = (
                f"{brand_clean} has {len(claims)} documented claim(s); "
                f"expand canonical facts before relying on {key.replace('_', ' ')} answers."
            )
        else:
            model_representations[key] = (
                f"{brand_clean} lacks verified claims in this audit; "
                f"{key.replace('_', ' ')} may infer incomplete or generic positioning."
            )

    misinformation_risks: list[dict[str, Any]] = []
    if not domain_ok:
        misinformation_risks.append(
            {
                "risk": "Canonical domain not verified or not crawlable",
                "severity": "high",
                "affected_models": list(_MODEL_KEYS),
                "correction": "Fix DNS/TLS and publish a public homepage with Organization schema.",
            }
        )
    if len(claims) < 3:
        misinformation_risks.append(
            {
                "risk": "Insufficient verified brand claims on file",
                "severity": "medium",
                "affected_models": ["gpt4o", "perplexity"],
                "correction": "Document at least five verifiable claims with sources.",
            }
        )
    if specific_claims < 2 and claims:
        misinformation_risks.append(
            {
                "risk": "Claims lack dates, metrics, or verifiable anchors",
                "severity": "medium",
                "affected_models": ["claude_35", "gemini_15"],
                "correction": "Add founding year, customer counts, or product version to each claim.",
            }
        )

    knowledge_gaps: list[dict[str, Any]] = []
    standard_topics = [
        ("Company mission and positioning", "missing" if len(claims) < 2 else "outdated"),
        ("Product pricing and packaging", "missing"),
        ("Customer proof and case studies", "missing" if specific_claims < 2 else "outdated"),
    ]
    for topic, gap_type in standard_topics:
        knowledge_gaps.append({"topic": topic, "gap_type": gap_type, "fix_effort": "low" if gap_type == "missing" else "medium"})

    citation_plan: list[dict[str, Any]] = [
        {
            "action": f"Publish canonical About page for {brand_clean} with Organization JSON-LD",
            "source_type": "press_release",
            "timeline_days": 21,
            "impact": "high",
        },
        {
            "action": "Document each key claim on a single /facts page with outbound citations",
            "source_type": "data_study",
            "timeline_days": 30,
            "impact": "high",
        },
    ]
    if rivals:
        citation_plan.append(
            {
                "action": f"Publish comparison content vs {rivals[0]} with cited third-party sources",
                "source_type": "press_release",
                "timeline_days": 45,
                "impact": "medium",
            }
        )

    correction_strategy = [
        {"step": "Audit AI answers for top branded queries", "owner": "seo", "deadline_weeks": 2},
        {"step": "Align website copy with verified claim ledger", "owner": "content", "deadline_weeks": 3},
        {"step": "Track competitor mention accuracy weekly", "owner": "seo", "deadline_weeks": 4},
    ]

    entity_signals = [
        {
            "signal": "Organization JSON-LD on homepage",
            "present": domain_ok and page.get("fetch_ok"),
            "acquisition_method": "Add schema.org/Organization to primary template",
        },
        {
            "signal": "Wikidata entity",
            "present": False,
            "acquisition_method": "Create after notability coverage in independent publications",
        },
    ]

    queries = [f"What is {brand_clean}?", f"Who are {brand_clean} competitors?"]
    if rivals:
        queries.append(f"How does {brand_clean} compare to {rivals[0]}?")
    for claim in claims[:2]:
        queries.append(f"Is it true that {brand_clean} {claim[:60]}?")

    return {
        "brand_ai_score": score,
        "accuracy_risk": risk,
        "consistency_score": consistency,
        "model_representations": model_representations,
        "misinformation_risks": misinformation_risks,
        "knowledge_gaps": knowledge_gaps,
        "citation_building_plan": citation_plan,
        "correction_strategy": correction_strategy,
        "entity_authority_signals": entity_signals,
        "training_data_influence": {
            "preferred_sources": ["wikipedia.org", "wikidata.org", normalize_domain(domain) or "owned-domain"],
            "toxic_sources_to_suppress": [],
            "freshness_score": _clamp(40 + specific_claims * 8 + (12 if domain_ok else 0)),
        },
        "monitoring_plan": {
            "queries_to_track": queries[:8],
            "frequency": "weekly",
            "alert_threshold_score": 50,
        },
        "quick_wins": [
            f"Publish five verified claims for {brand_clean} on a single /brand-facts page",
            "Add Organization JSON-LD with legal name, URL, and sameAs profiles",
            "Run weekly spot-checks on the queries in monitoring_plan",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "brand_signals": {
            "claims_provided": len(claims),
            "specific_claims": specific_claims,
            "competitors_listed": len(rivals),
            "domain_crawl_ok": domain_ok,
            "page_url": page.get("url"),
        },
    }


def normalize_llmo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    try:
        out["brand_ai_score"] = _clamp(int(float(out.get("brand_ai_score", 50))))
    except (TypeError, ValueError):
        out["brand_ai_score"] = 50

    try:
        out["consistency_score"] = _clamp(int(float(out.get("consistency_score", out["brand_ai_score"]))))
    except (TypeError, ValueError):
        out["consistency_score"] = int(out["brand_ai_score"])

    risk = str(out.get("accuracy_risk", "medium")).lower()
    if risk not in ("low", "medium", "high"):
        out["accuracy_risk"] = _risk_level(int(out["brand_ai_score"]), 0, False)
    else:
        out["accuracy_risk"] = risk

    for list_key in (
        "misinformation_risks",
        "knowledge_gaps",
        "citation_building_plan",
        "correction_strategy",
        "entity_authority_signals",
        "quick_wins",
    ):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []

    reps = out.get("model_representations")
    if not isinstance(reps, dict):
        out["model_representations"] = {}

    monitoring = out.get("monitoring_plan")
    if not isinstance(monitoring, dict):
        out["monitoring_plan"] = {"queries_to_track": [], "frequency": "weekly", "alert_threshold_score": 50}

    influence = out.get("training_data_influence")
    if not isinstance(influence, dict):
        out["training_data_influence"] = {"preferred_sources": [], "toxic_sources_to_suppress": [], "freshness_score": 50}

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_llmo_brand(
    *,
    brand: str,
    domain: str,
    key_claims: list[str],
    competitors: list[str],
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run LLMO brand audit."""
    page = await fetch_page_signals(domain) if domain.strip() else {"fetch_ok": False, "url": ""}
    prompt = (
        f"Conduct a comprehensive LLMO audit for brand: '{clean_text_fn(brand, 200)}'.\n"
        f"Domain: {clean_text_fn(domain, 300)}.\n"
        f"Key claims: {clean_text_fn(', '.join(key_claims[:10]), 1500)}.\n"
        f"Competitors: {clean_text_fn(', '.join(competitors[:5]), 500)}.\n"
        f"Homepage signals: {clean_text_fn(str(page), 1500)}\n"
        "Return brand_ai_score, accuracy_risk, model_representations, knowledge gaps, and action plans. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("brand_ai_score") is not None or llm_result.get("model_representations"):
            return normalize_llmo_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_llmo_signals(
        brand=brand,
        domain=domain,
        key_claims=key_claims,
        competitors=competitors,
        page=page,
    )
    return normalize_llmo_result(heuristic, analysis_mode="heuristic", ai_available=False)
