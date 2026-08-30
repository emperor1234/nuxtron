from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

JsonObject = dict[str, object]
AuthDep = Annotated[AuthContext, Depends(require_auth)]


# ── Request models ──────────────────────────────────────────────────────────────

class AiGatewayGenerateRequest(BaseModel):
    provider: Literal['auto', 'openai', 'anthropic', 'google_vertex'] = 'auto'
    prompt: str = Field(min_length=1, max_length=12000)
    system_prompt: str | None = Field(default=None, max_length=4000)
    model: str | None = Field(default=None, max_length=120)
    max_tokens: int = Field(default=500, ge=1, le=4000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    target_roi: float = Field(default=0.70, ge=0.0, le=20.0)
    value_per_1k_tokens: float = Field(default=0.006, ge=0.0001, le=50.0)
    quality_floor: float = Field(default=0.80, ge=0.0, le=1.0)


class AiSecurityRotateKeyRequest(BaseModel):
    provider: Literal['openai', 'anthropic', 'google_vertex']
    api_key: str = Field(min_length=8, max_length=500)
    label: str | None = Field(default=None, max_length=120)


class AiSecurityAppealRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=1200)


class AiSecurityAppealResolveRequest(BaseModel):
    decision: Literal['approved', 'rejected']
    notes: str | None = Field(default=None, max_length=1200)


class AiSecurityIdseventRequest(BaseModel):
    source: Literal['suricata', 'zeek', 'ossec', 'fail2ban', 'manual']
    severity: Literal['low', 'medium', 'high', 'critical']
    rule_id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=3, max_length=1200)
    tenant_id: str | None = Field(default=None, max_length=120)
    provider: Literal['openai', 'anthropic', 'google_vertex'] | None = None
    ip_address: str | None = Field(default=None, max_length=120)
    action: Literal['alert', 'block-tenant', 'disable-provider'] = 'alert'


# ── Router factory ──────────────────────────────────────────────────────────────


