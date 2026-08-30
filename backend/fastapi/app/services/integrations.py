"""
Third-Party Integration helper functions extracted from legacy_main.py.

Contains email providers (Listmonk, Postal, SES, Resend), webhook signature
validation (GitHub, Stripe, Generic), MinIO presigned URLs, and vault health checks.
"""

import hashlib
import hmac
import os
import smtplib
import ssl
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Annotated

import httpx
from fastapi import HTTPException

from ..ai_gateway import CONTENT_TYPE_JSON
from ..deps import AuthContext
from ..transparent_encryption import te_decrypt

JsonObject = dict[str, object]

DEFAULT_FROM_EMAIL = 'noreply@nuxtron.local'


# ── Email Provider Helpers ────────────────────────────────

def _send_via_listmonk(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    base_url = os.getenv('LISTMONK_URL', '').rstrip('/')
    token = os.getenv('LISTMONK_API_TOKEN', '')
    if not base_url or not token:
        return False, 'Listmonk not configured.'

    headers = {
        'Authorization': f'token {token}',
        'Content-Type': CONTENT_TYPE_JSON,
    }
    payload = {
        'subscriber_email': recipient_email,
        'subject': subject,
        'body': body,
        'content_type': 'html',
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/api/tx', headers=headers, json=payload)
            if response.is_success:
                return True, 'Delivered via Listmonk transactional API.'
            return False, f'Listmonk API error: {response.status_code}'
    except Exception as ex:
        return False, f'Listmonk request failed: {ex}'


def _send_via_postal(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    base_url = os.getenv('POSTAL_BASE_URL', '').rstrip('/')
    api_key = os.getenv('POSTAL_API_KEY', '')
    from_email = os.getenv('POSTAL_FROM_EMAIL', DEFAULT_FROM_EMAIL)
    if not base_url or not api_key:
        return False, 'Postal not configured.'

    headers = {
        'X-Server-API-Key': api_key,
        'Content-Type': CONTENT_TYPE_JSON,
    }
    payload = {
        'from': from_email,
        'to': recipient_email,
        'subject': subject,
        'plain_body': body,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(f'{base_url}/api/v1/send/message', headers=headers, json=payload)
            if response.is_success:
                return True, 'Delivered via Postal API.'
            return False, f'Postal API error: {response.status_code}'
    except Exception as ex:
        return False, f'Postal request failed: {ex}'


def _send_via_ses(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    host = os.getenv('SES_SMTP_HOST', '').strip()
    port = int(os.getenv('SES_SMTP_PORT', '587'))
    username = os.getenv('SES_SMTP_USERNAME', '').strip()
    password = os.getenv('SES_SMTP_PASSWORD', '').strip()
    from_email = os.getenv('SES_FROM_EMAIL', DEFAULT_FROM_EMAIL).strip()

    if not host or not username or not password:
        return False, 'SES SMTP not configured.'

    message = EmailMessage()
    message['From'] = from_email
    message['To'] = recipient_email
    message['Subject'] = subject
    message.set_content(body)

    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host=host, port=port, context=context, timeout=12) as server:
                server.login(username, password)
                server.send_message(message)
        else:
            with smtplib.SMTP(host=host, port=port, timeout=12) as server:
                server.starttls(context=context)
                server.login(username, password)
                server.send_message(message)
        return True, 'Delivered via SES SMTP.'
    except Exception as ex:
        return False, f'SES SMTP request failed: {ex}'


def _send_via_resend(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    api_base_url = os.getenv('RESEND_API_BASE_URL', 'https://api.resend.com').rstrip('/')
    from_email = os.getenv('RESEND_FROM_EMAIL', '').strip() or os.getenv('SMTP_FROM', '').strip() or DEFAULT_FROM_EMAIL
    if not api_key:
        return False, 'Resend not configured.'

    payload: dict[str, object] = {
        'from': from_email,
        'to': [recipient_email],
        'subject': subject,
        'text': body,
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                f'{api_base_url}/emails',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': CONTENT_TYPE_JSON,
                },
                json=payload,
            )
            if response.is_success:
                return True, 'Delivered via Resend.'
            return False, f'Resend API error: {response.status_code}'
    except Exception as ex:
        return False, f'Resend request failed: {ex}'


def _security_alert_from_email() -> str:
    for candidate in (
        os.getenv('SMTP_FROM', '').strip(),
        os.getenv('RESEND_FROM_EMAIL', '').strip(),
        os.getenv('SES_FROM_EMAIL', '').strip(),
        os.getenv('POSTAL_FROM_EMAIL', '').strip(),
    ):
        if candidate:
            return candidate
    return ''


def _dispatch_security_email(recipient_email: str, subject: str, body: str) -> tuple[bool, str, str]:
    last_detail = 'No configured email transport for security alerts.'
    for provider, sender in (
        ('resend', _send_via_resend),
        ('postal', _send_via_postal),
        ('ses', _send_via_ses),
        ('listmonk', _send_via_listmonk),
    ):
        success, detail = sender(recipient_email, subject, body)
        if success:
            return True, provider, detail
        last_detail = detail
        if 'not configured' not in detail.lower():
            return False, provider, detail
    return False, 'unavailable', last_detail


# ── Webhook Signature Validation ──────────────────────────

def _verify_github_signature(secret: str, raw_body: bytes, sig_header: str) -> bool:
    expected = 'sha256=' + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header)


def _verify_stripe_signature(secret: str, raw_body: bytes, sig_header: str) -> bool:
    parts = {kv.split('=', 1)[0]: kv.split('=', 1)[1] for kv in sig_header.split(',') if '=' in kv}
    timestamp = parts.get('t', '')
    v1 = parts.get('v1', '')
    signed = f'{timestamp}.'.encode() + raw_body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, v1)


def _ensure_signature_header(secret: str, sig_header: str, provider_name: str) -> None:
    if secret and not sig_header:
        raise HTTPException(
            status_code=400,
            detail=f'{provider_name} webhook signature header required when {provider_name.upper()} secret is set.',
        )


def _validate_github_webhook_signature(payload: object) -> bool | None:
    secret = os.getenv('WEBHOOK_GITHUB_SECRET', '').strip()
    sig_header = getattr(payload, 'signature', '') or ''
    _ensure_signature_header(secret, sig_header, 'GitHub')
    if secret and sig_header:
        raw = str(getattr(payload, 'payload', '')).encode()
        return _verify_github_signature(secret, raw, sig_header)
    return None


def _validate_stripe_webhook_signature(payload: object) -> bool | None:
    secret = os.getenv('WEBHOOK_STRIPE_SECRET', '').strip()
    sig_header = getattr(payload, 'signature', '') or ''
    _ensure_signature_header(secret, sig_header, 'Stripe')
    if secret and sig_header:
        raw = str(getattr(payload, 'payload', '')).encode()
        return _verify_stripe_signature(secret, raw, sig_header)
    return None


def _validate_generic_webhook_signature(payload: object) -> bool | None:
    secret = os.getenv('WEBHOOK_GENERIC_SECRET', '').strip()
    sig_header = getattr(payload, 'signature', '') or ''
    if secret and sig_header:
        raw = str(getattr(payload, 'payload', '')).encode()
        expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig_header)
    return None


def _validate_webhook_signature(provider_lower: str, payload: object) -> bool | None:
    if provider_lower == 'github':
        return _validate_github_webhook_signature(payload)
    if provider_lower == 'stripe':
        return _validate_stripe_webhook_signature(payload)
    if provider_lower == 'generic':
        return _validate_generic_webhook_signature(payload)
    return None


# ── MinIO Presigned URL Helpers ───────────────────────────

def _minio_hmac_sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def _minio_presign(
    endpoint: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    object_key: str,
    method: str,
    expires: int,
) -> str:
    """Generate an AWS-compatible presigned URL for MinIO (v4 query-string signing)."""
    import urllib.parse

    now = datetime.now(UTC)
    date_stamp = now.strftime('%Y%m%d')
    amz_date = now.strftime('%Y%m%dT%H%M%SZ')
    region = 'us-east-1'
    service = 's3'

    host = endpoint.replace('http://', '').replace('https://', '').rstrip('/')
    scheme = 'https' if endpoint.startswith('https') else 'http'
    canonical_uri = f'/{bucket}/{urllib.parse.quote(object_key, safe="")}'

    credential_scope = f'{date_stamp}/{region}/{service}/aws4_request'
    credential = f'{access_key}/{credential_scope}'

    canonical_query = '&'.join([
        'X-Amz-Algorithm=AWS4-HMAC-SHA256',
        f'X-Amz-Credential={urllib.parse.quote(credential, safe="")}',
        f'X-Amz-Date={amz_date}',
        f'X-Amz-Expires={expires}',
        'X-Amz-SignedHeaders=host',
    ])

    canonical_headers = f'host:{host}\n'
    canonical_request = '\n'.join([
        method, canonical_uri, canonical_query,
        canonical_headers, 'host', 'UNSIGNED-PAYLOAD',
    ])

    string_to_sign = '\n'.join([
        'AWS4-HMAC-SHA256', amz_date, credential_scope,
        hashlib.sha256(canonical_request.encode()).hexdigest(),
    ])

    signing_key = _minio_hmac_sign(
        _minio_hmac_sign(
            _minio_hmac_sign(
                _minio_hmac_sign(f'AWS4{secret_key}'.encode(), date_stamp),
                region,
            ),
            service,
        ),
        'aws4_request',
    )
    signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()

    return (
        f'{scheme}://{host}{canonical_uri}'
        f'?{canonical_query}&X-Amz-Signature={signature}'
    )


# ── Vault Health Check Helpers ────────────────────────────

def _hashicorp_vault_health() -> JsonObject:
    from .vault.hashicorp_vault import HashiCorpVaultClient
    client = HashiCorpVaultClient()
    ok = client.connect()
    return {
        'enabled': bool(ok),
        'backend': 'hashicorp-vault',
        'address': client.vault_addr,
    }


def _supabase_vault_health() -> JsonObject:
    from .vault.supabase_vault import SupabaseVaultClient
    client = SupabaseVaultClient()
    ok = bool(getattr(client, 'is_ready', False))
    return {
        'enabled': bool(ok),
        'backend': 'supabase-vault',
    }
