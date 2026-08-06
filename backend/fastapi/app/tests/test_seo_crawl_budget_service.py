"""Unit tests for Crawl Budget service (phase-e module 5)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_crawl_budget_service import analyze_crawl_budget, analyze_crawl_budget_signals


def test_heuristic_scales() -> None:
    thin = analyze_crawl_budget_signals(domain="example.com", sample_urls=["/"], log_snippet="", notes="")
    rich = analyze_crawl_budget_signals(
        domain="big.example",
        sample_urls=["/", "/pricing", "/features", "/blog/seo"],
        log_snippet="GET /pricing 200\nGET /features 200",
        notes="Baseline crawl review",
    )
    assert rich["crawl_budget_score"] > thin["crawl_budget_score"]
    assert thin["crawl_budget_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"crawl_budget_score": 69, "priority_buckets": {"high": ["/"]}}

    assert (
        await analyze_crawl_budget(
            domain="example.com",
            sample_urls=["/"],
            log_snippet="",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_crawl_budget(
            domain="example.com",
            sample_urls=[],
            log_snippet="",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
