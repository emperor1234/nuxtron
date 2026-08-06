"""
DAEO (Decentralized Answer Engine Optimization) — module 13.

Assesses federated and self-hosted answer-engine readiness from domain and fact inputs.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_PROTOCOLS = ["self_hosted_search", "federated_index", "knowledge_api"]
_PROTOCOL_ALIASES = {
    "self_hosted_search": "self_hosted_search",
    "self-hosted search": "self_hosted_search",
    "federated_index": "federated_index",
    "federated index": "federated_index",
    "knowledge_api": "knowledge_api",
    "knowledge api": "knowledge_api",
    "activitypub": "ActivityPub",
    "nostr": "Nostr",
    "atproto": "ATProto",
    "solid": "Solid",
    "ipfs": "IPFS_knowledge",
}
_API_RE = re.compile(r"\b(api|endpoint|json-ld|well-known|federation|index)\b", re.IGNORECASE)
_BRACKET_RE = re.compile(r"\[[^\]]+\]")


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _clamp_conf(value: float) -> float:
    return round(max(0.05, min(0.98, value)), 2)


def _normalize_protocol(raw: str) -> str:
    key = raw.strip().lower()
    return _PROTOCOL_ALIASES.get(key, raw.strip().replace(" ", "_"))


def analyze_daeo_signals(
    *,
    domain: str,
    protocol_targets: list[str],
    canonical_facts: list[str],
    federation_notes: str,
    notes: str,
) -> dict[str, Any]:
    """Deterministic DAEO readiness scoring."""
    site = domain.strip()
    protocols = [_normalize_protocol(p) for p in protocol_targets if p.strip()] or _DEFAULT_PROTOCOLS.copy()
    facts = [f.strip() for f in canonical_facts if f.strip()]
    federation = federation_notes.strip()
    notes_text = notes.strip()
    combined = f"{federation}\n{notes_text}".lower()

    parsed = urlparse(site if "://" in site else f"https://{site}") if site else None
    https_ok = bool(parsed and parsed.scheme == "https")

    fact_count = len(facts)
    api_hits = len(_API_RE.findall(federation + notes_text))
    bracket_count = len(_BRACKET_RE.findall(federation + notes_text))
    has_well_known = "well-known" in combined or ".well-known" in combined

    decentralization_score = 34
    decentralization_score += min(20, fact_count * 5)
    decentralization_score += min(16, api_hits * 4)
    decentralization_score += 10 if https_ok else 0
    decentralization_score += min(12, len(protocols) * 3)
    decentralization_score -= min(12, bracket_count * 4)
    decentralization_score = _clamp(decentralization_score)

    federation_readiness_score = 32
    federation_readiness_score += min(18, fact_count * 4)
    federation_readiness_score += min(20, api_hits * 5)
    federation_readiness_score += 12 if has_well_known else 0
    federation_readiness_score += 8 if len(federation) >= 80 else 0
    federation_readiness_score = _clamp(federation_readiness_score)

    interoperability_score = _clamp(int(round((decentralization_score + federation_readiness_score) / 2)))

    protocol_opportunities: list[dict[str, Any]] = []
    for protocol in protocols[:8]:
        readiness = "high" if protocol in {"knowledge_api", "self_hosted_search"} and fact_count >= 2 else "medium"
        if protocol == "federated_index" and api_hits >= 2:
            readiness = "high"
        protocol_opportunities.append(
            {
                "protocol": protocol,
                "benefit": f"Improves federated discoverability for {site or 'the domain'} via {protocol.replace('_', ' ')}.",
                "readiness": readiness,
                "adoption_timeline": "6mo" if readiness == "high" else "12mo",
                "effort": "medium",
            }
        )

    canonical_fact_pack: list[dict[str, Any]] = []
    if facts:
        for fact in facts[:12]:
            canonical_fact_pack.append(
                {
                    "fact": fact,
                    "confidence": _clamp_conf(0.75 + min(0.2, len(fact) / 200)),
                    "source": site or "operator_provided",
                    "machine_readable_format": "json-ld",
                }
            )
    elif site:
        canonical_fact_pack.append(
            {
                "fact": f"{site} is the canonical source for brand and product facts.",
                "confidence": 0.7,
                "source": site,
                "machine_readable_format": "json-ld",
            }
        )

    self_hosting_gaps: list[dict[str, Any]] = []
    if not has_well_known:
        self_hosting_gaps.append(
            {
                "gap": "Missing machine-readable facts endpoint under /.well-known/",
                "risk_if_unaddressed": "Federated crawlers cannot fetch canonical facts reliably.",
                "fix": "Publish /.well-known/facts.json with JSON-LD fact pack.",
            }
        )
    if fact_count < 3:
        self_hosting_gaps.append(
            {
                "gap": "Canonical fact pack has fewer than three verifiable claims",
                "risk_if_unaddressed": "Answer engines may treat outputs as low-trust.",
                "fix": "Add dated, source-linked facts for core brand claims.",
            }
        )
    if not https_ok and site:
        self_hosting_gaps.append(
            {
                "gap": "Domain not indicated as HTTPS in inputs",
                "risk_if_unaddressed": "Trust and integrity signals are weakened for federated consumers.",
                "fix": "Serve all fact endpoints over HTTPS with valid certificates.",
            }
        )

    knowledge_api = {
        "recommended_endpoint": "/.well-known/facts.json",
        "schema_format": "json-ld",
        "entities_to_expose": max(fact_count, 1),
        "auth_model": "public" if "token" not in combined else "token_gated",
    }

    trust_distribution_plan: list[dict[str, Any]] = [
        {
            "phase": 1,
            "action": "Publish canonical JSON-LD fact pack on owned domain",
            "trust_gain": "Establishes single source of truth for federated indexes",
            "timeline_weeks": 4,
        },
        {
            "phase": 2,
            "action": "Register core entities on Wikidata or equivalent knowledge graph",
            "trust_gain": "Improves cross-engine entity resolution",
            "timeline_weeks": 8,
        },
    ]
    if fact_count >= 2:
        trust_distribution_plan.append(
            {
                "phase": 3,
                "action": "Syndicate fact pack hash to federated index partners",
                "trust_gain": "Enables tamper-evident fact verification",
                "timeline_weeks": 12,
            }
        )

    next_actions: list[dict[str, Any]] = [
        {
            "action": "Deploy /.well-known/facts.json with canonical JSON-LD",
            "priority": "high",
            "effort": "medium",
            "expected_impact": "Unlocks self-hosted answer engine consumption",
        },
        {
            "action": "Document federation API constraints and auth model",
            "priority": "high",
            "effort": "low",
            "expected_impact": "Reduces integration friction for partners",
        },
    ]
    if notes_text:
        next_actions.append(
            {
                "action": f"Operator note: {notes_text[:160]}",
                "priority": "medium",
                "effort": "low",
                "expected_impact": "Aligns rollout with governance context",
            }
        )

    return {
        "decentralization_score": decentralization_score,
        "federation_readiness_score": federation_readiness_score,
        "interoperability_score": interoperability_score,
        "protocol_opportunities": protocol_opportunities,
        "canonical_fact_pack": canonical_fact_pack,
        "self_hosting_gaps": self_hosting_gaps,
        "knowledge_api": knowledge_api,
        "trust_distribution_plan": trust_distribution_plan,
        "next_actions": next_actions,
        "quick_wins": [
            "Publish three canonical facts with sources in JSON-LD.",
            "Add link rel=canonical on fact-bearing pages.",
            "Expose a read-only knowledge API endpoint for partners.",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "canonical_fact_count": fact_count,
            "protocol_count": len(protocols),
            "api_signal_hits": api_hits,
            "has_well_known_endpoint": has_well_known,
        },
    }


def normalize_daeo_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    for score_key in ("decentralization_score", "federation_readiness_score", "interoperability_score"):
        try:
            out[score_key] = _clamp(int(float(out.get(score_key, 50))))
        except (TypeError, ValueError):
            out[score_key] = 50

    if not isinstance(out.get("knowledge_api"), dict):
        out["knowledge_api"] = {
            "recommended_endpoint": "/.well-known/facts.json",
            "schema_format": "json-ld",
            "entities_to_expose": 0,
            "auth_model": "public",
        }

    for list_key in (
        "protocol_opportunities",
        "canonical_fact_pack",
        "self_hosting_gaps",
        "trust_distribution_plan",
        "next_actions",
        "quick_wins",
    ):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_daeo_readiness(
    *,
    domain: str,
    protocol_targets: list[str],
    canonical_facts: list[str],
    federation_notes: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run DAEO analysis."""
    prompt = (
        f"Create a DAEO plan for domain: {clean_text_fn(domain, 300)}.\n"
        f"Protocol targets: {', '.join(protocol_targets[:10])}.\n"
        f"Canonical facts: {', '.join(canonical_facts[:12])}.\n"
        f"Federation notes:\n{clean_text_fn(federation_notes, 2200)}\n\n"
        f"Notes: {clean_text_fn(notes, 500)}.\n"
        "Score decentralization and federation readiness with actionable gaps. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("decentralization_score") is not None or llm_result.get("protocol_opportunities"):
            return normalize_daeo_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_daeo_signals(
        domain=domain,
        protocol_targets=protocol_targets,
        canonical_facts=canonical_facts,
        federation_notes=federation_notes,
        notes=notes,
    )
    return normalize_daeo_result(heuristic, analysis_mode="heuristic", ai_available=False)
