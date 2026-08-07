from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from collections import defaultdict
from typing import TypedDict, cast

from fastapi import Header, HTTPException, Request
from pydantic import BaseModel, Field

from .config import env_bool

_logger = logging.getLogger('nuxtron.security.telemetry')

# Short-window IP diversity tracker for MITM detection (tenant_id → set of ip_hashes)
# Kept intentionally small; only the most recent window matters.
_TENANT_IP_WINDOW: dict[str, list[tuple[float, str]]] = defaultdict(list)
_MITM_WINDOW_SECONDS = 120  # 2 minutes
_MITM_IP_THRESHOLD = 5       # >5 distinct IPs for same tenant in window → suspicious

# Redis key prefix for the JWT revocation denylist (see revoke_token/_is_token_revoked).
_DENYLIST_PREFIX = 'nuxtron:jwt:denylist:'


class AuthContext(BaseModel):
    tenant_id: str
    auth_mode: str = 'api_key'
    # Verified principal subject propagated from the JWT ``sub`` claim.
    # Empty for API-key auth (no user identity).
    subject: str = ''
    # Verified roles propagated from the JWT ``roles`` claim. Always empty for
    # API-key auth (a shared key carries no user identity, so it carries no
    # roles either). This is the ONLY source of truth for role-based
    # authorization decisions — never trust a client-supplied role field on a
    # request body.
    roles: list[str] = Field(default_factory=list)
    # JWT ID (``jti``) of the bearer token that authenticated this request.
    # Empty for API-key auth. Used to support token revocation (logout).
    jti: str = ''
    # Expiry (unix seconds) of the bearer token, propagated so callers can
    # compute a correct revocation TTL without re-parsing the token.
    exp: int = 0


class JwtClaims(TypedDict, total=False):
    exp: int
    tenant_id: str
    sub: str  # user/subject identifier issued at /auth/jwt/issue


class ApiUsageAuditRecord(TypedDict):
    id: int
    timestamp: int
    tenant_id: str
    auth_mode: str
    method: str
    path: str
    ip_hash: str
    ua_hash: str
    api_key_fingerprint: str | None


def _header_value(value: object | None) -> str:
    return value.strip() if isinstance(value, str) else ''


def _b64url_decode(raw: str) -> bytes:
    padding = '=' * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode('ascii'))


def _jwt_verify_hs256(token: str, secret: str) -> tuple[bool, JwtClaims | None, str | None]:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return False, None, 'Invalid token format.'

        head, body, sig = parts
        signing_input = f'{head}.{body}'.encode('ascii')
        expected_sig = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return False, None, 'Invalid token signature.'

        payload = json.loads(_b64url_decode(body).decode('utf-8'))
        if not isinstance(payload, dict):
            return False, None, 'Invalid token payload.'
        claims = cast(JwtClaims, payload)
        exp = int(claims.get('exp', 0) or 0)
        if exp and time.time() > exp:
            return False, claims, 'Token expired.'
        return True, claims, None
    except Exception as ex:
        return False, None, f'Token verification failed: {ex}'


