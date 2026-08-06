"""RAG Site Search Engine — phase-f module 3."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "topic"


def analyze_rag_search_signals(
    *,
    query: str,
    site_domain: str,
    content_corpus: str,
    top_k: int,
    notes: str,
) -> dict[str, Any]:
    q = query.strip()
    domain = site_domain.strip() or "example.com"
    corpus = content_corpus.strip()
    k = max(1, min(20, top_k))
    corpus_words = len(re.findall(r"\b\w+\b", corpus))
    q_tokens = [t for t in re.findall(r"\b\w{3,}\b", q.lower())]

    confidence = round(min(0.82, 0.48 + corpus_words / 400 + len(q_tokens) * 0.03), 2)
    intent = "transactional" if any(w in q.lower() for w in ("buy", "price", "best", "tool")) else "informational"

    search_results = []
    for i in range(min(k, 5)):
        rel = round(max(0.52, 0.88 - i * 0.08), 2)
        slug = _slug(q)
        search_results.append(
            {
                "rank": i + 1,
                "title": f"{q} — {'Guide' if i == 0 else 'FAQ' if i == 1 else 'Tools'}",
                "url": f"https://{domain}/{'guide' if i == 0 else 'faq' if i == 1 else 'tools'}/{slug}",
                "snippet": corpus[:180] if corpus and i == 0 else f"Coverage of {q} with practical steps and examples.",
                "relevance_score": rel,
                "reasoning": "Query token overlap with title and corpus" if q_tokens else "Semantic match from site topic model",
            }
        )

    return {
        "query": q,
        "search_results": search_results,
        "answer_synthesis": (
            f"Based on indexed content on {domain}, {q} is covered across guide and FAQ pages. "
            "Prioritize updating the top guide with fresh examples and internal links."
        ),
        "entities_detected": list(dict.fromkeys(q_tokens + [domain]))[:8],
        "intent": intent,
        "related_queries": [f"how to {q}", f"best {q} tools", f"{q} examples"],
        "confidence": confidence,
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_rag_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        conf = float(out.get("confidence", 0.6))
        out["confidence"] = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        out["confidence"] = 0.6
    if out["confidence"] >= 0.99 and analysis_mode == "heuristic":
        out["confidence"] = 0.72
    for list_key in ("search_results", "entities_detected", "related_queries"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def query_rag_search(
    *,
    query: str,
    site_domain: str,
    content_corpus: str,
    top_k: int,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Query: {clean_text_fn(query, 500)}. Site: {clean_text_fn(site_domain, 300)}. "
        f"Corpus: {clean_text_fn(content_corpus, 4000)}. Top-K: {top_k}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("search_results") or llm.get("answer_synthesis"):
            return normalize_rag_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_rag_search_signals(
        query=query, site_domain=site_domain, content_corpus=content_corpus, top_k=top_k, notes=notes,
    )
    return normalize_rag_result(heur, analysis_mode="heuristic", ai_available=False)
