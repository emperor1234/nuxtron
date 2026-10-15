"""Helpers for review-only SEO workflow drafts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _default_workflow() -> list[dict[str, str]]:
    """Return a generic review sequence; no task in it is executed here."""
    return [
        {
            "phase": "Confirm scope",
            "module": "Your brief",
            "action": "Set a measurable outcome, baseline, owner, and review date before prioritizing work.",
            "path": "",
        },
        {
            "phase": "Validate search evidence",
            "module": "Keyword Data Review",
            "action": "Inspect a keyword export you provide; no search-demand metrics are generated here.",
            "path": "/seo/keywords",
        },
        {
            "phase": "Prepare content",
            "module": "Content Generation",
            "action": "Create an editable draft from a reviewed brief; publication remains a human decision.",
            "path": "/content-generation",
        },
        {
            "phase": "Review results",
            "module": "Analysis History",
            "action": "Run supported analyses separately and compare archived results after approved changes.",
            "path": "/seo/history",
        },
    ]


def analyze_planner_execute_signals(
    *,
    goal: str,
    domain: str,
    primary_keyword: str,
    market: str,
) -> dict[str, Any]:
    """Create clearly generic suggestions from the submitted brief, not site facts."""
    site = domain.strip() or "your site"
    keyword = primary_keyword.strip() or "your target topic"
    market_name = market.strip() or "your selected market"
    return {
        "priorities": [
            f"Review search intent for {keyword} in {market_name} before choosing target pages.",
            f"Consider a focused content brief for {site} before increasing publishing volume.",
            "Validate any technical or structured-data work against current findings before prioritizing it.",
        ],
        "risks": [
            "A plan drafted without current ranking, search-demand, or crawl evidence may prioritize the wrong work.",
            "Publishing or technical changes without an owner and review step can create avoidable risk.",
        ],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_planner_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    """Return only supported draft fields; discard ungrounded score-like model output."""
    out: dict[str, Any] = {}
    for list_key in ("priorities", "risks", "next_actions"):
        value = raw.get(list_key)
        out[list_key] = (
            [item.strip()[:1000] for item in value if isinstance(item, str) and item.strip()][:20]
            if isinstance(value, list)
            else []
        )
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def execute_planner(
    *,
    goal: str,
    domain: str,
    primary_keyword: str,
    market: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    safe_goal = clean_text_fn(goal, 500)
    safe_domain = clean_text_fn(domain, 200)
    safe_keyword = clean_text_fn(primary_keyword, 200)
    safe_market = clean_text_fn(market, 200)
    prompt = (
        f"Create a review-only SEO workflow draft for goal '{safe_goal}'. "
        f"Domain: {safe_domain}. Primary keyword: {safe_keyword}. Market: {safe_market}. "
        "Use only this brief. Do not imply that you inspected a site, rankings, analytics, crawl data, or competitors. "
        "Return only priorities, potential risks, and next_actions as concise suggestions."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if (
        isinstance(llm, dict)
        and not llm.get("fallback")
        and not llm.get("error")
        and (llm.get("priorities") or llm.get("risks") or llm.get("next_actions"))
    ):
        return normalize_planner_result(llm, analysis_mode="llm", ai_available=True)
    fallback = analyze_planner_execute_signals(
        goal=goal,
        domain=domain,
        primary_keyword=primary_keyword,
        market=market,
    )
    return normalize_planner_result(fallback, analysis_mode="heuristic", ai_available=False)


def default_planner_workflow() -> list[dict[str, str]]:
    """Return the generic, unexecuted sequence shown with a Planner draft."""
    return _default_workflow()
