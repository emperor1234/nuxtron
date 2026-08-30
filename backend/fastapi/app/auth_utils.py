"""Authentication utilities: JWT signing/verification and TOTP operations."""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import cast

from .deps import JwtClaims

JsonObject = dict[str, object]


def b64url_encode(raw: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def b64url_decode(raw: str) -> bytes:
    """Base64url decode with padding restoration."""
    padding = '=' * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode('ascii'))


def jwt_sign_hs256(payload: JsonObject, secret: str) -> str:
    """Sign a JWT token using HS256 algorithm."""
    header = {'alg': 'HS256', 'typ': 'JWT'}
    head = b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    body = b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signing_input = f'{head}.{body}'.encode('ascii')
    signature = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    return f'{head}.{body}.{b64url_encode(signature)}'


def jwt_verify_hs256(token: str, secret: str) -> tuple[bool, JwtClaims | None, str | None]:
    """Verify a JWT token using HS256 algorithm.
    
    Returns:
        Tuple of (is_valid, claims, error_message)
    """
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return False, None, 'Invalid token format.'

        head, body, sig = parts
        signing_input = f'{head}.{body}'.encode('ascii')
        expected_sig = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
        actual_sig = b64url_decode(sig)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return False, None, 'Invalid token signature.'

        payload = json.loads(b64url_decode(body).decode('utf-8'))
        if not isinstance(payload, dict):
            return False, None, 'Invalid token payload.'
        claims = cast(JwtClaims, payload)
        exp = int(claims.get('exp', 0) or 0)
        if exp and time.time() > exp:
            return False, claims, 'Token expired.'
        return True, claims, None
    except Exception as ex:
        return False, None, f'Token verification failed: {ex}'


def totp_secret() -> str:
    """Generate a new TOTP secret."""
    return base64.b32encode(os.urandom(20)).decode('ascii').rstrip('=')


def totp_code(secret: str, for_time: int | None = None, step: int = 30, digits: int = 6) -> str:
    """Generate a TOTP code for the given time."""
    ts = int(time.time() if for_time is None else for_time)
    counter = ts // step
    padded = secret + ('=' * ((8 - len(secret) % 8) % 8))
    key = base64.b32decode(padded.upper())
    msg = counter.to_bytes(8, byteorder='big')
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = ((digest[offset] & 0x7F) << 24) | ((digest[offset + 1] & 0xFF) << 16) | ((digest[offset + 2] & 0xFF) << 8) | (digest[offset + 3] & 0xFF)
    return str(code_int % (10 ** digits)).zfill(digits)


def totp_verify(secret: str, code: str, window: int = 1, step: int = 30) -> bool:
    """Verify a TOTP code with a time window."""
    now = int(time.time())
    for w in range(-window, window + 1):
        if hmac.compare_digest(totp_code(secret, for_time=now + (w * step), step=step), code):
            return True
    return False


def hash_email(email: str) -> str:
    """Deterministic hash for email lookups without decryption."""
    from .security import get_password_pepper
    pepper = get_password_pepper()
    return hashlib.sha256(f'{email.strip().lower()}:{pepper}'.encode()).hexdigest()


def extract_ip_hash(client_host: str) -> str:
    """Extract a hash of the client IP for logging."""
    return hashlib.sha256(client_host.encode('utf-8')).hexdigest()[:16] if client_host else ''


def extract_ua_hash(user_agent: str) -> str:
    """Extract a hash of the user agent for logging."""
    return hashlib.sha256(user_agent.encode('utf-8')).hexdigest()[:16] if user_agent else ''
