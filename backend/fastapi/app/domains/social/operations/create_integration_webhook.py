"""Social use cases: create integration webhook."""

from ....domains.social.persistence import _SocialWorkspaceState
from ....domains.social.persistence import _sw_audit
from ....domains.social.persistence import _sw_get_account
from ....domains.social.schemas import AutoPostRequest
from ....domains.social.schemas import BrowserExtensionCaptureRequest
from ....domains.social.schemas import BrowserExtensionQueueRequest
from ....domains.social.schemas import CanvaImportRequest
from ....domains.social.schemas import IntegrationWebhookCreateRequest
from ....domains.social.schemas import IntegrationWebhookTestRequest
from ....domains.social.schemas import IntegrationWebhookUpdateRequest
from ....domains.social.schemas import MobileDeviceRegisterRequest
from ..constants import ACCOUNT_NOT_FOUND
from ..constants import AuthDep
from ..services.capabilities import _require_hubspot_for_strict_social
from ..services.publishing import _sw_humanized_publish_slot
from ..services.publishing import _sw_publish_mode_to_status
from ..services.publishing import _sw_resolve_publish_at
from ..services.workspace import _sw_deliver_webhook
from ..services.workspace import _sw_http_error
from ..services.workspace import _sw_resolve_canva_asset_url
from datetime import UTC
from datetime import datetime
from fastapi import APIRouter
from typing import Any
from typing import cast
from urllib.parse import urlparse
import os


