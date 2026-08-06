"""
SEO A/B Testing Framework — phase-b module 4.

Designs experiment readiness, sample sizing, and guardrails from URL and variant inputs.
Uses LLM when available; no fake perfect scores in heuristic output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_CTA_RE = re.compile(r"\b(cta|click|sign up|buy|demo|trial|subscribe)\b", re.IGNORECASE)
_TITLE_RE = re.compile(r"\b(title|headline|h1|meta)\b", re.IGNORECASE)
_GUARDRAIL_RE = re.compile(r"\b(bounce|indexation|time on page|guardrail|seasonality)\b", re.IGNORECASE)
_BRACKET_RE = re.compile(r"\[[^\]]+\]")
_VAGUE_HYP_RE = re.compile(r"\b(maybe|might|could|possibly)\b", re.IGNORECASE)

_DEFAULT_GUARDRAILS = ["bounce_rate", "avg_time_on_page", "indexation_rate"]


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _token_set(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"\b\w{3,}\b", text)}


def _variant_differentiation(variant_a: str, variant_b: str) -> float:
    a = _token_set(variant_a)
    b = _token_set(variant_b)
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return 1.0 - (len(a & b) / len(union))


def _estimate_sample_size(*, duration_days: int, metric: str, diff_score: float) -> int:
    base = 4200
    if "conversion" in metric.lower():
        base = 6800
    elif "click" in metric.lower() or "ctr" in metric.lower():
        base = 5200
    elif "rank" in metric.lower() or "position" in metric.lower():
        base = 9000
    duration_factor = min(1.4, duration_days / 21)
    diff_factor = max(0.85, 1.15 - diff_score)
    return int(round(base * duration_factor * diff_factor))


def analyze_seo_ab_testing_signals(
    *,
    url: str,
    hypothesis: str,
    primary_metric: str,
    variant_a: str,
    variant_b: str,
    test_duration_days: int,
    notes: str,
    feature_flag_provider: str,
    experiment_platform: str,
    ai_analyst_model: str,
    variant_payloads: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Deterministic SEO A/B experiment design."""
    page_url = url.strip()
    hyp = hypothesis.strip()
    metric = primary_metric.strip() or "conversion_rate"
    a_text = variant_a.strip()
    b_text = variant_b.strip()
    notes_text = notes.strip()
    duration = max(7, min(90, test_duration_days))

    parsed = urlparse(page_url if "://" in page_url else f"https://{page_url}") if page_url else None
    https_ok = bool(parsed and parsed.scheme == "https")

    hyp_words = len(re.findall(r"\b\w+\b", hyp))
    diff_score = _variant_differentiation(a_text, b_text)
    cta_in_b = bool(_CTA_RE.search(b_text))
    title_change = bool(_TITLE_RE.search(hyp + " " + a_text + " " + b_text))
    guardrail_notes = bool(_GUARDRAIL_RE.search(notes_text))
    vague_hits = len(_VAGUE_HYP_RE.findall(hyp))
    bracket_count = len(_BRACKET_RE.findall(hyp + notes_text))
    payload_count = len(variant_payloads or [])

    experiment_readiness_score = 36
    experiment_readiness_score += min(18, hyp_words)
    experiment_readiness_score += min(14, int(diff_score * 20))
    experiment_readiness_score += 8 if https_ok else 0
    experiment_readiness_score += 6 if cta_in_b else 0
    experiment_readiness_score += 6 if guardrail_notes else 0
    experiment_readiness_score += 4 if feature_flag_provider.strip() else 0
    experiment_readiness_score += 4 if experiment_platform.strip() else 0
    experiment_readiness_score -= min(12, vague_hits * 4)
    experiment_readiness_score -= min(10, bracket_count * 4)
    experiment_readiness_score = _clamp(experiment_readiness_score)

    sample_size = _estimate_sample_size(duration_days=duration, metric=metric, diff_score=diff_score)
    guardrails = list(_DEFAULT_GUARDRAILS)
    if guardrail_notes and "bounce" in notes_text.lower():
        guardrails.append("scroll_depth")

    lift_b = _clamp(int(round(4 + diff_score * 12 + (3 if cta_in_b else 0))))
    lift_a = _clamp(max(1, lift_b - 5))

    variant_recommendations = [
        {
            "variant": "B",
            "expected_lift_pct": lift_b,
            "rationale": "Treatment variant shows stronger differentiation and clearer action cues"
            if diff_score >= 0.35
            else "Moderate differentiation — validate messaging with qualitative checks before launch",
        },
        {
            "variant": "A",
            "expected_lift_pct": lift_a,
            "rationale": "Control variant is lower risk for SEO stability but offers limited upside",
        },
    ]

    measurement_plan = [
        f"Track `{metric}` daily with weekday seasonality normalization",
        f"Run for at least {duration} days before final significance read",
        "Freeze unrelated on-page and template changes during the experiment window",
    ]
    if experiment_platform:
        measurement_plan.append(f"Configure experiment in {experiment_platform} with 50/50 assignment and exposure logging")
    if ai_analyst_model.strip():
        measurement_plan.append(f"Use {ai_analyst_model.strip()} for weekly narrative summaries of metric deltas")

    risk_flags: list[str] = []
    if title_change:
        risk_flags.append("Title or meta changes may introduce SERP volatility — monitor impressions and CTR")
    if diff_score < 0.25:
        risk_flags.append("Variants may be too similar to detect meaningful lift at planned sample size")
    if duration < 14:
        risk_flags.append("Short test window increases false-positive risk for SEO metrics")
    if not https_ok and page_url:
        risk_flags.append("Non-HTTPS URL in inputs — ensure canonical secure URLs in experiment bucketing")
    if payload_count == 0:
        risk_flags.append("No structured variant payloads supplied — document variant IDs in feature flags")

    return {
        "experiment_readiness_score": experiment_readiness_score,
        "test_design": {
            "traffic_split": "50/50",
            "sample_size_estimate": sample_size,
            "guardrail_metrics": guardrails[:6],
            "duration_days": duration,
            "primary_metric": metric,
        },
        "variant_recommendations": variant_recommendations,
        "measurement_plan": measurement_plan,
        "risk_flags": risk_flags[:6],
        "analysis_mode": "heuristic",
        "ai_available": False,
        "content_signals": {
            "variant_differentiation": round(diff_score, 2),
            "hypothesis_word_count": hyp_words,
            "variant_payload_count": payload_count,
        },
    }


