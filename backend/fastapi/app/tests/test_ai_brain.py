"""Tests for ai_brain.py — AIBrainModelLayer."""
from __future__ import annotations

import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from backend.fastapi.app.ai_brain import AIBrainModelLayer, _as_dict, _as_list


def _now():
    return datetime.now(UTC).isoformat()


def _make_brain(**kwargs):
    return AIBrainModelLayer(now_iso_fn=_now, **kwargs)


# --------------------------------------------------------------------------- #
#  Module-level helpers
# --------------------------------------------------------------------------- #

class TestAsDict:
    def test_with_dict(self):
        assert _as_dict({"a": 1}) == {"a": 1}

    def test_with_non_dict(self):
        assert _as_dict("string") == {}
        assert _as_dict(42) == {}
        assert _as_dict(None) == {}


class TestAsList:
    def test_with_list(self):
        assert _as_list([1, 2, 3]) == [1, 2, 3]

    def test_with_tuple(self):
        assert _as_list((1, 2)) == []  # _as_list only accepts list, not tuple

    def test_with_non_iterable(self):
        assert _as_list(None) == []
        assert _as_list(42) == []


# --------------------------------------------------------------------------- #
#  capabilities
# --------------------------------------------------------------------------- #

class TestCapabilities:
    def test_returns_dict_with_providers(self):
        brain = _make_brain()
        caps = brain.capabilities()
        assert "providers" in caps
        assert "openai" in caps["providers"]
        assert "anthropic" in caps["providers"]

    def test_principles_in_capabilities(self):
        brain = _make_brain()
        caps = brain.capabilities()
        assert "principles" in caps

    def test_recommended_order_includes_configured(self):
        brain = _make_brain()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            caps = brain.capabilities()
        assert "openai" in caps["recommended_order_auto"]

    def test_recommended_order_excludes_unconfigured_apis(self):
        brain = _make_brain()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("GOOGLE_VERTEX_API_KEY", None)
            caps = brain.capabilities()
        # llama and mistral are always "configured"
        for p in caps["recommended_order_auto"]:
            assert p in ("llama", "mistral")


# --------------------------------------------------------------------------- #
#  _auto_candidates
# --------------------------------------------------------------------------- #

class TestAutoCandidates:
    def test_with_no_api_keys_returns_open_source(self):
        brain = _make_brain()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("GOOGLE_VERTEX_API_KEY", None)
            candidates = brain._auto_candidates(require_function_calling=False)
        assert "llama" in candidates or "mistral" in candidates

    def test_with_function_calling_excludes_llama(self):
        brain = _make_brain()
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "ANTHROPIC_API_KEY": "",
            "GOOGLE_VERTEX_API_KEY": "",
        }):
            candidates = brain._auto_candidates(require_function_calling=True)
        # llama/mistral don't support function calling
        assert "llama" not in candidates or "openai" in candidates

    def test_with_no_configured_returns_fallback(self):
        brain = _make_brain()
        # Patch catalog to show nothing configured
        with patch.object(brain, "_provider_catalog", return_value={
            "openai": {"configured": False, "function_calling": True},
            "anthropic": {"configured": False, "function_calling": True},
            "google_deepmind": {"configured": False, "function_calling": True},
            "llama": {"configured": False, "function_calling": False},
            "mistral": {"configured": False, "function_calling": False},
        }):
            candidates = brain._auto_candidates(require_function_calling=False)
        assert candidates == ["llama", "mistral"]


# --------------------------------------------------------------------------- #
#  _openai_reason
# --------------------------------------------------------------------------- #

class TestOpenaiReason:
    def test_raises_when_no_api_key(self):
        brain = _make_brain()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OPENAI_API_KEY", None)
            with pytest.raises(RuntimeError, match="OpenAI is not configured"):
                brain._openai_reason(prompt="hi", model="gpt-4", tools=[], temperature=0.2, max_tokens=100)

    def test_succeeds_with_mock_response(self):
        brain = _make_brain()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "answer", "tool_calls": None}}]
        }
        mock_response.raise_for_status = MagicMock()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}), \
             patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            result = brain._openai_reason(prompt="test", model="gpt-4", tools=[], temperature=0.2, max_tokens=100)
        assert result["provider"] == "openai"
        assert result["output_text"] == "answer"

    def test_with_tools_sets_function_calling(self):
        brain = _make_brain()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "", "tool_calls": [{"id": "tc1"}]}}]
        }
        mock_response.raise_for_status = MagicMock()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}), \
             patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            result = brain._openai_reason(prompt="test", model="gpt-4", tools=[{"name": "fn1"}], temperature=0.2, max_tokens=100)
        assert result["function_calling_used"] is True


# --------------------------------------------------------------------------- #
#  _anthropic_reason
# --------------------------------------------------------------------------- #

