"""Workforce provider actions and AI mission artifact generation."""

from __future__ import annotations
from ..constants import DEFAULT_AI_GATEWAY_PATH
from ..constants import JSON_CONTENT_TYPE
from ..constants import PROVIDER_CATALOG
from datetime import UTC
from datetime import datetime
from typing import Any
import httpx
import os
from urllib.parse import urlsplit
from ....identity.async_egress import outbound_async_request
from ....identity.async_egress import resolve_outbound_target_async


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


async def _verify_provider_live_standalone(provider: str, token: str) -> tuple[bool, int, dict[str, Any]]:
    entry = PROVIDER_CATALOG.get(provider)
    if entry is None:
        return (False, 422, {"error": "unsupported-provider"})
    timeout = float(os.getenv("WORKFORCE_PROVIDER_TEST_TIMEOUT_SECONDS", "15"))
    headers = {"Authorization": f"Bearer {token}"}
    target = await resolve_outbound_target_async(entry["test_url"])
    response = await outbound_async_request(
        "GET", target, headers=headers, timeout=timeout, max_response_bytes=1_000_000
    )
    ok = response.status_code < 400
    try:
        payload = response.json()
        body = payload if isinstance(payload, dict) else {"data": payload}
    except Exception:
        body = {"raw": response.text[:500]}
    return (ok, response.status_code, body)


def _ai_gateway_url() -> str:
    explicit = str(os.getenv("WORKFORCE_AI_GATEWAY_URL", "")).strip()
    base_urls = [str(os.getenv(key, "")).strip().rstrip("/") for key in ("FASTAPI_URL", "NEXT_PUBLIC_FASTAPI_URL")]
    base_urls = [value for value in base_urls if value]
    is_production = os.getenv("ENVIRONMENT", "development").strip().lower() == "production"

    if explicit:
        candidate = explicit.rstrip("/")
    elif base_urls:
        candidate = f"{base_urls[0]}{DEFAULT_AI_GATEWAY_PATH}"
    elif is_production:
        raise RuntimeError("Production Workforce AI gateway is not configured.")
    else:
        return f"http://127.0.0.1:8000{DEFAULT_AI_GATEWAY_PATH}"

    if is_production:
        parsed = urlsplit(candidate)
        allowed_hosts = {parsed_base.hostname.lower() for base in base_urls if (parsed_base := urlsplit(base)).hostname}
        allowed_hosts.update(
            host.strip().lower()
            for host in os.getenv("WORKFORCE_AI_GATEWAY_ALLOWED_HOSTS", "").split(",")
            if host.strip()
        )
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.hostname.lower() not in allowed_hosts
        ):
            raise RuntimeError("Production Workforce AI gateway origin is not allowed.")
    return candidate


def _mission_system_prompt(role: str) -> str:
    return f"You are an autonomous execution agent in production mode. Role={role}. Output concise execution-ready content and an execution brief. Never include placeholders, fake IDs, or TODO text."


def _extract_ai_text(payload: dict[str, Any]) -> str:
    candidates = [
        payload.get("content"),
        payload.get("text"),
        payload.get("response"),
        payload.get("result"),
        payload.get("output"),
    ]
    for item in candidates:
        if isinstance(item, str) and item.strip():
            return item.strip()
        if isinstance(item, dict):
            nested = _extract_ai_text(item)
            if nested:
                return nested
    return ""


