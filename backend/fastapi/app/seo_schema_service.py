"""AI Schema Engine — phase-f module 1."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def analyze_schema_signals(*, schema_type: str, content: str, url: str) -> dict[str, Any]:
    stype = schema_type.strip() or "Article"
    text = content.strip()
    page_url = url.strip() or "https://example.com"
    words = len(re.findall(r"\b\w+\b", text))
    title_match = re.search(r"^#\s*(.+)$", text, re.MULTILINE)
    name = title_match.group(1).strip() if title_match else text[:80].strip() or stype

    schema_score = 36
    schema_score += min(18, words // 20)
    schema_score += 8 if page_url.startswith("http") else 0
    schema_score += 6 if stype in {"Product", "LocalBusiness", "FAQPage"} else 4
    schema_score = _clamp(schema_score)

    schema_json: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": stype,
        "name": name,
        "description": text[:240] or f"Structured data for {stype}",
        "url": page_url,
    }
    if stype == "FAQPage":
        schema_json["mainEntity"] = [{"@type": "Question", "name": "Overview", "acceptedAnswer": {"@type": "Answer", "text": text[:400]}}]
    elif stype == "Product":
        schema_json["offers"] = {"@type": "Offer", "availability": "https://schema.org/InStock"}

    validation_issues = []
    if words < 40:
        validation_issues.append({"property": "description", "message": "Content is thin for rich results", "severity": "warning"})
    if not page_url.startswith("http"):
        validation_issues.append({"property": "url", "message": "Absolute URL recommended", "severity": "warning"})

    json_ld = json.dumps(schema_json, indent=2)
    validation_score = _clamp(schema_score - len(validation_issues) * 4)
    missing_recommended = ["image"] if stype in {"Article", "Product"} else []

    return {
        "schema_score": schema_score,
        "schema_json": schema_json,
        "schema_type": stype,
        "validation": {"valid": validation_score >= 55, "warnings": [i["message"] for i in validation_issues]},
        "json_ld": json_ld,
        "validation_score": validation_score,
        "is_valid": validation_score >= 55,
        "validation_issues": validation_issues,
        "rich_result_types": [stype] if validation_score >= 60 else [],
        "properties_used": list(schema_json.keys()),
        "missing_recommended": missing_recommended,
        "google_preview_hints": ["Add primary image URL", "Ensure canonical URL matches schema url"],
        "analysis_mode": "heuristic",
        "ai_available": False,
    }


def normalize_schema_result(raw: dict[str, Any], *, analysis_mode: str, ai_available: bool) -> dict[str, Any]:
    out = {k: v for k, v in raw.items() if k not in ("fallback", "error")}
    try:
        out["schema_score"] = _clamp(int(float(out.get("schema_score", out.get("validation_score", 50)))))
    except (TypeError, ValueError):
        out["schema_score"] = 50
    if "validation_score" not in out:
        out["validation_score"] = out["schema_score"]
    else:
        try:
            out["validation_score"] = _clamp(int(float(out["validation_score"])))
        except (TypeError, ValueError):
            out["validation_score"] = out["schema_score"]
    if isinstance(out.get("schema_json"), dict) and not out.get("json_ld"):
        out["json_ld"] = json.dumps(out["schema_json"], indent=2)
    if "is_valid" not in out:
        out["is_valid"] = out["validation_score"] >= 55
    for list_key in ("validation_issues", "rich_result_types", "properties_used", "missing_recommended", "google_preview_hints"):
        if not isinstance(out.get(list_key), list):
            out[list_key] = []
    if not isinstance(out.get("validation"), dict):
        out["validation"] = {"valid": bool(out.get("is_valid")), "warnings": []}
    out["analysis_mode"] = analysis_mode
    out["ai_available"] = ai_available
    return out


async def generate_schema_markup(
    *,
    schema_type: str,
    content: str,
    url: str,
    ollama_json_fn: Callable[..., Awaitable[dict[str, Any]]],
    system_prompt: str,
    clean_text_fn: Callable[[str, int], str],
) -> dict[str, Any]:
    prompt = (
        f"Generate Schema.org JSON-LD for type: {clean_text_fn(schema_type, 80)}. "
        f"URL: {clean_text_fn(url, 300)}. Content: {clean_text_fn(content, 1500)}."
    )
    llm = await ollama_json_fn(system_prompt, prompt)
    if isinstance(llm, dict) and not llm.get("fallback") and not llm.get("error"):
        if llm.get("schema_json") or llm.get("schema_score") is not None:
            out = normalize_schema_result(llm, analysis_mode="llm", ai_available=True)
            if isinstance(out.get("schema_json"), dict) and not out.get("json_ld"):
                out["json_ld"] = json.dumps(out["schema_json"], indent=2)
            return out
    heur = analyze_schema_signals(schema_type=schema_type, content=content, url=url)
    return normalize_schema_result(heur, analysis_mode="heuristic", ai_available=False)
