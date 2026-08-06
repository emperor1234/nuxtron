"""Tests for pure helper functions in production_middleware.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.production_middleware import (
    _build_schema_unified_31_block,
    _percentile,
    _record_request_latency,
    get_health_check_data,
    get_request_latency_snapshot,
)

# ─── _percentile ─────────────────────────────────────────────────────────────

class TestPercentile:
    def test_empty_list_returns_zero(self):
        assert _percentile([], 0.5) == 0.0

    def test_single_element(self):
        assert _percentile([42.0], 0.5) == 42.0
        assert _percentile([42.0], 0.0) == 42.0
        assert _percentile([42.0], 1.0) == 42.0

    def test_p50_median(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = _percentile(values, 0.5)
        assert result == 3.0

    def test_p0_is_min(self):
        values = [5.0, 1.0, 3.0, 2.0, 4.0]
        assert _percentile(values, 0.0) == 1.0

    def test_p1_is_max(self):
        values = [5.0, 1.0, 3.0, 2.0, 4.0]
        assert _percentile(values, 1.0) == 5.0

    def test_clips_percentile_above_1(self):
        values = [1.0, 2.0, 3.0]
        # percentile > 1.0 should still return max
        assert _percentile(values, 1.5) == 3.0

    def test_clips_percentile_below_0(self):
        values = [1.0, 2.0, 3.0]
        assert _percentile(values, -0.1) == 1.0


# ─── _build_schema_unified_31_block ─────────────────────────────────────────

class TestBuildSchemaUnified31Block:
    def test_db_ready_true(self):
        result = _build_schema_unified_31_block(True)
        assert result["db_ready"] is True
        assert result["ready"] is True
        assert result["module_seed_count"] == 31

    def test_db_ready_false(self):
        result = _build_schema_unified_31_block(False)
        assert result["db_ready"] is False
        assert result["ready"] is False
        assert result["module_seed_count"] == 0

    def test_has_required_keys(self):
        result = _build_schema_unified_31_block(True)
        for key in ["schema", "migration", "db_ready", "ready", "module_seed_count"]:
            assert key in result

    def test_returns_dict(self):
        result = _build_schema_unified_31_block(False)
        assert isinstance(result, dict)


# ─── get_health_check_data ────────────────────────────────────────────────────

class TestGetHealthCheckData:
    def test_db_ready_status(self):
        result = get_health_check_data(True, [], [])
        assert result["checks"]["database"]["status"] == "ready"

    def test_db_not_ready_status(self):
        result = get_health_check_data(False, [], [])
        assert result["checks"]["database"]["status"] == "unavailable"

    def test_has_expected_structure(self):
        result = get_health_check_data(True, [], [])
        assert "status" in result
        assert "timestamp" in result
        assert "service" in result
        assert "checks" in result

    def test_healthy_status_db_ready(self):
        result = get_health_check_data(True, [], [])
        assert result["status"] == "healthy"

    def test_auth_sessions_counted(self):
        auth_mem = [{"session": 1}, {"session": 2}]
        result = get_health_check_data(True, auth_mem, [])
        assert result["checks"]["auth"]["sessions_active"] == 2

    def test_notifications_counted(self):
        notif = [{"n": 1}]
        result = get_health_check_data(True, [], notif)
        assert result["checks"]["notifications"]["pending_count"] == 1


# ─── _record_request_latency / get_request_latency_snapshot ──────────────────

class TestRequestLatency:
    def test_recording_and_retrieving(self):
        _record_request_latency("/test-unique-path-abc", 42.5)
        snapshot = get_request_latency_snapshot()
        assert "/test-unique-path-abc" in snapshot["paths"]

    def test_snapshot_has_required_keys(self):
        _record_request_latency("/test-path-for-keys", 10.0)
        snapshot = get_request_latency_snapshot()
        assert "window_size" in snapshot
        assert "path_count" in snapshot
        assert "sample_count" in snapshot

    def test_path_stats_contain_percentiles(self):
        _record_request_latency("/test-path-percentiles", 20.0)
        snapshot = get_request_latency_snapshot()
        path_data = snapshot["paths"].get("/test-path-percentiles")
        if path_data:
            assert "p50_ms" in path_data
            assert "p95_ms" in path_data
            assert "max_ms" in path_data
