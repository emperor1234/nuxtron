"""
Content-Security-Policy configuration for the Django service.

Design notes:
- Default-deny: every directive starts from 'self' or 'none', nothing is
  wildcarded, and nothing allows 'unsafe-inline' or 'unsafe-eval' without an
  explicit, reviewed exception below.
- Nonce-based script execution: django-csp auto-generates a per-request nonce
  and exposes it as ``request.csp_nonce``; templates that need inline <script>
  tags must use the nonce rather than adding 'unsafe-inline'.
- Report-only mode is available via CSP_REPORT_ONLY for staged rollout but
  MUST be False in production once verified (see WO-1 Verification).
"""
from __future__ import annotations

import os

from django.core.exceptions import ImproperlyConfigured


def _bool_env(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {'1', 'true', 'yes', 'on'}


def _csv_env(name: str) -> list[str]:
    val = os.environ.get(name, '')
    return [v.strip() for v in val.split(',') if v.strip()]


def build_csp_settings(*, debug: bool) -> dict:
    """
    Returns the dict of ``CSP_*`` settings to merge into ``settings.py``.

    In production (``debug=False``) this raises :class:`ImproperlyConfigured` if
    ``DJANGO_CSP_REPORT_URI`` is unset, because shipping a CSP with nowhere to
    report violations means breakages are invisible until a user complains.
    """
    report_uri = os.environ.get('DJANGO_CSP_REPORT_URI', '')
    if not debug and not report_uri:
        raise ImproperlyConfigured(
            'DJANGO_CSP_REPORT_URI must be set in production so CSP '
            'violations are observable (e.g. https://your-siem/csp-reports).'
        )

    extra_connect_src = _csv_env('DJANGO_CSP_EXTRA_CONNECT_SRC')
    extra_img_src = _csv_env('DJANGO_CSP_EXTRA_IMG_SRC')

    return {
        'CSP_DEFAULT_SRC': ("'self'",),
        'CSP_SCRIPT_SRC': ("'self'",),  # nonce is injected automatically by django-csp
        'CSP_STYLE_SRC': ("'self'",),
        'CSP_IMG_SRC': ("'self'", 'data:', *extra_img_src),
        'CSP_FONT_SRC': ("'self'",),
        'CSP_CONNECT_SRC': ("'self'", *extra_connect_src),
        'CSP_FRAME_ANCESTORS': ("'none'",),
        'CSP_FORM_ACTION': ("'self'",),
        'CSP_BASE_URI': ("'none'",),
        'CSP_OBJECT_SRC': ("'none'",),
        'CSP_UPGRADE_INSECURE_REQUESTS': not debug,
        'CSP_INCLUDE_NONCE_IN': ['script-src'],
        'CSP_REPORT_URI': [report_uri] if report_uri else [],
        'CSP_REPORT_ONLY': _bool_env('DJANGO_CSP_REPORT_ONLY', default=debug),
    }
