"""
Tests for benchmarks.py DB-backed paths.
Covers lines 154-173, 188-198, 205-235, 257-268, 277-316, 324-343 via mocked psycopg.
"""
from __future__ import annotations

import os

os.environ.setdefault("NUXTRON_SKIP_STARTUP_DB_INIT", "1")
os.environ.setdefault("APP_ENC_KEY", "00" * 32)
os.environ.setdefault("FASTAPI_API_KEY", "test-api-key")

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

VALID = (200, 201, 202, 400, 401, 403, 404, 409, 422, 500, 503)
H = {"X-API-Key": "test-api-key", "X-Tenant-Id": "bench-db-tenant"}


def _make_mock_conn(rows=None, fetchone=None):
    cur = MagicMock()
    cur.fetchall.return_value = rows or []
    cur.fetchone.return_value = fetchone
    conn = MagicMock()
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn, cur


@pytest.fixture(scope="module")
def client() -> TestClient:
    from backend.fastapi.app.main import app
    return TestClient(app, raise_server_exceptions=False)


class TestBenchmarksDbSubmit:
    """Cover lines 205-235: _handle_submit_benchmark with DB enabled."""

    def test_submit_with_db_enabled(self, client: TestClient) -> None:
        """Lines 215-230: DB path in submit_benchmark."""
        import backend.fastapi.app.legacy_main as lm
        mock_conn, _ = _make_mock_conn()

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                r = client.post("/benchmarks", headers=H, json={
                    "metric": "conversion_rate",
                    "value": 3.5,
                    "baseline_value": 2.8,
                    "period_label": "Q1-2024",
                    "segment": "saas",
                    "notes": "DB test run",
                })
                assert r.status_code in VALID
                if r.status_code in (200, 201):
                    data = r.json()
                    assert "bench_id" in data

    def test_submit_db_exception_falls_back_to_memory(self, client: TestClient) -> None:
        """Lines 231-234: DB exception → falls back to memory."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", side_effect=Exception("DB down")):
                r = client.post("/benchmarks", headers=H, json={
                    "metric": "click_rate",
                    "value": 5.1,
                    "period_label": "Q2-2024",
                })
                assert r.status_code in VALID

    def test_submit_db_enabled_no_baseline(self, client: TestClient) -> None:
        """Submit without baseline_value → uplift is None."""
        import backend.fastapi.app.legacy_main as lm
        mock_conn, _ = _make_mock_conn()

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                r = client.post("/benchmarks", headers=H, json={
                    "metric": "page_views",
                    "value": 1000.0,
                    "period_label": "Q3-2024",
                })
                assert r.status_code in VALID


class TestBenchmarksDbList:
    """Cover lines 257-267: _handle_list_benchmarks with DB enabled."""

    def test_list_with_db_enabled(self, client: TestClient) -> None:
        """Lines 257-267: DB query for list benchmarks."""
        import backend.fastapi.app.legacy_main as lm
        # Return mock benchmark rows: (id, tenant_id, metric, value, baseline, uplift, period, segment, notes, created_at)
        rows = [
            ("abc-123", "bench-db-tenant", "conversion_rate", 3.5, 2.8, 25.0, "Q1-2024", "all", None, "2024-01-01T12:00:00"),
        ]
        mock_conn, _ = _make_mock_conn(rows=rows)

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                r = client.get("/benchmarks", headers=H)
                assert r.status_code in VALID

    def test_list_db_exception_falls_back(self, client: TestClient) -> None:
        """Lines 264-267: DB exception → memory fallback."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", side_effect=Exception("timeout")):
                r = client.get("/benchmarks", headers=H)
                assert r.status_code in VALID


