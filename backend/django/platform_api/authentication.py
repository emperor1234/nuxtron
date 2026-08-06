"""DRF authentication that accepts bearer JWTs issued by the FastAPI service.

Background: FastAPI (backend/fastapi/app/deps.py, routers/auth.py) and Django
(this service, via rest_framework_simplejwt) each issue their own HS256 JWTs
today, signed with different secrets and shaped around different identity
models (FastAPI: tenant_id + subject + roles claims, no Django User row;
Django: simplejwt's user_id claim resolving to a real `auth.User`). A token
minted by one service could not be validated by the other, so a session could
not move between them without a full re-login.

This makes FastAPI the single issuer for cross-service identity: this class
validates a FastAPI-issued token here, using the SAME `JWT_SIGNING_KEY`
secret FastAPI resolves in `deps._resolve_jwt_secret` (must be set to the
identical value in both services' environments — see nuxtron/security in
Vault). It does NOT replace Django's own `JWTAuthentication` (simplejwt),
which keeps working for Django-native flows (the admin panel's session auth,
`ThrottledTokenObtainPairView` for Django-only clients) — this is additive,
tried after simplejwt in `DEFAULT_AUTHENTICATION_CLASSES`.

Because a FastAPI-issued token carries no Django `auth.User` row (there is no
tenant/user model on the Django side yet — see platform_api/models.py), a
successful validation returns a lightweight `FastAPIPrincipal`, not a real
Django `User`. Code that needs `request.user` to be a persisted `auth.User`
(the Django admin, anything doing `request.user.pk`-based ORM lookups) will
not work against a FastAPI-issued token — that is expected: this class is for
API endpoints that only need tenant/subject/role identity, mirroring what
`AuthContext` gives FastAPI routers.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

# Keep in sync with backend/fastapi/app/deps.py::_INSECURE_DEFAULT_SECRETS —
# a token signed with one of these must never validate on either side.
_INSECURE_DEFAULT_SECRETS = frozenset({
    'change-this-fastapi-key',
    'change-me',
    'dev-jwt-signing-key',
    'secret',
    '',
})


class FastAPIPrincipal:
    """Minimal authenticated-principal object for a FastAPI-issued token.

    Deliberately NOT a Django `auth.User` — see module docstring. Duck-types
    just enough of the `User`/`AnonymousUser` contract for
    `IsAuthenticated`/`request.user` checks to work.
    """

    is_authenticated = True
    is_anonymous = False
    is_active = True

    def __init__(self, *, tenant_id: str, subject: str, roles: list[str], jti: str) -> None:
        self.tenant_id = tenant_id
        self.subject = subject
        self.roles = roles
        self.jti = jti
        # Common DRF/logging code paths read `.pk`/`.id`/`.username` defensively;
        # give them a stable, non-None value rather than raising AttributeError.
        self.pk = None
        self.id = None
        self.username = subject or f'fastapi:{tenant_id}'

    def __str__(self) -> str:
        return self.username


def _b64url_decode(raw: str) -> bytes:
    padding = '=' * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode('ascii'))


def _resolve_shared_jwt_secret() -> str:
    """Mirror FastAPI's deps._resolve_jwt_secret resolution/fallback rules.

    Production requires JWT_SIGNING_KEY to be set to a non-default value.
    Non-production allows falling back to FASTAPI_API_KEY (also only if
    non-default) so a forgotten env var in staging still can't forge tokens.
    """
    jwt_secret = os.environ.get('JWT_SIGNING_KEY', '').strip()
    if jwt_secret and jwt_secret not in _INSECURE_DEFAULT_SECRETS:
        return jwt_secret

    if getattr(settings, 'IS_PRODUCTION', True):
        return ''

    fallback = os.environ.get('FASTAPI_API_KEY', '').strip()
    if fallback and fallback not in _INSECURE_DEFAULT_SECRETS:
        return fallback
    return ''


def _verify_hs256(token: str, secret: str) -> dict[str, Any] | None:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        head, body, sig = parts
        signing_input = f'{head}.{body}'.encode('ascii')
        expected_sig = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(sig)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(_b64url_decode(body).decode('utf-8'))
        if not isinstance(payload, dict):
            return None
        exp = int(payload.get('exp', 0) or 0)
        if exp and time.time() > exp:
            return None
        return payload
    except Exception:
        return None


class FastAPIJWTAuthentication(BaseAuthentication):
    """Accepts an `Authorization: Bearer <token>` issued by FastAPI's
    `/auth/login`, `/auth/register`, or `/auth/jwt/issue`.

    Only tokens with `iss == 'nuxtron-fastapi'` are considered — this keeps
    the class from ever being asked to adjudicate a Django-issued (simplejwt)
    token that happens to reach it first in the auth-class chain (DRF tries
    each configured authenticator in order and moves on if one returns None).
    """

    keyword = 'Bearer'

    def authenticate(self, request: Any) -> tuple[FastAPIPrincipal, str] | None:
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.lower().startswith('bearer '):
            return None
        token = auth_header[7:].strip()
        if not token:
            return None

        secret = _resolve_shared_jwt_secret()
        if not secret:
            return None

        claims = _verify_hs256(token, secret)
        if claims is None:
            return None
        if claims.get('iss') != 'nuxtron-fastapi':
            # Not a FastAPI-issued token (or missing the marker) — let the
            # next authenticator (Django's own JWTAuthentication) try it.
            return None

        tenant_id = str(claims.get('tenant_id', '')).strip()
        if not tenant_id:
            raise AuthenticationFailed('Bearer token is missing a tenant claim.')

        subject = str(claims.get('sub', '')).strip()
        roles_raw = claims.get('roles')
        roles = [r for r in roles_raw if isinstance(r, str)] if isinstance(roles_raw, list) else []
        jti = str(claims.get('jti', '')).strip()

        principal = FastAPIPrincipal(tenant_id=tenant_id, subject=subject, roles=roles, jti=jti)
        return principal, token

    def authenticate_header(self, request: Any) -> str:
        return self.keyword
