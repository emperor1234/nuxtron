import hashlib
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Protocol, TypedDict, cast
from urllib.parse import urlparse

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..authz import has_any_role
from ..deps import AuthContext, JwtClaims, _is_production_environment, _resolve_jwt_secret, require_auth, revoke_token
from ..saml_sso import is_saml_enabled, login_url, metadata_xml  # pyright: ignore[reportUnknownVariableType]
from ..saml_sso import process_acs as raw_process_acs
from ..security_redis import fixed_window_increment, reset_counter

# Type alias for dependency injection
AuthDep = Annotated[AuthContext, Depends(require_auth)]
SAML_DISABLED_MESSAGE = 'SAML is disabled.'
JsonObject = dict[str, object]

# Claims that establish identity, scope, or lifetime. A caller may never supply
# these through JwtIssueRequest.additional_claims; the server always owns them.
_RESERVED_JWT_CLAIMS = frozenset({'sub', 'tenant_id', 'roles', 'iat', 'exp', 'iss', 'jti'})


def _validate_relay_state(relay_state: str | None) -> str | None:
    """Validate relay_state to prevent open-redirect attacks.

    Only relative paths (starting with /) or URLs matching the configured
    SAML_PUBLIC_BASE_URL are permitted.  Anything else is silently dropped.
    """
    if relay_state is None:
        return None
    rs = relay_state.strip()
    if not rs:
        return None
    # Allow relative paths — safe by definition
    if rs.startswith('/'):
        # Reject protocol-relative URLs (//evil.com)
        if rs.startswith('//'):
            return None
        return rs
    # Allow absolute URLs whose origin matches the configured SP base
    base = os.getenv('SAML_PUBLIC_BASE_URL', '').strip().rstrip('/')
    if base:
        try:
            parsed = urlparse(rs)
            base_parsed = urlparse(base)
            if parsed.scheme == base_parsed.scheme and parsed.netloc == base_parsed.netloc:
                return rs
        except Exception:
            pass
    # Everything else is rejected
    return None


class RateLimiter(Protocol):
    def __call__(self, key: str, *, limit: int, window_seconds: int) -> None: ...


class TotpVerifier(Protocol):
    def __call__(self, secret: str, code: str, *, window: int = 1) -> bool: ...


class JwtSigner(Protocol):
    def __call__(self, payload: JsonObject, secret: str) -> str: ...


class JwtVerifier(Protocol):
    def __call__(self, token: str, secret: str) -> tuple[bool, JwtClaims | None, str | None]: ...


class AuthSecurityRecord(TypedDict, total=False):
    id: int
    tenant_id: str
    type: str
    account_name: str
    valid: bool
    subject: str
    jti: str
    created_at: str


class SamlAssertion(TypedDict, total=False):
    name_id: str
    attributes: dict[str, object]


process_saml_acs = cast(Callable[[Request, str], SamlAssertion], raw_process_acs)


class TotpSetupRequest(BaseModel):
    account_name: str = Field(default='user@nuxtron.local', min_length=3, max_length=180)
    issuer: str = Field(default='Nuxtron', min_length=2, max_length=80)


class TotpVerifyRequest(BaseModel):
    secret: str = Field(min_length=16, max_length=128)
    code: str = Field(min_length=6, max_length=8)
    window: int = Field(default=1, ge=0, le=3)


class JwtIssueRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=180)
    # 24h cap, down from a prior 7-day cap. This endpoint mints a NEW token
    # from an EXISTING one — it must never be a way to extend a session's
    # effective lifetime far beyond what re-authentication would give you.
    expires_in_seconds: int = Field(default=3600, ge=60, le=86400)
    roles: list[str] = Field(default_factory=list, max_length=20)
    additional_claims: dict[str, object] = Field(default_factory=dict)


class JwtVerifyRequest(BaseModel):
    token: str = Field(min_length=20, max_length=12000)


class SamlAcsRequest(BaseModel):
    saml_response: str = Field(min_length=40)
    relay_state: str | None = Field(default=None, max_length=2048)


