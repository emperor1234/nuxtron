"""Common utilities shared across modules to avoid circular imports."""

import os


def _is_production() -> bool:
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def _security_alert_from_email() -> str:
    return os.getenv('SECURITY_ALERT_FROM_EMAIL', 'noreply@nuxtron.local')


def _queue_security_alert_email(email_event: dict) -> None:
    """Queue a security alert email. This is a placeholder - actual implementation in services."""
    # This will be overridden by the actual implementation in services
    pass


# Provide the real implementations as well
def _real_queue_security_alert_email(email_event: dict) -> None:
    """Queue a security alert email to the memory store."""
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


# Assign the real implementation by default
_queue_security_alert_email = _real_queue_security_alert_email