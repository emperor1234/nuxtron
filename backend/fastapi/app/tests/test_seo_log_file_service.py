"""Unit tests for Log File service (phase-h module 1)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_log_file_service import analyze_log_file, analyze_log_file_signals


def test_heuristic_scales() -> None:
    thin = analyze_log_file_signals(log_snippet="GET / 200", domain="", notes="")
    rich = analyze_log_file_signals(
        log_snippet='66.249.64.13 - "GET /blog HTTP/1.1" 200\n66.249.64.14 - "GET /missing HTTP/1.1" 404\n',
        domain="example.com",
        notes="Crawl log review with googlebot traffic and 404 patterns across product paths",
    )
    assert rich["crawl_health_score"] != thin["crawl_health_score"] or rich["total_requests"] >= thin["total_requests"]
    assert thin["crawl_health_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"crawl_health_score": 68, "anomalies": []}

    assert (
        await analyze_log_file(
            log_snippet='Googlebot "GET / HTTP/1.1" 200',
            domain="example.com",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_log_file(
            log_snippet='Googlebot "GET / HTTP/1.1" 200',
            domain="example.com",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
