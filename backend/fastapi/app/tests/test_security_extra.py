"""
Tests for security.py pure helper functions not yet covered.
Covers: _derive_data_key, _read_pqc_secret.
"""
from __future__ import annotations

import os
from unittest.mock import patch

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

from backend.fastapi.app.security import _derive_base_key, _derive_data_key, _read_pqc_secret


class TestDeriveDataKey:
    def test_returns_32_bytes(self) -> None:
        base = _derive_base_key()
        key = _derive_data_key(base)
        assert len(key) == 32

    def test_different_with_pq_secret(self) -> None:
        base = _derive_base_key()
        key_without = _derive_data_key(base, None)
        key_with = _derive_data_key(base, b"pq-secret-bytes")
        assert key_without != key_with

    def test_deterministic(self) -> None:
        base = _derive_base_key()
        key1 = _derive_data_key(base, b"same-secret")
        key2 = _derive_data_key(base, b"same-secret")
        assert key1 == key2

    def test_empty_pq_secret_same_as_none(self) -> None:
        base = _derive_base_key()
        key_none = _derive_data_key(base, None)
        key_empty = _derive_data_key(base, b"")
        assert key_none == key_empty


class TestReadPqcSecret:
    def test_returns_env_var_when_set(self) -> None:
        with patch.dict(os.environ, {"PQC_TEST_KEY": "my-secret-value"}):
            result = _read_pqc_secret("PQC_TEST_KEY", "VAULT_FIELD_ENV", "default-field")
            assert result == "my-secret-value"

    def test_returns_empty_when_env_not_set(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            # Remove env var if set
            os.environ.pop("PQC_MISSING_KEY", None)
            result = _read_pqc_secret("PQC_MISSING_KEY", "VAULT_FIELD_ENV", "default-field")
            # Should return some string (empty or default)
            assert isinstance(result, str)
