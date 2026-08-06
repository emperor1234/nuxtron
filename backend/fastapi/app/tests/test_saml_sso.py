"""Tests for saml_sso.py — SAML enabled/disabled, _base_url, _request_data, _settings."""
import os
from unittest.mock import MagicMock, patch

import pytest
from backend.fastapi.app.saml_sso import (
    SAML_BINDING_HTTP_POST,
    SAML_BINDING_HTTP_REDIRECT,
    _base_url,
    _ensure_toolkit_available,
    _request_data,
    _settings,
    is_saml_enabled,
    login_url,
    metadata_xml,
    process_acs,
)
from fastapi import Request


def _make_request(url: str = "http://localhost/auth/saml/acs", headers: dict | None = None) -> Request:
    """Create a minimal Starlette Request for testing."""
    {
        "type": "http",
        "method": "GET",
        "path": "/auth/saml/acs",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "server": ("localhost", 80),
    }
    # Use a mock URL object
    mock_request = MagicMock(spec=Request)
    mock_request.headers = headers or {}
    mock_request.query_params = {}
    from starlette.datastructures import URL
    mock_request.url = URL(url)
    mock_request.base_url = URL("http://localhost/")
    return mock_request


class TestIsSamlEnabled:
    def test_disabled_by_default(self):
        os.environ.pop("SAML_ENABLED", None)
        assert is_saml_enabled() is False

    def test_enabled_when_env_true(self):
        with patch.dict(os.environ, {"SAML_ENABLED": "true"}):
            assert is_saml_enabled() is True

    def test_disabled_when_false(self):
        with patch.dict(os.environ, {"SAML_ENABLED": "false"}):
            assert is_saml_enabled() is False


class TestEnsureToolkitAvailable:
    def test_raises_when_onelogin_missing(self):
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "onelogin":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            with pytest.raises(RuntimeError, match="SAML toolkit not installed"):
                _ensure_toolkit_available()

    def test_passes_when_onelogin_present(self):
        with patch("builtins.__import__", side_effect=lambda n, *a, **kw: MagicMock() if n == "onelogin" else __import__(n, *a, **kw)):
            _ensure_toolkit_available()  # should not raise


class TestBaseUrl:
    def test_uses_explicit_env_var(self):
        req = _make_request()
        with patch.dict(os.environ, {"SAML_PUBLIC_BASE_URL": "https://my-app.com/"}):
            result = _base_url(req)
        assert result == "https://my-app.com"

    def test_falls_back_to_request_base_url(self):
        req = _make_request()
        os.environ.pop("SAML_PUBLIC_BASE_URL", None)
        result = _base_url(req)
        assert result.startswith("http")

    def test_strips_trailing_slash(self):
        req = _make_request()
        with patch.dict(os.environ, {"SAML_PUBLIC_BASE_URL": "https://example.com///"}):
            result = _base_url(req)
        assert not result.endswith("/")


class TestRequestData:
    def test_returns_dict_with_required_keys(self):
        req = _make_request()
        data = _request_data(req)
        assert "https" in data
        assert "http_host" in data
        assert "server_port" in data
        assert "script_name" in data
        assert "query_string" in data
        assert "get_data" in data
        assert "post_data" in data

    def test_http_url_returns_off(self):
        req = _make_request(url="http://localhost/path")
        data = _request_data(req)
        assert data["https"] == "off"

    def test_https_url_returns_on(self):
        req = _make_request(url="https://secure.example.com/saml/acs")
        data = _request_data(req)
        assert data["https"] == "on"

    def test_post_data_starts_empty(self):
        req = _make_request()
        data = _request_data(req)
        assert data["post_data"] == {}


class TestSamlConstants:
    def test_binding_constants(self):
        assert "HTTP-POST" in SAML_BINDING_HTTP_POST
        assert "HTTP-Redirect" in SAML_BINDING_HTTP_REDIRECT


# ── _settings() path (lines 33-64) ───────────────────────────────────────────


