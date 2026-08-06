"""Unit tests for SEO A/B Testing service (phase-b module 4)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.no_legacy

from backend.fastapi.app.seo_ab_testing_service import (
    analyze_seo_ab_testing,
    analyze_seo_ab_testing_signals,
    normalize_seo_ab_testing_result,
)


def test_heuristic_scales_with_variant_differentiation() -> None:
    thin = analyze_seo_ab_testing_signals(
        url="example.com",
        hypothesis="Test",
        primary_metric="conversion_rate",
        variant_a="Same copy",
        variant_b="Same copy",
        test_duration_days=7,
        notes="",
        feature_flag_provider="",
        experiment_platform="",
        ai_analyst_model="",
    )
    rich = analyze_seo_ab_testing_signals(
        url="https://example.com/pricing",
        hypothesis="Clearer hero and CTA will improve conversion from organic sessions",
        primary_metric="conversion_rate",
        variant_a="Current headline",
        variant_b="Intent-led headline with proof points and sign-up CTA above the fold",
        test_duration_days=28,
        notes="Guardrail metrics include bounce rate",
        feature_flag_provider="posthog",
        experiment_platform="posthog",
        ai_analyst_model="llama3",
    )
    assert rich["experiment_readiness_score"] > thin["experiment_readiness_score"]
    assert rich["analysis_mode"] == "heuristic"
    assert rich["experiment_readiness_score"] < 100


def test_no_fallback_key_in_normalize() -> None:
    out = normalize_seo_ab_testing_result(
        {"experiment_readiness_score": 130, "fallback": True, "test_design": {}},
        analysis_mode="llm",
        ai_available=True,
    )
    assert out["experiment_readiness_score"] == 100
    assert "fallback" not in out


@pytest.mark.asyncio
async def test_analyze_seo_ab_llm_path() -> None:
    async def _llm(_s: str, _u: str, **_k: object) -> dict:
        return {
            "experiment_readiness_score": 72,
            "test_design": {"traffic_split": "50/50", "sample_size_estimate": 7000},
        }

    result = await analyze_seo_ab_testing(
        url="https://example.com",
        hypothesis="CTA test",
        primary_metric="conversion_rate",
        variant_a="A",
        variant_b="B with CTA",
        test_duration_days=21,
        notes="",
        feature_flag_provider="posthog",
        experiment_platform="posthog",
        ai_analyst_model="llama3",
        variant_payloads=[],
        ollama_json_fn=_llm,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "llm"
    assert result["experiment_readiness_score"] == 72


@pytest.mark.asyncio
async def test_analyze_seo_ab_heuristic_when_llm_down() -> None:
    async def _down(_s: str, _u: str, **_k: object) -> dict:
        return {"fallback": True}

    result = await analyze_seo_ab_testing(
        url="https://example.com",
        hypothesis="Improve conversion",
        primary_metric="conversion_rate",
        variant_a="control",
        variant_b="variant",
        test_duration_days=14,
        notes="",
        feature_flag_provider="posthog",
        experiment_platform="posthog",
        ai_analyst_model="",
        variant_payloads=[],
        ollama_json_fn=_down,
        system_prompt="sys",
        clean_text_fn=lambda t, _m: t,
    )
    assert result["analysis_mode"] == "heuristic"
    assert result["experiment_readiness_score"] < 100
