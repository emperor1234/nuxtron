'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────

type Sentiment = 'positive' | 'neutral' | 'negative';
type Platform = 'linkedin' | 'x' | 'instagram' | 'facebook' | 'reddit' | 'youtube' | 'news';
type CrisisLevel = 'none' | 'watch' | 'high' | 'critical';

interface Mention {
  id: number;
  platform: string;
  query: string;
  author_handle: string;
  text: string;
  sentiment: Sentiment;
  engagement_count: number;
  created_at: string;
}

interface AlertRule {
  id: number;
  name: string;
  query: string | null;
  platform: string | null;
  min_engagement: number;
  negative_only: boolean;
  enabled: boolean;
  created_at: string;
}

interface Alert {
  id: number;
  rule_name: string;
  mention_id: number;
  severity: 'medium' | 'high';
  status: 'open' | 'closed';
  created_at: string;
}

interface Cluster {
  query: string;
  platform: string;
  sentiment: Sentiment;
  mentions: number;
}

interface Summary {
  total_mentions: number;
  sentiment: { positive: number; neutral: number; negative: number };
  platforms: Record<string, number>;
  top_queries: { query: string; mentions: number }[];
  avg_engagement: number;
  clusters: { cluster: string; query: string; platform: string; mentions: number }[];
  alerts_open: number;
  crisis: {
    triggered: boolean;
    level: CrisisLevel;
    negative_ratio: number;
    high_negative_mentions: number;
  };
}

// ── Constants ─────────────────────────────────────────────────────────────────

const API_BASE = '/api/fastapi';
// Falls back to a dev tenant when NEXT_PUBLIC_DEFAULT_TENANT_ID is unset so the
// app runs locally without crashing.
const DEFAULT_TENANT = (process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID || 'default').trim();

const SENTIMENT_COLORS: Record<Sentiment, string> = {
  positive: '#26d78e',
  neutral: '#1bc7ff',
  negative: '#f87171',
};

const CRISIS_COLORS: Record<CrisisLevel, string> = {
  none: '#26d78e',
  watch: '#f59e0b',
  high: '#f97316',
  critical: '#ef4444',
};

const PLATFORM_ICONS: Record<string, string> = {
  linkedin: '💼',
  x: '𝕏',
  instagram: '📸',
  facebook: '👥',
  reddit: '🟠',
  youtube: '▶️',
  news: '📰',
};

// ── Helpers ───────────────────────────────────────────────────────────────────

async function apiFetch(path: string, tenantId: string, opts?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-Id': tenantId,
      ...(opts?.headers ?? {}),
    },
  });
  const data = await res.json();
  if (!res.ok) throw new Error((data?.detail as string) ?? `HTTP ${res.status}`);
  return data;
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Card({ children, style }: Readonly<{ children: React.ReactNode; style?: React.CSSProperties }>) {
  return (
    <div
      style={{
        background: 'var(--bg-soft)',
        border: '1px solid var(--line)',
        borderRadius: 12,
        padding: '20px 24px',
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function SectionTitle({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <h2
      style={{
        margin: '0 0 16px',
        fontSize: 15,
        fontWeight: 600,
        color: 'var(--brand)',
        textTransform: 'uppercase',
        letterSpacing: '0.07em',
      }}
    >
      {children}
    </h2>
  );
}

function Pill({ label, color, small }: Readonly<{ label: string; color: string; small?: boolean }>) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: small ? '2px 8px' : '4px 10px',
        borderRadius: 99,
        fontSize: small ? 11 : 12,
        fontWeight: 600,
        background: `${color}22`,
        color,
        border: `1px solid ${color}55`,
      }}
    >
      {label}
    </span>
  );
}

function StatCard({
  label,
  value,
  sub,
  accent,
}: Readonly<{ label: string; value: string | number; sub?: string; accent?: string }>) {
  return (
    <Card>
      <div style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 6 }}>{label}</div>
      <div
        style={{
          fontSize: 28,
          fontWeight: 700,
          color: accent ?? 'var(--text)',
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>{sub}</div>}
    </Card>
  );
}

