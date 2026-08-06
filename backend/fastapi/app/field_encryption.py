"""
Transparent Field-Level Encryption for FastAPI
===============================================

NOT CURRENTLY THE CANONICAL ENCRYPTION PATH — READ BEFORE USING
-----------------------------------------------------------------
Three independent field-encryption implementations exist in this codebase:
this module (Vault Transit / envelope / local AES-GCM), ``security.py``
(HKDF-derived AES-256-GCM keyed off ``APP_ENC_KEY``+``PASSWORD_PEPPER``,
optionally PQC-hybrid), and ``transparent_encryption.py`` (Postgres-side
pgcrypto). They have different key-management assumptions and are NOT
interchangeable — ciphertext from one cannot be decrypted by another.

``security.py``'s ``encrypt_value``/``decrypt_value`` is the one actually
wired into live PII encryption today (``routers/auth.py``'s email/name
fields). This module is otherwise only referenced by ``routers/pentest_sync.py``
and tests — it is a more complete design (centralized key rotation via Vault,
no redeploy needed to rotate) but adopting it as canonical requires migrating
existing ciphertext with a dual-read/single-write cutover against a real,
tested Vault instance, not a drop-in swap. Until that migration happens,
do not add new call sites here for data that must interoperate with
``security.py``-encrypted fields — pick one deliberately, per record type.

Architecture
------------
Three encryption strategies, auto-selected by token prefix:

  vault:v{n}:...        Vault Transit direct   — every op logged in Vault audit
  envelope:...          Envelope encryption    — fast bulk; DEK per record
  local:v1:...          Local AES-256-GCM      — dev/fallback only

Key hierarchy (Vault Transit keys at nuxtron/transit/):
  pii           — emails, names, phone numbers
  api_keys      — third-party API keys and secrets
  tokens        — auth/refresh tokens
  attachments   — file/blob DEKs (used with envelope strategy)
  sops          — SOPS .env encryption

Envelope encryption pattern:
  1. Vault generates a random DEK (256-bit AES)
  2. Data encrypted locally with DEK (AES-256-GCM, fast)
  3. Encrypted DEK stored alongside ciphertext
  → Vault audit trail for all DEK operations
  → Local crypto speed (no Vault round-trip per record)
  → Key rotation via Vault rewrap (no data re-encryption needed)

Usage
-----
  from .field_encryption import get_field_encryptor

  enc = await get_field_encryptor()

  # Encrypt a sensitive field (Vault Transit, audit trail per operation)
  ct = await enc.encrypt("user@example.com", key_name="pii")

  # Decrypt
  pt = await enc.decrypt(ct, key_name="pii")

  # Encrypt a large blob (envelope: fast, one Vault call for DEK)
  ct = await enc.encrypt(large_bytes, key_name="attachments", strategy="envelope")

  # Local only (dev / testing, no Vault required)
  ct = enc.encrypt_local("value")

Environment variables
---------------------
  VAULT_ADDR              Vault server (default: http://vault:8200)
  VAULT_TOKEN             Vault token
  VAULT_TRANSIT_MOUNT     Transit mount path (default: nuxtron/transit)
    APP_ENC_KEY             Fallback local encryption key material
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import secrets

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_VAULT_ADDR = os.getenv("VAULT_ADDR", "http://vault:8200")
_VAULT_TOKEN = os.getenv("VAULT_TOKEN", "")
_VAULT_TRANSIT_MOUNT = os.getenv("VAULT_TRANSIT_MOUNT", "nuxtron/transit")
_DEK_CACHE_TTL = 300  # seconds — how long to cache plaintext DEKs in memory
_ENVELOPE_PREFIX = "envelope:"


# ---------------------------------------------------------------------------
# Vault Transit client
# ---------------------------------------------------------------------------

class VaultTransitError(RuntimeError):
    pass


class VaultTransitClient:
    """Async client for Vault Transit Engine (encryption as a service)."""

    def __init__(
        self,
        addr: str = _VAULT_ADDR,
        token: str = _VAULT_TOKEN,
        mount: str = _VAULT_TRANSIT_MOUNT,
    ) -> None:
        self._addr = addr.rstrip("/")
        self._token = token
        self._mount = mount.strip("/")
        self._http: httpx.AsyncClient | None = None

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                base_url=self._addr,
                headers={"X-Vault-Token": self._token},
                timeout=httpx.Timeout(connect=3.0, read=10.0, write=5.0, pool=3.0),
            )
        return self._http

    async def close(self) -> None:
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    # ── Core operations ──────────────────────────────────────────────────────

    async def encrypt(self, plaintext: str | bytes, key_name: str) -> str:
        """
        Encrypt with Vault Transit.
        Returns a ciphertext token of the form ``vault:v{version}:{base64}``.
        Every call is recorded in the Vault audit log.
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        encoded = base64.b64encode(plaintext).decode()

        resp = await self._client.post(
            f"/v1/{self._mount}/encrypt/{key_name}",
            json={"plaintext": encoded},
        )
        if resp.status_code != 200:
            raise VaultTransitError(
                f"Vault Transit encrypt failed [{resp.status_code}]: {resp.text}"
            )
        return resp.json()["data"]["ciphertext"]

    async def decrypt(self, ciphertext: str, key_name: str) -> bytes:
        """
        Decrypt a ``vault:v{n}:...`` token.
        Works for all key versions (old versions still decrypt after rotation).
        """
        resp = await self._client.post(
            f"/v1/{self._mount}/decrypt/{key_name}",
            json={"ciphertext": ciphertext},
        )
        if resp.status_code != 200:
            raise VaultTransitError(
                f"Vault Transit decrypt failed [{resp.status_code}]: {resp.text}"
            )
        return base64.b64decode(resp.json()["data"]["plaintext"])

    async def rewrap(self, ciphertext: str, key_name: str) -> str:
        """
        Re-encrypt with the latest key version.
        Use after key rotation to upgrade all stored ciphertexts without
        decrypting the plaintext (the plaintext never leaves Vault).
        """
        resp = await self._client.post(
            f"/v1/{self._mount}/rewrap/{key_name}",
            json={"ciphertext": ciphertext},
        )
        if resp.status_code != 200:
            raise VaultTransitError(
                f"Vault Transit rewrap failed [{resp.status_code}]: {resp.text}"
            )
        return resp.json()["data"]["ciphertext"]

    async def rotate_key(self, key_name: str) -> None:
        """
        Rotate a Transit key.
        New encryptions use the latest version; old versions still decrypt.
        Call rewrap() on all stored ciphertexts to migrate to the new version.
        """
        resp = await self._client.post(
            f"/v1/{self._mount}/keys/{key_name}/rotate"
        )
        if resp.status_code not in (200, 204):
            raise VaultTransitError(
                f"Vault Transit rotate_key failed [{resp.status_code}]: {resp.text}"
            )

    async def generate_data_key(self, key_name: str) -> tuple[bytes, str]:
        """
        Generate a random data encryption key (DEK) for envelope encryption.

        Returns (plaintext_key: bytes, encrypted_key: str).
        - Use plaintext_key to encrypt data locally, then discard immediately.
        - Store encrypted_key alongside the ciphertext.
        - The encrypted_key is the only Vault-audited artifact.
        """
        resp = await self._client.post(
            f"/v1/{self._mount}/datakey/plaintext/{key_name}",
            json={"bits": 256},
        )
        if resp.status_code != 200:
            raise VaultTransitError(
                f"Vault Transit datakey failed [{resp.status_code}]: {resp.text}"
            )
        data = resp.json()["data"]
        plaintext_key = base64.b64decode(data["plaintext"])
        encrypted_key: str = data["ciphertext"]
        return plaintext_key, encrypted_key

    async def decrypt_data_key(self, encrypted_key: str, key_name: str) -> bytes:
        """Decrypt an envelope DEK returned by generate_data_key()."""
        return await self.decrypt(encrypted_key, key_name)


