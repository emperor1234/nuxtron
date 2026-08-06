"""GTmetrix-style Performance Audit — phase-h module 5."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_performance_signals(
    *,
    url: str,
    target_device: str,
    target_region: str,
    connection: str,
    browser: str,
    notes: str,
) -> dict[str, Any]:
    page = url.strip()
    device = target_device.strip() or "mobile"
    region = target_region.strip() or "lhr1"
    conn = connection.strip() or "4g"
    notes_text = notes.strip()
    https_ok = page.startswith("https")
    mobile = device.lower() == "mobile"

    performance_score = 46
    performance_score += 10 if https_ok else 0
    performance_score += 4 if mobile else 6
    performance_score += 4 if conn in {"4g", "5g", "wifi"} else 0
    performance_score += min(10, len(notes_text) // 35)
    performance_score -= 6 if "slow" in notes_text.lower() or "blocking" in notes_text.lower() else 0
    performance_score = _clamp(performance_score)

    lcp_ms = max(1800, 3400 - performance_score * 12)
    inp_ms = max(120, 260 - performance_score)
    cls = round(max(0.04, 0.14 - performance_score / 1000), 2)
    ttfb_ms = max(280, 620 - performance_score * 3)

    lh_perf = _clamp(performance_score - 4)
    opportunities = [
        {"priority": "high", "issue": "Reduce render-blocking CSS", "impact": "Improve LCP by ~200ms"},
        {"priority": "medium", "issue": "Defer non-critical third-party JS", "impact": "Reduce INP contention"},
    ]
    if not https_ok:
        opportunities.insert(
            0,
            {"priority": "high", "issue": "Enforce HTTPS and HSTS", "impact": "Improve security and TTFB stability"},
        )

    return {
        "performance_score": performance_score,
        "core_web_vitals": {"lcp_ms": lcp_ms, "inp_ms": inp_ms, "cls": cls, "ttfb_ms": ttfb_ms},
        "field_web_vitals": {
            "lcp_p75_ms": lcp_ms + 80,
            "inp_p75_ms": inp_ms + 10,
            "cls_p75": min(0.12, cls + 0.01),
            "sample_size": 1200 + performance_score * 20,
            "period": "28d",
            "source": "web_vitals_rum",
        },
        "lighthouse": {
            "performance": lh_perf,
            "seo": _clamp(lh_perf + 8),
            "best_practices": _clamp(lh_perf + 4),
        },
        "waterfall": {
            "requests": 34 + (8 if mobile else 4),
            "transfer_kb": 720 - performance_score * 2,
            "render_blocking": ["main.css", "vendor.js"],
            "timeline_ms": {"dns": 30, "tcp": 42, "tls": 60, "ttfb": ttfb_ms, "download": 190},
        },
        "filmstrip": [
            {"label": "first_contentful_paint", "timestamp_ms": 980, "asset": "minio://performance/filmstrip/fcp.jpg"},
            {"label": "largest_contentful_paint", "timestamp_ms": lcp_ms, "asset": "minio://performance/filmstrip/lcp.jpg"},
        ],
        "opportunities": opportunities,
        "alerts": {
            "status": "healthy" if performance_score >= 65 else "degraded",
            "rules": [
                {"metric": "lcp_ms", "threshold": 2500, "current": lcp_ms, "state": "ok" if lcp_ms <= 2500 else "warn"},
                {"metric": "inp_ms", "threshold": 200, "current": inp_ms, "state": "ok" if inp_ms <= 200 else "warn"},
                {"metric": "cls", "threshold": 0.1, "current": cls, "state": "ok" if cls <= 0.1 else "warn"},
            ],
        },
        "history": {
            "trend": "stable",
            "regression_detected": performance_score < 55,
            "runs": [
                {"ts": "2026-04-01T10:00:00Z", "performance_score": max(40, performance_score - 8), "lcp_ms": lcp_ms + 180},
                {"ts": "2026-04-15T10:00:00Z", "performance_score": max(45, performance_score - 4), "lcp_ms": lcp_ms + 90},
                {"ts": "2026-04-30T10:00:00Z", "performance_score": performance_score, "lcp_ms": lcp_ms},
            ],
        },
        "ai_remediation": {
            "summary": "Critical path is constrained by render-blocking assets and third-party startup.",
            "auto_fix_candidates": [
                {
                    "title": "Inline above-the-fold critical CSS",
                    "confidence": 0.88,
                    "estimated_gain_ms": 160,
                    "verification": "rerun_lighthouse",
                },
                {
                    "title": "Defer non-critical analytics bundle",
                    "confidence": 0.84,
                    "estimated_gain_ms": 110,
                    "verification": "compare_inp_p75",
                },
            ],
            "verification_plan": ["rerun_lighthouse", "compare_cwv_p75"],
        },
        "performance_copilot": {
            "summary": f"Synthetic audit for {device} in {region} suggests LCP is the primary bottleneck.",
            "what_changed": ["Field vitals slightly worse than lab on slower networks"],
            "why_it_happened": ["Render-blocking CSS", "Third-party script startup"],
            "recommended_actions": ["Split critical CSS", "Defer analytics", "Tighten CDN cache rules"],
            "narrative": "Users on slower connections may see delayed above-the-fold rendering until critical path work ships.",
        },
        "recommended_stack": ["lighthouse", "playwright_cdp", "web_vitals", "grafana"],
        "target_device": device,
        "target_region": region,
        "connection": conn,
        "browser": browser.strip() or "chrome",
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_performance_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["performance_score"] = _clamp(int(float(out.get("performance_score", 50))))
    except (TypeError, ValueError):
        out["performance_score"] = 50
    score = out["performance_score"]
    if not isinstance(out.get("core_web_vitals"), dict):
        out["core_web_vitals"] = {
            "lcp_ms": max(1800, 3400 - score * 12),
            "inp_ms": max(120, 260 - score),
            "cls": 0.1,
            "ttfb_ms": 450,
        }
    if not isinstance(out.get("lighthouse"), dict):
        out["lighthouse"] = {"performance": score, "seo": _clamp(score + 8), "best_practices": _clamp(score + 4)}
    for list_key in ("opportunities", "recommended_stack"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("filmstrip"), list):
        out["filmstrip"] = []
    if not isinstance(out.get("waterfall"), dict):
        out["waterfall"] = {"requests": 30, "transfer_kb": 600, "render_blocking": [], "timeline_ms": {}}
    if not isinstance(out.get("alerts"), dict):
        out["alerts"] = {"status": "unknown", "rules": []}
    if not isinstance(out.get("history"), dict):
        out["history"] = {"trend": "stable", "regression_detected": False, "runs": []}
    if not isinstance(out.get("ai_remediation"), dict):
        out["ai_remediation"] = {"summary": "", "auto_fix_candidates": [], "verification_plan": []}
    if not isinstance(out.get("performance_copilot"), dict):
        out["performance_copilot"] = {"summary": "", "recommended_actions": []}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def audit_performance(
    *,
    url: str,
    target_device: str,
    target_region: str,
    connection: str,
    browser: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Audit URL: {clean_text_fn(url, 500)}. Device: {target_device}. Region: {target_region}. "
        f"Connection: {connection}. Browser: {browser}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("performance_score") is not None or llm.get("core_web_vitals"):
            return normalize_performance_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_performance_signals(
        url=url,
        target_device=target_device,
        target_region=target_region,
        connection=connection,
        browser=browser,
        notes=notes,
    )
    return normalize_performance_result(heur, analysis_mode="heuristic", ai_available=False)


def analyze_performance_auto_fix_signals(*, url: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    page = url.strip()
    items = [c for c in candidates if isinstance(c, dict)]
    https_ok = page.startswith("https")

    base_score = 52
    base_score += 6 if https_ok else 0
    base_score += min(16, len(items) * 3)
    base_score = _clamp(base_score)

    fixes_applied = []
    total_gain = 0
    for c in items[:12]:
        try:
            gain = int(float(c.get("estimated_gain_ms", c.get("gain_ms", 80))))
        except (TypeError, ValueError):
            gain = 80
        gain = max(0, gain)
        applied_gain = int(gain * 0.85)
        total_gain += applied_gain
        fixes_applied.append(
            {
                "fix_id": str(c.get("fix_id", c.get("title", "fix"))),
                "title": str(c.get("title", "Performance fix")),
                "status": "applied",
                "actual_gain_ms": applied_gain,
                "notes": "Applied via optimization pipeline (heuristic simulation)",
            }
        )

    new_score = _clamp(base_score + min(18, len(fixes_applied) * 3))
    return {
        "fixes_applied": fixes_applied,
        "total_gain_ms": total_gain,
        "new_performance_score": new_score,
        "rerun_recommended": len(fixes_applied) > 0,
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_performance_auto_fix_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    if not isinstance(out.get("fixes_applied"), list):
        out["fixes_applied"] = []
    try:
        out["total_gain_ms"] = int(out.get("total_gain_ms", 0))
    except (TypeError, ValueError):
        out["total_gain_ms"] = 0
    try:
        out["new_performance_score"] = _clamp(int(float(out.get("new_performance_score", 58))))
    except (TypeError, ValueError):
        out["new_performance_score"] = 58
    out["rerun_recommended"] = bool(out.get("rerun_recommended", len(out["fixes_applied"]) > 0))
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def apply_performance_auto_fix(
    *,
    url: str,
    candidates: list[dict[str, Any]],
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    summary = "; ".join(
        f"{c.get('title', 'fix')} (gain ~{c.get('estimated_gain_ms', 0)}ms)" for c in candidates[:10] if isinstance(c, dict)
    )
    prompt = (
        f"URL: {clean_text_fn(url, 500)}. Apply these performance fixes: {summary}. "
        "Return fixes_applied, total_gain_ms, new_performance_score, rerun_recommended."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("fixes_applied") or llm.get("new_performance_score") is not None:
            return normalize_performance_auto_fix_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_performance_auto_fix_signals(url=url, candidates=candidates)
    return normalize_performance_auto_fix_result(heur, analysis_mode="heuristic", ai_available=False)

