"""Email Campaigns Service

Extracted from legacy_main.py: Email contacts, campaigns, test sending.
"""

from __future__ import annotations

import os
from fastapi import Depends
from datetime import UTC, datetime
from typing import Annotated, TYPE_CHECKING, Literal

import httpx
import psycopg

if TYPE_CHECKING:
    from ..deps import AuthContext

JsonObject = dict[str, object]
from ..deps import AuthContext, require_auth
AuthDep = Annotated[AuthContext, Depends(require_auth)]


CONTENT_TYPE_JSON = 'application/json'

# ── Memory Store References (set by legacy_main.py) ──────────
_email_contacts_memory = []
_email_campaigns_memory = []
_security_alert_emails_memory = []
_rate_buckets = {}
_rate_lock = None
from ..rate_limiter import enforce_rate_limit as _enforce_rate_limit  # default; may be overwritten by set_memory_stores
_db_ready = False
_db_dsn_fn = None
_te_encrypt = None
_te_decrypt = None
_coerce_int = int


def set_memory_stores(
    email_contacts_memory=None,
    email_campaigns_memory=None,
    security_alert_emails_memory=None,
    rate_buckets=None,
    rate_lock=None,
    enforce_rate_limit=None,
    db_ready=None,
    db_dsn_fn=None,
    te_encrypt=None,
    te_decrypt=None,
    coerce_int=None,
) -> None:
    global _email_contacts_memory, _email_campaigns_memory, _security_alert_emails_memory
    global _rate_buckets, _rate_lock, _enforce_rate_limit
    global _db_ready, _db_dsn_fn, _te_encrypt, _te_decrypt, _coerce_int
    if email_contacts_memory is not None:
        _email_contacts_memory = email_contacts_memory
    if email_campaigns_memory is not None:
        _email_campaigns_memory = email_campaigns_memory
    if security_alert_emails_memory is not None:
        _security_alert_emails_memory = security_alert_emails_memory
    if rate_buckets is not None:
        _rate_buckets = rate_buckets
    if rate_lock is not None:
        _rate_lock = rate_lock
    if enforce_rate_limit is not None:
        _enforce_rate_limit = enforce_rate_limit
    if db_ready is not None:
        _db_ready = db_ready
    if db_dsn_fn is not None:
        _db_dsn_fn = db_dsn_fn
    if te_encrypt is not None:
        _te_encrypt = te_encrypt
    if te_decrypt is not None:
        _te_decrypt = te_decrypt
    if coerce_int is not None:
        _coerce_int = coerce_int


# ── Email Providers (copied from integrations) ────────────────


