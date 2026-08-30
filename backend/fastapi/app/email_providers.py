"""Email provider integrations for transactional email delivery."""

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_FROM_EMAIL = 'noreply@nuxtron.local'
CONTENT_TYPE_JSON = 'application/json'


def send_via_listmonk(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Send email via Listmonk transactional API."""
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
        logger.exception('Listmonk request failed')
        return False, f'Listmonk request failed: {ex}'


def send_via_postal(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Send email via Postal API."""
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
        logger.exception('Postal request failed')
        return False, f'Postal request failed: {ex}'


def send_via_ses(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Send email via SES SMTP."""
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
        logger.exception('SES SMTP request failed')
        return False, f'SES SMTP request failed: {ex}'


def send_via_resend(recipient_email: str, subject: str, body: str) -> tuple[bool, str]:
    """Send email via Resend API."""
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    api_base_url = os.getenv('RESEND_API_BASE_URL', 'https://api.resend.com').rstrip('/')
    from_email = os.getenv('RESEND_FROM_EMAIL', '').strip() or os.getenv('SMTP_FROM', '').strip() or DEFAULT_FROM_EMAIL
    if not api_key:
        return False, 'Resend not configured.'

    payload: dict[str, Any] = {
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
        logger.exception('Resend request failed')
        return False, f'Resend request failed: {ex}'


def get_security_alert_from_email() -> str:
    """Get the from email address for security alerts."""
    for candidate in (
        os.getenv('SMTP_FROM', '').strip(),
        os.getenv('RESEND_FROM_EMAIL', '').strip(),
        os.getenv('SES_FROM_EMAIL', '').strip(),
        os.getenv('POSTAL_FROM_EMAIL', '').strip(),
    ):
        if candidate:
            return candidate
    return ''


def dispatch_security_email(recipient_email: str, subject: str, body: str) -> tuple[bool, str, str]:
    """Dispatch a security alert email using available providers.
    
    Returns:
        Tuple of (success, provider_name, detail_message)
    """
    last_detail = 'No configured email transport for security alerts.'
    for provider, sender in (
        ('resend', send_via_resend),
        ('postal', send_via_postal),
        ('ses', send_via_ses),
        ('listmonk', send_via_listmonk),
    ):
        success, detail = sender(recipient_email, subject, body)
        if success:
            return True, provider, detail
        last_detail = detail
        if 'not configured' not in detail.lower():
            return False, provider, detail
    return False, 'unavailable', last_detail
