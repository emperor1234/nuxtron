"""Single super-admin gate: shared API key plus optional IP allowlist."""

from __future__ import annotations

import hmac
import ipaddress
import os

from fastapi import HTTPException, Request


def _is_production() -> bool:
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def require_super_admin_key(x_super_admin_key: str | None) -> None:
    expected = os.getenv('SUPER_ADMIN_API_KEY', '').strip()
    supplied = (x_super_admin_key or '').strip()
    if not expected:
        raise HTTPException(status_code=503, detail='SUPER_ADMIN_API_KEY is not configured.')
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail='Invalid super admin key.')


def request_source_ip(request: Request) -> str:
    forwarded_for = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip()
    if forwarded_for:
        return forwarded_for
    return request.client.host if request.client and request.client.host else ''


def source_ip_allowed(source_ip: str, allowlist: list[str]) -> bool:
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


def require_super_admin_access(request: Request, x_super_admin_key: str | None) -> None:
    require_super_admin_key(x_super_admin_key)

    raw_allowlist = os.getenv('SUPER_ADMIN_ALLOWLIST', '').strip()
    allowlist = [item.strip() for item in raw_allowlist.split(',') if item.strip()]
    if _is_production() and not allowlist:
        raise HTTPException(status_code=503, detail='SUPER_ADMIN_ALLOWLIST must be configured in production.')
    if not allowlist:
        return

    source_ip = request_source_ip(request)
    if not source_ip or not source_ip_allowed(source_ip, allowlist):
        raise HTTPException(status_code=403, detail='Source IP is not allowlisted for super admin access.')
