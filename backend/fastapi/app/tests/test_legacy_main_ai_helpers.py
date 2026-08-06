"""
Tests for legacy_main.py pure helper functions — AI gateway helpers.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)



class TestProviderEnvKey:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _provider_env_key
        return _provider_env_key

    def test_openai(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-openai"}, clear=False):
            assert fn("openai") == "sk-test-openai"

    def test_anthropic(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "ant-test"}, clear=False):
            assert fn("anthropic") == "ant-test"

    def test_google_vertex(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"GOOGLE_VERTEX_API_KEY": "gv-test"}, clear=False):
            assert fn("google_vertex") == "gv-test"

    def test_cohere(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"COHERE_API_KEY": "co-test"}, clear=False):
            assert fn("cohere") == "co-test"

    def test_mistral(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "ms-test"}, clear=False):
            assert fn("mistral") == "ms-test"

    def test_together_ai(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"TOGETHER_AI_API_KEY": "tai-test"}, clear=False):
            assert fn("together_ai") == "tai-test"

    def test_stability_ai(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"STABILITY_AI_API_KEY": "sai-test"}, clear=False):
            assert fn("stability_ai") == "sai-test"

    def test_unknown_returns_empty(self) -> None:
        fn = self._fn()
        assert fn("unknown_provider_xyz") == ""


class TestProviderDefaultModel:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _provider_default_model
        return _provider_default_model

    def test_openai_default(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"OPENAI_MODEL": ""}, clear=False):
            assert fn("openai") == "gpt-4o-mini"

    def test_openai_custom(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4o"}, clear=False):
            assert fn("openai") == "gpt-4o"

    def test_anthropic_default(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"ANTHROPIC_MODEL": ""}, clear=False):
            assert fn("anthropic") == "claude-3-5-haiku-latest"

    def test_cohere_default(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"COHERE_MODEL": ""}, clear=False):
            assert fn("cohere") == "command-r"

    def test_mistral_default(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"MISTRAL_MODEL": ""}, clear=False):
            assert fn("mistral") == "mistral-large"

    def test_stability_ai_default(self) -> None:
        from unittest.mock import patch
        fn = self._fn()
        with patch.dict(os.environ, {"STABILITY_AI_MODEL": ""}, clear=False):
            assert fn("stability_ai") == "stable-diffusion-3"

    def test_unknown_returns_empty(self) -> None:
        fn = self._fn()
        assert fn("unknown_provider_xyz") == ""


class TestModelUnitCost:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _model_unit_cost
        return _model_unit_cost

    def test_known_provider_model(self) -> None:
        fn = self._fn()
        result = fn("openai", "gpt-4o-mini")
        assert isinstance(result, float)
        assert result > 0

    def test_unknown_provider_fallback(self) -> None:
        fn = self._fn()
        result = fn("unknown_xyz", "unknown_model")
        assert result == 0.002  # fallback


class TestModelQuality:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _model_quality
        return _model_quality

    def test_known_provider_model(self) -> None:
        fn = self._fn()
        result = fn("openai", "gpt-4o-mini")
        assert isinstance(result, float)
        assert result > 0

    def test_unknown_provider_fallback(self) -> None:
        fn = self._fn()
        result = fn("unknown_xyz", "unknown_model")
        assert result == 0.8  # fallback


class TestUsageToTokens:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _usage_to_tokens
        return _usage_to_tokens

    def test_openai_style_usage(self) -> None:
        fn = self._fn()
        pt, ct, tt = fn({"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30})
        assert pt == 10
        assert ct == 20
        assert tt == 30

    def test_anthropic_style_usage(self) -> None:
        fn = self._fn()
        pt, ct, tt = fn({"input_tokens": 15, "output_tokens": 25})
        assert pt == 15
        assert ct == 25
        assert tt == 40  # computed from pt + ct

    def test_total_computed_if_zero(self) -> None:
        fn = self._fn()
        pt, ct, tt = fn({"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 0})
        assert tt == 15

    def test_empty_dict(self) -> None:
        fn = self._fn()
        pt, ct, tt = fn({})
        assert pt == 0
        assert ct == 0
        assert tt == 0

    def test_non_dict_input(self) -> None:
        fn = self._fn()
        pt, ct, tt = fn(None)
        assert pt == 0

    def test_combined_openai_anthropic(self) -> None:
        fn = self._fn()
        pt, ct, tt = fn({"prompt_tokens": 5, "input_tokens": 3, "output_tokens": 10, "completion_tokens": 2})
        assert pt == 8  # 5 + 3
        assert ct == 12  # 2 + 10


class TestComputeRoi:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _compute_roi
        return _compute_roi

    def test_zero_tokens(self) -> None:
        fn = self._fn()
        roi, cost, value = fn(0, 0.01, 0.002, 0.9)
        assert roi == 0.0
        assert cost == 0.0
        assert value == 0.0

    def test_positive_roi(self) -> None:
        fn = self._fn()
        roi, cost, value = fn(1000, 0.05, 0.002, 1.0)
        assert roi > 0  # value > cost

    def test_negative_roi(self) -> None:
        fn = self._fn()
        roi, cost, value = fn(1000, 0.001, 0.1, 0.5)
        assert roi < 0  # cost > value

    def test_returns_three_floats(self) -> None:
        fn = self._fn()
        result = fn(500, 0.01, 0.002, 0.8)
        assert len(result) == 3
        for v in result:
            assert isinstance(v, float)


class TestCoerceInt:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _coerce_int
        return _coerce_int

    def test_int_passthrough(self) -> None:
        assert self._fn()(42) == 42

    def test_float_truncated(self) -> None:
        assert self._fn()(3.7) == 3

    def test_string_int(self) -> None:
        assert self._fn()("99") == 99

    def test_string_invalid_default(self) -> None:
        assert self._fn()("abc", -1) == -1

    def test_bool_true(self) -> None:
        assert self._fn()(True) == 1

    def test_bool_false(self) -> None:
        assert self._fn()(False) == 0

    def test_none_default(self) -> None:
        assert self._fn()(None, 7) == 7


class TestCoerceFloat:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _coerce_float
        return _coerce_float

    def test_float_passthrough(self) -> None:
        assert self._fn()(3.14) == 3.14

    def test_int_to_float(self) -> None:
        assert self._fn()(5) == 5.0

    def test_string_float(self) -> None:
        assert self._fn()("2.5") == 2.5

    def test_string_invalid_default(self) -> None:
        assert self._fn()("abc", 0.0) == 0.0

    def test_bool_true(self) -> None:
        assert self._fn()(True) == 1.0

    def test_bool_false(self) -> None:
        assert self._fn()(False) == 0.0

    def test_none_default(self) -> None:
        assert self._fn()(None, -1.0) == -1.0


class TestJsonObject:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _json_object
        return _json_object

    def test_dict_returns_dict(self) -> None:
        fn = self._fn()
        d = {"key": "value"}
        assert fn(d) is d

    def test_non_dict_returns_none(self) -> None:
        fn = self._fn()
        assert fn("string") is None
        assert fn(123) is None
        assert fn(None) is None
        assert fn([1, 2]) is None


class TestExtractOpenaiResult:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _extract_openai_result
        return _extract_openai_result

    def test_valid_response(self) -> None:
        fn = self._fn()
        data = {
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        }
        text, usage = fn(data)
        assert text == "Hello!"
        assert isinstance(usage, dict)

    def test_non_dict_returns_empty(self) -> None:
        fn = self._fn()
        text, usage = fn(None)
        assert text == ""
        assert usage == {}

    def test_empty_choices(self) -> None:
        fn = self._fn()
        text, usage = fn({"choices": [], "usage": {}})
        assert text == ""

    def test_missing_choices(self) -> None:
        fn = self._fn()
        text, usage = fn({"usage": {"total_tokens": 5}})
        assert text == ""


class TestExtractAnthropicResult:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _extract_anthropic_result
        return _extract_anthropic_result

    def test_valid_response(self) -> None:
        fn = self._fn()
        data = {
            "content": [
                {"type": "text", "text": "Hello from Claude!"},
                {"type": "tool_use", "id": "abc"},
            ],
            "usage": {"input_tokens": 5, "output_tokens": 10},
        }
        texts, usage = fn(data)
        assert texts == ["Hello from Claude!"]
        assert isinstance(usage, dict)

    def test_non_dict_returns_empty(self) -> None:
        fn = self._fn()
        texts, usage = fn(None)
        assert texts == []
        assert usage == {}

    def test_empty_content(self) -> None:
        fn = self._fn()
        texts, usage = fn({"content": [], "usage": {}})
        assert texts == []

    def test_non_list_content(self) -> None:
        fn = self._fn()
        texts, usage = fn({"content": "not a list", "usage": {}})
        assert texts == []


class TestAssetExtensionForMime:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _asset_extension_for_mime
        return _asset_extension_for_mime

    def test_png(self) -> None:
        assert self._fn()("image/png") == "png"

    def test_jpeg(self) -> None:
        assert self._fn()("image/jpeg") == "jpg"

    def test_webp(self) -> None:
        assert self._fn()("image/webp") == "webp"

    def test_mp3(self) -> None:
        assert self._fn()("audio/mpeg") == "mp3"

    def test_wav(self) -> None:
        assert self._fn()("audio/wav") == "wav"

    def test_mp4(self) -> None:
        assert self._fn()("video/mp4") == "mp4"

    def test_unknown_fallback(self) -> None:
        assert self._fn()("application/octet-stream") == "bin"

    def test_case_insensitive(self) -> None:
        assert self._fn()("IMAGE/PNG") == "png"


class TestAiQueuedItem:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _ai_queued_item
        return _ai_queued_item

    def test_returns_dict_with_expected_keys(self) -> None:
        fn = self._fn()
        result = fn("tenant-1", "openai", "gpt-4o-mini", "Hello world")
        assert result["tenant_id"] == "tenant-1"
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o-mini"
        assert result["prompt_preview"] == "Hello world"
        assert result["status"] == "queued"

    def test_reason_changes_status(self) -> None:
        fn = self._fn()
        result = fn("t1", "openai", "gpt4", "prompt", reason="rate_limit")
        assert result["status"] == "queued-rate_limit"
        assert result["reason"] == "rate_limit"

    def test_no_reason_sets_none(self) -> None:
        fn = self._fn()
        result = fn("t1", "openai", "gpt4", "prompt")
        assert result["reason"] is None

    def test_prompt_truncated_at_120(self) -> None:
        fn = self._fn()
        long_prompt = "x" * 200
        result = fn("t1", "openai", "gpt4", long_prompt)
        assert len(result["prompt_preview"]) == 120

    def test_custom_created_at(self) -> None:
        fn = self._fn()
        result = fn("t1", "openai", "gpt4", "p", created_at="2024-01-01T00:00:00Z")
        assert result["created_at"] == "2024-01-01T00:00:00Z"


class TestGetProviderHealth:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _get_provider_health
        return _get_provider_health

    def test_unknown_provider_defaults(self) -> None:
        fn = self._fn()
        health = fn("nonexistent_provider_xyz")
        assert "success_rate" in health
        assert health["success_rate"] == 1.0

    def test_returns_dict(self) -> None:
        fn = self._fn()
        result = fn("openai")
        assert isinstance(result, dict)


class TestUpdateProviderHealth:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _update_provider_health
        return _update_provider_health

    def test_success_updates_rate(self) -> None:
        from backend.fastapi.app.legacy_main import _get_provider_health
        fn = self._fn()
        fn("test_prov_success", True, 100.0)
        health = _get_provider_health("test_prov_success")
        assert health.get("requests_total", 0) >= 1

    def test_failure_increments_errors(self) -> None:
        from backend.fastapi.app.legacy_main import _get_provider_health
        fn = self._fn()
        fn("test_prov_fail", False, 0.0)
        health = _get_provider_health("test_prov_fail")
        assert health.get("consecutive_errors", 0) >= 1


class TestDecryptValueOrEmpty:
    def _fn(self):
        from backend.fastapi.app.legacy_main import _decrypt_value_or_empty
        return _decrypt_value_or_empty

    def test_empty_returns_empty(self) -> None:
        fn = self._fn()
        assert fn("") == ""

    def test_invalid_ciphertext_returns_empty(self) -> None:
        fn = self._fn()
        result = fn("not_valid_ciphertext")
        assert result == ""
