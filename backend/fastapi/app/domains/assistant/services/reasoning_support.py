"""Assistant reasoning, text/vector normalization, and protection signals."""

from ..constants import DEFAULT_BLOCKED_ACTIONS
from ..constants import LOCAL_EMBEDDING_DIMENSIONS
from ..constants import TOKEN_PATTERN
from ..schemas import IRAChatActionPlan
from datetime import UTC
from datetime import datetime
from typing import Any
from typing import Literal
from typing import cast
import hashlib
import importlib.util
import math
import os
import re


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _event_epoch(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        try:
            return int(datetime.fromisoformat(normalized).timestamp())
        except ValueError:
            return 0
    return 0


def _slugify(value: str, *, fallback: str) -> str:
    lowered = re.sub("[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return lowered[:80] or fallback


def _tokenize_text(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(value)]


def _normalize_vector(values: list[float]) -> list[float]:
    magnitude = math.sqrt(sum((value * value for value in values)))
    if magnitude <= 0:
        return values
    return [round(value / magnitude, 8) for value in values]


def _local_hash_embedding(value: str, *, dimensions: int = LOCAL_EMBEDDING_DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    for token in _tokenize_text(value):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], byteorder="big") % dimensions
        direction = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + digest[5] / 255.0
        vector[index] += direction * weight
    return _normalize_vector(vector)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    return max(-1.0, min(1.0, round(sum((a * b for a, b in zip(left, right, strict=False))), 6)))


def _lexical_overlap_score(query_tokens: list[str], candidate_tokens: list[str]) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0
    query_set = set(query_tokens)
    candidate_set = set(candidate_tokens)
    overlap = len(query_set & candidate_set)
    return round(overlap / max(1, len(query_set)), 6)


def _chunk_text(value: str, *, chunk_size: int, chunk_overlap: int) -> list[str]:
    normalized = " ".join(value.split())
    if len(normalized) <= chunk_size:
        return [normalized]
    step = max(1, chunk_size - chunk_overlap)
    chunks: list[str] = []
    index = 0
    while index < len(normalized):
        chunk = normalized[index : index + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        index += step
    return chunks or [normalized]


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _normalize_brain_provider(
    value: str,
) -> Literal["auto", "openai", "anthropic", "google_deepmind", "deepseek", "llama", "mistral"]:
    lowered = value.strip().lower()
    if lowered in {"openai", "anthropic", "google_deepmind", "deepseek", "llama", "mistral"}:
        return cast(Literal["openai", "anthropic", "google_deepmind", "deepseek", "llama", "mistral"], lowered)
    return "auto"


def _normalize_chat_provider_preference(value: str) -> str:
    lowered = value.strip().lower()
    if lowered in {"", "auto", "default"}:
        return "auto"
    if lowered in {"internal", "built_in", "builtin", "rule_based"}:
        return "internal"
    if (
        lowered in {"openai", "chatgpt", "azure-openai", "azure_openai"}
        or lowered.startswith("gpt")
        or "openai" in lowered
        or ("chatgpt" in lowered)
        or ("azureopenai" in lowered)
        or ("azure-openai" in lowered)
        or ("azure_openai" in lowered)
    ):
        return "openai"
    if (
        lowered in {"anthropic", "claude", "claudebot"}
        or lowered.startswith("claude")
        or "anthropic" in lowered
        or ("claude" in lowered)
    ):
        return "anthropic"
    return lowered


def _extract_chat_provider_routing(context: dict[str, Any]) -> dict[str, Any]:
    llm_routing = (
        cast(dict[str, Any], context.get("llm_routing") or {}) if isinstance(context.get("llm_routing"), dict) else {}
    )
    requested = _normalize_chat_provider_preference(str(llm_routing.get("preferred_provider", "auto") or "auto"))
    brain_provider = _normalize_brain_provider(requested)
    return {
        "requested_provider": requested,
        "brain_provider": None if requested in {"auto", "internal"} or brain_provider == "auto" else brain_provider,
        "custom_provider_label": str(llm_routing.get("custom_provider_label", "") or "").strip(),
        "requested_external_provider": bool(llm_routing.get("requested_external_provider", False)),
    }


def _build_chat_reasoning_prompt(
    *,
    role: str,
    channel: str,
    message: str,
    intent: str,
    domain: str,
    risk: dict[str, Any],
    action_plan: IRAChatActionPlan,
    knowledge_hits: list[dict[str, Any]],
    recent_history: list[dict[str, Any]],
) -> str:
    knowledge_lines = [
        f"- {str(hit.get('title', 'Knowledge')).strip()}: {str(hit.get('content', '')).strip()[:180]}"
        for hit in knowledge_hits[:3]
    ]
    history_lines = [
        f"- {str(item.get('role', 'unknown'))}: {str(item.get('content', '')).strip()[:160]}"
        for item in recent_history[-4:]
        if str(item.get("content", "")).strip()
    ]
    action_lines = [
        f"- {str(item.get('label', item.get('action', 'step'))).strip()}"
        for item in action_plan.recommended_actions[:5]
    ]
    risk_level = str(risk.get("risk_level", "low")).strip() or "low"
    return f"You are IRA, a guarded autonomous operations copilot for Nuxtron. Respond concisely, stay operationally useful, avoid inventing actions that bypass approvals, and mention approval or human validation when the supplied risk/action plan requires it.\n\nRole: {role}\nChannel: {channel}\nUser message: {message.strip()}\nIntent: {intent}\nDomain: {domain}\nRisk level: {risk_level}\nRequires human validation: {action_plan.requires_human_validation}\nRequires explicit approval: {action_plan.requires_explicit_approval}\n\nRecommended actions:\n{(chr(10).join(action_lines) if action_lines else '- No recommended actions generated.')}\n\nKnowledge hits:\n{(chr(10).join(knowledge_lines) if knowledge_lines else '- No grounded knowledge hits available.')}\n\nRecent conversation history:\n{(chr(10).join(history_lines) if history_lines else '- No recent history available.')}\n\nReturn a single end-user-facing answer in plain text."


def _contains_risk_marker(value: object, markers: tuple[str, ...]) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.strip().lower()
    return any((marker in lowered for marker in markers))


def compute_tenant_revenue_snapshot(
    *, tenant_id: str, invoices_memory: list[dict[str, Any]], credit_ledger_memory: list[dict[str, Any]]
) -> dict[str, float]:
    revenue = 0.0
    for inv in invoices_memory:
        if inv.get("tenant_id") != tenant_id:
            continue
        if str(inv.get("status", "")).lower() not in {"paid", "settled"}:
            continue
        revenue += float(inv.get("amount", 0.0) or 0.0)
    credits_granted = sum(
        (
            max(0, int(entry.get("amount", 0) or 0))
            for entry in credit_ledger_memory
            if entry.get("tenant_id") == tenant_id
        )
    )
    credits_cost = round(credits_granted * 0.002, 2)
    estimated_cogs = round(revenue * 0.2, 2)
    total_cost = round(estimated_cogs + credits_cost, 2)
    profit_margin_pct = 0.0 if revenue <= 0 else round((revenue - total_cost) / revenue * 100.0, 2)
    return {
        "revenue": round(revenue, 2),
        "estimated_cogs": estimated_cogs,
        "credits_cost": credits_cost,
        "total_cost": total_cost,
        "profit_margin_pct": profit_margin_pct,
    }


def compute_tenant_suspicious_signal(
    *,
    tenant_id: str,
    stripe_events_memory: list[dict[str, Any]],
    revenue_conversions_memory: list[dict[str, Any]],
    api_usage_audit_memory: list[dict[str, Any]],
    ai_security_usage_memory: list[dict[str, Any]],
) -> dict[str, Any]:
    now_ts = int(datetime.now(UTC).timestamp())
    api_window_seconds = int(os.getenv("IRA_RISK_API_WINDOW_SECONDS", "900"))
    payment_window_seconds = int(os.getenv("IRA_RISK_PAYMENT_WINDOW_SECONDS", "86400"))
    ai_window_seconds = int(os.getenv("IRA_RISK_AI_WINDOW_SECONDS", "3600"))
    api_threshold = max(1, int(os.getenv("IRA_RISK_API_BURST_THRESHOLD", "250")))
    ai_cost_threshold = max(0.1, float(os.getenv("IRA_RISK_AI_COST_THRESHOLD", "25.0")))
    recent_api = [
        item
        for item in api_usage_audit_memory
        if item.get("tenant_id") == tenant_id and _event_epoch(item.get("timestamp", 0)) >= now_ts - api_window_seconds
    ]
    recent_payments = [
        item
        for item in stripe_events_memory
        if item.get("tenant_id") == tenant_id
        and _event_epoch(item.get("created_at")) >= now_ts - payment_window_seconds
    ]
    recent_conversions = [
        item
        for item in revenue_conversions_memory
        if item.get("tenant_id") == tenant_id
        and _event_epoch(item.get("received_at") or item.get("created_at")) >= now_ts - payment_window_seconds
    ]
    recent_ai_usage = [
        item
        for item in ai_security_usage_memory
        if item.get("tenant_id") == tenant_id and _event_epoch(item.get("timestamp", 0)) >= now_ts - ai_window_seconds
    ]
    payment_failures = [
        item
        for item in recent_payments
        if _contains_risk_marker(
            item.get("event_type") or item.get("type"), ("fail", "refund", "chargeback", "dispute")
        )
        or _contains_risk_marker(item.get("status"), ("failed", "refunded", "disputed"))
    ]
    api_score = min(1.0, len(recent_api) / api_threshold)
    ai_cost_total = round(sum((float(item.get("estimated_cost", 0.0) or 0.0) for item in recent_ai_usage)), 4)
    ai_score = min(1.0, ai_cost_total / ai_cost_threshold)
    payment_denominator = max(1, len(recent_conversions) + len(payment_failures))
    payment_score = min(1.0, len(payment_failures) / payment_denominator)
    reasons: list[str] = []
    if api_score >= 0.8:
        reasons.append("api_burst_detected")
    if payment_score >= 0.5:
        reasons.append("payment_failure_ratio_high")
    if ai_score >= 0.8:
        reasons.append("ai_cost_burn_high")
    if not recent_conversions and payment_failures:
        reasons.append("payments_failing_without_conversions")
    score = round(api_score * 0.35 + payment_score * 0.4 + ai_score * 0.25, 4)
    return {
        "score": score,
        "components": {
            "api_burst_score": round(api_score, 4),
            "payment_failure_score": round(payment_score, 4),
            "ai_cost_burn_score": round(ai_score, 4),
        },
        "metrics": {
            "api_requests_window": len(recent_api),
            "payment_failures_window": len(payment_failures),
            "conversion_count_window": len(recent_conversions),
            "ai_cost_window": ai_cost_total,
        },
        "reasons": reasons,
    }


def _watchdog_activation_reason(
    control: dict[str, Any], snapshot: dict[str, float], suspicious_signal: dict[str, Any]
) -> str | None:
    min_margin = float(control.get("min_profit_margin_pct", 70.0))
    if float(snapshot.get("profit_margin_pct", 0.0)) < min_margin:
        return "profit_below_target"
    if float(suspicious_signal.get("score", 0.0)) >= float(control.get("suspicious_signal_threshold", 0.75)):
        return "suspicious_signal"
    return None


def _activate_watchdog_protection(
    *,
    tenant_id: str,
    control: dict[str, Any],
    snapshot: dict[str, float],
    suspicious_signal: dict[str, Any],
    reason: str,
    ira_events_memory: list[dict[str, Any]],
    audit_log_memory: list[dict[str, Any]],
) -> None:
    control["protection_mode"] = True
    control["blocked_actions"] = list(DEFAULT_BLOCKED_ACTIONS)
    control["updated_at"] = _now_iso()
    audit_log_memory.append(
        {
            "id": len(audit_log_memory) + 1,
            "tenant_id": tenant_id,
            "action": "ira_watchdog_protection_mode_activated",
            "source": "ira-watchdog",
            "metadata": {
                "profit_margin_pct": snapshot.get("profit_margin_pct", 0.0),
                "suspicious_signal_score": suspicious_signal.get("score", 0.0),
                "reason": reason,
            },
            "created_at": _now_iso(),
        }
    )
    ira_events_memory.append(
        {
            "id": len(ira_events_memory) + 1,
            "tenant_id": tenant_id,
            "event_type": "watchdog_protection_mode_activated",
            "payload": {
                "reason": reason,
                "profit_margin_pct": snapshot.get("profit_margin_pct", 0.0),
                "suspicious_signal": suspicious_signal,
                "blocked_actions": control["blocked_actions"],
            },
            "created_at": _now_iso(),
        }
    )
