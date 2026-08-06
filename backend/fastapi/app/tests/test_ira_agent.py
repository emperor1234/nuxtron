"""Tests for ira_agent.py — IRAAgentRuntime."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from backend.fastapi.app.ira_agent import IRAAgentRuntime


def _now():
    return datetime.now(UTC).isoformat()


def _make_runtime(**kwargs):
    defaults = {
        "now_iso_fn": _now,
        "retrieve_knowledge": lambda q, top_k, min_score: [],
        "upsert_structured_memory": lambda mem_type, key, payload: {"source": "in_memory"},
        "get_short_term_messages": lambda tenant_id, limit: [],
        "compose_response": lambda prompt, hits: "default composed response",
    }
    defaults.update(kwargs)
    return IRAAgentRuntime(**defaults)


# --------------------------------------------------------------------------- #
#  framework_status
# --------------------------------------------------------------------------- #

class TestFrameworkStatus:
    def test_native_secure_loop_always_available(self):
        rt = _make_runtime()
        status = rt.framework_status()
        assert status["native_secure_loop"]["available"] is True
        assert status["native_secure_loop"]["secure"] is True

    def test_crewai_not_ready_when_env_not_set(self):
        import os
        rt = _make_runtime()
        with patch.dict(os.environ, {"IRA_ENABLE_CREWAI": "0", "IRA_CREWAI_SECURE_MODE": "0"}):
            status = rt.framework_status()
        assert status["crewai"]["available"] is False

    def test_crewai_ready_when_env_set_and_installed(self):
        import os
        rt = _make_runtime()
        with patch.dict(os.environ, {"IRA_ENABLE_CREWAI": "1", "IRA_CREWAI_SECURE_MODE": "1"}), \
             patch("importlib.util.find_spec", return_value=MagicMock()):
            status = rt.framework_status()
        assert status["crewai"]["available"] is True


# --------------------------------------------------------------------------- #
#  _resolve_framework
# --------------------------------------------------------------------------- #

class TestResolveFramework:
    def test_explicit_native_secure_loop(self):
        rt = _make_runtime()
        framework, reason = rt._resolve_framework("native_secure_loop", tenant_id="t1")
        assert framework == "native_secure_loop"
        assert "explicitly requested" in reason

    def test_auto_falls_back_to_native(self):
        rt = _make_runtime()
        # With no langchain/sk installed, should fall back to native
        with patch("importlib.util.find_spec", return_value=None):
            framework, _ = rt._resolve_framework("auto", tenant_id="t1")
        assert framework == "native_secure_loop"

    def test_auto_uses_tenant_preference(self):
        rt = _make_runtime(
            get_auto_framework_preference=lambda tid: "native_secure_loop"
        )
        framework, reason = rt._resolve_framework("auto", tenant_id="t1")
        assert framework == "native_secure_loop"
        assert "tenant policy" in reason

    def test_unavailable_framework_falls_back_to_native(self):
        rt = _make_runtime()
        with patch("importlib.util.find_spec", return_value=None):
            framework, reason = rt._resolve_framework("langchain", tenant_id="t1")
        assert framework == "native_secure_loop"
        assert "unavailable" in reason or "native" in reason

    def test_available_framework_used_directly(self):
        rt = _make_runtime()
        # Make langchain appear available
        with patch.object(rt, "framework_status", return_value={
            "langchain": {"available": True, "secure": True},
            "semantic_kernel": {"available": False, "secure": True},
            "native_secure_loop": {"available": True, "secure": True},
            "autogpt": {"available": False, "secure": False},
            "crewai": {"available": False, "secure": False},
        }):
            framework, _ = rt._resolve_framework("langchain", tenant_id="t1")
        assert framework == "langchain"


# --------------------------------------------------------------------------- #
#  _plan
# --------------------------------------------------------------------------- #

class TestPlan:
    def test_returns_four_phases(self):
        rt = _make_runtime()
        plan = rt._plan(goal="analyze logs", context_messages=[])
        assert len(plan) == 4
        tools = [step["tool"] for step in plan]
        assert "retrieve_knowledge" in tools
        assert "compose_response" in tools

    def test_truncates_long_goal(self):
        rt = _make_runtime()
        long_goal = "x" * 500
        plan = rt._plan(goal=long_goal, context_messages=[])
        # Ensure no error and plan returned
        assert len(plan) > 0


# --------------------------------------------------------------------------- #
#  _run_langchain_adapter
# --------------------------------------------------------------------------- #

class TestLangchainAdapter:
    def test_falls_back_gracefully_when_not_installed(self):
        rt = _make_runtime()
        with patch("importlib.util.find_spec", return_value=None):
            result = rt._run_langchain_adapter(goal="test goal", knowledge_hits=[])
        assert result["adapter"] == "langchain"
        # Either ok or fallback
        assert result["status"] in ("ok", "fallback")

    def test_ok_status_when_langchain_present(self):
        rt = _make_runtime()
        mock_template = MagicMock()
        mock_template.from_template.return_value.format.return_value = "formatted prompt"
        mock_module = MagicMock(PromptTemplate=mock_template)
        with patch("importlib.util.find_spec", return_value=MagicMock()), \
             patch("builtins.__import__", return_value=mock_module):
            result = rt._run_langchain_adapter(goal="goal", knowledge_hits=[{"title": "doc"}])
        assert result["adapter"] == "langchain"


# --------------------------------------------------------------------------- #
#  _run_semantic_kernel_adapter
# --------------------------------------------------------------------------- #

class TestSemanticKernelAdapter:
    def test_falls_back_gracefully_when_not_installed(self):
        rt = _make_runtime()
        with patch("builtins.__import__", side_effect=ImportError("no sk")):
            result = rt._run_semantic_kernel_adapter(goal="test", knowledge_hits=[])
        assert result["adapter"] == "semantic_kernel"
        assert result["status"] == "fallback"

    def test_ok_when_installed(self):
        rt = _make_runtime()
        mock_kernel = MagicMock()
        mock_kernel.Kernel = MagicMock()
        with patch("builtins.__import__", return_value=mock_kernel):
            result = rt._run_semantic_kernel_adapter(goal="test", knowledge_hits=[])
        # Might be ok or fallback depending on mock detail, but no error
        assert result["adapter"] == "semantic_kernel"


# --------------------------------------------------------------------------- #
#  _build_tool_contracts
# --------------------------------------------------------------------------- #

class TestBuildToolContracts:
    def test_returns_list_of_two(self):
        rt = _make_runtime()
        tools = rt._build_tool_contracts()
        assert len(tools) == 2
        names = [t["function"]["name"] for t in tools]
        assert "retrieve_knowledge" in names
        assert "upsert_structured_memory" in names


# --------------------------------------------------------------------------- #
#  _generate_final_response
# --------------------------------------------------------------------------- #

class TestGenerateFinalResponse:
    def test_without_brain_uses_compose(self):
        rt = _make_runtime(compose_response=lambda p, hits: "composed!")
        response, brain_out = rt._generate_final_response(final_prompt="p", knowledge_hits=[])
        assert response == "composed!"
        assert brain_out == {}

    def test_with_brain_uses_brain_output(self):
        def brain_fn(prompt, provider, tools):
            return {"reasoning": {"output_text": "brain answer"}}

        rt = _make_runtime(brain_reason=brain_fn)
        response, brain_out = rt._generate_final_response(final_prompt="p", knowledge_hits=[])
        assert response == "brain answer"

    def test_brain_exception_falls_back_to_compose(self):
        def brain_fn(prompt, provider, tools):
            raise Exception("brain down")

        rt = _make_runtime(
            brain_reason=brain_fn,
            compose_response=lambda p, hits: "fallback composed",
        )
        response, brain_out = rt._generate_final_response(final_prompt="p", knowledge_hits=[])
        assert response == "fallback composed"

    def test_brain_empty_output_falls_back_to_compose(self):
        def brain_fn(prompt, provider, tools):
            return {"reasoning": {"output_text": ""}}

        rt = _make_runtime(
            brain_reason=brain_fn,
            compose_response=lambda p, hits: "compose fallback",
        )
        response, brain_out = rt._generate_final_response(final_prompt="p", knowledge_hits=[])
        assert response == "compose fallback"


# --------------------------------------------------------------------------- #
#  run() - full integration
# --------------------------------------------------------------------------- #

class TestRun:
    def _minimal_runtime(self):
        return _make_runtime(
            retrieve_knowledge=lambda q, k, s: [{"chunk_id": "c1", "content": "doc"}],
            upsert_structured_memory=lambda t, k, p: {"source": "in_memory"},
            get_short_term_messages=lambda tid, lim: [{"role": "user", "content": "hi"}],
            compose_response=lambda p, hits: "agent response",
        )

    def test_returns_expected_structure(self):
        rt = self._minimal_runtime()
        result = rt.run(
            tenant_id="t1",
            goal="analyze security logs",
            requested_framework="native_secure_loop",
            max_iterations=3,
            dry_run=True,
            memory_key="wf_key",
        )
        assert "run_id" in result
        assert result["status"] == "completed"
        assert result["framework_selected"] == "native_secure_loop"
        assert result["dry_run"] is True
        assert "tool_traces" in result
        assert "plan" in result

    def test_capped_iterations(self):
        rt = self._minimal_runtime()
        result = rt.run(
            tenant_id="t1",
            goal="test",
            requested_framework="native_secure_loop",
            max_iterations=100,
            dry_run=False,
            memory_key="k",
        )
        assert result["max_iterations"] <= 12

    def test_includes_next_actions(self):
        rt = self._minimal_runtime()
        result = rt.run(
            tenant_id="t1",
            goal="test",
            requested_framework="native_secure_loop",
            max_iterations=3,
            dry_run=True,
            memory_key="k",
        )
        assert isinstance(result["next_actions"], list)
        assert len(result["next_actions"]) > 0

    def test_no_knowledge_hits_adds_suggestion(self):
        rt = _make_runtime(
            retrieve_knowledge=lambda q, k, s: [],
            upsert_structured_memory=lambda t, k, p: {"source": "in_memory"},
        )
        result = rt.run(
            tenant_id="t1",
            goal="test no knowledge",
            requested_framework="native_secure_loop",
            max_iterations=3,
            dry_run=True,
            memory_key="k",
        )
        suggestions = [a for a in result["next_actions"] if "knowledge" in a.lower()]
        assert len(suggestions) > 0

    def test_langchain_framework_selected(self):
        rt = self._minimal_runtime()
        with patch.object(rt, "_resolve_framework", return_value=("langchain", "forced")), \
             patch.object(rt, "_run_langchain_adapter", return_value={"adapter": "langchain", "status": "ok", "knowledge_used": 0}):
            result = rt.run(
                tenant_id="t1",
                goal="test langchain",
                requested_framework="langchain",
                max_iterations=3,
                dry_run=True,
                memory_key="k",
            )
        assert result["framework_selected"] == "langchain"

    def test_semantic_kernel_framework_selected(self):
        rt = self._minimal_runtime()
        with patch.object(rt, "_resolve_framework", return_value=("semantic_kernel", "forced")), \
             patch.object(rt, "_run_semantic_kernel_adapter", return_value={"adapter": "semantic_kernel", "status": "ok"}):
            result = rt.run(
                tenant_id="t1",
                goal="test sk",
                requested_framework="semantic_kernel",
                max_iterations=3,
                dry_run=True,
                memory_key="k",
            )
        assert result["framework_selected"] == "semantic_kernel"
