"""AI Gateway & Provider helper functions extracted from legacy_main.py."""

import base64
import hashlib
import hmac
import html
import io
import ipaddress
import json
import math
import os
import struct
import time
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import httpx
from fastapi import HTTPException, Request

from .. import memory_stores
from ..ai_gateway import (
    AI_MODEL_CATALOG,
    AI_PROVIDER_TIERS,
    AI_PROVIDERS,
    CONTENT_TYPE_JSON,
    GEMINI_FLASH_MODEL,
    IMAGE_GENERATION_MODEL,
    LLAMA_70B_MODEL,
    MIME_TYPE_MP3,
    MIME_TYPE_MP4,
    MIME_TYPE_PNG,
    MIME_TYPE_WAV,
)
from ..deps import AuthContext
from ..common_utils import (
    _is_production,
    _queue_security_alert_email,
    _security_alert_from_email,
)
from ..transparent_encryption import te_decrypt

# Local type alias
JsonObject = dict[str, object]

# Memory store aliases
_ai_security_usage_memory = memory_stores.ai_security_usage
_ai_security_alerts_memory = memory_stores.ai_security_alerts
_ai_security_blocks_memory = memory_stores.ai_security_blocks
_ai_provider_keys_memory = memory_stores.ai_provider_keys
_ai_gateway_memory = memory_stores.ai_gateway

# Local memory stores (not in memory_stores module)
_ai_generated_assets_memory: list[JsonObject] = []
_ai_generated_assets_lock = __import__('threading').Lock()

# Locks
_ai_security_lock = __import__('threading').Lock()

# Provider health tracking (in-memory, reset on restart)
_provider_health_metrics: dict[str, dict[str, float]] = {
    provider: {
        'success_rate': 1.0,
        'avg_latency_ms': 0.0,
        'last_error_at': 0,
        'consecutive_errors': 0,
        'requests_total': 0,
        'requests_success': 0,
        'updated_at': time.time(),
    }
    for provider in AI_PROVIDERS
}


# ── Provider Configuration ────────────────────────────────


def _provider_env_key(provider: str) -> str:
    if provider == 'openai':
        return os.getenv('OPENAI_API_KEY', '').strip()
    if provider == 'anthropic':
        return os.getenv('ANTHROPIC_API_KEY', '').strip()
    if provider == 'google_vertex':
        return os.getenv('GOOGLE_VERTEX_API_KEY', '').strip()
    if provider == 'cohere':
        return os.getenv('COHERE_API_KEY', '').strip()
    if provider == 'mistral':
        return os.getenv('MISTRAL_API_KEY', '').strip()
    if provider == 'together_ai':
        return os.getenv('TOGETHER_AI_API_KEY', '').strip()
    if provider == 'stability_ai':
        return os.getenv('STABILITY_AI_API_KEY', '').strip()
    return ''


def _provider_default_model(provider: str) -> str:
    if provider == 'openai':
        return os.getenv('OPENAI_MODEL', 'gpt-4o-mini').strip() or 'gpt-4o-mini'
    if provider == 'anthropic':
        return os.getenv('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest').strip() or 'claude-3-5-haiku-latest'
    if provider == 'google_vertex':
        return os.getenv('GOOGLE_VERTEX_MODEL', GEMINI_FLASH_MODEL).strip() or GEMINI_FLASH_MODEL
    if provider == 'cohere':
        return os.getenv('COHERE_MODEL', 'command-r').strip() or 'command-r'
    if provider == 'mistral':
        return os.getenv('MISTRAL_MODEL', 'mistral-large').strip() or 'mistral-large'
    if provider == 'together_ai':
        return os.getenv('TOGETHER_AI_MODEL', LLAMA_70B_MODEL).strip() or LLAMA_70B_MODEL
    if provider == 'stability_ai':
        return os.getenv('STABILITY_AI_MODEL', 'stable-diffusion-3').strip() or 'stable-diffusion-3'
    return ''


def _model_unit_cost(provider: str, model: str) -> float:
    provider_models = AI_MODEL_CATALOG.get(provider, {})
    model_meta = provider_models.get(model, {})
    value = model_meta.get('cost_per_1k_tokens', 0.002)
    return float(value if value > 0 else 0.002)


def _model_quality(provider: str, model: str) -> float:
    provider_models = AI_MODEL_CATALOG.get(provider, {})
    model_meta = provider_models.get(model, {})
    value = model_meta.get('quality_score', 0.8)
    return float(value if value > 0 else 0.8)


def _extract_ip_hash(request: Request) -> str:
    forwarded_for = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip()
    client_host = forwarded_for or (request.client.host if request.client else '')
    return hashlib.sha256(client_host.encode('utf-8')).hexdigest()[:16] if client_host else ''


def _extract_ua_hash(request: Request) -> str:
    ua = request.headers.get('User-Agent', '')
    return hashlib.sha256(ua.encode('utf-8')).hexdigest()[:16] if ua else ''


def _usage_to_tokens(usage: object) -> tuple[int, int, int]:
    usage_obj = cast(JsonObject, usage) if isinstance(usage, dict) else {}
    prompt_tokens = _coerce_int(usage_obj.get('prompt_tokens', 0), 0) + _coerce_int(usage_obj.get('input_tokens', 0), 0)
    completion_tokens = _coerce_int(usage_obj.get('completion_tokens', 0), 0) + _coerce_int(usage_obj.get('output_tokens', 0), 0)
    total_tokens = _coerce_int(usage_obj.get('total_tokens', 0), 0)
    if total_tokens <= 0:
        total_tokens = prompt_tokens + completion_tokens
    return prompt_tokens, completion_tokens, max(total_tokens, 0)


def _compute_roi(total_tokens: int, value_per_1k_tokens: float, cost_per_1k_tokens: float, quality_score: float) -> tuple[float, float, float]:
    token_units = max(total_tokens, 0) / 1000.0
    estimated_cost = token_units * max(cost_per_1k_tokens, 0.000001)
    estimated_value = token_units * max(value_per_1k_tokens, 0.000001) * max(quality_score, 0.01)
    if estimated_cost <= 0:
        return 0.0, estimated_cost, estimated_value
    roi = (estimated_value - estimated_cost) / estimated_cost
    return round(roi, 6), round(estimated_cost, 8), round(estimated_value, 8)


def _active_provider_key_record(provider: str) -> JsonObject | None:
    with _ai_security_lock:
        for item in reversed(_ai_provider_keys_memory):
            if item.get('provider') == provider and item.get('enabled') is True:
                return item
    return None


def _is_provider_disabled(provider: str) -> bool:
    with _ai_security_lock:
        for item in reversed(_ai_provider_keys_memory):
            if item.get('provider') == provider:
                enabled = bool(item.get('enabled'))
                return not enabled
    return False


def _resolve_provider_api_key(provider: str) -> str:
    record = _active_provider_key_record(provider)
    if record is not None:
        cipher = str(record.get('api_key_cipher', '') or '')
        secret = te_decrypt(cipher) or ''
        if secret:
            return secret
    return _provider_env_key(provider)


