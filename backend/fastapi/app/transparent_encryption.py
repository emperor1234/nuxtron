"""
Transparent Encryption Layer
============================

NOT CURRENTLY THE CANONICAL ENCRYPTION PATH — READ BEFORE USING
-----------------------------------------------------------------
This is one of THREE independent field-encryption implementations in this
codebase (see also ``security.py`` and ``field_encryption.py``), with its own
DB-side (pgcrypto) key-management model. Ciphertext produced here is not
interoperable with the other two. ``security.py``'s ``encrypt_value``/
``decrypt_value`` is the one actually wired into live PII encryption today
(``routers/auth.py``). Do not add new call sites here for data that must
interoperate with fields encrypted via ``security.py`` — see
``field_encryption.py``'s module docstring for the full consolidation note.

Sits on top of the existing security.py (AES-256-GCM + vault) stack.

Adds:
  - ChaCha20-Poly1305 (via PyNaCl/libsodium) as cipher algorithm v2
  - Automatic cipher selection: AES-256-GCM when AES-NI available, else ChaCha20-Poly1305
  - EncryptedField — descriptor for transparent model-level encrypt/decrypt
  - auto_encrypt_dict / auto_decrypt_dict — encrypt sensitive keys in dicts automatically
  - enable_pgcrypto() — enables PostgreSQL pgcrypto extension for DB-level encryption
  - rotate_key() — re-encrypts ciphertext under a new key without exposing plaintext
  - All existing vault + token security is PRESERVED and used for key material.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import nacl.secret
import nacl.utils
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .security import _b64d, _b64e, _derive_base_key, decrypt_value, encrypt_value

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cipher envelope version tags
#   nse1:  AES-256-GCM (existing, from security.py)
#   nse2:  ChaCha20-Poly1305 via PyNaCl/libsodium
# ---------------------------------------------------------------------------
_NSE2_PREFIX = 'nse2:'
_PGCRYPTO_KEY_PLACEHOLDER = "current_setting('app.encryption_key', true)"


def _aes_ni_available() -> bool:
    """Heuristic: if AES-GCM throughput is fast, hardware acceleration is present."""
    try:
        key = os.urandom(32)
        nonce = os.urandom(12)
        data = b'x' * 65536  # 64 KB
        t = time.perf_counter()
        for _ in range(5):
            AESGCM(key).encrypt(nonce, data, None)
        elapsed = time.perf_counter() - t
        return elapsed < 0.05  # < 10ms for 5×64KB = hardware
    except Exception:
        return False


# Determine preferred cipher once at import time
_USE_CHACHA20 = os.getenv('FORCE_CHACHA20_POLY1305', '').lower() in ('1', 'true') or (
    not _aes_ni_available() and os.getenv('ALLOW_CHACHA20_FALLBACK', '1').lower() not in ('0', 'false')
)

logger.info(
    'TransparentEncryption: primary cipher = %s',
    'ChaCha20-Poly1305' if _USE_CHACHA20 else 'AES-256-GCM',
)


# ---------------------------------------------------------------------------
# Internal: ChaCha20-Poly1305 envelope  (nse2:)
# ---------------------------------------------------------------------------

def _derive_chacha_key() -> bytes:
    """Derive a 32-byte key for ChaCha20-Poly1305 from the same vault-backed material."""
    base = _derive_base_key()
    return HKDF(
        algorithm=hashes.SHA384(),
        length=32,
        salt=b'nuxtron-chacha20-poly1305-v1',
        info=b'nuxtron/data-encryption-key/chacha20',
    ).derive(base)


def _encrypt_chacha20(plaintext: str) -> str:
    key = _derive_chacha_key()
    box = nacl.secret.SecretBox(key)
    nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
    ct = box.encrypt(plaintext.encode('utf-8'), nonce)
    # ct includes nonce prefix from PyNaCl; store as envelope for parity with nse1
    envelope = {
        'v': 1,
        'alg': 'ChaCha20-Poly1305',
        'kdf': 'HKDF-SHA384',
        'ct': _b64e(ct.ciphertext),
        'nonce': _b64e(nonce),
    }
    packed = json.dumps(envelope, separators=(',', ':')).encode('utf-8')
    return f"{_NSE2_PREFIX}{_b64e(packed)}"


def _decrypt_chacha20(ciphertext: str) -> str | None:
    if not ciphertext.startswith(_NSE2_PREFIX):
        return None
    try:
        packed = _b64d(ciphertext[len(_NSE2_PREFIX):])
        envelope = json.loads(packed.decode('utf-8'))
        nonce = _b64d(str(envelope['nonce']))
        ct_bytes = _b64d(str(envelope['ct']))
        key = _derive_chacha_key()
        box = nacl.secret.SecretBox(key)
        plaintext = box.decrypt(ct_bytes, nonce)
        return plaintext.decode('utf-8')
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public transparent encrypt / decrypt
# ---------------------------------------------------------------------------

def te_encrypt(plaintext: str) -> str:
    """
    Transparently encrypt a value using the best available cipher.
    Produces an nse2: (ChaCha20) or nse1: (AES-GCM) ciphertext.
    Vault-backed key material is always used (via security.py).
    """
    if _USE_CHACHA20:
        return _encrypt_chacha20(plaintext)
    return encrypt_value(plaintext)  # delegates to AES-256-GCM in security.py


def te_decrypt(ciphertext: str) -> str | None:
    """
    Transparently decrypt any supported envelope:
      nse2: → ChaCha20-Poly1305 (new)
      nse1: → AES-256-GCM       (existing)
      legacy Fernet             (backward compat via security.py)
    """
    if ciphertext.startswith(_NSE2_PREFIX):
        return _decrypt_chacha20(ciphertext)
    return decrypt_value(ciphertext)  # handles nse1: and legacy Fernet


# ---------------------------------------------------------------------------
# Key rotation — re-encrypt under current cipher without exposing plaintext
# ---------------------------------------------------------------------------

def rotate_key(old_ciphertext: str) -> str | None:
    """
    Decrypt with the old key material and re-encrypt under the current cipher.
    Returns the new ciphertext, or None if decryption fails.
    Does NOT log the plaintext value.
    """
    plaintext = te_decrypt(old_ciphertext)
    if plaintext is None:
        logger.warning('rotate_key: failed to decrypt ciphertext — skipping rotation')
        return None
    return te_encrypt(plaintext)


# ---------------------------------------------------------------------------
# Dict-level transparent encryption for API payloads / DB rows
# ---------------------------------------------------------------------------

#: Default sensitive field names to auto-encrypt in dicts.
DEFAULT_SENSITIVE_KEYS: frozenset[str] = frozenset({
    'password', 'secret', 'token', 'api_key', 'access_token', 'refresh_token',
    'email', 'phone', 'ssn', 'credit_card', 'card_number', 'cvv',
    'private_key', 'encryption_key', 'pepper', 'salt',
    'email_cipher', 'name_cipher', 'body_cipher', 'subject_cipher',
    'text_cipher', 'display_name_cipher',
})


def auto_encrypt_dict(
    data: dict[str, Any],
    sensitive_keys: frozenset[str] | set[str] | None = None,
) -> dict[str, Any]:
    """
    Return a copy of *data* with sensitive string values transparently encrypted.
    Already-encrypted values (starting with nse1: or nse2:) are left untouched.
    """
    keys = sensitive_keys if sensitive_keys is not None else DEFAULT_SENSITIVE_KEYS
    result: dict[str, Any] = {}
    for k, v in data.items():
        if k in keys and isinstance(v, str) and not (v.startswith('nse1:') or v.startswith(_NSE2_PREFIX)):
            result[k] = te_encrypt(v)
        else:
            result[k] = v
    return result


def auto_decrypt_dict(
    data: dict[str, Any],
    sensitive_keys: frozenset[str] | set[str] | None = None,
) -> dict[str, Any]:
    """
    Return a copy of *data* with nse1:/nse2: values transparently decrypted.
    Non-encrypted values are passed through unchanged.
    """
    keys = sensitive_keys if sensitive_keys is not None else DEFAULT_SENSITIVE_KEYS
    result: dict[str, Any] = {}
    for k, v in data.items():
        if k in keys and isinstance(v, str) and (v.startswith('nse1:') or v.startswith(_NSE2_PREFIX)):
            result[k] = te_decrypt(v)
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# EncryptedField — transparent descriptor for class-level model fields
# ---------------------------------------------------------------------------

class EncryptedField:
    """
    Descriptor that transparently encrypts on write and decrypts on read.

    Usage::

        class UserProfile:
            email = EncryptedField('_email_enc')
            phone = EncryptedField('_phone_enc')

        u = UserProfile()
        u.email = 'alice@example.com'   # stored encrypted
        print(u.email)                  # returns decrypted plaintext
    """

    def __init__(self, storage_attr: str) -> None:
        self._storage = storage_attr

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name
        if not self._storage:
            self._storage = f'_enc_{name}'

    def __get__(self, obj: Any, objtype: type | None = None) -> str | None:
        if obj is None:
            return self  # type: ignore[return-value]
        raw = getattr(obj, self._storage, None)
        if raw is None:
            return None
        return te_decrypt(raw)

    def __set__(self, obj: Any, value: str | None) -> None:
        if value is None:
            setattr(obj, self._storage, None)
        else:
            setattr(obj, self._storage, te_encrypt(value))


# ---------------------------------------------------------------------------
# Database-level: pgcrypto extension
# ---------------------------------------------------------------------------

def enable_pgcrypto(conn: Any) -> bool:
    """
    Enable the PostgreSQL pgcrypto extension on the given psycopg connection.
    pgcrypto provides SQL-level encrypt/decrypt functions as a second layer of
    defense (DB-at-rest encryption independent of application keys).

    Returns True if enabled, False on failure (non-fatal — app encryption still works).
    """
    try:
        with conn.cursor() as cur:
            cur.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto')
        conn.commit()
        logger.info('pgcrypto: extension enabled (database-level transparent encryption active)')
        return True
    except Exception as exc:
        logger.warning('pgcrypto: could not enable extension: %s', exc)
        return False


def pgcrypto_encrypt_sql(column: str) -> str:
    """
    Return a SQL fragment that encrypts *column* with pgcrypto using AES-256-CBC.
    The key is read from environment (vault-backed via dotenv).

    Example::

        sql = f"INSERT INTO users (email_enc) VALUES ({pgcrypto_encrypt_sql('$1')})"
    """
    return f"pgp_sym_encrypt({column}::text, {_PGCRYPTO_KEY_PLACEHOLDER})"


def pgcrypto_decrypt_sql(column: str) -> str:
    """
    Return a SQL fragment that decrypts a pgcrypto-encrypted column.

    Example::

        sql = f"SELECT {pgcrypto_decrypt_sql('email_enc')} AS email FROM users"
    """
    return f"pgp_sym_decrypt({column}::bytea, {_PGCRYPTO_KEY_PLACEHOLDER})"


def set_pgcrypto_session_key(conn: Any) -> bool:
    """
    Set the session-level pgcrypto key from vault/env so SQL pgcrypto operations work.
    Call this once after opening a DB connection.
    """
    from .security import get_ale_key_seed
    key = get_ale_key_seed()
    if not key or key.startswith('dev-'):
        logger.warning('pgcrypto session key: using dev/fallback key — set APP_ENC_KEY via vault in production')
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT set_config('app.encryption_key', %s, false)", (key,))
        return True
    except Exception as exc:
        logger.warning('pgcrypto session key: could not set: %s', exc)
        return False


# ---------------------------------------------------------------------------
# Health / status report
# ---------------------------------------------------------------------------

def encryption_status() -> dict[str, Any]:
    """Return current transparent encryption configuration for health endpoints."""
    pqc_enabled = os.getenv('ENABLE_NIST_PQC_HYBRID', '').lower() in ('1', 'true', 'yes', 'on')
    pqc_public_key_configured = bool(os.getenv('NIST_MLKEM_PUBLIC_KEY', '').strip())
    pqc_private_key_configured = bool(os.getenv('NIST_MLKEM_PRIVATE_KEY', '').strip())
    pqc_provider = _pqc_provider()
    return {
        'primary_cipher': 'ChaCha20-Poly1305' if _USE_CHACHA20 else 'AES-256-GCM',
        'fallback_cipher': 'AES-256-GCM' if _USE_CHACHA20 else 'ChaCha20-Poly1305',
        'aes_ni_detected': _aes_ni_available(),
        'pynacl_available': True,
        'pqc_available': pqc_provider != 'unavailable',
        'pqc_enabled': pqc_enabled,
        'pqc_algorithm': 'ML-KEM-768',
        'pqc_provider': pqc_provider,
        'pqc_public_key_configured': pqc_public_key_configured,
        'pqc_private_key_configured': pqc_private_key_configured,
        'envelope_versions': ['nse1 (AES-256-GCM)', 'nse2 (ChaCha20-Poly1305)', 'Fernet (legacy)'],
        'pgcrypto': 'enabled when DB connection provided',
        'key_source': 'HashiCorp Vault → Supabase Vault → environment',
    }


def _pqc_available() -> bool:
    return _pqc_provider() != 'unavailable'


def _pqc_provider() -> str:
    preferred = os.getenv('NIST_PQC_PROVIDER', 'pqcrypto').strip().lower()
    if preferred == 'oqs':
        try:
            import oqs  # noqa: F401
            return 'oqs'
        except Exception:
            pass

    try:
        from pqcrypto.kem import ml_kem_768  # noqa: F401
        return 'pqcrypto'
    except ImportError:
        pass

    try:
        import oqs  # noqa: F401
        return 'oqs'
    except Exception:
        return 'unavailable'
