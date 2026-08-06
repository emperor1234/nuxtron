'use client';

import Link from 'next/link';
import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type ROIForecastResult = {
  projected_engagement: number;
  projected_clicks: number;
  projected_conversions: number;
  projected_revenue: number;
  confidence: number;
  recommended_slot: string;
};

const PLATFORMS = ['linkedin', 'x', 'instagram', 'threads', 'tiktok', 'facebook', 'youtube'];

const DEFAULTS = {
  content_title: 'How AI Saves 20 Hours a Week on Social Media',
  platform: 'linkedin',
  expected_impressions: 8000,
  historical_revenue: '4200, 3800, 5100, 4600',
  historical_engagement_rate: '0.06, 0.055, 0.07, 0.065',
};

function MetricCard({ label, value, sub, accent }: Readonly<{ label: string; value: string; sub?: string; accent?: string }>) {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: '16px 20px' }}>
      <div style={{ fontSize: 11, color: 'var(--muted)', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 28, fontWeight: 800, color: accent ?? 'var(--text)' }}>{value}</div>
      {sub ? <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>{sub}</div> : null}
    </div>
  );
}

export default function ROIForecastPage() {
  const [form, setForm] = useState(DEFAULTS);
  const [result, setResult] = useState<ROIForecastResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function setField<K extends keyof typeof DEFAULTS>(key: K, value: typeof DEFAULTS[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function forecast() {
    if (!form.content_title.trim()) { setError('Content title is required.'); return; }
    setLoading(true);
    setError(null);
    try {
      const historical_revenue = form.historical_revenue
        .split(',')
        .map((v) => Number.parseFloat(v.trim()))
        .filter((v) => !Number.isNaN(v));
      const historical_engagement_rate = form.historical_engagement_rate
        .split(',')
        .map((v) => Number.parseFloat(v.trim()))
        .filter((v) => !Number.isNaN(v));

      if (historical_revenue.length < 2) {
        setError('Enter at least 2 historical revenue values, comma-separated.');
        setLoading(false);
        return;
      }
      if (historical_engagement_rate.length < 2) {
        setError('Enter at least 2 historical engagement rates, comma-separated.');
        setLoading(false);
        return;
      }

      const res = await apiSend<{ forecast?: ROIForecastResult }>(
        '/forecast/roi',
        'POST',
        {
          content_title: form.content_title,
          platform: form.platform,
          expected_impressions: form.expected_impressions,
          historical_revenue,
          historical_engagement_rate,
        },
        DEFAULT_TENANT_ID
      );
      setResult(res.forecast ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Forecast failed');
    } finally {
      setLoading(false);
    }
  }

  const confidencePct = result ? `${Math.round(result.confidence * 100)}%` : null;
  let confidenceColor = 'var(--muted)';
  if (result) {
    if (result.confidence >= 0.7) {
      confidenceColor = '#15803d';
    } else if (result.confidence >= 0.4) {
      confidenceColor = '#facc15';
    } else {
      confidenceColor = '#dc2626';
    }
  }
  let confidenceMessage = 'No forecast yet.';
  if (result) {
    if (result.confidence >= 0.7) {
      confidenceMessage = 'High confidence - solid historical data available.';
    } else if (result.confidence >= 0.4) {
      confidenceMessage = 'Moderate confidence - add more historical data points to improve accuracy.';
    } else {
      confidenceMessage = 'Low confidence - insufficient historical data. Publish a few posts first.';
    }
  }

  return (
    <div style={s.container}>
      <div style={s.header}>
        <Link href="/studio/lately" style={s.backLink}>← Lately AI Hub</Link>
        <h1 style={s.title}>ROI Forecaster</h1>
        <p style={s.subtitle}>
          Predict projected engagement, clicks, conversions, and revenue before you publish. Anchored to your own
          historical performance data so the model improves as you grow.
        </p>
      </div>

      {error ? <div style={s.errorBanner}>⚠ {error}</div> : null}

      <div style={s.layout}>
        {/* Input Form */}
        <section style={s.formCard}>
          <h2 style={s.sectionTitle}>Forecast Inputs</h2>

          <div style={s.field}>
            <label htmlFor="roi-content-title" style={s.label}>Content Title</label>
            <input
              id="roi-content-title"
              value={form.content_title}
              onChange={(e) => setField('content_title', e.target.value)}
              style={s.input}
              placeholder="e.g. How AI Saves 20 Hours a Week on Social Media"
            />
          </div>

          <div style={s.field}>
            <label htmlFor="roi-platform" style={s.label}>Publishing Platform</label>
            <select id="roi-platform" value={form.platform} onChange={(e) => setField('platform', e.target.value)} style={s.input}>
              {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          <div style={s.field}>
            <label htmlFor="roi-impressions" style={s.label}>Expected Impressions: <strong>{form.expected_impressions.toLocaleString()}</strong></label>
            <input
              id="roi-impressions"
              type="range"
              min={500}
              max={100000}
              step={500}
              value={form.expected_impressions}
              onChange={(e) => setField('expected_impressions', Number.parseInt(e.target.value, 10))}
              style={{ width: '100%', accentColor: '#6366f1' }}
            />
            <div style={s.rangeLabels}><span>500</span><span>100,000</span></div>
          </div>

          <div style={s.field}>
            <label htmlFor="roi-historical-revenue" style={s.label}>Historical Revenue (comma-separated, last 4 posts, USD)</label>
            <input
              id="roi-historical-revenue"
              value={form.historical_revenue}
              onChange={(e) => setField('historical_revenue', e.target.value)}
              style={s.input}
              placeholder="4200, 3800, 5100, 4600"
            />
          </div>

          <div style={s.field}>
            <label htmlFor="roi-historical-engagement" style={s.label}>Historical Engagement Rates (comma-separated, e.g. 0.06 = 6%)</label>
            <input
              id="roi-historical-engagement"
              value={form.historical_engagement_rate}
              onChange={(e) => setField('historical_engagement_rate', e.target.value)}
              style={s.input}
              placeholder="0.06, 0.055, 0.07, 0.065"
            />
            <span style={s.hint}>Engagement rate = (likes + comments + shares) / impressions</span>
          </div>

          <button onClick={forecast} disabled={loading} style={s.btn}>
            {loading ? 'Forecasting…' : '📈 Generate ROI Forecast'}
          </button>
        </section>

        {/* Results */}
        {result ? (
          <section style={s.resultsPanel}>
            <h2 style={s.sectionTitle}>Forecast Results</h2>
            <div style={s.metricsGrid}>
              <MetricCard
                label="Projected Engagement"
                value={result.projected_engagement.toLocaleString()}
                sub="likes + comments + shares"
                accent="var(--brand)"
              />
              <MetricCard
                label="Projected Clicks"
                value={result.projected_clicks.toLocaleString()}
                sub="link clicks / CTR"
                accent="#fbbf24"
              />
              <MetricCard
                label="Projected Conversions"
                value={result.projected_conversions.toLocaleString()}
                sub="sign-ups / demos / leads"
                accent="#34d399"
              />
              <MetricCard
                label="Projected Revenue"
                value={`$${result.projected_revenue.toLocaleString()}`}
                sub="USD, attributed"
                accent="#15803d"
              />
            </div>

            <div style={s.confidenceCard}>
              <div style={{ ...s.confidenceBar }}>
                <div style={s.confLabel}>Model Confidence</div>
                <div style={{ ...s.confValue, color: confidenceColor }}>
                  {confidencePct}
                </div>
              </div>
              <div style={s.confTrack}>
                <div
                  style={{
                    ...s.confFill,
                    width: confidencePct ?? '0%',
                    background: confidenceColor,
                  }}
                />
              </div>
              <div style={s.confNote}>{confidenceMessage}</div>
            </div>

            <div style={s.slotCard}>
              <div style={s.slotLabel}>Recommended Publishing Slot</div>
              <div style={s.slotValue}>{result.recommended_slot}</div>
              <div style={s.slotNote}>Optimal time window for {form.platform} based on historical performance</div>
            </div>
          </section>
        ) : (
          <section style={s.resultsPanel}>
            <h2 style={s.sectionTitle}>Forecast Results</h2>
            <div style={s.emptyResults}>
              <div style={s.emptyIcon}>📊</div>
              <div>Enter your content details and click <strong>Generate ROI Forecast</strong> to see projected metrics before publishing.</div>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  container: { maxWidth: 1100, margin: '0 auto', padding: '24px 16px', fontFamily: 'system-ui, sans-serif', color: 'var(--text)' },
  header: { marginBottom: 32 },
  backLink: { color: 'var(--muted)', textDecoration: 'none', fontSize: 14 },
  title: { fontSize: 28, fontWeight: 800, margin: '10px 0 8px', color: 'var(--text)' },
  subtitle: { fontSize: 14, color: 'var(--muted)', maxWidth: 720 },
  errorBanner: { background: 'rgba(248,113,113,0.1)', border: '1px solid rgba(248,113,113,0.3)', borderRadius: 8, padding: '10px 14px', color: '#dc2626', marginBottom: 20, fontSize: 13 },
  layout: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 24, alignItems: 'start' },
  formCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24 },
  resultsPanel: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24 },
  sectionTitle: { fontSize: 18, fontWeight: 700, margin: '0 0 20px', color: 'var(--text)' },
  field: { marginBottom: 16 },
  label: { fontSize: 12, color: 'var(--muted)', marginBottom: 4, display: 'block' },
  input: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '8px 12px', color: 'var(--text)', fontSize: 13, boxSizing: 'border-box' as const, width: '100%' },
  hint: { fontSize: 11, color: 'var(--muted)', marginTop: 4, display: 'block' },
  rangeLabels: { display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--muted)', marginTop: 2 },
  btn: { background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '10px 20px', cursor: 'pointer', fontWeight: 600, fontSize: 14, width: '100%' },
  metricsGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12, marginBottom: 16 },
  confidenceCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: 16, marginBottom: 12 },
  confidenceBar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  confLabel: { fontSize: 12, color: 'var(--muted)' },
  confValue: { fontSize: 20, fontWeight: 800 },
  confTrack: { background: 'var(--card)', borderRadius: 4, height: 8, marginBottom: 8 },
  confFill: { height: 8, borderRadius: 4, transition: 'width 0.5s ease' },
  confNote: { fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 },
  slotCard: { background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 10, padding: 16 },
  slotLabel: { fontSize: 11, color: '#6366f1', marginBottom: 4, textTransform: 'uppercase' as const, letterSpacing: 1 },
  slotValue: { fontSize: 20, fontWeight: 700, color: 'var(--brand)', marginBottom: 4 },
  slotNote: { fontSize: 12, color: 'var(--muted)' },
  emptyResults: { display: 'flex', flexDirection: 'column' as const, alignItems: 'center', justifyContent: 'center', padding: '60px 20px', color: 'var(--muted)', fontSize: 13, textAlign: 'center', gap: 16 },
  emptyIcon: { fontSize: 40 },
};