def _register_totp_routes(
    router: APIRouter,
    *,
    enforce_rate_limit: RateLimiter,
    totp_secret: Callable[[], str],
    totp_verify: TotpVerifier,
    auth_security_memory: list[AuthSecurityRecord],
) -> None:
    @router.post('/auth/totp/setup')
    def auth_totp_setup(payload: TotpSetupRequest, auth: AuthDep) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:auth:totp:setup', limit=30, window_seconds=60)
        secret = totp_secret()
        issuer = payload.issuer.strip()
        account_name = payload.account_name.strip()
        otpauth = f'otpauth://totp/{issuer}:{account_name}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30'

        auth_security_memory.append({
            'id': len(auth_security_memory) + 1,
            'tenant_id': auth.tenant_id,
            'type': 'totp-setup',
            'account_name': account_name,
            'created_at': datetime.now(UTC).isoformat(),
        })

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'result': {
                'secret': secret,
                'issuer': issuer,
                'account_name': account_name,
                'otpauth_url': otpauth,
            },
        }

    @router.post('/auth/totp/verify')
    def auth_totp_verify(payload: TotpVerifyRequest, auth: AuthDep) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:auth:totp:verify', limit=90, window_seconds=60)
        code = payload.code.strip()
        is_valid = totp_verify(payload.secret.strip(), code, window=payload.window)

        auth_security_memory.append({
            'id': len(auth_security_memory) + 1,
            'tenant_id': auth.tenant_id,
            'type': 'totp-verify',
            'valid': is_valid,
            'created_at': datetime.now(UTC).isoformat(),
        })

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'valid': is_valid,
        }


def _register_jwt_routes(
    router: APIRouter,
    *,
    enforce_rate_limit: RateLimiter,
    jwt_sign_hs256: JwtSigner,
    jwt_verify_hs256: JwtVerifier,
    auth_security_memory: list[AuthSecurityRecord],
) -> None:
    @router.post(
        '/auth/jwt/issue',
        responses={
            403: {'description': 'Cannot issue a token for another subject or with roles you do not hold.'},
        },
    )
    def auth_jwt_issue(payload: JwtIssueRequest, auth: AuthDep) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:auth:jwt:issue', limit=120, window_seconds=60)

        # A shared API key carries no user identity, so it must never be able to
        # mint a token asserting one. Only an already-authenticated user session
        # (a bearer JWT) can request a new token, and — unless the caller holds
        # an elevated role — only for themselves, with no more roles than they
        # already have. This closes an impersonation path where any API-key
        # holder could previously mint an arbitrary-subject, arbitrary-role,
        # long-lived token for any user in the tenant.
        if auth.auth_mode != 'bearer_jwt':
            raise HTTPException(
                status_code=403,
                detail='Token issuance requires an authenticated bearer session, not an API key.',
            )
        privileged = has_any_role(auth, 'token_issuer')
        if not privileged and payload.subject != auth.subject:
            raise HTTPException(status_code=403, detail='Cannot issue a token for a different subject.')
        if not privileged and not set(payload.roles).issubset(set(auth.roles)):
            raise HTTPException(status_code=403, detail='Cannot issue a token with roles you do not hold.')

        secret = _resolve_jwt_secret(_is_production_environment())
        if not secret:
            raise HTTPException(status_code=401, detail='JWT signing is not configured.')
        now = int(time.time())
        exp = now + payload.expires_in_seconds
        jti = hashlib.sha256(f'{auth.tenant_id}:{payload.subject}:{now}:{os.urandom(8).hex()}'.encode()).hexdigest()[:24]

        # Caller-supplied extras are merged *under* the reserved claims, never
        # over them. Merging after would let any authenticated user hand back
        # additional_claims={'tenant_id': <victim>, 'roles': ['super_admin']}
        # and have the server sign it, defeating the subject/role checks above.
        extra_claims = {
            key: value for key, value in payload.additional_claims.items() if key not in _RESERVED_JWT_CLAIMS
        }
        claims: JsonObject = {
            **extra_claims,
            'sub': payload.subject,
            'tenant_id': auth.tenant_id,
            'roles': payload.roles,
            'iat': now,
            'exp': exp,
            'iss': 'nuxtron-fastapi',
            'jti': jti,
        }
        token = jwt_sign_hs256(claims, secret)

        auth_security_memory.append({
            'id': len(auth_security_memory) + 1,
            'tenant_id': auth.tenant_id,
            'type': 'jwt-issue',
            'subject': payload.subject,
            'jti': jti,
            'created_at': datetime.now(UTC).isoformat(),
        })

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'result': {
                'token': token,
                'expires_at': datetime.fromtimestamp(exp, tz=UTC).isoformat(),
                'jti': jti,
                'signing_source': 'jwt-signing-key' if os.getenv('JWT_SIGNING_KEY', '').strip() else 'fastapi-api-key-fallback',
            },
        }

    @router.post('/auth/logout')
    async def auth_logout(auth: AuthDep) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        """Revoke the bearer token used to authenticate this request.

        No-op (but still ``200 ok``) for API-key auth, which has no per-token
        session to revoke. TTL matches the token's own remaining lifetime so
        the denylist entry never outlives the token it is blocking.
        """
        if auth.auth_mode == 'bearer_jwt' and auth.jti:
            ttl = max(int(auth.exp - time.time()), 1) if auth.exp else 86400
            await revoke_token(auth.jti, ttl)
            auth_security_memory.append({
                'id': len(auth_security_memory) + 1,
                'tenant_id': auth.tenant_id,
                'type': 'logout',
                'subject': auth.subject,
                'jti': auth.jti,
                'created_at': datetime.now(UTC).isoformat(),
            })
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'result': {'revoked': bool(auth.jti)}}

    @router.post('/auth/jwt/verify')
    def auth_jwt_verify(payload: JwtVerifyRequest, auth: AuthDep) -> JsonObject:  # pyright: ignore[reportUnusedFunction]
        enforce_rate_limit(f'{auth.tenant_id}:auth:jwt:verify', limit=300, window_seconds=60)
        secret = _resolve_jwt_secret(_is_production_environment())
        if not secret:
            raise HTTPException(status_code=401, detail='JWT validation is not configured.')
        valid, claims, error = jwt_verify_hs256(payload.token.strip(), secret)
        token_tenant = str((claims or {}).get('tenant_id', '')) if claims else ''

        if valid and token_tenant != auth.tenant_id:
            valid = False
            error = 'Token tenant mismatch.'

        auth_security_memory.append({
            'id': len(auth_security_memory) + 1,
            'tenant_id': auth.tenant_id,
            'type': 'jwt-verify',
            'valid': valid,
            'created_at': datetime.now(UTC).isoformat(),
        })

        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'valid': valid,
            'claims': claims if valid else None,
            'error': None if valid else error,
        }