function SentimentDonut({ sentiment }: Readonly<{ sentiment: Summary['sentiment'] }>) {
  const total = sentiment.positive + sentiment.neutral + sentiment.negative;
  if (total === 0)
    return (
      <svg viewBox="0 0 120 120" width={120} height={120}>
        <circle cx={60} cy={60} r={50} fill="none" stroke="var(--line)" strokeWidth={20} />
        <text x={60} y={66} textAnchor="middle" fontSize={14} fill="var(--muted)">
          No data
        </text>
      </svg>
    );

  const R = 50;
  const cx = 60;
  const cy = 60;
  const gap = 4;
  const segments: { key: Sentiment; count: number }[] = [
    { key: 'positive', count: sentiment.positive },
    { key: 'neutral', count: sentiment.neutral },
    { key: 'negative', count: sentiment.negative },
  ];

  let startAngle = -Math.PI / 2;
  const paths: React.ReactNode[] = [];

  for (const seg of segments) {
    if (seg.count === 0) continue;
    const frac = seg.count / total;
    const sweep = frac * 2 * Math.PI - (gap * Math.PI) / 180;
    const endAngle = startAngle + sweep;
    const x1 = cx + R * Math.cos(startAngle);
    const y1 = cy + R * Math.sin(startAngle);
    const x2 = cx + R * Math.cos(endAngle);
    const y2 = cy + R * Math.sin(endAngle);
    const largeArc = sweep > Math.PI ? 1 : 0;
    paths.push(
      <path
        key={seg.key}
        d={`M ${x1} ${y1} A ${R} ${R} 0 ${largeArc} 1 ${x2} ${y2}`}
        fill="none"
        stroke={SENTIMENT_COLORS[seg.key]}
        strokeWidth={20}
        strokeLinecap="round"
      />
    );
    startAngle = endAngle + (gap * Math.PI) / 180;
  }

  const negPct = total > 0 ? Math.round((sentiment.negative / total) * 100) : 0;

  return (
    <svg viewBox="0 0 120 120" width={120} height={120}>
      {paths}
      <text x={60} y={57} textAnchor="middle" fontSize={18} fontWeight="700" fill="var(--text)">
        {negPct}%
      </text>
      <text x={60} y={72} textAnchor="middle" fontSize={10} fill="var(--muted)">
        negative
      </text>
    </svg>
  );
}

function CrisisBadge({ level }: Readonly<{ level: CrisisLevel }>) {
  const labels: Record<CrisisLevel, string> = {
    none: '✅ No Crisis',
    watch: '⚠️ Watch',
    high: '🔥 High Risk',
    critical: '🚨 CRITICAL',
  };
  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '6px 14px',
        borderRadius: 99,
        fontWeight: 700,
        fontSize: 13,
        color: CRISIS_COLORS[level],
        background: `${CRISIS_COLORS[level]}18`,
        border: `1.5px solid ${CRISIS_COLORS[level]}55`,
      }}
    >
      {labels[level]}
    </div>
  );
}

