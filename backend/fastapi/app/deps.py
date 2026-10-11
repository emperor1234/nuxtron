from __future__ import annotations
import sys
import hashlib
import hmac
import logging
import os
import time
import asyncio
from collections import defaultdict
from typing import TypedDict, cast
from fastapi import Header, HTTPException, Request
from pydantic import BaseModel, Field
from .domains.identity.auth_utils import b64url_decode as _b64url_decode
from .domains.identity.auth_utils import JwtClaims as JwtClaims
from .domains.identity.auth_utils import jwt_verify_hs256 as _jwt_verify_hs256
from .config import env_bool
from .domains.identity.oidc import OIDCVerificationError, verify_oidc_jwt

_logger = logging.getLogger("nuxtron.security.telemetry")
_TENANT_IP_WINDOW: dict[str, list[tuple[float, str]]] = defaultdict(list)
_MITM_WINDOW_SECONDS = 120
_MITM_IP_THRESHOLD = 5
_DENYLIST_PREFIX = "nuxtron:jwt:denylist:"


class AuthContext(BaseModel):
    tenant_id: str
    external_organization_id: str = ""
    auth_mode: str = "api_key"
    subject: str = ""
    roles: list[str] = Field(default_factory=list)
    jti: str = ""
    exp: int = 0


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
    return value.strip() if isinstance(value, str) else ""