def _record_ai_security_alert(severity: str, title: str, details: JsonObject | None = None) -> JsonObject:
    now_iso = datetime.now(UTC).isoformat()
    event: JsonObject = {
        'id': len(_ai_security_alerts_memory) + 1,
        'severity': severity,
        'title': title,
        'details': details or {},
        'created_at': now_iso,
    }
    payload = json.dumps(event, sort_keys=True, separators=(',', ':'))
    prev_hash = str(_ai_security_alerts_memory[-1].get('chain_hash', 'genesis')) if _ai_security_alerts_memory else 'genesis'
    event['chain_hash'] = hashlib.sha256(f'{prev_hash}:{payload}'.encode()).hexdigest()
    with _ai_security_lock:
        _ai_security_alerts_memory.append(event)
        if len(_ai_security_alerts_memory) > 5000:
            del _ai_security_alerts_memory[:-5000]
    return event


def _send_security_email_alert(alert: JsonObject) -> None:
    security_to = os.getenv('SECURITY_ALERT_EMAIL', '').strip()
    from_email = _security_alert_from_email()
    if not (from_email and security_to):
        return

    severity = str(alert.get('severity', 'info') or 'info').upper()
    title = str(alert.get('title', '') or '')
    email_event: JsonObject = {
        'tenant_id': 'platform-security',
        'provider': 'smtp-queue',
        'to': security_to,
        'from': from_email,
        'subject': f'[Nuxtron AI Security] {severity} {title}',
        'body': json.dumps(alert, indent=2, sort_keys=True),
        'status': 'queued',
        'created_at': datetime.now(UTC).isoformat(),
    }
    _queue_security_alert_email(email_event)


def _block_tenant(tenant_id: str, reason: str, window_seconds: int = 1800) -> JsonObject:
    now_ts = int(time.time())
    until_ts = now_ts + max(window_seconds, 60)
    block: JsonObject = {
        'id': len(_ai_security_blocks_memory) + 1,
        'tenant_id': tenant_id,
        'reason': reason,
        'active': True,
        'created_at': datetime.now(UTC).isoformat(),
        'until_ts': until_ts,
        'type': 'tenant',
    }
    with _ai_security_lock:
        _ai_security_blocks_memory.append(block)
    alert = _record_ai_security_alert('critical', 'Tenant blocked for AI misuse', {'tenant_id': tenant_id, 'reason': reason, 'until_ts': until_ts})
    _send_security_email_alert(alert)
    return block


def _is_tenant_blocked(tenant_id: str) -> tuple[bool, int]:
    now_ts = int(time.time())
    with _ai_security_lock:
        for item in reversed(_ai_security_blocks_memory):
            if item.get('tenant_id') != tenant_id or item.get('active') is not True:
                continue
            until_ts = _coerce_int(item.get('until_ts', 0), 0)
            if until_ts > now_ts:
                return True, until_ts
            item['active'] = False
    return False, 0


def _disable_provider(provider: str, reason: str) -> None:
    now_iso = datetime.now(UTC).isoformat()
    with _ai_security_lock:
        disabled = False
        for item in reversed(_ai_provider_keys_memory):
            if item.get('provider') == provider and item.get('enabled') is True:
                item['enabled'] = False
                item['disabled_reason'] = reason
                item['disabled_at'] = now_iso
                disabled = True
                break
    if disabled:
        alert = _record_ai_security_alert('critical', 'Provider API disabled automatically', {'provider': provider, 'reason': reason})
        _send_security_email_alert(alert)


def _update_provider_health(provider: str, success: bool, latency_ms: float = 0) -> None:
    """Update provider health metrics for intelligent fallback."""
    with _ai_security_lock:
        metrics = _provider_health_metrics.get(provider, {})
        if not metrics:
            metrics = _provider_health_metrics[provider] = {
                'success_rate': 1.0,
                'avg_latency_ms': 0.0,
                'last_error_at': 0,
                'consecutive_errors': 0,
                'requests_total': 0,
                'requests_success': 0,
                'updated_at': time.time(),
            }
        
        metrics['requests_total'] = metrics.get('requests_total', 0) + 1
        if success:
            metrics['requests_success'] = metrics.get('requests_success', 0) + 1
            metrics['consecutive_errors'] = 0
            total = metrics.get('requests_total', 1)
            metrics['success_rate'] = metrics.get('requests_success', 0) / total
            # Exponential moving average for latency
            current_avg = metrics.get('avg_latency_ms', 0)
            metrics['avg_latency_ms'] = (current_avg * 0.7) + (latency_ms * 0.3)
        else:
            metrics['last_error_at'] = time.time()
            metrics['consecutive_errors'] = metrics.get('consecutive_errors', 0) + 1
            # Auto-disable if too many errors
            if metrics['consecutive_errors'] >= 5:
                _disable_provider(provider, f'Auto-disabled: {metrics["consecutive_errors"]} consecutive errors')
        
        metrics['updated_at'] = time.time()


def _get_provider_health(provider: str) -> dict[str, float]:
    """Get provider health metrics for intelligent selection."""
    with _ai_security_lock:
        return _provider_health_metrics.get(provider, {
            'success_rate': 1.0,
            'avg_latency_ms': 0.0,
            'consecutive_errors': 0,
        })


def _select_provider_with_tiers(payload: object, task_type: str = 'text_generation') -> tuple[str, str]:  # NOSONAR
    """
    Intelligent provider selection with automatic tier fallback.
    Tier 1: Primary (best quality)
    Tier 2: Secondary (good quality, cheaper)
    Tier 3: Tertiary (acceptable quality, budget-friendly)
    Tier 4: Emergency (always available fallback)
    """
    tiers = AI_PROVIDER_TIERS.get(task_type, AI_PROVIDER_TIERS['text_generation'])
    min_quality_floor = max(getattr(payload, 'quality_floor', 0), 0.70)  # Never go below 0.70 quality
    
    # Try each tier in order until we find a viable provider
    for tier_key in ['tier_1', 'tier_2', 'tier_3', 'tier_4']:
        tier_providers = tiers.get(tier_key, [])
        candidates: list[tuple[str, str, float, float]] = []  # (provider, model, score, health_score)
        
        for provider in tier_providers:
            if _is_provider_disabled(provider):
                continue
            
            # Check if API key is configured
            api_key = _resolve_provider_api_key(provider)
            if not api_key:
                continue
            
            model = getattr(payload, 'model', None) or _provider_default_model(provider)
            if not model or model not in AI_MODEL_CATALOG.get(provider, {}):
                continue
            
            quality = _model_quality(provider, model)
            if quality < min_quality_floor:
                continue  # Skip if quality doesn't meet minimum threshold
            
            cost = _model_unit_cost(provider, model)
            roi, _, _ = _compute_roi(max(getattr(payload, 'max_tokens', 1), 1), getattr(payload, 'value_per_1k_tokens', 0.01), cost, quality)
            
            # Health scoring: success_rate * (1 - normalized_latency)
            health = _get_provider_health(provider)
            success_rate = health.get('success_rate', 1.0)
            avg_latency_ms = health.get('avg_latency_ms', 0)
            uptime_percent = AI_MODEL_CATALOG[provider][model].get('uptime_percent', 99.5) / 100

            # Lightweight latency damping so very slow providers score lower.
            latency_penalty = min(max(float(avg_latency_ms), 0.0) / 10000.0, 0.25)
            
            # Combined score: (ROI + quality) * health_factor
            health_factor = success_rate * uptime_percent * (1.0 - latency_penalty)
            combined_score = (roi + quality) * health_factor
            
            candidates.append((provider, model, combined_score, health_factor))
        
        if candidates:
            # Sort by combined score (ROI + quality + health), prefer cheapest if tied on quality
            candidates.sort(key=lambda x: (-x[2], _model_unit_cost(x[0], x[1])))
            return candidates[0][0], candidates[0][1]
    
    # Absolute fallback: return first configured provider
    return 'openai', (getattr(payload, 'model', None) or _provider_default_model('openai'))


