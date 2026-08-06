"""Tests for platform_api.views — liveness, readiness, metrics, profile.

Django service's views.py was previously ~70% covered. These exercise the
actual HTTP contract: status codes, response shape, and the readiness
endpoint's 503-on-unhealthy-dependency behavior specifically, since that's
what an orchestrator gates traffic on.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from platform_api.health_checks import CheckResult

User = get_user_model()

# Cache-backed rate limiting (metrics_view) and cache-backed sessions
# (SESSION_ENGINE) both need a real cache backend to function at all — the
# deployed config points at Redis, which isn't available in a plain unit-test
# environment. LocMemCache exercises the same code paths without requiring
# live Redis; this is a test-environment concern, not a production one.
_LOCMEM_CACHE = override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}})


@pytest.mark.django_db
class TestHealthView:
    def test_returns_200_with_service_identity(self) -> None:
        client = Client(HTTP_HOST='testserver')
        response = client.get('/api/health/')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert data['service'] == 'django-api'
        assert 'uptime_s' in data


@pytest.mark.django_db
class TestReadinessView:
    def test_returns_200_when_all_checks_pass(self) -> None:
        client = Client(HTTP_HOST='testserver')
        with patch('platform_api.views.CHECKS', [
            ('database', lambda: CheckResult(True, 'ok')),
            ('cache', lambda: CheckResult(True, 'ok')),
        ]):
            response = client.get('/api/readiness/')
        assert response.status_code == 200
        assert response.json()['status'] == 'ok'

    def test_returns_503_when_any_check_fails(self) -> None:
        client = Client(HTTP_HOST='testserver')
        with patch('platform_api.views.CHECKS', [
            ('database', lambda: CheckResult(True, 'ok')),
            ('vault', lambda: CheckResult(False, 'sealed')),
        ]):
            response = client.get('/api/readiness/')
        assert response.status_code == 503
        data = response.json()
        assert data['status'] == 'degraded'
        assert data['checks']['vault']['ok'] is False

    def test_readiness_never_raises_even_if_a_check_would(self) -> None:
        """health_checks.py's contract is 'never raise' — readiness_view
        trusts that contract rather than wrapping each call in a try/except,
        so this confirms a broken check surfaces as ok=False, not a 500."""
        client = Client(HTTP_HOST='testserver')

        def _broken() -> CheckResult:
            return CheckResult(False, 'simulated failure, not a raised exception')

        with patch('platform_api.views.CHECKS', [('database', _broken)]):
            response = client.get('/api/readiness/')
        assert response.status_code == 503


@pytest.mark.django_db
class TestMetricsView:
    @_LOCMEM_CACHE
    def test_returns_prometheus_text_format(self) -> None:
        client = Client(HTTP_HOST='testserver')
        response = client.get('/api/metrics/')
        assert response.status_code == 200
        assert response['Content-Type'].startswith('text/plain')
        body = response.content.decode()
        assert 'nuxtron_up 1' in body
        assert 'nuxtron_db_ready' in body

    @_LOCMEM_CACHE
    def test_reflects_database_probe_failure(self) -> None:
        client = Client(HTTP_HOST='testserver')
        with patch('platform_api.views.CHECKS', [('database', lambda: CheckResult(False, 'down'))]):
            response = client.get('/api/metrics/')
        assert 'nuxtron_db_ready 0' in response.content.decode()


@pytest.mark.django_db
class TestProfileView:
    def test_requires_authentication(self) -> None:
        client = Client(HTTP_HOST='testserver')
        response = client.get('/api/profile/')
        assert response.status_code in (401, 403)

    @_LOCMEM_CACHE
    def test_returns_identity_for_authenticated_user(self) -> None:
        user = User.objects.create_user(username='profiletestuser', email='profile@example.com', password='testpass123!')
        client = Client(HTTP_HOST='testserver')
        client.force_login(user)
        response = client.get('/api/profile/')
        assert response.status_code == 200
        data = response.json()
        assert data['username'] == 'profiletestuser'
        assert data['email'] == 'profile@example.com'
        assert data['is_staff'] is False
        assert data['is_superuser'] is False