def _emit_siem_telemetry(
    request: Request, *, event_type: str, severity: str, tenant_id: str, detail: str, ip_hash: str, ua_hash: str
) -> None:
    """Write a structured security event to the SIEM cases store on app state."""
    siem_store = getattr(request.app.state, "siem_cases", None)
    ira_store = getattr(request.app.state, "ira_events", None)
    event: dict[str, object] = {
        "id": int(time.time() * 1000),
        "timestamp": int(time.time()),
        "event_type": event_type,
        "severity": severity,
        "tenant_id": tenant_id,
        "detail": detail,
        "ip_hash": ip_hash,
        "ua_hash": ua_hash,
        "path": request.url.path,
        "method": request.method,
        "status": "open",
        "assignee": "root-admin",
    }
    _logger.warning(
        "SECURITY_TELEMETRY event_type=%s severity=%s tenant=%s detail=%s", event_type, severity, tenant_id, detail
    )
    if isinstance(siem_store, list):
        siem_store.append(event)
        max_siem = int(os.getenv("SIEM_CASES_MAX", "5000"))
        if len(siem_store) > max_siem:
            del siem_store[:-max_siem]
    if isinstance(ira_store, list):
        ira_store.append(
            {
                "id": int(time.time() * 1000),
                "tenant_id": tenant_id,
                "event_type": event_type,
                "message": detail,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        max_ira = int(os.getenv("IRA_EVENTS_MAX", "5000"))
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
            key = f"nuxtron:mitm:ipwindow:{tenant_id}"
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
            event_type="mitm_ip_diversity_alert",
            severity="high",
            tenant_id=tenant_id,
            detail=f"Tenant {tenant_id!r} made requests from {distinct_ips} distinct IP hashes within {_MITM_WINDOW_SECONDS}s — possible MITM, session hijack, or shared credential abuse.",
            ip_hash=ip_hash,
            ua_hash="",
        )


async def _audit_api_usage(request: Request, *, tenant_id: str, auth_mode: str, api_key_value: str | None) -> None:
    store_obj = getattr(request.app.state, "api_usage_audit", None)
    if not isinstance(store_obj, list):
        return
    store = cast(list[ApiUsageAuditRecord], store_obj)
    max_items = int(os.getenv("API_USAGE_AUDIT_MAX", "2000"))
    forwarded_for = (request.headers.get("X-Forwarded-For", "") or "").split(",")[0].strip()
    client_host = forwarded_for or (request.client.host if request.client else "")
    ua = request.headers.get("User-Agent", "")
    ip_hash = hashlib.sha256(client_host.encode("utf-8")).hexdigest()[:16] if client_host else ""
    ua_hash = hashlib.sha256(ua.encode("utf-8")).hexdigest()[:16] if ua else ""
    key_fingerprint = hashlib.sha256((api_key_value or "").encode("utf-8")).hexdigest()[:12] if api_key_value else None
    from .domains.identity.security_audit import durable_audit_enabled, record_security_event

    if durable_audit_enabled():
        await asyncio.to_thread(
            record_security_event,
            tenant_id=tenant_id,
            event_type="api_request",
            principal_id="",
            auth_mode=auth_mode,
            method=request.method,
            path=request.url.path,
            request_id=request.headers.get("X-Request-ID", ""),
            client_ip=client_host,
            user_agent=ua,
            metadata={"api_key_fingerprint": key_fingerprint} if key_fingerprint else None,
        )
    store.append(
        {
            "id": len(store) + 1,
            "timestamp": int(time.time()),
            "tenant_id": tenant_id,
            "auth_mode": auth_mode,
            "method": request.method,
            "path": request.url.path,
            "ip_hash": ip_hash,
            "ua_hash": ua_hash,
            "api_key_fingerprint": key_fingerprint,
        }
    )
    if len(store) > max_items:
        del store[:-max_items]
    if ip_hash:
        await _check_mitm_signal(request, tenant_id, ip_hash)
    if not tenant_id or tenant_id in ("", "unknown", "anonymous"):
        _emit_siem_telemetry(
            request,
            event_type="unknown_user_access",
            severity="high",
            tenant_id=tenant_id or "unknown",
            detail="Request authenticated but resolved to empty/unknown tenant_id — possible bypass or misconfigured token.",
            ip_hash=ip_hash,
            ua_hash=ua_hash,
        )
    if auth_mode == "api_key" and api_key_value:
        sensitive_path = any(
            (
                request.url.path.startswith(p)
                for p in ("/api-governance", "/admin", "/super-admin", "/vault", "/siem", "/security", "/pentest")
            )
        )
        if sensitive_path:
            _emit_siem_telemetry(
                request,
                event_type="api_key_on_sensitive_route",
                severity="critical",
                tenant_id=tenant_id,
                detail=f"API key used on sensitive route {request.url.path!r}. This may indicate a bypass attempt. Key fingerprint logged. Consider rotating the key and auditing the caller.",
                ip_hash=ip_hash,
                ua_hash=ua_hash,
            )


def _enforce_query_api_key_policy(request: Request) -> None:
    if "api_key" not in request.query_params:
        return
    path = request.url.path
    is_content_job_stream = path.endswith("/stream") and "/content/generate/jobs/" in path
    is_stream_endpoint = (
        path.endswith("/notifications/stream")
        or (path.endswith("/stream") and "/media/jobs/" in path)
        or is_content_job_stream
    )
    if not (env_bool("ALLOW_QUERY_API_KEY_FOR_STREAM", True) and is_stream_endpoint):
        raise HTTPException(status_code=400, detail="API key must not be sent via query parameters.")


def _enforce_transport_security(forwarded_proto: str, client_cert_verified: str) -> None:
    if env_bool("ENFORCE_HTTPS_HEADER", False):
        scheme = forwarded_proto.split(",")[0].strip().lower()
        if scheme and scheme != "https":
            raise HTTPException(status_code=400, detail="HTTPS is required.")
    if env_bool("REQUIRE_MTLS", False):
        cert_state = client_cert_verified.strip().lower()
        if cert_state not in {"success", "1", "true", "verified"}:
            raise HTTPException(status_code=401, detail="mTLS client certificate verification failed.")


_INSECURE_DEFAULT_SECRETS = frozenset({"change-this-fastapi-key", "change-me", "dev-jwt-signing-key", "secret", ""})


def _is_production_environment() -> bool:
    """Normalize the environment flag so casing variants are not silently dev.

    Only the literal token ``production`` is treated as production. Anything
    else (``prod``, ``PRODUCTION``, ``staging``, unset) is NOT production — but
    we still refuse the known-default secrets everywhere, so a mislabeled
    staging box can't accidentally forge tokens.
    """
    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"


def _resolve_jwt_secret(is_production: bool) -> str:
    """Resolve the JWT signing secret, refusing insecure defaults.

    In production a real ``JWT_SIGNING_KEY`` is mandatory and must differ from
    the shipped defaults. Outside production we allow a fallback to
    ``FASTAPI_API_KEY`` *only if* it has been changed from its default — so a
    forgotten env var in staging still can't produce forgeable tokens.
    """
    jwt_secret = os.getenv("JWT_SIGNING_KEY", "").strip()
    if jwt_secret and jwt_secret not in _INSECURE_DEFAULT_SECRETS:
        return jwt_secret
    if is_production:
        return ""
    fallback = os.getenv("FASTAPI_API_KEY", "").strip()
    if fallback and fallback not in _INSECURE_DEFAULT_SECRETS:
        return fallback
    return ""


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

    Development keeps the historical availability-friendly behavior. Production
    fails closed because accepting a potentially revoked bearer token is an
    authentication-control failure, not a harmless cache miss.
    """
    if not jti:
        return False
    try:
        from .redis_cache import get_redis

        client = await get_redis()
        if client is None:
            if _is_production_environment():
                raise HTTPException(status_code=503, detail="Authentication revocation service unavailable.")
            return False
        return bool(await client.exists(f"{_DENYLIST_PREFIX}{jti}"))
    except Exception:
        if _is_production_environment():
            raise HTTPException(status_code=503, detail="Authentication revocation service unavailable.")
        _logger.warning("Token revocation lookup failed outside production.", exc_info=True)
        return False


async def revoke_token(jti: str, ttl_seconds: int) -> None:
    """Add a ``jti`` to the Redis-backed denylist for the remainder of its life."""
    if not jti or ttl_seconds <= 0:
        return
    try:
        from .redis_cache import get_redis

        client = await get_redis()
        if client is None:
            _logger.warning("Token revocation requested but Redis is unavailable; jti=%s not denylisted.", jti)
            if _is_production_environment():
                raise HTTPException(status_code=503, detail="Authentication revocation service unavailable.")
            return
        await client.setex(f"{_DENYLIST_PREFIX}{jti}", ttl_seconds, "1")
    except Exception:
        _logger.warning("Token revocation failed for jti=%s", jti, exc_info=True)
        if _is_production_environment():
            raise HTTPException(status_code=503, detail="Authentication revocation service unavailable.")


def _authenticate_bearer(
    authorization_value: str, supplied_tenant_id: str, *, is_production: bool
) -> tuple[str, str, str, list[str], str, int]:
    """Return ``(tenant_id, auth_mode, subject, roles, jti, exp)`` for a verified bearer token.

    ``subject`` is the JWT ``sub`` claim (the authenticated user); ``roles`` is
    the JWT ``roles`` claim. Both are propagated to callers so downstream code
    never has to re-parse the token or trust a client-supplied identity/role.
    """
    token = authorization_value[7:].strip()
    jwt_secret = _resolve_jwt_secret(is_production)
    if not jwt_secret:
        raise HTTPException(status_code=401, detail="JWT validation is not configured.")
    valid, claims, error = _jwt_verify_hs256(token, jwt_secret)
    if not valid:
        raise HTTPException(status_code=401, detail=error or "Invalid bearer token.")
    token_tenant = str((claims or {}).get("tenant_id", "")).strip()
    if not token_tenant:
        raise HTTPException(status_code=401, detail="Bearer token is missing a tenant claim.")
    if supplied_tenant_id and token_tenant != supplied_tenant_id:
        raise HTTPException(status_code=403, detail="Token tenant mismatch.")
    tenant_id = token_tenant
    subject = str((claims or {}).get("sub", "")).strip()
    roles = _sanitize_roles((claims or {}).get("roles"))
    jti = str((claims or {}).get("jti", "")).strip()
    exp = int((claims or {}).get("exp", 0) or 0)
    return (tenant_id, "bearer_jwt", subject, roles, jti, exp)


async def _authenticate_oidc_bearer(
    authorization_value: str, supplied_tenant_id: str
) -> tuple[str, str, str, list[str], str, int]:
    """Authenticate an Auth0/OIDC RS256 bearer token when OIDC is configured."""
    token = authorization_value[7:].strip()
    try:
        claims = await verify_oidc_jwt(token)
    except OIDCVerificationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    token_tenant = str(claims.get("organization_id") or claims.get("org_id") or claims.get("tenant_id") or "").strip()
    if supplied_tenant_id and token_tenant != supplied_tenant_id:
        raise HTTPException(status_code=403, detail="Token tenant mismatch.")
    raw_roles = claims.get("roles")
    roles = _sanitize_roles(raw_roles)
    if not roles:
        roles = _sanitize_roles(claims.get("https://nuxtron.com/roles"))
    try:
        exp = int(claims.get("exp", 0) or 0)
    except (TypeError, ValueError):
        exp = 0
    return (
        token_tenant,
        "oidc_bearer",
        str(claims.get("sub", "")).strip(),
        roles,
        str(claims.get("jti", "")).strip(),
        exp,
    )


_AUTH_BOOTSTRAP_PATHS = frozenset(
    {"/auth/register", "/auth/login", "/auth/password-reset/request", "/auth/password-reset/confirm"}
)


def _authenticate_api_key(
    supplied_api_key: str, supplied_tenant_id: str, request_path: str = ""
) -> tuple[str, str, str, list[str], str, int]:
    """Return ``(tenant_id, 'api_key', '', [], '', 0)``. No user identity or roles for key auth."""
    is_test_mode = bool(os.getenv("PYTEST_CURRENT_TEST") and "pytest" in sys.modules)
    is_bootstrap_path = request_path in _AUTH_BOOTSTRAP_PATHS
    if not env_bool("ALLOW_HEADER_API_KEYS", False) and (not is_test_mode) and (not is_bootstrap_path):
        raise HTTPException(status_code=401, detail="Header API keys are disabled. Use bearer tokens.")
    expected = os.getenv("FASTAPI_API_KEY", "change-this-fastapi-key").strip()
    if not supplied_api_key or not hmac.compare_digest(supplied_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key.")
    if not supplied_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header.")
    return (supplied_tenant_id, "api_key", "", [], "", 0)


async def require_auth(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_forwarded_proto: str | None = Header(default=None, alias="X-Forwarded-Proto"),
    x_client_cert_verified: str | None = Header(default=None, alias="X-Client-Cert-Verified"),
) -> AuthContext:
    supplied_api_key = _header_value(x_api_key)
    supplied_tenant_id = _header_value(x_tenant_id)
    authorization_value = _header_value(authorization)
    forwarded_proto = _header_value(x_forwarded_proto)
    client_cert_verified = _header_value(x_client_cert_verified)
    _enforce_query_api_key_policy(request)
    _enforce_transport_security(forwarded_proto, client_cert_verified)
    is_production = _is_production_environment()
    if authorization_value and authorization_value.lower().startswith("bearer "):
        if os.getenv("AUTH0_ISSUER", "").strip() or os.getenv("AUTH0_AUDIENCE", "").strip():
            tenant_id, auth_mode, subject, roles, jti, exp = await _authenticate_oidc_bearer(
                authorization_value, supplied_tenant_id
            )
        else:
            if is_production and (not (os.getenv("PYTEST_CURRENT_TEST") and "pytest" in sys.modules)):
                raise HTTPException(status_code=503, detail="OIDC authentication is not configured.")
            tenant_id, auth_mode, subject, roles, jti, exp = _authenticate_bearer(
                authorization_value, supplied_tenant_id, is_production=is_production
            )
        if jti and await _is_token_revoked(jti):
            raise HTTPException(status_code=401, detail="Token has been revoked.")
    else:
        tenant_id, auth_mode, subject, roles, jti, exp = _authenticate_api_key(
            supplied_api_key, supplied_tenant_id, request.url.path
        )
    await _audit_api_usage(
        request,
        tenant_id=tenant_id,
        auth_mode=auth_mode,
        api_key_value=supplied_api_key if auth_mode == "api_key" else None,
    )
    from .domains.identity.organization_identity import resolve_external_organization

    resolved_organization = resolve_external_organization(tenant_id)
    tenant_id = resolved_organization.tenant_id
    request.state.auth_context = {
        "tenant_id": tenant_id,
        "external_organization_id": resolved_organization.external_organization_id,
        "auth_mode": auth_mode,
        "subject": subject,
        "roles": roles,
        "jti": jti,
    }
    auth_context = AuthContext(
        tenant_id=tenant_id,
        external_organization_id=resolved_organization.external_organization_id,
        auth_mode=auth_mode,
        subject=subject,
        roles=roles,
        jti=jti,
        exp=exp,
    )
    from .domains.identity.security_context import OrganizationContext

    request.state.organization_context = OrganizationContext.from_auth(auth_context)
    return auth_context
