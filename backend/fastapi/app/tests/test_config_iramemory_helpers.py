"""Tests for pure helper functions in config.py and ira_memory.py."""
import os
from unittest.mock import patch

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.config import env_bool, required_security_vars_present
from backend.fastapi.app.ira_memory import _cosine_similarity

# ─── config: env_bool ────────────────────────────────────────────────────────

class TestEnvBool:
    def test_true_values(self):
        for val in ["1", "true", "yes", "on", "TRUE", "True", "YES"]:
            with patch.dict(os.environ, {"TEST_BOOL_VAR": val}, clear=False):
                assert env_bool("TEST_BOOL_VAR") is True

    def test_false_values(self):
        for val in ["0", "false", "no", "off", "FALSE"]:
            with patch.dict(os.environ, {"TEST_BOOL_VAR": val}, clear=False):
                assert env_bool("TEST_BOOL_VAR") is False

    def test_unset_returns_default(self):
        with patch.dict(os.environ, {}, clear=False):
            # Ensure var is not set
            os.environ.pop("NONEXISTENT_VAR_XYZ", None)
            assert env_bool("NONEXISTENT_VAR_XYZ") is False
            assert env_bool("NONEXISTENT_VAR_XYZ", default=True) is True

    def test_empty_string_returns_default(self):
        with patch.dict(os.environ, {"TEST_BOOL_VAR": ""}, clear=False):
            assert env_bool("TEST_BOOL_VAR") is False


# ─── config: required_security_vars_present ──────────────────────────────────

class TestRequiredSecurityVarsPresent:
    def test_all_present_returns_empty(self):
        with patch.dict(os.environ, {
            "FASTAPI_API_KEY": "some-key",
            "PASSWORD_PEPPER": "some-pepper",
            "APP_ENC_KEY": "00" * 32,
        }, clear=False):
            missing = required_security_vars_present()
            assert missing == []

    def test_missing_vars_returned(self):
        with patch.dict(os.environ, {
            "FASTAPI_API_KEY": "",
            "PASSWORD_PEPPER": "",
        }, clear=False):
            os.environ["APP_ENC_KEY"] = "00" * 32
            missing = required_security_vars_present()
            assert "FASTAPI_API_KEY" in missing
            assert "PASSWORD_PEPPER" in missing

    def test_returns_list(self):
        result = required_security_vars_present()
        assert isinstance(result, list)


# ─── ira_memory: _cosine_similarity ─────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_unit_vectors(self):
        v = [1.0, 0.0, 0.0]
        result = _cosine_similarity(v, v)
        assert result == 1.0

    def test_orthogonal_vectors(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        result = _cosine_similarity(v1, v2)
        assert result == 0.0

    def test_opposite_vectors(self):
        v1 = [1.0, 0.0]
        v2 = [-1.0, 0.0]
        result = _cosine_similarity(v1, v2)
        assert result == -1.0

    def test_empty_vectors_returns_zero(self):
        assert _cosine_similarity([], []) == 0.0

    def test_mismatched_lengths_returns_zero(self):
        assert _cosine_similarity([1.0, 2.0], [1.0]) == 0.0

    def test_result_clamped_to_range(self):
        v = [100.0, 0.0]
        result = _cosine_similarity(v, v)
        assert -1.0 <= result <= 1.0

    def test_non_unit_vectors(self):
        v1 = [3.0, 4.0]
        v2 = [3.0, 4.0]
        # non-normalized - dot product = 9+16=25, but no normalization
        # The function doesn't normalize, it's just raw dot product
        result = _cosine_similarity(v1, v2)
        # Should be clamped to 1.0 since 25 > 1.0
        assert result == 1.0