def _record_ai_usage(
    *,
    tenant_id: str,
    provider: str,
    model: str,
    request: Request,
    payload: object,
    result: JsonObject,
) -> JsonObject:
    usage = result.get('usage', {})
    prompt_tokens, completion_tokens, total_tokens = _usage_to_tokens(usage)
    if total_tokens <= 0:
        total_tokens = max(min(len(getattr(payload, 'prompt', '')) // 3, 4000), 1)

    quality = _model_quality(provider, model)
    unit_cost = _model_unit_cost(provider, model)
    roi, estimated_cost, estimated_value = _compute_roi(total_tokens, getattr(payload, 'value_per_1k_tokens', 0.01), unit_cost, quality)

    item: JsonObject = {
        'id': len(_ai_security_usage_memory) + 1,
        'created_at': datetime.now(UTC).isoformat(),
        'timestamp': int(time.time()),
        'tenant_id': tenant_id,
        'provider': provider,
        'model': model,
        'prompt_preview': getattr(payload, 'prompt', '')[:80],
        'ip_hash': _extract_ip_hash(request),
        'ua_hash': _extract_ua_hash(request),
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens': total_tokens,
        'estimated_cost': estimated_cost,
        'estimated_value': estimated_value,
        'roi': roi,
        'quality_score': quality,
        'latency_ms': _coerce_int(result.get('latency_ms', 0), 0),
        'status': 'success' if result.get('output_text') else 'degraded',
    }

    payload_str = json.dumps(item, sort_keys=True, separators=(',', ':'))
    prev_hash = str(_ai_security_usage_memory[-1].get('chain_hash', 'genesis')) if _ai_security_usage_memory else 'genesis'
    item['chain_hash'] = hashlib.sha256(f'{prev_hash}:{payload_str}'.encode()).hexdigest()

    with _ai_security_lock:
        _ai_security_usage_memory.append(item)
        if len(_ai_security_usage_memory) > 12000:
            del _ai_security_usage_memory[:-12000]

    return item


def _evaluate_ai_guardrails(tenant_id: str, provider: str, usage_item: JsonObject) -> None:
    now_ts = int(time.time())
    max_req_5m = int(os.getenv('AI_SECURITY_MAX_REQUESTS_5M', '120'))
    low_roi_floor = float(os.getenv('AI_SECURITY_LOW_ROI_FLOOR', '0.07'))

    recent_tenant = [
        item for item in _ai_security_usage_memory
        if item.get('tenant_id') == tenant_id and _coerce_int(item.get('timestamp', 0), 0) >= (now_ts - 300)
    ]
    if len(recent_tenant) > max_req_5m:
        _block_tenant(tenant_id, f'Burst traffic exceeded {max_req_5m} requests/5m')
        return

    provider_window = [
        item for item in _ai_security_usage_memory[-60:]
        if item.get('provider') == provider and item.get('status') == 'success'
    ]
    if provider_window:
        avg_roi = sum(_coerce_float(item.get('roi', 0.0), 0.0) for item in provider_window) / len(provider_window)
        if avg_roi < low_roi_floor:
            _disable_provider(provider, f'Average ROI {avg_roi:.4f} is below floor {low_roi_floor:.4f}')

    roi_now = _coerce_float(usage_item.get('roi', 0.0), 0.0)
    if roi_now < low_roi_floor:
        alert = _record_ai_security_alert(
            'warning',
            'Low ROI AI usage detected',
            {
                'tenant_id': tenant_id,
                'provider': provider,
                'roi': roi_now,
                'status': usage_item.get('status', ''),
            },
        )
        _send_security_email_alert(alert)


def _ai_queued_item(tenant_id: str, provider: str, model: str, prompt: str, reason: str = '', created_at: str = '') -> JsonObject:
    """Create a queued item for AI gateway."""
    if not created_at:
        created_at = datetime.now(UTC).isoformat()
    return {
        'id': len(_ai_gateway_memory) + 1,
        'tenant_id': tenant_id,
        'provider': provider,
        'model': model,
        'prompt_preview': prompt[:120],
        'status': 'queued' if not reason else f'queued-{reason}',
        'reason': reason or None,
        'created_at': created_at,
    }


def _json_object(value: object) -> JsonObject | None:
    return cast(JsonObject, value) if isinstance(value, dict) else None


def _coerce_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _coerce_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _extract_openai_result(data: object) -> tuple[str, object]:
    data_obj = _json_object(data)
    if data_obj is None:
        return '', {}

    usage = data_obj.get('usage', {})
    choices_value = data_obj.get('choices', [])
    if not isinstance(choices_value, list) or not choices_value:
        return '', usage
    choices_obj = cast(list[object], choices_value)

    first_choice = _json_object(choices_obj[0])
    if first_choice is None:
        return '', usage

    message = _json_object(first_choice.get('message', {}))
    if message is None:
        return '', usage

    content = message.get('content', '')
    return (content.strip(), usage) if isinstance(content, str) else ('', usage)


def _extract_anthropic_result(data: object) -> tuple[list[str], object]:
    data_obj = _json_object(data)
    if data_obj is None:
        return [], {}

    usage = data_obj.get('usage', {})
    blocks_value = data_obj.get('content', [])
    if not isinstance(blocks_value, list):
        return [], usage
    blocks_obj = cast(list[object], blocks_value)

    text_parts: list[str] = []
    for block_obj in blocks_obj:
        block = _json_object(block_obj)
        if block is None or block.get('type') != 'text':
            continue
        text = block.get('text', '')
        if isinstance(text, str) and text:
            text_parts.append(text)

    return text_parts, usage


def _ai_generate_openai(payload: object, auth: AuthContext, created_at: str) -> JsonObject:
    """Generate response via OpenAI API."""
    api_key = _resolve_provider_api_key('openai')
    model = getattr(payload, 'model', None) or os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

    if not api_key:
        item = _ai_queued_item(auth.tenant_id, 'openai', model, getattr(payload, 'prompt', ''), 'OpenAI not configured', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}

    messages: list[dict[str, str]] = []
    if getattr(payload, 'system_prompt', None):
        messages.append({'role': 'system', 'content': getattr(payload, 'system_prompt', '')})
    messages.append({'role': 'user', 'content': getattr(payload, 'prompt', '')})

    try:
        started = time.perf_counter()
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                'https://api.openai.com/v1/chat/completions',
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON},
                json={'model': model, 'messages': messages, 'temperature': getattr(payload, 'temperature', 0.7), 'max_tokens': getattr(payload, 'max_tokens', 1024)},
            )
            if response.is_success:
                text, usage = _extract_openai_result(response.json())
                latency_ms = round((time.perf_counter() - started) * 1000)
                return {'status': 'ok', 'result': {'tenant_id': auth.tenant_id, 'provider': 'openai', 'model': model, 'output_text': text, 'usage': usage, 'source': 'openai', 'latency_ms': latency_ms}}
    except Exception as ex:
        item = _ai_queued_item(auth.tenant_id, 'openai', model, getattr(payload, 'prompt', ''), f'error:{ex}', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}

    item = _ai_queued_item(auth.tenant_id, 'openai', model, getattr(payload, 'prompt', ''), 'non-success', created_at)
    _ai_gateway_memory.append(item)
    return {'status': 'ok', 'result': item}