def create_ai_security_router(  # NOSONAR
    *,
    enforce_rate_limit: Callable[[str, int, int], None],
    is_tenant_blocked: Callable[[str], tuple[bool, int]],
    prepare_ai_gateway_attempt: Callable[[AiGatewayGenerateRequest, str, str | None, bool], tuple[str, str, object] | None],
    invoke_ai_provider_generation: Callable[[str, object, AuthContext, str], JsonObject],
    update_provider_health: Callable[[str, bool, float], None],
    record_ai_gateway_success: Callable[[JsonObject, object, str, AuthContext, Request], None],
    coerce_int: Callable[[object, int], int],
    coerce_float: Callable[[object, float], float],
    load_ai_generated_asset_bytes: Callable[[JsonObject, int, str], bytes],
    record_ai_security_alert: Callable[[str, str, JsonObject], JsonObject],
    send_security_email_alert: Callable[[JsonObject], None],
    block_tenant: Callable[[str, str], None],
    disable_provider: Callable[[str, str], None],
    security_alert_db_queue_enabled: Callable[[], bool],
    db_security_alert_email_queue_items: Callable[[str, int, int], list[JsonObject] | None],
    memory_security_alert_email_queue_items: Callable[[str, int, int], list[JsonObject]],
    paginate_email_queue_items: Callable[[list[JsonObject], int], tuple[list[JsonObject], bool, int | None]],
    db_requeue_security_alert_email: Callable[[int, str, str], JsonObject | None],
    memory_requeue_security_alert_email: Callable[[int, str, str], JsonObject | None],
    db_security_alert_email_exists: Callable[[int], bool],
    security_alert_delivery_summary: Callable[[], JsonObject],
    is_provider_disabled: Callable[[str], bool],
    ai_security_usage_memory: list[JsonObject],
    ai_security_alerts_memory: list[JsonObject],
    ai_security_blocks_memory: list[JsonObject],
    ai_security_appeals_memory: list[JsonObject],
    ai_security_ids_events_memory: list[JsonObject],
    ai_provider_keys_memory: list[JsonObject],
    resend_messages_memory: list[JsonObject],
    ai_generated_assets_memory: list[JsonObject],
    ai_generated_assets_lock: threading.Lock,
    ai_security_lock: threading.Lock,
    ai_providers: tuple[str, ...],
    ai_model_catalog: dict[str, dict[str, dict[str, float]]],
    provider_health_metrics: dict[str, dict[str, float]],
    is_production: Callable[[], bool],
) -> APIRouter:
    router = APIRouter()

    # ── Scoped helpers ──────────────────────────────────────────────────────────

    def _ai_security_usage_window(tenant_id: str, window_minutes: int) -> list[JsonObject]:
        now_ts = int(time.time())
        window_seconds = max(1, min(window_minutes, 24 * 60)) * 60
        return [
            item for item in ai_security_usage_memory
            if item.get('tenant_id') == tenant_id and coerce_int(item.get('timestamp', 0), 0) >= (now_ts - window_seconds)
        ]

    def _ai_security_provider_graph(usage_window: list[JsonObject]) -> list[JsonObject]:
        rows: list[JsonObject] = []
        for provider in ai_providers:
            provider_items = [item for item in usage_window if item.get('provider') == provider]
            provider_calls = len(provider_items)
            provider_roi = round(sum(coerce_float(item.get('roi', 0.0), 0.0) for item in provider_items) / provider_calls, 6) if provider_calls else 0.0
            disabled = is_provider_disabled(provider)
            rows.append({
                'provider': provider,
                'calls': provider_calls,
                'avg_roi': provider_roi,
                'color': 'red' if disabled else 'green',
                'status': 'blocked' if disabled else 'healthy',
            })
        return rows

    def _ai_security_timeline(usage_window: list[JsonObject]) -> list[JsonObject]:
        return [
            {
                'ts': item.get('timestamp'),
                'provider': item.get('provider'),
                'model': item.get('model'),
                'roi': item.get('roi'),
                'latency_ms': item.get('latency_ms'),
                'estimated_cost': item.get('estimated_cost'),
                'status': item.get('status'),
            }
            for item in usage_window[-240:]
        ]

    def _ai_security_tenant_alerts(tenant_id: str) -> list[JsonObject]:
        tenant_alerts: list[JsonObject] = []
        for alert in ai_security_alerts_memory[-200:]:
            raw_details = alert.get('details', {})
            details: JsonObject = cast(JsonObject, raw_details) if isinstance(raw_details, dict) else {}
            tenant_scope = str(details.get('tenant_id', '') or '')
            if tenant_scope in {'', tenant_id}:
                tenant_alerts.append(alert)
        return tenant_alerts

    def _require_super_admin_key(x_super_admin_key: str | None) -> None:
        expected = os.getenv('SUPER_ADMIN_API_KEY', '').strip()
        supplied = (x_super_admin_key or '').strip()
        if not expected:
            raise HTTPException(status_code=503, detail='SUPER_ADMIN_API_KEY is not configured.')
        if not supplied or not hmac.compare_digest(supplied, expected):
            raise HTTPException(status_code=401, detail='Invalid super admin key.')

    def _request_source_ip(request: Request) -> str:
        forwarded_for = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip()
        if forwarded_for:
            return forwarded_for
        return request.client.host if request.client and request.client.host else ''

    def _source_ip_allowed(source_ip: str, allowlist: list[str]) -> bool:
        try:
            ip_obj = ipaddress.ip_address(source_ip)
        except ValueError:
            return False

        for item in allowlist:
            candidate = item.strip()
            if not candidate:
                continue
            try:
                if '/' in candidate:
                    if ip_obj in ipaddress.ip_network(candidate, strict=False):
                        return True
                elif ip_obj == ipaddress.ip_address(candidate):
                    return True
            except ValueError:
                continue
        return False

    def _require_super_admin_access(request: Request, x_super_admin_key: str | None) -> None:
        _require_super_admin_key(x_super_admin_key)

        raw_allowlist = os.getenv('SUPER_ADMIN_ALLOWLIST', '').strip()
        allowlist = [item.strip() for item in raw_allowlist.split(',') if item.strip()]
        if is_production() and not allowlist:
            raise HTTPException(status_code=503, detail='SUPER_ADMIN_ALLOWLIST must be configured in production.')
        if not allowlist:
            return

        source_ip = _request_source_ip(request)
        if not source_ip or not _source_ip_allowed(source_ip, allowlist):
            raise HTTPException(status_code=403, detail='Source IP is not allowlisted for super admin access.')

    # ── Route handlers ──────────────────────────────────────────────────────────

    @router.post('/ai/gateway/generate', responses={
        403: {'description': 'Tenant blocked for AI misuse.'},
        422: {'description': 'Unsupported AI provider.'},
        503: {'description': 'Provider disabled by security policy.'},
    })
    def ai_gateway_generate(payload: AiGatewayGenerateRequest, auth: AuthDep, request: Request) -> JsonObject:  # NOSONAR
        """
        Generate AI response via configured provider with automatic failover.
        
        Strategy:
        1. If provider specified: use it (or fail)
        2. If provider='auto': use tier-based selection with fallback chain
        3. Track provider health for auto-adjustment
        4. Retry with fallback providers on failure (up to 3 attempts)
        """
        enforce_rate_limit(f'{auth.tenant_id}:ai:gateway', limit=120, window_seconds=60)
        blocked, until_ts = is_tenant_blocked(auth.tenant_id)
        if blocked:
            raise HTTPException(
                status_code=403,
                detail=f'Tenant is temporarily blocked for AI misuse until {until_ts}. Submit appeal via /ai/security/appeals.',
            )

        provider = payload.provider.lower().strip()
        created_at = datetime.now(UTC).isoformat()
        selected_model = payload.model
        max_attempts = 3 if provider == 'auto' else 1
        last_error = ''

        for attempt in range(1, max_attempts + 1):
            start_time = time.time()

            try:
                prepared = prepare_ai_gateway_attempt(payload, provider, selected_model, attempt < max_attempts)
                if prepared is None:
                    provider = 'auto'
                    continue

                provider, selected_model, scoped_payload = prepared
                output = invoke_ai_provider_generation(provider, scoped_payload, auth, created_at)
                latency_ms = (time.time() - start_time) * 1000
                update_provider_health(provider, True, latency_ms)
                record_ai_gateway_success(
                    output=output,
                    scoped_payload=scoped_payload,
                    provider=provider,
                    auth=auth,
                    request=request,
                )
                return output

            except HTTPException:
                raise
            except Exception as error:
                latency_ms = (time.time() - start_time) * 1000
                update_provider_health(provider, False, latency_ms)
                last_error = str(error)

                if attempt < max_attempts:
                    provider = 'auto'
                    continue

                raise HTTPException(
                    status_code=503,
                    detail=f'AI gateway unavailable. All providers failed. Last error: {last_error[:200]}',
                )

        raise HTTPException(status_code=503, detail='AI gateway unavailable. Please try again.')

    @router.get('/ai/generated-assets/{asset_id}', responses={
        404: {'description': 'Generated asset not found.'},
    })
    def ai_generated_asset_download(asset_id: int, auth: AuthDep) -> Response:
        enforce_rate_limit(f'{auth.tenant_id}:ai:asset-download', limit=240, window_seconds=60)

        with ai_generated_assets_lock:
            item = next(
                (
                    row
                    for row in ai_generated_assets_memory
                    if coerce_int(row.get('id'), 0) == asset_id and str(row.get('tenant_id', '')) == auth.tenant_id
                ),
                None,
            )

        if item is None:
            raise HTTPException(status_code=404, detail='Generated asset not found.')

        mime_type = str(item.get('mime_type', 'application/octet-stream') or 'application/octet-stream')
        file_name = str(item.get('file_name', f'asset-{asset_id}.bin') or f'asset-{asset_id}.bin')
        try:
            content = load_ai_generated_asset_bytes(item, asset_id, file_name)
        except Exception as ex:
            if isinstance(ex, HTTPException):
                raise
            raise HTTPException(status_code=404, detail=f'Generated asset is corrupted: {ex}') from ex

        return Response(
            content=content,
            media_type=mime_type,
            headers={'Content-Disposition': f'inline; filename="{file_name}"'},
        )

    @router.post('/ai/security/admin/provider-keys/rotate', responses={
        401: {'description': 'Invalid super admin key.'},
        403: {'description': 'Source IP is not allowlisted for super admin access.'},
        503: {'description': 'Super admin key not configured.'},
    })
    def ai_security_rotate_provider_key(
        request: Request,
        payload: AiSecurityRotateKeyRequest,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:
        _require_super_admin_access(request, x_super_admin_key)
        now_iso = datetime.now(UTC).isoformat()
        from ..transparent_encryption import te_encrypt
        cipher = te_encrypt(payload.api_key)

        with ai_security_lock:
            for item in ai_provider_keys_memory:
                if item.get('provider') == payload.provider and item.get('enabled') is True:
                    item['enabled'] = False
                    item['disabled_reason'] = 'rotated'
                    item['disabled_at'] = now_iso

            record: JsonObject = {
                'id': len(ai_provider_keys_memory) + 1,
                'provider': payload.provider,
                'label': payload.label or f'{payload.provider}-key',
                'api_key_cipher': cipher,
                'fingerprint': hashlib.sha256(payload.api_key.encode('utf-8')).hexdigest()[:12],
                'enabled': True,
                'created_at': now_iso,
            }
            ai_provider_keys_memory.append(record)

        alert = record_ai_security_alert('info', 'AI provider API key rotated', {'provider': payload.provider, 'label': record['label']})
        send_security_email_alert(alert)
        return {'status': 'ok', 'provider_key': {'provider': payload.provider, 'label': record['label'], 'fingerprint': record['fingerprint'], 'enabled': True}}

    @router.get('/ai/security/analytics')
    def ai_security_analytics(auth: AuthDep, window_minutes: int = 60) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:ai:security:analytics', limit=120, window_seconds=60)
        usage_window = _ai_security_usage_window(auth.tenant_id, window_minutes)
        blocked, until_ts = is_tenant_blocked(auth.tenant_id)
        total_calls = len(usage_window)
        success_calls = sum(1 for item in usage_window if item.get('status') == 'success')

        kpi: JsonObject = {
            'total_calls': total_calls,
            'success_calls': success_calls,
            'success_rate': round((success_calls / total_calls), 4) if total_calls else 0.0,
            'avg_roi': round(sum(coerce_float(item.get('roi', 0.0), 0.0) for item in usage_window) / total_calls, 6) if total_calls else 0.0,
            'avg_latency_ms': round(sum(coerce_float(item.get('latency_ms', 0), 0.0) for item in usage_window) / total_calls, 2) if total_calls else 0.0,
            'total_estimated_cost': round(sum(coerce_float(item.get('estimated_cost', 0.0), 0.0) for item in usage_window), 8),
            'total_estimated_value': round(sum(coerce_float(item.get('estimated_value', 0.0), 0.0) for item in usage_window), 8),
            'is_blocked': blocked,
            'blocked_until_ts': until_ts if blocked else 0,
        }

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'window_minutes': window_minutes,
            'kpi': kpi,
            'provider_graph': _ai_security_provider_graph(usage_window),
            'timeline': _ai_security_timeline(usage_window),
            'alerts': _ai_security_tenant_alerts(auth.tenant_id)[-20:],
        }

    @router.post('/ai/security/appeals')
    def ai_security_create_appeal(payload: AiSecurityAppealRequest, auth: AuthDep) -> JsonObject:
        enforce_rate_limit(f'{auth.tenant_id}:ai:security:appeal', limit=12, window_seconds=3600)
        now_iso = datetime.now(UTC).isoformat()
        appeal: JsonObject = {
            'id': len(ai_security_appeals_memory) + 1,
            'tenant_id': auth.tenant_id,
            'reason': payload.reason,
            'status': 'pending',
            'created_at': now_iso,
        }
        with ai_security_lock:
            ai_security_appeals_memory.append(appeal)
        alert = record_ai_security_alert('warning', 'AI block appeal created', {'tenant_id': auth.tenant_id, 'appeal_id': appeal['id']})
        send_security_email_alert(alert)
        return {'status': 'ok', 'appeal': appeal}

    @router.post('/ai/security/admin/appeals/{appeal_id}/resolve', responses={
        401: {'description': 'Invalid super admin key.'},
        403: {'description': 'Source IP is not allowlisted for super admin access.'},
        404: {'description': 'Appeal not found.'},
        503: {'description': 'Super admin key not configured.'},
    })
    def ai_security_resolve_appeal(
        request: Request,
        appeal_id: int,
        payload: AiSecurityAppealResolveRequest,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:
        _require_super_admin_access(request, x_super_admin_key)
        now_iso = datetime.now(UTC).isoformat()
        with ai_security_lock:
            appeal = next((item for item in ai_security_appeals_memory if coerce_int(item.get('id', 0), 0) == appeal_id), None)
            if appeal is None:
                raise HTTPException(status_code=404, detail='Appeal not found.')
            appeal['status'] = payload.decision
            appeal['resolved_at'] = now_iso
            appeal['notes'] = payload.notes or ''
            if payload.decision == 'approved':
                for block in ai_security_blocks_memory:
                    if block.get('tenant_id') == appeal.get('tenant_id') and block.get('active') is True:
                        block['active'] = False
                        block['resolved_at'] = now_iso

        alert = record_ai_security_alert('info', 'AI appeal resolved', {'appeal_id': appeal_id, 'decision': payload.decision})
        send_security_email_alert(alert)
        return {'status': 'ok', 'appeal': appeal}

    @router.post('/ai/security/admin/ids/events', responses={
        401: {'description': 'Invalid super admin key.'},
        403: {'description': 'Source IP is not allowlisted for super admin access.'},
        503: {'description': 'Super admin key not configured.'},
    })
    def ai_security_ingest_ids_event(
        request: Request,
        payload: AiSecurityIdseventRequest,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:
        _require_super_admin_access(request, x_super_admin_key)
        now_iso = datetime.now(UTC).isoformat()
        event: JsonObject = {
            'id': len(ai_security_ids_events_memory) + 1,
            'timestamp': int(time.time()),
            'source': payload.source,
            'severity': payload.severity,
            'rule_id': payload.rule_id,
            'message': payload.message,
            'tenant_id': payload.tenant_id or '',
            'provider': payload.provider or '',
            'ip_hash': hashlib.sha256((payload.ip_address or '').encode('utf-8')).hexdigest()[:16] if payload.ip_address else '',
            'action': payload.action,
            'created_at': now_iso,
        }
        with ai_security_lock:
            ai_security_ids_events_memory.append(event)
            if len(ai_security_ids_events_memory) > 10000:
                del ai_security_ids_events_memory[:-10000]

        if payload.action == 'block-tenant' and payload.tenant_id:
            block_tenant(payload.tenant_id, f'IDS/IPS event {payload.source}:{payload.rule_id}')
        elif payload.action == 'disable-provider' and payload.provider:
            disable_provider(payload.provider, f'IDS/IPS event {payload.source}:{payload.rule_id}')
        else:
            alert = record_ai_security_alert(
                'critical' if payload.severity in {'high', 'critical'} else 'warning',
                'IDS/IPS alert ingested',
                {
                    'source': payload.source,
                    'rule_id': payload.rule_id,
                    'tenant_id': payload.tenant_id or '',
                    'provider': payload.provider or '',
                    'action': payload.action,
                },
            )
            send_security_email_alert(alert)

        return {'status': 'ok', 'event': event}

    @router.get('/ai/security/admin/ids/state', responses={
        401: {'description': 'Invalid super admin key.'},
        403: {'description': 'Source IP is not allowlisted for super admin access.'},
        503: {'description': 'Super admin key not configured.'},
    })
    def ai_security_ids_state(
        request: Request,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
        window_minutes: int = 60,
    ) -> JsonObject:
        _require_super_admin_access(request, x_super_admin_key)
        now_ts = int(time.time())
        window_seconds = max(1, min(window_minutes, 24 * 60)) * 60
        window_events = [
            item for item in ai_security_ids_events_memory
            if coerce_int(item.get('id', 0), 0) > 0 and coerce_int(item.get('timestamp', now_ts), now_ts) >= (now_ts - window_seconds)
        ]
        if not window_events:
            window_events = ai_security_ids_events_memory[-500:]

        by_source: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        for item in window_events:
            source = str(item.get('source', 'unknown') or 'unknown')
            severity = str(item.get('severity', 'unknown') or 'unknown')
            by_source[source] = by_source.get(source, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1

        return {
            'status': 'ok',
            'window_minutes': window_minutes,
            'total_events': len(window_events),
            'by_source': by_source,
            'by_severity': by_severity,
            'security_email_delivery': security_alert_delivery_summary(),
            'recent_events': window_events[-100:],
            'active_blocks': [item for item in ai_security_blocks_memory if item.get('active') is True],
            'provider_keys': [
                {
                    'provider': item.get('provider', ''),
                    'label': item.get('label', ''),
                    'fingerprint': item.get('fingerprint', ''),
                    'enabled': bool(item.get('enabled')),
                }
                for item in ai_provider_keys_memory[-20:]
            ],
        }

    @router.get('/ai/security/admin/email-queue', responses={
        401: {'description': 'Invalid super admin key.'},
        403: {'description': 'Source IP is not allowlisted for super admin access.'},
        503: {'description': 'Super admin key not configured.'},
    })
    def ai_security_admin_email_queue(
        request: Request,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
        status: Literal['all', 'queued', 'sending', 'retry', 'sent', 'failed'] = 'failed',
        limit: int = 50,
        cursor_before_id: int = 0,
    ) -> JsonObject:
        _require_super_admin_access(request, x_super_admin_key)
        safe_limit = max(1, min(limit, 200))
        safe_cursor = max(0, cursor_before_id)

        fetch_size = safe_limit + 1
        db_items = db_security_alert_email_queue_items(status, fetch_size, safe_cursor) if security_alert_db_queue_enabled() else None
        items_raw = db_items if db_items is not None else memory_security_alert_email_queue_items(status, fetch_size, safe_cursor)
        items, has_more, next_cursor = paginate_email_queue_items(items_raw, safe_limit)
        queue_source = 'db' if db_items is not None else 'memory'

        return {
            'status': 'ok',
            'queue_source': queue_source,
            'filter_status': status,
            'limit': safe_limit,
            'cursor_before_id': safe_cursor,
            'has_more': has_more,
            'next_cursor_before_id': next_cursor,
            'count': len(items),
            'items': items,
        }

    @router.post('/ai/security/admin/email-queue/{message_id}/requeue', responses={
        401: {'description': 'Invalid super admin key.'},
        403: {'description': 'Source IP is not allowlisted for super admin access.'},
        404: {'description': 'Queue message not found.'},
        409: {'description': 'Only failed messages can be requeued.'},
        503: {'description': 'Super admin key not configured.'},
    })
    def ai_security_admin_requeue_email(
        request: Request,
        message_id: int,
        x_super_admin_key: Annotated[str | None, Header(alias='X-Super-Admin-Key')] = None,
    ) -> JsonObject:
        _require_super_admin_access(request, x_super_admin_key)
        if message_id <= 0:
            raise HTTPException(status_code=404, detail='Queue message not found.')

        source_ip = _request_source_ip(request)
        super_admin_fingerprint = hashlib.sha256((x_super_admin_key or '').encode('utf-8')).hexdigest()[:16]

        queue_source = 'memory'
        item: JsonObject | None
        if security_alert_db_queue_enabled():
            item = db_requeue_security_alert_email(message_id, super_admin_fingerprint, source_ip)
            queue_source = 'db'
        else:
            item = memory_requeue_security_alert_email(message_id, super_admin_fingerprint, source_ip)

        if item is None:
            if security_alert_db_queue_enabled():
                exists = db_security_alert_email_exists(message_id)
            else:
                exists = any(
                    raw.get('tenant_id') == 'platform-security' and coerce_int(raw.get('id', 0), 0) == message_id
                    for raw in resend_messages_memory
                )
            if exists:
                raise HTTPException(status_code=409, detail='Only failed messages can be requeued.')
            raise HTTPException(status_code=404, detail='Queue message not found.')

        alert = record_ai_security_alert('info', 'Security alert email requeued', {'message_id': message_id, 'queue_source': queue_source})
        send_security_email_alert(alert)
        return {'status': 'ok', 'queue_source': queue_source, 'item': item}

    return router