def _ensure_saml_enabled() -> None:
    if not is_saml_enabled():
        raise HTTPException(status_code=503, detail=SAML_DISABLED_MESSAGE)


def _resolve_saml_tenant_id(assertion: SamlAssertion) -> str:
    attributes = assertion.get('attributes', {})
    tenant_attribute = os.getenv('SAML_TENANT_ATTRIBUTE', 'tenant_id').strip()
    tenant_candidates = attributes.get(tenant_attribute)
    tenant_id = ''
    if isinstance(tenant_candidates, list) and tenant_candidates:
        first_candidate = cast(list[object], tenant_candidates)[0]
        tenant_id = first_candidate.strip() if isinstance(first_candidate, str) else str(first_candidate).strip()
    if not tenant_id:
        tenant_id = os.getenv('SAML_DEFAULT_TENANT_ID', '').strip()
    if not tenant_id:
        raise HTTPException(status_code=400, detail=f'Missing tenant mapping in SAML assertion (attribute: {tenant_attribute}).')
    return tenant_id


def _resolve_saml_subject(assertion: SamlAssertion) -> str:
    subject = str(assertion.get('name_id', '')).strip()
    if not subject:
        raise HTTPException(status_code=400, detail='SAML assertion did not provide NameID.')
    return subject


def _issue_saml_jwt(
    *,
    tenant_id: str,
    subject: str,
    jwt_sign_hs256: JwtSigner,
) -> tuple[str, int, str]:
    secret = _resolve_jwt_secret(_is_production_environment())
    if not secret:
        raise HTTPException(status_code=401, detail='JWT signing is not configured.')
    now = int(time.time())
    exp = now + int(os.getenv('SAML_SESSION_SECONDS', '900'))
    jti = hashlib.sha256(f'{tenant_id}:{subject}:{now}:{os.urandom(8).hex()}'.encode()).hexdigest()[:24]
    claims: JsonObject = {
        'sub': subject,
        'tenant_id': tenant_id,
        'roles': ['saml_user'],
        'auth_method': 'saml',
        'iat': now,
        'exp': exp,
        'iss': 'nuxtron-fastapi',
        'jti': jti,
    }
    token = jwt_sign_hs256(claims, secret)
    return token, exp, jti


