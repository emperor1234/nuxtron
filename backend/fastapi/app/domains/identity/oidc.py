"""Small, dependency-light OIDC JWT verification adapter.

Production identity providers publish RSA signing keys through JWKS. This module
keeps network access and cryptographic verification behind one narrow seam so the
request dependency can remain testable and the provider can later be swapped.
"""

from __future__ import annotations


import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.hashes import SHA256

_logger = logging.getLogger("nuxtron.security.oidc")
_ALLOWED_ALGORITHMS = frozenset({"RS256"})
_DEFAULT_JWKS_TTL_SECONDS = 300


class OIDCVerificationError(ValueError):
    """Raised when an OIDC token cannot be verified or fails claim policy."""


@dataclass(frozen=True)
class OIDCSettings:
    issuer: str
    audience: str
    jwks_url: str
    jwks_ttl_seconds: int = _DEFAULT_JWKS_TTL_SECONDS

    @classmethod
    def from_environment(cls) -> "OIDCSettings | None":
        issuer = os.getenv("AUTH0_ISSUER", "").strip().rstrip("/")
        audience = os.getenv("AUTH0_AUDIENCE", "").strip()
        if not issuer and not audience:
            return None
        if not issuer or not audience:
            raise OIDCVerificationError("AUTH0_ISSUER and AUTH0_AUDIENCE must be configured together.")
        jwks_url = os.getenv("AUTH0_JWKS_URL", f"{issuer}/.well-known/jwks.json").strip()
        if not jwks_url.startswith("https://"):
            raise OIDCVerificationError("AUTH0_JWKS_URL must use HTTPS.")
        try:
            ttl = int(os.getenv("AUTH0_JWKS_TTL_SECONDS", str(_DEFAULT_JWKS_TTL_SECONDS)))
        except ValueError as exc:
            raise OIDCVerificationError("AUTH0_JWKS_TTL_SECONDS must be an integer.") from exc
        if not 60 <= ttl <= 86_400:
            raise OIDCVerificationError("AUTH0_JWKS_TTL_SECONDS must be between 60 and 86400.")
        return cls(issuer=issuer, audience=audience, jwks_url=jwks_url, jwks_ttl_seconds=ttl)


@dataclass
class _JWKCache:
    expires_at: float = 0.0
    keys: dict[str, rsa.RSAPublicKey] | None = None


_cache_by_url: dict[str, _JWKCache] = {}


def _b64url_decode(value: str) -> bytes:
    padding_chars = "=" * ((4 - len(value) % 4) % 4)
    try:
        return base64.urlsafe_b64decode((value + padding_chars).encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise OIDCVerificationError("Malformed base64url token component.") from exc


def _parse_rsa_key(raw: dict[str, Any]) -> rsa.RSAPublicKey:
    if raw.get("kty") != "RSA" or raw.get("alg") not in _ALLOWED_ALGORITHMS:
        raise OIDCVerificationError("Unsupported OIDC signing key.")
    try:
        modulus = int.from_bytes(_b64url_decode(str(raw["n"])), "big")
        exponent = int.from_bytes(_b64url_decode(str(raw["e"])), "big")
        return rsa.RSAPublicNumbers(exponent, modulus).public_key()
    except (KeyError, TypeError, ValueError) as exc:
        raise OIDCVerificationError("Malformed OIDC RSA signing key.") from exc


async def _load_jwks(settings: OIDCSettings, *, force_refresh: bool = False) -> dict[str, rsa.RSAPublicKey]:
    cached = _cache_by_url.setdefault(settings.jwks_url, _JWKCache())
    now = time.monotonic()
    if not force_refresh and cached.keys is not None and cached.expires_at > now:
        return cached.keys

    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.get(settings.jwks_url)
            response.raise_for_status()
            document = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        _logger.error("OIDC JWKS fetch failed: url=%s error=%s", settings.jwks_url, type(exc).__name__)
        raise OIDCVerificationError("OIDC signing-key service is unavailable.") from exc

    raw_keys = document.get("keys") if isinstance(document, dict) else None
    if not isinstance(raw_keys, list):
        raise OIDCVerificationError("OIDC JWKS response has no keys.")
    parsed: dict[str, rsa.RSAPublicKey] = {}
    for raw in raw_keys:
        if isinstance(raw, dict) and isinstance(raw.get("kid"), str):
            parsed[raw["kid"]] = _parse_rsa_key(raw)
    if not parsed:
        raise OIDCVerificationError("OIDC JWKS response has no supported RSA keys.")
    cached.keys = parsed
    cached.expires_at = now + settings.jwks_ttl_seconds
    return parsed


def _decode_json_segment(segment: str) -> dict[str, Any]:
    try:
        value = json.loads(_b64url_decode(segment).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OIDCVerificationError("Malformed JWT JSON segment.") from exc
    if not isinstance(value, dict):
        raise OIDCVerificationError("JWT segment must be a JSON object.")
    return value


def _validate_claims(claims: dict[str, Any], settings: OIDCSettings, now: int) -> None:
    if claims.get("iss") != f"{settings.issuer}/":
        raise OIDCVerificationError("Invalid token issuer.")
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if settings.audience not in audiences:
        raise OIDCVerificationError("Invalid token audience.")
    exp = claims.get("exp")
    if not isinstance(exp, int) or now >= exp:
        raise OIDCVerificationError("Token expired or missing expiry.")
    nbf = claims.get("nbf")
    if isinstance(nbf, int) and now < nbf:
        raise OIDCVerificationError("Token is not active yet.")
    if not isinstance(claims.get("sub"), str) or not claims["sub"].strip():
        raise OIDCVerificationError("Token subject is required.")
    organization_id = claims.get("organization_id") or claims.get("org_id") or claims.get("tenant_id")
    if not isinstance(organization_id, str) or not organization_id.strip():
        raise OIDCVerificationError("Token organization claim is required.")


async def verify_oidc_jwt(token: str, settings: OIDCSettings | None = None) -> dict[str, Any]:
    """Verify an OIDC RS256 JWT and return claims only after policy validation."""
    settings = settings or OIDCSettings.from_environment()
    if settings is None:
        raise OIDCVerificationError("OIDC is not configured.")
    parts = token.split(".")
    if len(parts) != 3:
        raise OIDCVerificationError("Invalid token format.")
    header = _decode_json_segment(parts[0])
    if header.get("alg") not in _ALLOWED_ALGORITHMS or not isinstance(header.get("kid"), str):
        raise OIDCVerificationError("Unsupported JWT algorithm or missing key ID.")
    claims = _decode_json_segment(parts[1])
    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    signature = _b64url_decode(parts[2])
    keys = await _load_jwks(settings)
    key = keys.get(header["kid"])
    if key is None:
        keys = await _load_jwks(settings, force_refresh=True)
        key = keys.get(header["kid"])
    if key is None:
        raise OIDCVerificationError("Unknown JWT signing key.")
    try:
        key.verify(signature, signing_input, padding.PKCS1v15(), SHA256())
    except Exception as exc:
        raise OIDCVerificationError("Invalid token signature.") from exc
    _validate_claims(claims, settings, int(time.time()))
    return claims
