'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { DEFAULT_TENANT_ID, apiGet } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type TimeSlot = {
  day: string;
  hour: number;
  score: number;
  expected_engagement: number;
  reason: string;
};

type NetworkRecommendation = {
  network: string;
  timezone: string;
  best_slots: TimeSlot[];
  avoid_times: string[];
};

type HeatmapRow = {
  day: string;
  hours: Record<string, number>;
};

type BestTimeData = {
  recommendations: NetworkRecommendation[];
  model_metadata: { last_trained: string; data_points: number; accuracy: string };
};

const NETWORK_COLORS: Record<string, string> = {
  instagram: '#E1306C',
  x: '#1DA1F2',
  facebook: '#1877F2',
  linkedin: '#0A66C2',
  tiktok: '#69C9D0',
  youtube: '#FF0000',
};

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const HOURS = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22];

function scoreToColor(score: number): string {
  if (score >= 90) return '#22c55e';
  if (score >= 75) return '#84CC16';
  if (score >= 60) return '#F59E0B';
  if (score >= 40) return '#EF4444';
  return '#eef0f4';
}

function scoreToOpacity(score: number): number {
  return 0.08 + (score / 100) * 0.85;
}

function formatHourLabel(hour: number): string {
  if (hour < 12) return `${hour}am`;
  if (hour === 12) return '12pm';
  return `${hour - 12}pm`;
}

function rankLabel(index: number): string {
  if (index === 0) return '🥇';
  if (index === 1) return '🥈';
  return '🥉';
}

function networkColorRgb(network: string): string {
  const hex = NETWORK_COLORS[network] ?? '#eef0f4';
  const channels = hex
    .slice(1)
    .match(/.{2}/g)
    ?.map((value) => Number.parseInt(value, 16)) ?? [31, 41, 55];
  return channels.join(',');
}

