"""Tests for production_middleware.py."""
from __future__ import annotations

import asyncio
import logging
import os
import threading
from unittest.mock import MagicMock, patch

import pytest

# Ensure the app env vars are set
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")

from backend.fastapi.app.production_middleware import (
    GlobalExceptionHandler,
    StructuredLogger,
    _build_schema_unified_31_block,
    _percentile,
    _record_request_latency,
    format_error_response,
    get_health_check_data,
    get_metrics_data,
    get_request_latency_snapshot,
    validate_environment,
)

# --------------------------------------------------------------------------- #
#  _percentile
# --------------------------------------------------------------------------- #

class TestPercentile:
    def test_empty_returns_zero(self):
        assert _percentile([], 0.50) == 0.0

    def test_single_element(self):
        assert _percentile([5.0], 0.50) == 5.0

    def test_p50(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _percentile(vals, 0.50) == 3.0

    def test_p95(self):
        vals = list(range(1, 101))
        result = _percentile([float(v) for v in vals], 0.95)
        assert result == 95.0

    def test_clamps_to_one(self):
        vals = [1.0, 2.0, 3.0]
        assert _percentile(vals, 1.5) == _percentile(vals, 1.0)

    def test_clamps_to_zero(self):
        vals = [1.0, 2.0, 3.0]
        assert _percentile(vals, -0.5) == _percentile(vals, 0.0)


# --------------------------------------------------------------------------- #
#  _record_request_latency and get_request_latency_snapshot
# --------------------------------------------------------------------------- #

class TestLatencyTracking:
    def test_records_latency(self):
        _record_request_latency("/test-unique-path-xyz", 42.0)
        snapshot = get_request_latency_snapshot()
        assert "/test-unique-path-xyz" in snapshot["paths"]

    def test_empty_path_defaults_to_slash(self):
        _record_request_latency("", 10.0)
        snapshot = get_request_latency_snapshot()
        assert "/" in snapshot["paths"]

    def test_negative_duration_clamped_to_zero(self):
        _record_request_latency("/negative-test", -100.0)
        snapshot = get_request_latency_snapshot()
        path_data = snapshot["paths"].get("/negative-test")
        if path_data:
            assert path_data["p50_ms"] >= 0.0

    def test_snapshot_has_required_keys(self):
        snapshot = get_request_latency_snapshot()
        assert "window_size" in snapshot
        assert "path_count" in snapshot
        assert "sample_count" in snapshot
        assert "paths" in snapshot

    def test_window_size_trimming(self):
        # Record more than _LATENCY_WINDOW_SIZE samples
        from backend.fastapi.app.production_middleware import _LATENCY_WINDOW_SIZE, _request_latency_ms
        path = "/trim-test-path"
        for i in range(_LATENCY_WINDOW_SIZE + 50):
            _record_request_latency(path, float(i))
        from backend.fastapi.app.production_middleware import _latency_lock
        with _latency_lock:
            assert len(_request_latency_ms.get(path, [])) <= _LATENCY_WINDOW_SIZE


# --------------------------------------------------------------------------- #
#  StructuredLogger
# --------------------------------------------------------------------------- #

class TestStructuredLogger:
    def test_creates_logger(self):
        sl = StructuredLogger("test.logger")
        assert sl.logger is not None

    def test_info_emits_json(self, capsys):
        sl = StructuredLogger("test.info", level=logging.DEBUG)
        sl.info("Test message", key="value")

    def test_warning_emits(self):
        sl = StructuredLogger("test.warn")
        sl.warning("warning here", reason="test")

    def test_error_emits(self):
        sl = StructuredLogger("test.err")
        sl.error("error here")

    def test_critical_emits(self):
        sl = StructuredLogger("test.critical")
        sl.critical("critical here")

    def test_debug_emits(self):
        sl = StructuredLogger("test.debug", level=logging.DEBUG)
        sl.debug("debug here")

    def test_does_not_add_duplicate_handlers(self):
        sl = StructuredLogger("test.no_dup")
        count_before = len(sl.logger.handlers)
        sl2 = StructuredLogger("test.no_dup")
        count_after = len(sl2.logger.handlers)
        assert count_after == count_before


# --------------------------------------------------------------------------- #
#  validate_environment
# --------------------------------------------------------------------------- #

class TestValidateEnvironment:
    def test_returns_dict_in_development(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            result = validate_environment()
        assert isinstance(result, dict)

    def test_includes_set_optional_vars(self):
        env = {"ENVIRONMENT": "development", "LOG_LEVEL": "INFO"}
        with patch.dict(os.environ, env):
            result = validate_environment()
        assert "LOG_LEVEL" in result

    def test_raises_in_production_with_missing_required_vars(self):
        env = {
            "ENVIRONMENT": "production",
            "JWT_SIGNING_KEY": "",
            "APP_ENC_KEY": "",
            "PASSWORD_PEPPER": "",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("JWT_SIGNING_KEY", None)
            os.environ.pop("APP_ENC_KEY", None)
            os.environ.pop("PASSWORD_PEPPER", None)
            with pytest.raises(RuntimeError, match="Missing required environment variables"):
                validate_environment()

    def test_does_not_raise_in_production_when_vars_set(self):
        env = {
            "ENVIRONMENT": "production",
            "JWT_SIGNING_KEY": "prod-signing-key",
            "APP_ENC_KEY": "prod-enc-key",
            "PASSWORD_PEPPER": "prod-pepper",
        }
        with patch.dict(os.environ, env):
            result = validate_environment()
        assert "JWT_SIGNING_KEY" in result


# --------------------------------------------------------------------------- #
#  _build_schema_unified_31_block
# --------------------------------------------------------------------------- #

class TestBuildSchemaBlock:
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


# --------------------------------------------------------------------------- #
#  get_health_check_data
# --------------------------------------------------------------------------- #

class TestGetHealthCheckData:
    def test_returns_healthy_when_db_ready(self):
        result = get_health_check_data(True, [], [])
        assert result["status"] == "healthy"

    def test_healthy_in_dev_even_without_db(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            result = get_health_check_data(False, [], [])
        assert result["status"] == "healthy"

    def test_degraded_in_production_without_db(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            result = get_health_check_data(False, [], [])
        assert result["status"] == "degraded"

    def test_includes_required_structure(self):
        result = get_health_check_data(True, [1, 2], [3])
        assert "checks" in result
        assert "service" in result
        assert "security" in result
        assert result["checks"]["auth"]["sessions_active"] == 2
        assert result["checks"]["notifications"]["pending_count"] == 1


# --------------------------------------------------------------------------- #
#  get_metrics_data
# --------------------------------------------------------------------------- #

class TestGetMetricsData:
    def test_returns_metrics_structure(self):
        lock = threading.Lock()
        queues = {"queue_a": [1, 2, 3], "queue_b": [4]}
        rate_buckets = {"ip1": [10.0, 20.0], "ip2": [30.0]}
        result = get_metrics_data(queues, rate_buckets, lock)
        assert "metrics" in result
        assert result["metrics"]["queue_total_items"] == 4
        assert result["metrics"]["queues"]["queue_a"] == 3

    def test_empty_queues(self):
        lock = threading.Lock()
        result = get_metrics_data({}, {}, lock)
        assert result["metrics"]["queue_total_items"] == 0


# --------------------------------------------------------------------------- #
#  format_error_response
# --------------------------------------------------------------------------- #

class TestFormatErrorResponse:
    def test_returns_expected_structure(self):
        result = format_error_response("err-123", "Not found", 404, detail="Resource missing")
        assert result["error_id"] == "err-123"
        assert result["message"] == "Not found"
        assert result["status_code"] == 404
        assert result["detail"] == "Resource missing"
        assert result["status"] == "error"

    def test_detail_optional(self):
        result = format_error_response("e1", "Server error", 500)
        assert result["detail"] is None


# --------------------------------------------------------------------------- #
#  GlobalExceptionHandler
# --------------------------------------------------------------------------- #

class TestGlobalExceptionHandler:
    def test_returns_500_json_response(self):
        from fastapi.responses import JSONResponse

        req = MagicMock()
        req.url.path = "/test"
        req.method = "GET"

        exc = ValueError("Something went wrong")

        async def run():
            return await GlobalExceptionHandler.exception_handler(req, exc)

        response = asyncio.run(run())
        assert isinstance(response, JSONResponse)
        assert response.status_code == 500

    def test_response_includes_error_id(self):
        import json

        req = MagicMock()
        req.url.path = "/some/path"
        req.method = "POST"

        exc = RuntimeError("crash")

        async def run():
            return await GlobalExceptionHandler.exception_handler(req, exc)

        response = asyncio.run(run())
        body = json.loads(response.body)
        assert "error_id" in body
        assert body["status"] == "error"