def _ai_generate_anthropic(payload: object, auth: AuthContext, created_at: str) -> JsonObject:
    """Generate response via Anthropic API."""
    api_key = _resolve_provider_api_key('anthropic')
    model = getattr(payload, 'model', None) or os.getenv('ANTHROPIC_MODEL', 'claude-3-5-haiku-latest')

    if not api_key:
        item = _ai_queued_item(auth.tenant_id, 'anthropic', model, getattr(payload, 'prompt', ''), 'Anthropic not configured', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}

    body: JsonObject = {'model': model, 'max_tokens': getattr(payload, 'max_tokens', 1024), 'temperature': getattr(payload, 'temperature', 0.7), 'messages': [{'role': 'user', 'content': getattr(payload, 'prompt', '')}]}
    if getattr(payload, 'system_prompt', None):
        body['system'] = getattr(payload, 'system_prompt', '')

    try:
        started = time.perf_counter()
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                'https://api.anthropic.com/v1/messages',
                headers={'x-api-key': api_key, 'anthropic-version': '2023-06-01', 'Content-Type': CONTENT_TYPE_JSON},
                json=body,
            )
            if response.is_success:
                text_parts, usage = _extract_anthropic_result(response.json())
                latency_ms = round((time.perf_counter() - started) * 1000)
                return {'status': 'ok', 'result': {'tenant_id': auth.tenant_id, 'provider': 'anthropic', 'model': model, 'output_text': '\n'.join(text_parts).strip(), 'usage': usage, 'source': 'anthropic', 'latency_ms': latency_ms}}
    except Exception as ex:
        item = _ai_queued_item(auth.tenant_id, 'anthropic', model, getattr(payload, 'prompt', ''), f'error:{ex}', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}

    item = _ai_queued_item(auth.tenant_id, 'anthropic', model, getattr(payload, 'prompt', ''), 'non-success', created_at)
    _ai_gateway_memory.append(item)
    return {'status': 'ok', 'result': item}


def _ai_generate_google_vertex(payload: object, auth: AuthContext, created_at: str) -> JsonObject:  # NOSONAR
    """Generate response via Google Vertex AI API (text, image, video, voice).

    Auth: set GOOGLE_VERTEX_API_KEY to a short-lived OAuth2 access token obtained
    from a GCP service account (e.g. via `gcloud auth print-access-token` or the
    google-auth library). Plain API keys are NOT accepted by the Vertex AI endpoint.

    Required env vars:
        GOOGLE_VERTEX_API_KEY    — OAuth2 Bearer access token
        GOOGLE_VERTEX_PROJECT_ID — GCP project id (e.g. my-gcp-project-123)
        GOOGLE_VERTEX_MODEL      — model name, defaults to gemini-2.0-flash
        GOOGLE_VERTEX_LOCATION   — GCP region, defaults to us-central1
    """
    access_token = _resolve_provider_api_key('google_vertex')
    project_id = os.getenv('GOOGLE_VERTEX_PROJECT_ID', '').strip()
    model = getattr(payload, 'model', None) or os.getenv('GOOGLE_VERTEX_MODEL', GEMINI_FLASH_MODEL)
    location = os.getenv('GOOGLE_VERTEX_LOCATION', 'us-central1').strip() or 'us-central1'

    reason = _google_vertex_missing_reason(access_token, project_id)
    if reason is not None:
        item = _ai_queued_item(auth.tenant_id, 'google_vertex', model, getattr(payload, 'prompt', ''), reason, created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}

    body = _build_google_vertex_body(payload)

    try:
        started = time.perf_counter()
        url = (
            f'https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}'
            f'/locations/{location}/publishers/google/models/{model}:generateContent'
        )

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                headers={'Authorization': f'Bearer {access_token}', 'Content-Type': CONTENT_TYPE_JSON},
                json=body,
            )
            if response.is_success:
                return _build_google_vertex_success_result(response.json(), auth.tenant_id, model, started)

            error_detail = response.text[:300]
            item = _ai_queued_item(auth.tenant_id, 'google_vertex', model, getattr(payload, 'prompt', ''), f'http_{response.status_code}:{error_detail}', created_at)
            _ai_gateway_memory.append(item)
            return {'status': 'ok', 'result': item}
    except Exception as ex:
        item = _ai_queued_item(auth.tenant_id, 'google_vertex', model, getattr(payload, 'prompt', ''), f'error:{ex}', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}


def _google_vertex_missing_reason(access_token: str, project_id: str) -> str | None:
    missing: list[str] = []
    if not access_token:
        missing.append('GOOGLE_VERTEX_API_KEY')
    if not project_id:
        missing.append('GOOGLE_VERTEX_PROJECT_ID')
    if not missing:
        return None
    return f'Google Vertex not configured: missing {", ".join(missing)}'


def _build_google_vertex_body(payload: object) -> JsonObject:
    body: JsonObject = {
        'contents': [{
            'role': 'user',
            'parts': [{'text': getattr(payload, 'prompt', '')}],
        }],
        'generationConfig': {
            'temperature': getattr(payload, 'temperature', 0.7),
            'maxOutputTokens': getattr(payload, 'max_tokens', 1024),
        },
    }
    if getattr(payload, 'system_prompt', None):
        body['systemInstruction'] = {'parts': [{'text': getattr(payload, 'system_prompt', '')}]}
    return body


def _build_google_vertex_success_result(data: JsonObject, tenant_id: str, model: str, started: float) -> JsonObject:
    text_parts = _extract_google_vertex_text_parts(data)
    usage = _extract_google_vertex_usage(data)
    return {
        'status': 'ok',
        'result': {
            'tenant_id': tenant_id,
            'provider': 'google_vertex',
            'model': model,
            'output_text': '\n'.join(text_parts).strip() if text_parts else '',
            'usage': usage,
            'source': 'google_vertex',
            'latency_ms': round((time.perf_counter() - started) * 1000),
        },
    }


def _extract_google_vertex_text_parts(data: JsonObject) -> list[str]:
    text_parts: list[str] = []
    candidates = data.get('candidates')
    if not isinstance(candidates, list) or not candidates:
        return text_parts

    candidate = cast(list[object], candidates)[0]
    if not isinstance(candidate, dict):
        return text_parts

    content = candidate.get('content', {})
    parts = content.get('parts') if isinstance(content, dict) else None
    if not isinstance(parts, list):
        return text_parts

    for part in parts:
        if isinstance(part, dict) and isinstance(part.get('text'), str):
            text_parts.append(part['text'])
    return text_parts


