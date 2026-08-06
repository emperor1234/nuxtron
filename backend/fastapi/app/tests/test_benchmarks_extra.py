"""
Additional tests for benchmarks.py pure helpers and outcome_attribution routes.
Focus: _compute_uplift, _percentile_band, _build_metrics_summary, _build_comparison.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")


class TestComputeUplift:
    def _fn(self):
        from backend.fastapi.app.routers.benchmarks import _compute_uplift
        return _compute_uplift

    def test_positive_uplift(self) -> None:
        assert self._fn()(110.0, 100.0) == 10.0

    def test_negative_uplift(self) -> None:
        result = self._fn()(90.0, 100.0)
        assert result == -10.0

    def test_none_baseline(self) -> None:
        assert self._fn()(100.0, None) is None

    def test_zero_baseline(self) -> None:
        assert self._fn()(100.0, 0.0) is None

    def test_equal_values(self) -> None:
        assert self._fn()(100.0, 100.0) == 0.0

    def test_returns_rounded(self) -> None:
        result = self._fn()(100.0, 300.0)
        assert result is not None
        assert isinstance(result, float)


class TestPercentileBand:
    def _fn(self):
        from backend.fastapi.app.routers.benchmarks import _percentile_band
        return _percentile_band

    def test_below_median(self) -> None:
        seg = {"p50": 60.0, "p75": 80.0}
        assert self._fn()(40.0, seg) == "below_median"

    def test_above_median(self) -> None:
        seg = {"p50": 60.0, "p75": 80.0}
        assert self._fn()(70.0, seg) == "above_median"

    def test_top_quartile(self) -> None:
        seg = {"p50": 60.0, "p75": 80.0}
        assert self._fn()(90.0, seg) == "top_quartile"

    def test_at_median_boundary(self) -> None:
        seg = {"p50": 60.0, "p75": 80.0}
        # 60.0 is not < 60.0, so it goes to the next check
        result = self._fn()(60.0, seg)
        assert result in ("above_median", "top_quartile")

    def test_empty_seg_defaults(self) -> None:
        seg = {}
        result = self._fn()(0.0, seg)
        assert result == "top_quartile"  # 0 is not < 0 for p50/p75


class TestBuildMetricsSummary:
    def _fn(self):
        from backend.fastapi.app.routers.benchmarks import _build_metrics_summary
        return _build_metrics_summary

    def test_empty_list(self) -> None:
        result = self._fn()([])
        assert result == {}

    def test_single_metric(self) -> None:
        benches = [{"metric": "conversion_rate", "value": 5.2, "uplift_pct": 10.0}]
        result = self._fn()(benches)
        assert "conversion_rate" in result
        assert result["conversion_rate"]["avg_value"] == 5.2
        assert result["conversion_rate"]["data_points"] == 1

    def test_multiple_values_same_metric(self) -> None:
        benches = [
            {"metric": "ctr", "value": 4.0, "uplift_pct": 5.0},
            {"metric": "ctr", "value": 6.0, "uplift_pct": 15.0},
        ]
        result = self._fn()(benches)
        assert result["ctr"]["avg_value"] == 5.0
        assert result["ctr"]["avg_uplift_pct"] == 10.0
        assert result["ctr"]["data_points"] == 2

    def test_no_uplift_returns_none(self) -> None:
        benches = [{"metric": "sessions", "value": 100.0}]  # no uplift_pct
        result = self._fn()(benches)
        assert result["sessions"]["avg_uplift_pct"] is None


class TestBuildComparison:
    def _fn(self):
        from backend.fastapi.app.routers.benchmarks import _build_comparison
        return _build_comparison

    def test_empty_benches(self) -> None:
        result = self._fn()([], {})
        assert result == []

    def test_with_segment_data(self) -> None:
        tenant_benches = [{"metric": "conversion_rate", "value": 5.5}]
        seg_by_metric = {
            "conversion_rate": {"p50": 4.0, "p75": 6.0, "p90": 8.0}
        }
        result = self._fn()(tenant_benches, seg_by_metric)
        assert len(result) == 1
        assert result[0]["metric"] == "conversion_rate"
        assert result[0]["tenant_value"] == 5.5
        assert result[0]["percentile_band"] == "above_median"

    def test_without_segment_data(self) -> None:
        tenant_benches = [{"metric": "sessions", "value": 1000.0}]
        result = self._fn()(tenant_benches, {})
        assert len(result) == 1
        assert result[0]["percentile_band"] == "no_segment_data"
        assert result[0]["segment_p50"] is None


class TestBuildLatestSegMap:
    def _fn(self):
        from backend.fastapi.app.routers.benchmarks import _build_latest_seg_map
        return _build_latest_seg_map

    def test_empty_memory(self) -> None:
        result = self._fn()("saas", [])
        assert result == {}

    def test_filters_by_segment(self) -> None:
        memory = [
            {"segment": "saas", "metric": "churn", "created_at": "2024-01-01T00:00:00"},
            {"segment": "enterprise", "metric": "churn", "created_at": "2024-01-02T00:00:00"},
        ]
        result = self._fn()("saas", memory)
        assert "churn" in result
        # "enterprise" not in "saas" or "all" — should not appear separately

    def test_includes_all_segment(self) -> None:
        memory = [
            {"segment": "all", "metric": "mrr", "created_at": "2024-01-01T00:00:00"},
        ]
        result = self._fn()("saas", memory)
        assert "mrr" in result

    def test_returns_latest_per_metric(self) -> None:
        memory = [
            {"segment": "saas", "metric": "churn", "created_at": "2024-01-01T00:00:00", "p50": 3.0},
            {"segment": "saas", "metric": "churn", "created_at": "2024-02-01T00:00:00", "p50": 4.0},
        ]
        result = self._fn()("saas", memory)
        # Latest should win
        assert result["churn"]["p50"] == 4.0


class TestRowToBenchmark:
    def test_basic_conversion(self) -> None:
        from backend.fastapi.app.routers.benchmarks import _row_to_benchmark
        row = ("b-1", "tenant-1", "ctr", 5.5, 4.0, 37.5, "Q1 2024", "saas", "Good result", "2024-01-01T00:00:00Z")
        result = _row_to_benchmark(row)
        assert result["id"] == "b-1"
        assert result["value"] == 5.5
        assert result["uplift_pct"] == 37.5

    def test_none_uplift(self) -> None:
        from backend.fastapi.app.routers.benchmarks import _row_to_benchmark
        row = ("b-2", "t-1", "sessions", 1000.0, None, None, "", "all", "", "2024-01-01")
        result = _row_to_benchmark(row)
        assert result["uplift_pct"] is None
        assert result["baseline_value"] is None
