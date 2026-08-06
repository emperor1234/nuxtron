"""Password hashing and field-level encryption.

``encrypt_value``/``decrypt_value`` here (AES-256-GCM, HKDF-derived from
``APP_ENC_KEY``+``PASSWORD_PEPPER``, optional PQC hybrid) is the CANONICAL
field-encryption path — it's what routers/auth.py actually uses for PII today.
Two other, non-interoperable implementations exist elsewhere in this codebase
(``field_encryption.py``'s Vault Transit scheme, ``transparent_encryption.py``'s
pgcrypto scheme) that predate a decision to consolidate on this one; see
``field_encryption.py``'s module docstring for the migration note. Do not add
new call sites for those two without first checking whether this module
already covers the need.
"""
import base64
import hashlib
import json
import os
from typing import Literal

import bcrypt
import hvac
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .config import env_bool

_PASSWORD_HASHER = PasswordHasher(
    time_cost=int(os.getenv('ARGON2_TIME_COST', '3')),
    memory_cost=int(os.getenv('ARGON2_MEMORY_COST', '65536')),
    parallelism=int(os.getenv('ARGON2_PARALLELISM', '2')),
)


def _read_vault_secret(path: str, field: str) -> str | None:
    vault_addr = os.getenv('VAULT_ADDR', '').strip()
    vault_token = os.getenv('VAULT_TOKEN', '').strip()
    if not vault_addr or not vault_token or not path:
        return None

    try:
        client = hvac.Client(url=vault_addr, token=vault_token)
        response = client.secrets.kv.v2.read_secret_version(path=path)  # type: ignore[attr-defined]
        data = response.get('data', {}).get('data', {})  # type: ignore[attr-defined]
        value = data.get(field)  # type: ignore[attr-defined]
        return str(value) if value else None  # type: ignore[arg-type]
    except Exception:
        return None


def _read_managed_secret(
    env_name: str,
    vault_path_env: str,
    default_path: str,
    vault_field_env: str,
    default_field: str,
) -> str:
    env_value = os.getenv(env_name, '').strip()
    if env_value:
        return env_value

    secret_path = os.getenv(vault_path_env, default_path)
    secret_field = os.getenv(vault_field_env, default_field)

    try:
        from .vault import get_secrets_manager

        manager = get_secrets_manager()
        secret = manager.get_secret(env_name, secret_path=secret_path, secret_field=secret_field)
        if secret:
            return secret
        if secret_field != env_name:
            alt_secret = manager.get_secret(secret_field, secret_path=secret_path, secret_field=secret_field)
            if alt_secret:
                return alt_secret
    except Exception:
        pass

    return _read_vault_secret(secret_path, secret_field) or ''


def get_password_pepper() -> str:
    vault_value = _read_managed_secret(
        'PASSWORD_PEPPER',
        'VAULT_PASSWORD_PEPPER_PATH',
        'nuxtron/security',
        'VAULT_PASSWORD_PEPPER_FIELD',
        'password_pepper',
    )
    return vault_value or 'dev-pepper-change-me'


def get_ale_key_seed() -> str:
    vault_value = _read_managed_secret(
        'APP_ENC_KEY',
        'VAULT_APP_ENC_KEY_PATH',
        'nuxtron/security',
        'VAULT_APP_ENC_KEY_FIELD',
        'app_enc_key',
    )
    return vault_value or 'dev-app-enc-key-change-me'


def _fernet_from_seed(seed: str) -> Fernet:
    digest = hashlib.sha256(seed.encode('utf-8')).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode('ascii').rstrip('=')


def _b64d(raw: str) -> bytes:
    padding = '=' * ((4 - len(raw) % 4) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode('ascii'))


def _derive_base_key() -> bytes:
    seed = f"{get_ale_key_seed()}::{get_password_pepper()}".encode()
    salt = os.getenv('APP_ENC_SALT', 'nuxtron-app-enc-salt-v1').encode('utf-8')
    return HKDF(
        algorithm=hashes.SHA384(),
        length=32,
        salt=salt,
        info=b'nuxtron/security/aes256gcm/v1',
    ).derive(seed)


def _derive_data_key(base_key: bytes, pq_shared_secret: bytes | None = None) -> bytes:
    material = base_key + (pq_shared_secret or b'')
    return HKDF(
        algorithm=hashes.SHA384(),
        length=32,
        salt=b'nuxtron-hybrid-kdf-v1',
        info=b'nuxtron/data-encryption-key',
    ).derive(material)


def _mlkem_enabled() -> bool:
    return env_bool('ENABLE_NIST_PQC_HYBRID', False)


def _read_pqc_secret(env_name: str, vault_field_env: str, default_field: str) -> str:
    return _read_managed_secret(
        env_name,
        'VAULT_NIST_PQC_PATH',
        'nuxtron/pqc',
        vault_field_env,
        default_field,
    )


def _mlkem_provider() -> str:
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
    except Exception as ex:
        try:
            import oqs  # noqa: F401
            return 'oqs'
        except Exception:
            raise RuntimeError('ENABLE_NIST_PQC_HYBRID is enabled but no ML-KEM provider is available.') from ex