def _extract_google_vertex_usage(data: JsonObject) -> JsonObject:
    usage_metadata = data.get('usageMetadata', {})
    if not isinstance(usage_metadata, dict):
        usage_metadata = {}
    return {
        'input_tokens': _coerce_int(usage_metadata.get('promptTokenCount', 0), 0),
        'output_tokens': _coerce_int(usage_metadata.get('candidatesTokenCount', 0), 0),
    }


def _generate_with_cohere(api_key: str, model: str, payload: object) -> tuple[str, JsonObject]:
    body: JsonObject = {'model': model, 'prompt': getattr(payload, 'prompt', ''), 'max_tokens': getattr(payload, 'max_tokens', 1024), 'temperature': getattr(payload, 'temperature', 0.7)}
    output_text = ''
    usage: JsonObject = {'input_tokens': 0, 'output_tokens': 0}
    with httpx.Client(timeout=30.0) as client:
        response = client.post('https://api.cohere.ai/v1/generate', headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON}, json=body)
        if response.is_success:
            data = response.json()
            if isinstance(data.get('generations'), list) and data['generations']:
                output_text = data['generations'][0].get('text', '')
            usage['output_tokens'] = _coerce_int(data.get('generations', [{}])[0].get('token_count', 0), 0)
    return output_text, usage


def _generate_with_mistral(api_key: str, model: str, payload: object) -> tuple[str, JsonObject]:
    body: JsonObject = {'model': model, 'messages': [{'role': 'user', 'content': getattr(payload, 'prompt', '')}], 'temperature': getattr(payload, 'temperature', 0.7), 'max_tokens': getattr(payload, 'max_tokens', 1024)}
    output_text = ''
    usage: JsonObject = {'input_tokens': 0, 'output_tokens': 0}
    with httpx.Client(timeout=30.0) as client:
        response = client.post('https://api.mistral.ai/v1/chat/completions', headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON}, json=body)
        if response.is_success:
            data = response.json()
            if isinstance(data.get('choices'), list) and data['choices']:
                output_text = data['choices'][0].get('message', {}).get('content', '')
            if isinstance(data.get('usage'), dict):
                usage = {'input_tokens': _coerce_int(data['usage'].get('prompt_tokens', 0), 0), 'output_tokens': _coerce_int(data['usage'].get('completion_tokens', 0), 0)}
    return output_text, usage


def _generate_with_together_ai(api_key: str, model: str, payload: object) -> tuple[str, JsonObject]:
    body: JsonObject = {'model': model, 'prompt': getattr(payload, 'prompt', ''), 'max_tokens': getattr(payload, 'max_tokens', 1024), 'temperature': getattr(payload, 'temperature', 0.7)}
    output_text = ''
    usage: JsonObject = {'input_tokens': 0, 'output_tokens': 0}
    with httpx.Client(timeout=30.0) as client:
        response = client.post('https://api.together.xyz/v1/completions', headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON}, json=body)
        if response.is_success:
            data = response.json()
            if isinstance(data.get('output'), list) and data['output']:
                output_text = data['output'][0] if isinstance(data['output'][0], str) else str(data['output'][0])
    return output_text, usage


def _generate_with_stability_ai(api_key: str, _model: str, payload: object) -> tuple[str, JsonObject]:
    body: JsonObject = {'text_prompts': [{'text': getattr(payload, 'prompt', ''), 'weight': 1}], 'height': 512, 'width': 512, 'steps': 30, 'cfg_scale': 7.0}
    output_text = ''
    usage: JsonObject = {'input_tokens': 0, 'output_tokens': 0}
    with httpx.Client(timeout=60.0) as client:
        response = client.post('https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image', headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON}, json=body)
        if response.is_success:
            data = response.json()
            if isinstance(data.get('artifacts'), list) and data['artifacts']:
                output_text = f'Generated {len(data["artifacts"])} image(s)'
    return output_text, usage


def _run_generic_provider_generation(provider: str, api_key: str, model: str, payload: object) -> tuple[str, JsonObject] | None:
    handlers = {
        'cohere': _generate_with_cohere,
        'mistral': _generate_with_mistral,
        'together_ai': _generate_with_together_ai,
        'stability_ai': _generate_with_stability_ai,
    }
    handler = handlers.get(provider)
    if handler is None:
        return None
    return handler(api_key, model, payload)


def _ai_generate_generic(provider: str, payload: object, auth: AuthContext, created_at: str) -> JsonObject:  # NOSONAR
    """Generic handler for Cohere, Mistral, Together.ai, Stability.ai."""
    api_key = _resolve_provider_api_key(provider)
    model = getattr(payload, 'model', None) or _provider_default_model(provider)
    if not api_key:
        item = _ai_queued_item(auth.tenant_id, provider, model, getattr(payload, 'prompt', ''), f'{provider} not configured', created_at)
        _ai_gateway_memory.append(item)
        return {'status': 'ok', 'result': item}
    try:
        started = time.perf_counter()
        generated = _run_generic_provider_generation(provider, api_key, model, payload)
        if generated is None:
            item = _ai_queued_item(auth.tenant_id, provider, model, getattr(payload, 'prompt', ''), 'unknown_provider', created_at)
            _ai_gateway_memory.append(item)
            return {'status': 'ok', 'result': item}
        output_text, usage = generated
        latency_ms = round((time.perf_counter() - started) * 1000)
        return {'status': 'ok', 'result': {'tenant_id': auth.tenant_id, 'provider': provider, 'model': model, 'output_text': output_text, 'usage': usage, 'source': provider, 'latency_ms': latency_ms}}
    except Exception as ex:
        item = _ai_queued_item(auth.tenant_id, provider, model, getattr(payload, 'prompt', ''), f'error:{str(ex)[:100]}', created_at)
        _ai_gateway_memory.append(item)
        raise


def _asset_extension_for_mime(mime_type: str) -> str:
    mapping = {
        MIME_TYPE_PNG: 'png',
        'image/jpeg': 'jpg',
        'image/webp': 'webp',
        'image/gif': 'gif',
        'image/svg+xml': 'svg',
        MIME_TYPE_MP3: 'mp3',
        MIME_TYPE_WAV: 'wav',
        MIME_TYPE_MP4: 'mp4',
    }
    return mapping.get(mime_type.lower().strip(), 'bin')