class TestSettings:
    _SAML_ENV = {
        "SAML_IDP_ENTITY_ID": "https://idp.example.com",
        "SAML_IDP_SSO_URL": "https://idp.example.com/sso",
        "SAML_IDP_SLO_URL": "https://idp.example.com/slo",
        "SAML_IDP_X509_CERT": "MIIcertXXX",
    }

    def test_raises_when_idp_entity_id_missing(self):
        req = _make_request()
        with patch.dict(os.environ, {"SAML_IDP_ENTITY_ID": "", "SAML_IDP_SSO_URL": "https://sso"}):
            with pytest.raises(RuntimeError, match="SAML IdP settings"):
                _settings(req)

    def test_raises_when_idp_sso_url_missing(self):
        req = _make_request()
        with patch.dict(os.environ, {"SAML_IDP_ENTITY_ID": "https://idp", "SAML_IDP_SSO_URL": ""}):
            with pytest.raises(RuntimeError, match="SAML IdP settings"):
                _settings(req)

    def test_returns_dict_with_all_sections(self):
        req = _make_request()
        with patch.dict(os.environ, self._SAML_ENV):
            result = _settings(req)
        assert "sp" in result
        assert "idp" in result
        assert "security" in result

    def test_sp_entity_id_defaults_to_base_url_path(self):
        req = _make_request()
        env = {**self._SAML_ENV, "SAML_SP_ENTITY_ID": ""}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("SAML_SP_ENTITY_ID", None)
            result = _settings(req)
        assert "/auth/saml/metadata" in str(result["sp"]["entityId"])

    def test_sp_entity_id_uses_env_when_set(self):
        req = _make_request()
        env = {**self._SAML_ENV, "SAML_SP_ENTITY_ID": "https://mysp.example.com"}
        with patch.dict(os.environ, env):
            result = _settings(req)
        assert result["sp"]["entityId"] == "https://mysp.example.com"

    def test_can_sign_when_cert_and_key_set(self):
        req = _make_request()
        env = {
            **self._SAML_ENV,
            "SAML_SP_X509_CERT": "mycert",
            "SAML_SP_PRIVATE_KEY": "mykey",
        }
        with patch.dict(os.environ, env):
            result = _settings(req)
        # When both cert + key are present, signing defaults to True
        assert result["security"]["authnRequestsSigned"] is True

    def test_cannot_sign_without_cert_or_key(self):
        req = _make_request()
        env = {**self._SAML_ENV, "SAML_SP_X509_CERT": "", "SAML_SP_PRIVATE_KEY": ""}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("SAML_SP_X509_CERT", None)
            os.environ.pop("SAML_SP_PRIVATE_KEY", None)
            result = _settings(req)
        assert result["security"]["authnRequestsSigned"] is False


# ── metadata_xml, login_url, process_acs (lines 126-160) ─────────────────────


def _mock_onelogin():
    """Create a mock onelogin.saml2 module tree."""
    mock_onelogin = MagicMock()
    mock_settings_cls = MagicMock()
    mock_settings_instance = MagicMock()
    mock_settings_instance.get_sp_metadata.return_value = "<xml>meta</xml>"
    mock_settings_instance.validate_metadata.return_value = []
    mock_settings_cls.return_value = mock_settings_instance
    mock_onelogin.saml2.settings.OneLogin_Saml2_Settings = mock_settings_cls

    mock_auth_cls = MagicMock()
    mock_auth_instance = MagicMock()
    mock_auth_instance.login.return_value = "https://idp.example.com/sso?SAMLRequest=xxx"
    mock_auth_instance.get_errors.return_value = []
    mock_auth_instance.is_authenticated.return_value = True
    mock_auth_instance.get_nameid.return_value = "user@example.com"
    mock_auth_instance.get_session_index.return_value = "_session1"
    mock_auth_instance.get_nameid_format.return_value = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    mock_auth_instance.get_attributes.return_value = {"email": ["user@example.com"]}
    mock_auth_cls.return_value = mock_auth_instance
    mock_onelogin.saml2.auth.OneLogin_Saml2_Auth = mock_auth_cls

    return mock_onelogin, mock_settings_instance, mock_auth_instance