def normalize_seo_ab_testing_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}

    try:
        out["experiment_readiness_score"] = _clamp(int(float(out.get("experiment_readiness_score", 50))))
    except (TypeError, ValueError):
        out["experiment_readiness_score"] = 50

    if not isinstance(out.get("test_design"), dict):
        out["test_design"] = {
            "traffic_split": "50/50",
            "sample_size_estimate": 5000,
            "guardrail_metrics": list(_DEFAULT_GUARDRAILS),
        }
    else:
        design = out["test_design"]
        if not design.get("traffic_split"):
            design["traffic_split"] = "50/50"
        try:
            design["sample_size_estimate"] = max(500, int(float(design.get("sample_size_estimate", 5000))))
        except (TypeError, ValueError):
            design["sample_size_estimate"] = 5000
        if not isinstance(design.get("guardrail_metrics"), list):
            design["guardrail_metrics"] = list(_DEFAULT_GUARDRAILS)

    for list_key in ("variant_recommendations", "measurement_plan", "risk_flags"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []

    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_seo_ab_testing(
    *,
    url: str,
    hypothesis: str,
    primary_metric: str,
    variant_a: str,
    variant_b: str,
    test_duration_days: int,
    notes: str,
    feature_flag_provider: str,
    experiment_platform: str,
    ai_analyst_model: str,
    variant_payloads: list[dict[str, Any]] | None = None,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    """Run SEO A/B testing analysis."""
    prompt = (
        f"URL: {clean_text_fn(url, 500)}. Hypothesis: {clean_text_fn(hypothesis, 500)}. "
        f"Primary metric: {clean_text_fn(primary_metric, 120)}. "
        f"Variant A: {clean_text_fn(variant_a, 1200)}. Variant B: {clean_text_fn(variant_b, 1200)}. "
        f"Duration days: {test_duration_days}. Notes: {clean_text_fn(notes, 500)}. "
        f"Feature flags: {clean_text_fn(feature_flag_provider, 120)}. "
        f"Experiment platform: {clean_text_fn(experiment_platform, 120)}. "
        f"AI analyst model: {clean_text_fn(ai_analyst_model, 100)}. "
        f"Variant payloads: {(variant_payloads or [])[:5]}. "
        "Return test readiness, experiment design, expected lift by variant, and risk controls. "
        "Do not use bracket placeholders."
    )

    llm_result = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm_result, dict) and not llm_result.get("fallback") and not llm_result.get("error"):
        if llm_result.get("experiment_readiness_score") is not None or llm_result.get("test_design"):
            return normalize_seo_ab_testing_result(llm_result, analysis_mode="llm", ai_available=True)

    heuristic = analyze_seo_ab_testing_signals(
        url=url,
        hypothesis=hypothesis,
        primary_metric=primary_metric,
        variant_a=variant_a,
        variant_b=variant_b,
        test_duration_days=test_duration_days,
        notes=notes,
        feature_flag_provider=feature_flag_provider,
        experiment_platform=experiment_platform,
        ai_analyst_model=ai_analyst_model,
        variant_payloads=variant_payloads,
    )
    return normalize_seo_ab_testing_result(heuristic, analysis_mode="heuristic", ai_available=False)
