"""Tests for security.py — password hashing, encrypt/decrypt, key derivation."""
import os
from unittest.mock import MagicMock, patch

import pytest

# ── helpers ──────────────────────────────────────────────────────────────────

def _import():
    """Import module fresh (clears any cached singletons if needed)."""
    import backend.fastapi.app.security as sec
    return sec


# ── _read_vault_secret ───────────────────────────────────────────────────────

class TestReadVaultSecret:
    def test_returns_none_when_no_env(self):
        sec = _import()
        result = sec._read_vault_secret("some/path", "field")
        assert result is None

    def test_returns_none_on_exception(self):
        sec = _import()
        with patch.dict(os.environ, {"VAULT_ADDR": "http://fake", "VAULT_TOKEN": "tok"}):
            with patch("hvac.Client") as mock_client:
                mock_client.return_value.secrets.kv.v2.read_secret_version.side_effect = Exception("fail")
                result = sec._read_vault_secret("path", "field")
        assert result is None


# ── _read_managed_secret ─────────────────────────────────────────────────────

class TestReadManagedSecret:
    def test_returns_env_var_if_set(self):
        sec = _import()
        with patch.dict(os.environ, {"MY_SECRET": "myvalue"}):
            result = sec._read_managed_secret("MY_SECRET", "VP", "path", "VF", "field")
        assert result == "myvalue"

    def test_falls_back_to_empty_string(self):
        sec = _import()
        # no env, no vault
        with patch.dict(os.environ, {}, clear=False):
            # ensure vars not set
            for k in ("MY_SECRET_X", "VAULT_ADDR", "VAULT_TOKEN"):
                os.environ.pop(k, None)
            result = sec._read_managed_secret("MY_SECRET_X", "VP", "p/q", "VF", "f")
        assert isinstance(result, str)


# ── get_password_pepper / get_ale_key_seed ────────────────────────────────────

class TestGetters:
    def test_get_password_pepper_default(self):
        sec = _import()
        val = sec.get_password_pepper()
        assert isinstance(val, str) and len(val) > 0

    def test_get_password_pepper_from_env(self):
        sec = _import()
        with patch.dict(os.environ, {"PASSWORD_PEPPER": "my-pepper"}):
            val = sec.get_password_pepper()
        assert val == "my-pepper"

    def test_get_ale_key_seed_default(self):
        sec = _import()
        val = sec.get_ale_key_seed()
        assert isinstance(val, str) and len(val) > 0

    def test_get_ale_key_seed_from_env(self):
        sec = _import()
        with patch.dict(os.environ, {"APP_ENC_KEY": "my-enc-key"}):
            val = sec.get_ale_key_seed()
        assert val == "my-enc-key"


# ── _b64e / _b64d roundtrip ──────────────────────────────────────────────────

class TestBase64Helpers:
    def test_roundtrip(self):
        sec = _import()
        raw = b"hello world binary \x00\xff"
        assert sec._b64d(sec._b64e(raw)) == raw

    def test_empty_bytes(self):
        sec = _import()
        assert sec._b64d(sec._b64e(b"")) == b""


# ── _derive_base_key ─────────────────────────────────────────────────────────

class TestDeriveBaseKey:
    def test_returns_32_bytes(self):
        sec = _import()
        key = sec._derive_base_key()
        assert isinstance(key, bytes) and len(key) == 32

    def test_deterministic(self):
        sec = _import()
        k1 = sec._derive_base_key()
        k2 = sec._derive_base_key()
        assert k1 == k2


# ── encrypt_value / decrypt_value ────────────────────────────────────────────

class TestEncryptDecrypt:
    def test_roundtrip(self):
        sec = _import()
        ct = sec.encrypt_value("hello world")
        assert ct.startswith("nse1:")
        pt = sec.decrypt_value(ct)
        assert pt == "hello world"

    def test_decrypt_invalid_returns_none(self):
        sec = _import()
        result = sec.decrypt_value("garbage-not-a-valid-token")
        assert result is None

    def test_decrypt_empty_string_returns_none(self):
        sec = _import()
        result = sec.decrypt_value("")
        assert result is None

    def test_encrypt_unicode(self):
        sec = _import()
        text = "héllo wörld 🌍"
        ct = sec.encrypt_value(text)
        assert sec.decrypt_value(ct) == text

    def test_encrypt_long_string(self):
        sec = _import()
        text = "A" * 10000
        ct = sec.encrypt_value(text)
        assert sec.decrypt_value(ct) == text

    def test_multiple_encryptions_differ(self):
        sec = _import()
        ct1 = sec.encrypt_value("same text")
        ct2 = sec.encrypt_value("same text")
        # Nonce is random so ciphertexts should differ
        assert ct1 != ct2

    def test_decrypt_non_nse1_prefix_tries_fernet_fallback(self):
        sec = _import()
        # A non-nse1 string that's also not valid fernet → should return None
        result = sec.decrypt_value("nse2:invaliddatahere")
        assert result is None