export default function BestTimeToPostPage() {
  const [data, setData] = useState<BestTimeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNetwork, setSelectedNetwork] = useState('instagram');
  const [viewMode, setViewMode] = useState<'recommendations' | 'heatmap'>('recommendations');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiGet('/social/best-time', DEFAULT_TENANT_ID);
      setData(res as BestTimeData);
    } catch {
      setData(null);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Best-time backend unavailable in strict no-mock mode.'
          : 'Best-time backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  function buildHeatmap(): HeatmapRow[] {
    const rec = data?.recommendations.find((r) => r.network === selectedNetwork);
    if (!rec) return DAYS.map((day) => ({ day, hours: Object.fromEntries(HOURS.map((h) => [h, 30])) }));
    const slotMap: Record<string, number> = {};
    rec.best_slots.forEach((s) => {
      slotMap[`${s.day}-${s.hour}`] = s.score;
    });
    return DAYS.map((day) => ({
      day,
      hours: Object.fromEntries(HOURS.map((h) => [h, slotMap[`${day}-${h}`] ?? (h >= 9 && h <= 17 ? 45 : 20)])),
    }));
  }

  const currentRec = data?.recommendations.find((r) => r.network === selectedNetwork);
  const heatmapRows = buildHeatmap();

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>Best Time to Post</h1>
          <p style={styles.subtitle}>
            AI-powered posting time recommendations based on your audience engagement patterns · Updated continuously
          </p>
          <Link href="/studio/social-studio/optimization" style={styles.optimizeLink}>
            Open AI Optimization Workspace
          </Link>
        </div>
        {data?.model_metadata && (
          <div style={styles.modelMeta}>
            <div style={styles.metaItem}>🤖 {data.model_metadata.accuracy} accuracy</div>
            <div style={styles.metaItem}>📊 {(data.model_metadata.data_points / 1000000).toFixed(1)}M data points</div>
          </div>
        )}
      </div>

      {/* Network Selector */}
      <div style={styles.networkTabs}>
        {(data?.recommendations ?? []).map((rec) => (
          <button
            key={rec.network}
            onClick={() => setSelectedNetwork(rec.network)}
            style={{
              ...styles.networkTab,
              ...(selectedNetwork === rec.network
                ? { background: NETWORK_COLORS[rec.network], color: '#fff', borderColor: NETWORK_COLORS[rec.network] }
                : {}),
            }}
          >
            {rec.network}
          </button>
        ))}
      </div>

      {/* View Mode Toggle */}
      <div style={styles.viewToggle}>
        <button
          onClick={() => setViewMode('recommendations')}
          style={{ ...styles.toggleBtn, ...(viewMode === 'recommendations' ? styles.toggleActive : {}) }}
        >
          🏆 Top Slots
        </button>
        <button
          onClick={() => setViewMode('heatmap')}
          style={{ ...styles.toggleBtn, ...(viewMode === 'heatmap' ? styles.toggleActive : {}) }}
        >
          🌡 Heatmap
        </button>
      </div>

      {error ? <div style={styles.errorBanner}>⚠ {error}</div> : null}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[1, 2, 3].map((i) => (
            <div key={i} style={{ height: 120, background: 'var(--card)', borderRadius: 12 }} />
          ))}
        </div>
      ) : (
        <>
          {viewMode === 'recommendations' && currentRec && (
            <div>
              <div style={styles.topSlotsGrid}>
                {currentRec.best_slots.map((slot, i) => (
                  <div
                    key={`${slot.day}-${slot.hour}`}
                    style={{ ...styles.slotCard, borderColor: i === 0 ? NETWORK_COLORS[selectedNetwork] : '#e7e9ef' }}
                  >
                    <div style={styles.slotRank}>{rankLabel(i)}</div>
                    <div style={styles.slotMain}>
                      <div style={styles.slotTime}>
                        {slot.day} at {formatHourLabel(slot.hour)}
                      </div>
                      <div style={styles.slotScore}>
                        <div style={{ ...styles.scoreBar, background: scoreToColor(slot.score) }} />
                        <span style={{ color: scoreToColor(slot.score), fontWeight: 700 }}>{slot.score}</span>
                        <span style={styles.muted}>/100</span>
                      </div>
                    </div>
                    <div style={styles.slotEngagement}>
                      Expected: <strong style={{ color: '#22c55e' }}>{slot.expected_engagement}%</strong> engagement
                    </div>
                    <div style={styles.slotReason}>{slot.reason}</div>
                  </div>
                ))}
              </div>
              <div style={styles.avoidSection}>
                <h3 style={styles.avoidTitle}>⚠ Times to Avoid on {selectedNetwork}</h3>
                <div style={styles.avoidList}>
                  {currentRec.avoid_times.map((t) => (
                    <span key={t} style={styles.avoidTag}>
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {viewMode === 'heatmap' && (
            <div style={styles.heatmapSection}>
              <h3 style={styles.heatmapTitle}>Engagement Heatmap — {selectedNetwork}</h3>
              <div style={styles.heatmapWrap}>
                <div style={styles.heatmapGrid}>
                  {/* Hour labels */}
                  <div style={styles.cornerCell} />
                  {HOURS.map((h) => (
                    <div key={h} style={styles.hourLabel}>
                      {formatHourLabel(h)}
                    </div>
                  ))}
                  {/* Rows */}
                  {heatmapRows.map((row) => (
                    <>
                      <div key={`label-${row.day}`} style={styles.dayLabel}>
                        {row.day.slice(0, 3)}
                      </div>
                      {HOURS.map((h) => (
                        <div
                          key={`${row.day}-${h}`}
                          style={{
                            ...styles.heatCell,
                            background: `rgba(${networkColorRgb(selectedNetwork)}, ${scoreToOpacity(row.hours[h] ?? 20)})`,
                          }}
                          title={`${row.day} ${h}:00 — Score: ${row.hours[h] ?? 20}`}
                        />
                      ))}
                    </>
                  ))}
                </div>
                {/* Legend */}
                <div style={styles.legend}>
                  <span style={styles.legendLabel}>Low</span>
                  <div style={styles.legendBar} />
                  <span style={styles.legendLabel}>High engagement</span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: 'var(--card)',
    minHeight: '100vh',
    padding: '32px 40px',
    color: 'var(--text)',
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 },
  backLink: { color: 'var(--muted)', textDecoration: 'none', fontSize: 13, display: 'block', marginBottom: 8 },
  title: { fontSize: 28, fontWeight: 700, margin: 0, letterSpacing: '-0.5px' },
  subtitle: { color: 'var(--muted)', fontSize: 14, marginTop: 6, lineHeight: 1.5 },
  optimizeLink: { display: 'inline-flex', marginTop: 12, color: 'var(--brand)', fontWeight: 700, textDecoration: 'none' },
  modelMeta: { display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end' },
  metaItem: {
    fontSize: 13,
    color: 'var(--muted)',
    background: 'var(--card)',
    padding: '4px 10px',
    borderRadius: 6,
    border: '1px solid var(--line)',
  },
  networkTabs: { display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' },
  networkTab: {
    padding: '7px 16px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--card)',
    color: 'var(--muted)',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
    textTransform: 'capitalize',
  },
  viewToggle: {
    display: 'flex',
    gap: 4,
    marginBottom: 24,
    background: 'var(--card)',
    borderRadius: 10,
    padding: 4,
    width: 'fit-content',
  },
  errorBanner: {
    background: 'rgba(245, 158, 11, 0.12)',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    color: '#b45309',
    padding: '12px 14px',
    borderRadius: 10,
    marginBottom: 16,
  },
  toggleBtn: {
    padding: '8px 20px',
    borderRadius: 8,
    border: 'none',
    background: 'transparent',
    color: 'var(--muted)',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 500,
  },
  toggleActive: { background: 'var(--card)', color: 'var(--text)' },
  topSlotsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))',
    gap: 16,
    marginBottom: 24,
  },
  slotCard: {
    background: 'var(--card)',
    borderRadius: 12,
    padding: '20px 24px',
    border: '2px solid',
    position: 'relative',
  },
  slotRank: { fontSize: 28, marginBottom: 12 },
  slotMain: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  slotTime: { fontSize: 18, fontWeight: 700 },
  slotScore: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 20 },
  scoreBar: { width: 10, height: 10, borderRadius: '50%' },
  slotEngagement: { fontSize: 14, color: 'var(--muted)', marginBottom: 10 },
  slotReason: { fontSize: 13, color: 'var(--muted)', lineHeight: 1.5 },
  avoidSection: { background: 'var(--card)', borderRadius: 12, padding: '16px 20px', border: '1px solid var(--line)' },
  avoidTitle: { fontSize: 14, fontWeight: 600, color: '#F59E0B', marginBottom: 10 },
  avoidList: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  avoidTag: {
    background: '#fee2e222',
    border: '1px solid #EF444444',
    color: '#EF4444',
    padding: '4px 12px',
    borderRadius: 6,
    fontSize: 13,
  },
  heatmapSection: {
    background: 'var(--card)',
    borderRadius: 12,
    padding: 24,
    border: '1px solid var(--line)',
    overflowX: 'auto',
  },
  heatmapTitle: { fontSize: 16, fontWeight: 600, marginBottom: 16 },
  heatmapWrap: {},
  heatmapGrid: { display: 'grid', gridTemplateColumns: `60px repeat(${HOURS.length}, 40px)`, gap: 2 },
  cornerCell: { width: 60, height: 24 },
  hourLabel: {
    fontSize: 10,
    color: 'var(--muted)',
    textAlign: 'center',
    height: 24,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  dayLabel: { fontSize: 11, color: 'var(--muted)', display: 'flex', alignItems: 'center', fontWeight: 500 },
  heatCell: { width: 40, height: 28, borderRadius: 4, cursor: 'help' },
  legend: { display: 'flex', alignItems: 'center', gap: 8, marginTop: 12 },
  legendBar: {
    flex: 1,
    height: 8,
    borderRadius: 4,
    background: 'linear-gradient(to right, #eef0f4, #6366f1, #22c55e)',
  },
  legendLabel: { fontSize: 11, color: 'var(--muted)' },
  muted: { color: 'var(--muted)', fontSize: 14 },
};