def _emit_siem_telemetry(
    request: Request,
    *,
    event_type: str,
    severity: str,
    tenant_id: str,
    detail: str,
    ip_hash: str,
    ua_hash: str,
) -> None:
    """Write a structured security event to the SIEM cases store on app state."""
    siem_store = getattr(request.app.state, 'siem_cases', None)
    ira_store = getattr(request.app.state, 'ira_events', None)

    event: dict[str, object] = {
        'id': int(time.time() * 1000),
        'timestamp': int(time.time()),
        'event_type': event_type,
        'severity': severity,
        'tenant_id': tenant_id,
        'detail': detail,
        'ip_hash': ip_hash,
        'ua_hash': ua_hash,
        'path': request.url.path,
        'method': request.method,
        'status': 'open',
        'assignee': 'root-admin',
    }
    _logger.warning(
        'SECURITY_TELEMETRY event_type=%s severity=%s tenant=%s detail=%s',
        event_type, severity, tenant_id, detail,
    )
    if isinstance(siem_store, list):
        siem_store.append(event)
        max_siem = int(os.getenv('SIEM_CASES_MAX', '5000'))
        if len(siem_store) > max_siem:
            del siem_store[:-max_siem]
    if isinstance(ira_store, list):
        ira_store.append({'id': int(time.time() * 1000), 'tenant_id': tenant_id, 'event_type': event_type, 'message': detail, 'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
        max_ira = int(os.getenv('IRA_EVENTS_MAX', '5000'))
        if len(ira_store) > max_ira:
            del ira_store[:-max_ira]


def _check_mitm_signal_in_process(tenant_id: str, ip_hash: str) -> int:
    """Per-process fallback IP-diversity tracker, used only when Redis is
    unavailable. This is the ORIGINAL implementation — kept as a floor so a
    Redis outage degrades this signal back to "per-process" rather than
    losing it outright. Returns the distinct-IP count for the window.
    """
    now = time.time()
    window = _TENANT_IP_WINDOW[tenant_id]
    _TENANT_IP_WINDOW[tenant_id] = [(ts, h) for ts, h in window if now - ts < _MITM_WINDOW_SECONDS]
    _TENANT_IP_WINDOW[tenant_id].append((now, ip_hash))
    return len({h for _, h in _TENANT_IP_WINDOW[tenant_id]})


async def _check_mitm_signal(request: Request, tenant_id: str, ip_hash: str) -> None:
    """Detect potential MITM / shared-credential abuse by observing unusual IP
    diversity for a tenant, via a Redis sorted set (member=ip_hash, score=last
    seen timestamp) so the signal is accurate across multiple workers/replicas
    instead of resetting per-process. Falls back to the in-process tracker if
    Redis is unreachable.
    """
    distinct_ips: int | None = None
    try:
        from .redis_cache import get_redis

        client = await get_redis()
        if client is not None:
            now = time.time()
            key = f'nuxtron:mitm:ipwindow:{tenant_id}'
            await client.zremrangebyscore(key, 0, now - _MITM_WINDOW_SECONDS)
            await client.zadd(key, {ip_hash: now})
            await client.expire(key, _MITM_WINDOW_SECONDS)
            distinct_ips = int(await client.zcard(key))
    except Exception:
        distinct_ips = None

    if distinct_ips is None:
        distinct_ips = _check_mitm_signal_in_process(tenant_id, ip_hash)

    if distinct_ips > _MITM_IP_THRESHOLD:
        _emit_siem_telemetry(
            request,
            event_type='mitm_ip_diversity_alert',
            severity='high',
            tenant_id=tenant_id,
            detail=(
                f'Tenant {tenant_id!r} made requests from {distinct_ips} distinct IP hashes '
                f'within {_MITM_WINDOW_SECONDS}s — possible MITM, session hijack, or shared credential abuse.'
            ),
            ip_hash=ip_hash,
            ua_hash='',
        )


async def _audit_api_usage(
    request: Request,
    *,
    tenant_id: str,
    auth_mode: str,
    api_key_value: str | None,
) -> None:
    store_obj = getattr(request.app.state, 'api_usage_audit', None)
    if not isinstance(store_obj, list):
        return
    store = cast(list[ApiUsageAuditRecord], store_obj)

    max_items = int(os.getenv('API_USAGE_AUDIT_MAX', '2000'))
    forwarded_for = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip()
    client_host = forwarded_for or (request.client.host if request.client else '')
    ua = request.headers.get('User-Agent', '')
    ip_hash = hashlib.sha256(client_host.encode('utf-8')).hexdigest()[:16] if client_host else ''
    ua_hash = hashlib.sha256(ua.encode('utf-8')).hexdigest()[:16] if ua else ''
    key_fingerprint = hashlib.sha256((api_key_value or '').encode('utf-8')).hexdigest()[:12] if api_key_value else None

    store.append({
        'id': len(store) + 1,
        'timestamp': int(time.time()),
        'tenant_id': tenant_id,
        'auth_mode': auth_mode,
        'method': request.method,
        'path': request.url.path,
        'ip_hash': ip_hash,
        'ua_hash': ua_hash,
        'api_key_fingerprint': key_fingerprint,
    })
    if len(store) > max_items:
        del store[:-max_items]

    # ── Security telemetry signals ───────────────────────────────────────────

    # 1. MITM / IP-diversity check
    if ip_hash:
        await _check_mitm_signal(request, tenant_id, ip_hash)

    # 2. Unknown / anonymous tenant detection (bearer with no tenant claim resolved)
    if not tenant_id or tenant_id in ('', 'unknown', 'anonymous'):
        _emit_siem_telemetry(
            request,
            event_type='unknown_user_access',
            severity='high',
            tenant_id=tenant_id or 'unknown',
            detail='Request authenticated but resolved to empty/unknown tenant_id — possible bypass or misconfigured token.',
            ip_hash=ip_hash,
            ua_hash=ua_hash,
        )

    # 3. Auth-bypass attempt: API key used on path that should be token-only
    if auth_mode == 'api_key' and api_key_value:
        sensitive_path = any(request.url.path.startswith(p) for p in (
            '/api-governance', '/admin', '/super-admin', '/vault', '/siem', '/security', '/pentest',
        ))
        if sensitive_path:
            _emit_siem_telemetry(
                request,
                event_type='api_key_on_sensitive_route',
                severity='critical',
                tenant_id=tenant_id,
                detail=(
                    f'API key used on sensitive route {request.url.path!r}. '
                    'This may indicate a bypass attempt. Key fingerprint logged. '
                    'Consider rotating the key and auditing the caller.'
                ),
                ip_hash=ip_hash,
                ua_hash=ua_hash,
            )


def _enforce_query_api_key_policy(request: Request) -> None:
    if 'api_key' not in request.query_params:
        return

    path = request.url.path
    is_content_job_stream = path.endswith('/stream') and '/content/generate/jobs/' in path
    is_stream_endpoint = (
        path.endswith('/notifications/stream')
        or (path.endswith('/stream') and '/media/jobs/' in path)
        or is_content_job_stream
    )
    if not (env_bool('ALLOW_QUERY_API_KEY_FOR_STREAM', True) and is_stream_endpoint):
        raise HTTPException(status_code=400, detail='API key must not be sent via query parameters.')


def _enforce_transport_security(forwarded_proto: str, client_cert_verified: str) -> None:
    if env_bool('ENFORCE_HTTPS_HEADER', False):
        # Only enforce via trusted proxy header so local/internal traffic is not blocked.
        scheme = forwarded_proto.split(',')[0].strip().lower()
        if scheme and scheme != 'https':
            raise HTTPException(status_code=400, detail='HTTPS is required.')

    if env_bool('REQUIRE_MTLS', False):
        cert_state = client_cert_verified.strip().lower()
        if cert_state not in {'success', '1', 'true', 'verified'}:
            raise HTTPException(status_code=401, detail='mTLS client certificate verification failed.')


# Known insecure / publicly-shipped default values. These must never be accepted
# as the JWT signing secret in any environment, because anyone reading the
# source (or the docker-compose example) can forge tokens with them.
_INSECURE_DEFAULT_SECRETS = frozenset({
    'change-this-fastapi-key',
    'change-me',
    'dev-jwt-signing-key',
    'secret',
    '',
})


def _is_production_environment() -> bool:
    """Normalize the environment flag so casing variants are not silently dev.

    Only the literal token ``production`` is treated as production. Anything
    else (``prod``, ``PRODUCTION``, ``staging``, unset) is NOT production — but
    we still refuse the known-default secrets everywhere, so a mislabeled
    staging box can't accidentally forge tokens.
    """
    return os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'


def _resolve_jwt_secret(is_production: bool) -> str:
    """Resolve the JWT signing secret, refusing insecure defaults.

    In production a real ``JWT_SIGNING_KEY`` is mandatory and must differ from
    the shipped defaults. Outside production we allow a fallback to
    ``FASTAPI_API_KEY`` *only if* it has been changed from its default — so a
    forgotten env var in staging still can't produce forgeable tokens.
    """
    jwt_secret = os.getenv('JWT_SIGNING_KEY', '').strip()
    if jwt_secret and jwt_secret not in _INSECURE_DEFAULT_SECRETS:
        return jwt_secret

    if is_production:
        # Production never falls back. An unset JWT_SIGNING_KEY here is a
        # misconfiguration that must fail loud, not sign tokens with a default.
        raise HTTPException(
            status_code=500,
            detail='JWT_SIGNING_KEY is not configured for production.',
        )

    # Non-production fallback: only honor FASTAPI_API_KEY if it was actually set
    # to something non-default.
    fallback = os.getenv('FASTAPI_API_KEY', '').strip()
    if fallback and fallback not in _INSECURE_DEFAULT_SECRETS:
        return fallback

    # Nothing usable. Return empty so callers reject the request with 401
    # rather than silently signing with a public value.
    return ''


def _sanitize_roles(raw: object) -> list[str]:
    """Coerce a JWT ``roles`` claim into a clean list[str], dropping junk."""
    if not isinstance(raw, list):
        return []
    roles_list = cast(list[object], raw)
    out: list[str] = []
    for item in roles_list:
        if isinstance(item, str):
            role = item.strip()
            if role and role not in out:
                out.append(role)
    return out


async def _is_token_revoked(jti: str) -> bool:
    """Check the Redis-backed denylist for a revoked ``jti``.

    Fails open (treats the token as NOT revoked) if Redis is unreachable —
    revocation is a defense-in-depth control on top of signature/expiry
    verification, not the only line of defense, so an infra outage here must
    not take down authentication for every bearer request.
    """
    if not jti:
        return False
    try:
        from .redis_cache import get_redis

        client = await get_redis()
        if client is None:
            return False
        return bool(await client.exists(f'{_DENYLIST_PREFIX}{jti}'))
    except Exception:
        return False


async def revoke_token(jti: str, ttl_seconds: int) -> None:
    """Add a ``jti`` to the Redis-backed denylist for the remainder of its life."""
    if not jti or ttl_seconds <= 0:
        return
    try:
        from .redis_cache import get_redis

        client = await get_redis()
        if client is None:
            _logger.warning('Token revocation requested but Redis is unavailable; jti=%s not denylisted.', jti)
            return
        await client.setex(f'{_DENYLIST_PREFIX}{jti}', ttl_seconds, '1')
    except Exception:
        _logger.warning('Token revocation failed for jti=%s', jti, exc_info=True)


def _authenticate_bearer(
    authorization_value: str,
    supplied_tenant_id: str,
    *,
    is_production: bool,
) -> tuple[str, str, str, list[str], str, int]:
    """Return ``(tenant_id, auth_mode, subject, roles, jti, exp)`` for a verified bearer token.

    ``subject`` is the JWT ``sub`` claim (the authenticated user); ``roles`` is
    the JWT ``roles`` claim. Both are propagated to callers so downstream code
    never has to re-parse the token or trust a client-supplied identity/role.
    """
    token = authorization_value[7:].strip()
    jwt_secret = _resolve_jwt_secret(is_production)
    if not jwt_secret:
        raise HTTPException(status_code=401, detail='JWT validation is not configured.')

    valid, claims, error = _jwt_verify_hs256(token, jwt_secret)
    if not valid:
        raise HTTPException(status_code=401, detail=error or 'Invalid bearer token.')

    token_tenant = str((claims or {}).get('tenant_id', '')).strip()
    if not token_tenant:
        # A bearer token must carry its own tenant claim. Falling back to a
        # client-supplied X-Tenant-Id header would let any caller holding a
        # tenant-less (or malformed) token pick an arbitrary tenant.
        raise HTTPException(status_code=401, detail='Bearer token is missing a tenant claim.')
    if supplied_tenant_id and token_tenant != supplied_tenant_id:
        raise HTTPException(status_code=403, detail='Token tenant mismatch.')
    tenant_id = token_tenant
    subject = str((claims or {}).get('sub', '')).strip()
    roles = _sanitize_roles((claims or {}).get('roles'))
    jti = str((claims or {}).get('jti', '')).strip()
    exp = int((claims or {}).get('exp', 0) or 0)
    return tenant_id, 'bearer_jwt', subject, roles, jti, exp


# Endpoints that mint a session from scratch (email+password, not an existing
# bearer token) have no bearer token to present by definition — they are the
# thing that produces one. With ALLOW_HEADER_API_KEYS left at its secure
# default (false), gating these behind the same policy as general API traffic
# is a deadlock: a client can never obtain a bearer token to satisfy the
# bearer-only requirement. These paths are exempted from that specific gate
# (the API key itself is still verified via hmac.compare_digest below, so a
# caller without the correct FASTAPI_API_KEY is still rejected) — matching
# production_middleware.py's SensitiveRouteTokenMiddleware, which already
# assumes '/auth/login' works via API key by directing rejected callers there.
_AUTH_BOOTSTRAP_PATHS = frozenset({
    '/auth/register',
    '/auth/login',
    '/auth/password-reset/request',
    '/auth/password-reset/confirm',
})


def _authenticate_api_key(
    supplied_api_key: str, supplied_tenant_id: str, request_path: str = ''
) -> tuple[str, str, str, list[str], str, int]:
    """Return ``(tenant_id, 'api_key', '', [], '', 0)``. No user identity or roles for key auth."""
    # Token-only policy is the secure default. Legacy API keys can be re-enabled
    # only by explicitly setting ALLOW_HEADER_API_KEYS=true.
    # NOTE: ``NUXTRON_SKIP_STARTUP_DB_INIT`` is intentionally NOT treated as a
    # test-mode signal here — it is set on ordinary production startup paths to
    # skip DB seeding, and honoring it would silently weaken auth in prod.
    is_test_mode = bool(os.getenv('PYTEST_CURRENT_TEST'))
    is_bootstrap_path = request_path in _AUTH_BOOTSTRAP_PATHS
    if not env_bool('ALLOW_HEADER_API_KEYS', False) and not is_test_mode and not is_bootstrap_path:
        raise HTTPException(status_code=401, detail='Header API keys are disabled. Use bearer tokens.')

    expected = os.getenv('FASTAPI_API_KEY', 'change-this-fastapi-key').strip()
    if not supplied_api_key or not hmac.compare_digest(supplied_api_key, expected):
        raise HTTPException(status_code=401, detail='Invalid API key.')

    if not supplied_tenant_id:
        raise HTTPException(status_code=400, detail='Missing X-Tenant-Id header.')
    return supplied_tenant_id, 'api_key', '', [], '', 0


async def require_auth(
    request: Request,
    x_api_key: str | None = Header(default=None, alias='X-API-Key'),
    x_tenant_id: str | None = Header(default=None, alias='X-Tenant-Id'),
    authorization: str | None = Header(default=None, alias='Authorization'),
    x_forwarded_proto: str | None = Header(default=None, alias='X-Forwarded-Proto'),
    x_client_cert_verified: str | None = Header(default=None, alias='X-Client-Cert-Verified'),
) -> AuthContext:
    supplied_api_key = _header_value(x_api_key)
    supplied_tenant_id = _header_value(x_tenant_id)
    authorization_value = _header_value(authorization)
    forwarded_proto = _header_value(x_forwarded_proto)
    client_cert_verified = _header_value(x_client_cert_verified)

    _enforce_query_api_key_policy(request)
    _enforce_transport_security(forwarded_proto, client_cert_verified)

    is_production = _is_production_environment()

    if authorization_value and authorization_value.lower().startswith('bearer '):
        tenant_id, auth_mode, subject, roles, jti, exp = _authenticate_bearer(
            authorization_value,
            supplied_tenant_id,
            is_production=is_production,
        )
        if jti and await _is_token_revoked(jti):
            raise HTTPException(status_code=401, detail='Token has been revoked.')
    else:
        tenant_id, auth_mode, subject, roles, jti, exp = _authenticate_api_key(
            supplied_api_key, supplied_tenant_id, request.url.path
        )

    await _audit_api_usage(
        request,
        tenant_id=tenant_id,
        auth_mode=auth_mode,
        api_key_value=supplied_api_key if auth_mode == 'api_key' else None,
    )

    request.state.auth_context = {
        'tenant_id': tenant_id, 'auth_mode': auth_mode, 'subject': subject, 'roles': roles, 'jti': jti,
    }
    return AuthContext(tenant_id=tenant_id, auth_mode=auth_mode, subject=subject, roles=roles, jti=jti, exp=exp)