_SAML_ENV = {
    "SAML_IDP_ENTITY_ID": "https://idp.example.com",
    "SAML_IDP_SSO_URL": "https://idp.example.com/sso",
    "SAML_IDP_SLO_URL": "",
    "SAML_IDP_X509_CERT": "",
}


class TestMetadataXml:
    def test_returns_metadata_string(self):
        req = _make_request()
        mock_onelogin, _, _ = _mock_onelogin()
        with patch.dict(os.environ, _SAML_ENV), \
             patch.dict(__import__("sys").modules, {
                 "onelogin": mock_onelogin,
                 "onelogin.saml2": mock_onelogin.saml2,
                 "onelogin.saml2.settings": mock_onelogin.saml2.settings,
             }):
            result = metadata_xml(req)
        assert "<xml>" in result

    def test_raises_on_validation_errors(self):
        req = _make_request()
        mock_onelogin, mock_settings_instance, _ = _mock_onelogin()
        mock_settings_instance.validate_metadata.return_value = ["error1"]
        with patch.dict(os.environ, _SAML_ENV), \
             patch.dict(__import__("sys").modules, {
                 "onelogin": mock_onelogin,
                 "onelogin.saml2": mock_onelogin.saml2,
                 "onelogin.saml2.settings": mock_onelogin.saml2.settings,
             }):
            with pytest.raises(RuntimeError, match="Invalid SAML metadata"):
                metadata_xml(req)


class TestLoginUrl:
    def test_returns_redirect_url(self):
        req = _make_request()
        mock_onelogin, _, mock_auth = _mock_onelogin()
        with patch.dict(os.environ, _SAML_ENV), \
             patch.dict(__import__("sys").modules, {
                 "onelogin": mock_onelogin,
                 "onelogin.saml2": mock_onelogin.saml2,
                 "onelogin.saml2.auth": mock_onelogin.saml2.auth,
             }):
            url = login_url(req, relay_state="/dashboard")
        assert "SAMLRequest" in url or url.startswith("https://")


class TestProcessAcs:
    def test_returns_user_info_on_success(self):
        req = _make_request()
        mock_onelogin, _, mock_auth = _mock_onelogin()
        with patch.dict(os.environ, _SAML_ENV), \
             patch.dict(__import__("sys").modules, {
                 "onelogin": mock_onelogin,
                 "onelogin.saml2": mock_onelogin.saml2,
                 "onelogin.saml2.auth": mock_onelogin.saml2.auth,
             }):
            result = process_acs(req, saml_response="base64response")
        assert "name_id" in result
        assert result["name_id"] == "user@example.com"

    def test_raises_on_saml_errors(self):
        req = _make_request()
        mock_onelogin, _, mock_auth = _mock_onelogin()
        mock_auth.get_errors.return_value = ["invalid_signature"]
        with patch.dict(os.environ, _SAML_ENV), \
             patch.dict(__import__("sys").modules, {
                 "onelogin": mock_onelogin,
                 "onelogin.saml2": mock_onelogin.saml2,
                 "onelogin.saml2.auth": mock_onelogin.saml2.auth,
             }):
            with pytest.raises(RuntimeError, match="SAML assertion validation"):
                process_acs(req, saml_response="bad")

    def test_raises_when_not_authenticated(self):
        req = _make_request()
        mock_onelogin, _, mock_auth = _mock_onelogin()
        mock_auth.get_errors.return_value = []
        mock_auth.is_authenticated.return_value = False
        with patch.dict(os.environ, _SAML_ENV), \
             patch.dict(__import__("sys").modules, {
                 "onelogin": mock_onelogin,
                 "onelogin.saml2": mock_onelogin.saml2,
                 "onelogin.saml2.auth": mock_onelogin.saml2.auth,
             }):
            with pytest.raises(RuntimeError, match="SAML authentication failed"):
                process_acs(req, saml_response="bad")
