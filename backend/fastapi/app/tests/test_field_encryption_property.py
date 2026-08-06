from __future__ import annotations

from backend.fastapi.app.field_encryption import AESGCMLocalCipher
from hypothesis import given, settings
from hypothesis import strategies as st


@given(
    plaintext=st.binary(min_size=0, max_size=1024),
    key=st.binary(min_size=32, max_size=32),
)
@settings(max_examples=50)
def test_aesgcm_local_roundtrip(plaintext: bytes, key: bytes) -> None:
    token = AESGCMLocalCipher.encrypt(plaintext, key)
    restored = AESGCMLocalCipher.decrypt(token, key)
    assert restored == plaintext


@given(
    plaintext=st.binary(min_size=1, max_size=256),
    key=st.binary(min_size=32, max_size=32),
)
@settings(max_examples=30)
def test_aesgcm_local_ciphertext_differs_from_plaintext(plaintext: bytes, key: bytes) -> None:
    token = AESGCMLocalCipher.encrypt(plaintext, key)
    assert token.startswith(AESGCMLocalCipher.PREFIX)
    raw = token[len(AESGCMLocalCipher.PREFIX):].encode()
    assert len(raw) > len(plaintext)