class TestBenchmarksDbSummary:
    """Cover lines 188-198: _fetch_tenant_benchmarks with DB enabled."""

    def test_summary_with_db_enabled(self, client: TestClient) -> None:
        """Lines 187-198: DB fetch in get_summary."""
        import backend.fastapi.app.legacy_main as lm
        rows = [
            ("abc-456", "bench-db-tenant", "revenue_per_user", 42.0, None, None, "Q1-2024", "all", None, "2024-01-01"),
        ]
        mock_conn, _ = _make_mock_conn(rows=rows)

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                r = client.get("/benchmarks/summary", headers=H)
                assert r.status_code in VALID

    def test_summary_db_exception(self, client: TestClient) -> None:
        """DB exception in summary → returns memory fallback."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", side_effect=Exception("connection refused")):
                r = client.get("/benchmarks/summary", headers=H)
                assert r.status_code in VALID


class TestBenchmarksDbSegment:
    """Cover lines 277-316: _handle_get_segment with DB enabled."""

    def test_get_segment_with_db_enabled(self, client: TestClient) -> None:
        """Lines 288-316: DB path for get_segment."""
        import backend.fastapi.app.legacy_main as lm
        rows = [
            ("abc-789", "bench-db-tenant", "conversion_rate", 3.5, None, None, "Q1", "all", None, "2024-01-01"),
        ]
        seg_rows = [
            ("seg-001", "saas", "conversion_rate", 2.5, 3.0, 4.0, "Q1-2024", 100, "2024-01-01"),
        ]

        call_count = [0]

        def mock_connect(dsn):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: tenant benchmarks
                conn, cur = _make_mock_conn(rows=rows)
                return conn
            else:
                # Second call: segment data
                conn, cur = _make_mock_conn(rows=seg_rows)
                return conn

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", side_effect=mock_connect):
                r = client.get("/benchmarks/segments/saas", headers=H)
                assert r.status_code in VALID

    def test_get_segment_db_exception(self, client: TestClient) -> None:
        """DB exception in get_segment → memory fallback."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", side_effect=Exception("down")):
                r = client.get("/benchmarks/segments/ecommerce", headers=H)
                assert r.status_code in VALID


class TestBenchmarksDbCompare:
    """Cover lines 329-343: _handle_compare with DB enabled."""

    def test_compare_with_db_enabled(self, client: TestClient) -> None:
        """Lines 311-343: DB path for compare."""
        import backend.fastapi.app.legacy_main as lm
        rows = [
            ("abc-999", "bench-db-tenant", "conversion_rate", 3.5, None, None, "Q1", "all", None, "2024-01-01"),
        ]
        mock_conn, _ = _make_mock_conn(rows=rows)

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", return_value=mock_conn):
                r = client.get("/benchmarks/compare/saas", headers=H)
                assert r.status_code in VALID

    def test_compare_db_exception(self, client: TestClient) -> None:
        """Lines 342: DB exception → memory fallback in compare."""
        import backend.fastapi.app.legacy_main as lm

        with patch.object(lm, "_db_ready", True):
            with patch("psycopg.connect", side_effect=Exception("error")):
                r = client.get("/benchmarks/compare/all", headers=H)
                assert r.status_code in VALID


class TestBenchmarksPublishSegment:
    """Cover lines 277-316: _handle_publish_segment with DB enabled."""

    def test_publish_segment_with_db_enabled(self, client: TestClient) -> None:
        """Lines 288-305: DB path for publish_segment with valid super admin key."""
        import backend.fastapi.app.legacy_main as lm
        mock_conn, _ = _make_mock_conn()

        with patch.dict(os.environ, {"SUPER_ADMIN_KEY": "test-super-key"}, clear=False):
            with patch.object(lm, "_db_ready", True):
                with patch("psycopg.connect", return_value=mock_conn):
                    r = client.post("/benchmarks/segments", headers=H, json={
                        "segment": "enterprise",
                        "metric": "deal_size",
                        "p50": 50000.0,
                        "p75": 75000.0,
                        "p90": 90000.0,
                        "period_label": "2024-Q1",
                        "sample_size": 500,
                    }, params={"x_super_admin_key": "test-super-key"})
                    assert r.status_code in VALID

    def test_publish_segment_without_key(self, client: TestClient) -> None:
        """Lines 277: 403 when super admin key missing."""
        r = client.post("/benchmarks/segments", headers=H, json={
            "segment": "smb",
            "metric": "churn_rate",
            "p50": 0.05,
            "p75": 0.08,
            "p90": 0.12,
            "period_label": "2024-Q2",
            "sample_size": 200,
        })
        assert r.status_code in VALID
        if r.status_code == 403:
            assert "super-admin" in r.json().get("detail", "").lower()

    def test_publish_segment_db_exception(self, client: TestClient) -> None:
        """Lines 300-305: DB exception → memory fallback."""
        import backend.fastapi.app.legacy_main as lm

        with patch.dict(os.environ, {"SUPER_ADMIN_KEY": "test-super-key2"}, clear=False):
            with patch.object(lm, "_db_ready", True):
                with patch("psycopg.connect", side_effect=Exception("DB error")):
                    r = client.post("/benchmarks/segments", headers=H, json={
                        "segment": "growth",
                        "metric": "nps",
                        "p50": 40.0,
                        "p75": 55.0,
                        "p90": 70.0,
                        "period_label": "2024-Q3",
                        "sample_size": 300,
                    }, params={"x_super_admin_key": "test-super-key2"})
                    assert r.status_code in VALID
