# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportUnusedFunction=false

"""
Performance Benchmarks — Flywheel Module 4.
Tenant-level and segment-level uplift benchmarks.
DB-first (psycopg3) with in-memory fallback.
"""

import hmac
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import AuthContext, require_auth

AuthDep = Annotated[AuthContext, Depends(require_auth)]

_METRIC_TYPES: frozenset[str] = frozenset({
    'activation_rate_pct', 'churn_reduction_pct',
    'dispute_auto_resolution_rate_pct', 'revenue_per_recommendation_gbp',
    'qualified_lead_rate_pct', 'organic_reach_uplift_pct',
    'response_time_minutes', 'attribution_coverage_pct',
    'outreach_conversion_pct', 'avg_decision_quality_score',
    'net_revenue_retained_gbp', 'autonomous_workflow_coverage_pct',
})

_SEGMENTS: frozenset[str] = frozenset({
    'ecommerce', 'saas', 'agency', 'media', 'fintech',
    'healthtech', 'nonprofit', 'education', 'marketplace', 'all',
})


@dataclass(frozen=True)
class BenchmarksContext:
    enforce_rate_limit: Any
    benchmarks_memory: list[dict[str, Any]]
    segment_benchmarks_memory: list[dict[str, Any]]
    audit_log_memory: list[dict[str, Any]]
    get_db_ready: Callable[[], bool] = field(default=lambda: False)
    db_dsn: Callable[[], str] = field(default=lambda: "")


class SubmitBenchmarkRequest(BaseModel):
    metric: str = Field(min_length=1, max_length=120)
    value: float
    period_label: str = Field(min_length=1, max_length=80)
    segment: str = Field(default='all', min_length=1, max_length=80)
    notes: str = Field(default='', max_length=500)
    baseline_value: float | None = None


class SegmentBenchmarkRequest(BaseModel):
    segment: Literal[
        'ecommerce', 'saas', 'agency', 'media', 'fintech',
        'healthtech', 'nonprofit', 'education', 'marketplace', 'all',
    ]
    metric: str = Field(min_length=1, max_length=120)
    p50: float
    p75: float
    p90: float
    period_label: str = Field(min_length=1, max_length=80)
    sample_size: int = Field(ge=1)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _compute_uplift(value: float, baseline: float | None) -> float | None:
    if baseline is None or abs(baseline) < 1e-9:
        return None
    return round(((value - baseline) / abs(baseline)) * 100.0, 2)


def _percentile_band(tenant_value: float, seg: dict[str, Any]) -> str:
    p50 = float(seg.get('p50', 0.0) or 0.0)
    p75 = float(seg.get('p75', 0.0) or 0.0)
    if tenant_value < p50:
        return 'below_median'
    if tenant_value < p75:
        return 'above_median'
    return 'top_quartile'


def _build_metrics_summary(tenant_benches: list[dict[str, Any]]) -> dict[str, Any]:
    by_metric: dict[str, list[float]] = {}
    by_metric_uplift: dict[str, list[float]] = {}
    for b in tenant_benches:
        key = str(b.get('metric', ''))
        val = float(b.get('value', 0.0) or 0.0)
        by_metric.setdefault(key, []).append(val)
        uplift = b.get('uplift_pct')
        if uplift is not None:
            by_metric_uplift.setdefault(key, []).append(float(uplift))
    result: dict[str, Any] = {}
    for metric, values in by_metric.items():
        avg_val = round(sum(values) / len(values), 2)
        uplifts = by_metric_uplift.get(metric, [])
        avg_uplift: float | None = round(sum(uplifts) / len(uplifts), 2) if uplifts else None
        result[metric] = {'avg_value': avg_val, 'avg_uplift_pct': avg_uplift, 'data_points': len(values)}
    return result


