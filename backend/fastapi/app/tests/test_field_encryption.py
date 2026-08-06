"""Tests for field_encryption.py — AESGCMLocalCipher and VaultTransitError."""
import base64
import secrets

import pytest
from backend.fastapi.app.field_encryption import (
    AESGCMLocalCipher,
    VaultTransitError,
)
from cryptography.exceptions import InvalidTag


def _make_key() -> bytes:
    return secrets.token_bytes(32)


class TestAESGCMLocalCipher:
    def test_encrypt_returns_local_prefix(self):
        key = _make_key()
        token = AESGCMLocalCipher.encrypt("hello", key)
        assert token.startswith("local:v1:")

    def test_roundtrip_str(self):
        key = _make_key()
        token = AESGCMLocalCipher.encrypt("plaintext", key)
        decrypted = AESGCMLocalCipher.decrypt(token, key)
        assert decrypted == b"plaintext"

    def test_roundtrip_bytes(self):
        key = _make_key()
        raw = b"\x00\xff\xab binary data"
        token = AESGCMLocalCipher.encrypt(raw, key)
        assert AESGCMLocalCipher.decrypt(token, key) == raw

    def test_encrypt_unicode(self):
        key = _make_key()
        text = "héllo wörld 🌍"
        token = AESGCMLocalCipher.encrypt(text, key)
        assert AESGCMLocalCipher.decrypt(token, key) == text.encode()

    def test_encrypt_empty_string(self):
        key = _make_key()
        token = AESGCMLocalCipher.encrypt("", key)
        assert AESGCMLocalCipher.decrypt(token, key) == b""

    def test_encrypt_long_value(self):
        key = _make_key()
        big = "X" * 100_000
        token = AESGCMLocalCipher.encrypt(big, key)
        assert AESGCMLocalCipher.decrypt(token, key) == big.encode()

    def test_different_keys_produce_different_tokens(self):
        k1, k2 = _make_key(), _make_key()
        t1 = AESGCMLocalCipher.encrypt("same", k1)
        t2 = AESGCMLocalCipher.encrypt("same", k2)
        assert t1 != t2

    def test_two_encryptions_same_key_differ(self):
        # Random nonce → distinct ciphertexts for same plaintext
        key = _make_key()
        t1 = AESGCMLocalCipher.encrypt("same", key)
        t2 = AESGCMLocalCipher.encrypt("same", key)
        assert t1 != t2

    def test_wrong_key_raises(self):
        k1, k2 = _make_key(), _make_key()
        token = AESGCMLocalCipher.encrypt("secret", k1)
        with pytest.raises(InvalidTag):
            AESGCMLocalCipher.decrypt(token, k2)

    def test_bad_key_length_encrypt_raises(self):
        with pytest.raises(ValueError, match="32 bytes"):
            AESGCMLocalCipher.encrypt("hi", b"short-key")

    def test_bad_key_length_decrypt_raises(self):
        key = _make_key()
        token = AESGCMLocalCipher.encrypt("hi", key)
        with pytest.raises(ValueError, match="32 bytes"):
            AESGCMLocalCipher.decrypt(token, b"short-key")

    def test_decrypt_wrong_prefix_raises(self):
        with pytest.raises(ValueError):
            AESGCMLocalCipher.decrypt("vault:v1:notlocal", _make_key())

    def test_tampered_ciphertext_raises(self):
        key = _make_key()
        token = AESGCMLocalCipher.encrypt("data", key)
        # Flip a byte in the base64 payload
        prefix = "local:v1:"
        raw = base64.b64decode(token[len(prefix):])
        tampered = raw[:12] + bytes([raw[12] ^ 0xFF]) + raw[13:]
        bad_token = prefix + base64.b64encode(tampered).decode()
        with pytest.raises(InvalidTag):
            AESGCMLocalCipher.decrypt(bad_token, key)


class TestVaultTransitError:
    def test_is_runtime_error(self):
        err = VaultTransitError("something went wrong")
        assert isinstance(err, RuntimeError)
        assert "something went wrong" in str(err)