async def _generate_mission_artifact(tenant_id: str, mission: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    timeout = float(os.getenv("WORKFORCE_AI_TIMEOUT_SECONDS", "25"))
    is_production = os.getenv("ENVIRONMENT", "development").strip().lower() == "production"
    strict_mode = is_production or str(os.getenv("WORKFORCE_STRICT_AI_EXECUTION", "true")).lower() == "true"
    provider = str(os.getenv("WORKFORCE_AI_PROVIDER", "auto")).strip().lower() or "auto"
    prompt = f"Mission title: {mission.get('title', '')}\nRole: {mission.get('role', '')}\nObjective: {mission.get('objective', '')}\nDescription: {mission.get('description', '')}\nInput context: {mission.get('input_context', {})}\nProduce:\n1) final_output\n2) execution_summary\n3) priority_actions (max 5)"
    headers: dict[str, str] = {"Content-Type": JSON_CONTENT_TYPE}
    api_key = str(os.getenv("FASTAPI_API_KEY", "")).strip()
    if api_key:
        headers["X-API-Key"] = api_key
        headers["X-Tenant-Id"] = tenant_id
    request_body: dict[str, Any] = {
        "provider": provider,
        "prompt": prompt,
        "system_prompt": _mission_system_prompt(str(mission.get("role", "general"))),
    }
    try:
        async with httpx.AsyncClient(timeout=timeout, trust_env=False, follow_redirects=False) as client:
            response = await client.post(_ai_gateway_url(), json=request_body, headers=headers)
        if response.status_code >= 400:
            return (False, {"error": "ai-gateway-failed", "status_code": response.status_code})
        raw = response.json()
        payload = raw if isinstance(raw, dict) else {"data": raw}
        generated = _extract_ai_text(payload)
        if not generated:
            return (False, {"error": "ai-gateway-empty-output", "response": payload})
        return (True, {"provider": provider, "generated": generated, "raw": payload})
    except Exception as exc:
        if strict_mode:
            return (False, {"error": "ai-gateway-unreachable", "detail": type(exc).__name__})
        fallback_text = f"Execution brief for role={mission.get('role')} objective={mission.get('objective')} generated_at={_now_iso()}"
        return (
            True,
            {
                "provider": "rules_fallback",
                "generated": fallback_text,
                "raw": {"fallback": True},
                "warning": "AI gateway unavailable; switched to deterministic fallback. Set WORKFORCE_STRICT_AI_EXECUTION=true to fail hard.",
            },
        )


async def _dispatch_provider_action(
    provider: str, token: str, mission: dict[str, Any], generated_artifact: str, connection: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    timeout = float(os.getenv("WORKFORCE_PROVIDER_ACTION_TIMEOUT_SECONDS", "20"))
    metadata = connection.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    headers = {"Authorization": f"Bearer {token}"}
    if provider == "slack":
        channel = str(metadata.get("channel") or "#general").strip()
        payload = {"channel": channel, "text": f"[{mission.get('title', 'Mission')}]\n{generated_artifact[:3500]}"}
        target = await resolve_outbound_target_async(PROVIDER_CATALOG[provider]["action_url"])
        response = await outbound_async_request(
            "POST", target, json=payload, headers=headers, timeout=timeout, max_response_bytes=1_000_000
        )
        ok = response.status_code < 400
        response_payload = (
            response.json()
            if response.headers.get("content-type", "").startswith(JSON_CONTENT_TYPE)
            else {"raw": response.text[:500]}
        )
        return (ok, {"channel": channel, "status_code": response.status_code, "response": response_payload})
    if provider == "x":
        payload = {"text": generated_artifact[:260]}
        target = await resolve_outbound_target_async(PROVIDER_CATALOG[provider]["action_url"])
        response = await outbound_async_request(
            "POST", target, json=payload, headers=headers, timeout=timeout, max_response_bytes=1_000_000
        )
        ok = response.status_code < 400
        response_payload = (
            response.json()
            if response.headers.get("content-type", "").startswith(JSON_CONTENT_TYPE)
            else {"raw": response.text[:500]}
        )
        return (ok, {"status_code": response.status_code, "response": response_payload})
    action_url = str(metadata.get("action_url") or "").strip()
    if action_url:
        # The integration access token is scoped to its named provider. Never
        # forward it to a tenant-supplied URL; custom webhook credentials need
        # a separate, explicitly scoped secret and egress policy.
        return (False, {"error": "custom-action-endpoints-not-supported"})
    provider_kind = PROVIDER_CATALOG.get(provider, {}).get("kind")
    if provider_kind == "analytics":
        return (False, {"error": "analytics-provider-does-not-support-actions", "provider": provider})
    return (False, {"error": "action-endpoint-not-configured", "provider": provider})
