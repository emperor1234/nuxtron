'use client';

import { useState, useCallback, useMemo } from 'react';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  RefreshCw,
  Download,
  Filter,
  Search,
  ChevronUp,
  ChevronDown,
  BarChart2,
  Zap,
  Target,
  Globe,
  Clock,
  Eye,
  Bell,
  Trophy,
} from 'lucide-react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type RankHistory = {
  keyword: string;
  current_position: number;
  previous_position?: number;
  trend: 'up' | 'down' | 'flat';
  position_change: number;
  '30d_trend': string;
  search_volume?: number;
  difficulty?: number;
  url?: string;
};
type KeyMovement = { keyword: string; movement: string; likely_cause: string };
type TrendForecast = { direction: string; confidence: number; forecast_horizon_days: number; key_drivers: string[] };
type RankResult = {
  analysis_id: string;
  tracking_score: number;
  volatile_keywords: string[];
  ranking_history: RankHistory[];
  volatility_index: number;
  key_movements: KeyMovement[];
  competitor_movements: { competitor: string; keyword: string; change: number }[];
  trend_forecast: TrendForecast;
  alert_triggers: string[];
  next_actions: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

type ScoreGaugeProps = Readonly<{ score: number; label: string; size?: number }>;
type VolatilityBarProps = Readonly<{ value: number }>;
type StatCardProps = Readonly<{
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}>;
type PosBadgeProps = Readonly<{ pos: number; change: number }>;

const RANK_AUDIT_PHASES = [
  'Set domain, keyword universe, and lookback scope',
  'Detect movement patterns and volatility signals',
  'Prioritize response actions and forecasting strategy',
];

function getScoreColor(score: number): string {
  if (score >= 75) return '#26d78e';
  if (score >= 50) return '#ffb867';
  return '#dc2626';
}

function getVolatilityMeta(value: number): { color: string; label: string } {
  if (value >= 0.7) return { color: '#dc2626', label: 'High' };
  if (value >= 0.4) return { color: '#ffb867', label: 'Medium' };
  return { color: '#26d78e', label: 'Low' };
}

function getChangeColor(change: number): string {
  if (change > 0) return '#26d78e';
  if (change < 0) return '#dc2626';
  return 'var(--muted)';
}

function getPositionColor(pos: number): string {
  if (pos <= 3) return '#ffb867';
  if (pos <= 10) return '#26d78e';
  return 'var(--text)';
}

function getTrendDirectionMeta(direction: string): { color: string; label: string } {
  if (direction === 'up') return { color: '#26d78e', label: '📈 Upward' };
  if (direction === 'down') return { color: '#dc2626', label: '📉 Downward' };
  return { color: 'var(--muted)', label: '➡️ Stable' };
}

function ScoreGauge({ score, label, size = 100 }: ScoreGaugeProps) {
  const radius = size * 0.36,
    stroke = size * 0.07,
    circumference = Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  const color = getScoreColor(score);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg width={size} height={size * 0.6} viewBox={`0 0 ${size} ${size * 0.6}`}>
        <path
          d={`M ${stroke} ${size * 0.56} A ${radius} ${radius} 0 0 1 ${size - stroke} ${size * 0.56}`}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        <path
          d={`M ${stroke} ${size * 0.56} A ${radius} ${radius} 0 0 1 ${size - stroke} ${size * 0.56}`}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
        <text
          x={size / 2}
          y={size * 0.48}
          textAnchor="middle"
          fill={color}
          style={{ fontSize: size * 0.22, fontWeight: 800 }}
        >
          {score}
        </text>
      </svg>
      <span
        style={{
          fontSize: 11,
          color: 'var(--muted)',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
        }}
      >
        {label}
      </span>
    </div>
  );
}