class TestAnthropicReason:
    def test_raises_when_no_api_key(self):
        brain = _make_brain()
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(RuntimeError, match="Anthropic is not configured"):
                brain._anthropic_reason(prompt="hi", model="claude", temperature=0.2, max_tokens=100)

    def test_succeeds_with_mock(self):
        brain = _make_brain()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "claude answer"}]
        }
        mock_response.raise_for_status = MagicMock()
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}), \
             patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            result = brain._anthropic_reason(prompt="test", model="claude-3", temperature=0.2, max_tokens=100)
        assert result["provider"] == "anthropic"
        assert result["output_text"] == "claude answer"


# --------------------------------------------------------------------------- #
#  _google_reason
# --------------------------------------------------------------------------- #

class TestGoogleReason:
    def test_raises_when_not_configured(self):
        brain = _make_brain()
        with patch.dict(os.environ, {"GOOGLE_VERTEX_API_KEY": "", "GOOGLE_VERTEX_PROJECT_ID": ""}):
            with pytest.raises(RuntimeError, match="Google DeepMind"):
                brain._google_reason(prompt="hi", model="gemini", temperature=0.2, max_tokens=100)

    def test_succeeds_with_mock(self):
        brain = _make_brain()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "gemini answer"}]}}]
        }
        mock_response.raise_for_status = MagicMock()
        env = {"GOOGLE_VERTEX_API_KEY": "gvk", "GOOGLE_VERTEX_PROJECT_ID": "proj"}
        with patch.dict(os.environ, env), \
             patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            result = brain._google_reason(prompt="test", model="gemini", temperature=0.2, max_tokens=100)
        assert result["provider"] == "google_deepmind"
        assert result["output_text"] == "gemini answer"


# --------------------------------------------------------------------------- #
#  _ollama_reason
# --------------------------------------------------------------------------- #

class TestOllamaReason:
    def test_succeeds_with_mock(self):
        brain = _make_brain()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "llama response"}
        }
        mock_response.raise_for_status = MagicMock()
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_response
            result = brain._ollama_reason(provider="llama", prompt="test", model="llama3", temperature=0.2)
        assert result["provider"] == "llama"
        assert result["output_text"] == "llama response"


# --------------------------------------------------------------------------- #
#  reason() — orchestration
# --------------------------------------------------------------------------- #

class TestReason:
    def test_returns_fallback_when_all_fail(self):
        brain = _make_brain()
        # Patch all candidate providers to raise
        with patch.object(brain, "_auto_candidates", return_value=["llama"]), \
             patch.object(brain, "_ollama_reason", side_effect=Exception("connection refused")):
            result = brain.reason(prompt="what to do?")
        assert result["status"] == "fallback"
        assert "fallback_stub" in result["reasoning"]["provider"]

    def test_returns_ok_on_first_success(self):
        brain = _make_brain()
        fake_result = {
            "provider": "openai",
            "model": "gpt-4",
            "output_text": "do the thing",
            "tool_calls": [],
            "function_calling_used": False,
            "latency_ms": 200,
        }
        with patch.object(brain, "_auto_candidates", return_value=["openai"]), \
             patch.object(brain, "_openai_reason", return_value=fake_result):
            result = brain.reason(prompt="what to do?")
        assert result["status"] == "ok"
        assert result["reasoning"]["output_text"] == "do the thing"

    def test_skips_empty_output(self):
        brain = _make_brain()
        empty_result = {
            "provider": "openai",
            "model": "gpt-4",
            "output_text": "",
            "tool_calls": [],
            "function_calling_used": False,
            "latency_ms": 100,
        }
        with patch.object(brain, "_auto_candidates", return_value=["openai", "llama"]), \
             patch.object(brain, "_openai_reason", return_value=empty_result), \
             patch.object(brain, "_ollama_reason", side_effect=Exception("down")):
            result = brain.reason(prompt="test")
        # openai returned empty, llama failed → fallback
        assert result["status"] == "fallback"

    def test_explicit_provider_used(self):
        brain = _make_brain()
        fake_result = {
            "provider": "anthropic",
            "model": "claude",
            "output_text": "answer",
            "tool_calls": [],
            "function_calling_used": False,
            "latency_ms": 150,
        }
        with patch.object(brain, "_anthropic_reason", return_value=fake_result):
            result = brain.reason(prompt="test", provider="anthropic")
        assert result["reasoning"]["provider"] == "anthropic"

    def test_unknown_provider_falls_through_to_fallback(self):
        brain = _make_brain()
        result = brain.reason(prompt="test", provider="unknown_provider")  # type: ignore[arg-type]
        assert result["status"] == "fallback"

    def test_explicit_mistral_provider_uses_ollama_path(self):
        brain = _make_brain()
        fake_result = {
            "provider": "mistral",
            "model": "mistral",
            "output_text": "mistral answer",
            "tool_calls": [],
            "function_calling_used": False,
            "latency_ms": 75,
        }
        with patch.object(brain, "_ollama_reason", return_value=fake_result) as mock_ollama:
            result = brain.reason(prompt="test", provider="mistral")
        assert result["status"] == "ok"
        assert result["reasoning"]["provider"] == "mistral"
        assert mock_ollama.called
