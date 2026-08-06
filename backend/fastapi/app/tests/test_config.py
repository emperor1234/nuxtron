"""Tests for config.py — env_bool, required_security_vars_present, validate_startup_security."""
import os
from unittest.mock import patch

import pytest
from backend.fastapi.app.config import (
    env_bool,
    required_security_vars_present,
    validate_startup_security,
)


class TestEnvBool:
    def test_returns_default_when_not_set(self):
        os.environ.pop("_TEST_BOOL_X", None)
        assert env_bool("_TEST_BOOL_X", False) is False
        assert env_bool("_TEST_BOOL_X", True) is True

    def test_true_values(self):
        for val in ("1", "true", "yes", "on", "True", "YES", "ON"):
            with patch.dict(os.environ, {"_TEST_BOOL_Y": val}):
                assert env_bool("_TEST_BOOL_Y") is True

    def test_false_values(self):
        for val in ("0", "false", "no", "off", "False", "NO"):
            with patch.dict(os.environ, {"_TEST_BOOL_Z": val}):
                assert env_bool("_TEST_BOOL_Z", True) is False


class TestRequiredSecurityVarsPresent:
    def test_all_present_returns_empty(self):
        with patch.dict(os.environ, {
            "FASTAPI_API_KEY": "key1",
            "PASSWORD_PEPPER": "pepper",
            "APP_ENC_KEY": "enckey",
        }):
            assert required_security_vars_present() == []

    def test_missing_returns_names(self):
        with patch.dict(os.environ, {}, clear=False):
            for k in ("FASTAPI_API_KEY", "PASSWORD_PEPPER", "APP_ENC_KEY"):
                os.environ.pop(k, None)
            missing = required_security_vars_present()
        assert "FASTAPI_API_KEY" in missing
        assert "PASSWORD_PEPPER" in missing
        assert "APP_ENC_KEY" in missing

    def test_partial_missing(self):
        with patch.dict(os.environ, {
            "FASTAPI_API_KEY": "key",
            "PASSWORD_PEPPER": "",
            "APP_ENC_KEY": "enc",
        }):
            missing = required_security_vars_present()
        assert "PASSWORD_PEPPER" in missing
        assert "FASTAPI_API_KEY" not in missing


class TestValidateStartupSecurity:
    def test_non_strict_does_nothing(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "SECURITY_STRICT_MODE": "false"}):
            validate_startup_security()  # should not raise

    def test_strict_raises_when_vars_missing(self):
        env = {
            "SECURITY_STRICT_MODE": "true",
            "ENVIRONMENT": "development",
            "FASTAPI_API_KEY": "",
            "PASSWORD_PEPPER": "",
            "APP_ENC_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(RuntimeError, match="required vars are missing"):
                validate_startup_security()

    def test_strict_raises_for_default_api_key(self):
        env = {
            "SECURITY_STRICT_MODE": "true",
            "FASTAPI_API_KEY": "change-this-fastapi-key",
            "PASSWORD_PEPPER": "pepper",
            "APP_ENC_KEY": "enckey",
        }
        with patch.dict(os.environ, env):
            with pytest.raises(RuntimeError, match="must be changed"):
                validate_startup_security()

    def test_production_environment_enables_strict_mode(self):
        env = {
            "ENVIRONMENT": "production",
            "SECURITY_STRICT_MODE": "false",
            "FASTAPI_API_KEY": "",
            "PASSWORD_PEPPER": "",
            "APP_ENC_KEY": "",
        }
        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(RuntimeError):
                validate_startup_security()
