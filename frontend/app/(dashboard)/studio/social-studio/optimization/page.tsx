'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { apiGet } from '@/app/lib/platform-api';
import {
  socialApi,
  type AnalyticsMetrics,
  type SocialNetwork,
  type OwlyWriterGeneration,
  type OwlyWriterGeneratePayload,
} from '@/app/lib/social-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type BestTimeSlot = {
  day: string;
  hour: number;
  score: number;
  expected_engagement: number;
  reason: string;
};

type BestTimeRecommendation = {
  network: string;
  timezone: string;
  best_slots: BestTimeSlot[];
  avoid_times: string[];
};

type BestTimeResponse = {
  recommendations: BestTimeRecommendation[];
  model_metadata?: { last_trained: string; data_points: number; accuracy: string };
};

const NETWORK_OPTIONS: SocialNetwork[] = [
  'instagram',
  'twitter',
  'facebook',
  'linkedin',
  'tiktok',
  'youtube',
  'threads',
];
const STYLE_OPTIONS = ['professional', 'casual', 'humorous', 'inspirational'] as const;

function safeNumber(value: number | undefined, fallback: number): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function scoreToTone(score: number): string {
  if (score >= 85) return '#22c55e';
  if (score >= 70) return '#84cc16';
  if (score >= 55) return '#f59e0b';
  return '#ef4444';
}

