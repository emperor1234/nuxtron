"""Social Workspace ai policy service."""

from ..constants import JSON_CONTENT_TYPE
from ..constants import OPENAI_CHAT_COMPLETIONS_URL
from ..constants import _SW_AI_ALLOWED_ACTIONS
from ..constants import _SW_AI_DEFAULT_POLICY
from ..constants import _SW_AI_LOGGER
from .website import _sw_strip_html
from .workspace import _sw_http_error
from typing import Any
from typing import cast
import httpx
from fastapi import HTTPException
import json
import os
import re


def _sw_load_ai_policy() -> dict[str, Any]:
    policy = dict(_SW_AI_DEFAULT_POLICY)
    raw_policy = os.getenv("SOCIAL_AI_POLICY_JSON", "").strip()
    policy_path = os.getenv("SOCIAL_AI_POLICY_PATH", "").strip()
    candidate: dict[str, Any] | None = None
    if raw_policy:
        try:
            loaded = json.loads(raw_policy)
            if isinstance(loaded, dict):
                candidate = loaded
        except json.JSONDecodeError:
            candidate = None
    elif policy_path:
        try:
            with open(policy_path, encoding="utf-8") as policy_file:
                loaded = json.load(policy_file)
            if isinstance(loaded, dict):
                candidate = loaded
        except (OSError, json.JSONDecodeError):
            candidate = None
    if candidate:
        policy.update(candidate)
        if "allow_actions" in candidate and isinstance(candidate["allow_actions"], list):
            policy["allow_actions"] = [
                str(item).strip().lower() for item in candidate["allow_actions"] if str(item).strip()
            ]
    return policy


def _sw_ai_signal_flags(text: str) -> list[str]:
    lowered = text.lower()
    signals: list[str] = []
    pattern_map = {
        "prompt_injection": [
            "(?i)\\b(ignore|disregard|bypass|override)\\b.{0,40}\\b(instruction|prompt|policy|system|guardrail|safety)\\b",
            "(?i)\\b(reveal|expose|show)\\b.{0,40}\\b(system prompt|secret|api key|token)\\b",
            "(?i)\\bdeveloper message\\b",
        ],
        "pii": [
            "\\b[\\w.+-]+@[\\w.-]+\\.[A-Za-z]{2,}\\b",
            "\\b\\+?\\d[\\d\\s().-]{7,}\\d\\b",
            "\\b\\d{3}-\\d{2}-\\d{4}\\b",
        ],
        "toxicity": ["(?i)\\b(idiot|stupid|moron|trash|dumb|hate you|kill yourself)\\b"],
    }
    for label, patterns in pattern_map.items():
        if any((re.search(pattern, lowered) for pattern in patterns)):
            signals.append(label)
    return signals


def _sw_llm_guard(stage: str, text: str, policy: dict[str, Any]) -> dict[str, Any]:
    sanitized = _sw_strip_html(text) if policy.get("redact_html", True) else text.strip()
    signals = _sw_ai_signal_flags(sanitized)
    blocked = bool(signals) and (
        policy.get("block_prompt_injection", True)
        and "prompt_injection" in signals
        or (policy.get("block_pii", True) and "pii" in signals)
        or (policy.get("block_toxicity", True) and "toxicity" in signals)
    )
    return {
        "stage": stage,
        "allowed": not blocked,
        "blocked": blocked,
        "signals": signals,
        "sanitized_text": sanitized,
        "policy_version": "social-ai-policy-v1",
    }


def _sw_nemo_guardrails(action: str, request_text: str, policy: dict[str, Any]) -> dict[str, Any]:
    normalized_action = action.strip().lower()
    allowed_actions = (
        set((str(item).strip().lower() for item in policy.get("allow_actions", []) if str(item).strip()))
        or _SW_AI_ALLOWED_ACTIONS
    )
    action_allowed = normalized_action in allowed_actions
    has_structure_hint = bool(re.search("(?i)\\b(json|schema|structured output|strict output)\\b", request_text))
    return {
        "allowed": action_allowed,
        "blocked": not action_allowed,
        "action": normalized_action,
        "structure_hint": has_structure_hint,
        "tool_restrictions": ["llm_text_only"],
        "rules": [
            "allow_listed_actions_only",
            "output_must_remain_text_only",
            "structured_outputs_available_via_schema",
        ],
    }