class _SamlRouteHandlers:
    def __init__(
        self,
        *,
        jwt_sign_hs256: JwtSigner,
        auth_security_memory: list[AuthSecurityRecord],
    ) -> None:
        self.jwt_sign_hs256 = jwt_sign_hs256
        self.auth_security_memory = auth_security_memory

    def metadata(self, request: Request) -> JsonObject:
        _ensure_saml_enabled()
        try:
            xml = metadata_xml(request)
            return {'status': 'ok', 'metadata_xml': xml}
        except Exception as ex:
            raise HTTPException(status_code=500, detail=str(ex)) from ex

    def login(self, request: Request, relay_state: str | None = None) -> JsonObject:
        _ensure_saml_enabled()
        # Validate relay_state before passing to the toolkit to prevent open redirect
        safe_relay = _validate_relay_state(relay_state)
        try:
            url = login_url(request, relay_state=safe_relay)
            return {'status': 'ok', 'redirect_url': url}
        except Exception as ex:
            raise HTTPException(status_code=500, detail=str(ex)) from ex

    def acs(self, payload: SamlAcsRequest, request: Request) -> JsonObject:
        _ensure_saml_enabled()
        try:
            assertion = process_saml_acs(request, payload.saml_response)
        except Exception as ex:
            raise HTTPException(status_code=401, detail=str(ex)) from ex

        tenant_id = _resolve_saml_tenant_id(assertion)
        subject = _resolve_saml_subject(assertion)
        token, exp, jti = _issue_saml_jwt(
            tenant_id=tenant_id,
            subject=subject,
            jwt_sign_hs256=self.jwt_sign_hs256,
        )

        self.auth_security_memory.append({
            'id': len(self.auth_security_memory) + 1,
            'tenant_id': tenant_id,
            'type': 'saml-login',
            'subject': subject,
            'jti': jti,
            'created_at': datetime.now(UTC).isoformat(),
        })

        # Validate relay_state before echoing it back to the caller
        safe_relay = _validate_relay_state(payload.relay_state)

        return {
            'status': 'ok',
            'tenant_id': tenant_id,
            'result': {
                'token': token,
                'expires_at': datetime.fromtimestamp(exp, tz=UTC).isoformat(),
                'subject': subject,
                'auth_method': 'saml',
                'relay_state': safe_relay,
            },
        }


def _register_saml_routes(
    router: APIRouter,
    *,
    jwt_sign_hs256: JwtSigner,
    auth_security_memory: list[AuthSecurityRecord],
) -> None:
    handlers = _SamlRouteHandlers(
        jwt_sign_hs256=jwt_sign_hs256,
        auth_security_memory=auth_security_memory,
    )
    router.add_api_route(
        '/auth/saml/metadata',
        handlers.metadata,
        methods=['GET'],
        responses={
            503: {'description': SAML_DISABLED_MESSAGE},
            500: {'description': 'SAML metadata generation failed.'},
        },
    )
    router.add_api_route(
        '/auth/saml/login',
        handlers.login,
        methods=['GET'],
        responses={
            503: {'description': SAML_DISABLED_MESSAGE},
            500: {'description': 'SAML login URL generation failed.'},
        },
    )
    router.add_api_route(
        '/auth/saml/acs',
        handlers.acs,
        methods=['POST'],
        responses={
            503: {'description': SAML_DISABLED_MESSAGE},
            401: {'description': 'SAML assertion validation failed.'},
            400: {'description': 'SAML assertion missing required tenant or subject mapping.'},
        },
    )


class UserRegisterRequest(BaseModel):
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=10, max_length=1024)
    first_name: str = Field(default='', max_length=100)
    last_name: str = Field(default='', max_length=100)


class UserLoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=1, max_length=1024)


class PasswordResetRequestPayload(BaseModel):
    email: str = Field(min_length=5, max_length=180)


class PasswordResetConfirmPayload(BaseModel):
    email: str = Field(min_length=5, max_length=180)
    token: str = Field(min_length=16, max_length=128)
    new_password: str = Field(min_length=10, max_length=1024)


def _register_user_auth_routes(
    router: APIRouter,
    *,
    enforce_rate_limit: RateLimiter,
    jwt_sign_hs256: JwtSigner,
    hash_password: Callable[[str], str],
    verify_password: Callable[[str, str], bool],
    encrypt_value: Callable[[str], str],
    hash_email: Callable[[str], str],
    get_db_ready: Callable[[], bool],
    db_dsn: Callable[[], str],
    users_memory: list[JsonObject],
    auth_security_memory: list[AuthSecurityRecord],
) -> None:
    handlers = _UserAuthHandlers(
        jwt_sign_hs256=jwt_sign_hs256,
        hash_password=hash_password,
        verify_password=verify_password,
        encrypt_value=encrypt_value,
        hash_email=hash_email,
        get_db_ready=get_db_ready,
        db_dsn=db_dsn,
        users_memory=users_memory,
        auth_security_memory=auth_security_memory,
        enforce_rate_limit=enforce_rate_limit,
    )
    router.add_api_route(
        '/auth/register',
        handlers.register,
        methods=['POST'],
        responses={409: {'description': 'Email already registered.'}},
    )
    router.add_api_route(
        '/auth/login',
        handlers.login,
        methods=['POST'],
        responses={401: {'description': 'Invalid credentials.'}},
    )
    router.add_api_route(
        '/auth/password-reset/request',
        handlers.request_reset,
        methods=['POST'],
    )
    router.add_api_route(
        '/auth/password-reset/confirm',
        handlers.confirm_reset,
        methods=['POST'],
        responses={400: {'description': 'Invalid or expired reset token.'}},
    )