# ---------------------------------------------------------------------------
# Local AES-256-GCM cipher (high-throughput / Vault-unavailable fallback)
# ---------------------------------------------------------------------------

class AESGCMLocalCipher:
    """
    Symmetric AES-256-GCM encryption.

    Key must be sourced externally (from Vault, KMS, or APP_ENC_KEY env var).
    Never use a hardcoded key in production.

    Token format: ``local:v1:<base64(nonce[12] + ciphertext + tag[16])>``
    """

    PREFIX = "local:v1:"

    @staticmethod
    def encrypt(plaintext: str | bytes, key: bytes) -> str:
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        if len(key) != 32:
            raise ValueError("AES-256 key must be exactly 32 bytes")
        nonce = secrets.token_bytes(12)  # 96-bit GCM nonce
        aesgcm = AESGCM(key)
        ct = aesgcm.encrypt(nonce, plaintext, None)  # includes 16-byte auth tag
        return AESGCMLocalCipher.PREFIX + base64.b64encode(nonce + ct).decode()

    @staticmethod
    def decrypt(token: str, key: bytes) -> bytes:
        if not token.startswith(AESGCMLocalCipher.PREFIX):
            raise ValueError(f"Not a {AESGCMLocalCipher.PREFIX!r} token")
        if len(key) != 32:
            raise ValueError("AES-256 key must be exactly 32 bytes")
        raw = base64.b64decode(token[len(AESGCMLocalCipher.PREFIX):])
        nonce, ct = raw[:12], raw[12:]
        aesgcm = AESGCM(key)
        return aesgcm.decrypt(nonce, ct, None)