def operation_create_integration_webhook(
    st: _SocialWorkspaceState, router: APIRouter, payload: IntegrationWebhookCreateRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:integrations:webhooks:create", 120, 60)
    parsed = urlparse(payload.url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise _sw_http_error(status_code=422, detail="Webhook URL must be a valid HTTP(S) URL.")
    with st.lock:
        item = {
            "id": len(st.integration_webhooks) + 1,
            "tenant_id": auth.tenant_id,
            "name": payload.name.strip(),
            "provider": payload.provider.strip().lower(),
            "url": payload.url.strip(),
            "event_types": [evt.strip() for evt in payload.event_types if evt.strip()],
            "secret": payload.secret,
            "action_type": payload.action_type,
            "enabled": payload.enabled,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        st.integration_webhooks.append(item)
        created = item.copy()
    _sw_audit(st, auth.tenant_id, "social_integration_webhook_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "webhook": created}


def operation_update_integration_webhook(
    st: _SocialWorkspaceState,
    router: APIRouter,
    webhook_id: int,
    payload: IntegrationWebhookUpdateRequest,
    auth: AuthDep,
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:integrations:webhooks:update", 180, 60)
    with st.lock:
        webhook = next(
            (
                item
                for item in st.integration_webhooks
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == webhook_id
            ),
            None,
        )
        if webhook is None:
            raise _sw_http_error(status_code=404, detail="Webhook integration not found.")
        if payload.enabled is not None:
            webhook["enabled"] = payload.enabled
        if payload.event_types is not None:
            webhook["event_types"] = [evt.strip() for evt in payload.event_types if evt.strip()]
        if payload.action_type is not None:
            webhook["action_type"] = payload.action_type
        webhook["updated_at"] = datetime.now(UTC).isoformat()
        updated = webhook.copy()
    _sw_audit(st, auth.tenant_id, "social_integration_webhook_updated", webhook_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "webhook": updated}


def operation_test_integration_webhook(
    st: _SocialWorkspaceState, router: APIRouter, webhook_id: int, payload: IntegrationWebhookTestRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:integrations:webhooks:test", 120, 60)
    with st.lock:
        webhook = next(
            (
                item
                for item in st.integration_webhooks
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == webhook_id
            ),
            None,
        )
        if webhook is None:
            raise _sw_http_error(status_code=404, detail="Webhook integration not found.")
    delivery = _sw_deliver_webhook(
        str(webhook.get("url") or ""), payload.event_type, payload.payload, cast(str | None, webhook.get("secret"))
    )
    with st.lock:
        st.integration_events.append(
            {
                "id": len(st.integration_events) + 1,
                "tenant_id": auth.tenant_id,
                "direction": "outgoing",
                "provider": webhook.get("provider"),
                "event_type": payload.event_type,
                "webhook_id": webhook_id,
                "delivery": delivery,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
    _sw_audit(st, auth.tenant_id, "social_integration_webhook_tested", webhook_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "delivery": delivery}


def operation_receive_incoming_webhook(
    st: _SocialWorkspaceState, router: APIRouter, provider: str, payload: dict[str, Any], auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:integrations:webhooks:incoming", 240, 60)
    provider_key = provider.strip().lower()
    if provider_key == "hubspot":
        _require_hubspot_for_strict_social("HubSpot CRM-connected social webhooks")
    event_type = str(payload.get("event_type") or "social.external.event").strip()
    event_payload = cast(dict[str, Any], payload.get("payload") or payload)
    generated_idea = None
    queued_post = None
    with st.lock:
        st.integration_events.append(
            {
                "id": len(st.integration_events) + 1,
                "tenant_id": auth.tenant_id,
                "direction": "incoming",
                "provider": provider_key,
                "event_type": event_type,
                "payload": event_payload,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        if event_type in {"content_idea.created", "social.idea.create"}:
            generated_idea = {
                "id": len(st.content_ideas) + 1,
                "tenant_id": auth.tenant_id,
                "title": str(event_payload.get("title") or f"{provider_key.title()} idea"),
                "body": str(
                    event_payload.get("body") or event_payload.get("text") or "New externally-triggered social idea."
                ),
                "source": provider_key,
                "source_ref": event_payload.get("id"),
                "tags": cast(list[str], event_payload.get("tags") or ["integration", provider_key]),
                "status": "new",
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            st.content_ideas.append(generated_idea)
        if event_type in {"post.queue", "social.post.queue"}:
            publish_at_raw = str(event_payload.get("publish_at") or "").strip()
            publish_at = datetime.now(UTC)
            if publish_at_raw:
                try:
                    publish_at = datetime.fromisoformat(publish_at_raw)
                    if publish_at.tzinfo is None:
                        publish_at = publish_at.replace(tzinfo=UTC)
                except ValueError:
                    publish_at = datetime.now(UTC)
            queued_post = {
                "id": len(st.scheduled_posts) + 1,
                "tenant_id": auth.tenant_id,
                "platform": str(event_payload.get("platform") or "linkedin").strip().lower(),
                "title": str(event_payload.get("title") or f"{provider_key.title()} queued post"),
                "text": str(event_payload.get("text") or event_payload.get("caption") or ""),
                "publish_at": publish_at.isoformat(),
                "status": "scheduled",
                "created_at": datetime.now(UTC).isoformat(),
                "source": provider_key,
            }
            st.scheduled_posts.append(queued_post)
    _sw_audit(st, auth.tenant_id, "social_integration_webhook_received", None)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "provider": provider_key,
        "event_type": event_type,
        "idea": generated_idea,
        "queued_post": queued_post,
    }


def operation_import_from_canva(
    st: _SocialWorkspaceState, router: APIRouter, payload: CanvaImportRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:integrations:canva:import", 120, 60)
    account = _sw_get_account(st, auth.tenant_id, payload.account_id)
    if account is None:
        raise _sw_http_error(status_code=404, detail=ACCOUNT_NOT_FOUND)
    media_url = _sw_resolve_canva_asset_url(payload)
    publish_at_dt = _sw_resolve_publish_at(
        AutoPostRequest(
            account_id=payload.account_id,
            content_type="image",
            headline=payload.headline,
            caption=payload.caption,
            media_urls=[media_url],
            publish_mode=payload.publish_mode,
            publish_at=payload.publish_at,
        ),
        _sw_humanized_publish_slot(str(payload.target_network).lower(), datetime.now(UTC)),
    )
    with st.lock:
        post = {
            "id": len(st.scheduled_posts) + 1,
            "tenant_id": auth.tenant_id,
            "platform": str(payload.target_network).strip().lower() or str(account.get("network") or "instagram"),
            "headline": payload.headline.strip(),
            "text": payload.caption.strip(),
            "media_urls": [media_url],
            "publish_at": publish_at_dt.isoformat(),
            "status": _sw_publish_mode_to_status(payload.publish_mode),
            "created_at": datetime.now(UTC).isoformat(),
            "source": "canva",
        }
        st.scheduled_posts.append(post)
        job = {
            "id": len(st.canva_import_jobs) + 1,
            "tenant_id": auth.tenant_id,
            "account_id": payload.account_id,
            "design_id": payload.design_id,
            "design_url": payload.design_url,
            "resolved_media_url": media_url,
            "post_id": post["id"],
            "status": "imported",
            "created_at": datetime.now(UTC).isoformat(),
        }
        st.canva_import_jobs.append(job)
        created_job = job.copy()
    _sw_audit(st, auth.tenant_id, "social_canva_imported", created_job["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "job": created_job, "post": post}


def operation_list_canva_imports(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:integrations:canva:imports:list", 240, 60)
    with st.lock:
        items = [item.copy() for item in st.canva_import_jobs if item.get("tenant_id") == auth.tenant_id]
    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(items), "jobs": items}


def operation_get_browser_extension_manifest(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:extensions:browser:manifest", 240, 60)
    base_url = (
        (os.getenv("NEXT_PUBLIC_SITE_URL") or os.getenv("SITE_URL") or "http://localhost:4173").strip().rstrip("/")
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "name": "Nuxtron Social Capture",
        "version": "1.0.0",
        "capture_endpoint": "/api/fastapi/social/extensions/browser/captures",
        "queue_endpoint_template": "/api/fastapi/social/extensions/browser/captures/{capture_id}/queue",
        "auth_headers": ["Authorization", "X-API-Key", "X-Tenant-Id"],
        "permissions": ["activeTab", "contextMenus", "storage", "scripting"],
        "web_accessible_origin": base_url,
    }


def operation_create_browser_capture(
    st: _SocialWorkspaceState, router: APIRouter, payload: BrowserExtensionCaptureRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:extensions:browser:capture:create", 240, 60)
    parsed = urlparse(payload.source_url.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise _sw_http_error(status_code=422, detail="source_url must be a valid HTTP(S) URL.")
    with st.lock:
        capture = {
            "id": len(st.extension_captures) + 1,
            "tenant_id": auth.tenant_id,
            "source_url": payload.source_url.strip(),
            "title": payload.title.strip(),
            "selected_text": (payload.selected_text or "").strip(),
            "note": (payload.note or "").strip(),
            "suggested_network": payload.suggested_network.strip().lower() or "linkedin",
            "screenshot_url": (payload.screenshot_url or "").strip() or None,
            "tags": [tag.strip().lower() for tag in payload.tags if tag.strip()],
            "status": "captured",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        st.extension_captures.append(capture)
        created = capture.copy()
    _sw_audit(st, auth.tenant_id, "social_extension_capture_created", created["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "capture": created}


def operation_list_browser_captures(
    st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep, status: str | None = None, limit: int = 100
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:extensions:browser:capture:list", 240, 60)
    clamped_limit = max(1, min(limit, 500))
    with st.lock:
        items = [
            item.copy()
            for item in st.extension_captures
            if item.get("tenant_id") == auth.tenant_id and (not status or item.get("status") == status)
        ]
    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "count": len(items[:clamped_limit]),
        "captures": items[:clamped_limit],
    }


def operation_queue_browser_capture(
    st: _SocialWorkspaceState, router: APIRouter, capture_id: int, payload: BrowserExtensionQueueRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:extensions:browser:capture:queue", 180, 60)
    account = _sw_get_account(st, auth.tenant_id, payload.account_id)
    if account is None:
        raise _sw_http_error(status_code=404, detail=ACCOUNT_NOT_FOUND)
    with st.lock:
        capture = next(
            (
                item
                for item in st.extension_captures
                if item.get("tenant_id") == auth.tenant_id and item.get("id") == capture_id
            ),
            None,
        )
        if capture is None:
            raise _sw_http_error(status_code=404, detail="Browser capture not found.")
        publish_at = payload.publish_at or _sw_humanized_publish_slot(
            (payload.target_network or str(capture.get("suggested_network") or account.get("network") or "linkedin"))
            .strip()
            .lower(),
            datetime.now(UTC),
        )
        network = (
            (payload.target_network or str(capture.get("suggested_network") or account.get("network") or "linkedin"))
            .strip()
            .lower()
        )
        selected_text = str(capture.get("selected_text") or "").strip()
        note = str(capture.get("note") or "").strip()
        summary = selected_text[:400] if selected_text else note[:400]
        post = {
            "id": len(st.scheduled_posts) + 1,
            "tenant_id": auth.tenant_id,
            "platform": network,
            "headline": str(capture.get("title") or "Captured insight")[:180],
            "text": f"{summary}\n\nSource: {capture.get('source_url')}",
            "media_urls": [capture.get("screenshot_url")] if capture.get("screenshot_url") else [],
            "publish_at": publish_at.isoformat(),
            "status": _sw_publish_mode_to_status(payload.publish_mode),
            "created_at": datetime.now(UTC).isoformat(),
            "source": "browser_extension",
            "source_capture_id": capture_id,
            "tags": capture.get("tags", []),
        }
        st.scheduled_posts.append(post)
        capture["status"] = "queued"
        capture["queued_post_id"] = post["id"]
        capture["updated_at"] = datetime.now(UTC).isoformat()
        queued_capture = capture.copy()
    _sw_audit(st, auth.tenant_id, "social_extension_capture_queued", capture_id)
    return {"status": "ok", "tenant_id": auth.tenant_id, "capture": queued_capture, "post": post}


def operation_get_mobile_config(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:mobile:config", 240, 60)
    api_base = (
        (os.getenv("NEXT_PUBLIC_SITE_URL") or os.getenv("SITE_URL") or "http://localhost:4173").strip().rstrip("/")
    )
    return {
        "status": "ok",
        "tenant_id": auth.tenant_id,
        "offline_sync_enabled": True,
        "quick_post_enabled": True,
        "max_offline_events": 200,
        "push_providers": ["fcm", "onesignal", "apns"],
        "api_base": api_base,
        "sync_endpoint": "/api/fastapi/social/mobile/sync",
        "quick_post_endpoint": "/api/fastapi/social/mobile/quick-post",
    }


def operation_register_mobile_device(
    st: _SocialWorkspaceState, router: APIRouter, payload: MobileDeviceRegisterRequest, auth: AuthDep
) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:mobile:devices:register", 180, 60)
    with st.lock:
        existing = next(
            (
                item
                for item in st.mobile_devices
                if item.get("tenant_id") == auth.tenant_id and item.get("device_id") == payload.device_id.strip()
            ),
            None,
        )
        if existing is None:
            device = {
                "id": len(st.mobile_devices) + 1,
                "tenant_id": auth.tenant_id,
                "device_id": payload.device_id.strip(),
                "platform": payload.platform,
                "push_provider": payload.push_provider,
                "push_token": payload.push_token,
                "app_version": payload.app_version,
                "locale": payload.locale,
                "timezone": payload.timezone,
                "last_seen_at": datetime.now(UTC).isoformat(),
                "created_at": datetime.now(UTC).isoformat(),
            }
            st.mobile_devices.append(device)
            result = device.copy()
        else:
            existing["push_provider"] = payload.push_provider
            existing["push_token"] = payload.push_token
            existing["app_version"] = payload.app_version
            existing["locale"] = payload.locale
            existing["timezone"] = payload.timezone
            existing["last_seen_at"] = datetime.now(UTC).isoformat()
            result = existing.copy()
    _sw_audit(st, auth.tenant_id, "social_mobile_device_registered", result["id"])
    return {"status": "ok", "tenant_id": auth.tenant_id, "device": result}


def operation_list_mobile_devices(st: _SocialWorkspaceState, router: APIRouter, auth: AuthDep) -> dict[str, Any]:
    st.enforce_rate_limit(f"{auth.tenant_id}:mobile:devices:list", 240, 60)
    with st.lock:
        devices = [item.copy() for item in st.mobile_devices if item.get("tenant_id") == auth.tenant_id]
    devices.sort(key=lambda item: str(item.get("last_seen_at") or ""), reverse=True)
    return {"status": "ok", "tenant_id": auth.tenant_id, "count": len(devices), "devices": devices}