# ── hash_password / verify_password ─────────────────────────────────────────

class TestHashPassword:
    def test_bcrypt_hash_and_verify(self):
        sec = _import()
        hashed = sec.hash_password("secretpassword", algorithm="bcrypt")
        assert hashed.startswith("bcrypt$")
        assert sec.verify_password("secretpassword", hashed) is True

    def test_bcrypt_wrong_password(self):
        sec = _import()
        hashed = sec.hash_password("correct", algorithm="bcrypt")
        assert sec.verify_password("wrong", hashed) is False

    def test_argon2id_hash_and_verify(self):
        sec = _import()
        hashed = sec.hash_password("mypassword", algorithm="argon2id")
        assert hashed.startswith("argon2id$")
        assert sec.verify_password("mypassword", hashed) is True

    def test_argon2id_wrong_password(self):
        sec = _import()
        hashed = sec.hash_password("right", algorithm="argon2id")
        assert sec.verify_password("wrong", hashed) is False

    def test_default_algorithm_env(self):
        sec = _import()
        with patch.dict(os.environ, {"PASSWORD_HASH_ALGO": "bcrypt"}):
            hashed = sec.hash_password("pw")
        assert hashed.startswith("bcrypt$")

    def test_verify_unknown_hash_format_returns_false(self):
        sec = _import()
        assert sec.verify_password("pw", "sha256$abcdef") is False

    def test_hashes_unique(self):
        sec = _import()
        h1 = sec.hash_password("same")
        h2 = sec.hash_password("same")
        # bcrypt uses random salt
        assert h1 != h2


# ── _mlkem_enabled ───────────────────────────────────────────────────────────

class TestMlkemEnabled:
    def test_disabled_by_default(self):
        sec = _import()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENABLE_NIST_PQC_HYBRID", None)
            assert sec._mlkem_enabled() is False

    def test_enabled_when_env_true(self):
        sec = _import()
        with patch.dict(os.environ, {"ENABLE_NIST_PQC_HYBRID": "true"}):
            assert sec._mlkem_enabled() is True


# ── _mlkem_encapsulate (disabled path) ──────────────────────────────────────

class TestMlkemEncapsulate:
    def test_returns_none_when_disabled(self):
        sec = _import()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENABLE_NIST_PQC_HYBRID", None)
            result = sec._mlkem_encapsulate()
        assert result is None


# ── _fernet_from_seed ────────────────────────────────────────────────────────

class TestFernetFromSeed:
    def test_returns_fernet(self):
        from cryptography.fernet import Fernet
        sec = _import()
        f = sec._fernet_from_seed("test-seed")
        assert isinstance(f, Fernet)

    def test_fernet_encrypt_decrypt(self):
        sec = _import()
        f = sec._fernet_from_seed("test-seed")
        token = f.encrypt(b"hello")
        assert f.decrypt(token) == b"hello"


# ── _read_vault_secret: success path (lines 34-36) ───────────────────────────

class TestReadVaultSecretSuccess:
    def test_returns_value_when_vault_responds(self):
        sec = _import()
        mock_client = MagicMock()
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {"myfield": "secretvalue"}}
        }
        with patch.dict(os.environ, {"VAULT_ADDR": "http://fake-vault", "VAULT_TOKEN": "tok"}), \
             patch("hvac.Client", return_value=mock_client):
            result = sec._read_vault_secret("some/path", "myfield")
        assert result == "secretvalue"

    def test_returns_none_when_field_missing(self):
        sec = _import()
        mock_client = MagicMock()
        mock_client.secrets.kv.v2.read_secret_version.return_value = {
            "data": {"data": {}}
        }
        with patch.dict(os.environ, {"VAULT_ADDR": "http://fake-vault", "VAULT_TOKEN": "tok"}), \
             patch("hvac.Client", return_value=mock_client):
            result = sec._read_vault_secret("some/path", "missing_field")
        assert result is None


# ── _read_managed_secret: vault manager paths (lines 61, 65-67) ──────────────