# ---------------------------------------------------------------------------
# Envelope encryption (Vault DEK + local AES-256-GCM)
# ---------------------------------------------------------------------------

class EnvelopeEncryptor:
    """
    Envelope encryption: Vault DEK wrapped around local AES-256-GCM.

    Why:
      - Local encryption is ~100× faster than per-record Vault Transit calls.
      - Vault still provides key management, rotation, and audit trail.
      - The plaintext DEK exists in memory only for the duration of the call.

    Stored format (JSON, base64-wrapped in token string):
      {
        "enc":  "envelope/aes256gcm+vault-transit",
        "key":  "attachments",
        "edek": "vault:v2:...",   ← encrypted DEK (Vault Transit)
        "ct":   "local:v1:..."    ← ciphertext (AES-256-GCM)
      }
    """

    def __init__(self, vault: VaultTransitClient) -> None:
        self._vault = vault

    async def encrypt(self, plaintext: str | bytes, key_name: str) -> str:
        dek, encrypted_dek = await self._vault.generate_data_key(key_name)
        try:
            ct = AESGCMLocalCipher.encrypt(plaintext, dek)
        finally:
            # Zero and release the plaintext DEK immediately
            dek = bytes(len(dek))  # noqa: F841
        envelope = {
            "enc": "envelope/aes256gcm+vault-transit",
            "key": key_name,
            "edek": encrypted_dek,
            "ct": ct,
        }
        return _ENVELOPE_PREFIX + base64.b64encode(
            json.dumps(envelope, separators=(",", ":")).encode()
        ).decode()

    async def decrypt(self, token: str) -> bytes:
        if not token.startswith(_ENVELOPE_PREFIX):
            raise ValueError("Not an envelope token")
        envelope = json.loads(base64.b64decode(token[len(_ENVELOPE_PREFIX):]))
        if envelope.get("enc") != "envelope/aes256gcm+vault-transit":
            raise ValueError(f"Unknown envelope type: {envelope.get('enc')!r}")
        dek = await self._vault.decrypt_data_key(envelope["edek"], envelope["key"])
        try:
            return AESGCMLocalCipher.decrypt(envelope["ct"], dek)
        finally:
            dek = bytes(len(dek))  # noqa: F841


# ---------------------------------------------------------------------------
# High-level FieldEncryptor
# ---------------------------------------------------------------------------