def _send_via_listmonk(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    base_url = os.getenv('LISTMONK_URL', '').rstrip('/')
    token = os.getenv('LISTMONK_API_TOKEN', '')
    if not base_url or not token:
        return False, 'listmonk not configured'
    try:
        with httpx.Client(timeout=12.0) as client:
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': CONTENT_TYPE_JSON}
            resp = client.post(f'{base_url}/api/tx', json={'email': recipient_email, 'subject': subject, 'body': body}, headers=headers)
            if resp.is_success:
                return True, 'sent'
            return False, f'listmonk error: {resp.status_code} {resp.text[:120]}'
    except Exception as ex:
        return False, f'listmonk exception: {ex}'


def _send_via_postal(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    base_url = os.getenv('POSTAL_BASE_URL', '').rstrip('/')
    token = os.getenv('POSTAL_API_KEY', '')
    if not base_url or not token:
        return False, 'postal not configured'
    try:
        with httpx.Client(timeout=12.0) as client:
            headers = {'X-Server-API-Key': token, 'Content-Type': CONTENT_TYPE_JSON}
            resp = client.post(f'{base_url}/messages', json={'to': [{'email': recipient_email}], 'subject': subject, 'html_body': body}, headers=headers)
            if resp.is_success:
                return True, 'sent'
            return False, f'postal error: {resp.status_code} {resp.text[:120]}'
    except Exception as ex:
        return False, f'postal exception: {ex}'


def _send_via_ses(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    from botocore.config import Config
    import boto3
    ses_host = os.getenv('SES_SMTP_HOST', '').strip()
    access_key = os.getenv('AWS_ACCESS_KEY_ID', '').strip()
    secret_key = os.getenv('AWS_SECRET_ACCESS_KEY', '').strip()
    region = os.getenv('AWS_REGION', 'us-east-1').strip()
    from_email = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@nuxtron.local')
    if not ses_host or not access_key or not secret_key:
        return False, 'SES not configured'
    try:
        client = boto3.client('ses', endpoint_url=f'https://{ses_host}', region_name=region, aws_access_key_id=access_key, aws_secret_access_key=secret_key, config=Config(retries={'max_attempts': 2}))
        client.send_email(Source=from_email, Destination={'ToAddresses': [recipient_email]}, Message={'Subject': {'Data': subject}, 'Body': {'Html': {'Data': body}}})
        return True, 'sent'
    except Exception as ex:
        return False, f'SES exception: {ex}'


def _send_via_resend(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    from_email = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@nuxtron.local')
    if not api_key:
        return False, 'resend not configured'
    try:
        with httpx.Client(timeout=12.0) as client:
            headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': CONTENT_TYPE_JSON}
            resp = client.post('https://api.resend.com/emails', json={'from': from_email, 'to': [recipient_email], 'subject': subject, 'html': body}, headers=headers)
            if resp.is_success:
                return True, 'sent'
            return False, f'resend error: {resp.status_code} {resp.text[:120]}'
    except Exception as ex:
        return False, f'resend exception: {ex}'


def _security_alert_from_email() -> str:
    return os.getenv('SECURITY_ALERT_FROM_EMAIL', 'noreply@nuxtron.local')


def _dispatch_security_email(provider: str, to_email: str, subject: str, body: str) -> tuple[bool, str]:
    if provider == 'postal':
        return _send_via_postal(to_email, subject, body)
    if provider == 'ses':
        return _send_via_ses(to_email, subject, body)
    return _send_via_listmonk(to_email, subject, body)


# ── Email Contacts ────────────────────────────────────────────


def create_email_contact(payload: EmailContactCreateRequest, auth: AuthDep) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:email:contacts:create', limit=120, window_seconds=60)
    email_cipher = _te_encrypt(payload.email)
    name_cipher = _te_encrypt(payload.name)
    email_preview = payload.email[:4] + '***'
    name_preview = payload.name[:1] + '***'

    if _db_ready:
        with psycopg.connect(_db_dsn_fn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO email_contacts (tenant_id, email_cipher, email_preview, name_cipher, name_preview, tags)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (auth.tenant_id, email_cipher, email_preview, name_cipher, name_preview, payload.tags),
                )
                row = cur.fetchone()
                new_id = row[0] if row else len(_email_contacts_memory) + 1
            conn.commit()
    else:
        new_id = len(_email_contacts_memory) + 1

    item: JsonObject = {
        'id': new_id,
        'tenant_id': auth.tenant_id,
        'email': payload.email,
        'email_cipher': email_cipher,
        'name': payload.name,
        'name_cipher': name_cipher,
        'tags': payload.tags,
        'created_at': datetime.now(UTC).isoformat(),
        'persistence': 'postgres' if _db_ready else 'memory-fallback',
        'encryption': 'application-level',
    }
    _email_contacts_memory.append(item)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'contact': item}


def list_email_contacts(auth: AuthDep) -> JsonObject:
    items: list[JsonObject] = [c for c in _email_contacts_memory if c.get('tenant_id') == auth.tenant_id]
    for c in items:
        c['email'] = _te_decrypt(c.get('email_cipher', '')) or c.get('email_preview', '***')
        c['name'] = _te_decrypt(c.get('name_cipher', '')) or c.get('name_preview', '***')
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'contacts': items}


# ── Email Campaigns ──────────────────────────────────────────


def create_email_campaign(payload: EmailCampaignCreateRequest, auth: AuthDep) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:email:campaigns:create', limit=60, window_seconds=60)
    subject_cipher = _te_encrypt(payload.subject)
    body_cipher = _te_encrypt(payload.body)
    subject_preview = payload.subject[:50] + ('...' if len(payload.subject) > 50 else '')
    body_preview = payload.body[:100] + ('...' if len(payload.body) > 100 else '')

    if _db_ready:
        with psycopg.connect(_db_dsn_fn()) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO email_campaigns (tenant_id, subject_cipher, subject_preview, body_cipher, status, provider)
                    VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (auth.tenant_id, subject_cipher, subject_preview, body_cipher, 'draft', payload.provider),
                )
                row = cur.fetchone()
                new_id = row[0] if row else len(_email_campaigns_memory) + 1
            conn.commit()
    else:
        new_id = len(_email_campaigns_memory) + 1

    item: JsonObject = {
        'id': new_id,
        'tenant_id': auth.tenant_id,
        'subject': payload.subject,
        'subject_cipher': subject_cipher,
        'subject_preview': subject_preview,
        'body': payload.body,
        'body_cipher': body_cipher,
        'status': 'draft',
        'provider': payload.provider,
        'created_at': datetime.now(UTC).isoformat(),
        'persistence': 'postgres' if _db_ready else 'memory-fallback',
        'encryption': 'application-level',
    }
    _email_campaigns_memory.append(item)
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'campaign': item}


