"""Social Workspace workspace parse longform variants service."""

from .ai_policy import _sw_ai_output_guard
from .ai_policy import _sw_ai_safety_bundle
from .workspace import _sw_http_error
from .workspace_buffer_compute_comment_score import _sw_build_longform_fallback_variants
from .workspace_buffer_compute_comment_score import _sw_request_longform_variants
from typing import Any
import os
import re


def _sw_parse_longform_variants(generated_text: str) -> list[str]:
    variants: list[str] = []
    for raw_line in generated_text.splitlines():
        cleaned = re.sub("^\\s*(?:\\d+[\\).:-]\\s*|[-*]\\s*)", "", raw_line).strip()
        if cleaned and cleaned not in variants:
            variants.append(cleaned)
    if variants:
        return variants
    stripped = generated_text.strip()
    return [stripped] if stripped else []


def _sw_pad_longform_variants(
    variants: list[str], source_text: str, title_label: str, platform_label: str, variant_count: int
) -> list[str]:
    if len(variants) >= variant_count:
        return variants[:variant_count]
    compact_source = re.sub("\\s+", " ", source_text.strip())
    intro = compact_source[:140] or title_label
    padded = variants[:]
    while len(padded) < variant_count:
        idx = len(padded) + 1
        padded.append(f"{title_label} variant {idx} for {platform_label}: {intro}")
    return padded[:variant_count]


def _sw_generate_longform_variants(
    source_text: str, source_title: str, target_platform: str, tone: str, variant_count: int
) -> tuple[list[str], str, str, dict[str, Any]]:
    platform_label = target_platform.strip() or "LinkedIn"
    tone_label = tone.strip() or "professional"
    title_label = source_title.strip() or "Longform asset"
    safety = _sw_ai_safety_bundle("longform_repurpose", "repurpose", source_text)
    if safety["blocked"]:
        raise _sw_http_error(status_code=422, detail="Longform repurpose request blocked by LLM Guard/NeMo Guardrails.")
    prompt = f"Repurpose this longform asset into {variant_count} distinct social posts for {platform_label}. Use a {tone_label} tone. Keep each variant concise, distinct, and ready to publish. Return each variant on its own line, numbered 1 to {variant_count}.\n\nTitle: {title_label}\n\nAsset:\n{source_text.strip()}"
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    generated_text = _sw_request_longform_variants(openai_key, prompt) if openai_key else ""
    if not generated_text.strip():
        variants = _sw_build_longform_fallback_variants(source_text, title_label, platform_label, variant_count)
        output_safety = _sw_ai_output_guard("longform_repurpose", "\n".join(variants), safety)
        if output_safety["blocked"]:
            raise _sw_http_error(status_code=502, detail="Longform repurpose fallback output blocked by LLM Guard.")
        return (variants, prompt, "fallback", {**safety, "output_safety": output_safety, "provider": "fallback"})
    parsed_variants = _sw_parse_longform_variants(generated_text)
    variants = _sw_pad_longform_variants(parsed_variants, source_text, title_label, platform_label, variant_count)
    output_safety = _sw_ai_output_guard("longform_repurpose", "\n".join(variants), safety)
    if output_safety["blocked"]:
        raise _sw_http_error(status_code=502, detail="Longform repurpose output blocked by LLM Guard.")
    return (variants, prompt, "openai", {**safety, "output_safety": output_safety, "provider": "openai"})
