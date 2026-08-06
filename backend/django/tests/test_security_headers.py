"""Security-header tests: CSP enforcement (WO-1) and CSRF trusted origins (WO-2).

These tests fail if the corresponding Work Order is reverted — e.g. removing
``csp.middleware.CSPMiddleware`` makes the first test fail because no
``Content-Security-Policy`` header is emitted.
"""
from __future__ import annotations

import pytest
from django.test import Client


def _csp_policy(response) -> str:
    """Return the CSP policy string whether enforcing or report-only.

    In DEBUG the header is ``Content-Security-Policy-Report-Only`` (staged
    rollout); in production it is the enforcing ``Content-Security-Policy``.
    Either way the directive set must be present and strict.
    """
    return (
        response.headers.get('Content-Security-Policy')
        or response.headers.get('Content-Security-Policy-Report-Only')
        or ''
    )


@pytest.mark.django_db
class TestContentSecurityPolicy:
    def test_csp_header_present_on_response(self) -> None:
        client = Client(HTTP_HOST='testserver')
        response = client.get('/api/health/')
        # Must emit a CSP header in either enforcing or report-only form.
        assert _csp_policy(response), (
            'No Content-Security-Policy header emitted; is CSPMiddleware wired?'
        )

    def test_csp_denies_object_and_frame_ancestors(self) -> None:
        client = Client(HTTP_HOST='testserver')
        response = client.get('/api/health/')
        policy = _csp_policy(response)
        assert "object-src 'none'" in policy
        assert "frame-ancestors 'none'" in policy

    def test_csp_has_no_unsafe_inline_or_eval(self) -> None:
        client = Client(HTTP_HOST='testserver')
        response = client.get('/api/health/')
        policy = _csp_policy(response)
        assert "'unsafe-inline'" not in policy
        assert "'unsafe-eval'" not in policy

    def test_missing_report_uri_fails_closed_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from django.core.exceptions import ImproperlyConfigured

        from config.csp import build_csp_settings

        monkeypatch.delenv('DJANGO_CSP_REPORT_URI', raising=False)
        with pytest.raises(ImproperlyConfigured):
            build_csp_settings(debug=False)


class TestCsrfTrustedOrigins:
    def test_missing_trusted_origins_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from django.core.exceptions import ImproperlyConfigured

        from config.settings import _require_csrf_trusted_origins

        monkeypatch.delenv('DJANGO_CSRF_TRUSTED_ORIGINS', raising=False)
        with pytest.raises(ImproperlyConfigured):
            _require_csrf_trusted_origins(debug=False)

    def test_http_origin_rejected_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from django.core.exceptions import ImproperlyConfigured

        from config.settings import _require_csrf_trusted_origins

        monkeypatch.setenv('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://insecure.example.com')
        with pytest.raises(ImproperlyConfigured):
            _require_csrf_trusted_origins(debug=False)

    def test_valid_https_origin_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from config.settings import _require_csrf_trusted_origins

        monkeypatch.setenv(
            'DJANGO_CSRF_TRUSTED_ORIGINS', 'https://app.nuxtron.io,https://admin.nuxtron.io'
        )
        origins = _require_csrf_trusted_origins(debug=False)
        assert origins == ['https://app.nuxtron.io', 'https://admin.nuxtron.io']

    def test_dev_allows_empty_origins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from config.settings import _require_csrf_trusted_origins

        monkeypatch.delenv('DJANGO_CSRF_TRUSTED_ORIGINS', raising=False)
        assert _require_csrf_trusted_origins(debug=True) == []