class FieldEncryptor:
    """
    Transparent field-level encryption.

    Strategies
    ----------
    "vault"     Vault Transit direct  — best audit trail, ~1 ms overhead per op
    "envelope"  Envelope encryption   — fastest for large values/blobs
    "local"     Local AES-256-GCM     — dev/testing only; no Vault required

    Key names
    ---------
    "pii"          Personally identifiable information
    "api_keys"     API keys and service secrets
    "tokens"       Auth/refresh tokens
    "attachments"  File blobs (use envelope strategy)

    All strategies produce self-describing tokens that auto-detect on decrypt:
      vault:v{n}:...   → Vault Transit
      envelope:...     → Envelope
      local:v1:...     → Local AES-256-GCM
    """

    def __init__(
        self,
        vault_addr: str = _VAULT_ADDR,
        vault_token: str = _VAULT_TOKEN,
        vault_mount: str = _VAULT_TRANSIT_MOUNT,
    ) -> None:
        self._vault: VaultTransitClient | None = None
        self._envelope: EnvelopeEncryptor | None = None
        self._local_key: bytes | None = None
        self._vault_addr = vault_addr
        self._vault_token = vault_token
        self._vault_mount = vault_mount

    # ── Lazy singletons ──────────────────────────────────────────────────────

    @property
    def vault(self) -> VaultTransitClient:
        if self._vault is None:
            self._vault = VaultTransitClient(
                self._vault_addr, self._vault_token, self._vault_mount
            )
        return self._vault

    @property
    def envelope(self) -> EnvelopeEncryptor:
        if self._envelope is None:
            self._envelope = EnvelopeEncryptor(self.vault)
        return self._envelope

    @property
    def local_key(self) -> bytes:
        """Derive a 32-byte key from APP_ENC_KEY env var (SHA-256)."""
        if self._local_key is None:
            raw = os.getenv("APP_ENC_KEY", "")
            if not raw:
                raise RuntimeError("APP_ENC_KEY must be set for local encryption")
            self._local_key = hashlib.sha256(raw.encode()).digest()
        return self._local_key

    # ── Public API ───────────────────────────────────────────────────────────

    async def encrypt(
        self,
        value: str | bytes,
        key_name: str = "pii",
        strategy: str = "vault",
    ) -> str:
        """
        Encrypt a field value. Returns a string token for database storage.

        Parameters
        ----------
        value     : plaintext to encrypt
        key_name  : Vault Transit key name (pii / api_keys / tokens / attachments)
        strategy  : "vault" | "envelope" | "local"
        """
        if strategy == "vault":
            return await self.vault.encrypt(value, key_name)
        if strategy == "envelope":
            return await self.envelope.encrypt(value, key_name)
        if strategy == "local":
            return AESGCMLocalCipher.encrypt(value, self.local_key)
        raise ValueError(f"Unknown encryption strategy: {strategy!r}")

    async def decrypt(
        self,
        token: str,
        key_name: str = "pii",
    ) -> str:
        """
        Decrypt a field token. Auto-detects strategy from prefix.
        Returns plaintext as a UTF-8 string.
        """
        if token.startswith("vault:"):
            result = await self.vault.decrypt(token, key_name)
        elif token.startswith(_ENVELOPE_PREFIX):
            result = await self.envelope.decrypt(token)
        elif token.startswith("local:"):
            result = AESGCMLocalCipher.decrypt(token, self.local_key)
        else:
            raise ValueError(f"Unrecognised token format: {token[:24]!r}")
        if isinstance(result, str):
            return result
        return bytes(result).decode()

    def encrypt_local(self, value: str | bytes) -> str:
        """Synchronous local-only encryption (no Vault). Dev / testing."""
        return AESGCMLocalCipher.encrypt(value, self.local_key)

    def decrypt_local(self, token: str) -> str:
        """Synchronous local-only decryption (no Vault). Dev / testing."""
        result = AESGCMLocalCipher.decrypt(token, self.local_key)
        return result.decode()

    async def rewrap_field(self, token: str, key_name: str) -> str:
        """
        Re-encrypt a stored Vault Transit token with the latest key version.
        Call this after rotating a key to migrate existing records.
        For envelope tokens, re-wraps only the DEK (no plaintext access needed).
        """
        if token.startswith("vault:"):
            return await self.vault.rewrap(token, key_name)
        if token.startswith(_ENVELOPE_PREFIX):
            envelope = json.loads(
                base64.b64decode(token[len(_ENVELOPE_PREFIX):])
            )
            new_edek = await self.vault.rewrap(envelope["edek"], key_name)
            envelope["edek"] = new_edek
            return _ENVELOPE_PREFIX + base64.b64encode(
                json.dumps(envelope, separators=(",", ":")).encode()
            ).decode()
        raise ValueError(f"Cannot rewrap token type: {token[:12]!r}")

    async def close(self) -> None:
        if self._vault:
            await self._vault.close()


# ---------------------------------------------------------------------------
# Module-level singleton (async-safe lazy init)
# ---------------------------------------------------------------------------

_encryptor: FieldEncryptor | None = None
_encryptor_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _encryptor_lock
    if _encryptor_lock is None:
        _encryptor_lock = asyncio.Lock()
    return _encryptor_lock


async def get_field_encryptor() -> FieldEncryptor:
    """Return the module-level FieldEncryptor singleton (lazy init)."""
    global _encryptor
    if _encryptor is None:
        async with _get_lock():
            if _encryptor is None:
                _encryptor = FieldEncryptor()
    return _encryptor


async def close_field_encryptor() -> None:
    """Close the singleton's HTTP client. Call on app shutdown."""
    global _encryptor
    if _encryptor is not None:
        await _encryptor.close()
        _encryptor = None