class _UserStore:
    """Thin adapter that routes DB or memory operations for user records."""

    def __init__(
        self,
        *,
        get_db_ready: Callable[[], bool],
        db_dsn: Callable[[], str],
        users_memory: list[JsonObject],
    ) -> None:
        self._get_db_ready = get_db_ready
        self._db_dsn = db_dsn
        self._mem = users_memory

    # ── helpers ──────────────────────────────────────────────────────────

    def _find_mem(self, tenant_id: str, email_hash: str) -> JsonObject | None:
        for u in self._mem:
            if u.get('tenant_id') == tenant_id and u.get('email_hash') == email_hash:
                return u
        return None

    # ── public interface ──────────────────────────────────────────────────

    def email_exists(self, tenant_id: str, email_hash: str) -> bool:
        if self._get_db_ready():
            with psycopg.connect(self._db_dsn()) as conn, conn.cursor() as cur:
                cur.execute(
                    'SELECT 1 FROM users WHERE tenant_id = %s AND email_hash = %s LIMIT 1',
                    (tenant_id, email_hash),
                )
                return cur.fetchone() is not None
        return self._find_mem(tenant_id, email_hash) is not None

    def create_user(
        self,
        tenant_id: str,
        email_hash: str,
        email_cipher: str,
        pw_hash: str,
        name_cipher: str,
        roles: list[str] | None = None,
    ) -> int:
        roles_csv = ','.join(roles) if roles else 'user'
        if self._get_db_ready():
            with psycopg.connect(self._db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO users (tenant_id, email_hash, email_cipher, password_hash, name_cipher, roles)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                        """,
                        (tenant_id, email_hash, email_cipher, pw_hash, name_cipher or None, roles_csv),
                    )
                    row = cur.fetchone()
                conn.commit()
            return int(row[0]) if row else 1
        user_id = len(self._mem) + 1
        self._mem.append({
            'id': user_id,
            'tenant_id': tenant_id,
            'email_hash': email_hash,
            'email_cipher': email_cipher,
            'password_hash': pw_hash,
            'name_cipher': name_cipher,
            'is_verified': False,
            'reset_token': None,
            'reset_token_expires': None,
            'roles': roles_csv,
            'created_at': datetime.now(UTC).isoformat(),
        })
        return user_id

    def fetch_password_hash(self, tenant_id: str, email_hash: str) -> tuple[int, str, list[str]] | None:
        if self._get_db_ready():
            with psycopg.connect(self._db_dsn()) as conn, conn.cursor() as cur:
                cur.execute(
                    'SELECT id, password_hash, roles FROM users WHERE tenant_id = %s AND email_hash = %s LIMIT 1',
                    (tenant_id, email_hash),
                )
                row = cur.fetchone()
            if not row:
                return None
            roles = [role for role in str(row[2] or 'user').split(',') if role]
            return int(row[0]), str(row[1]), roles or ['user']
        user = self._find_mem(tenant_id, email_hash)
        if not user:
            return None
        roles = [role for role in str(user.get('roles') or 'user').split(',') if role]
        return int(str(user['id'])), str(user['password_hash']), roles or ['user']

    def set_reset_token(self, tenant_id: str, email_hash: str, token: str, expires_ts: int) -> bool:
        if self._get_db_ready():
            with psycopg.connect(self._db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET reset_token = %s, reset_token_expires = TO_TIMESTAMP(%s), updated_at = NOW()
                        WHERE tenant_id = %s AND email_hash = %s RETURNING id
                        """,
                        (token, expires_ts, tenant_id, email_hash),
                    )
                    found = cur.fetchone() is not None
                conn.commit()
            return found
        user = self._find_mem(tenant_id, email_hash)
        if not user:
            return False
        user['reset_token'] = token
        user['reset_token_expires'] = expires_ts
        return True

    def consume_reset_token(
        self,
        tenant_id: str,
        email_hash: str,
        token: str,
        new_pw_hash: str,
        now_ts: int,
    ) -> bool:
        if self._get_db_ready():
            with psycopg.connect(self._db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, reset_token, EXTRACT(EPOCH FROM reset_token_expires)::BIGINT
                        FROM users WHERE tenant_id = %s AND email_hash = %s LIMIT 1
                        """,
                        (tenant_id, email_hash),
                    )
                    row = cur.fetchone()
                    if not row or str(row[1]) != token:
                        return False
                    if row[2] is not None and int(row[2]) < now_ts:
                        return False
                    cur.execute(
                        """
                        UPDATE users SET password_hash = %s, reset_token = NULL,
                            reset_token_expires = NULL, updated_at = NOW()
                        WHERE id = %s
                        """,
                        (new_pw_hash, int(row[0])),
                    )
                conn.commit()
            return True
        user = self._find_mem(tenant_id, email_hash)
        if not user:
            return False
        if str(user.get('reset_token', '')) != token:
            return False
        exp = user.get('reset_token_expires')
        if exp is not None and int(str(exp)) < now_ts:
            return False
        user['password_hash'] = new_pw_hash
        user['reset_token'] = None
        user['reset_token_expires'] = None
        return True


class _UserAuthHandlers:
    def __init__(
        self,
        *,
        jwt_sign_hs256: JwtSigner,
        hash_password: Callable[[str], str],
        verify_password: Callable[[str, str], bool],
        encrypt_value: Callable[[str], str],
        hash_email: Callable[[str], str],
        get_db_ready: Callable[[], bool],
        db_dsn: Callable[[], str],
        users_memory: list[JsonObject],
        auth_security_memory: list[AuthSecurityRecord],
        enforce_rate_limit: RateLimiter,
    ) -> None:
        self._sign = jwt_sign_hs256
        self._hash_pw = hash_password
        self._verify_pw = verify_password
        self._encrypt = encrypt_value
        self._hash_email = hash_email
        self._security_mem = auth_security_memory
        self._rl = enforce_rate_limit
        self._store = _UserStore(
            get_db_ready=get_db_ready,
            db_dsn=db_dsn,
            users_memory=users_memory,
        )

    def _issue_jwt(self, tenant_id: str, user_id: int, email: str, roles: list[str] | None = None) -> tuple[str, int]:
        secret = _resolve_jwt_secret(_is_production_environment())
        if not secret:
            raise HTTPException(status_code=401, detail='JWT signing is not configured.')
        now = int(time.time())
        exp = now + 3600
        jti = hashlib.sha256(f'{tenant_id}:{user_id}:{now}:{os.urandom(8).hex()}'.encode()).hexdigest()[:24]
        claims: JsonObject = {
            'sub': str(user_id),
            'tenant_id': tenant_id,
            'email': email,
            'roles': roles or ['user'],
            'iat': now,
            'exp': exp,
            'iss': 'nuxtron-fastapi',
            'jti': jti,
        }
        return self._sign(claims, secret), exp

    def _log(self, tenant_id: str, event_type: str, subject: str) -> None:
        self._security_mem.append({
            'id': len(self._security_mem) + 1,
            'tenant_id': tenant_id,
            'type': event_type,
            'subject': subject,
            'created_at': datetime.now(UTC).isoformat(),
        })

    def register(self, payload: UserRegisterRequest, auth: AuthDep) -> JsonObject:
        self._rl(f'{auth.tenant_id}:auth:register', limit=10, window_seconds=60)
        email_clean = payload.email.strip().lower()
        email_hash = self._hash_email(email_clean)

        if self._store.email_exists(auth.tenant_id, email_hash):
            raise HTTPException(status_code=409, detail='An account with this email already exists.')

        # No self-service path to 'admin' — every self-registered user gets
        # the baseline 'user' role, full stop. Admin is granted only through
        # the Django superadmin console, out of band from this endpoint, so
        # there is no way for a registrant to escalate themselves or anyone
        # else by being first, by tenant name, or by any other client-visible
        # signal.
        roles = ['user']

        email_cipher = self._encrypt(email_clean)
        pw_hash = self._hash_pw(payload.password)
        name_raw = f'{payload.first_name.strip()} {payload.last_name.strip()}'.strip()
        name_cipher = self._encrypt(name_raw) if name_raw else ''
        user_id = self._store.create_user(auth.tenant_id, email_hash, email_cipher, pw_hash, name_cipher, roles=roles)

        token, exp = self._issue_jwt(auth.tenant_id, user_id, email_clean, roles=roles)
        self._log(auth.tenant_id, 'user-register', email_clean)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'result': {
                'token': token,
                'expires_at': datetime.fromtimestamp(exp, tz=UTC).isoformat(),
            },
        }

    def login(self, payload: UserLoginRequest, auth: AuthDep, request: Request) -> JsonObject:
        # Tenant-wide limiter: coarse protection against overall abuse, but a
        # single busy tenant sharing this budget across all its users means it
        # is NOT sufficient brute-force protection for one targeted account.
        self._rl(f'{auth.tenant_id}:auth:login', limit=20, window_seconds=60)
        email_clean = payload.email.strip().lower()
        email_hash = self._hash_email(email_clean)

        # Per-account and per-IP limiters: the actual brute-force protection.
        # Keyed independently of the tenant-wide limiter above so one noisy
        # tenant can't starve another's login budget, and so a single account
        # under attack gets throttled even while the tenant overall is quiet.
        client_ip = self._client_ip(request)
        account_key = f'nuxtron:bruteforce:login:acct:{auth.tenant_id}:{email_hash}'
        ip_key = f'nuxtron:bruteforce:login:ip:{hashlib.sha256(client_ip.encode()).hexdigest()[:16]}'
        account_ok, _ = fixed_window_increment(account_key, limit=8, window_seconds=300)
        ip_ok, _ = fixed_window_increment(ip_key, limit=30, window_seconds=300)
        if not account_ok or not ip_ok:
            self._log(auth.tenant_id, 'user-login-throttled', email_clean)
            raise HTTPException(status_code=429, detail='Too many login attempts. Try again shortly.')

        record = self._store.fetch_password_hash(auth.tenant_id, email_hash)
        if not record or not self._verify_pw(payload.password, record[1]):
            # Only failures count toward the lockout window — a successful
            # login below resets it, so legitimate rapid logins are never
            # penalized, and every failure is now auditable as such (previously
            # failed attempts were indistinguishable from "never happened").
            self._log(auth.tenant_id, 'user-login-failed', email_clean)
            raise HTTPException(status_code=401, detail='Invalid email or password.')

        reset_counter(account_key)
        token, exp = self._issue_jwt(auth.tenant_id, record[0], email_clean, roles=record[2])
        self._log(auth.tenant_id, 'user-login', email_clean)
        return {
            'status': 'ok',
            'tenant_id': auth.tenant_id,
            'result': {
                'token': token,
                'expires_at': datetime.fromtimestamp(exp, tz=UTC).isoformat(),
            },
        }

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded_for = (request.headers.get('X-Forwarded-For', '') or '').split(',')[0].strip()
        return forwarded_for or (request.client.host if request.client else 'unknown')

    def request_reset(self, payload: PasswordResetRequestPayload, auth: AuthDep) -> JsonObject:
        self._rl(f'{auth.tenant_id}:auth:reset:req', limit=5, window_seconds=60)
        email_clean = payload.email.strip().lower()
        email_hash = self._hash_email(email_clean)
        reset_token = os.urandom(32).hex()
        expires_ts = int(time.time()) + 3600

        found = self._store.set_reset_token(auth.tenant_id, email_hash, reset_token, expires_ts)
        result: JsonObject = {'message': 'If your account exists, a reset link has been sent.'}
        is_prod = os.getenv('ENVIRONMENT', 'development').strip().lower() == 'production'
        if not is_prod and found:
            result['dev_reset_token'] = reset_token
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'result': result}

    def confirm_reset(self, payload: PasswordResetConfirmPayload, auth: AuthDep) -> JsonObject:
        self._rl(f'{auth.tenant_id}:auth:reset:confirm', limit=10, window_seconds=60)
        email_clean = payload.email.strip().lower()
        email_hash = self._hash_email(email_clean)
        new_pw_hash = self._hash_pw(payload.new_password)

        ok = self._store.consume_reset_token(
            auth.tenant_id, email_hash, payload.token, new_pw_hash, int(time.time())
        )
        if not ok:
            raise HTTPException(status_code=400, detail='Invalid or expired reset token.')
        return {'status': 'ok', 'tenant_id': auth.tenant_id, 'result': {'message': 'Password updated successfully.'}}


def create_auth_router(
    *,
    enforce_rate_limit: RateLimiter,
    totp_secret: Callable[[], str],
    totp_verify: TotpVerifier,
    jwt_sign_hs256: JwtSigner,
    jwt_verify_hs256: JwtVerifier,
    auth_security_memory: list[AuthSecurityRecord],
    hash_password: Callable[[str], str] | None = None,
    verify_password: Callable[[str, str], bool] | None = None,
    encrypt_value: Callable[[str], str] | None = None,
    hash_email: Callable[[str], str] | None = None,
    get_db_ready: Callable[[], bool] | None = None,
    db_dsn: Callable[[], str] | None = None,
    users_memory: list[JsonObject] | None = None,
) -> APIRouter:
    router = APIRouter()
    _register_totp_routes(
        router,
        enforce_rate_limit=enforce_rate_limit,
        totp_secret=totp_secret,
        totp_verify=totp_verify,
        auth_security_memory=auth_security_memory,
    )
    _register_jwt_routes(
        router,
        enforce_rate_limit=enforce_rate_limit,
        jwt_sign_hs256=jwt_sign_hs256,
        jwt_verify_hs256=jwt_verify_hs256,
        auth_security_memory=auth_security_memory,
    )
    _register_saml_routes(
        router,
        jwt_sign_hs256=jwt_sign_hs256,
        auth_security_memory=auth_security_memory,
    )
    if (hash_password is not None and verify_password is not None
            and encrypt_value is not None and hash_email is not None
            and get_db_ready is not None and db_dsn is not None
            and users_memory is not None):
        _register_user_auth_routes(
            router,
            enforce_rate_limit=enforce_rate_limit,
            jwt_sign_hs256=jwt_sign_hs256,
            hash_password=hash_password,
            verify_password=verify_password,
            encrypt_value=encrypt_value,
            hash_email=hash_email,
            get_db_ready=get_db_ready,
            db_dsn=db_dsn,
            users_memory=users_memory,
            auth_security_memory=auth_security_memory,
        )

    return router