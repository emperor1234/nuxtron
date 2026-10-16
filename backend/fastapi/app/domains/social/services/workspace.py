"""Social Workspace workspace service."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.schemas import CanvaImportRequest
from ..constants import JSON_CONTENT_TYPE
from ..constants import SUPPORTED_NETWORKS
from ...identity.secure_egress import outbound_request
from ...identity.secure_egress import resolve_outbound_target
from collections.abc import Callable
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from operator import eq
from operator import ge
from operator import gt
from operator import le
from operator import lt
from operator import ne
from typing import Any
from typing import cast
import httpx
import os
import re


def _sw_http_error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def _normalized_text(payload: dict[str, Any], key: str, default: str) -> str:
    value = payload.get(key)
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned:
            return cleaned
    return default


def _sw_extract_urls(text: str) -> list[str]:
    return [match.group(0) for match in re.finditer("https?://[^\\s)\\]>]+", text)]


def _sw_conditional_metrics(st: "_SocialWorkspaceState", tenant_id: str) -> dict[str, float]:
    with st.lock:
        queued_posts = sum(
            (
                1
                for post in st.scheduled_posts
                if post.get("tenant_id") == tenant_id and post.get("status") == "scheduled"
            )
        )
        draft_posts = sum(
            (1 for post in st.scheduled_posts if post.get("tenant_id") == tenant_id and post.get("status") == "draft")
        )
        inbox_unread = sum(
            (
                1
                for item in st.inbox_messages
                if item.get("tenant_id") == tenant_id and item.get("status") not in {"responded", "complete"}
            )
        )
        connected_accounts = sum((1 for account in st.social_accounts if account.get("tenant_id") == tenant_id))
    return {
        "queued_posts": float(queued_posts),
        "draft_posts": float(draft_posts),
        "inbox_unread": float(inbox_unread),
        "connected_accounts": float(connected_accounts),
    }


def _sw_evaluate_conditions(st: "_SocialWorkspaceState", tenant_id: str, rules: list[dict[str, Any]]) -> dict[str, Any]:
    if not rules:
        return {"passed": True, "results": [], "metrics": _sw_conditional_metrics(st, tenant_id)}
    metrics = _sw_conditional_metrics(st, tenant_id)
    operators: dict[str, Callable[[float, float], bool]] = {
        "gt": gt,
        "gte": ge,
        "lt": lt,
        "lte": le,
        "eq": eq,
        "neq": ne,
    }
    comparisons: list[dict[str, Any]] = []
    passed = True
    for rule in rules:
        metric = str(rule.get("metric") or "").strip().lower()
        operator = str(rule.get("operator") or "gte").strip().lower()
        try:
            expected = float(rule.get("value"))
        except (TypeError, ValueError):
            expected = 0.0
        actual = float(metrics.get(metric, 0.0))
        comparator = operators.get(operator)
        ok = metric in metrics and comparator is not None and comparator(actual, expected)
        if not ok:
            passed = False
        comparisons.append(
            {"metric": metric, "operator": operator, "expected": expected, "actual": actual, "passed": ok}
        )
    return {"passed": passed, "results": comparisons, "metrics": metrics}


def _sw_deliver_webhook(
    url: str, event_type: str, payload: dict[str, Any], secret: str | None = None
) -> dict[str, Any]:
    headers = {"Content-Type": JSON_CONTENT_TYPE, "User-Agent": "NuxtronSocial/1.0"}
    if secret and secret.strip():
        headers["X-Nuxtron-Webhook-Secret"] = secret.strip()
    body = {"event_type": event_type, "occurred_at": datetime.now(UTC).isoformat(), "payload": payload}
    try:
        target = resolve_outbound_target(url)
        response = outbound_request(
            "POST",
            target,
            headers=headers,
            json=body,
            timeout=12.0,
            max_response_bytes=64_000,
        )
        return {"ok": response.status_code < 300, "status_code": response.status_code}
    except Exception as exc:
        return {"ok": False, "status_code": 0, "error": f"Webhook delivery failed ({type(exc).__name__})."}


def _sw_resolve_canva_asset_url(payload: CanvaImportRequest) -> str:
    if payload.design_url and payload.design_url.strip():
        return payload.design_url.strip()
    if not payload.design_id or not payload.design_id.strip():
        raise _sw_http_error(status_code=422, detail="Provide either design_url or design_id for Canva import.")
    api_base = os.getenv("CANVA_API_BASE_URL", "https://api.canva.com/rest/v1").strip().rstrip("/")
    token = os.getenv("CANVA_ACCESS_TOKEN", "").strip()
    if not token:
        raise _sw_http_error(status_code=503, detail="CANVA_ACCESS_TOKEN is not configured.")
    design_id = payload.design_id.strip()
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(
                f"{api_base}/designs/{design_id}/exports",
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
        if resp.status_code >= 400:
            raise _sw_http_error(status_code=502, detail=f"Canva export fetch failed with status {resp.status_code}.")
        body = resp.json()
        exports = cast(list[dict[str, Any]], body.get("items") or body.get("exports") or [])
        export_url = ""
        if exports:
            export_url = str(exports[0].get("url") or exports[0].get("download_url") or "").strip()
        if not export_url:
            export_url = str(body.get("url") or body.get("download_url") or "").strip()
        if not export_url:
            raise _sw_http_error(status_code=502, detail="Canva API did not return an export URL.")
        return export_url
    except HTTPException:
        raise
    except Exception as exc:
        raise _sw_http_error(status_code=502, detail=f"Canva import failed: {str(exc)}")


def _sw_seed_notifications(st: _SocialWorkspaceState, tenant_id: str, network: str, account_name: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_inbox_messages(st: _SocialWorkspaceState, tenant_id: str, network: str, handle: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_post_history(st: _SocialWorkspaceState, tenant_id: str, network: str, account_id: int) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_listening(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_monitoring_streams(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_ad_campaigns(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_reports(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_competitors(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_reviews(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_influencers(st: _SocialWorkspaceState) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return


def _sw_seed_saved_replies(st: _SocialWorkspaceState, tenant_id: str) -> None:
    # Demo data is never created for a workspace; records exist only once a user or a connected provider creates them.
    return
