'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

type Keyword = {
  keyword: string;
  impressions: number;
  engagement: number;
  weight: number;
  engagement_rate: number;
  platform: string;
};

type TopKeywordsResult = {
  keywords?: Keyword[];
};

const PLATFORMS = ['linkedin', 'x', 'instagram', 'threads', 'tiktok', 'facebook'];

function fontSizeForWeight(w: number): number {
  // weight is 10–100 → font 13–44px
  return Math.round(13 + ((w - 10) / 90) * 31);
}

function colorForEngagement(rate: number): string {
  if (rate >= 0.08) return '#15803d';
  if (rate >= 0.04) return '#facc15';
  if (rate >= 0.02) return '#fb923c';
  return 'var(--muted)';
}

export default function WordCloudPage() {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trackKw, setTrackKw] = useState('');
  const [trackPlatform, setTrackPlatform] = useState('linkedin');
  const [trackImpressions, setTrackImpressions] = useState('1000');
  const [trackEngagement, setTrackEngagement] = useState('80');
  const [submitting, setSubmitting] = useState(false);
  const [sortBy, setSortBy] = useState<'impressions' | 'engagement_rate' | 'weight'>('impressions');

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet<TopKeywordsResult>('/analytics/keywords/top', DEFAULT_TENANT_ID);
      setKeywords(res.keywords ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load keywords');
    } finally {
      setLoading(false);
    }
  }

  async function trackKeyword() {
    if (!trackKw.trim() || trackKw.trim().length < 2) {
      setError('Keyword must be at least 2 characters.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await apiSend(
        '/analytics/keywords/track',
        'POST',
        {
          keyword: trackKw.trim(),
          platform: trackPlatform,
          impressions: Math.max(0, Number.parseInt(trackImpressions, 10) || 0),
          engagement: Math.max(0, Number.parseInt(trackEngagement, 10) || 0),
        },
        DEFAULT_TENANT_ID
      );
      setTrackKw('');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Track failed');
    } finally {
      setSubmitting(false);
    }
  }

  const sorted = [...keywords].sort((a, b) => b[sortBy] - a[sortBy]);
  const top40 = sorted.slice(0, 40);
  let cloudContent: React.ReactNode;
  if (loading) {
    cloudContent = <div style={s.skeleton}>Loading keyword data…</div>;
  } else if (keywords.length === 0) {
    cloudContent = (
      <div style={s.empty}>
        No keyword data yet. Track some keywords below or run analytics sync.
      </div>
    );
  } else {
    cloudContent = (
      <div style={s.cloud}>
        {keywords.map((kw) => (
          <span
            key={kw.keyword + kw.platform}
            style={{
              ...s.cloudWord,
              fontSize: fontSizeForWeight(kw.weight),
              color: colorForEngagement(kw.engagement_rate),
            }}
            title={`${kw.keyword} — impressions: ${kw.impressions.toLocaleString()}, engagement rate: ${(kw.engagement_rate * 100).toFixed(1)}%, platform: ${kw.platform}`}
          >
            {kw.keyword}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div style={s.container}>
      <div style={s.header}>
        <Link href="/studio/lately" style={s.backLink}>← Lately AI Hub</Link>
        <h1 style={s.title}>Keyword Intelligence</h1>
        <p style={s.subtitle}>
          Visual word cloud showing which keywords and phrases drive the highest reach and engagement across all
          channels. Sized by weight (performance impact), coloured by engagement rate.
        </p>
      </div>

      {error ? <div style={s.errorBanner}>⚠ {error}</div> : null}

      {/* Word Cloud */}
      <section style={s.cloudCard}>
        <h2 style={s.sectionTitle}>Keyword Word Cloud</h2>
        {cloudContent}
        <div style={s.legend}>
          <span style={{ color: '#15803d' }}>■ &gt;8% eng.</span>
          <span style={{ color: '#facc15' }}>■ 4–8%</span>
          <span style={{ color: '#fb923c' }}>■ 2–4%</span>
          <span style={{ color: 'var(--muted)' }}>■ &lt;2%</span>
          <span style={{ color: 'var(--muted)', marginLeft: 8 }}>Size = performance weight</span>
        </div>
      </section>

      {/* Sort + Table */}
      <section style={s.card}>
        <div style={s.tableHeader}>
          <h2 style={s.sectionTitle}>Top Keywords (40)</h2>
          <div style={s.sortRow}>
            <span style={s.sortLabel}>Sort by:</span>
            {(['impressions', 'engagement_rate', 'weight'] as const).map((k) => (
              <button
                key={k}
                onClick={() => setSortBy(k)}
                style={{ ...s.sortChip, ...(sortBy === k ? s.sortChipActive : {}) }}
              >
                {k === 'engagement_rate' ? 'Engagement Rate' : k.charAt(0).toUpperCase() + k.slice(1)}
              </button>
            ))}
          </div>
        </div>
        {top40.length === 0 ? (
          <div style={s.empty}>No data yet.</div>
        ) : (
          <table style={s.table}>
            <thead>
              <tr>
                <th style={s.th}>#</th>
                <th style={s.th}>Keyword</th>
                <th style={s.th}>Platform</th>
                <th style={s.th}>Impressions</th>
                <th style={s.th}>Engagement</th>
                <th style={s.th}>Eng. Rate</th>
                <th style={s.th}>Weight</th>
              </tr>
            </thead>
            <tbody>
              {top40.map((kw, i) => (
                <tr key={kw.keyword + kw.platform + i}>
                  <td style={s.td}>{i + 1}</td>
                  <td style={{ ...s.td, fontWeight: 600, color: 'var(--text)' }}>{kw.keyword}</td>
                  <td style={s.td}>
                    <span style={s.platBadge}>{kw.platform}</span>
                  </td>
                  <td style={s.td}>{kw.impressions.toLocaleString()}</td>
                  <td style={s.td}>{kw.engagement.toLocaleString()}</td>
                  <td style={{ ...s.td, color: colorForEngagement(kw.engagement_rate) }}>
                    {(kw.engagement_rate * 100).toFixed(1)}%
                  </td>
                  <td style={s.td}>
                    <div style={s.weightBar}>
                      <div
                        style={{
                          ...s.weightFill,
                          width: `${kw.weight}%`,
                          background: colorForEngagement(kw.engagement_rate),
                        }}
                      />
                      <span style={s.weightLabel}>{kw.weight}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {/* Track keyword form */}
      <section style={s.card}>
        <h2 style={s.sectionTitle}>Track a Keyword</h2>
        <p style={s.hint}>Manually add or update a keyword's performance data. Synced from your social analytics automatically in production.</p>
        <div style={s.formRow}>
          <div style={s.field}>
            <label htmlFor="track-keyword" style={s.label}>Keyword</label>
            <input
              id="track-keyword"
              value={trackKw}
              onChange={(e) => setTrackKw(e.target.value)}
              style={s.input}
              placeholder="e.g. AI automation"
            />
          </div>
          <div style={s.field}>
            <label htmlFor="track-platform" style={s.label}>Platform</label>
            <select id="track-platform" value={trackPlatform} onChange={(e) => setTrackPlatform(e.target.value)} style={s.input}>
              {PLATFORMS.map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div style={s.field}>
            <label htmlFor="track-impressions" style={s.label}>Impressions</label>
            <input
              id="track-impressions"
              type="number"
              value={trackImpressions}
              onChange={(e) => setTrackImpressions(e.target.value)}
              style={s.input}
              min={0}
            />
          </div>
          <div style={s.field}>
            <label htmlFor="track-engagement" style={s.label}>Engagement</label>
            <input
              id="track-engagement"
              type="number"
              value={trackEngagement}
              onChange={(e) => setTrackEngagement(e.target.value)}
              style={s.input}
              min={0}
            />
          </div>
        </div>
        <button onClick={trackKeyword} disabled={submitting} style={s.btn}>
          {submitting ? 'Tracking…' : '+ Track Keyword'}
        </button>
      </section>
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
  cloudCard: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, marginBottom: 24 },
  card: { background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12, padding: 24, marginBottom: 24 },
  sectionTitle: { fontSize: 18, fontWeight: 700, margin: '0 0 16px', color: 'var(--text)' },
  skeleton: { color: 'var(--muted)', fontSize: 13, padding: 24 },
  empty: { color: 'var(--muted)', fontSize: 13, textAlign: 'center', padding: 32 },
  cloud: { display: 'flex', flexWrap: 'wrap' as const, gap: 12, alignItems: 'center', padding: '12px 0', minHeight: 120 },
  cloudWord: { cursor: 'default', fontWeight: 700, lineHeight: 1.3, transition: 'opacity 0.2s' },
  legend: { display: 'flex', gap: 16, marginTop: 16, fontSize: 12, color: 'var(--muted)', flexWrap: 'wrap' as const },
  tableHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap' as const, gap: 8 },
  sortRow: { display: 'flex', gap: 6, alignItems: 'center' },
  sortLabel: { fontSize: 12, color: 'var(--muted)' },
  sortChip: { background: 'var(--card)', color: 'var(--muted)', border: '1px solid var(--line)', borderRadius: 6, padding: '3px 10px', cursor: 'pointer', fontSize: 12 },
  sortChipActive: { background: 'rgba(99,102,241,0.2)', color: 'var(--brand)', borderColor: '#6366f1' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  th: { background: 'var(--card)', color: 'var(--muted)', padding: '8px 12px', textAlign: 'left', borderBottom: '1px solid var(--line)', fontWeight: 600 },
  td: { padding: '8px 12px', borderBottom: '1px solid var(--line)', color: 'var(--muted)' },
  platBadge: { background: 'var(--card)', color: 'var(--muted)', borderRadius: 4, padding: '2px 6px', fontSize: 11 },
  weightBar: { display: 'flex', alignItems: 'center', gap: 6 },
  weightFill: { height: 6, borderRadius: 3, minWidth: 2, transition: 'width 0.3s' },
  weightLabel: { fontSize: 11, color: 'var(--muted)', minWidth: 20 },
  formRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 180px), 1fr))', gap: 14, marginBottom: 14 },
  field: {},
  label: { fontSize: 12, color: 'var(--muted)', marginBottom: 4, display: 'block' },
  input: { width: '100%', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 8, padding: '8px 12px', color: 'var(--text)', fontSize: 13, boxSizing: 'border-box' as const },
  btn: { background: '#6366f1', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 18px', cursor: 'pointer', fontWeight: 600, fontSize: 14 },
  hint: { fontSize: 12, color: 'var(--muted)', marginBottom: 16, lineHeight: 1.6 },
};
