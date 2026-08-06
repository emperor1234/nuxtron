"""Unit tests for Technical Audit service (phase-k module 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_technical_audit_service import analyze_technical_audit, analyze_technical_audit_signals


def test_heuristic_scales_with_crawl_options() -> None:
    base = analyze_technical_audit_signals(url="https://example.com", issues_raw=[])
    rich = analyze_technical_audit_signals(
        url="https://example.com",
        issues_raw=[],
        sitemap_url="https://example.com/sitemap.xml",
        crawl_depth=5,
    )
    assert rich["overall_score"] >= base["overall_score"]
    assert rich["sitemap_found"] is True


def test_heuristic_scales() -> None:
    thin = analyze_technical_audit_signals(url="http://example.com", issues_raw=[])
    rich = analyze_technical_audit_signals(
        url="https://acme.example.com",
        issues_raw=[{"type": "404", "severity": "critical", "detail": "Broken links", "fix": "Redirect"}],
    )
    assert rich["overall_score"] >= thin["overall_score"] or rich["https_secure"]
    assert thin["overall_score"] < 100
    assert isinstance(thin["issues"], list)


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"overall_score": 71, "categories": {"crawlability": {"score": 75}}}

    assert (
        await analyze_technical_audit(
            url="https://example.com",
            issues_raw=[],
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_technical_audit(
            url="https://example.com",
            issues_raw=[],
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
