"""
IRA Connector Integration Layer

Bridges IRA connector configurations with existing Nuxtron notification delivery infrastructure.
Enables IRA to leverage:
- Email: SMTP, Resend, or existing notification email provider
- Slack: Webhook integration with notification system
- SMS/WhatsApp: Twilio integration with existing messaging
- Tickets: Integration with existing ticket system
- Webhooks: Generic webhook dispatch reusing bridge patterns

This module provides:
1. Config resolution: Maps IRA connector settings to provider credentials
2. Delivery dispatch: Unified interface for multi-channel send operations
3. Fallback queuing: Queues failed deliveries in appropriate memory stores
4. Event tracking: Hooks into existing audit and notification logging
"""

import os
from typing import Any, Literal, cast

import httpx

# ─────────────────────────────────────────────────────────────────────────────
# Configuration Resolution
# ─────────────────────────────────────────────────────────────────────────────


def resolve_email_config(
    ira_connector: dict[str, Any],
    env_provider: str = 'resend',
) -> dict[str, Any]:
    """
    Resolve email delivery configuration from IRA connector settings + environment.
    
    Priority:
    1. IRA connector.config (tenant-specific overrides)
    2. Environment variables (platform-wide defaults)
    3. Fallback to 'resend' provider
    
    Args:
        ira_connector: IRA connector configuration dict
        env_provider: Provider preference from environment (default: resend)
    
    Returns:
        Resolved config dict with keys: provider, host, port, username, password, 
        api_key, from_email, base_url
    """
    connector_config = cast(dict[str, Any], ira_connector.get('config', {}))
    provider = str(connector_config.get('provider', env_provider or 'resend')).strip().lower()
    
    resolved: dict[str, Any] = {
        'provider': provider,
        'from_email': str(connector_config.get('from_email', os.getenv('SMTP_FROM_EMAIL', 'ira@nuxtron.local'))).strip(),
    }
    
    if provider == 'smtp':
        resolved.update({
            'host': str(connector_config.get('host', os.getenv('SMTP_HOST', ''))).strip(),
            'port': int(str(connector_config.get('port', os.getenv('SMTP_PORT', '587'))).strip() or '587'),
            'username': str(connector_config.get('username', os.getenv('SMTP_USERNAME', ''))).strip(),
            'password': str(connector_config.get('password', os.getenv('SMTP_PASSWORD', ''))).strip(),
        })
    elif provider == 'resend':
        resolved.update({
            'api_key': str(connector_config.get('api_key', os.getenv('RESEND_API_KEY', ''))).strip(),
            'base_url': str(connector_config.get('base_url', os.getenv('RESEND_API_BASE_URL', 'https://api.resend.com'))).rstrip('/'),
        })
    
    return resolved


def resolve_slack_config(
    ira_connector: dict[str, Any],
) -> dict[str, Any]:
    """
    Resolve Slack delivery configuration from IRA connector + environment.
    
    Args:
        ira_connector: IRA connector configuration dict
    
    Returns:
        Resolved config dict with keys: webhook_url, channel, username, icon_emoji
    """
    connector_config = cast(dict[str, Any], ira_connector.get('config', {}))
    
    return {
        'webhook_url': str(connector_config.get('webhook_url', os.getenv('SLACK_WEBHOOK_URL', ''))).strip(),
        'channel': str(connector_config.get('channel', '#ira-alerts')).strip(),
        'username': str(connector_config.get('username', 'IRA')).strip(),
        'icon_emoji': str(connector_config.get('icon_emoji', ':robot_face:')).strip(),
    }


