"""Unit tests for Security SEO service (phase-g module 4)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_security_service import analyze_security_seo_signals, audit_security_seo


def test_heuristic_scales() -> None:
    thin = analyze_security_seo_signals(url="http://x.com", check_cloaking=False, notes="")
    rich = analyze_security_seo_signals(
        url="https://example.com",
        check_cloaking=True,
        notes="Security audit with HTTPS headers cloaking and redirect chain review notes",
    )
    assert rich["security_seo_score"] > thin["security_seo_score"]
    assert thin["security_seo_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"security_seo_score": 74, "issues": []}

    assert (
        await audit_security_seo(
            url="https://example.com",
            check_cloaking=True,
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await audit_security_seo(
            url="https://example.com",
            check_cloaking=True,
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
