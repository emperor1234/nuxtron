"""
Unit tests for pure helper functions in SEO modules:
- entity_first_seo._deduplicate_entities
- field_encryption helpers
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from cryptography.exceptions import InvalidTag


class TestDeduplicateEntities:
    """Test EntityFirstSEO._deduplicate_entities (pure method, no DB needed)."""

    def _make_module(self):
        from backend.fastapi.app.modules.entity_first_seo import EntityFirstSEO
        mod = EntityFirstSEO.__new__(EntityFirstSEO)
        return mod

    def test_empty_list(self) -> None:
        mod = self._make_module()
        result = mod._deduplicate_entities([])
        assert result == []

    def test_no_duplicates(self) -> None:
        mod = self._make_module()
        entities = [
            {"name": "Apple", "type": "brand"},
            {"name": "Google", "type": "brand"},
        ]
        result = mod._deduplicate_entities(entities)
        assert len(result) == 2

    def test_removes_exact_duplicates(self) -> None:
        mod = self._make_module()
        entities = [
            {"name": "Apple", "type": "brand"},
            {"name": "Apple", "type": "brand"},
            {"name": "Apple", "type": "brand"},
        ]
        result = mod._deduplicate_entities(entities)
        assert len(result) == 1
        assert result[0]["name"] == "Apple"

    def test_same_name_different_type_kept(self) -> None:
        mod = self._make_module()
        entities = [
            {"name": "Python", "type": "product"},
            {"name": "Python", "type": "concept"},
        ]
        result = mod._deduplicate_entities(entities)
        assert len(result) == 2

    def test_case_insensitive_dedup(self) -> None:
        mod = self._make_module()
        entities = [
            {"name": "Apple", "type": "brand"},
            {"name": "apple", "type": "brand"},
            {"name": "APPLE", "type": "brand"},
        ]
        result = mod._deduplicate_entities(entities)
        assert len(result) == 1

    def test_preserves_first_occurrence(self) -> None:
        mod = self._make_module()
        entities = [
            {"name": "First", "type": "brand", "confidence": 0.9},
            {"name": "First", "type": "brand", "confidence": 0.5},
        ]
        result = mod._deduplicate_entities(entities)
        assert result[0]["confidence"] == 0.9

    def test_mixed_unique_and_dups(self) -> None:
        mod = self._make_module()
        entities = [
            {"name": "A", "type": "brand"},
            {"name": "B", "type": "brand"},
            {"name": "A", "type": "brand"},  # dup
            {"name": "C", "type": "concept"},
        ]
        result = mod._deduplicate_entities(entities)
        assert len(result) == 3


class TestAESGCMLocalCipher:
    """Test AESGCMLocalCipher — pure, no Vault needed."""

    KEY = b"\x00" * 32  # 32-byte test key

    def test_encrypt_decrypt_roundtrip(self) -> None:
        from backend.fastapi.app.field_encryption import AESGCMLocalCipher
        original = "sensitive-api-key-12345"
        token = AESGCMLocalCipher.encrypt(original, self.KEY)
        decrypted = AESGCMLocalCipher.decrypt(token, self.KEY)
        assert decrypted == original.encode()

    def test_token_has_local_prefix(self) -> None:
        from backend.fastapi.app.field_encryption import AESGCMLocalCipher
        token = AESGCMLocalCipher.encrypt("value", self.KEY)
        assert token.startswith("local:v1:")

    def test_encrypt_empty_string(self) -> None:
        from backend.fastapi.app.field_encryption import AESGCMLocalCipher
        token = AESGCMLocalCipher.encrypt("", self.KEY)
        decrypted = AESGCMLocalCipher.decrypt(token, self.KEY)
        assert decrypted == b""

    def test_encrypt_bytes(self) -> None:
        from backend.fastapi.app.field_encryption import AESGCMLocalCipher
        data = b"\x00\x01\x02\xff"
        token = AESGCMLocalCipher.encrypt(data, self.KEY)
        decrypted = AESGCMLocalCipher.decrypt(token, self.KEY)
        assert decrypted == data

    def test_different_nonce_each_time(self) -> None:
        """Each call should produce a different ciphertext due to random nonce."""
        from backend.fastapi.app.field_encryption import AESGCMLocalCipher
        t1 = AESGCMLocalCipher.encrypt("same", self.KEY)
        t2 = AESGCMLocalCipher.encrypt("same", self.KEY)
        assert t1 != t2

    def test_decrypt_wrong_key_raises(self) -> None:
        from backend.fastapi.app.field_encryption import AESGCMLocalCipher
        token = AESGCMLocalCipher.encrypt("hello", self.KEY)
        wrong_key = b"\xff" * 32
        with pytest.raises(InvalidTag):
            AESGCMLocalCipher.decrypt(token, wrong_key)

    def test_decrypt_invalid_prefix_raises(self) -> None:
        from backend.fastapi.app.field_encryption import AESGCMLocalCipher
        with pytest.raises(ValueError):
            AESGCMLocalCipher.decrypt("vault:bad:token", self.KEY)

    def test_wrong_key_length_raises(self) -> None:
        from backend.fastapi.app.field_encryption import AESGCMLocalCipher
        with pytest.raises(ValueError):
            AESGCMLocalCipher.encrypt("hello", b"short-key")


class TestFieldEncryptorLocal:
    """Test FieldEncryptor.encrypt_local / decrypt_local synchronous path."""

    def _make_encryptor(self):
        from backend.fastapi.app.field_encryption import FieldEncryptor
        enc = FieldEncryptor.__new__(FieldEncryptor)
        enc._vault = None
        enc._envelope = None
        enc._local_key = b"\xaa" * 32
        return enc

    def test_encrypt_local_roundtrip(self) -> None:
        enc = self._make_encryptor()
        token = enc.encrypt_local("secret-value")
        decrypted = enc.decrypt_local(token)
        assert decrypted == "secret-value"

    def test_encrypt_local_unicode(self) -> None:
        enc = self._make_encryptor()
        val = "αβγ emoji: 🔐"
        assert enc.decrypt_local(enc.encrypt_local(val)) == val

    def test_module_importable(self) -> None:
        import backend.fastapi.app.field_encryption as fe
        assert fe is not None