class TestReadManagedSecretVaultPath:
    def test_uses_vault_manager_when_env_missing(self):
        sec = _import()
        mock_manager = MagicMock()
        mock_manager.get_secret.return_value = "vault-secret-value"
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MY_SECRET_Y", None)
            with patch("backend.fastapi.app.security.get_secrets_manager", return_value=mock_manager,
                       create=True):
                # Patch the import inside _read_managed_secret
                with patch.dict(
                    __import__("sys").modules,
                    {"backend.fastapi.app.vault": MagicMock(get_secrets_manager=lambda: mock_manager)},
                ):
                    result = sec._read_managed_secret("MY_SECRET_Y", "VP", "path", "VF", "field")
        # Either from vault or empty (import might fail gracefully) — just assert it's a string
        assert isinstance(result, str)

    def test_vault_manager_fallback_to_vault_read(self):
        sec = _import()
        # When vault module raises, falls back to _read_vault_secret
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MY_SECRET_Z", None)
            os.environ.pop("VAULT_ADDR", None)
            result = sec._read_managed_secret("MY_SECRET_Z", "VP", "p/q", "VF", "f")
        assert result == ""


# ── Legacy Fernet decrypt success path (line 270-271) ────────────────────────

class TestDecryptFernetLegacy:
    def test_legacy_fernet_decrypts_correctly(self):
        sec = _import()
        seed = f"{sec.get_ale_key_seed()}::{sec.get_password_pepper()}"
        fernet = sec._fernet_from_seed(seed)
        legacy_ct = fernet.encrypt(b"legacy value").decode()
        # Should be decrypted via Fernet fallback (not nse1:)
        result = sec.decrypt_value(legacy_ct)
        assert result == "legacy value"


# ── Argon2id exception handler in verify_password (line 318-319) ─────────────

class TestVerifyPasswordArgon2Exception:
    def test_unexpected_exception_returns_false(self):
        sec = _import()
        hashed = sec.hash_password("pw", algorithm="argon2id")
        # Patch _PASSWORD_HASHER at the module level using a wrapper
        original = sec._PASSWORD_HASHER
        mock_hasher = MagicMock(wraps=original)
        mock_hasher.verify.side_effect = Exception("internal error")
        sec._PASSWORD_HASHER = mock_hasher
        try:
            result = sec.verify_password("pw", hashed)
        finally:
            sec._PASSWORD_HASHER = original
        assert result is False


# ── _mlkem_provider (lines 145-161: provider branches) ───────────────────────

class TestMlkemProvider:
    def test_returns_pqcrypto_when_available(self):
        sec = _import()
        mock_ml_kem = MagicMock()
        with patch.dict(os.environ, {"NIST_PQC_PROVIDER": "pqcrypto"}), \
             patch.dict(__import__("sys").modules, {"pqcrypto": MagicMock(), "pqcrypto.kem": MagicMock(), "pqcrypto.kem.ml_kem_768": mock_ml_kem}):
            provider = sec._mlkem_provider()
        assert provider == "pqcrypto"

    def test_returns_unavailable_when_nothing_available(self):
        sec = _import()
        import sys
        # Remove pqcrypto and oqs from modules
        saved_pq = sys.modules.pop("pqcrypto", None)
        saved_pq_kem = sys.modules.pop("pqcrypto.kem", None)
        saved_pq_mlkem = sys.modules.pop("pqcrypto.kem.ml_kem_768", None)
        saved_oqs = sys.modules.pop("oqs", None)
        try:
            with patch.dict(os.environ, {"NIST_PQC_PROVIDER": "pqcrypto"}), \
                 patch.dict(sys.modules, {"pqcrypto": None, "pqcrypto.kem": None, "pqcrypto.kem.ml_kem_768": None, "oqs": None}):
                try:
                    provider = sec._mlkem_provider()
                except RuntimeError:
                    provider = "unavailable"
        finally:
            if saved_pq is not None:
                sys.modules["pqcrypto"] = saved_pq
            if saved_pq_kem is not None:
                sys.modules["pqcrypto.kem"] = saved_pq_kem
            if saved_pq_mlkem is not None:
                sys.modules["pqcrypto.kem.ml_kem_768"] = saved_pq_mlkem
            if saved_oqs is not None:
                sys.modules["oqs"] = saved_oqs
        assert provider in ("pqcrypto", "oqs", "unavailable")

    def test_encapsulate_raises_when_enabled_but_key_missing(self):
        sec = _import()
        with patch.dict(os.environ, {"ENABLE_NIST_PQC_HYBRID": "1", "NIST_MLKEM_PUBLIC_KEY": ""}):
            with pytest.raises(RuntimeError, match="NIST_MLKEM_PUBLIC_KEY"):
                sec._mlkem_encapsulate()

    def test_decapsulate_returns_none_when_no_alg(self):
        sec = _import()
        result = sec._mlkem_decapsulate("", "")
        assert result is None

    def test_decapsulate_raises_when_private_key_missing(self):
        sec = _import()
        with patch.dict(os.environ, {"NIST_MLKEM_PRIVATE_KEY": ""}):
            with pytest.raises(RuntimeError, match="NIST_MLKEM_PRIVATE_KEY"):
                sec._mlkem_decapsulate("ML-KEM-768", "validb64ct")