def _persist_ai_generated_asset(
    *,
    tenant_id: str,
    kind: str,
    mime_type: str,
    content: bytes,
    provider_used: str,
    generation_status: str,
) -> JsonObject:
    now_iso = datetime.now(UTC).isoformat()
    encoded = base64.b64encode(content).decode('ascii')
    ext = _asset_extension_for_mime(mime_type)
    storage_dir = Path(os.getenv('AI_GENERATED_ASSET_STORAGE_DIR', '') or (Path.cwd() / 'storage' / 'ai-generated-assets'))
    storage_dir.mkdir(parents=True, exist_ok=True)

    with _ai_generated_assets_lock:
        asset_id = len(_ai_generated_assets_memory) + 1
        file_path = storage_dir / f'{asset_id}.{ext}'
        try:
            file_path.write_bytes(content)
        except Exception:
            file_path = storage_dir / f'{kind}-{asset_id}.{ext}'
            file_path.write_bytes(content)
        item: JsonObject = {
            'id': asset_id,
            'tenant_id': tenant_id,
            'kind': kind,
            'mime_type': mime_type,
            'size_bytes': len(content),
            'provider_used': provider_used,
            'generation_status': generation_status,
            'content_base64': encoded,
            'created_at': now_iso,
            'file_name': f'{kind}-{asset_id}.{ext}',
            'download_url': f'/ai/generated-assets/{asset_id}',
            'file_path': str(file_path),
        }
        _ai_generated_assets_memory.append(item)
        if len(_ai_generated_assets_memory) > 2000:
            del _ai_generated_assets_memory[:500]

    return {
        'id': asset_id,
        'kind': kind,
        'mime_type': mime_type,
        'size_bytes': len(content),
        'provider_used': provider_used,
        'generation_status': generation_status,
        'file_name': f'{kind}-{asset_id}.{ext}',
        'download_url': f'/ai/generated-assets/{asset_id}',
    }


def _load_ai_generated_asset_bytes(item: JsonObject, asset_id: int, file_name: str) -> bytes:
    raw_b64 = str(item.get('content_base64', '') or '')
    if raw_b64:
        return base64.b64decode(raw_b64)

    file_path = str(item.get('file_path', '') or '')
    storage_dir = Path(os.getenv('AI_GENERATED_ASSET_STORAGE_DIR', '') or (Path.cwd() / 'storage' / 'ai-generated-assets'))
    if not file_path:
        candidate = storage_dir / file_name
        if candidate.exists():
            file_path = str(candidate)
        else:
            suffix = file_name.rsplit('.', 1)[-1] if '.' in file_name else 'bin'
            file_path = str(storage_dir / f'{asset_id}.{suffix}')

    candidate_path = Path(file_path)
    if not candidate_path.exists():
        raise HTTPException(status_code=404, detail='Generated asset payload is missing.')

    return candidate_path.read_bytes()


def _svg_image_placeholder_bytes(prompt: str) -> bytes:
    caption = html.escape(prompt.strip()[:180] or 'Generated creative')
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='1024' height='1024' viewBox='0 0 1024 1024'>"
        "<defs><linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0%' stop-color='#0f172a'/><stop offset='100%' stop-color='#0ea5a4'/></linearGradient></defs>"
        "<rect width='1024' height='1024' fill='url(#bg)'/>"
        "<rect x='72' y='72' width='880' height='880' rx='36' fill='rgba(255,255,255,0.08)' stroke='rgba(255,255,255,0.25)'/>"
        "<text x='96' y='180' fill='#f8fafc' font-size='44' font-family='Segoe UI, Arial, sans-serif'>Nuxtron AI Creative</text>"
        f"<text x='96' y='260' fill='#e2e8f0' font-size='28' font-family='Segoe UI, Arial, sans-serif'>{caption}</text>"
        "</svg>"
    )
    return svg.encode('utf-8')


def _try_generate_vertex_image(prompt: str) -> tuple[bytes, str] | None:
    access_token = _resolve_provider_api_key('google_vertex')
    project_id = os.getenv('GOOGLE_VERTEX_PROJECT_ID', '').strip()
    location = os.getenv('GOOGLE_VERTEX_LOCATION', 'us-central1').strip() or 'us-central1'
    model = os.getenv('GOOGLE_VERTEX_IMAGE_MODEL', IMAGE_GENERATION_MODEL).strip() or IMAGE_GENERATION_MODEL
    if not access_token or not project_id:
        return None

    url = (
        f'https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}'
        f'/locations/{location}/publishers/google/models/{model}:predict'
    )
    body: JsonObject = {
        'instances': [{'prompt': prompt}],
        'parameters': {
            'sampleCount': 1,
            'aspectRatio': '1:1',
        },
    }

    with httpx.Client(timeout=45.0) as client:
        response = client.post(
            url,
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': CONTENT_TYPE_JSON},
            json=body,
        )
        if not response.is_success:
            return None
        data = response.json()
        predictions = data.get('predictions')
        if not isinstance(predictions, list) or not predictions:
            return None
        first = predictions[0] if isinstance(predictions[0], dict) else {}
        raw_b64 = first.get('bytesBase64Encoded')
        if not isinstance(raw_b64, str) or not raw_b64:
            return None
        mime_raw = first.get('mimeType')
        mime = mime_raw if isinstance(mime_raw, str) and mime_raw else MIME_TYPE_PNG
        return base64.b64decode(raw_b64), mime


def _try_generate_stability_image(prompt: str) -> tuple[bytes, str] | None:
    api_key = _resolve_provider_api_key('stability_ai')
    if not api_key:
        return None

    body: JsonObject = {
        'text_prompts': [{'text': prompt, 'weight': 1}],
        'height': 1024,
        'width': 1024,
        'steps': 30,
        'cfg_scale': 7.0,
    }
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            'https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON},
            json=body,
        )
        if not response.is_success:
            return None
        data = response.json()
        artifacts = data.get('artifacts')
        if not isinstance(artifacts, list) or not artifacts:
            return None
        first = artifacts[0] if isinstance(artifacts[0], dict) else {}
        raw_b64 = first.get('base64')
        if not isinstance(raw_b64, str) or not raw_b64:
            return None
        return base64.b64decode(raw_b64), MIME_TYPE_PNG


def _ai_generate_image_binary(prompt: str, requested_provider: str) -> tuple[bytes, str, str, str]:
    provider = requested_provider.strip().lower()
    try:
        if provider in {'google_vertex', 'auto'}:
            vertex_result = _try_generate_vertex_image(prompt)
            if vertex_result is not None:
                return vertex_result[0], vertex_result[1], 'google_vertex', 'generated'
        if provider in {'stability_ai', 'auto'}:
            stability_result = _try_generate_stability_image(prompt)
            if stability_result is not None:
                return stability_result[0], stability_result[1], 'stability_ai', 'generated'
    except Exception:
        pass

    return _svg_image_placeholder_bytes(prompt), 'image/svg+xml', 'fallback', 'fallback'


def _try_generate_elevenlabs_voice(text: str) -> tuple[bytes, str] | None:
    api_key = os.getenv('ELEVENLABS_API_KEY', '').strip()
    voice_id = os.getenv('ELEVENLABS_VOICE_ID', '').strip() or 'EXAVITQu4vr4xnSDxMaL'
    if not api_key:
        return None

    body: JsonObject = {
        'text': text,
        'model_id': os.getenv('ELEVENLABS_MODEL_ID', 'eleven_multilingual_v2').strip() or 'eleven_multilingual_v2',
        'voice_settings': {'stability': 0.4, 'similarity_boost': 0.75},
    }
    with httpx.Client(timeout=45.0) as client:
        response = client.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
            headers={'xi-api-key': api_key, 'Accept': MIME_TYPE_MP3, 'Content-Type': CONTENT_TYPE_JSON},
            json=body,
        )
        if response.is_success and response.content:
            return response.content, MIME_TYPE_MP3
    return None