function VolatilityBar({ value }: VolatilityBarProps) {
  const { color, label } = getVolatilityMeta(value);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${Math.round(value * 100)}%`,
            background: color,
            borderRadius: 3,
            transition: 'width 0.6s ease',
          }}
        />
      </div>
      <span style={{ fontSize: 11, color, fontWeight: 700, minWidth: 44 }}>{label}</span>
    </div>
  );
}

function StatCard({ icon, label, value, sub, color }: StatCardProps) {
  return (
    <div
      style={{ background: 'var(--bg-soft)', border: '1px solid var(--line)', borderRadius: 12, padding: '16px 20px' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <span style={{ color: color ?? 'var(--brand)' }}>{icon}</span>
        <span
          style={{
            fontSize: 11,
            color: 'var(--muted)',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
          }}
        >
          {label}
        </span>
      </div>
      <div style={{ fontSize: 26, fontWeight: 800, color: color ?? 'var(--text)', lineHeight: 1 }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function PosBadge({ pos, change }: PosBadgeProps) {
  const color = getChangeColor(change);
  let Icon = Minus;
  if (change > 0) {
    Icon = ChevronUp;
  } else if (change < 0) {
    Icon = ChevronDown;
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span
        style={{
          fontWeight: 700,
          fontFamily: 'monospace',
          fontSize: 15,
          color: getPositionColor(pos),
        }}
      >
        #{pos}
      </span>
      {change !== 0 && (
        <span style={{ display: 'flex', alignItems: 'center', gap: 2, fontSize: 11, color, fontWeight: 700 }}>
          <Icon size={11} strokeWidth={2.5} />
          {Math.abs(change)}
        </span>
      )}
    </div>
  );
}

export default function RankTrackingPage() {
  const [domain, setDomain] = useState('');
  const [trackedKeywords, setTrackedKeywords] = useState('');
  const [lookbackPeriod, setLookbackPeriod] = useState('30');
  const [includeCompetitor, setIncludeCompetitor] = useState(false);
  const [competitorDomains, setCompetitorDomains] = useState('');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<RankResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'keywords' | 'movements' | 'forecast'>('overview');
  const [sortKey, setSortKey] = useState<'current_position' | 'position_change' | 'keyword'>('current_position');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [kwFilter, setKwFilter] = useState('');

  const handleSort = (key: typeof sortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  async function runTracking() {
    if (!domain || !trackedKeywords) {
      setError('Domain and keywords are required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const kws = trackedKeywords
        .split('\n')
        .map((k) => k.trim())
        .filter(Boolean);
      const comps = includeCompetitor
        ? competitorDomains
            .split('\n')
            .map((d) => d.trim())
            .filter(Boolean)
        : [];
      const data = await apiSend<RankResult>(
        '/seo-platform/rank-tracking/analyze',
        'POST',
        {
          domain,
          tracked_keywords: kws,
          historical_lookback_days: Number.parseInt(lookbackPeriod, 10),
          include_competitor_tracking: includeCompetitor,
          competitor_domains: comps,
          notes,
        },
        DEFAULT_TENANT_ID
      );
      if (data?.fallback === true && data?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }
      setResult(data);
      setActiveTab('overview');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Tracking failed');
    } finally {
      setLoading(false);
    }
  }

  const sortedKeywords = useMemo(() => {
    if (!result?.ranking_history) return [];
    const filtered = result.ranking_history.filter(
      (r) => !kwFilter || r.keyword.toLowerCase().includes(kwFilter.toLowerCase())
    );
    return [...filtered].sort((a, b) => {
      if (sortKey === 'keyword')
        return sortDir === 'asc' ? a.keyword.localeCompare(b.keyword) : b.keyword.localeCompare(a.keyword);
      if (sortKey === 'position_change')
        return sortDir === 'asc' ? a.position_change - b.position_change : b.position_change - a.position_change;
      return sortDir === 'asc' ? a.current_position - b.current_position : b.current_position - a.current_position;
    });
  }, [result, sortKey, sortDir, kwFilter]);

  const exportCSV = useCallback(() => {
    if (!result?.ranking_history) return;
    const rows = result.ranking_history.map(
      (r) => `"${r.keyword}",${r.current_position},${r.position_change},"${r.trend}","${r['30d_trend']}"`
    );
    const blob = new Blob(['Keyword,Position,Change,Trend,30d Trend\n' + rows.join('\n')], { type: 'text/csv' });
    const a = Object.assign(document.createElement('a'), {
      href: URL.createObjectURL(blob),
      download: `rank-tracking-${domain}.csv`,
    });
    a.click();
    URL.revokeObjectURL(a.href);
  }, [result, domain]);

  const card: React.CSSProperties = {
    background: '#ffffff',
    border: '1px solid rgba(148, 163, 184, 0.16)',
    borderRadius: 16,
    padding: '20px 24px',
    marginBottom: 20,
    backdropFilter: 'blur(12px)',
    boxShadow: '0 20px 60px -45px rgba(59, 130, 246, 0.65)',
  };
  const input: React.CSSProperties = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: 12,
    border: '1px solid rgba(148, 163, 184, 0.22)',
    background: '#ffffff',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box',
    fontSize: 14,
  };
  const th: React.CSSProperties = {
    textAlign: 'left',
    padding: '8px 12px',
    fontSize: 11,
    fontWeight: 700,
    textTransform: 'uppercase',
    color: 'var(--muted)',
    borderBottom: '1px solid var(--line)',
    cursor: 'pointer',
    userSelect: 'none',
  };
  const td: React.CSSProperties = { padding: '10px 12px', fontSize: 13, borderBottom: '1px solid var(--line)' };

  const top3 = result?.ranking_history?.filter((r) => r.current_position <= 3).length ?? 0;
  const top10 = result?.ranking_history?.filter((r) => r.current_position <= 10).length ?? 0;
  const gainers = result?.ranking_history?.filter((r) => r.position_change > 0).length ?? 0;
  const losers = result?.ranking_history?.filter((r) => r.position_change < 0).length ?? 0;
  const tabs = [
    { key: 'overview' as const, label: 'Overview', icon: <BarChart2 size={13} /> },
    {
      key: 'keywords' as const,
      label: `Keywords (${result?.ranking_history?.length ?? 0})`,
      icon: <Target size={13} />,
    },
    { key: 'movements' as const, label: 'Movements', icon: <TrendingUp size={13} /> },
    { key: 'forecast' as const, label: 'Forecast', icon: <Eye size={13} /> },
  ];

  return (
    <main className="seo-advanced-page" style={{ minHeight: '100vh', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <section
          style={{
            position: 'relative',
            overflow: 'hidden',
            borderRadius: 16,
            border: '1px solid rgba(96,165,250,0.3)',
            background:
              'var(--card)',
            padding: '22px 24px',
            marginBottom: 20,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
            <div>
              <div style={{ display: 'inline-flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.12em',
                    color: 'var(--brand)',
                    border: '1px solid rgba(147,197,253,0.45)',
                    borderRadius: 999,
                    padding: '3px 10px',
                    background: 'rgba(96,165,250,0.14)',
                  }}
                >
                  Rank Intelligence
                </span>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.12em',
                    color: 'var(--muted)',
                    border: '1px solid rgba(148,163,184,0.3)',
                    borderRadius: 999,
                    padding: '3px 10px',
                    background: 'rgba(148,163,184,0.12)',
                  }}
                >
                  Volatility + Forecast
                </span>
              </div>
              <h1
                style={{
                  margin: 0,
                  fontSize: 30,
                  fontWeight: 800,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  color: 'var(--text)',
                }}
              >
                <TrendingUp size={26} color="#60a5fa" />
                Rank Tracking
              </h1>
              <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 15 }}>
                Keyword position monitoring, volatility detection, competitor surveillance, and 30-day forecast.
              </p>
            </div>
            {result && (
              <button
                onClick={exportCSV}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '8px 16px',
                  border: '1px solid rgba(148,163,184,0.35)',
                  borderRadius: 10,
                  background: '#f4f5f8',
                  color: 'var(--text)',
                  cursor: 'pointer',
                  fontSize: 13,
                }}
              >
                <Download size={14} />
                Export CSV
              </button>
            )}
          </div>
        </section>

        {error && (
          <div style={{ ...card, color: '#dc2626', borderColor: '#dc262644', background: '#dc262611' }}>{error}</div>
        )}

        <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))' }}>
          <section style={{ ...card, marginBottom: 0 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                marginBottom: 12,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Filter size={15} color="var(--brand)" />
                <span style={{ fontWeight: 700, fontSize: 14 }}>Tracking Configuration</span>
              </div>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: 'var(--brand)',
                  border: '1px solid rgba(147,197,253,0.35)',
                  borderRadius: 8,
                  padding: '4px 8px',
                  background: 'rgba(96,165,250,0.12)',
                }}
              >
                Advanced Mode
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 }}>
              <div>
                <label
                  htmlFor="rank-domain"
                  style={{
                    display: 'block',
                    fontSize: 12,
                    fontWeight: 600,
                    marginBottom: 5,
                    color: 'var(--muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  Target Domain
                </label>
                <input
                  id="rank-domain"
                  style={input}
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="example.com"
                />
                <label
                  htmlFor="rank-lookback"
                  style={{
                    display: 'block',
                    fontSize: 12,
                    fontWeight: 600,
                    marginBottom: 5,
                    color: 'var(--muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  Lookback Period
                </label>
                <select
                  id="rank-lookback"
                  style={input}
                  value={lookbackPeriod}
                  onChange={(e) => setLookbackPeriod(e.target.value)}
                >
                  {['7', '30', '90', '180', '365'].map((v) => (
                    <option key={v} value={v}>
                      Last {v} Days
                    </option>
                  ))}
                </select>
                <label
                  htmlFor="rank-include-competitor"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    fontSize: 13,
                    cursor: 'pointer',
                    marginBottom: 10,
                  }}
                >
                  <input
                    id="rank-include-competitor"
                    type="checkbox"
                    checked={includeCompetitor}
                    onChange={(e) => setIncludeCompetitor(e.target.checked)}
                  />
                  <span>Track Competitor Rankings</span>
                </label>
                {includeCompetitor && (
                  <textarea
                    id="rank-competitors"
                    style={{ ...input, minHeight: 80, resize: 'vertical' }}
                    value={competitorDomains}
                    onChange={(e) => setCompetitorDomains(e.target.value)}
                    placeholder="competitor1.com&#10;competitor2.com"
                  />
                )}
                <label
                  htmlFor="rank-notes"
                  style={{
                    display: 'block',
                    fontSize: 12,
                    fontWeight: 600,
                    marginBottom: 5,
                    color: 'var(--muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  Notes / Context
                </label>
                <textarea
                  id="rank-notes"
                  style={{ ...input, minHeight: 48, resize: 'vertical' }}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Focus areas, recent changes..."
                />
              </div>
              <div>
                <label
                  htmlFor="rank-keywords"
                  style={{
                    display: 'block',
                    fontSize: 12,
                    fontWeight: 600,
                    marginBottom: 5,
                    color: 'var(--muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  Keywords to Track (one per line)
                </label>
                <textarea
                  id="rank-keywords"
                  style={{ ...input, minHeight: 200, resize: 'vertical' }}
                  value={trackedKeywords}
                  onChange={(e) => setTrackedKeywords(e.target.value)}
                  placeholder="best seo tool&#10;seo platform free&#10;keyword research tool&#10;rank tracker"
                />
              </div>
            </div>
            <button
              onClick={() => void runTracking()}
              disabled={loading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '10px 28px',
                border: 'none',
                borderRadius: 8,
                background: loading ? 'var(--muted)' : 'var(--brand)',
                color: '#00101e',
                fontWeight: 800,
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 14,
                marginTop: 4,
              }}
            >
              {loading ? (
                <>
                  <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} />
                  Analyzing...
                </>
              ) : (
                <>
                  <TrendingUp size={15} />
                  Track Rankings
                </>
              )}
            </button>
          </section>

          <aside style={{ ...card, marginBottom: 0 }}>
            <div>
              <h3 style={{ margin: '0 0 6px', fontSize: 16, color: 'var(--text)' }}>Audit Blueprint</h3>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                Execution flow for rank movement intelligence.
              </p>
            </div>
            <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
              {RANK_AUDIT_PHASES.map((phase, index) => (
                <div
                  key={phase}
                  style={{
                    display: 'flex',
                    gap: 10,
                    alignItems: 'flex-start',
                    border: '1px solid rgba(148,163,184,0.16)',
                    borderRadius: 10,
                    padding: '8px 10px',
                    background: '#f4f5f8',
                  }}
                >
                  <div
                    style={{
                      width: 20,
                      height: 20,
                      borderRadius: 999,
                      border: '1px solid rgba(147,197,253,0.4)',
                      background: 'rgba(96,165,250,0.16)',
                      color: 'var(--brand)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 11,
                      fontWeight: 700,
                    }}
                  >
                    {index + 1}
                  </div>
                  <div style={{ fontSize: 12, lineHeight: 1.4, color: 'var(--muted)' }}>{phase}</div>
                </div>
              ))}
            </div>
            <div
              style={{
                marginTop: 12,
                border: '1px solid rgba(148,163,184,0.16)',
                borderRadius: 10,
                padding: '10px 12px',
                background: '#f4f5f8',
              }}
            >
              <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                Current Scope
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
                <span
                  style={{
                    border: '1px solid rgba(147,197,253,0.35)',
                    background: 'rgba(96,165,250,0.14)',
                    color: 'var(--brand)',
                    borderRadius: 999,
                    padding: '3px 8px',
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  {lookbackPeriod} day window
                </span>
                <span
                  style={{
                    border: '1px solid rgba(148,163,184,0.35)',
                    background: 'rgba(148,163,184,0.12)',
                    color: 'var(--text)',
                    borderRadius: 999,
                    padding: '3px 8px',
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  {includeCompetitor ? 'Competitors on' : 'Competitors off'}
                </span>
              </div>
            </div>
          </aside>
        </div>

        {result && (
          <>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
                {result.analysis_mode && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)', color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)' }}>
                    {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                  </span>
                )}
                {result.cached && (
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: 'rgba(56,189,248,0.12)', color: '#38bdf8' }}>Cached result</span>
                )}
              </div>
            )}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 160px), 1fr))',
                gap: 12,
                marginBottom: 20,
              }}
            >
              <StatCard
                icon={<Trophy size={16} />}
                label="Tracking Score"
                value={result.tracking_score}
                sub="out of 100"
                color="var(--brand)"
              />
              <StatCard icon={<Zap size={16} />} label="Top 3" value={top3} sub="positions" color="#ffb867" />
              <StatCard icon={<Target size={16} />} label="Top 10" value={top10} sub="first page" color="#26d78e" />
              <StatCard icon={<ChevronUp size={16} />} label="Gainers" value={gainers} sub="improved" color="#26d78e" />
              <StatCard icon={<ChevronDown size={16} />} label="Losers" value={losers} sub="dropped" color="#dc2626" />
              <StatCard
                icon={<AlertTriangle size={16} />}
                label="Volatile"
                value={result.volatile_keywords?.length ?? 0}
                sub="need attention"
                color="#dc2626"
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 16, marginBottom: 20 }}>
              <div style={{ ...card, marginBottom: 0 }}>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    color: 'var(--muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    marginBottom: 12,
                  }}
                >
                  Volatility Index
                </div>
                <VolatilityBar value={result.volatility_index} />
                <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {result.volatile_keywords?.map((kw) => (
                    <span
                      key={kw}
                      style={{
                        padding: '3px 10px',
                        borderRadius: 999,
                        background: 'rgba(248,113,113,0.12)',
                        color: '#dc2626',
                        fontSize: 11,
                        fontWeight: 700,
                        border: '1px solid rgba(248,113,113,0.3)',
                      }}
                    >
                      {kw}
                    </span>
                  ))}
                </div>
              </div>
              <div
                style={{ ...card, marginBottom: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              >
                <ScoreGauge score={result.tracking_score} label="Rank Score" size={110} />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid var(--line)' }}>
              {tabs.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setActiveTab(t.key)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '8px 16px',
                    border: 'none',
                    borderRadius: '8px 8px 0 0',
                    background: activeTab === t.key ? 'var(--bg-soft)' : 'transparent',
                    color: activeTab === t.key ? 'var(--brand)' : 'var(--muted)',
                    fontWeight: 700,
                    fontSize: 13,
                    cursor: 'pointer',
                    borderBottom: activeTab === t.key ? '2px solid var(--brand)' : '2px solid transparent',
                  }}
                >
                  {t.icon}
                  {t.label}
                </button>
              ))}
            </div>

            {activeTab === 'overview' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Summary &amp; Next Actions</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 }}>
                  <div>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: 'var(--muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        marginBottom: 10,
                      }}
                    >
                      Alert Triggers
                    </div>
                    {result.alert_triggers?.map((a, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
                        <Bell size={12} color="#dc2626" style={{ marginTop: 2, flexShrink: 0 }} />
                        <span style={{ fontSize: 13 }}>{a}</span>
                      </div>
                    ))}
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: 'var(--muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        marginBottom: 10,
                      }}
                    >
                      Next Actions
                    </div>
                    {result.next_actions?.map((a, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
                        <Zap size={12} color="#26d78e" style={{ marginTop: 2, flexShrink: 0 }} />
                        <span style={{ fontSize: 13 }}>{a}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'keywords' && (
              <div style={card}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
                  <div style={{ position: 'relative', flex: 1, maxWidth: 320 }}>
                    <Search
                      size={13}
                      style={{
                        position: 'absolute',
                        left: 10,
                        top: '50%',
                        transform: 'translateY(-50%)',
                        color: 'var(--muted)',
                      }}
                    />
                    <input
                      style={{ ...input, paddingLeft: 32, marginBottom: 0 }}
                      value={kwFilter}
                      onChange={(e) => setKwFilter(e.target.value)}
                      placeholder="Filter keywords..."
                    />
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--muted)' }}>{sortedKeywords.length} keywords</span>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={th} onClick={() => handleSort('keyword')}>
                          Keyword {sortKey === 'keyword' && (sortDir === 'asc' ? '↑' : '↓')}
                        </th>
                        <th style={th} onClick={() => handleSort('current_position')}>
                          Position {sortKey === 'current_position' && (sortDir === 'asc' ? '↑' : '↓')}
                        </th>
                        <th style={th} onClick={() => handleSort('position_change')}>
                          Change {sortKey === 'position_change' && (sortDir === 'asc' ? '↑' : '↓')}
                        </th>
                        <th style={th}>Trend</th>
                        <th style={th}>30d Trend</th>
                        <th style={th}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedKeywords.map((r, i) => {
                        const isVolatile = result.volatile_keywords?.includes(r.keyword);
                        return (
                          <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                            <td style={td}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                {isVolatile && <AlertTriangle size={11} color="#ffb867" />}
                                <span style={{ fontWeight: 600 }}>{r.keyword}</span>
                              </div>
                            </td>
                            <td style={td}>
                              <PosBadge pos={r.current_position} change={r.position_change} />
                            </td>
                            <td style={td}>
                              <span
                                style={{
                                  color:
                                    r.position_change > 0
                                      ? '#26d78e'
                                      : r.position_change < 0
                                        ? '#dc2626'
                                        : 'var(--muted)',
                                  fontWeight: 700,
                                }}
                              >
                                {r.position_change > 0 ? `+${r.position_change}` : r.position_change}
                              </span>
                            </td>
                            <td style={td}>
                              {r.trend === 'up' ? (
                                <TrendingUp size={14} color="#26d78e" />
                              ) : r.trend === 'down' ? (
                                <TrendingDown size={14} color="#dc2626" />
                              ) : (
                                <Minus size={14} color="var(--muted)" />
                              )}
                            </td>
                            <td style={{ ...td, color: 'var(--muted)', fontSize: 12 }}>{r['30d_trend']}</td>
                            <td style={td}>
                              {isVolatile ? (
                                <span
                                  style={{
                                    padding: '2px 8px',
                                    borderRadius: 999,
                                    background: 'rgba(248,113,113,0.12)',
                                    color: '#dc2626',
                                    fontSize: 10,
                                    fontWeight: 700,
                                  }}
                                >
                                  VOLATILE
                                </span>
                              ) : (
                                <span style={{ color: 'var(--muted)', fontSize: 11 }}>Stable</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'movements' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Key Movements</h3>
                <div style={{ display: 'grid', gap: 10 }}>
                  {result.key_movements?.map((m, i) => (
                    <div
                      key={i}
                      style={{
                        background: 'var(--bg)',
                        borderRadius: 10,
                        padding: '14px 16px',
                        border: '1px solid var(--line)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                        <TrendingUp size={14} color="var(--brand)" />
                        <span style={{ fontWeight: 700, fontSize: 14 }}>{m.keyword}</span>
                        <span
                          style={{
                            fontSize: 12,
                            padding: '2px 8px',
                            borderRadius: 6,
                            background: 'rgba(27,199,255,0.1)',
                            color: 'var(--brand)',
                          }}
                        >
                          {m.movement}
                        </span>
                      </div>
                      <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)', lineHeight: 1.5 }}>
                        {m.likely_cause}
                      </p>
                    </div>
                  ))}
                </div>
                {result.competitor_movements?.length > 0 && (
                  <div style={{ marginTop: 20 }}>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: 'var(--muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        marginBottom: 12,
                      }}
                    >
                      Competitor Movements
                    </div>
                    <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr>
                          <th style={th}>Competitor</th>
                          <th style={th}>Keyword</th>
                          <th style={th}>Change</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.competitor_movements.map((c, i) => (
                          <tr key={i}>
                            <td style={{ ...td, fontWeight: 600 }}>
                              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <Globe size={12} />
                                {c.competitor}
                              </span>
                            </td>
                            <td style={td}>{c.keyword}</td>
                            <td style={td}>
                              <span style={{ color: c.change > 0 ? '#26d78e' : '#dc2626', fontWeight: 700 }}>
                                {c.change > 0 ? `+${c.change}` : c.change}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'forecast' && result.trend_forecast && (
              <div style={card}>
                <h3 style={{ margin: '0 0 20px', fontSize: 15, fontWeight: 700 }}>Trend Forecast</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 24 }}>
                  <div style={{ textAlign: 'center' }}>
                    <ScoreGauge
                      score={Math.round(result.trend_forecast.confidence * 100)}
                      label="Confidence"
                      size={120}
                    />
                    <div
                      style={{
                        marginTop: 8,
                        fontSize: 18,
                        fontWeight: 800,
                        color:
                          result.trend_forecast.direction === 'up'
                            ? '#26d78e'
                            : result.trend_forecast.direction === 'down'
                              ? '#dc2626'
                              : 'var(--muted)',
                      }}
                    >
                      {result.trend_forecast.direction === 'up'
                        ? '📈 Upward'
                        : result.trend_forecast.direction === 'down'
                          ? '📉 Downward'
                          : '➡️ Stable'}
                    </div>
                    <div
                      style={{
                        fontSize: 12,
                        color: 'var(--muted)',
                        marginTop: 4,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 4,
                      }}
                    >
                      <Clock size={11} />
                      {result.trend_forecast.forecast_horizon_days}d horizon
                    </div>
                  </div>
                  <div>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: 'var(--muted)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        marginBottom: 12,
                      }}
                    >
                      Key Drivers
                    </div>
                    {result.trend_forecast.key_drivers?.map((d, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
                        <Zap size={12} color="var(--brand)" style={{ marginTop: 2, flexShrink: 0 }} />
                        <span style={{ fontSize: 13 }}>{d}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </main>
  );
}
