"""
Tests for field_encryption.py — VaultTransitClient, EnvelopeEncryptor,
FieldEncryptor (local strategy), and module-level singleton.
"""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestVaultTransitClientInit:
    def test_init_stores_fields(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient(
            addr="http://vault-test:8200",
            token="s.testtoken",
            mount="test/transit",
        )
        assert client._addr == "http://vault-test:8200"
        assert client._token == "s.testtoken"
        assert client._mount == "test/transit"

    def test_default_addr_strips_slash(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient(addr="http://vault:8200/")
        assert not client._addr.endswith("/")

    def test_client_property_creates_httpx_client(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient()
        http_client = client._client
        assert http_client is not None
        # The X-Vault-Token header should be set
        assert "X-Vault-Token" in http_client.headers

    def test_client_property_returns_same_instance(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient()
        c1 = client._client
        c2 = client._client
        assert c1 is c2


class TestVaultTransitClientClose:
    def test_close_when_none(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient()
        # Should not raise when _http is None
        asyncio.run(client.close())

    def test_close_calls_aclose(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient()
        _ = client._client  # initialize _http
        asyncio.run(client.close())


class TestVaultTransitClientEncrypt:
    def test_encrypt_calls_vault(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient(addr="http://vault-test:8200", token="tok")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"ciphertext": "vault:v1:abc123"}
        }
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.post = AsyncMock(return_value=mock_response)
        client._http = mock_http

        result = asyncio.run(client.encrypt("hello world", "pii"))
        assert result == "vault:v1:abc123"

    def test_encrypt_non_200_raises(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient, VaultTransitError
        client = VaultTransitClient(addr="http://vault-test:8200", token="tok")

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "permission denied"
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.post = AsyncMock(return_value=mock_response)
        client._http = mock_http

        with pytest.raises(VaultTransitError):
            asyncio.run(client.encrypt("hello", "pii"))

    def test_encrypt_bytes_plaintext(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient(addr="http://vault-test:8200", token="tok")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"ciphertext": "vault:v1:xyz"}
        }
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.post = AsyncMock(return_value=mock_response)
        client._http = mock_http

        result = asyncio.run(client.encrypt(b"bytes data", "pii"))
        assert result == "vault:v1:xyz"


class TestVaultTransitClientDecrypt:
    def test_decrypt_calls_vault(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient(addr="http://vault-test:8200", token="tok")

        import base64
        plaintext_b64 = base64.b64encode(b"decrypted!").decode()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"plaintext": plaintext_b64}
        }
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.post = AsyncMock(return_value=mock_response)
        client._http = mock_http

        result = asyncio.run(client.decrypt("vault:v1:abc123", "pii"))
        assert result == b"decrypted!"

    def test_decrypt_non_200_raises(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient, VaultTransitError
        client = VaultTransitClient(addr="http://vault-test:8200", token="tok")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "bad token"
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.post = AsyncMock(return_value=mock_response)
        client._http = mock_http

        with pytest.raises(VaultTransitError):
            asyncio.run(client.decrypt("vault:v1:bad", "pii"))


class TestVaultTransitClientRewrap:
    def test_rewrap_calls_vault(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient(addr="http://vault-test:8200", token="tok")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {"ciphertext": "vault:v2:rewrapped"}
        }
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.post = AsyncMock(return_value=mock_response)
        client._http = mock_http

        result = asyncio.run(client.rewrap("vault:v1:old", "pii"))
        assert result == "vault:v2:rewrapped"

    def test_rewrap_non_200_raises(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient, VaultTransitError
        client = VaultTransitClient(addr="http://vault-test:8200", token="tok")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "server error"
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.post = AsyncMock(return_value=mock_response)
        client._http = mock_http

        with pytest.raises(VaultTransitError):
            asyncio.run(client.rewrap("vault:v1:token", "pii"))


class TestVaultTransitRotateAndDataKey:
    def test_rotate_key_success(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient(addr="http://vault-test:8200", token="tok")

        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.post = AsyncMock(return_value=mock_response)
        client._http = mock_http

        # Should not raise
        asyncio.run(client.rotate_key("pii"))

    def test_rotate_key_non_success_raises(self) -> None:
        from backend.fastapi.app.field_encryption import VaultTransitClient, VaultTransitError
        client = VaultTransitClient(addr="http://vault-test:8200", token="tok")

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "denied"
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.post = AsyncMock(return_value=mock_response)
        client._http = mock_http

        with pytest.raises(VaultTransitError):
            asyncio.run(client.rotate_key("pii"))

    def test_generate_data_key_success(self) -> None:
        import base64
        import os as _os

        from backend.fastapi.app.field_encryption import VaultTransitClient
        client = VaultTransitClient(addr="http://vault-test:8200", token="tok")

        dek_bytes = _os.urandom(32)
        plaintext_b64 = base64.b64encode(dek_bytes).decode()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "plaintext": plaintext_b64,
                "ciphertext": "vault:v1:edek",
            }
        }
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.post = AsyncMock(return_value=mock_response)
        client._http = mock_http

        dek, edek = asyncio.run(client.generate_data_key("attachments"))
        assert len(dek) == 32
        assert edek == "vault:v1:edek"


class TestFieldEncryptorLocalStrategy:
    def _make_enc(self) -> object:
        from backend.fastapi.app.field_encryption import FieldEncryptor
        enc = FieldEncryptor.__new__(FieldEncryptor)
        enc._vault = None
        enc._envelope = None
        enc._local_key = b"\xaa" * 32
        return enc

    def test_encrypt_local_returns_token(self) -> None:
        enc = self._make_enc()
        result = enc.encrypt_local("hello")
        assert result.startswith("local:")

    def test_decrypt_local_roundtrip(self) -> None:
        enc = self._make_enc()
        token = enc.encrypt_local("secret value")
        result = enc.decrypt_local(token)
        assert result == "secret value"

    def test_encrypt_local_bytes(self) -> None:
        enc = self._make_enc()
        result = enc.encrypt_local(b"byte value")
        assert result.startswith("local:")

    def test_local_strategy_via_async_encrypt(self) -> None:
        enc = self._make_enc()
        result = asyncio.run(enc.encrypt("async local", strategy="local"))
        assert result.startswith("local:")

    def test_local_strategy_via_async_decrypt(self) -> None:
        enc = self._make_enc()
        token = asyncio.run(enc.encrypt("async decrypt test", strategy="local"))
        result = asyncio.run(enc.decrypt(token))
        assert result == "async decrypt test"

    def test_unknown_strategy_raises(self) -> None:
        enc = self._make_enc()
        with pytest.raises(ValueError, match="Unknown encryption strategy"):
            asyncio.run(enc.encrypt("val", strategy="invalid_strategy"))

    def test_unknown_token_format_raises(self) -> None:
        enc = self._make_enc()
        with pytest.raises(ValueError, match="Unrecognised token format"):
            asyncio.run(enc.decrypt("bad:token"))

    def test_vault_property_lazy_init(self) -> None:
        from backend.fastapi.app.field_encryption import FieldEncryptor, VaultTransitClient
        enc = FieldEncryptor.__new__(FieldEncryptor)
        enc._vault = None
        enc._envelope = None
        enc._local_key = None
        enc._vault_addr = "http://vault-test:8200"
        enc._vault_token = "tok"
        enc._vault_mount = "test/transit"
        vault = enc.vault
        assert isinstance(vault, VaultTransitClient)
        # Second access returns same instance
        assert enc.vault is vault

    def test_envelope_property_lazy_init(self) -> None:
        from backend.fastapi.app.field_encryption import EnvelopeEncryptor, FieldEncryptor
        enc = FieldEncryptor.__new__(FieldEncryptor)
        enc._vault = None
        enc._envelope = None
        enc._local_key = None
        enc._vault_addr = "http://vault-test:8200"
        enc._vault_token = "tok"
        enc._vault_mount = "test/transit"
        env = enc.envelope
        assert isinstance(env, EnvelopeEncryptor)

    def test_local_key_from_env(self) -> None:
        from backend.fastapi.app.field_encryption import FieldEncryptor
        enc = FieldEncryptor.__new__(FieldEncryptor)
        enc._local_key = None
        enc._vault = None
        enc._envelope = None
        enc._vault_addr = "http://vault:8200"
        enc._vault_token = ""
        enc._vault_mount = "test/transit"
        with patch.dict(os.environ, {"APP_ENC_KEY": "00" * 32}, clear=False):
            key = enc.local_key
            assert len(key) == 32
            # Cached
            assert enc.local_key is key

    def test_local_key_missing_raises(self) -> None:
        from backend.fastapi.app.field_encryption import FieldEncryptor
        enc = FieldEncryptor.__new__(FieldEncryptor)
        enc._local_key = None
        enc._vault = None
        enc._envelope = None
        enc._vault_addr = "http://vault:8200"
        enc._vault_token = ""
        enc._vault_mount = "test/transit"
        with patch.dict(os.environ, {"APP_ENC_KEY": ""}, clear=False):
            with pytest.raises(RuntimeError, match="APP_ENC_KEY"):
                _ = enc.local_key


class TestFieldEncryptorClose:
    def test_close_no_vault(self) -> None:
        from backend.fastapi.app.field_encryption import FieldEncryptor
        enc = FieldEncryptor.__new__(FieldEncryptor)
        enc._vault = None
        enc._envelope = None
        enc._local_key = None
        # Should not raise
        asyncio.run(enc.close())


class TestGetFieldEncryptorSingleton:
    def test_singleton_returns_field_encryptor(self) -> None:
        import backend.fastapi.app.field_encryption as fe
        from backend.fastapi.app.field_encryption import FieldEncryptor, get_field_encryptor
        # Reset singleton
        fe._encryptor = None
        fe._encryptor_lock = None
        result = asyncio.run(get_field_encryptor())
        assert isinstance(result, FieldEncryptor)

    def test_singleton_returns_same_instance(self) -> None:
        import backend.fastapi.app.field_encryption as fe
        from backend.fastapi.app.field_encryption import get_field_encryptor
        fe._encryptor = None
        fe._encryptor_lock = None
        enc1 = asyncio.run(get_field_encryptor())
        enc2 = asyncio.run(get_field_encryptor())
        assert enc1 is enc2


class TestCloseFieldEncryptor:
    def test_close_singleton(self) -> None:
        import backend.fastapi.app.field_encryption as fe
        from backend.fastapi.app.field_encryption import close_field_encryptor, get_field_encryptor
        fe._encryptor = None
        fe._encryptor_lock = None
        asyncio.run(get_field_encryptor())
        asyncio.run(close_field_encryptor())
        assert fe._encryptor is None

    def test_close_when_none(self) -> None:
        import backend.fastapi.app.field_encryption as fe
        from backend.fastapi.app.field_encryption import close_field_encryptor
        fe._encryptor = None
        # Should not raise
        asyncio.run(close_field_encryptor())


class TestEnvelopeEncryptor:
    def test_decrypt_wrong_prefix_raises(self) -> None:
        from backend.fastapi.app.field_encryption import EnvelopeEncryptor
        mock_vault = MagicMock()
        enc = EnvelopeEncryptor(mock_vault)
        with pytest.raises(ValueError, match="Not an envelope token"):
            asyncio.run(enc.decrypt("vault:v1:notenvelope"))

    def test_decrypt_unknown_enc_type_raises(self) -> None:
        import base64
        import json

        from backend.fastapi.app.field_encryption import EnvelopeEncryptor
        mock_vault = MagicMock()
        enc = EnvelopeEncryptor(mock_vault)

        envelope = {"enc": "unknown/type", "key": "pii", "edek": "x", "ct": "y"}
        token = "envelope:" + base64.b64encode(json.dumps(envelope).encode()).decode()
        with pytest.raises(ValueError, match="Unknown envelope type"):
            asyncio.run(enc.decrypt(token))


class TestFieldEncryptorRewrap:
    def test_rewrap_non_vault_non_envelope_raises(self) -> None:
        from backend.fastapi.app.field_encryption import FieldEncryptor
        enc = FieldEncryptor.__new__(FieldEncryptor)
        enc._vault = None
        enc._envelope = None
        enc._local_key = b"\xaa" * 32
        enc._vault_addr = "http://vault:8200"
        enc._vault_token = ""
        enc._vault_mount = "test/transit"

        with pytest.raises(ValueError, match="Cannot rewrap"):
            asyncio.run(enc.rewrap_field("local:v1:cannot_rewrap", "pii"))
