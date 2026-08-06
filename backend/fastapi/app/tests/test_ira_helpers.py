"""Tests for pure helper functions in routers/ira.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

import pytest
from backend.fastapi.app.routers.ira import (
    _activate_watchdog_protection,
    _chunk_text,
    _contains_risk_marker,
    _cosine_similarity,
    _event_epoch,
    _lexical_overlap_score,
    _local_hash_embedding,
    _module_available,
    _normalize_brain_provider,
    _normalize_vector,
    _slugify,
    _tokenize_text,
    _watchdog_activation_reason,
    compute_tenant_revenue_snapshot,
    compute_tenant_suspicious_signal,
)

# ─── _event_epoch ────────────────────────────────────────────────────────────

class TestEventEpoch:
    def test_int_passthrough(self):
        assert _event_epoch(1700000000) == 1700000000

    def test_float_truncated(self):
        assert _event_epoch(1700000000.9) == 1700000000

    def test_iso_string(self):
        result = _event_epoch("2024-01-01T00:00:00+00:00")
        assert isinstance(result, int)
        assert result > 0

    def test_iso_string_z_suffix(self):
        result = _event_epoch("2024-01-01T00:00:00Z")
        assert isinstance(result, int)
        assert result > 0

    def test_invalid_string(self):
        assert _event_epoch("not-a-date") == 0

    def test_empty_string(self):
        assert _event_epoch("") == 0

    def test_none(self):
        assert _event_epoch(None) == 0

    def test_list(self):
        assert _event_epoch([]) == 0


# ─── _slugify ────────────────────────────────────────────────────────────────

class TestSlugify:
    def test_basic(self):
        assert _slugify("Hello World", fallback="fallback") == "hello-world"

    def test_special_chars(self):
        assert _slugify("foo & bar!", fallback="fb") == "foo-bar"

    def test_empty_falls_back(self):
        assert _slugify("", fallback="default") == "default"

    def test_only_special_chars(self):
        assert _slugify("!@#$%", fallback="fb") == "fb"

    def test_truncated_at_80_chars(self):
        long_str = "a" * 100
        result = _slugify(long_str, fallback="fb")
        assert len(result) <= 80

    def test_strips_leading_trailing_dashes(self):
        result = _slugify("-hello-", fallback="fb")
        assert not result.startswith("-")
        assert not result.endswith("-")


# ─── _tokenize_text ──────────────────────────────────────────────────────────

class TestTokenizeText:
    def test_basic(self):
        tokens = _tokenize_text("Hello World")
        assert "hello" in tokens
        assert "world" in tokens

    def test_lowercase(self):
        tokens = _tokenize_text("UPPER")
        assert "upper" in tokens

    def test_empty(self):
        assert _tokenize_text("") == []

    def test_ignores_punctuation(self):
        tokens = _tokenize_text("hello, world!")
        assert "hello" in tokens
        assert "world" in tokens


# ─── _normalize_vector ───────────────────────────────────────────────────────

class TestNormalizeVector:
    def test_normalizes(self):
        result = _normalize_vector([3.0, 4.0])
        assert abs(sum(x * x for x in result) - 1.0) < 0.001

    def test_zero_vector_unchanged(self):
        v = [0.0, 0.0, 0.0]
        assert _normalize_vector(v) == v

    def test_single_element(self):
        result = _normalize_vector([5.0])
        assert abs(result[0] - 1.0) < 0.001


# ─── _local_hash_embedding ───────────────────────────────────────────────────

class TestLocalHashEmbedding:
    def test_returns_list(self):
        result = _local_hash_embedding("test query")
        assert isinstance(result, list)

    def test_correct_dimensions(self):
        result = _local_hash_embedding("test", dimensions=128)
        assert len(result) == 128

    def test_deterministic(self):
        r1 = _local_hash_embedding("hello world")
        r2 = _local_hash_embedding("hello world")
        assert r1 == r2

    def test_different_inputs_differ(self):
        r1 = _local_hash_embedding("hello")
        r2 = _local_hash_embedding("world")
        assert r1 != r2

    def test_empty_string(self):
        result = _local_hash_embedding("")
        assert len(result) > 0


# ─── _cosine_similarity ──────────────────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert _cosine_similarity(v, v) == pytest.approx(1.0, abs=1e-5)

    def test_orthogonal_vectors(self):
        assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0, abs=1e-5)

    def test_opposite_vectors(self):
        v = [1.0, 0.0]
        assert _cosine_similarity(v, [-1.0, 0.0]) == pytest.approx(-1.0, abs=1e-5)

    def test_length_mismatch(self):
        assert _cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    def test_empty(self):
        assert _cosine_similarity([], []) == 0.0


# ─── _lexical_overlap_score ──────────────────────────────────────────────────

class TestLexicalOverlapScore:
    def test_full_overlap(self):
        tokens = ["a", "b", "c"]
        assert _lexical_overlap_score(tokens, tokens) == pytest.approx(1.0, abs=1e-5)

    def test_no_overlap(self):
        assert _lexical_overlap_score(["a", "b"], ["c", "d"]) == pytest.approx(0.0, abs=1e-5)

    def test_partial_overlap(self):
        score = _lexical_overlap_score(["a", "b", "c"], ["a", "c", "d"])
        assert 0.0 < score < 1.0

    def test_empty_query(self):
        assert _lexical_overlap_score([], ["a", "b"]) == pytest.approx(0.0, abs=1e-5)

    def test_empty_candidate(self):
        assert _lexical_overlap_score(["a"], []) == pytest.approx(0.0, abs=1e-5)


# ─── _chunk_text ─────────────────────────────────────────────────────────────

class TestChunkText:
    def test_short_text_no_chunking(self):
        result = _chunk_text("hello world", chunk_size=100, chunk_overlap=10)
        assert result == ["hello world"]

    def test_long_text_creates_chunks(self):
        text = "a " * 100
        result = _chunk_text(text.strip(), chunk_size=20, chunk_overlap=5)
        assert len(result) > 1

    def test_chunks_have_max_size(self):
        text = "word " * 50
        result = _chunk_text(text.strip(), chunk_size=30, chunk_overlap=5)
        for chunk in result:
            assert len(chunk) <= 30

    def test_empty_text(self):
        result = _chunk_text("", chunk_size=100, chunk_overlap=10)
        assert result == [""]


# ─── _module_available ───────────────────────────────────────────────────────

class TestModuleAvailable:
    def test_builtin_available(self):
        assert _module_available("os") is True

    def test_missing_module(self):
        assert _module_available("this_module_does_not_exist_xyz") is False

    def test_stdlib_module(self):
        assert _module_available("hashlib") is True


# ─── _normalize_brain_provider ───────────────────────────────────────────────

class TestNormalizeBrainProvider:
    def test_openai(self):
        assert _normalize_brain_provider("openai") == "openai"

    def test_anthropic(self):
        assert _normalize_brain_provider("anthropic") == "anthropic"

    def test_google(self):
        assert _normalize_brain_provider("google_deepmind") == "google_deepmind"

    def test_llama(self):
        assert _normalize_brain_provider("llama") == "llama"

    def test_mistral(self):
        assert _normalize_brain_provider("mistral") == "mistral"

    def test_unknown_returns_auto(self):
        assert _normalize_brain_provider("gpt4") == "auto"

    def test_whitespace_stripped(self):
        assert _normalize_brain_provider("  openai  ") == "openai"

    def test_uppercase(self):
        assert _normalize_brain_provider("OPENAI") == "openai"


# ─── _contains_risk_marker ───────────────────────────────────────────────────

class TestContainsRiskMarker:
    def test_contains_fail(self):
        assert _contains_risk_marker("payment_failed", ("fail", "refund")) is True

    def test_contains_refund(self):
        assert _contains_risk_marker("refund_issued", ("fail", "refund")) is True

    def test_no_match(self):
        assert _contains_risk_marker("payment_success", ("fail", "refund")) is False

    def test_non_string(self):
        assert _contains_risk_marker(None, ("fail",)) is False

    def test_dict_non_string(self):
        assert _contains_risk_marker({"type": "fail"}, ("fail",)) is False

    def test_case_insensitive(self):
        assert _contains_risk_marker("FAILED", ("fail",)) is True


# ─── compute_tenant_revenue_snapshot ─────────────────────────────────────────

class TestComputeTenantRevenueSnapshot:
    def test_basic_revenue(self):
        invoices = [
            {"tenant_id": "t1", "status": "paid", "amount": 100.0},
            {"tenant_id": "t1", "status": "paid", "amount": 50.0},
        ]
        result = compute_tenant_revenue_snapshot(
            tenant_id="t1",
            invoices_memory=invoices,
            credit_ledger_memory=[],
        )
        assert result["revenue"] == 150.0

    def test_excludes_other_tenants(self):
        invoices = [
            {"tenant_id": "t2", "status": "paid", "amount": 200.0},
        ]
        result = compute_tenant_revenue_snapshot(
            tenant_id="t1",
            invoices_memory=invoices,
            credit_ledger_memory=[],
        )
        assert result["revenue"] == 0.0

    def test_excludes_unpaid(self):
        invoices = [
            {"tenant_id": "t1", "status": "pending", "amount": 100.0},
        ]
        result = compute_tenant_revenue_snapshot(
            tenant_id="t1",
            invoices_memory=invoices,
            credit_ledger_memory=[],
        )
        assert result["revenue"] == 0.0

    def test_credits_cost(self):
        result = compute_tenant_revenue_snapshot(
            tenant_id="t1",
            invoices_memory=[],
            credit_ledger_memory=[{"tenant_id": "t1", "amount": 1000}],
        )
        assert result["credits_cost"] == pytest.approx(2.0, abs=0.01)

    def test_zero_revenue_zero_margin(self):
        result = compute_tenant_revenue_snapshot(
            tenant_id="t1",
            invoices_memory=[],
            credit_ledger_memory=[],
        )
        assert result["profit_margin_pct"] == 0.0

    def test_settled_status_counted(self):
        invoices = [{"tenant_id": "t1", "status": "settled", "amount": 75.0}]
        result = compute_tenant_revenue_snapshot(
            tenant_id="t1",
            invoices_memory=invoices,
            credit_ledger_memory=[],
        )
        assert result["revenue"] == 75.0


# ─── compute_tenant_suspicious_signal ────────────────────────────────────────

class TestComputeTenantSuspiciousSignal:
    def _call(self, **kwargs):
        defaults = {
            "tenant_id": "t1",
            "stripe_events_memory": [],
            "revenue_conversions_memory": [],
            "api_usage_audit_memory": [],
            "ai_security_usage_memory": [],
        }
        defaults.update(kwargs)
        return compute_tenant_suspicious_signal(**defaults)

    def test_empty_returns_zero_score(self):
        result = self._call()
        assert result["score"] == 0.0

    def test_returns_expected_keys(self):
        result = self._call()
        assert "score" in result
        assert "components" in result
        assert "metrics" in result
        assert "reasons" in result

    def test_api_burst_score_increases_with_usage(self):
        import time
        now = int(time.time())
        # Add many recent API calls
        api_calls = [{"tenant_id": "t1", "timestamp": now} for _ in range(300)]
        result = self._call(api_usage_audit_memory=api_calls)
        assert result["components"]["api_burst_score"] > 0

    def test_payment_failure_adds_reason(self):
        import time
        now = int(time.time())
        events = [{"tenant_id": "t1", "event_type": "payment_failed", "created_at": now}]
        result = self._call(stripe_events_memory=events)
        assert "payment_failure_ratio_high" in result["reasons"]

    def test_excludes_other_tenant_data(self):
        import time
        now = int(time.time())
        api_calls = [{"tenant_id": "t2", "timestamp": now} for _ in range(300)]
        result = self._call(tenant_id="t1", api_usage_audit_memory=api_calls)
        assert result["metrics"]["api_requests_window"] == 0


# ─── _watchdog_activation_reason ─────────────────────────────────────────────

class TestWatchdogActivationReason:
    def test_below_margin_triggers(self):
        control = {"min_profit_margin_pct": 70.0, "suspicious_signal_threshold": 0.75}
        snapshot = {"profit_margin_pct": 50.0}
        signal = {"score": 0.1}
        result = _watchdog_activation_reason(control, snapshot, signal)
        assert result == "profit_below_target"

    def test_suspicious_signal_triggers(self):
        control = {"min_profit_margin_pct": 0.0, "suspicious_signal_threshold": 0.75}
        snapshot = {"profit_margin_pct": 100.0}
        signal = {"score": 0.9}
        result = _watchdog_activation_reason(control, snapshot, signal)
        assert result == "suspicious_signal"

    def test_healthy_returns_none(self):
        control = {"min_profit_margin_pct": 50.0, "suspicious_signal_threshold": 0.75}
        snapshot = {"profit_margin_pct": 80.0}
        signal = {"score": 0.1}
        result = _watchdog_activation_reason(control, snapshot, signal)
        assert result is None


# ─── _activate_watchdog_protection ───────────────────────────────────────────

class TestActivateWatchdogProtection:
    def test_sets_protection_mode(self):
        control = {}
        audit_log = []
        events = []
        _activate_watchdog_protection(
            tenant_id="t1",
            control=control,
            snapshot={"profit_margin_pct": 30.0},
            suspicious_signal={"score": 0.9},
            reason="profit_below_target",
            ira_events_memory=events,
            audit_log_memory=audit_log,
        )
        assert control["protection_mode"] is True

    def test_appends_audit_log(self):
        control = {}
        audit_log = []
        events = []
        _activate_watchdog_protection(
            tenant_id="t1",
            control=control,
            snapshot={"profit_margin_pct": 30.0},
            suspicious_signal={"score": 0.9},
            reason="profit_below_target",
            ira_events_memory=events,
            audit_log_memory=audit_log,
        )
        assert len(audit_log) == 1
        assert audit_log[0]["action"] == "ira_watchdog_protection_mode_activated"

    def test_appends_ira_event(self):
        control = {}
        audit_log = []
        events = []
        _activate_watchdog_protection(
            tenant_id="t1",
            control=control,
            snapshot={"profit_margin_pct": 30.0},
            suspicious_signal={"score": 0.9},
            reason="profit_below_target",
            ira_events_memory=events,
            audit_log_memory=audit_log,
        )
        assert len(events) == 1
        assert events[0]["event_type"] == "watchdog_protection_mode_activated"

    def test_sets_blocked_actions(self):
        control = {}
        _activate_watchdog_protection(
            tenant_id="t1",
            control=control,
            snapshot={"profit_margin_pct": 30.0},
            suspicious_signal={"score": 0.9},
            reason="suspicious_signal",
            ira_events_memory=[],
            audit_log_memory=[],
        )
        assert "blocked_actions" in control
        assert isinstance(control["blocked_actions"], list)
