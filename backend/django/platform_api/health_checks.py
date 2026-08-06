"""Infrastructure dependency checks used by health/readiness endpoints.

Each checker returns ``(ok: bool, detail: str)`` and must never raise — a raising
checker would make the health endpoint itself unhealthy and mask the real cause.
"""

from __future__ import annotations

import time
from typing import Callable, NamedTuple

from django.conf import settings
from django.db import DatabaseError, connection, OperationalError
from django.core.cache import cache

CheckResult = NamedTuple('CheckResult', [('ok', bool), ('detail', str)])


class HealthCheckError(Exception):
    """Raised only by callers that want to short-circuit on a failed check."""


def check_database() -> CheckResult:
    """Round-trip a SELECT 1 against the default database."""
    start = time.perf_counter()
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            row = cur.fetchone()
        ok = bool(row and row[0] == 1)
        latency_ms = (time.perf_counter() - start) * 1000
        return CheckResult(ok, f'{latency_ms:.1f}ms')
    except (OperationalError, DatabaseError) as exc:
        return CheckResult(False, f'database error: {exc.__class__.__name__}: {exc}')
    except Exception as exc:  # pragma: no cover - defensive
        return CheckResult(False, f'unexpected: {exc.__class__.__name__}: {exc}')


def check_cache() -> CheckResult:
    """Round-trip a set/get/del against the configured cache backend."""
    start = time.perf_counter()
    probe_key = f'health:probe:{int(time.time())}'
    try:
        cache.set(probe_key, '1', timeout=10)
        value = cache.get(probe_key)
        cache.delete(probe_key)
        ok = value == '1'
        latency_ms = (time.perf_counter() - start) * 1000
        backend = getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown')
        return CheckResult(ok, f'{backend} {latency_ms:.1f}ms')
    except Exception as exc:  # cache must never make /health crash
        return CheckResult(False, f'cache error: {exc.__class__.__name__}: {exc}')


def _vault_client():  # pragma: no cover - exercised only when vault is configured
    try:
        import hvac  # type: ignore
    except ImportError:
        return None
    addr = getattr(settings, 'VAULT_ADDR', '')
    token = getattr(settings, 'VAULT_TOKEN', '')
    if not addr or not token:
        return None
    try:
        client = hvac.Client(url=addr, token=token)
        if getattr(settings, 'VAULT_NAMESPACE', ''):
            client.adapter.headers['X-Vault-Request'] = 'true'
        return client
    except Exception:
        return None


def check_vault() -> CheckResult:
    """Best-effort Vault seal/auth probe. Non-fatal if Vault is unconfigured."""
    addr = getattr(settings, 'VAULT_ADDR', '')
    if not addr or not getattr(settings, 'VAULT_TOKEN', ''):
        return CheckResult(True, 'not configured (skipped)')
    client = _vault_client()
    if client is None:
        return CheckResult(False, 'hvac not installed')
    try:
        is_authenticated = bool(client.is_authenticated())
        sealed = bool(client.sys.is_sealed()) if is_authenticated else True
        return CheckResult(is_authenticated and not sealed, 'authed, unsealed' if is_authenticated else 'auth failed')
    except Exception as exc:
        return CheckResult(False, f'vault error: {exc.__class__.__name__}: {exc}')


# Registry — ordered; DB is the most important signal for readiness.
CHECKS: list[tuple[str, Callable[[], CheckResult]]] = [
    ('database', check_database),
    ('cache', check_cache),
    ('vault', check_vault),
]