def _build_latest_seg_map(
    segment: str,
    segment_benches_memory: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    segs = [s for s in segment_benches_memory if s.get('segment') in {segment, 'all'}]
    latest: dict[str, dict[str, Any]] = {}
    for s in sorted(segs, key=lambda s: str(s.get('created_at', ''))):
        latest[str(s.get('metric', ''))] = s
    return latest


def _build_comparison(
    tenant_benches: list[dict[str, Any]],
    seg_by_metric: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    tenant_latest: dict[str, float] = {}
    for b in tenant_benches:
        tenant_latest[str(b.get('metric', ''))] = float(b.get('value', 0.0) or 0.0)
    comparison: list[dict[str, Any]] = []
    for metric, tenant_value in tenant_latest.items():
        seg = seg_by_metric.get(metric)
        if seg:
            comparison.append({
                'metric': metric,
                'tenant_value': tenant_value,
                'segment_p50': float(seg.get('p50', 0.0) or 0.0),
                'segment_p75': float(seg.get('p75', 0.0) or 0.0),
                'segment_p90': float(seg.get('p90', 0.0) or 0.0),
                'percentile_band': _percentile_band(tenant_value, seg),
            })
        else:
            comparison.append({
                'metric': metric,
                'tenant_value': tenant_value,
                'segment_p50': None, 'segment_p75': None, 'segment_p90': None,
                'percentile_band': 'no_segment_data',
            })
    return comparison


def _db_latest_seg_map(
    ctx: BenchmarksContext, segment: str
) -> dict[str, dict[str, Any]]:
    with psycopg.connect(ctx.db_dsn()) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT DISTINCT ON (metric) id,segment,metric,p50,p75,p90,period_label,sample_size,created_at
                FROM segment_benchmarks WHERE segment=ANY(%s::text[])
                ORDER BY metric, created_at DESC
                """,
            ([segment, 'all'],),
        )
        rows = cur.fetchall()
    result: dict[str, dict[str, Any]] = {}
    for r in rows:
        result[str(r[2])] = {
            'id': str(r[0]), 'segment': str(r[1]), 'metric': str(r[2]),
            'p50': float(r[3] or 0), 'p75': float(r[4] or 0), 'p90': float(r[5] or 0),
            'period_label': str(r[6] or ''),
            'sample_size': int(r[7] or 0),
            'created_at': r[8].isoformat() if hasattr(r[8], 'isoformat') else str(r[8]),
        }
    return result

def _row_to_benchmark(r: Any) -> dict[str, Any]:
    return {
        'id': str(r[0]), 'tenant_id': str(r[1]), 'metric': str(r[2]),
        'value': float(r[3] or 0), 'baseline_value': r[4],
        'uplift_pct': float(r[5]) if r[5] is not None else None,
        'period_label': str(r[6] or ''), 'segment': str(r[7] or 'all'),
        'notes': str(r[8] or ''),
        'created_at': r[9].isoformat() if hasattr(r[9], 'isoformat') else str(r[9]),
    }


def _fetch_tenant_benchmarks(ctx: BenchmarksContext, tenant_id: str) -> list[dict[str, Any]]:
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT id,tenant_id,metric,value,baseline_value,uplift_pct,period_label,segment,notes,created_at FROM benchmarks WHERE tenant_id=%s',
                        (tenant_id,),
                    )
                    rows = cur.fetchall()
            return [_row_to_benchmark(r) for r in rows]
        except Exception:
            pass
    return [b for b in ctx.benchmarks_memory if b.get('tenant_id') == tenant_id]


# ── Route handler helpers ─────────────────────────────────────────────────────

def _handle_submit_benchmark(ctx: BenchmarksContext, body: SubmitBenchmarkRequest, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:benchmarks_submit', 120, 60)
    bench_id = str(uuid.uuid4())
    uplift = _compute_uplift(body.value, body.baseline_value)
    record: dict[str, Any] = {
        'id': bench_id, 'tenant_id': auth.tenant_id,
        'metric': body.metric, 'value': body.value,
        'baseline_value': body.baseline_value, 'uplift_pct': uplift,
        'period_label': body.period_label, 'segment': body.segment,
        'notes': body.notes, 'created_at': _now_iso(),
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        '''
                        INSERT INTO benchmarks
                            (id,tenant_id,metric,value,baseline_value,uplift_pct,
                             period_label,segment,notes,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING
                        ''',
                        (bench_id, auth.tenant_id, body.metric, body.value,
                         body.baseline_value, uplift,
                         body.period_label, body.segment, body.notes, record['created_at']),
                    )
                conn.commit()
        except Exception:
            ctx.benchmarks_memory.append(record)
    else:
        ctx.benchmarks_memory.append(record)
    ctx.audit_log_memory.append({
        'id': str(uuid.uuid4()), 'tenant_id': auth.tenant_id,
        'event': 'benchmark.submitted', 'bench_id': bench_id,
        'metric': body.metric, 'created_at': _now_iso(),
    })
    return {'bench_id': bench_id, 'uplift_pct': uplift, 'status': 'recorded'}


def _handle_get_summary(ctx: BenchmarksContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:benchmarks_summary', 120, 60)
    tenant_benches = _fetch_tenant_benchmarks(ctx, auth.tenant_id)
    return {
        'tenant_id': auth.tenant_id,
        'metrics': _build_metrics_summary(tenant_benches),
        'total_data_points': len(tenant_benches),
        'retrieved_at': _now_iso(),
    }


def _handle_list_benchmarks(ctx: BenchmarksContext, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:benchmarks_list', 120, 60)
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT id,tenant_id,metric,value,baseline_value,uplift_pct,period_label,segment,notes,created_at FROM benchmarks WHERE tenant_id=%s ORDER BY created_at DESC LIMIT 200',
                        (auth.tenant_id,),
                    )
                    rows = cur.fetchall()
            tenant_benches = [_row_to_benchmark(r) for r in rows]
            return {'benchmarks': tenant_benches, 'total': len(tenant_benches)}
        except Exception:
            pass
    tenant_benches = sorted(
        [b for b in ctx.benchmarks_memory if b.get('tenant_id') == auth.tenant_id],
        key=lambda b: str(b.get('created_at', '')), reverse=True,
    )
    return {'benchmarks': tenant_benches[:200], 'total': len(tenant_benches)}


def _handle_publish_segment(ctx: BenchmarksContext, body: SegmentBenchmarkRequest, auth: AuthContext, x_super_admin_key: str) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:benchmarks_publish_segment', 120, 60)
    expected_key = os.environ.get('SUPER_ADMIN_KEY', '')
    if not expected_key or not hmac.compare_digest(x_super_admin_key, expected_key):
        raise HTTPException(status_code=403, detail='Super-admin key required to publish segment benchmarks')
    seg_id = str(uuid.uuid4())
    seg_record: dict[str, Any] = {
        'id': seg_id, 'segment': body.segment, 'metric': body.metric,
        'p50': body.p50, 'p75': body.p75, 'p90': body.p90,
        'period_label': body.period_label, 'sample_size': body.sample_size,
        'published_by_tenant': auth.tenant_id, 'created_at': _now_iso(),
    }
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        '''
                        INSERT INTO segment_benchmarks
                            (id,segment,metric,p50,p75,p90,period_label,sample_size,published_by_tenant,created_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING
                        ''',
                        (seg_id, body.segment, body.metric, body.p50, body.p75, body.p90,
                         body.period_label, body.sample_size, auth.tenant_id, seg_record['created_at']),
                    )
                conn.commit()
        except Exception:
            ctx.segment_benchmarks_memory.append(seg_record)
    else:
        ctx.segment_benchmarks_memory.append(seg_record)
    return {'seg_id': seg_id, 'status': 'published'}


def _handle_get_segment(ctx: BenchmarksContext, segment: str, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:benchmarks_get_segment', 120, 60)
    if ctx.get_db_ready():
        try:
            latest_by_metric = _db_latest_seg_map(ctx, segment)
            if not latest_by_metric:
                raise HTTPException(status_code=404, detail='No benchmark data for this segment yet')
            return {'segment': segment, 'benchmarks': list(latest_by_metric.values()), 'retrieved_at': _now_iso()}
        except HTTPException:
            raise
        except Exception:
            pass
    latest_by_metric = _build_latest_seg_map(segment, ctx.segment_benchmarks_memory)
    if not latest_by_metric:
        raise HTTPException(status_code=404, detail='No benchmark data for this segment yet')
    return {'segment': segment, 'benchmarks': list(latest_by_metric.values()), 'retrieved_at': _now_iso()}


def _handle_compare(ctx: BenchmarksContext, segment: str, auth: AuthContext) -> dict[str, Any]:
    ctx.enforce_rate_limit(f'{auth.tenant_id}:benchmarks_compare', 120, 60)
    if ctx.get_db_ready():
        try:
            with psycopg.connect(ctx.db_dsn()) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'SELECT id,tenant_id,metric,value,baseline_value,uplift_pct,period_label,segment,notes,created_at FROM benchmarks WHERE tenant_id=%s',
                        (auth.tenant_id,),
                    )
                    rows = cur.fetchall()
            tenant_benches: list[dict[str, Any]] = [{'metric': str(r[2]), 'value': float(r[3] or 0)} for r in rows]
            seg_by_metric = _db_latest_seg_map(ctx, segment)
            comparison = _build_comparison(tenant_benches, seg_by_metric)
            return {'tenant_id': auth.tenant_id, 'segment': segment, 'comparison': comparison, 'retrieved_at': _now_iso()}
        except Exception:
            pass
    tenant_benches = [b for b in ctx.benchmarks_memory if b.get('tenant_id') == auth.tenant_id]
    seg_by_metric = _build_latest_seg_map(segment, ctx.segment_benchmarks_memory)
    comparison = _build_comparison(tenant_benches, seg_by_metric)
    return {'tenant_id': auth.tenant_id, 'segment': segment, 'comparison': comparison, 'retrieved_at': _now_iso()}


# ── Router factory (thin wrappers only) ───────────────────────────────────────

def create_benchmarks_router(ctx: BenchmarksContext) -> APIRouter:
    router = APIRouter(prefix='/benchmarks', tags=['Performance Benchmarks'])

    @router.post('', status_code=201)
    def submit_benchmark(body: SubmitBenchmarkRequest, auth: AuthDep) -> dict[str, Any]:
        return _handle_submit_benchmark(ctx, body, auth)

    @router.get('/summary')
    def get_summary(auth: AuthDep) -> dict[str, Any]:
        return _handle_get_summary(ctx, auth)

    @router.get('')
    def list_benchmarks(auth: AuthDep) -> dict[str, Any]:
        return _handle_list_benchmarks(ctx, auth)

    @router.post('/segments', status_code=201, responses={403: {'description': 'Super-admin key required'}})
    def publish_segment_benchmark(
        body: SegmentBenchmarkRequest,
        auth: AuthDep,
        x_super_admin_key: str = '',
    ) -> dict[str, Any]:
        return _handle_publish_segment(ctx, body, auth, x_super_admin_key)

    @router.get('/segments/{segment}', responses={404: {'description': 'No benchmark data for this segment yet'}})
    def get_segment_benchmarks(segment: str, auth: AuthDep) -> dict[str, Any]:
        return _handle_get_segment(ctx, segment, auth)

    @router.get('/compare/{segment}')
    def compare_to_segment(segment: str, auth: AuthDep) -> dict[str, Any]:
        return _handle_compare(ctx, segment, auth)

    return router