function BarRow({
  label,
  value,
  max,
  color,
  extra,
}: Readonly<{ label: string; value: number; max: number; color: string; extra?: string }>) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div style={{ marginBottom: 10 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 12,
          color: 'var(--muted)',
          marginBottom: 4,
        }}
      >
        <span>{label}</span>
        <span>
          {value} {extra}
        </span>
      </div>
      <div
        style={{
          height: 6,
          borderRadius: 3,
          background: 'var(--line)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: color,
            borderRadius: 3,
            transition: 'width 0.4s',
          }}
        />
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function SocialListeningPage() {
  const [tenantId] = useState(DEFAULT_TENANT);

  // Data state
  const [summary, setSummary] = useState<Summary | null>(null);
  const [mentions, setMentions] = useState<Mention[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [clusters, setClusters] = useState<Cluster[]>([]);
  const [rules, setRules] = useState<AlertRule[]>([]);

  // UI state
  const [tab, setTab] = useState<'overview' | 'mentions' | 'alerts' | 'rules' | 'ingest'>('overview');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Ingest form
  const [ingestPlatform, setIngestPlatform] = useState<Platform>('linkedin');
  const [ingestQuery, setIngestQuery] = useState('brand reputation');
  const [ingestHandle, setIngestHandle] = useState('@user');
  const [ingestText, setIngestText] = useState('');
  const [ingestSentiment, setIngestSentiment] = useState<Sentiment>('neutral');
  const [ingestEngagement, setIngestEngagement] = useState('0');

  // Alert rule form
  const [ruleName, setRuleName] = useState('');
  const [ruleQuery, setRuleQuery] = useState('');
  const [rulePlatform, setRulePlatform] = useState('');
  const [ruleMinEngagement, setRuleMinEngagement] = useState('20');
  const [ruleNegOnly, setRuleNegOnly] = useState(true);

  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [sumRes, mentRes, alertRes, clusterRes] = await Promise.all([
        apiFetch('/social/listening/summary', tenantId),
        apiFetch('/social/listening/mentions', tenantId),
        apiFetch('/social/listening/alerts', tenantId),
        apiFetch('/social/listening/clusters', tenantId),
      ]);
      setSummary(sumRes.summary as Summary);
      setMentions((mentRes.mentions as Mention[]) ?? []);
      setAlerts((alertRes.alerts as Alert[]) ?? []);
      setClusters((clusterRes.clusters as Cluster[]) ?? []);
    } catch {
      // silently ignore background refresh errors
    }
  }, [tenantId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadAll();
    refreshTimer.current = setInterval(loadAll, 30_000);
    return () => {
      if (refreshTimer.current) clearInterval(refreshTimer.current);
    };
  }, [loadAll]);

  const notify = (msg: string, isError = false) => {
    if (isError) {
      setError(msg);
      setSuccess('');
    } else {
      setSuccess(msg);
      setError('');
    }
    setTimeout(() => {
      setError('');
      setSuccess('');
    }, 4000);
  };

  async function handleIngest() {
    if (!ingestText.trim()) {
      notify('Mention text is required.', true);
      return;
    }
    setLoading(true);
    try {
      await apiFetch('/social/listening/ingest', tenantId, {
        method: 'POST',
        body: JSON.stringify({
          platform: ingestPlatform,
          query: ingestQuery,
          author_handle: ingestHandle,
          text: ingestText,
          sentiment: ingestSentiment,
          engagement_count: Math.max(0, Number.parseInt(ingestEngagement, 10) || 0),
        }),
      });
      setIngestText('');
      notify('Mention ingested successfully.');
      await loadAll();
    } catch (e: unknown) {
      notify((e as Error).message, true);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateRule() {
    if (!ruleName.trim()) {
      notify('Rule name is required.', true);
      return;
    }
    setLoading(true);
    try {
      const res = await apiFetch('/social/listening/rules', tenantId, {
        method: 'POST',
        body: JSON.stringify({
          name: ruleName,
          query: ruleQuery || null,
          platform: rulePlatform || null,
          min_engagement: Math.max(0, Number.parseInt(ruleMinEngagement, 10) || 0),
          negative_only: ruleNegOnly,
        }),
      });
      setRules((prev) => [res.rule as AlertRule, ...prev]);
      setRuleName('');
      setRuleQuery('');
      setRulePlatform('');
      notify('Alert rule created.');
    } catch (e: unknown) {
      notify((e as Error).message, true);
    } finally {
      setLoading(false);
    }
  }

  // ── Styles ────────────────────────────────────────────────────────────────

  const page: React.CSSProperties = {
    minHeight: '100vh',
    background: 'var(--bg)',
    color: 'var(--text)',
    padding: '32px 24px',
    fontFamily: 'var(--font-geist-sans, system-ui, sans-serif)',
  };

  const container: React.CSSProperties = {
    maxWidth: 1080,
    margin: '0 auto',
  };

  const tabBar: React.CSSProperties = {
    display: 'flex',
    gap: 4,
    marginBottom: 28,
    borderBottom: '1px solid var(--line)',
    paddingBottom: 0,
  };

  const tabBtn = (active: boolean): React.CSSProperties => ({
    padding: '8px 18px',
    borderRadius: '8px 8px 0 0',
    border: 'none',
    background: active ? 'var(--brand)' : 'transparent',
    color: active ? '#000' : 'var(--muted)',
    fontWeight: active ? 700 : 500,
    fontSize: 13,
    cursor: 'pointer',
    transition: 'all 0.15s',
  });

  const input: React.CSSProperties = {
    width: '100%',
    padding: '8px 12px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
    fontSize: 13,
    marginBottom: 10,
    boxSizing: 'border-box',
  };

  const select: React.CSSProperties = { ...input };

  const btn: React.CSSProperties = {
    padding: '9px 20px',
    borderRadius: 8,
    border: 'none',
    background: 'var(--brand)',
    color: '#000',
    fontWeight: 700,
    fontSize: 13,
    cursor: loading ? 'not-allowed' : 'pointer',
    opacity: loading ? 0.6 : 1,
  };

  const grid2: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
    gap: 16,
    marginBottom: 20,
  };

  const grid4: React.CSSProperties = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 170px), 1fr))',
    gap: 16,
    marginBottom: 20,
  };

  // ── Tab content ───────────────────────────────────────────────────────────

  const openAlerts = alerts.filter((a) => a.status === 'open');
  const criticalAlerts = openAlerts.filter((a) => a.severity === 'high');

  const platformMax = summary ? Math.max(...Object.values(summary.platforms), 1) : 1;

  return (
    <div style={page}>
      <div style={container}>
        {/* Header */}
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <div
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                background: 'linear-gradient(135deg, #1bc7ff, #26d78e)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 20,
              }}
            >
              📡
            </div>
            <div>
              <h1
                style={{
                  margin: 0,
                  fontSize: 24,
                  fontWeight: 800,
                  background: 'linear-gradient(90deg, var(--brand), var(--brand-2))',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                }}
              >
                Social Listening
              </h1>
              <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)' }}>
                Real-time brand monitoring · Sentiment analysis · Crisis detection · Alert rules
              </p>
            </div>
            {summary && (
              <div style={{ marginLeft: 'auto' }}>
                <CrisisBadge level={summary.crisis.level} />
              </div>
            )}
          </div>
        </div>

        {/* Toast */}
        {(error || success) && (
          <div
            style={{
              padding: '10px 16px',
              borderRadius: 8,
              marginBottom: 16,
              background: error ? '#ef444422' : '#26d78e22',
              border: `1px solid ${error ? '#ef4444' : '#26d78e'}55`,
              color: error ? '#ef4444' : '#26d78e',
              fontSize: 13,
            }}
          >
            {error || success}
          </div>
        )}

        {/* Stat bar */}
        <div style={grid4}>
          <StatCard
            label="Total Mentions"
            value={summary?.total_mentions ?? '—'}
            sub={summary ? `${summary.alerts_open} open alerts` : undefined}
          />
          <StatCard
            label="Negative Ratio"
            value={summary ? `${Math.round(summary.crisis.negative_ratio * 100)}%` : '—'}
            sub="sentiment score"
            accent={summary ? CRISIS_COLORS[summary.crisis.level] : 'var(--text)'}
          />
          <StatCard
            label="Avg Engagement"
            value={summary?.avg_engagement ?? '—'}
            sub="per mention"
            accent="var(--brand)"
          />
          <StatCard
            label="Critical Alerts"
            value={criticalAlerts.length}
            sub={`${openAlerts.length} total open`}
            accent={criticalAlerts.length > 0 ? '#ef4444' : 'var(--brand-2)'}
          />
        </div>

        {/* Tab bar */}
        <div style={tabBar}>
          {(['overview', 'mentions', 'alerts', 'rules', 'ingest'] as const).map((t) => (
            <button key={t} style={tabBtn(tab === t)} onClick={() => setTab(t)}>
              {t === 'overview' && '📊 '}
              {t === 'mentions' && '💬 '}
              {t === 'alerts' && '🔔 '}
              {t === 'rules' && '⚙️ '}
              {t === 'ingest' && '➕ '}
              {t.charAt(0).toUpperCase() + t.slice(1)}
              {t === 'alerts' && openAlerts.length > 0 && (
                <span
                  style={{
                    marginLeft: 6,
                    background: '#ef4444',
                    color: '#fff',
                    borderRadius: 99,
                    fontSize: 10,
                    padding: '1px 5px',
                  }}
                >
                  {openAlerts.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ── Overview tab ─────────────────────────────────────────────────── */}
        {tab === 'overview' && (
          <div>
            <div style={grid2}>
              {/* Sentiment donut */}
              <Card>
                <SectionTitle>Sentiment Breakdown</SectionTitle>
                <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                  <SentimentDonut sentiment={summary?.sentiment ?? { positive: 0, neutral: 0, negative: 0 }} />
                  <div style={{ flex: 1 }}>
                    {(['positive', 'neutral', 'negative'] as Sentiment[]).map((s) => (
                      <div
                        key={s}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: 13,
                          marginBottom: 8,
                        }}
                      >
                        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span
                            style={{
                              width: 10,
                              height: 10,
                              borderRadius: '50%',
                              background: SENTIMENT_COLORS[s],
                              display: 'inline-block',
                            }}
                          />
                          {s.charAt(0).toUpperCase() + s.slice(1)}
                        </span>
                        <span style={{ fontWeight: 600 }}>{summary?.sentiment[s] ?? 0}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>

              {/* Platform breakdown */}
              <Card>
                <SectionTitle>Platform Breakdown</SectionTitle>
                {summary && Object.keys(summary.platforms).length === 0 && (
                  <p style={{ color: 'var(--muted)', fontSize: 13 }}>No mentions yet.</p>
                )}
                {summary &&
                  Object.entries(summary.platforms)
                    .sort(([, a], [, b]) => b - a)
                    .map(([platform, count]) => (
                      <BarRow
                        key={platform}
                        label={`${PLATFORM_ICONS[platform] ?? '🌐'} ${platform}`}
                        value={count}
                        max={platformMax}
                        color="var(--brand)"
                        extra="mentions"
                      />
                    ))}
              </Card>
            </div>

            {/* Top queries */}
            <Card style={{ marginBottom: 16 }}>
              <SectionTitle>Top Tracked Queries</SectionTitle>
              {!summary || summary.top_queries.length === 0 ? (
                <p style={{ color: 'var(--muted)', fontSize: 13 }}>No queries tracked yet.</p>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                  {summary.top_queries.map((q, i) => (
                    <div
                      key={`item-${i}`}
                      style={{
                        padding: '8px 14px',
                        borderRadius: 8,
                        background: 'var(--bg)',
                        border: '1px solid var(--line)',
                        fontSize: 13,
                      }}
                    >
                      <span style={{ fontWeight: 600 }}>{q.query}</span>
                      <span
                        style={{
                          marginLeft: 8,
                          color: 'var(--brand)',
                          fontWeight: 700,
                        }}
                      >
                        {q.mentions}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Clusters */}
            <Card>
              <SectionTitle>Mention Clusters</SectionTitle>
              {clusters.length === 0 ? (
                <p style={{ color: 'var(--muted)', fontSize: 13 }}>
                  No clusters yet — ingest mentions to see patterns.
                </p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                    <thead>
                      <tr style={{ color: 'var(--muted)', textAlign: 'left' }}>
                        {['Query', 'Platform', 'Sentiment', 'Mentions'].map((h) => (
                          <th
                            key={h}
                            style={{ padding: '6px 12px', borderBottom: '1px solid var(--line)', fontWeight: 600 }}
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {clusters.slice(0, 20).map((c, i) => (
                        <tr key={`item-${i}`} style={{ borderBottom: '1px solid var(--line)' }}>
                          <td style={{ padding: '8px 12px' }}>{c.query}</td>
                          <td style={{ padding: '8px 12px' }}>
                            {PLATFORM_ICONS[c.platform] ?? '🌐'} {c.platform}
                          </td>
                          <td style={{ padding: '8px 12px' }}>
                            <Pill
                              label={c.sentiment}
                              color={SENTIMENT_COLORS[c.sentiment as Sentiment] ?? 'var(--muted)'}
                              small
                            />
                          </td>
                          <td style={{ padding: '8px 12px', fontWeight: 700 }}>{c.mentions}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* ── Mentions tab ─────────────────────────────────────────────────── */}
        {tab === 'mentions' && (
          <Card>
            <SectionTitle>Live Mentions Feed ({mentions.length})</SectionTitle>
            {mentions.length === 0 ? (
              <p style={{ color: 'var(--muted)', fontSize: 13 }}>
                No mentions yet. Use the Ingest tab or a webhook to stream mentions.
              </p>
            ) : (
              <div>
                {mentions.map((m) => (
                  <div
                    key={m.id}
                    style={{
                      padding: '12px 0',
                      borderBottom: '1px solid var(--line)',
                      display: 'grid',
                      gridTemplateColumns: '1fr auto',
                      gap: 12,
                    }}
                  >
                    <div>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          marginBottom: 4,
                          flexWrap: 'wrap',
                        }}
                      >
                        <span style={{ fontWeight: 600, fontSize: 13 }}>{m.author_handle}</span>
                        <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                          {PLATFORM_ICONS[m.platform] ?? '🌐'} {m.platform}
                        </span>
                        <Pill label={m.sentiment} color={SENTIMENT_COLORS[m.sentiment]} small />
                        {m.engagement_count > 0 && (
                          <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                            ❤️ {m.engagement_count.toLocaleString()}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.5 }}>{m.text}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                        Query: <strong>{m.query}</strong> · {timeAgo(m.created_at)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        )}

        {/* ── Alerts tab ───────────────────────────────────────────────────── */}
        {tab === 'alerts' && (
          <Card>
            <SectionTitle>Active Alerts ({openAlerts.length} open)</SectionTitle>
            {alerts.length === 0 ? (
              <p style={{ color: 'var(--muted)', fontSize: 13 }}>
                No alerts fired yet. Create alert rules and ingest negative high-engagement mentions to trigger them.
              </p>
            ) : (
              alerts.map((a) => (
                <div
                  key={a.id}
                  style={{
                    padding: '12px 14px',
                    borderRadius: 8,
                    marginBottom: 10,
                    background: a.severity === 'high' ? '#ef444411' : '#f59e0b11',
                    border: `1px solid ${a.severity === 'high' ? '#ef444444' : '#f59e0b44'}`,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: 12,
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: 13,
                        color: a.severity === 'high' ? '#ef4444' : '#f59e0b',
                        marginBottom: 2,
                      }}
                    >
                      {a.severity === 'high' ? '🔴 HIGH' : '🟡 MEDIUM'} — {a.rule_name}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      Mention #{a.mention_id} · {timeAgo(a.created_at)}
                    </div>
                  </div>
                  <Pill label={a.status} color={a.status === 'open' ? '#ef4444' : '#26d78e'} small />
                </div>
              ))
            )}
          </Card>
        )}

        {/* ── Rules tab ────────────────────────────────────────────────────── */}
        {tab === 'rules' && (
          <div style={grid2}>
            {/* Create rule form */}
            <Card>
              <SectionTitle>Create Alert Rule</SectionTitle>
              <label style={{ fontSize: 12, color: 'var(--muted)' }}>Rule Name *</label>
              <input
                style={input}
                placeholder="e.g. Brand crisis monitor"
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
              />
              <label style={{ fontSize: 12, color: 'var(--muted)' }}>Track Query (optional)</label>
              <input
                style={input}
                placeholder="e.g. brand name, product name"
                value={ruleQuery}
                onChange={(e) => setRuleQuery(e.target.value)}
              />
              <label style={{ fontSize: 12, color: 'var(--muted)' }}>Platform filter (optional)</label>
              <select style={select} value={rulePlatform} onChange={(e) => setRulePlatform(e.target.value)}>
                <option value="">All platforms</option>
                {(['linkedin', 'x', 'instagram', 'facebook', 'reddit', 'youtube', 'news'] as Platform[]).map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <label style={{ fontSize: 12, color: 'var(--muted)' }}>Min Engagement</label>
              <input
                style={input}
                type="number"
                value={ruleMinEngagement}
                onChange={(e) => setRuleMinEngagement(e.target.value)}
              />
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 14,
                }}
              >
                <input
                  type="checkbox"
                  id="negOnly"
                  checked={ruleNegOnly}
                  onChange={(e) => setRuleNegOnly(e.target.checked)}
                />
                <label htmlFor="negOnly" style={{ fontSize: 13 }}>
                  Negative mentions only
                </label>
              </div>
              <button style={btn} disabled={loading} onClick={handleCreateRule}>
                {loading ? 'Creating…' : 'Create Alert Rule'}
              </button>
            </Card>

            {/* Existing rules */}
            <Card>
              <SectionTitle>Existing Rules ({rules.length})</SectionTitle>
              {rules.length === 0 ? (
                <p style={{ color: 'var(--muted)', fontSize: 13 }}>No rules yet.</p>
              ) : (
                rules.map((r) => (
                  <div
                    key={r.id}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 8,
                      marginBottom: 8,
                      background: 'var(--bg)',
                      border: '1px solid var(--line)',
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{r.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>
                      {r.query ? `Query: ${r.query} · ` : ''}
                      {r.platform ? `Platform: ${r.platform} · ` : ''}
                      Min engagement: {r.min_engagement} ·{r.negative_only ? ' Negative only' : ' All sentiment'}
                    </div>
                    <div style={{ marginTop: 4 }}>
                      <Pill
                        label={r.enabled ? 'Active' : 'Disabled'}
                        color={r.enabled ? '#26d78e' : 'var(--muted)'}
                        small
                      />
                    </div>
                  </div>
                ))
              )}
            </Card>
          </div>
        )}

        {/* ── Ingest tab ───────────────────────────────────────────────────── */}
        {tab === 'ingest' && (
          <Card style={{ maxWidth: 560 }}>
            <SectionTitle>Ingest Mention</SectionTitle>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 14 }}>
              Manually add a mention or use this as a webhook target for live platform data.
            </p>

            <label style={{ fontSize: 12, color: 'var(--muted)' }}>Platform</label>
            <select
              style={select}
              value={ingestPlatform}
              onChange={(e) => setIngestPlatform(e.target.value as Platform)}
            >
              {(['linkedin', 'x', 'instagram', 'facebook', 'reddit', 'youtube', 'news'] as Platform[]).map((p) => (
                <option key={p} value={p}>
                  {PLATFORM_ICONS[p]} {p}
                </option>
              ))}
            </select>

            <label style={{ fontSize: 12, color: 'var(--muted)' }}>Tracked Query</label>
            <input
              style={input}
              placeholder="e.g. brand name"
              value={ingestQuery}
              onChange={(e) => setIngestQuery(e.target.value)}
            />

            <label style={{ fontSize: 12, color: 'var(--muted)' }}>Author Handle</label>
            <input
              style={input}
              placeholder="@user"
              value={ingestHandle}
              onChange={(e) => setIngestHandle(e.target.value)}
            />

            <label style={{ fontSize: 12, color: 'var(--muted)' }}>Mention Text *</label>
            <textarea
              style={{ ...input, height: 80, resize: 'vertical' }}
              placeholder="Paste the mention content here…"
              value={ingestText}
              onChange={(e) => setIngestText(e.target.value)}
            />

            <label style={{ fontSize: 12, color: 'var(--muted)' }}>Sentiment</label>
            <select
              style={select}
              value={ingestSentiment}
              onChange={(e) => setIngestSentiment(e.target.value as Sentiment)}
            >
              <option value="positive">😊 Positive</option>
              <option value="neutral">😐 Neutral</option>
              <option value="negative">😠 Negative</option>
            </select>

            <label style={{ fontSize: 12, color: 'var(--muted)' }}>Engagement Count</label>
            <input
              style={input}
              type="number"
              value={ingestEngagement}
              onChange={(e) => setIngestEngagement(e.target.value)}
              placeholder="0"
            />

            <button style={btn} disabled={loading} onClick={handleIngest}>
              {loading ? 'Ingesting…' : 'Ingest Mention'}
            </button>

            <div
              style={{
                marginTop: 20,
                padding: '12px 14px',
                borderRadius: 8,
                background: 'var(--bg)',
                border: '1px solid var(--line)',
                fontSize: 12,
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--brand)' }}>Webhook / API Endpoint</div>
              <code style={{ color: 'var(--muted)', wordBreak: 'break-all' }}>
                POST {API_BASE}/social/listening/ingest
              </code>
              <pre
                style={{
                  marginTop: 8,
                  fontSize: 11,
                  color: 'var(--muted)',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                }}
              >{`{
  "platform": "linkedin",
  "query": "brand name",
  "author_handle": "@user",
  "text": "mention content",
  "sentiment": "negative",
  "engagement_count": 150
}`}</pre>
            </div>
          </Card>
        )}

        {/* Auto-refresh indicator */}
        <div
          style={{
            marginTop: 24,
            textAlign: 'center',
            fontSize: 11,
            color: 'var(--muted)',
          }}
        >
          Auto-refreshes every 30s · {summary ? `${summary.total_mentions} total mentions tracked` : 'Loading…'}
        </div>
      </div>
    </div>
  );
}
