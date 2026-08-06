"""Site Migration SEO Manager — phase-d module 5."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_site_migration_signals(
    *,
    source_domain: str,
    target_domain: str,
    sample_urls: list[str],
    launch_window: str,
    notes: str,
) -> dict[str, Any]:
    source = source_domain.strip()
    target = target_domain.strip()
    urls = [u.strip() for u in sample_urls if u.strip()] or ["/", "/pricing", "/blog"]
    window = launch_window.strip()
    notes_text = notes.strip()
    same_host = source.replace("https://", "").replace("http://", "").split("/")[0] == target.replace("https://", "").replace("http://", "").split("/")[0]

    migration_readiness_score = 40
    migration_readiness_score += min(18, len(urls) * 3)
    migration_readiness_score += 8 if window else 0
    migration_readiness_score += 6 if notes_text else 0
    migration_readiness_score -= 12 if same_host else 0
    migration_readiness_score = _clamp(migration_readiness_score)

    redirect_coverage_pct = _clamp(min(88, 40 + len(urls) * 6))

    def _map_path(path: str) -> str:
        if path.startswith("http"):
            return path.replace(source, target) if source in path else path
        return f"https://{target}{path if path.startswith('/') else '/' + path}"

    return {
        "migration_readiness_score": migration_readiness_score,
        "redirect_coverage_pct": redirect_coverage_pct,
        "critical_issues": [
            {
                "type": "redirect_gap",
                "severity": "high" if len(urls) < 3 else "medium",
                "detail": "Some legacy URLs may lack explicit 301 destinations",
                "fix": "Add one-to-one 301 mapping for top-traffic legacy URLs",
            }
        ],
        "url_mapping_preview": [
            {"legacy_url": f"https://{source}{p if p.startswith('/') else '/' + p}", "target_url": _map_path(p), "status": "mapped"}
            for p in urls[:6]
        ],
        "monitoring_plan": [
            "Track 404 and redirect chain rates daily for 21 days post-launch",
            "Compare branded query visibility by landing template",
            "Audit indexation deltas after each deploy",
        ],
        "recommended_tools": ["search_console", "screaming_frog", "bing_webmaster_tools"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_site_migration_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    for key in ("migration_readiness_score", "redirect_coverage_pct"):
        try:
            out[key] = _clamp(int(float(out.get(key, 50))))
        except (TypeError, ValueError):
            out[key] = 50
    for list_key in ("critical_issues", "url_mapping_preview", "monitoring_plan", "recommended_tools"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def analyze_site_migration(
    *,
    source_domain: str,
    target_domain: str,
    sample_urls: list[str],
    launch_window: str,
    notes: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    urls = sample_urls[:12] if sample_urls else ["/", "/pricing"]
    prompt = (
        f"Source: {clean_text_fn(source_domain, 300)}. Target: {clean_text_fn(target_domain, 300)}. "
        f"Sample URLs: {urls}. Launch: {clean_text_fn(launch_window, 120)}. Notes: {clean_text_fn(notes, 500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("migration_readiness_score") is not None or llm.get("url_mapping_preview"):
            return normalize_site_migration_result(llm, analysis_mode="llm", ai_available=True)
    heur = analyze_site_migration_signals(
        source_domain=source_domain, target_domain=target_domain, sample_urls=sample_urls,
        launch_window=launch_window, notes=notes,
    )
    return normalize_site_migration_result(heur, analysis_mode="heuristic", ai_available=False)
