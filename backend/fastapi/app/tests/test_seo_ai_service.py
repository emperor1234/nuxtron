"""Unit tests for production SEO-AI service (module 1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_ai_service import (
    analyze_seo_ai_core,
    heuristic_seo_ai_analysis,
    normalize_domain,
    normalize_seo_ai_result,
)


def test_normalize_domain_strips_scheme() -> None:
    assert normalize_domain("https://Example.COM/path") == "example.com"


def test_heuristic_never_returns_perfect_score_without_signals() -> None:
    result = heuristic_seo_ai_analysis(
        domain="example.com",
        primary_keyword="crm software",
        business_goal="growth",
        content_excerpt="",
        notes="",
        page={"fetch_ok": False, "url": "https://example.com", "error": "timeout"},
    )
    assert result["seo_ai_score"] <= 88
    assert result["analysis_mode"] == "heuristic"
    assert result["ai_available"] is False
    assert any("crawled" in t["issue"].lower() for t in result["technical_priorities"])


def test_heuristic_boosts_score_when_keyword_in_excerpt() -> None:
    thin = heuristic_seo_ai_analysis(
        domain="example.com",
        primary_keyword="crm",
        business_goal="growth",
        content_excerpt="",
        notes="",
        page={"fetch_ok": False},
    )
    rich = heuristic_seo_ai_analysis(
        domain="example.com",
        primary_keyword="crm",
        business_goal="growth",
        content_excerpt="Our crm platform helps teams manage pipeline and revenue with crm workflows.",
        notes="",
        page={"fetch_ok": True, "h1_count": 1, "meta_description": "crm tool", "has_canonical": True},
    )
    assert rich["seo_ai_score"] > thin["seo_ai_score"]


def test_normalize_strips_fallback_keys() -> None:
    out = normalize_seo_ai_result(
        {"seo_ai_score": 150, "fallback": True, "error": "x", "keyword_opportunities": []},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["seo_ai_score"] == 100
    assert "fallback" not in out
    assert "error" not in out


@pytest.mark.asyncio
async def test_analyze_uses_llm_when_valid() -> None:
    async def _good_llm(_sys: str, _user: str, **_kw: object) -> dict:
        return {
            "seo_ai_score": 72,
            "keyword_opportunities": [{"keyword": "crm", "intent": "commercial", "priority": "high"}],
            "content_priorities": [],
            "technical_priorities": [],
            "serp_strategy": {"primary_surface": "organic", "ctr_focus": "a", "snippet_angle": "b"},
            "next_actions": ["a"],
        }

    with patch(
        "backend.fastapi.app.seo_ai_service.fetch_page_signals",
        new=AsyncMock(return_value={"fetch_ok": True, "url": "https://example.com", "status_code": 200}),
    ):
        result = await analyze_seo_ai_core(
            domain="example.com",
            primary_keyword="crm",
            business_goal="growth",
            content_excerpt="crm software for startups",
            notes="",
            ollama_json_fn=_good_llm,
            system_prompt="sys",
            clean_text_fn=lambda t, _m: t,
        )
    assert result["analysis_mode"] == "llm"
    assert result["ai_available"] is True
    assert result["seo_ai_score"] == 72


@pytest.mark.asyncio
async def test_analyze_heuristic_when_llm_fallback() -> None:
    async def _fail_llm(_sys: str, _user: str, **_kw: object) -> dict:
        return {"fallback": True, "error": "connection refused"}

    with patch(
        "backend.fastapi.app.seo_ai_service.fetch_page_signals",
        new=AsyncMock(return_value={"fetch_ok": False, "url": "https://example.com"}),
    ):
        result = await analyze_seo_ai_core(
            domain="example.com",
            primary_keyword="crm",
            business_goal="growth",
            content_excerpt="",
            notes="",
            ollama_json_fn=_fail_llm,
            system_prompt="sys",
            clean_text_fn=lambda t, _m: t,
        )
    assert result["analysis_mode"] == "heuristic"
    assert result["seo_ai_score"] < 90