export default function OptimizationWorkspacePage() {
  const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
  const [bestTime, setBestTime] = useState<BestTimeResponse | null>(null);
  const [history, setHistory] = useState<OwlyWriterGeneration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [network, setNetwork] = useState<SocialNetwork>('instagram');
  const [topic, setTopic] = useState('Launch a feature update');
  const [goal, setGoal] = useState('Drive qualified clicks and saves');
  const [audience, setAudience] = useState('social media managers and founders');
  const [style, setStyle] = useState<(typeof STYLE_OPTIONS)[number]>('professional');
  const [generated, setGenerated] = useState<OwlyWriterGeneration | null>(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    void loadData();
  }, [network]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [metricsRes, bestTimeRes, historyRes] = await Promise.all([
        socialApi.getAnalytics('month'),
        apiGet<BestTimeResponse>('/social/best-time'),
        socialApi.listOwlyWriterHistory(8),
      ]);
      setMetrics(metricsRes);
      setBestTime(bestTimeRes);
      setHistory(historyRes);
    } catch (err) {
      console.error('Failed to load optimization workspace', err);
      setMetrics(null);
      setBestTime(null);
      setHistory([]);
      setError(
        IS_STRICT_NO_MOCK_MODE
          ? 'Optimization backend unavailable in strict no-mock mode.'
          : 'Optimization backend unavailable in fail-closed mode.'
      );
    } finally {
      setLoading(false);
    }
  }

  async function generateVariants() {
    setGenerating(true);
    setError(null);
    try {
      const payload: OwlyWriterGeneratePayload = {
        topic: topic.trim() || 'Social campaign idea',
        goal: goal.trim() || 'Improve engagement',
        style,
        audience: audience.trim() || 'social audience',
        platforms: [network],
        include_hashtags: true,
        include_emoji: true,
        include_cta: true,
        variations_per_platform: 4,
      };
      const response = await socialApi.generateOwlyWriter(payload);
      setGenerated(response);
      setHistory((current) => [response, ...current].slice(0, 8));
    } catch (err) {
      console.error('Failed to generate optimization variants', err);
      setError('Variant generation failed. Check the AI backend and try again.');
    } finally {
      setGenerating(false);
    }
  }

  const currentBestTime = useMemo(
    () => bestTime?.recommendations.find((item) => item.network === network) ?? null,
    [bestTime, network]
  );
  const optimizationScore = useMemo(() => {
    const engagement = metrics ? (metrics.engagement / Math.max(1, metrics.reach)) * 100 : 0;
    const slotScore = currentBestTime?.best_slots[0]?.score ?? 0;
    const roiBoost = metrics ? Math.min(100, metrics.roiPercentage) : 0;
    return Math.round(engagement * 0.35 + slotScore * 0.4 + roiBoost * 0.25);
  }, [currentBestTime, metrics]);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <Link href="/studio/social-studio" style={styles.backLink}>
            ← Back to Hub
          </Link>
          <h1 style={styles.title}>AI Optimization</h1>
          <p style={styles.subtitle}>
            Score your posting windows, compare performance signals, and generate variants tuned for conversion.
          </p>
        </div>
        <div style={styles.pillRow}>
          <span style={styles.pill}>Optimization score: {optimizationScore}/100</span>
          <span style={styles.pill}>{currentBestTime?.timezone ?? 'UTC'}</span>
        </div>
      </div>

      <div style={styles.networkRow}>
        {NETWORK_OPTIONS.map((item) => (
          <button
            key={item}
            onClick={() => setNetwork(item)}
            style={{
              ...styles.networkButton,
              ...(network === item ? styles.networkButtonActive : {}),
            }}
          >
            {item}
          </button>
        ))}
      </div>

      {error ? <div style={styles.errorBanner}>{error}</div> : null}

      {loading ? (
        <div style={styles.loadingGrid}>
          <div style={styles.loadingCard} />
          <div style={styles.loadingCard} />
          <div style={styles.loadingCard} />
        </div>
      ) : (
        <>
          <section style={styles.grid}>
            <article style={styles.card}>
              <h2 style={styles.cardTitle}>Performance Snapshot</h2>
              <div style={styles.metricGrid}>
                <div style={styles.metricBox}>
                  <span style={styles.metricLabel}>Impressions</span>
                  <strong style={styles.metricValue}>{metrics?.impressions?.toLocaleString() ?? '0'}</strong>
                </div>
                <div style={styles.metricBox}>
                  <span style={styles.metricLabel}>Reach</span>
                  <strong style={styles.metricValue}>{metrics?.reach?.toLocaleString() ?? '0'}</strong>
                </div>
                <div style={styles.metricBox}>
                  <span style={styles.metricLabel}>Engagement</span>
                  <strong style={styles.metricValue}>{metrics?.engagement?.toLocaleString() ?? '0'}</strong>
                </div>
                <div style={styles.metricBox}>
                  <span style={styles.metricLabel}>ROI</span>
                  <strong style={styles.metricValue}>{metrics?.roiPercentage ?? 0}%</strong>
                </div>
              </div>
            </article>

            <article style={styles.card}>
              <h2 style={styles.cardTitle}>Best Posting Window</h2>
              {currentBestTime?.best_slots?.[0] ? (
                <>
                  <div style={styles.topSlot}>
                    <span
                      style={{ ...styles.slotBadge, background: scoreToTone(currentBestTime.best_slots[0].score) }}
                    />
                    <div>
                      <strong>
                        {currentBestTime.best_slots[0].day} at {currentBestTime.best_slots[0].hour}:00
                      </strong>
                      <p style={styles.cardText}>{currentBestTime.best_slots[0].reason}</p>
                    </div>
                  </div>
                  <div style={styles.metricGrid}>
                    <div style={styles.metricBox}>
                      <span style={styles.metricLabel}>Score</span>
                      <strong style={styles.metricValue}>{currentBestTime.best_slots[0].score}/100</strong>
                    </div>
                    <div style={styles.metricBox}>
                      <span style={styles.metricLabel}>Expected engagement</span>
                      <strong style={styles.metricValue}>{currentBestTime.best_slots[0].expected_engagement}%</strong>
                    </div>
                    <div style={styles.metricBox}>
                      <span style={styles.metricLabel}>Avoid</span>
                      <strong style={styles.metricValue}>
                        {currentBestTime.avoid_times.slice(0, 2).join(', ') || 'None'}
                      </strong>
                    </div>
                  </div>
                </>
              ) : (
                <p style={styles.cardText}>No best-time data returned for this network.</p>
              )}
            </article>

            <article style={styles.card}>
              <h2 style={styles.cardTitle}>Optimize Creative</h2>
              <div style={styles.formGrid}>
                <label style={styles.field}>
                  Topic <input style={styles.input} value={topic} onChange={(e) => setTopic(e.target.value)} />
                </label>
                <label style={styles.field}>
                  Goal <input style={styles.input} value={goal} onChange={(e) => setGoal(e.target.value)} />
                </label>
                <label style={styles.field}>
                  Audience <input style={styles.input} value={audience} onChange={(e) => setAudience(e.target.value)} />
                </label>
                <label style={styles.field}>
                  Style{' '}
                  <select style={styles.input} value={style} onChange={(e) => setStyle(e.target.value as typeof style)}>
                    {STYLE_OPTIONS.map((item) => (
                      <option key={item} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button style={styles.primaryButton} onClick={generateVariants} disabled={generating}>
                {generating ? 'Generating…' : 'Generate Variants'}
              </button>
            </article>
          </section>

          <section style={styles.card}>
            <h2 style={styles.cardTitle}>Generated Variants</h2>
            {generated ? (
              <div style={styles.variantGrid}>
                {generated.items.slice(0, 4).map((item) => (
                  <article key={item.variation_id} style={styles.variantCard}>
                    <div style={styles.variantHeader}>
                      <strong>{item.platform}</strong>
                      <span style={styles.variantQuality}>{item.quality.overall}/100</span>
                    </div>
                    <p style={styles.variantCaption}>{item.caption}</p>
                    <div style={styles.variantMeta}>
                      <span>Readability {item.quality.components.readability}</span>
                      <span>CTA {item.quality.components.cta_strength}</span>
                      <span>{item.hashtags.join(' ')}</span>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p style={styles.cardText}>Generate a batch to compare platform-specific variants.</p>
            )}
          </section>

          <section style={styles.card}>
            <h2 style={styles.cardTitle}>Recent Optimization History</h2>
            <div style={styles.historyList}>
              {history.length > 0 ? (
                history.map((run) => (
                  <article key={run.id} style={styles.historyCard}>
                    <div style={styles.variantHeader}>
                      <strong>{run.topic}</strong>
                      <span style={styles.variantQuality}>{run.provider}</span>
                    </div>
                    <p style={styles.cardText}>{run.goal}</p>
                    <div style={styles.variantMeta}>
                      <span>{run.platforms.join(', ')}</span>
                      <span>{run.generated_at}</span>
                    </div>
                  </article>
                ))
              ) : (
                <p style={styles.cardText}>No optimization history yet.</p>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

const styles: Record<string, CSSProperties> = {
  container: {
    minHeight: '100vh',
    padding: 24,
    display: 'grid',
    gap: 16,
    background: 'linear-gradient(180deg, #fff7ed 0%, var(--text) 100%)',
  },
  header: { display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', flexWrap: 'wrap' },
  backLink: { color: '#c2410c', textDecoration: 'none', fontWeight: 700 },
  title: { margin: '8px 0 4px', fontSize: 32, color: '#eef0f4' },
  subtitle: { margin: 0, color: '#e7e9ef' },
  pillRow: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  pill: {
    background: '#fff',
    border: '1px solid #fed7aa',
    borderRadius: 999,
    padding: '6px 12px',
    color: '#9a3412',
    fontWeight: 700,
  },
  networkRow: { display: 'flex', gap: 8, flexWrap: 'wrap' },
  networkButton: {
    border: '1px solid #fdba74',
    background: '#fff',
    color: '#9a3412',
    borderRadius: 999,
    padding: '8px 12px',
    cursor: 'pointer',
    fontWeight: 700,
    textTransform: 'capitalize',
  },
  networkButtonActive: { background: '#c2410c', color: '#fff', borderColor: '#c2410c' },
  errorBanner: {
    background: '#fee2e2',
    color: '#fee2e2',
    border: '1px solid #fecaca',
    borderRadius: 12,
    padding: '10px 12px',
  },
  loadingGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: 12 },
  loadingCard: {
    height: 180,
    borderRadius: 16,
    background: 'linear-gradient(90deg, var(--text) 0%, var(--text) 50%, var(--text) 100%)',
  },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 12 },
  card: { background: '#fff', border: '1px solid var(--text)', borderRadius: 16, padding: 16, display: 'grid', gap: 12 },
  cardTitle: { margin: 0, color: '#eef0f4' },
  cardText: { margin: 0, color: '#e7e9ef', lineHeight: 1.5 },
  metricGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 120px), 1fr))', gap: 10 },
  metricBox: {
    background: '#fff7ed',
    border: '1px solid #fed7aa',
    borderRadius: 12,
    padding: 12,
    display: 'grid',
    gap: 6,
  },
  metricLabel: { color: '#9a3412', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' },
  metricValue: { color: '#eef0f4', fontSize: 18 },
  topSlot: { display: 'flex', gap: 12, alignItems: 'center' },
  slotBadge: { width: 14, height: 14, borderRadius: '50%', flex: '0 0 auto' },
  formGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 10 },
  field: { display: 'grid', gap: 6, color: '#e7e9ef', fontWeight: 700, fontSize: 13 },
  input: { border: '1px solid var(--muted)', borderRadius: 10, padding: '9px 10px', fontSize: 14 },
  primaryButton: {
    border: 'none',
    borderRadius: 10,
    background: '#c2410c',
    color: '#fff',
    fontWeight: 800,
    padding: '10px 14px',
    cursor: 'pointer',
    width: 'fit-content',
  },
  variantGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: 12 },
  variantCard: {
    border: '1px solid #fed7aa',
    borderRadius: 16,
    background: '#fff7ed',
    padding: 14,
    display: 'grid',
    gap: 10,
  },
  variantHeader: { display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' },
  variantQuality: {
    background: '#fff',
    border: '1px solid #fdba74',
    borderRadius: 999,
    padding: '3px 10px',
    fontWeight: 700,
    color: '#9a3412',
  },
  variantCaption: { margin: 0, color: '#eef0f4', lineHeight: 1.5 },
  variantMeta: { display: 'flex', gap: 8, flexWrap: 'wrap', color: 'var(--muted)', fontSize: 12 },
  historyList: { display: 'grid', gap: 10 },
  historyCard: {
    border: '1px solid var(--text)',
    borderRadius: 12,
    padding: 12,
    display: 'grid',
    gap: 6,
    background: '#fff',
  },
};
