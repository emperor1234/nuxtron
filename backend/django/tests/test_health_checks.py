"""Tests for platform_api.health_checks — the readiness/liveness dependency probes.

These were previously the thinnest-covered module in the Django service
(~26%). Focused on the contract every checker promises: return
CheckResult(ok, detail), never raise, even when the dependency is broken.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from platform_api.health_checks import (
    CHECKS,
    CheckResult,
    check_cache,
    check_database,
    check_vault,
)

# check_cache's "healthy roundtrip" case needs a real, reachable cache
# backend; the deployed config points at Redis, unavailable in a plain
# unit-test environment. LocMemCache exercises the same set/get/delete code
# path without requiring live Redis.
_LOCMEM_CACHE = override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})


class TestCheckDatabase:
    @pytest.mark.django_db
    def test_returns_ok_true_on_healthy_connection(self) -> None:
        result = check_database()
        assert isinstance(result, CheckResult)
        assert result.ok is True
        assert 'ms' in result.detail

    def test_returns_ok_false_on_operational_error(self) -> None:
        from django.db import OperationalError

        with patch('platform_api.health_checks.connection') as mock_conn:
            mock_conn.cursor.side_effect = OperationalError('connection refused')
            result = check_database()
        assert result.ok is False
        assert 'database error' in result.detail

    def test_never_raises_on_unexpected_exception(self) -> None:
        with patch('platform_api.health_checks.connection') as mock_conn:
            mock_conn.cursor.side_effect = RuntimeError('something else broke')
            result = check_database()
        assert result.ok is False
        assert 'unexpected' in result.detail


class TestCheckCache:
    @_LOCMEM_CACHE
    def test_returns_ok_true_on_healthy_roundtrip(self) -> None:
        result = check_cache()
        assert isinstance(result, CheckResult)
        assert result.ok is True

    def test_returns_ok_false_when_cache_raises(self) -> None:
        with patch('platform_api.health_checks.cache') as mock_cache:
            mock_cache.set.side_effect = RuntimeError('cache backend down')
            result = check_cache()
        assert result.ok is False
        assert 'cache error' in result.detail

    def test_returns_ok_false_when_value_mismatch(self) -> None:
        with patch('platform_api.health_checks.cache') as mock_cache:
            mock_cache.get.return_value = 'not-what-we-set'
            result = check_cache()
        assert result.ok is False


class TestCheckVault:
    def test_skipped_when_not_configured(self) -> None:
        with patch('platform_api.health_checks.settings') as mock_settings:
            mock_settings.VAULT_ADDR = ''
            mock_settings.VAULT_TOKEN = ''
            result = check_vault()
        assert result.ok is True
        assert 'not configured' in result.detail

    def test_fails_when_hvac_client_unavailable(self) -> None:
        with patch('platform_api.health_checks.settings') as mock_settings, \
             patch('platform_api.health_checks._vault_client', return_value=None):
            mock_settings.VAULT_ADDR = 'https://vault.internal'
            mock_settings.VAULT_TOKEN = 'test-token'
            result = check_vault()
        assert result.ok is False
        assert 'hvac not installed' in result.detail

    def test_authenticated_and_unsealed_is_ok(self) -> None:
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client.sys.is_sealed.return_value = False
        with patch('platform_api.health_checks.settings') as mock_settings, \
             patch('platform_api.health_checks._vault_client', return_value=mock_client):
            mock_settings.VAULT_ADDR = 'https://vault.internal'
            mock_settings.VAULT_TOKEN = 'test-token'
            result = check_vault()
        assert result.ok is True
        assert 'unsealed' in result.detail

    def test_sealed_vault_is_not_ok(self) -> None:
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client.sys.is_sealed.return_value = True
        with patch('platform_api.health_checks.settings') as mock_settings, \
             patch('platform_api.health_checks._vault_client', return_value=mock_client):
            mock_settings.VAULT_ADDR = 'https://vault.internal'
            mock_settings.VAULT_TOKEN = 'test-token'
            result = check_vault()
        assert result.ok is False

    def test_vault_client_exception_is_caught(self) -> None:
        mock_client = MagicMock()
        mock_client.is_authenticated.side_effect = RuntimeError('network error')
        with patch('platform_api.health_checks.settings') as mock_settings, \
             patch('platform_api.health_checks._vault_client', return_value=mock_client):
            mock_settings.VAULT_ADDR = 'https://vault.internal'
            mock_settings.VAULT_TOKEN = 'test-token'
            result = check_vault()
        assert result.ok is False
        assert 'vault error' in result.detail


class TestChecksRegistry:
    def test_registry_has_expected_checks_in_order(self) -> None:
        names = [name for name, _ in CHECKS]
        assert names == ['database', 'cache', 'vault']
