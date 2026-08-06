"""
Tests for fallback_pressure_refresh_baseline.py and fallback_pressure_trend_check.py
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")


SAMPLE_SNAPSHOT = {
    "fallback_buffers": {
        "max_items_per_buffer": 1000,
        "warning_utilization_threshold": 0.8,
        "sizes": {"scheduled_posts": 5, "email_campaigns": 2},
        "utilization_ratio": {"scheduled_posts": 0.005, "email_campaigns": 0.002},
        "hot_buffers": [],
        "any_buffer_hot": False,
    }
}

SAMPLE_BASELINE = {
    "fallback_buffers": {
        "max_items_per_buffer": 1000,
        "warning_utilization_threshold": 0.8,
        "sizes": {"scheduled_posts": 3, "email_campaigns": 2},
        "utilization_ratio": {"scheduled_posts": 0.003, "email_campaigns": 0.002},
        "hot_buffers": [],
        "any_buffer_hot": False,
    }
}


class TestRefreshBaseline:
    def test_creates_baseline_from_snapshot(self) -> None:
        from backend.fastapi.app.fallback_pressure_refresh_baseline import refresh_baseline

        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = Path(tmpdir) / "snapshot.json"
            out_path = Path(tmpdir) / "baseline.json"
            snap_path.write_text(json.dumps(SAMPLE_SNAPSHOT))

            with patch.dict(os.environ, {
                "FALLBACK_PRESSURE_SNAPSHOT_PATH": str(snap_path),
                "FALLBACK_PRESSURE_BASELINE_OUTPUT_PATH": str(out_path),
            }):
                refresh_baseline()

            assert out_path.exists()
            result = json.loads(out_path.read_text())
            assert "fallback_buffers" in result
            fb = result["fallback_buffers"]
            assert fb["max_items_per_buffer"] == 1000
            assert abs(fb["warning_utilization_threshold"] - 0.8) < 0.001

    def test_missing_snapshot_raises(self) -> None:
        from backend.fastapi.app.fallback_pressure_refresh_baseline import refresh_baseline

        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "nonexistent.json"
            with patch.dict(os.environ, {
                "FALLBACK_PRESSURE_SNAPSHOT_PATH": str(missing_path),
            }):
                with pytest.raises(FileNotFoundError):
                    refresh_baseline()

    def test_missing_fallback_buffers_raises(self) -> None:
        from backend.fastapi.app.fallback_pressure_refresh_baseline import refresh_baseline

        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = Path(tmpdir) / "snapshot.json"
            out_path = Path(tmpdir) / "baseline.json"
            snap_path.write_text(json.dumps({"other_key": "value"}))

            with patch.dict(os.environ, {
                "FALLBACK_PRESSURE_SNAPSHOT_PATH": str(snap_path),
                "FALLBACK_PRESSURE_BASELINE_OUTPUT_PATH": str(out_path),
            }):
                with pytest.raises(ValueError):
                    refresh_baseline()


class TestTrendCheck:
    def test_no_worsening(self) -> None:
        from backend.fastapi.app.fallback_pressure_trend_check import run_trend_check

        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = Path(tmpdir) / "snapshot.json"
            base_path = Path(tmpdir) / "baseline.json"
            report_path = Path(tmpdir) / "report.json"

            snap_path.write_text(json.dumps(SAMPLE_SNAPSHOT))
            base_path.write_text(json.dumps(SAMPLE_BASELINE))

            with patch.dict(os.environ, {
                "FALLBACK_PRESSURE_SNAPSHOT_PATH": str(snap_path),
                "FALLBACK_PRESSURE_BASELINE_PATH": str(base_path),
                "FALLBACK_PRESSURE_TREND_REPORT_PATH": str(report_path),
                "FALLBACK_PRESSURE_TREND_TOLERANCE": "0.05",
            }):
                run_trend_check()

            assert report_path.exists()
            report = json.loads(report_path.read_text())
            assert report["has_trend_warning"] is False
            assert report["worsened_buffers"] == []

    def test_worsening_triggers_warning(self) -> None:
        from backend.fastapi.app.fallback_pressure_trend_check import run_trend_check

        worsened_snapshot = {
            "fallback_buffers": {
                **SAMPLE_SNAPSHOT["fallback_buffers"],
                "utilization_ratio": {
                    "scheduled_posts": 0.5,  # way above baseline of 0.003
                    "email_campaigns": 0.002,
                },
                "hot_buffers": ["scheduled_posts"],
                "any_buffer_hot": True,
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = Path(tmpdir) / "snapshot.json"
            base_path = Path(tmpdir) / "baseline.json"
            report_path = Path(tmpdir) / "report.json"

            snap_path.write_text(json.dumps(worsened_snapshot))
            base_path.write_text(json.dumps(SAMPLE_BASELINE))

            with patch.dict(os.environ, {
                "FALLBACK_PRESSURE_SNAPSHOT_PATH": str(snap_path),
                "FALLBACK_PRESSURE_BASELINE_PATH": str(base_path),
                "FALLBACK_PRESSURE_TREND_REPORT_PATH": str(report_path),
                "FALLBACK_PRESSURE_TREND_TOLERANCE": "0.05",
            }):
                run_trend_check()

            report = json.loads(report_path.read_text())
            assert report["has_trend_warning"] is True
            assert len(report["worsened_buffers"]) > 0

    def test_missing_snapshot_raises(self) -> None:
        from backend.fastapi.app.fallback_pressure_trend_check import run_trend_check

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {
                "FALLBACK_PRESSURE_SNAPSHOT_PATH": str(Path(tmpdir) / "missing.json"),
                "FALLBACK_PRESSURE_BASELINE_PATH": str(Path(tmpdir) / "baseline.json"),
            }):
                with pytest.raises(FileNotFoundError):
                    run_trend_check()

    def test_missing_baseline_raises(self) -> None:
        from backend.fastapi.app.fallback_pressure_trend_check import run_trend_check

        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = Path(tmpdir) / "snapshot.json"
            snap_path.write_text(json.dumps(SAMPLE_SNAPSHOT))

            with patch.dict(os.environ, {
                "FALLBACK_PRESSURE_SNAPSHOT_PATH": str(snap_path),
                "FALLBACK_PRESSURE_BASELINE_PATH": str(Path(tmpdir) / "missing_baseline.json"),
            }):
                with pytest.raises(FileNotFoundError):
                    run_trend_check()

    def test_github_actions_warn_format(self) -> None:
        """Covers the _warn path with GITHUB_ACTIONS=true"""
        from backend.fastapi.app.fallback_pressure_trend_check import run_trend_check

        worsened_snapshot = {
            "fallback_buffers": {
                **SAMPLE_SNAPSHOT["fallback_buffers"],
                "utilization_ratio": {"scheduled_posts": 0.9},
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = Path(tmpdir) / "snapshot.json"
            base_path = Path(tmpdir) / "baseline.json"
            report_path = Path(tmpdir) / "report.json"

            snap_path.write_text(json.dumps(worsened_snapshot))
            base_path.write_text(json.dumps(SAMPLE_BASELINE))

            with patch.dict(os.environ, {
                "FALLBACK_PRESSURE_SNAPSHOT_PATH": str(snap_path),
                "FALLBACK_PRESSURE_BASELINE_PATH": str(base_path),
                "FALLBACK_PRESSURE_TREND_REPORT_PATH": str(report_path),
                "FALLBACK_PRESSURE_TREND_TOLERANCE": "0.05",
                "GITHUB_ACTIONS": "true",
            }):
                run_trend_check()  # Should not raise but print ::warning::

            report = json.loads(report_path.read_text())
            assert report["has_trend_warning"] is True
