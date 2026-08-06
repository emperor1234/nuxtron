"""
Additional tests for platform_intelligence.py pure helpers.
Focus: _now, _sha256, _uptime_seconds, _detect_hallucination_indicators,
_validate_json_keys, _get_env_model_registry.
"""
from __future__ import annotations

import json
import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import patch


class TestNow:
    def test_returns_iso_string(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _now
        result = _now()
        assert isinstance(result, str)
        assert "T" in result


class TestSha256:
    def test_returns_16_char_hex(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _sha256
        result = _sha256("hello world")
        assert isinstance(result, str)
        assert len(result) == 16

    def test_consistent_hash(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _sha256
        assert _sha256("test") == _sha256("test")

    def test_different_inputs_different_hashes(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _sha256
        assert _sha256("hello") != _sha256("world")


class TestUptimeSeconds:
    def test_returns_positive_float(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _uptime_seconds
        result = _uptime_seconds()
        assert isinstance(result, float)
        assert result >= 0.0


class TestDetectHallucinationIndicators:
    def _fn(self):
        from backend.fastapi.app.routers.platform_intelligence import _detect_hallucination_indicators
        return _detect_hallucination_indicators

    def test_clean_content_high_score(self) -> None:
        result = self._fn()("The model achieved good results in the test conditions.")
        assert result["hallucination_score"] >= 80
        assert result["risk_level"] in ("low", "medium")
        assert isinstance(result["flags"], list)

    def test_overconfident_language_penalized(self) -> None:
        result = self._fn()("This is 100% guaranteed to work without exception. It always performs perfectly.")
        assert result["hallucination_score"] < 100

    def test_short_content_penalized(self) -> None:
        result = self._fn()("yes")
        assert "suspiciously short" in " ".join(result["flags"]).lower() or result["hallucination_score"] < 100

    def test_future_years_penalized(self) -> None:
        result = self._fn()("This will happen in 2087 and 2099.")
        flags_text = " ".join(result["flags"]).lower()
        assert "future" in flags_text or result["hallucination_score"] < 100

    def test_contradiction_detected(self) -> None:
        result = self._fn()("The process always increases and always decreases the value at the same time.")
        # "always" + "sometimes" or "increase" + "decrease" should be flagged
        assert len(result["flags"]) > 0 or result["hallucination_score"] < 100

    def test_returns_required_keys(self) -> None:
        result = self._fn()("Some content here")
        assert "hallucination_score" in result
        assert "risk_level" in result
        assert "flags" in result
        assert "flag_count" in result

    def test_risk_level_mapping(self) -> None:
        result = self._fn()("Normal content without issues, a reasonable analysis.")
        assert result["risk_level"] in ("low", "medium", "high")

    def test_score_capped_at_zero(self) -> None:
        # Very bad content to test floor of 0
        bad = "always never always never always never always sometimes " * 20 + "never always"
        result = self._fn()(bad)
        assert result["hallucination_score"] >= 0

    def test_low_lexical_diversity_penalized(self) -> None:
        # Repetitive content
        repetitive = ("word " * 60).strip()
        result = self._fn()(repetitive)
        assert result["hallucination_score"] < 100


class TestValidateJsonKeys:
    def _fn(self):
        from backend.fastapi.app.routers.platform_intelligence import _validate_json_keys
        return _validate_json_keys

    def test_valid_all_keys_present(self) -> None:
        content = json.dumps({"name": "Alice", "age": 30})
        result = self._fn()(content, ["name", "age"])
        assert result["valid"] is True
        assert result["missing_keys"] == []

    def test_missing_keys_detected(self) -> None:
        content = json.dumps({"name": "Alice"})
        result = self._fn()(content, ["name", "age"])
        assert result["valid"] is False
        assert "age" in result["missing_keys"]
        assert "name" in result["found_keys"]

    def test_invalid_json(self) -> None:
        result = self._fn()("not-valid-json", ["key1"])
        assert result["valid"] is False
        assert result["parse_error"] is not None

    def test_empty_required_keys(self) -> None:
        result = self._fn()(json.dumps({"x": 1}), [])
        assert result["valid"] is True

    def test_empty_json_object(self) -> None:
        result = self._fn()(json.dumps({}), ["required_key"])
        assert result["valid"] is False
        assert "required_key" in result["missing_keys"]


class TestGetEnvModelRegistry:
    def test_returns_list(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _get_env_model_registry
        result = _get_env_model_registry()
        assert isinstance(result, list)

    def test_has_required_fields(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _get_env_model_registry
        result = _get_env_model_registry()
        for model in result:
            assert "id" in model
            assert "provider" in model
            assert "model" in model

    def test_openai_entry_when_key_set(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _get_env_model_registry
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key"}, clear=False):
            result = _get_env_model_registry()
            providers = [m["provider"] for m in result]
            assert "openai" in providers

    def test_anthropic_entry_when_key_set(self) -> None:
        from backend.fastapi.app.routers.platform_intelligence import _get_env_model_registry
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "ant-test-key"}, clear=False):
            result = _get_env_model_registry()
            providers = [m["provider"] for m in result]
            assert "anthropic" in providers
