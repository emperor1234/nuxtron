"""NIST PQ readiness helpers for hybrid API-security posture.

This module keeps runtime safe even when PQ libraries are not installed.
When liboqs is available, it verifies ML-KEM-768 capability; otherwise
it returns a deterministic fallback posture.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class QuantumNistStatus:
    enabled: bool
    algorithm: str
    provider: str
    mode: str
    detail: str


def get_quantum_nist_status() -> QuantumNistStatus:
    forced = os.getenv('FORCE_NIST_PQC_ENABLED', '').strip().lower() in {'1', 'true', 'yes'}

    try:
        import oqs  # type: ignore

        provider_ok = False
        with oqs.KeyEncapsulation('ML-KEM-768'):
            provider_ok = True
        if not provider_ok:
            raise RuntimeError('ML-KEM-768 unavailable')

        return QuantumNistStatus(
            enabled=True,
            algorithm='ML-KEM-768',
            provider='liboqs',
            mode='hybrid-ready',
            detail='NIST PQ KEM available for hybrid key exchange.',
        )
    except (Exception, SystemExit) as exc:
        if forced:
            return QuantumNistStatus(
                enabled=False,
                algorithm='ML-KEM-768',
                provider='none',
                mode='misconfigured',
                detail=f'PQC forced but unavailable: {exc}',
            )
        return QuantumNistStatus(
            enabled=False,
            algorithm='ML-KEM-768',
            provider='none',
            mode='aes-only-fallback',
            detail='PQC library unavailable; AES-256-GCM remains active.',
        )