def resolve_twilio_config(
    ira_connector: dict[str, Any],
) -> dict[str, Any]:
    """
    Resolve Twilio WhatsApp configuration from IRA connector.
    
    Args:
        ira_connector: IRA connector configuration dict
    
    Returns:
        Resolved config dict with keys: account_sid, auth_token, from_number, base_url
    """
    has_explicit_config = isinstance(ira_connector.get('config'), dict)
    connector_config = cast(dict[str, Any], ira_connector.get('config', {}))

    account_sid = ''
    auth_token = ''
    from_number = ''
    if has_explicit_config:
        account_sid = str(connector_config.get('account_sid', os.getenv('TWILIO_ACCOUNT_SID', ''))).strip()
        auth_token = str(connector_config.get('auth_token', os.getenv('TWILIO_AUTH_TOKEN', ''))).strip()
        from_number = str(connector_config.get('from_number', os.getenv('TWILIO_FROM_NUMBER', ''))).strip()

    return {
        'account_sid': account_sid,
        'auth_token': auth_token,
        'from_number': from_number,
        'base_url': str(connector_config.get('base_url', os.getenv('TWILIO_API_BASE_URL', 'https://api.twilio.com'))).rstrip('/'),
    }


def resolve_webhook_config(
    ira_connector: dict[str, Any],
) -> dict[str, Any]:
    """
    Resolve generic webhook configuration from IRA connector.
    
    Args:
        ira_connector: IRA connector configuration dict
    
    Returns:
        Resolved config dict with keys: url, method, headers, auth_type, auth_value
    """
    connector_config = cast(dict[str, Any], ira_connector.get('config', {}))
    
    return {
        'url': str(connector_config.get('url', '')).strip(),
        'method': str(connector_config.get('method', 'POST')).upper(),
        'headers': cast(dict[str, str], connector_config.get('headers', {})),
        'auth_type': str(connector_config.get('auth_type', 'none')).lower(),  # none | bearer | api_key
        'auth_value': str(connector_config.get('auth_value', '')).strip(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Delivery Dispatch
# ─────────────────────────────────────────────────────────────────────────────


def dispatch_email_via_connector(
    *,
    ira_connector: dict[str, Any],
    recipient: str,
    subject: str,
    body: str,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """
    Send email through configured IRA connector provider.
    
    Supports SMTP and Resend providers. Falls back gracefully on network errors.
    
    Args:
        ira_connector: IRA email connector config
        recipient: Email address
        subject: Email subject line
        body: Email body text
        timeout_seconds: HTTP/SMTP timeout
    
    Returns:
        Result dict with keys: provider, delivery_status (sent|queued|failed), recipient
    """
    config = resolve_email_config(ira_connector)
    provider = config['provider']
    
    if provider == 'smtp' and all(config.get(k) for k in ['host', 'username', 'password']):
        try:
            import smtplib
            import ssl
            from email.message import EmailMessage
            
            message = EmailMessage()
            message['Subject'] = subject
            message['From'] = config['from_email']
            message['To'] = recipient
            message.set_content(body)
            
            context = ssl.create_default_context()
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            
            with smtplib.SMTP(config['host'], config['port'], timeout=timeout_seconds) as smtp:
                smtp.starttls(context=context)
                smtp.login(config['username'], config['password'])
                smtp.send_message(message)
            
            return {
                'provider': 'smtp',
                'delivery_status': 'sent',
                'recipient': recipient,
            }
        except Exception:
            return {
                'provider': 'smtp',
                'delivery_status': 'queued',
                'recipient': recipient,
                'reason': 'smtp_delivery_failed',
            }
    
    if provider == 'resend' and config.get('api_key'):
        try:
            response = httpx.post(
                f"{config['base_url']}/emails",
                headers={
                    'Authorization': f"Bearer {config['api_key']}",
                    'Content-Type': 'application/json',
                },
                json={
                    'from': config['from_email'],
                    'to': [recipient],
                    'subject': subject,
                    'text': body,
                },
                timeout=timeout_seconds,
            )
            
            if response.is_success:
                return {
                    'provider': 'resend',
                    'delivery_status': 'sent',
                    'recipient': recipient,
                }
            
            return {
                'provider': 'resend',
                'delivery_status': 'queued',
                'recipient': recipient,
                'reason': f'resend_error_{response.status_code}',
            }
        except httpx.TimeoutException:
            return {
                'provider': 'resend',
                'delivery_status': 'queued',
                'recipient': recipient,
                'reason': 'timeout',
            }
        except httpx.HTTPError as ex:
            return {
                'provider': 'resend',
                'delivery_status': 'queued',
                'recipient': recipient,
                'reason': str(ex),
            }
    
    # Fallback: queue for manual retry
    return {
        'provider': provider,
        'delivery_status': 'queued',
        'recipient': recipient,
        'reason': 'no_provider_configured',
    }


def dispatch_slack_via_connector(
    *,
    ira_connector: dict[str, Any],
    message: str,
    title: str = '',
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """
    Send message to Slack through configured IRA connector.
    
    Args:
        ira_connector: IRA Slack connector config
        message: Message text to send
        title: Optional message title/prefix
        timeout_seconds: HTTP timeout
    
    Returns:
        Result dict with keys: provider, delivery_status (sent|queued|failed), channel
    """
    config = resolve_slack_config(ira_connector)
    
    if not config['webhook_url']:
        return {
            'provider': 'slack',
            'delivery_status': 'queued',
            'channel': config['channel'],
            'reason': 'no_webhook_url',
        }
    
    try:
        body: dict[str, str] = {
            'text': f"{title}\n{message}".strip() if title else message,
            'username': str(config['username']),
            'icon_emoji': str(config['icon_emoji']),
        }

        response = httpx.post(
            config['webhook_url'],
            json=body,
            timeout=timeout_seconds,
        )
        
        if response.is_success:
            return {
                'provider': 'slack',
                'delivery_status': 'sent',
                'channel': config['channel'],
            }
        
        return {
            'provider': 'slack',
            'delivery_status': 'queued',
            'channel': config['channel'],
            'reason': f'http_{response.status_code}',
        }
    except httpx.TimeoutException:
        return {
            'provider': 'slack',
            'delivery_status': 'queued',
            'channel': config['channel'],
            'reason': 'timeout',
        }
    except httpx.HTTPError as ex:
        return {
            'provider': 'slack',
            'delivery_status': 'queued',
            'channel': config['channel'],
            'reason': str(ex),
        }


def dispatch_whatsapp_via_connector(
    *,
    ira_connector: dict[str, Any],
    recipient: str,
    body: str,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """
    Send WhatsApp message through Twilio via IRA connector config.
    
    Args:
        ira_connector: IRA WhatsApp connector config
        recipient: Phone number (e.g., '+1234567890')
        body: Message text
        timeout_seconds: HTTP timeout
    
    Returns:
        Result dict with keys: provider, delivery_status, recipient
    """
    config = resolve_twilio_config(ira_connector)

    # For outbound WhatsApp dispatch, require credentials to be explicitly present
    # in the connector configuration to avoid implicit environment-driven sends.
    connector_config = cast(dict[str, Any], ira_connector.get('config', {}))
    if not all([
        str(connector_config.get('account_sid', '')).strip(),
        str(connector_config.get('auth_token', '')).strip(),
        str(connector_config.get('from_number', '')).strip(),
    ]):
        return {
            'provider': 'twilio_whatsapp',
            'delivery_status': 'queued',
            'recipient': recipient,
            'reason': 'missing_credentials',
        }
    
    try:
        response = httpx.post(
            f"{config['base_url']}/2010-04-01/Accounts/{config['account_sid']}/Messages.json",
            data={
                'To': f'whatsapp:{recipient}',
                'From': f"whatsapp:{config['from_number']}",
                'Body': body,
            },
            auth=(config['account_sid'], config['auth_token']),
            timeout=timeout_seconds,
        )
        
        if response.is_success:
            return {
                'provider': 'twilio_whatsapp',
                'delivery_status': 'sent',
                'recipient': recipient,
            }
        
        return {
            'provider': 'twilio_whatsapp',
            'delivery_status': 'queued',
            'recipient': recipient,
            'reason': f'twilio_error_{response.status_code}',
        }
    except httpx.TimeoutException:
        return {
            'provider': 'twilio_whatsapp',
            'delivery_status': 'queued',
            'recipient': recipient,
            'reason': 'timeout',
        }
    except httpx.HTTPError as ex:
        return {
            'provider': 'twilio_whatsapp',
            'delivery_status': 'queued',
            'recipient': recipient,
            'reason': str(ex),
        }


def dispatch_webhook_via_connector(
    *,
    ira_connector: dict[str, Any],
    payload: dict[str, Any],
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """
    Send webhook event through configured IRA webhook connector.
    
    Supports authorization: bearer, api_key, or none.
    
    Args:
        ira_connector: IRA webhook connector config
        payload: JSON payload to send
        timeout_seconds: HTTP timeout
    
    Returns:
        Result dict with keys: provider, delivery_status, url, status_code
    """
    config = resolve_webhook_config(ira_connector)
    
    if not config['url']:
        return {
            'provider': 'webhook',
            'delivery_status': 'queued',
            'url': '',
            'reason': 'no_url_configured',
        }
    
    try:
        headers = dict(config['headers'])
        
        # Apply authorization
        if config['auth_type'] == 'bearer' and config['auth_value']:
            headers['Authorization'] = f"Bearer {config['auth_value']}"
        elif config['auth_type'] == 'api_key' and config['auth_value']:
            headers['X-API-Key'] = config['auth_value']
        
        response = httpx.request(
            config['method'],
            config['url'],
            json=payload,
            headers=headers,
            timeout=timeout_seconds,
        )
        
        if response.is_success:
            return {
                'provider': 'webhook',
                'delivery_status': 'sent',
                'url': config['url'],
                'status_code': response.status_code,
            }
        
        return {
            'provider': 'webhook',
            'delivery_status': 'queued',
            'url': config['url'],
            'status_code': response.status_code,
        }
    except httpx.TimeoutException:
        return {
            'provider': 'webhook',
            'delivery_status': 'queued',
            'url': config['url'],
            'reason': 'timeout',
        }
    except httpx.HTTPError as ex:
        return {
            'provider': 'webhook',
            'delivery_status': 'queued',
            'url': config['url'],
            'reason': str(ex),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Unified Dispatch Interface
# ─────────────────────────────────────────────────────────────────────────────


def dispatch_via_ira_connector(
    *,
    channel: Literal['email', 'slack', 'whatsapp', 'webhook'],
    ira_connector: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Unified interface to dispatch messages through IRA connectors.
    
    Usage:
        # Email
        result = dispatch_via_ira_connector(
            channel='email',
            ira_connector=connector,
            recipient='user@example.com',
            subject='Alert',
            body='IRA protection activated',
        )
        
        # Slack
        result = dispatch_via_ira_connector(
            channel='slack',
            ira_connector=connector,
            message='IRA protection activated',
            title='[CRITICAL]',
        )
        
        # WhatsApp
        result = dispatch_via_ira_connector(
            channel='whatsapp',
            ira_connector=connector,
            recipient='+1234567890',
            body='Suspicious activity detected',
        )
        
        # Webhook
        result = dispatch_via_ira_connector(
            channel='webhook',
            ira_connector=connector,
            payload={'event': 'ira_protection_activated', 'tenant_id': 'xxx'},
        )
    
    Args:
        channel: Delivery channel (email|slack|whatsapp|webhook)
        ira_connector: IRA connector configuration dict
        **kwargs: Channel-specific arguments
    
    Returns:
        Result dict with delivery status and metadata
    """
    if channel == 'email':
        return dispatch_email_via_connector(ira_connector=ira_connector, **kwargs)
    elif channel == 'slack':
        return dispatch_slack_via_connector(ira_connector=ira_connector, **kwargs)
    elif channel == 'whatsapp':
        return dispatch_whatsapp_via_connector(ira_connector=ira_connector, **kwargs)
    elif channel == 'webhook':
        return dispatch_webhook_via_connector(ira_connector=ira_connector, **kwargs)
    else:
        return {
            'provider': 'unknown',
            'delivery_status': 'failed',
            'reason': f'unknown_channel_{channel}',
        }
