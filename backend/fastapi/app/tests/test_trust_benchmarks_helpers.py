"""Tests for pure helpers in trust_center.py and benchmarks.py."""
import os

os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from backend.fastapi.app.routers.benchmarks import (
    _build_comparison,
    _build_latest_seg_map,
    _build_metrics_summary,
    _compute_uplift,
    _percentile_band,
)
from backend.fastapi.app.routers.benchmarks import (
    _now_iso as bm_now_iso,
)
from backend.fastapi.app.routers.trust_center import (
    _mem_count_active_chains,
    _mem_count_open_incidents,
    _posture_rating,
)
from backend.fastapi.app.routers.trust_center import (
    _now_iso as tc_now_iso,
)

# ─── trust_center._now_iso ───────────────────────────────────────────────────

class TestTrustCenterNowIso:
    def test_returns_string(self):
        assert isinstance(tc_now_iso(), str)

    def test_contains_t(self):
        assert "T" in tc_now_iso()


# ─── _posture_rating ─────────────────────────────────────────────────────────

class TestPostureRating:
    def test_critical_below_40(self):
        assert _posture_rating(0.0) == "critical"
        assert _posture_rating(39.9) == "critical"

    def test_warning_between_40_and_70(self):
        assert _posture_rating(40.0) == "warning"
        assert _posture_rating(69.9) == "warning"

    def test_healthy_at_or_above_70(self):
        assert _posture_rating(70.0) == "healthy"
        assert _posture_rating(100.0) == "healthy"


# ─── _mem_count_open_incidents ───────────────────────────────────────────────

class TestMemCountOpenIncidents:
    def test_counts_open_incidents(self):
        incidents = [
            {"tenant_id": "t1", "resolved": False, "severity": "low"},
            {"tenant_id": "t1", "resolved": True, "severity": "critical"},
            {"tenant_id": "t1", "resolved": False, "severity": "critical"},
            {"tenant_id": "other", "resolved": False, "severity": "critical"},
        ]
        open_count, crit_count = _mem_count_open_incidents(incidents, "t1")
        assert open_count == 2
        assert crit_count == 1

    def test_empty_list(self):
        open_count, crit_count = _mem_count_open_incidents([], "t1")
        assert open_count == 0
        assert crit_count == 0

    def test_wrong_tenant_excluded(self):
        incidents = [{"tenant_id": "other", "resolved": False, "severity": "critical"}]
        open_count, crit_count = _mem_count_open_incidents(incidents, "t1")
        assert open_count == 0


# ─── _mem_count_active_chains ────────────────────────────────────────────────

class TestMemCountActiveChains:
    def test_counts_active_chains(self):
        chains = [
            {"tenant_id": "t1", "active": True},
            {"tenant_id": "t1", "active": False},
            {"tenant_id": "t1", "active": True},
            {"tenant_id": "other", "active": True},
        ]
        assert _mem_count_active_chains(chains, "t1") == 2

    def test_empty(self):
        assert _mem_count_active_chains([], "t1") == 0


# ─── benchmarks._now_iso ─────────────────────────────────────────────────────

class TestBenchmarksNowIso:
    def test_returns_string(self):
        assert isinstance(bm_now_iso(), str)


# ─── _compute_uplift ─────────────────────────────────────────────────────────

class TestComputeUplift:
    def test_none_baseline_returns_none(self):
        assert _compute_uplift(50.0, None) is None

    def test_zero_baseline_returns_none(self):
        assert _compute_uplift(50.0, 0.0) is None

    def test_positive_uplift(self):
        result = _compute_uplift(110.0, 100.0)
        assert result == 10.0

    def test_negative_uplift(self):
        result = _compute_uplift(90.0, 100.0)
        assert result == -10.0

    def test_same_value_zero_uplift(self):
        result = _compute_uplift(100.0, 100.0)
        assert result == 0.0


# ─── _percentile_band ────────────────────────────────────────────────────────

class TestPercentileBand:
    def test_below_median(self):
        seg = {"p50": 50.0, "p75": 75.0}
        assert _percentile_band(40.0, seg) == "below_median"

    def test_above_median(self):
        seg = {"p50": 50.0, "p75": 75.0}
        assert _percentile_band(60.0, seg) == "above_median"

    def test_top_quartile(self):
        seg = {"p50": 50.0, "p75": 75.0}
        assert _percentile_band(80.0, seg) == "top_quartile"

    def test_at_p50_boundary(self):
        seg = {"p50": 50.0, "p75": 75.0}
        assert _percentile_band(50.0, seg) == "above_median"


# ─── _build_metrics_summary ──────────────────────────────────────────────────

class TestBuildMetricsSummary:
    def test_basic_summary(self):
        benches = [
            {"metric": "ctr", "value": 0.05, "uplift_pct": 10.0},
            {"metric": "ctr", "value": 0.07, "uplift_pct": None},
        ]
        result = _build_metrics_summary(benches)
        assert "ctr" in result
        assert result["ctr"]["avg_value"] == 0.06
        assert result["ctr"]["data_points"] == 2

    def test_empty(self):
        assert _build_metrics_summary([]) == {}

    def test_multiple_metrics(self):
        benches = [
            {"metric": "ctr", "value": 0.05},
            {"metric": "cvr", "value": 0.03},
        ]
        result = _build_metrics_summary(benches)
        assert "ctr" in result
        assert "cvr" in result

    def test_uplift_avg(self):
        benches = [
            {"metric": "ctr", "value": 0.05, "uplift_pct": 10.0},
            {"metric": "ctr", "value": 0.07, "uplift_pct": 20.0},
        ]
        result = _build_metrics_summary(benches)
        assert result["ctr"]["avg_uplift_pct"] == 15.0


# ─── _build_latest_seg_map ───────────────────────────────────────────────────

class TestBuildLatestSegMap:
    def test_returns_dict(self):
        segs = [{"segment": "smb", "metric": "ctr", "p50": 0.05, "created_at": "2024-01-01"}]
        result = _build_latest_seg_map("smb", segs)
        assert "ctr" in result

    def test_all_segment_included(self):
        segs = [{"segment": "all", "metric": "cvr", "p50": 0.03, "created_at": "2024-01-01"}]
        result = _build_latest_seg_map("enterprise", segs)
        assert "cvr" in result

    def test_latest_overwrites_earlier(self):
        segs = [
            {"segment": "smb", "metric": "ctr", "p50": 0.03, "created_at": "2024-01-01"},
            {"segment": "smb", "metric": "ctr", "p50": 0.05, "created_at": "2024-01-15"},
        ]
        result = _build_latest_seg_map("smb", segs)
        assert result["ctr"]["p50"] == 0.05


# ─── _build_comparison ───────────────────────────────────────────────────────

class TestBuildComparison:
    def test_with_matching_segment(self):
        benches = [{"metric": "ctr", "value": 0.08}]
        seg_map = {"ctr": {"p50": 0.05, "p75": 0.07, "p90": 0.10}}
        result = _build_comparison(benches, seg_map)
        assert len(result) == 1
        assert result[0]["metric"] == "ctr"
        assert result[0]["percentile_band"] == "top_quartile"

    def test_no_segment_data(self):
        benches = [{"metric": "ctr", "value": 0.08}]
        result = _build_comparison(benches, {})
        assert result[0]["percentile_band"] == "no_segment_data"

    def test_empty_tenant_benches(self):
        result = _build_comparison([], {"ctr": {"p50": 0.05}})
        assert result == []