def _mlkem_encapsulate() -> tuple[bytes, str, str] | None:
    if not _mlkem_enabled():
        return None

    public_key_raw = _read_pqc_secret(
        'NIST_MLKEM_PUBLIC_KEY',
        'VAULT_NIST_MLKEM_PUBLIC_KEY_FIELD',
        'mlkem_public_key',
    )
    if not public_key_raw:
        raise RuntimeError('ENABLE_NIST_PQC_HYBRID is enabled but NIST_MLKEM_PUBLIC_KEY is missing.')

    public_key = _b64d(public_key_raw)
    provider = _mlkem_provider()
    if provider == 'oqs':
        import oqs  # type: ignore[import-not-found]

        with oqs.KeyEncapsulation('ML-KEM-768') as kem:  # type: ignore[attr-defined]
            ciphertext, shared_secret = kem.encap_secret(public_key)  # type: ignore[attr-defined]
            return shared_secret, 'ML-KEM-768', _b64e(ciphertext)  # type: ignore[arg-type]

    from pqcrypto.kem import ml_kem_768

    ciphertext, shared_secret = ml_kem_768.encrypt(public_key)
    return shared_secret, 'ML-KEM-768', _b64e(ciphertext)


def _mlkem_decapsulate(kem_alg: str, kem_ciphertext_b64: str) -> bytes | None:
    if not kem_alg or not kem_ciphertext_b64:
        return None

    private_key_raw = _read_pqc_secret(
        'NIST_MLKEM_PRIVATE_KEY',
        'VAULT_NIST_MLKEM_PRIVATE_KEY_FIELD',
        'mlkem_private_key',
    )
    if not private_key_raw:
        raise RuntimeError('PQC envelope present but NIST_MLKEM_PRIVATE_KEY is missing.')

    private_key = _b64d(private_key_raw)
    provider = _mlkem_provider()
    ciphertext = _b64d(kem_ciphertext_b64)
    if provider == 'oqs':
        import oqs  # type: ignore[import-not-found]

        with oqs.KeyEncapsulation(kem_alg) as kem:  # type: ignore[attr-defined]
            kem.secret_key = private_key
            return kem.decap_secret(ciphertext)  # type: ignore[attr-defined]

    from pqcrypto.kem import ml_kem_768

    return ml_kem_768.decrypt(private_key, ciphertext)


def _encrypt_nist_aes_gcm(plaintext: str) -> str:
    base_key = _derive_base_key()

    pq = _mlkem_encapsulate()
    pq_shared = pq[0] if pq else None
    pq_alg = pq[1] if pq else ''
    pq_ct = pq[2] if pq else ''

    data_key = _derive_data_key(base_key, pq_shared_secret=pq_shared)
    nonce = os.urandom(12)
    aad = b'nuxtron:nse1:aes-256-gcm'
    ciphertext = AESGCM(data_key).encrypt(nonce, plaintext.encode('utf-8'), aad)

    envelope: dict[str, object] = {
        'v': 1,
        'alg': 'AES-256-GCM',
        'kdf': 'HKDF-SHA384',
        'nonce': _b64e(nonce),
        'ct': _b64e(ciphertext),
        'aad': _b64e(aad),
        'pq': {
            'alg': pq_alg,
            'ct': pq_ct,
        } if pq else None,
    }
    packed = json.dumps(envelope, separators=(',', ':')).encode('utf-8')
    return f"nse1:{_b64e(packed)}"


def _decrypt_nist_aes_gcm(ciphertext: str) -> str | None:
    if not ciphertext.startswith('nse1:'):
        return None

    try:
        packed = _b64d(ciphertext.split(':', 1)[1])
        envelope: dict[str, object] = json.loads(packed.decode('utf-8'))

        from typing import cast as _cast
        pq_raw = envelope.get('pq')
        pq: dict[str, object] = _cast('dict[str, object]', pq_raw) if isinstance(pq_raw, dict) else {}
        pq_alg = str(pq.get('alg') or '').strip()
        pq_ct = str(pq.get('ct') or '').strip()
        pq_shared = _mlkem_decapsulate(pq_alg, pq_ct) if pq_alg and pq_ct else None

        base_key = _derive_base_key()
        data_key = _derive_data_key(base_key, pq_shared_secret=pq_shared)
        nonce = _b64d(str(envelope['nonce']))
        ct = _b64d(str(envelope['ct']))
        aad = _b64d(str(envelope['aad']))

        plaintext = AESGCM(data_key).decrypt(nonce, ct, aad)
        return plaintext.decode('utf-8')
    except Exception:
        return None


def encrypt_value(plaintext: str) -> str:
    return _encrypt_nist_aes_gcm(plaintext)


def decrypt_value(ciphertext: str) -> str | None:
    # Preferred path: NIST AES-256-GCM envelope.
    nist_value = _decrypt_nist_aes_gcm(ciphertext)
    if nist_value is not None:
        return nist_value

    # Backward compatibility for legacy Fernet ciphertexts.
    seed = f"{get_ale_key_seed()}::{get_password_pepper()}"
    fernet = _fernet_from_seed(seed)
    try:
        return fernet.decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except (InvalidToken, ValueError):
        return None


def hash_password(password: str, algorithm: Literal['bcrypt', 'argon2id'] | None = None) -> str:
    algo = (algorithm or os.getenv('PASSWORD_HASH_ALGO', 'bcrypt')).lower()
    pepper = get_password_pepper()
    material = f"{password}{pepper}".encode()

    if algo == 'argon2id':
        hashed = _PASSWORD_HASHER.hash(material.decode('utf-8'))
        return f"argon2id${hashed}"

    rounds = int(os.getenv('BCRYPT_ROUNDS', '12'))
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(material, salt).decode('utf-8')
    return f"bcrypt${hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    pepper = get_password_pepper()
    material = f"{password}{pepper}".encode()

    if stored_hash.startswith('argon2id$'):
        encoded = stored_hash.split('$', 1)[1]
        try:
            return _PASSWORD_HASHER.verify(encoded, material.decode('utf-8'))
        except VerifyMismatchError:
            return False
        except Exception:
            return False

    if stored_hash.startswith('bcrypt$'):
        encoded: bytes = stored_hash.split('$', 1)[1].encode('utf-8')
        return bcrypt.checkpw(material, encoded)

    return False
