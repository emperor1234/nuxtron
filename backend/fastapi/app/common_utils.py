"""Common utilities shared across modules to avoid circular imports."""

import os


def _is_production() -> bool:
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def _security_alert_from_email() -> str:
    return os.getenv('SECURITY_ALERT_FROM_EMAIL', 'noreply@nuxtron.local')


def _queue_security_alert_email(email_event: dict) -> None:
    """Queue a security alert email in the configured application queue."""
    from . import memory_stores
    item = {
        'id': len(memory_stores.security_alert_emails) + 1,
        'tenant_id': email_event.get('tenant_id', ''),
        'provider': email_event.get('provider', 'smtp-queue'),
        'to_email': email_event.get('to_email', ''),
        'from_email': email_event.get('from_email', ''),
        'subject': email_event.get('subject', ''),
        'body': email_event.get('body', ''),
        'status': 'queued',
        'attempts': 0,
        'created_at': __import__('datetime').datetime.now(__import__('datetime').UTC).isoformat(),
    }
    memory_stores.security_alert_emails.append(item)