def _resolve_oss_voice_endpoints() -> list[tuple[str, str]]:
    preset = os.getenv('VOICE_PROVIDER_PRESET', 'local_oss_first').strip().lower()
    openvoice_url = os.getenv('OPENVOICE_API_URL', 'http://127.0.0.1:9011/v1/tts').strip()
    bark_url = os.getenv('BARK_API_URL', 'http://127.0.0.1:9012/v1/tts').strip()
    rvc_url = os.getenv('RVC_API_URL', 'http://127.0.0.1:9013/v1/tts').strip()

    ordered: list[tuple[str, str]] = [
        ('openvoice', openvoice_url),
        ('bark', bark_url),
        ('rvc', rvc_url),
    ]
    if preset in {'bark_first', 'bark'}:
        ordered = [('bark', bark_url), ('openvoice', openvoice_url), ('rvc', rvc_url)]
    elif preset in {'rvc_first', 'rvc'}:
        ordered = [('rvc', rvc_url), ('openvoice', openvoice_url), ('bark', bark_url)]

    return [(name, url) for name, url in ordered if url]


def _try_generate_oss_voice(text: str) -> tuple[bytes, str, str] | None:
    timeout_seconds = max(2, _coerce_int(os.getenv('VOICE_PROVIDER_TIMEOUT_SECONDS', '6'), 6))
    payload: JsonObject = {
        'text': text[:2000],
        'language': 'en',
    }

    for provider_name, url in _resolve_oss_voice_endpoints():
        try:
            with httpx.Client(timeout=float(timeout_seconds)) as client:
                response = client.post(url, headers={'Content-Type': CONTENT_TYPE_JSON}, json=payload)
                if not response.is_success or not response.content:
                    continue
                content_type = str(response.headers.get('content-type', MIME_TYPE_WAV) or MIME_TYPE_WAV)
                mime_type = content_type.split(';', 1)[0].strip() or MIME_TYPE_WAV
                return response.content, mime_type, provider_name
        except Exception:
            continue

    return None


def _select_replicate_video_model(prompt: str) -> str:
    default_model = os.getenv('REPLICATE_VIDEO_MODEL', '').strip() or 'kwaivgi/kling-v1.6-pro'
    low_cost_model = os.getenv('REPLICATE_VIDEO_MODEL_LOW_COST', '').strip() or default_model
    high_quality_model = os.getenv('REPLICATE_VIDEO_MODEL_HIGH_QUALITY', '').strip() or default_model
    preset = os.getenv('REPLICATE_VIDEO_MODEL_PRESET', 'balanced').strip().lower()

    if preset in {'cost', 'low', 'cheap'}:
        return low_cost_model
    if preset in {'quality', 'high', 'premium'}:
        return high_quality_model

    normalized = prompt.lower()
    quality_keywords = {
        'cinematic',
        'luxury',
        'high fidelity',
        'brand film',
        'photoreal',
        'studio quality',
    }
    low_cost_keywords = {
        'short',
        'reel',
        'quick ad',
        'test variant',
        'ab test',
        'draft',
    }

    if any(keyword in normalized for keyword in quality_keywords):
        return high_quality_model
    if any(keyword in normalized for keyword in low_cost_keywords):
        return low_cost_model
    return default_model


def _synth_voice_wave_bytes(text: str) -> bytes:
    sample_rate = 16000
    max_chars = 220
    source = (text.strip() or 'nuxtron voice asset')[:max_chars]

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames: list[bytes] = []
        volume = 0.25
        tone_duration = 0.045
        gap_duration = 0.015

        for char in source:
            frequency = 180 + (ord(char) % 50) * 8
            sample_count = int(sample_rate * tone_duration)
            for i in range(sample_count):
                sample = int(volume * 32767 * math.sin(2 * math.pi * frequency * (i / sample_rate)))
                frames.append(struct.pack('<h', sample))
            for _ in range(int(sample_rate * gap_duration)):
                frames.append(struct.pack('<h', 0))

        wav_file.writeframes(b''.join(frames))

    return buf.getvalue()


def _ai_generate_voice_binary(text: str) -> tuple[bytes, str, str, str]:
    try:
        oss_voice = _try_generate_oss_voice(text)
        if oss_voice is not None:
            return oss_voice[0], oss_voice[1], oss_voice[2], 'generated'
    except Exception:
        pass

    try:
        elevenlabs = _try_generate_elevenlabs_voice(text)
        if elevenlabs is not None:
            return elevenlabs[0], elevenlabs[1], 'elevenlabs', 'generated'
    except Exception:
        pass

    return _synth_voice_wave_bytes(text), MIME_TYPE_WAV, 'fallback', 'fallback'


