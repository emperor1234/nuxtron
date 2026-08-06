'use client';

import { useEffect, useMemo, useState } from 'react';
import { apiGet, apiPost, resolveSessionTenant } from '@/app/lib/api-client';

type Json = Record<string, unknown>;

function asNumber(v: unknown, fb = 0): number {
  return typeof v === 'number' ? v : fb;
}
function asString(v: unknown, fb = ''): string {
  return typeof v === 'string' ? v : fb;
}
function asArray(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
function asObject(v: unknown): Json {
  return v !== null && typeof v === 'object' && !Array.isArray(v) ? (v as Json) : {};
}

const PERCENTILE_COLOR: Record<string, string> = {
  top_quartile: '#22c55e',
  above_median: 'var(--brand)',
  below_median: '#d97706',
  no_segment_data: 'var(--muted)',
};

const METRIC_LABELS: Record<string, string> = {
  activation_rate_pct: 'Activation Rate %',
  churn_reduction_pct: 'Churn Reduction %',
  dispute_auto_resolution_rate_pct: 'Dispute Auto-Resolution %',
  revenue_per_recommendation_gbp: 'Revenue / Recommendation £',
  qualified_lead_rate_pct: 'Qualified Lead Rate %',
  organic_reach_uplift_pct: 'Organic Reach Uplift %',
  response_time_minutes: 'Response Time (min)',
  attribution_coverage_pct: 'Attribution Coverage %',
  outreach_conversion_pct: 'Outreach Conversion %',
  avg_decision_quality_score: 'Avg Decision Quality',
  net_revenue_retained_gbp: 'Net Revenue Retained £',
  autonomous_workflow_coverage_pct: 'Autonomous Workflow Coverage %',
};

export default function BenchmarksPage() {
  const [tenantId] = useState(resolveSessionTenant);
  const [summary, setSummary] = useState<Json>({});
  const [comparison, setComparison] = useState<unknown[]>([]);
  const [benchmarks, setBenchmarks] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [segment, setSegment] = useState('saas');

  // Submit form
  const [metric, setMetric] = useState('activation_rate_pct');
  const [metricValue, setMetricValue] = useState(0);
  const [baseline, setBaseline] = useState('');
  const [period, setPeriod] = useState('2026-Q2');
  const [submitMsg, setSubmitMsg] = useState('');

  const metricsData = useMemo(() => asObject(summary.metrics), [summary]);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const [sumData, cmpData, listData] = await Promise.all([
        apiGet('/benchmarks/summary', tenantId),
        apiGet(`/benchmarks/compare/${segment}`, tenantId),
        apiGet('/benchmarks', tenantId),
      ]);
      setSummary(sumData as Json);
      setComparison(asArray((cmpData as Json).comparison));
      setBenchmarks(asArray((listData as Json).benchmarks));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenantId, segment]);

  async function submitBenchmark() {
    if (!metric.trim() || !period.trim()) return;
    setSubmitMsg('');
    try {
      const res = await apiPost(
        '/benchmarks',
        {
          metric,
          value: metricValue,
          baseline_value: baseline.trim() ? Number.parseFloat(baseline) : null,
          period_label: period,
          segment,
        },
        tenantId
      );
      const r = res as Json;
      const uplift = r.uplift_pct;
      const upliftText = uplift === null || uplift === undefined ? 'N/A (no baseline)' : `${asNumber(uplift)}%`;
      setSubmitMsg(`Recorded. Uplift: ${upliftText}`);
      await load();
    } catch (e) {
      setSubmitMsg(`Error: ${String(e)}`);
    }
  }

  return (
    <main style={{ padding: '2rem', maxWidth: '1100px', margin: '0 auto' }}>
      <h1 style={{ fontSize: '28px', fontWeight: 700, marginBottom: '0.5rem' }}>Performance Benchmarks</h1>
      <p style={{ color: 'var(--muted)', marginBottom: '1.5rem' }}>
        Tenant-level uplift data and segment-level comparisons — the Performance Benchmark Moat.
      </p>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1.5rem', alignItems: 'center' }}>
        <input
          value={tenantId}
          readOnly
          placeholder="Tenant ID"
          style={{
            padding: '0.5rem 0.8rem',
            borderRadius: 6,
            border: '1px solid var(--line)',
            background: 'var(--card)',
            color: 'var(--text)',
            minWidth: 200,
          }}
        />
        <select
          value={segment}
          onChange={(e) => setSegment(e.target.value)}
          style={{
            padding: '0.5rem 0.8rem',
            borderRadius: 6,
            border: '1px solid var(--line)',
            background: 'var(--card)',
            color: 'var(--text)',
          }}
        >
          {[
            'ecommerce',
            'saas',
            'agency',
            'media',
            'fintech',
            'healthtech',
            'nonprofit',
            'education',
            'marketplace',
            'all',
          ].map((s) => (
            <option key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>
        <button
          onClick={load}
          disabled={loading}
          style={{
            padding: '0.5rem 1.2rem',
            borderRadius: 6,
            background: '#6366f1',
            color: 'var(--text)',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          {loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {error && <p style={{ color: '#ef4444', marginBottom: '1rem' }}>{error}</p>}

      {/* Summary metrics */}
      {Object.keys(metricsData).length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '1rem' }}>Your Metrics</h2>
          <div
            style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 200px), 1fr))', gap: '0.75rem' }}
          >
            {Object.entries(metricsData).map(([key, data]) => {
              const d = asObject(data);
              const uplift = d.avg_uplift_pct;
              return (
                <div
                  key={key}
                  style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '0.75rem' }}
                >
                  <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '0.25rem' }}>
                    {METRIC_LABELS[key] ?? key.replaceAll('_', ' ')}
                  </div>
                  <div style={{ fontSize: '22px', fontWeight: 700, color: 'var(--brand)' }}>
                    {asNumber(d.avg_value).toFixed(1)}
                  </div>
                  {uplift !== null && uplift !== undefined && (
                    <div style={{ fontSize: '13px', color: asNumber(uplift) >= 0 ? '#22c55e' : '#ef4444' }}>
                      {asNumber(uplift) >= 0 ? '▲' : '▼'} {Math.abs(asNumber(uplift))}% uplift
                    </div>
                  )}
                  <div style={{ fontSize: '12px', color: 'var(--faint)' }}>{asNumber(d.data_points)} data point(s)</div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Segment comparison */}
      {comparison.length > 0 && (
        <section style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '1rem' }}>
            vs {segment.charAt(0).toUpperCase() + segment.slice(1)} Segment
          </h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Metric', 'Your Value', 'Segment P50', 'P75', 'P90', 'Band'].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '0.4rem 0.6rem', color: 'var(--muted)' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparison.map((c, idx) => {
                const cmp = c as Json;
                const band = asString(cmp.percentile_band, 'no_segment_data');
                const p50 =
                  cmp.segment_p50 === null || cmp.segment_p50 === undefined
                    ? '—'
                    : asNumber(cmp.segment_p50).toFixed(2);
                const p75 =
                  cmp.segment_p75 === null || cmp.segment_p75 === undefined
                    ? '—'
                    : asNumber(cmp.segment_p75).toFixed(2);
                const p90 =
                  cmp.segment_p90 === null || cmp.segment_p90 === undefined
                    ? '—'
                    : asNumber(cmp.segment_p90).toFixed(2);
                return (
                  <tr key={`${asString(cmp.metric)}-${idx}`} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '0.4rem 0.6rem', fontSize: '13px' }}>
                      {METRIC_LABELS[asString(cmp.metric)] ?? asString(cmp.metric).replaceAll('_', ' ')}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem', fontWeight: 700 }}>
                      {asNumber(cmp.tenant_value).toFixed(2)}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem', color: 'var(--muted)' }}>{p50}</td>
                    <td style={{ padding: '0.4rem 0.6rem', color: 'var(--muted)' }}>{p75}</td>
                    <td style={{ padding: '0.4rem 0.6rem', color: 'var(--muted)' }}>{p90}</td>
                    <td
                      style={{
                        padding: '0.4rem 0.6rem',
                        color: PERCENTILE_COLOR[band],
                        fontWeight: 600,
                        fontSize: '12px',
                      }}
                    >
                      {band.replaceAll('_', ' ')}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}

      {/* Submit benchmark */}
      <section
        style={{
          marginBottom: '2rem',
          background: 'var(--card)',
          border: '1px solid var(--line)',
          borderRadius: 8,
          padding: '1.25rem',
        }}
      >
        <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '1rem' }}>Record Benchmark Data Point</h2>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 170px), 1fr))',
            gap: '0.5rem',
            marginBottom: '0.75rem',
          }}
        >
          <div>
            <label htmlFor="metric-input" style={{ fontSize: '12px', color: 'var(--muted)' }}>
              Metric
            </label>
            <select
              id="metric-input"
              value={metric}
              onChange={(e) => setMetric(e.target.value)}
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                borderRadius: 6,
                border: '1px solid var(--line)',
                background: 'var(--card)',
                color: 'var(--text)',
              }}
            >
              {Object.entries(METRIC_LABELS).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="value-input" style={{ fontSize: '12px', color: 'var(--muted)' }}>
              Value
            </label>
            <input
              id="value-input"
              type="number"
              value={metricValue}
              onChange={(e) => setMetricValue(Number.parseFloat(e.target.value))}
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                borderRadius: 6,
                border: '1px solid var(--line)',
                background: 'var(--card)',
                color: 'var(--text)',
              }}
            />
          </div>
          <div>
            <label htmlFor="baseline-input" style={{ fontSize: '12px', color: 'var(--muted)' }}>
              Baseline (optional)
            </label>
            <input
              id="baseline-input"
              value={baseline}
              onChange={(e) => setBaseline(e.target.value)}
              placeholder="e.g. 20"
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                borderRadius: 6,
                border: '1px solid var(--line)',
                background: 'var(--card)',
                color: 'var(--text)',
              }}
            />
          </div>
          <div>
            <label htmlFor="period-input" style={{ fontSize: '12px', color: 'var(--muted)' }}>
              Period
            </label>
            <input
              id="period-input"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              placeholder="2026-Q2"
              style={{
                width: '100%',
                padding: '0.4rem 0.6rem',
                borderRadius: 6,
                border: '1px solid var(--line)',
                background: 'var(--card)',
                color: 'var(--text)',
              }}
            />
          </div>
        </div>
        <button
          onClick={submitBenchmark}
          style={{
            padding: '0.5rem 1.2rem',
            borderRadius: 6,
            background: '#6366f1',
            color: 'var(--text)',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          Submit
        </button>
        {submitMsg && <p style={{ color: 'var(--brand)', fontSize: '14px', marginTop: '0.5rem' }}>{submitMsg}</p>}
      </section>

      {/* Data history */}
      {benchmarks.length > 0 && (
        <section>
          <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '0.75rem' }}>Data History</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '14px' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--line)' }}>
                {['Metric', 'Value', 'Baseline', 'Uplift', 'Period', 'Date'].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '0.4rem 0.6rem', color: 'var(--muted)' }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {benchmarks.slice(0, 30).map((b, idx) => {
                const bm = b as Json;
                const upliftVal = bm.uplift_pct;
                const hasBaseline = bm.baseline_value !== null && bm.baseline_value !== undefined;
                const hasUplift = upliftVal !== null && upliftVal !== undefined;
                const upliftNumber = asNumber(upliftVal);
                const upliftColorInner = upliftNumber >= 0 ? '#22c55e' : '#ef4444';
                const upliftColor = hasUplift ? upliftColorInner : 'var(--muted)';
                const upliftSign = upliftNumber >= 0 ? '+' : '';
                const upliftText = hasUplift ? `${upliftSign}${upliftNumber}%` : '—';
                return (
                  <tr key={`${asString(bm.id)}-${idx}`} style={{ borderBottom: '1px solid var(--line)' }}>
                    <td style={{ padding: '0.4rem 0.6rem', fontSize: '13px' }}>
                      {METRIC_LABELS[asString(bm.metric)] ?? asString(bm.metric)}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem', fontWeight: 600 }}>{asNumber(bm.value).toFixed(2)}</td>
                    <td style={{ padding: '0.4rem 0.6rem', color: 'var(--muted)' }}>
                      {hasBaseline ? asNumber(bm.baseline_value).toFixed(2) : '—'}
                    </td>
                    <td style={{ padding: '0.4rem 0.6rem', color: upliftColor }}>{upliftText}</td>
                    <td style={{ padding: '0.4rem 0.6rem', color: 'var(--muted)' }}>{asString(bm.period_label)}</td>
                    <td style={{ padding: '0.4rem 0.6rem', color: 'var(--muted)', fontSize: '12px' }}>
                      {asString(bm.created_at).slice(0, 10)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
