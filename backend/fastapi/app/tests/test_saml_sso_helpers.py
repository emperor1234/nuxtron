"""Tests for pure helpers in saml_sso.py."""
import os
from unittest.mock import patch

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.saml_sso import is_saml_enabled


class TestIsSamlEnabled:
    def test_default_is_false(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SAML_ENABLED", None)
            assert is_saml_enabled() is False

    def test_enabled_true(self):
        with patch.dict(os.environ, {"SAML_ENABLED": "true"}, clear=False):
            assert is_saml_enabled() is True

    def test_enabled_1(self):
        with patch.dict(os.environ, {"SAML_ENABLED": "1"}, clear=False):
            assert is_saml_enabled() is True

    def test_disabled_false(self):
        with patch.dict(os.environ, {"SAML_ENABLED": "false"}, clear=False):
            assert is_saml_enabled() is False

    def test_disabled_0(self):
        with patch.dict(os.environ, {"SAML_ENABLED": "0"}, clear=False):
            assert is_saml_enabled() is False