def _try_generate_replicate_video(prompt: str) -> tuple[bytes, str] | None:  # NOSONAR
    token = os.getenv('REPLICATE_API_TOKEN', '').strip()
    model = _select_replicate_video_model(prompt)
    timeout_seconds = _coerce_int(os.getenv('REPLICATE_VIDEO_TIMEOUT_SECONDS', '120'), 120)
    if not token:
        return None

    start_body: JsonObject = {
        'model': model,
        'input': {
            'prompt': prompt[:800],
            'duration': 5,
            'aspect_ratio': '9:16',
        },
    }
    headers = {
        'Authorization': f'Token {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }

    with httpx.Client(timeout=30.0) as client:
        get_url = _start_replicate_prediction(client, headers, start_body)
        if get_url is None:
            return None

        deadline = time.time() + max(15, min(timeout_seconds, 300))
        while time.time() < deadline:
            prediction = _poll_replicate_prediction(client, headers, get_url)
            if prediction is None:
                return None
            status = str(prediction.get('status', '') or '')
            if status in {'starting', 'processing'}:
                time.sleep(1.5)
                continue
            if status != 'succeeded':
                return None

            output_url = _extract_replicate_output_url(prediction)
            if not output_url:
                return None

            return _download_replicate_video(client, output_url)

    return None


def _start_replicate_prediction(client: httpx.Client, headers: dict[str, str], start_body: JsonObject) -> str | None:
    start_response = client.post('https://api.replicate.com/v1/predictions', headers=headers, json=start_body)
    if not start_response.is_success:
        return None

    start_data = start_response.json()
    get_url = start_data.get('urls', {}).get('get') if isinstance(start_data.get('urls'), dict) else None
    if not isinstance(get_url, str) or not get_url:
        return None
    return get_url


def _poll_replicate_prediction(client: httpx.Client, headers: dict[str, str], get_url: str) -> JsonObject | None:
    poll = client.get(get_url, headers=headers)
    if not poll.is_success:
        return None
    return cast(JsonObject, poll.json())


def _extract_replicate_output_url(prediction: JsonObject) -> str:
    output = prediction.get('output')
    if isinstance(output, str):
        return output
    if isinstance(output, list) and output and isinstance(output[0], str):
        return output[0]
    return ''


def _download_replicate_video(client: httpx.Client, output_url: str) -> tuple[bytes, str] | None:
    video_response = client.get(output_url)
    if not video_response.is_success or not video_response.content:
        return None

    content_type = str(video_response.headers.get('content-type', MIME_TYPE_MP4) or MIME_TYPE_MP4)
    mime_type = content_type.split(';', 1)[0].strip() or MIME_TYPE_MP4
    return video_response.content, mime_type


def _placeholder_video_gif_bytes() -> bytes:
    # Tiny GIF binary fallback so UI can always render a downloadable "video-like" asset.
    return (
        b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01'
        b'\x0a\x00\x01\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02L\x01\x00;'
    )


def _ai_generate_video_binary(_prompt: str) -> tuple[bytes, str, str, str]:
    prompt = _prompt.strip()[:1200] or 'Create a short, engaging product reel with clear hook and CTA.'

    try:
        replicate_video = _try_generate_replicate_video(prompt)
        if replicate_video is not None:
            return replicate_video[0], replicate_video[1], 'replicate', 'generated'
    except Exception:
        pass

    return _placeholder_video_gif_bytes(), 'image/gif', 'fallback', 'fallback'


def _generate_media_asset_bundle(
    *,
    tenant_id: str,
    prompt: str,
    text_seed: str,
    requested_provider: str,
) -> JsonObject:
    image_bytes, image_mime, image_provider, image_status = _ai_generate_image_binary(prompt, requested_provider)
    voice_bytes, voice_mime, voice_provider, voice_status = _ai_generate_voice_binary(text_seed)
    video_bytes, video_mime, video_provider, video_status = _ai_generate_video_binary(prompt)

    image_asset = _persist_ai_generated_asset(
        tenant_id=tenant_id,
        kind='image',
        mime_type=image_mime,
        content=image_bytes,
        provider_used=image_provider,
        generation_status=image_status,
    )
    voice_asset = _persist_ai_generated_asset(
        tenant_id=tenant_id,
        kind='voice',
        mime_type=voice_mime,
        content=voice_bytes,
        provider_used=voice_provider,
        generation_status=voice_status,
    )
    video_asset = _persist_ai_generated_asset(
        tenant_id=tenant_id,
        kind='video',
        mime_type=video_mime,
        content=video_bytes,
        provider_used=video_provider,
        generation_status=video_status,
    )

    return {
        'image': image_asset,
        'voice': voice_asset,
        'video': video_asset,
    }


def _invoke_ai_provider_generation(
    provider: str,
    payload: object,
    auth: AuthContext,
    created_at: str,
) -> JsonObject:
    if provider == 'openai':
        return _ai_generate_openai(payload, auth, created_at)
    if provider == 'anthropic':
        return _ai_generate_anthropic(payload, auth, created_at)
    if provider == 'google_vertex':
        return _ai_generate_google_vertex(payload, auth, created_at)
    return _ai_generate_generic(provider, payload, auth, created_at)


def _extract_ai_result(output: JsonObject) -> tuple[JsonObject, str]:
    result = cast(JsonObject, output.get('result', {})) if isinstance(output.get('result', {}), dict) else {}
    output_text = str(result.get('output_text', '') or '').strip()
    return result, output_text


def _prepare_ai_gateway_attempt(
    payload: object,
    provider: str,
    selected_model: str,
    can_retry: bool,
) -> tuple[str, str, object] | None:
    resolved_provider = provider
    resolved_model = selected_model
    if resolved_provider == 'auto':
        resolved_provider, resolved_model = _select_provider_with_tiers(payload, 'text_generation')

    if resolved_provider not in AI_PROVIDERS:
        raise HTTPException(status_code=422, detail='Unsupported AI provider.')

    if _is_provider_disabled(resolved_provider):
        if can_retry:
            return None
        raise HTTPException(status_code=503, detail=f'Provider {resolved_provider} is disabled. No fallbacks available.')

    if not _resolve_provider_api_key(resolved_provider):
        if can_retry:
            return None
        raise HTTPException(status_code=503, detail=f'No API key configured for {resolved_provider}. No fallbacks available.')

    scoped_payload = payload.model_copy(update={'provider': resolved_provider, 'model': resolved_model})
    return resolved_provider, resolved_model, scoped_payload


def _record_ai_gateway_success(
    *,
    output: JsonObject,
    scoped_payload: object,
    provider: str,
    auth: AuthContext,
    request: Request,
) -> None:
    result, _ = _extract_ai_result(output)
    model_used = str(result.get('model', '') or getattr(scoped_payload, 'model', None) or _provider_default_model(provider))
    usage_item = _record_ai_usage(
        tenant_id=auth.tenant_id,
        provider=provider,
        model=model_used,
        request=request,
        payload=scoped_payload,
        result=result,
    )
    _evaluate_ai_guardrails(auth.tenant_id, provider, usage_item)


def _run_optional_ai_generation(
    payload: object,
    auth: AuthContext,
    created_at: str,
) -> tuple[str, str, JsonObject, str]:
    selected_provider: str = getattr(payload, 'provider', '') or ''
    selected_model = str(getattr(payload, 'model', None) or '')
    if selected_provider == 'auto':
        selected_provider, selected_model = _select_provider_with_tiers(payload, 'text_generation')

    scoped_payload = payload.model_copy(update={'provider': selected_provider, 'model': selected_model})

    try:
        output = _invoke_ai_provider_generation(selected_provider, scoped_payload, auth, created_at)
        ai_result, ai_text = _extract_ai_result(output)
        return selected_provider, selected_model, ai_result, ai_text
    except Exception:
        return selected_provider, selected_model, {}, ''


# ── Super Admin Access ────────────────────────────────────


from ..security_admin import (
    require_super_admin_access as _require_super_admin_access,
    require_super_admin_key as _require_super_admin_key,
    request_source_ip as _request_source_ip,
    source_ip_allowed as _source_ip_allowed,
)


# ── Security Analytics ────────────────────────────────────


def _ai_security_usage_window(tenant_id: str, window_minutes: int) -> list[JsonObject]:
    now_ts = int(time.time())
    window_seconds = max(1, min(window_minutes, 24 * 60)) * 60
    return [
        item for item in _ai_security_usage_memory
        if item.get('tenant_id') == tenant_id and _coerce_int(item.get('timestamp', 0), 0) >= (now_ts - window_seconds)
    ]


def _ai_security_provider_graph(usage_window: list[JsonObject]) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for provider in AI_PROVIDERS:
        provider_items = [item for item in usage_window if item.get('provider') == provider]
        provider_calls = len(provider_items)
        provider_roi = round(sum(_coerce_float(item.get('roi', 0.0), 0.0) for item in provider_items) / provider_calls, 6) if provider_calls else 0.0
        disabled = _is_provider_disabled(provider)
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
    for alert in _ai_security_alerts_memory[-200:]:
        raw_details = alert.get('details', {})
        details: JsonObject = cast(JsonObject, raw_details) if isinstance(raw_details, dict) else {}
        tenant_scope = str(details.get('tenant_id', '') or '')
        if tenant_scope in {'', tenant_id}:
            tenant_alerts.append(alert)
    return tenant_alerts
