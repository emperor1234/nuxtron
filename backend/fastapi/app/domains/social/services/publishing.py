"""Social Workspace publishing service."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_get_account
from ....domains.social.schemas import AutoPostRequest
from ..constants import ACCOUNT_NOT_FOUND
from ..constants import JSON_CONTENT_TYPE
from .brand import _sw_profile_defaults
from .workspace import _sw_extract_urls
from .workspace import _sw_http_error
from calendar import monthrange
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from fastapi import HTTPException
from typing import Any
from typing import cast
import httpx
import os


def _sw_humanized_publish_slot(network: str, now: datetime) -> datetime:
    base = (now + timedelta(hours=18)).replace(second=0, microsecond=0)
    preferred_hours = {"linkedin": 9, "instagram": 18, "facebook": 13, "x": 9, "tiktok": 19, "youtube": 17}
    minute_slots = [6, 12, 18, 27, 34, 41, 48, 53, 57]
    minute_index = sum((ord(char) for char in f"{network}:{base.date().isoformat()}")) % len(minute_slots)
    hour = preferred_hours.get(network, base.hour)
    candidate = base.replace(hour=hour, minute=minute_slots[minute_index])
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _sw_resolve_publish_at(payload: AutoPostRequest, fallback: datetime) -> datetime:
    if payload.publish_at is None:
        return fallback
    publish_at = payload.publish_at
    if publish_at.tzinfo is None:
        publish_at = publish_at.replace(tzinfo=UTC)
    return publish_at


def _sw_publish_mode_to_status(publish_mode: str) -> str:
    normalized = publish_mode.strip().lower()
    if normalized == "now":
        return "published"
    if normalized == "draft":
        return "draft"
    return "scheduled"


def _sw_shortener_payload(provider: str, url: str, domain: str | None = None) -> dict[str, Any]:
    if provider == "bitly":
        payload: dict[str, Any] = {"long_url": url}
        if domain:
            payload["domain"] = domain
        return payload
    if provider == "tinyurl":
        payload = {"url": url}
        if domain:
            payload["domain"] = domain
        return payload
    payload = {"destination": url}
    if domain:
        payload["domain"] = {"fullName": domain}
    return payload


def _sw_shortener_headers(provider: str, secret: str) -> dict[str, str]:
    if provider == "rebrandly":
        return {"apikey": secret, "Content-Type": JSON_CONTENT_TYPE}
    if provider in {"bitly", "tinyurl"}:
        return {"Authorization": f"Bearer {secret}", "Content-Type": JSON_CONTENT_TYPE}
    return {"Content-Type": JSON_CONTENT_TYPE}


def _sw_shortener_extract_url(provider: str, body: dict[str, Any]) -> str:
    if provider == "bitly":
        return str(body.get("link") or "").strip()
    if provider == "tinyurl":
        data = cast(dict[str, Any], body.get("data") or {})
        return str(data.get("tiny_url") or "").strip()
    short_url = str(body.get("shortUrl") or "").strip()
    if short_url and (not short_url.startswith("http")):
        return f"https://{short_url}"
    return short_url


def _sw_shortener_request(
    endpoint: str, headers: dict[str, str], payload: dict[str, Any], provider_label: str
) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.post(endpoint, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise _sw_http_error(
                status_code=502, detail=f"{provider_label} shortener failed with status {resp.status_code}."
            )
        return cast(dict[str, Any], resp.json())
    except HTTPException:
        raise
    except Exception as exc:
        raise _sw_http_error(status_code=502, detail=f"{provider_label} shortener failed: {str(exc)}")


def _sw_shortener_provider_config(selected_provider: str) -> dict[str, str] | None:
    config = {
        "bitly": {
            "secret_env": "BITLY_ACCESS_TOKEN",
            "endpoint": "https://api-ssl.bitly.com/v4/shorten",
            "label": "Bitly",
        },
        "tinyurl": {
            "secret_env": "TINYURL_API_TOKEN",
            "endpoint": "https://api.tinyurl.com/create",
            "label": "TinyURL",
        },
        "rebrandly": {
            "secret_env": "REBRANDLY_API_KEY",
            "endpoint": "https://api.rebrandly.com/v1/links",
            "label": "Rebrandly",
        },
    }
    return config.get(selected_provider)


def _sw_shorten_url(url: str, provider: str | None = None, domain: str | None = None) -> dict[str, Any]:
    selected_provider = (provider or os.getenv("SOCIAL_LINK_SHORTENER_PROVIDER") or "bitly").strip().lower()
    config = _sw_shortener_provider_config(selected_provider)
    if config is None:
        raise _sw_http_error(status_code=422, detail="Unsupported shortener provider.")
    secret_env = config["secret_env"]
    secret = os.getenv(secret_env, "").strip()
    if not secret:
        raise _sw_http_error(status_code=503, detail=f"{secret_env} is not configured.")
    payload = _sw_shortener_payload(selected_provider, url, domain)
    headers = _sw_shortener_headers(selected_provider, secret)
    body = _sw_shortener_request(config["endpoint"], headers, payload, config["label"])
    short_url = _sw_shortener_extract_url(selected_provider, body)
    return {"provider": selected_provider, "short_url": short_url, "raw": body}


def _sw_shift_month(dt: datetime, months: int) -> datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def _sw_apply_recurrence(base: datetime, recurrence: str, offset: int) -> datetime:
    if recurrence == "daily":
        return base + timedelta(days=offset)
    if recurrence == "weekly":
        return base + timedelta(weeks=offset)
    if recurrence == "monthly":
        return _sw_shift_month(base, offset)
    return base


def _sw_autopilot_preview(st: _SocialWorkspaceState, payload: AutoPostRequest, tenant_id: str) -> dict[str, Any]:
    account = _sw_get_account(st, tenant_id, payload.account_id)
    if account is None:
        raise _sw_http_error(status_code=404, detail=ACCOUNT_NOT_FOUND)
    profile = _sw_profile_defaults(st, tenant_id)
    network = str(account.get("network"))
    now = datetime.now(UTC)
    hashtags = [f"#{tag.lstrip('#').replace(' ', '')}" for tag in profile.get("hashtags", [])[:4]]
    keywords = list(profile.get("keywords", []))[:4]
    headline = payload.headline.strip()
    caption = payload.caption.strip()
    aspect_ratio = (
        "9:16"
        if network in {"instagram", "tiktok", "youtube"} and payload.content_type in {"video", "story"}
        else "1:1"
    )
    description = (
        f"{caption} | Optimized for {account.get('network_label')} with {profile.get('tone', 'professional')} tone."
    )
    recommended_publish_at = _sw_resolve_publish_at(payload, _sw_humanized_publish_slot(network, now))
    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "preview": {
            "account_id": payload.account_id,
            "network": network,
            "aspect_ratio": aspect_ratio,
            "headline": headline[:110],
            "caption": caption[:3000],
            "description": description[:500],
            "hashtags": hashtags,
            "keywords": keywords,
            "recommended_publish_at": recommended_publish_at.isoformat(),
            "supported_formats": account.get("capabilities", []),
        },
    }


def _sw_autopilot_publish_datetime(payload: AutoPostRequest, preview: dict[str, Any]) -> datetime:
    if payload.publish_mode == "now":
        return datetime.now(UTC)
    return _sw_resolve_publish_at(payload, datetime.fromisoformat(str(preview["recommended_publish_at"])))


def _sw_autopilot_apply_short_links(caption: str, payload: AutoPostRequest) -> tuple[str, list[dict[str, Any]]]:
    if not payload.shorten_links:
        return (caption, [])
    short_links: list[dict[str, Any]] = []
    updated_caption = caption
    for url in _sw_extract_urls(updated_caption):
        shortened = _sw_shorten_url(url, payload.shortener_provider, payload.shortener_domain)
        short_url = str(shortened.get("short_url") or "").strip()
        if short_url:
            updated_caption = updated_caption.replace(url, short_url)
            short_links.append({"source_url": url, "short_url": short_url, "provider": shortened.get("provider")})
    return (updated_caption, short_links)


def _sw_autopilot_approval_state(payload: AutoPostRequest) -> tuple[bool, list[str]]:
    approval_levels = [level.strip().lower() for level in payload.approval_levels if level.strip()]
    needs_approval = payload.requires_approval or bool(approval_levels)
    return (needs_approval, approval_levels)


def _sw_autopilot_post_status(publish_mode: str, needs_approval: bool) -> str:
    if needs_approval:
        return "pending_approval"
    if publish_mode == "now":
        return "published"
    return "scheduled"


def _sw_build_recurring_autopilot_posts(
    st: _SocialWorkspaceState,
    payload: AutoPostRequest,
    tenant_id: str,
    account: dict[str, Any],
    preview: dict[str, Any],
    caption: str,
    publish_at_dt: datetime,
    needs_approval: bool,
    approval_levels: list[str],
    short_links: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if payload.recurrence == "none" or payload.recurrence_count <= 1:
        return []
    recurring_posts: list[dict[str, Any]] = []
    until_dt = payload.recurrence_until
    if until_dt is not None and until_dt.tzinfo is None:
        until_dt = until_dt.replace(tzinfo=UTC)
    for offset in range(1, payload.recurrence_count):
        candidate = _sw_apply_recurrence(publish_at_dt, payload.recurrence, offset)
        if until_dt is not None and candidate > until_dt:
            break
        recurring_posts.append(
            {
                "id": len(st.scheduled_posts) + 1 + len(recurring_posts),
                "tenant_id": tenant_id,
                "platform": account.get("network"),
                "text": caption,
                "publish_at": candidate.isoformat(),
                "media_urls": payload.media_urls,
                "status": _sw_autopilot_post_status("scheduled", needs_approval),
                "created_at": datetime.now(UTC).isoformat(),
                "autopilot": True,
                "headline": preview["headline"],
                "description": preview["description"],
                "hashtags": preview["hashtags"],
                "keywords": preview["keywords"],
                "aspect_ratio": preview["aspect_ratio"],
                "recurrence": payload.recurrence,
                "recurrence_index": offset,
                "approval_status": "pending" if needs_approval else "not_required",
                "approval_levels": approval_levels,
                "short_links": short_links,
            }
        )
    return recurring_posts


def _sw_build_autopilot_approval_request(
    st: _SocialWorkspaceState,
    tenant_id: str,
    record: dict[str, Any],
    account: dict[str, Any],
    preview: dict[str, Any],
    approval_levels: list[str],
    auto_publish_on_approve: bool,
) -> dict[str, Any]:
    return {
        "id": f"appr-{len(st.approval_requests) + 1}",
        "tenant_id": tenant_id,
        "post_id": str(record["id"]),
        "platform": account.get("network"),
        "content_preview": str(preview["headline"])[:120],
        "requested_by": "autopilot",
        "approvers": approval_levels or ["approver"],
        "approval_levels": approval_levels or ["approver"],
        "approvals_received": [],
        "auto_publish_on_approve": auto_publish_on_approve,
        "status": "pending",
        "created_at": datetime.now(UTC).isoformat(),
    }


def _sw_store_short_links(
    st: _SocialWorkspaceState, tenant_id: str, post_id: int, short_links: list[dict[str, Any]]
) -> None:
    for item in short_links:
        st.short_links.append(
            {
                "id": len(st.short_links) + 1,
                "tenant_id": tenant_id,
                "post_id": str(post_id),
                "provider": item.get("provider"),
                "source_url": item.get("source_url"),
                "short_url": item.get("short_url"),
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
