"""
Tests for transparent_encryption.py
Covers all public APIs: te_encrypt, te_decrypt, rotate_key,
auto_encrypt_dict, auto_decrypt_dict, EncryptedField, encryption_status,
pgcrypto_encrypt_sql, pgcrypto_decrypt_sql.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "test-enc-key-for-unit-tests-only")


from backend.fastapi.app.transparent_encryption import (
    _NSE2_PREFIX,
    DEFAULT_SENSITIVE_KEYS,
    EncryptedField,
    _aes_ni_available,
    _decrypt_chacha20,
    _encrypt_chacha20,
    auto_decrypt_dict,
    auto_encrypt_dict,
    enable_pgcrypto,
    encryption_status,
    pgcrypto_decrypt_sql,
    pgcrypto_encrypt_sql,
    rotate_key,
    set_pgcrypto_session_key,
    te_decrypt,
    te_encrypt,
)

# ── te_encrypt / te_decrypt ──────────────────────────────────────────────────

class TestTeEncryptDecrypt:
    def test_encrypt_returns_string(self) -> None:
        ct = te_encrypt("hello")
        assert isinstance(ct, str)
        assert len(ct) > 0

    def test_encrypt_produces_envelope_prefix(self) -> None:
        ct = te_encrypt("hello")
        assert ct.startswith("nse1:") or ct.startswith("nse2:")

    def test_decrypt_roundtrip(self) -> None:
        plaintext = "super secret value"
        ct = te_encrypt(plaintext)
        result = te_decrypt(ct)
        assert result == plaintext

    def test_encrypt_empty_string(self) -> None:
        ct = te_encrypt("")
        assert isinstance(ct, str)
        result = te_decrypt(ct)
        assert result == ""

    def test_encrypt_unicode(self) -> None:
        plaintext = "こんにちは 🌏"
        ct = te_encrypt(plaintext)
        assert te_decrypt(ct) == plaintext

    def test_encrypt_long_string(self) -> None:
        plaintext = "A" * 10000
        ct = te_encrypt(plaintext)
        assert te_decrypt(ct) == plaintext

    def test_different_plaintexts_produce_different_ciphertexts(self) -> None:
        ct1 = te_encrypt("value1")
        ct2 = te_encrypt("value2")
        assert ct1 != ct2

    def test_same_plaintext_may_produce_different_ciphertexts(self) -> None:
        # Nonces ensure same plaintext produces different ciphertexts each time
        ct1 = te_encrypt("same")
        ct2 = te_encrypt("same")
        # They decode to the same plaintext, not necessarily equal ciphertexts
        assert te_decrypt(ct1) == te_decrypt(ct2) == "same"

    def test_decrypt_invalid_returns_none(self) -> None:
        result = te_decrypt("notvalidciphertext")
        assert result is None

    def test_decrypt_garbage_nse2_returns_none(self) -> None:
        result = te_decrypt(f"{_NSE2_PREFIX}notbase64!!")
        assert result is None

    def test_decrypt_nse2_truncated_returns_none(self) -> None:
        result = te_decrypt(f"{_NSE2_PREFIX}dGVzdA==")  # valid b64, invalid json
        assert result is None


# ── rotate_key ───────────────────────────────────────────────────────────────

class TestRotateKey:
    def test_rotate_key_produces_valid_ciphertext(self) -> None:
        original = te_encrypt("my secret")
        rotated = rotate_key(original)
        assert rotated is not None
        assert rotated.startswith("nse1:") or rotated.startswith("nse2:")

    def test_rotate_key_preserves_plaintext(self) -> None:
        plaintext = "rotate me"
        original = te_encrypt(plaintext)
        rotated = rotate_key(original)
        assert rotated is not None
        assert te_decrypt(rotated) == plaintext

    def test_rotate_key_invalid_returns_none(self) -> None:
        result = rotate_key("completely-invalid-ciphertext")
        assert result is None

    def test_rotate_key_empty_ciphertext_returns_none(self) -> None:
        result = rotate_key("")
        assert result is None


# ── auto_encrypt_dict / auto_decrypt_dict ────────────────────────────────────

class TestAutoEncryptDecryptDict:
    def test_auto_encrypt_encrypts_sensitive_key(self) -> None:
        data = {"password": "my-password", "username": "alice"}
        result = auto_encrypt_dict(data)
        assert result["password"].startswith("nse1:") or result["password"].startswith("nse2:")
        assert result["username"] == "alice"  # non-sensitive, untouched

    def test_auto_decrypt_decrypts_sensitive_key(self) -> None:
        data = {"password": "my-password", "username": "alice"}
        encrypted = auto_encrypt_dict(data)
        decrypted = auto_decrypt_dict(encrypted)
        assert decrypted["password"] == "my-password"
        assert decrypted["username"] == "alice"

    def test_auto_encrypt_already_encrypted_skipped(self) -> None:
        ct = te_encrypt("original")
        data = {"password": ct}
        result = auto_encrypt_dict(data)
        assert result["password"] == ct  # left untouched

    def test_auto_decrypt_non_encrypted_passthrough(self) -> None:
        data = {"password": "plaintext-no-prefix", "other": "value"}
        result = auto_decrypt_dict(data)
        assert result["password"] == "plaintext-no-prefix"
        assert result["other"] == "value"

    def test_auto_encrypt_non_string_values_preserved(self) -> None:
        data = {"password": 12345, "active": True, "count": None}
        result = auto_encrypt_dict(data)
        assert result["password"] == 12345
        assert result["active"] is True
        assert result["count"] is None

    def test_auto_encrypt_custom_sensitive_keys(self) -> None:
        data = {"my_secret_field": "value", "other": "visible"}
        result = auto_encrypt_dict(data, sensitive_keys={"my_secret_field"})
        assert result["my_secret_field"].startswith(("nse1:", "nse2:"))
        assert result["other"] == "visible"

    def test_auto_decrypt_custom_sensitive_keys(self) -> None:
        data = {"my_secret_field": "value"}
        encrypted = auto_encrypt_dict(data, sensitive_keys={"my_secret_field"})
        decrypted = auto_decrypt_dict(encrypted, sensitive_keys={"my_secret_field"})
        assert decrypted["my_secret_field"] == "value"

    def test_roundtrip_all_default_sensitive_keys(self) -> None:
        data = {k: f"val-{k}" for k in DEFAULT_SENSITIVE_KEYS}
        encrypted = auto_encrypt_dict(data)
        decrypted = auto_decrypt_dict(encrypted)
        for k in DEFAULT_SENSITIVE_KEYS:
            assert decrypted[k] == f"val-{k}"

    def test_auto_encrypt_empty_dict(self) -> None:
        assert auto_encrypt_dict({}) == {}

    def test_auto_decrypt_empty_dict(self) -> None:
        assert auto_decrypt_dict({}) == {}

    def test_auto_encrypt_does_not_mutate_input(self) -> None:
        data = {"password": "secret"}
        original_val = data["password"]
        auto_encrypt_dict(data)
        assert data["password"] == original_val  # original unchanged


# ── EncryptedField descriptor ─────────────────────────────────────────────────

class TestEncryptedField:
    def _make_model_class(self) -> type:
        class Profile:
            email = EncryptedField("_email_enc")
            phone = EncryptedField("_phone_enc")

        return Profile

    def test_set_then_get_decrypts(self) -> None:
        Profile = self._make_model_class()
        p = Profile()
        p.email = "alice@example.com"
        assert p.email == "alice@example.com"

    def test_storage_attribute_is_encrypted(self) -> None:
        Profile = self._make_model_class()
        p = Profile()
        p.email = "bob@example.com"
        stored = p._email_enc
        assert stored.startswith(("nse1:", "nse2:"))

    def test_set_none_stores_none(self) -> None:
        Profile = self._make_model_class()
        p = Profile()
        p.email = None
        assert p.email is None
        assert getattr(p, "_email_enc", None) is None

    def test_unset_field_returns_none(self) -> None:
        Profile = self._make_model_class()
        p = Profile()
        assert p.phone is None

    def test_multiple_instances_independent(self) -> None:
        Profile = self._make_model_class()
        p1 = Profile()
        p2 = Profile()
        p1.email = "alice@example.com"
        p2.email = "bob@example.com"
        assert p1.email == "alice@example.com"
        assert p2.email == "bob@example.com"

    def test_class_access_returns_descriptor(self) -> None:
        Profile = self._make_model_class()
        desc = Profile.email
        assert isinstance(desc, EncryptedField)

    def test_update_overwrites_previous_value(self) -> None:
        Profile = self._make_model_class()
        p = Profile()
        p.email = "first@example.com"
        p.email = "second@example.com"
        assert p.email == "second@example.com"


# ── encryption_status ─────────────────────────────────────────────────────────

class TestEncryptionStatus:
    def test_returns_dict(self) -> None:
        status = encryption_status()
        assert isinstance(status, dict)

    def test_has_required_keys(self) -> None:
        status = encryption_status()
        assert "primary_cipher" in status
        assert "fallback_cipher" in status
        assert "aes_ni_detected" in status
        assert "pynacl_available" in status
        assert "envelope_versions" in status
        assert "key_source" in status

    def test_pynacl_available_is_true(self) -> None:
        status = encryption_status()
        assert status["pynacl_available"] is True

    def test_primary_cipher_is_known_algorithm(self) -> None:
        status = encryption_status()
        assert status["primary_cipher"] in ("AES-256-GCM", "ChaCha20-Poly1305")

    def test_fallback_cipher_differs_from_primary(self) -> None:
        status = encryption_status()
        assert status["primary_cipher"] != status["fallback_cipher"]

    def test_envelope_versions_is_list(self) -> None:
        status = encryption_status()
        assert isinstance(status["envelope_versions"], list)
        assert len(status["envelope_versions"]) >= 2


# ── pgcrypto SQL helpers ──────────────────────────────────────────────────────

class TestPgcryptoSql:
    def test_encrypt_sql_contains_column(self) -> None:
        sql = pgcrypto_encrypt_sql("email")
        assert "email" in sql
        assert "pgp_sym_encrypt" in sql

    def test_decrypt_sql_contains_column(self) -> None:
        sql = pgcrypto_decrypt_sql("email_enc")
        assert "email_enc" in sql
        assert "pgp_sym_decrypt" in sql

    def test_encrypt_sql_contains_key_placeholder(self) -> None:
        sql = pgcrypto_encrypt_sql("$1")
        assert "current_setting" in sql

    def test_decrypt_sql_contains_key_placeholder(self) -> None:
        sql = pgcrypto_decrypt_sql("email_enc")
        assert "current_setting" in sql

    def test_encrypt_sql_returns_string(self) -> None:
        assert isinstance(pgcrypto_encrypt_sql("col"), str)

    def test_decrypt_sql_returns_string(self) -> None:
        assert isinstance(pgcrypto_decrypt_sql("col"), str)


# ── enable_pgcrypto / set_pgcrypto_session_key ────────────────────────────────


class TestEnablePgcrypto:
    def test_returns_true_on_success(self) -> None:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        result = enable_pgcrypto(mock_conn)
        assert result is True
        mock_conn.commit.assert_called_once()

    def test_returns_false_on_exception(self) -> None:
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("permission denied")
        result = enable_pgcrypto(mock_conn)
        assert result is False


class TestSetPgcryptoSessionKey:
    def test_returns_true_on_success(self) -> None:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        result = set_pgcrypto_session_key(mock_conn)
        assert result is True

    def test_returns_false_on_exception(self) -> None:
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("db error")
        result = set_pgcrypto_session_key(mock_conn)
        assert result is False


# ── _aes_ni_available and ChaCha20 cipher path ────────────────────────────────


class TestAesNiAvailable:
    def test_returns_bool(self) -> None:
        result = _aes_ni_available()
        assert isinstance(result, bool)

    def test_returns_false_on_exception(self) -> None:
        with patch("backend.fastapi.app.transparent_encryption.AESGCM", side_effect=Exception("hw err")):
            result = _aes_ni_available()
        assert result is False


class TestChaCha20Cipher:
    def test_roundtrip(self) -> None:
        ct = _encrypt_chacha20("hello world")
        assert ct.startswith("nse2:")
        result = _decrypt_chacha20(ct)
        assert result == "hello world"

    def test_decrypt_wrong_prefix_returns_none(self) -> None:
        result = _decrypt_chacha20("nse1:notchacha")
        assert result is None

    def test_decrypt_corrupt_returns_none(self) -> None:
        result = _decrypt_chacha20("nse2:bm90dmFsaWRiYXNlNjQ=")
        assert result is None