def _sw_ai_safety_bundle(
    feature_name: str, action: str, user_text: str, *, request_id: str | None = None
) -> dict[str, Any]:
    policy = _sw_load_ai_policy()
    llm_guard = _sw_llm_guard("input", user_text, policy)
    nemo_guardrails = _sw_nemo_guardrails(action, user_text, policy)
    safety = {
        "feature": feature_name,
        "request_id": request_id,
        "policy": policy,
        "llm_guard": llm_guard,
        "nemo_guardrails": nemo_guardrails,
        "blocked": not llm_guard["allowed"] or not nemo_guardrails["allowed"],
    }
    _SW_AI_LOGGER.info(
        json.dumps(
            {
                "event": "social_ai_safety_check",
                "feature": feature_name,
                "request_id": request_id,
                "llm_guard_allowed": llm_guard["allowed"],
                "llm_guard_signals": llm_guard["signals"],
                "nemo_guardrails_allowed": nemo_guardrails["allowed"],
                "action": nemo_guardrails["action"],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return safety


def _sw_ai_output_guard(feature_name: str, output_text: str, safety: dict[str, Any]) -> dict[str, Any]:
    policy = cast(dict[str, Any], safety.get("policy") or _sw_load_ai_policy())
    llm_guard = _sw_llm_guard("output", output_text, policy)
    nemo_guardrails = cast(dict[str, Any], safety.get("nemo_guardrails") or {})
    output_safety = {
        "feature": feature_name,
        "llm_guard": llm_guard,
        "nemo_guardrails": nemo_guardrails,
        "blocked": bool(llm_guard["blocked"]) or bool(nemo_guardrails.get("blocked")),
    }
    _SW_AI_LOGGER.info(
        json.dumps(
            {
                "event": "social_ai_output_check",
                "feature": feature_name,
                "llm_guard_allowed": llm_guard["allowed"],
                "llm_guard_signals": llm_guard["signals"],
                "nemo_guardrails_allowed": nemo_guardrails.get("allowed", True),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return output_safety


def _sw_ai_agent_templates() -> list[dict[str, Any]]:
    return [
        {
            "key": "social_poster",
            "name": "Social Poster",
            "description": "Generates and queues multi-channel posts from schedule, RSS, or product triggers.",
            "trigger_types": ["scheduled", "rss_new_item", "ecommerce_new_product"],
            "action": "create_and_queue_post",
            "vendors": ["OpenAI-compatible LLM", "RSS feed provider", "Shopify", "WooCommerce"],
        },
        {
            "key": "dm_chatbot",
            "name": "DM Chatbot",
            "description": "Auto-responds in DMs using inbox context, saved replies, and brand profile.",
            "trigger_types": ["new_dm", "mention_requires_reply"],
            "action": "respond_to_inbox_message",
            "vendors": ["OpenAI-compatible LLM", "Instagram Graph API", "Facebook Graph API", "X API"],
        },
        {
            "key": "comment_to_dm",
            "name": "Comment-to-DM",
            "description": "Detects offer keywords in comments and sends conversion-focused direct messages.",
            "trigger_types": ["keyword_comment_match"],
            "action": "send_direct_message_and_track_conversion",
            "vendors": ["Meta Graph API", "Bitly", "UTM analytics stack"],
        },
    ]


def _ai_assistant_fallback(action: str, text: str, platform: str) -> str:
    """Deterministic fallback when OpenAI key is not configured."""
    if action == "shorten":
        return text[:150] + ("…" if len(text) > 150 else "")
    if action == "expand":
        return f"{text}\n\n💡 [Expanded with more context for {platform or 'your audience'}. Set OPENAI_API_KEY for AI-powered expansion.]"
    if action == "casual":
        return text.replace("utilise", "use").replace("therefore", "so").replace("subsequently", "then") + " 😊"
    if action == "formal":
        return text.replace(" 😊", "").replace(" 🔥", "").replace(" 👋", "").strip() + "."
    if action == "repurpose":
        return f"[Repurposed for {platform or 'LinkedIn'}]: {text[:200]}..."
    if action == "generate":
        return f"1. {text}\n2. {text[:100]}... — join the conversation!\n3. Have you thought about {text[:80]}?"
    return text


def _sw_run_ai_assistant_text(action: str, text: str, platform: str, tone: str) -> tuple[str, dict[str, Any]]:
    safety = _sw_ai_safety_bundle("ai_assistant", action, text)
    if safety["blocked"]:
        raise _sw_http_error(status_code=422, detail="AI assistant request blocked by LLM Guard/NeMo Guardrails.")
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    sanitized_text = cast(str, safety["llm_guard"]["sanitized_text"])
    if openai_key:
        prompt_map = {
            "rephrase": f"Rephrase this social media post while keeping the same meaning. Tone: {tone}.\n\nPost: {sanitized_text}",
            "shorten": f"Shorten this social media post to under 150 characters while keeping the key message.\n\nPost: {sanitized_text}",
            "expand": f"Expand this social media post with more detail and engagement. Target platform: {platform or 'general'}.\n\nPost: {sanitized_text}",
            "casual": f"Rewrite this post in a casual, friendly tone.\n\nPost: {sanitized_text}",
            "formal": f"Rewrite this post in a formal, professional tone.\n\nPost: {sanitized_text}",
            "generate": f"Generate 3 engaging social media post variations about: {sanitized_text}. Platform: {platform or 'general'}. Tone: {tone}.",
            "repurpose": f"Repurpose this post for {platform or 'LinkedIn'}. Keep the core message but adapt format and length.\n\nOriginal: {sanitized_text}",
        }
        sys_prompt = "You are a social media expert assistant. Output only the post content, no explanation."
        user_prompt = prompt_map.get(action, f"Improve this social media post: {sanitized_text}")
        try:
            resp = httpx.post(
                (os.getenv("OPENAI_BASE_URL", "").strip().rstrip("/") + "/chat/completions")
                if os.getenv("OPENAI_BASE_URL", "").strip()
                else OPENAI_CHAT_COMPLETIONS_URL,
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": JSON_CONTENT_TYPE},
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
                timeout=15.0,
            )
            if not resp.is_success:
                # A rejected key or an outage must not come back as "your text, rewritten".
                raise _sw_http_error(status_code=503, detail="The AI writing assistant is not available right now (the provider rejected the request).")
            candidate = str(resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
            if not candidate:
                raise _sw_http_error(status_code=503, detail="The AI provider returned no text.")
            output_safety = _sw_ai_output_guard("ai_assistant", candidate, safety)
            if output_safety["blocked"]:
                raise _sw_http_error(status_code=502, detail="AI assistant output blocked by LLM Guard.")
            return (
                output_safety["llm_guard"]["sanitized_text"],
                {**safety, "output_safety": output_safety, "provider": "openai/gpt-4o"},
            )
        except HTTPException:
            raise
        except Exception:
            # Never answer with canned text posing as an AI rewrite.
            raise _sw_http_error(
                status_code=503,
                detail="The AI writing assistant is not available right now (no provider key configured or the provider did not answer).",
            )
    raise _sw_http_error(
        status_code=503,
        detail="The AI writing assistant is not available right now (no provider key configured).",
    )