def list_email_campaigns(auth: AuthDep) -> JsonObject:
    items: list[JsonObject] = [c for c in _email_campaigns_memory if c.get('tenant_id') == auth.tenant_id]
    for c in items:
        c['subject'] = _te_decrypt(c.get('subject_cipher', '')) or c.get('subject_preview', '***')
        c['body'] = _te_decrypt(c.get('body_cipher', '')) or c.get('body_preview', '***')
    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'count': len(items), 'campaigns': items}


def send_test_email_campaign(payload: EmailCampaignSendTestRequest, auth: AuthDep) -> JsonObject:
    _enforce_rate_limit(f'{auth.tenant_id}:email:campaigns:send-test', limit=20, window_seconds=60)

    provider, subject, body = _resolve_campaign_test_payload(payload.campaign_id, auth.tenant_id)
    ok, message = _dispatch_test_email(provider, payload.recipient_email, subject, body)

    return {'status': 'ok', 'tenant_id': auth.tenant_id, 'sent': ok, 'message': message, 'provider': provider}


def _resolve_campaign_test_payload(campaign_id: int, tenant_id: str) -> tuple[str, str, str]:
    provider = os.getenv('EMAIL_PROVIDER', 'listmonk')
    subject = f'Nuxtron Campaign #{campaign_id} Test'
    body = 'Secure test email from Nuxtron campaign module.'

    if _db_ready:
        import psycopg
        with psycopg.connect(_db_dsn_fn()) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT subject_cipher, subject_preview, body_cipher, provider
                FROM email_campaigns
                WHERE id = %s AND tenant_id = %s
                """,
                (campaign_id, tenant_id),
            )
            row = cur.fetchone()
            if row:
                subject = _te_decrypt(row[0]) or str(row[1])
                body = _te_decrypt(row[2]) or body
                if row[3]:
                    provider = str(row[3])
        return provider, subject, body

    for item in _email_campaigns_memory:
        if item.get('id') == campaign_id and item.get('tenant_id') == tenant_id:
            subject = str(item.get('subject') or subject)
            body = str(item.get('body') or body)
            provider = str(item.get('provider') or provider)
            break

    return provider, subject, body


def _dispatch_test_email(provider: str, recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    if provider == 'postal':
        return _send_via_postal(recipient_email, subject, body)
    if provider == 'ses':
        return _send_via_ses(recipient_email, subject, body)
    return _send_via_listmonk(recipient_email, subject, body)


# ── Request Models ────────────────────────────────────────────

from pydantic import BaseModel, Field, HttpUrl


class EmailContactCreateRequest(BaseModel):
    email: str = Field(min_length=5, max_length=320)
    name: str = Field(min_length=1, max_length=120)
    tags: list[str] = Field(default_factory=list, max_length=20)


class EmailCampaignCreateRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10000)
    provider: Literal['listmonk', 'postal', 'ses', 'resend'] = 'listmonk'


class EmailCampaignSendTestRequest(BaseModel):
    recipient_email: str = Field(min_length=5, max_length=320)
