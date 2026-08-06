"""Unit tests for Site Migration SEO service (phase-d module 5)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_site_migration_service import analyze_site_migration, analyze_site_migration_signals


def test_heuristic_scales() -> None:
    thin = analyze_site_migration_signals(
        source_domain="old.example",
        target_domain="old.example",
        sample_urls=[],
        launch_window="",
        notes="",
    )
    rich = analyze_site_migration_signals(
        source_domain="legacy.example",
        target_domain="new.example",
        sample_urls=["/", "/pricing", "/blog", "/features"],
        launch_window="Q3 2026",
        notes="Redirect map reviewed",
    )
    assert rich["migration_readiness_score"] > thin["migration_readiness_score"]
    assert thin["migration_readiness_score"] < 100


@pytest.mark.asyncio
async def test_llm_and_heuristic() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {"migration_readiness_score": 68, "redirect_coverage_pct": 80}

    assert (
        await analyze_site_migration(
            source_domain="old.example",
            target_domain="new.example",
            sample_urls=["/"],
            launch_window="Q3",
            notes="",
            ollama_json_fn=_llm,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "llm"

    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    assert (
        await analyze_site_migration(
            source_domain="old.example",
            target_domain="new.example",
            sample_urls=[],
            launch_window="",
            notes="",
            ollama_json_fn=_down,
            system_prompt="s",
            clean_text_fn=lambda t, _m: t,
        )
    )["analysis_mode"] == "heuristic"
