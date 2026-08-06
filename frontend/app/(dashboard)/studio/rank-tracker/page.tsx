'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { apiGet, apiSend } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Keyword {
  id: string;
  keyword: string;
  target_url: string;
  current_position: number;
  position_change_30d: number;
  search_volume: number;
  keyword_difficulty: number;
  traffic_potential: number;
  search_intent: string;
  is_tracking: boolean;
  added_at: string;
  checked_at: string;
}

interface Project {
  id: string;
  name: string;
  domain: string;
  location: string;
  search_engine: string;
  tracking_keywords: number;
  created_at: string;
}

interface Competitor {
  id: string;
  domain: string;
  authority_score: number;
  organic_keywords: number;
  organic_traffic_estimate: number;
  added_at: string;
}

interface PositionData {
  date: string;
  position: number;
  impressions: number;
  clicks: number;
  ctr: number;
}

interface Alert {
  id: string;
  keyword_id: string;
  keyword: string;
  alert_type: string;
  threshold: number;
  is_active: boolean;
  created_at: string;
}

interface KeywordResearchSource {
  key: string;
  label: string;
  role: string;
  configured: boolean;
}

interface KeywordVendor {
  key: string;
  category: string;
  coverage: string[];
  configured: boolean;
}

interface ProviderAttempt {
  provider: string;
  status: 'success' | 'error' | 'skipped';
  configured: boolean;
  attempted: boolean;
  latency_ms: number;
  error_code?: string;
  error_message?: string;
  fallback_reason?: string;
}

interface ProviderTelemetry {
  operation: string;
  attempt_count: number;
  attempted_live_providers: number;
  failed_live_attempts: number;
  provider_latency_total_ms: number;
  pipeline_latency_ms: number;
}

interface KeywordResearchOpportunity {
  keyword: string;
  search_volume: number;
  keyword_difficulty: number;
  cpc_usd: number;
  intent: string;
  serp_features: string[];
  trend_3m_pct: number[];
  competition_level: string;
  priority_score: number;
}

interface KeywordResearchCluster {
  topic: string;
  total_volume: number;
  avg_difficulty: number;
  keywords: KeywordResearchOpportunity[];
}

interface ContentGapOpportunity {
  keyword: string;
  search_volume: number;
  difficulty: number;
  covered_by_competitors: number;
  estimated_monthly_clicks: number;
  recommended_content_type: string;
}

// ---------------------------------------------------------------------------
// Style constants
// ---------------------------------------------------------------------------

const BG_PAGE: React.CSSProperties = {
  backgroundColor: 'var(--card)',
  minHeight: '100vh',
  color: 'var(--text)',
  fontFamily: 'Inter, sans-serif',
};
const PANEL: React.CSSProperties = { backgroundColor: 'var(--card)', border: '1px solid var(--line)', borderRadius: 12 };
const CARD: React.CSSProperties = {
  backgroundColor: 'var(--card)',
  border: '1px solid var(--line)',
  borderRadius: 8,
  padding: '16px 20px',
};
const INPUT_STYLE: React.CSSProperties = {
  backgroundColor: 'var(--card)',
  border: '1px solid var(--line)',
  borderRadius: 6,
  color: 'var(--text)',
  padding: '8px 12px',
  outline: 'none',
  width: '100%',
  fontSize: 14,
};
const BTN_PRIMARY: React.CSSProperties = {
  backgroundColor: '#06B6D4',
  color: '#eef0f4',
  border: 'none',
  borderRadius: 6,
  padding: '9px 18px',
  fontWeight: 700,
  cursor: 'pointer',
  fontSize: 14,
};
const BTN_SM: React.CSSProperties = {
  backgroundColor: 'var(--card)',
  color: 'var(--muted)',
  border: '1px solid var(--line)',
  borderRadius: 5,
  padding: '5px 12px',
  cursor: 'pointer',
  fontSize: 12,
};
const BADGE_UP: React.CSSProperties = {
  backgroundColor: '#dcfce7',
  color: '#34D399',
  borderRadius: 4,
  padding: '2px 7px',
  fontSize: 11,
  fontWeight: 600,
};
const BADGE_DOWN: React.CSSProperties = {
  backgroundColor: '#fee2e2',
  color: '#dc2626',
  borderRadius: 4,
  padding: '2px 7px',
  fontSize: 11,
  fontWeight: 600,
};
const BADGE_STABLE: React.CSSProperties = {
  backgroundColor: 'var(--card)',
  color: 'var(--brand)',
  borderRadius: 4,
  padding: '2px 7px',
  fontSize: 11,
  fontWeight: 600,
};
const TABLE_TH: React.CSSProperties = {
  padding: '10px 14px',
  textAlign: 'left',
  color: 'var(--muted)',
  fontWeight: 600,
  fontSize: 12,
  borderBottom: '1px solid var(--line)',
  whiteSpace: 'nowrap',
};
const TABLE_TD: React.CSSProperties = {
  padding: '10px 14px',
  borderBottom: '1px solid var(--line)',
  fontSize: 13,
  verticalAlign: 'middle',
};

const TABS = [
  'Overview',
  'Keywords',
  'Keyword Research',
  'Projects',
  'Competitors',
  'History',
  'Forecasts',
  'Analytics',
  'Alerts',
  'SERP Check',
] as const;
type Tab = (typeof TABS)[number];

const KEYWORD_RESEARCH_TAB = 'Keyword Research' as const;
const KEYWORD_RESEARCH_TAB_QUERY = 'keyword-research';

// ---------------------------------------------------------------------------
// Utility components
// ---------------------------------------------------------------------------

function PositionRing({ position, size = 100 }: { position: number; size?: number }) {
  const color = position <= 3 ? '#10B981' : position <= 10 ? '#F59E0B' : position <= 30 ? 'var(--brand)' : '#dc2626';
  const r = (size - 20) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - Math.min(100, position) / 100);
  return (
    <svg width={size} height={size}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#eef0f4" strokeWidth={8} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={8}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x={size / 2}
        y={size / 2 + 4}
        textAnchor="middle"
        fill={color}
        fontSize={size === 100 ? 20 : 16}
        fontWeight="700"
      >
        {position}
      </text>
    </svg>
  );
}

function PositionBadge({ change }: { change: number }) {
  if (change < -1) return <span style={BADGE_UP}>↑ {Math.abs(change)} spots</span>;
  if (change > 1) return <span style={BADGE_DOWN}>↓ {change} spots</span>;
  return <span style={BADGE_STABLE}>→ stable</span>;
}

function IntentBadge({ intent }: { intent: string }) {
  const colors: Record<string, string> = {
    commercial: '#F59E0B',
    informational: 'var(--brand)',
    navigational: '#06B6D4',
    transactional: '#10B981',
  };
  return (
    <span
      style={{
        backgroundColor: colors[intent] + '22',
        color: colors[intent],
        borderRadius: 4,
        padding: '2px 7px',
        fontSize: 11,
        fontWeight: 600,
      }}
    >
      {intent}
    </span>
  );
}

function MetricCard({
  label,
  value,
  sub,
  color = '#06B6D4',
}: {
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div style={CARD}>
      <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 4 }}>{label}</div>
      <div style={{ color, fontSize: 26, fontWeight: 700 }}>{value}</div>
      {sub && <div style={{ color: '#e7e9ef', fontSize: 12, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function RankTrackerPage() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>('Overview');
  const [overview, setOverview] = useState<any>(null);
  const [ovLoading, setOvLoading] = useState(false);

  const fetchOverview = useCallback(async () => {
    setOvLoading(true);
    try {
      const p = await apiGet<{ positions?: Keyword[]; summary?: Record<string, number> }>('/rank-tracker/positions');
      const vis = await apiGet<{ visibility?: Record<string, number> }>('/rank-tracker/visibility-score');
      setOverview({ positions: p, visibility: vis.visibility });
    } catch {
      setOverview(null);
    } finally {
      setOvLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  useEffect(() => {
    if (pathname.endsWith('/keyword-research')) {
      setTab(KEYWORD_RESEARCH_TAB);
      return;
    }
    const tabParam = searchParams.get('tab');
    if (tabParam === KEYWORD_RESEARCH_TAB_QUERY) {
      setTab(KEYWORD_RESEARCH_TAB);
    }
  }, [pathname, searchParams]);

  const handleTabClick = useCallback((nextTab: Tab) => {
    setTab(nextTab);
    if (globalThis.window === undefined) return;
    const nextUrl = new URL(globalThis.window.location.href);
    if (nextTab === KEYWORD_RESEARCH_TAB) {
      nextUrl.searchParams.set('tab', KEYWORD_RESEARCH_TAB_QUERY);
    } else {
      nextUrl.searchParams.delete('tab');
    }
    globalThis.window.history.replaceState(null, '', `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`);
  }, []);

  return (
    <div style={BG_PAGE}>
      {/* Header */}
      <div
        style={{
          background: 'linear-gradient(135deg, #eef0f4 0%, #eef0f4 100%)',
          borderBottom: '1px solid var(--line)',
          padding: '28px 40px 0',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 6 }}>
          <span style={{ fontSize: 32 }}>📊</span>
          <div>
            <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, color: 'var(--text)' }}>Rank Tracker</h1>
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: 14 }}>
              Ahrefs-grade keyword position monitoring: real-time SERP tracking, traffic forecasts, competitor
              benchmarking &amp; lost/gained keywords
            </p>
          </div>
        </div>
        {/* Tab bar */}
        <div style={{ display: 'flex', gap: 2, marginTop: 20, overflowX: 'auto' }}>
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => handleTabClick(t)}
              style={{
                background: tab === t ? '#06B6D4' : 'transparent',
                color: tab === t ? '#eef0f4' : 'var(--muted)',
                border: 'none',
                borderRadius: '6px 6px 0 0',
                padding: '10px 18px',
                fontWeight: tab === t ? 700 : 500,
                cursor: 'pointer',
                fontSize: 13,
                whiteSpace: 'nowrap',
                transition: 'all 0.15s',
              }}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: '32px 40px' }}>
        {tab === 'Overview' && <OverviewTab overview={overview} loading={ovLoading} onRefresh={fetchOverview} />}
        {tab === 'Keywords' && <KeywordsTab />}
        {tab === KEYWORD_RESEARCH_TAB && <KeywordResearchTab />}
        {tab === 'Projects' && <ProjectsTab />}
        {tab === 'Competitors' && <CompetitorsTab />}
        {tab === 'History' && <HistoryTab />}
        {tab === 'Forecasts' && <ForecastsTab />}
        {tab === 'Analytics' && <AnalyticsTab />}
        {tab === 'Alerts' && <AlertsTab />}
        {tab === 'SERP Check' && <SERPCheckTab />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Overview
// ---------------------------------------------------------------------------

function OverviewTab({ overview, loading, onRefresh }: { overview: any; loading: boolean; onRefresh: () => void }) {
  const pos = overview?.positions?.summary ?? {};
  const vis = overview?.visibility ?? {};

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Keyword Ranking Dashboard</h2>
        <button onClick={onRefresh} style={BTN_SM} disabled={loading}>
          {loading ? 'Loading…' : '↻ Refresh'}
        </button>
      </div>

      {/* Key metrics */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 160px), 1fr))',
          gap: 14,
          marginBottom: 32,
        }}
      >
        <MetricCard label="Total Keywords" value={pos.total_keywords ?? 0} sub="Tracked keywords" />
        <MetricCard label="Top 3" value={pos.top_3 ?? 0} sub="Position ≤ 3" color="#10B981" />
        <MetricCard label="Top 10" value={pos.top_10 ?? 0} sub="Position ≤ 10" color="#F59E0B" />
        <MetricCard label="Improved 30d" value={pos.improved_count ?? 0} sub="Gained positions" color="#34D399" />
        <MetricCard label="Declined 30d" value={pos.declined_count ?? 0} sub="Lost positions" color="#dc2626" />
        <MetricCard
          label="Visibility Score"
          value={`${vis.visibility_score ?? 0}%`}
          sub="Top 10 traffic %"
          color="var(--brand)"
        />
        <MetricCard
          label="Est. Monthly Traffic"
          value={`${(vis.estimated_monthly_traffic ?? 0) / 1000}k`}
          sub="Organic clicks"
          color="#06B6D4"
        />
      </div>

      {/* Traffic breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 }}>
        <div style={{ ...PANEL, padding: 24 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Ranking Distribution</h3>
          {[
            { label: 'Rank 1-3', count: pos.top_3 ?? 0, color: '#10B981' },
            { label: 'Rank 4-10', count: (pos.top_10 ?? 0) - (pos.top_3 ?? 0), color: '#F59E0B' },
            { label: 'Rank 11-30', count: (pos.total_keywords ?? 0) - (pos.top_10 ?? 0), color: 'var(--brand)' },
          ].map(({ label, count, color: c }) => (
            <div key={label} style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 13, color: 'var(--muted)' }}>{label}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: c }}>{count}</span>
              </div>
              <div style={{ background: 'var(--card)', borderRadius: 4, height: 8 }}>
                <div
                  style={{
                    background: c,
                    borderRadius: 4,
                    height: 8,
                    width: `${Math.max(0, Math.min(100, (count / Math.max(1, pos.total_keywords ?? 1)) * 100))}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>
        <div style={{ ...PANEL, padding: 24 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Quick Actions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              'Track New Keyword',
              'Check SERP Now',
              'View Traffic Forecast',
              'Add Competitor',
              'Create Rank Alert',
            ].map((a) => (
              <div
                key={a}
                style={{
                  fontSize: 13,
                  color: '#06B6D4',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                <span style={{ fontSize: 10 }}>▶</span>
                {a}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Keywords
// ---------------------------------------------------------------------------

function KeywordsTab() {
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [newKw, setNewKw] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const d = await apiGet<any>('/rank-tracker/tracked-keywords');
      setKeywords(d.keywords ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const add = async () => {
    if (!newKw) return;
    await apiSend('/rank-tracker/tracked-keywords', 'POST', { keyword: newKw, target_url: newUrl });
    setNewKw('');
    setNewUrl('');
    fetch();
  };

  const remove = async (id: string) => {
    await apiSend(`/rank-tracker/tracked-keywords/${id}`, 'DELETE', undefined);
    fetch();
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 24px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Tracked Keywords</h2>

      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Add Keyword to Track</h3>
        <div style={{ display: 'flex', gap: 12 }}>
          <input
            value={newKw}
            onChange={(e) => setNewKw(e.target.value)}
            placeholder="digital marketing platform"
            style={{ ...INPUT_STYLE, maxWidth: 280 }}
          />
          <input
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            placeholder="Target URL (optional)"
            style={{ ...INPUT_STYLE, maxWidth: 240 }}
          />
          <button onClick={add} style={BTN_PRIMARY}>
            + Track
          </button>
        </div>
      </div>

      <div style={{ ...PANEL, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Keyword', 'Position', '30d Change', 'Volume', 'Difficulty', 'Intent', 'Traffic Pot.', 'Action'].map(
                (h) => (
                  <th key={h} style={TABLE_TH}>
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} style={{ ...TABLE_TD, textAlign: 'center', color: 'var(--muted)' }}>
                  Loading…
                </td>
              </tr>
            ) : keywords.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ ...TABLE_TD, textAlign: 'center', color: 'var(--muted)' }}>
                  No keywords tracked yet.
                </td>
              </tr>
            ) : (
              keywords.map((kw) => (
                <tr key={kw.id}>
                  <td style={TABLE_TD}>
                    <a
                      href={kw.target_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#06B6D4', textDecoration: 'none' }}
                    >
                      {kw.keyword}
                    </a>
                  </td>
                  <td
                    style={{
                      ...TABLE_TD,
                      fontWeight: 700,
                      color: kw.current_position <= 10 ? '#10B981' : kw.current_position <= 30 ? '#F59E0B' : '#dc2626',
                    }}
                  >
                    {kw.current_position}
                  </td>
                  <td style={TABLE_TD}>
                    <PositionBadge change={kw.position_change_30d} />
                  </td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{kw.search_volume.toLocaleString()}</td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{kw.keyword_difficulty}</td>
                  <td style={TABLE_TD}>
                    <IntentBadge intent={kw.search_intent} />
                  </td>
                  <td style={{ ...TABLE_TD, fontWeight: 700, color: '#06B6D4' }}>
                    {kw.traffic_potential.toLocaleString()}
                  </td>
                  <td style={TABLE_TD}>
                    <button onClick={() => remove(kw.id)} style={{ ...BTN_SM, color: '#dc2626' }}>
                      ✕
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Keyword Research
// ---------------------------------------------------------------------------

function KeywordResearchTab() {
  const [seedKeyword, setSeedKeyword] = useState('social media management tool');
  const [location, setLocation] = useState('United States');
  const [includeQuestions, setIncludeQuestions] = useState(true);
  const [sources, setSources] = useState<KeywordResearchSource[]>([]);
  const [sourcePriorityOrder, setSourcePriorityOrder] = useState<string[]>([]);
  const [vendors, setVendors] = useState<KeywordVendor[]>([]);
  const [vendorStrategy, setVendorStrategy] = useState('');
  const [opportunities, setOpportunities] = useState<KeywordResearchOpportunity[]>([]);
  const [clusters, setClusters] = useState<KeywordResearchCluster[]>([]);
  const [gapDomain, setGapDomain] = useState('nuxtron.ai');
  const [competitorDomains, setCompetitorDomains] = useState('semrush.com, ahrefs.com, moz.com');
  const [gapResults, setGapResults] = useState<ContentGapOpportunity[]>([]);
  const [discoverProvider, setDiscoverProvider] = useState<string>('');
  const [discoverProviderAttempts, setDiscoverProviderAttempts] = useState<ProviderAttempt[]>([]);
  const [discoverTelemetry, setDiscoverTelemetry] = useState<ProviderTelemetry | null>(null);
  const [discoverProviderStrategy, setDiscoverProviderStrategy] = useState('');
  const [discoverFallbackUsed, setDiscoverFallbackUsed] = useState(false);
  const [discoverFallbackReason, setDiscoverFallbackReason] = useState('');
  const [gapProvider, setGapProvider] = useState<string>('');
  const [gapProviderAttempts, setGapProviderAttempts] = useState<ProviderAttempt[]>([]);
  const [gapTelemetry, setGapTelemetry] = useState<ProviderTelemetry | null>(null);
  const [gapProviderStrategy, setGapProviderStrategy] = useState('');
  const [gapFallbackUsed, setGapFallbackUsed] = useState(false);
  const [gapFallbackReason, setGapFallbackReason] = useState('');
  const [loadingDiscover, setLoadingDiscover] = useState(false);
  const [loadingGap, setLoadingGap] = useState(false);
  const [requestError, setRequestError] = useState('');

  useEffect(() => {
    void apiGet<{ sources?: KeywordResearchSource[]; priority_order?: string[] }>(
      '/rank-tracker/keyword-research/sources'
    )
      .then((result) => {
        setSources(result.sources ?? []);
        setSourcePriorityOrder(result.priority_order ?? []);
      })
      .catch(() => {
        setSources([]);
        setSourcePriorityOrder([]);
      });
  }, []);

  useEffect(() => {
    void apiGet<{ providers?: KeywordVendor[]; strategy?: string }>('/rank-tracker/keyword-research/vendors')
      .then((result) => {
        setVendors(result.providers ?? []);
        setVendorStrategy(result.strategy ?? '');
      })
      .catch(() => {
        setVendors([]);
        setVendorStrategy('');
      });
  }, []);

  const discoverKeywords = async () => {
    if (!seedKeyword.trim()) return;
    setLoadingDiscover(true);
    setRequestError('');
    try {
      const result = await apiSend<{
        opportunities?: KeywordResearchOpportunity[];
        clusters?: KeywordResearchCluster[];
        provider_selected?: string;
        provider_strategy?: string;
        provider_attempts?: ProviderAttempt[];
        telemetry?: ProviderTelemetry;
        fallback_used?: boolean;
        fallback_reason?: string | null;
      }>('/rank-tracker/keyword-research/discover', 'POST', {
        seed_keyword: seedKeyword,
        location,
        language: 'en',
        include_questions: includeQuestions,
        max_results: 80,
      });
      if (result.fallback_used) {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? `Live keyword discovery is unavailable in strict no-mock mode.${result.fallback_reason ? ` ${result.fallback_reason}` : ''}`
            : `Live keyword discovery is unavailable in fail-closed mode.${result.fallback_reason ? ` ${result.fallback_reason}` : ''}`
        );
      }
      setOpportunities(result.opportunities ?? []);
      setClusters(result.clusters ?? []);
      setDiscoverProvider(result.provider_selected ?? '');
      setDiscoverProviderStrategy(result.provider_strategy ?? '');
      setDiscoverProviderAttempts(result.provider_attempts ?? []);
      setDiscoverTelemetry(result.telemetry ?? null);
      setDiscoverFallbackUsed(Boolean(result.fallback_used));
      setDiscoverFallbackReason(result.fallback_reason ?? '');
    } catch (error) {
      setOpportunities([]);
      setClusters([]);
      setDiscoverProvider('');
      setDiscoverProviderStrategy('');
      setDiscoverProviderAttempts([]);
      setDiscoverTelemetry(null);
      setDiscoverFallbackUsed(false);
      setDiscoverFallbackReason('');
      setRequestError(error instanceof Error ? error.message : 'Keyword discovery failed.');
    } finally {
      setLoadingDiscover(false);
    }
  };

  const runGapAnalysis = async () => {
    if (!gapDomain.trim()) return;
    const competitors = competitorDomains
      .split(',')
      .map((entry) => entry.trim())
      .filter(Boolean)
      .slice(0, 6);
    if (!competitors.length) return;
    setLoadingGap(true);
    setRequestError('');
    try {
      const result = await apiSend<{
        opportunities?: ContentGapOpportunity[];
        provider_selected?: string;
        provider_strategy?: string;
        provider_attempts?: ProviderAttempt[];
        telemetry?: ProviderTelemetry;
        fallback_used?: boolean;
        fallback_reason?: string | null;
      }>('/rank-tracker/keyword-research/content-gap', 'POST', {
        your_domain: gapDomain,
        competitor_domains: competitors,
        max_results: 25,
      });
      if (result.fallback_used) {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? `Live content gap analysis is unavailable in strict no-mock mode.${result.fallback_reason ? ` ${result.fallback_reason}` : ''}`
            : `Live content gap analysis is unavailable in fail-closed mode.${result.fallback_reason ? ` ${result.fallback_reason}` : ''}`
        );
      }
      setGapResults(result.opportunities ?? []);
      setGapProvider(result.provider_selected ?? '');
      setGapProviderStrategy(result.provider_strategy ?? '');
      setGapProviderAttempts(result.provider_attempts ?? []);
      setGapTelemetry(result.telemetry ?? null);
      setGapFallbackUsed(Boolean(result.fallback_used));
      setGapFallbackReason(result.fallback_reason ?? '');
    } catch (error) {
      setGapResults([]);
      setGapProvider('');
      setGapProviderStrategy('');
      setGapProviderAttempts([]);
      setGapTelemetry(null);
      setGapFallbackUsed(false);
      setGapFallbackReason('');
      setRequestError(error instanceof Error ? error.message : 'Content gap analysis failed.');
    } finally {
      setLoadingGap(false);
    }
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 24px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Keyword Research</h2>
      {requestError && (
        <div
          style={{
            ...PANEL,
            border: '1px solid #fee2e2',
            padding: 14,
            marginBottom: 16,
            color: '#dc2626',
            fontSize: 13,
          }}
        >
          {requestError}
        </div>
      )}

      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Provider Sources</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 10 }}>
          {sources.length === 0 ? (
            <div style={{ color: 'var(--muted)', fontSize: 13 }}>No provider metadata available.</div>
          ) : (
            sources.map((source) => (
              <div key={source.key} style={{ ...CARD, padding: 12 }}>
                <div style={{ color: 'var(--text)', fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{source.label}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 8 }}>{source.role}</div>
                <span style={{ ...(source.configured ? BADGE_UP : BADGE_STABLE) }}>
                  {source.configured ? 'configured' : 'not configured'}
                </span>
              </div>
            ))
          )}
        </div>
        {sourcePriorityOrder.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 8 }}>Execution order</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {sourcePriorityOrder.map((providerName, index) => (
                <span
                  key={`${providerName}-${index}`}
                  style={{
                    backgroundColor: 'var(--card)',
                    border: '1px solid var(--line)',
                    borderRadius: 9999,
                    padding: '4px 10px',
                    color: 'var(--muted)',
                    fontSize: 12,
                  }}
                >
                  {index + 1}. {providerName}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 10px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Vendor Stack</h3>
        {vendorStrategy && (
          <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 12 }}>Strategy: {vendorStrategy}</div>
        )}
        {vendors.length === 0 ? (
          <div style={{ color: 'var(--muted)', fontSize: 13 }}>No vendor metadata available.</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 10 }}>
            {vendors.map((vendor) => (
              <div key={vendor.key} style={{ ...CARD, padding: 12 }}>
                <div style={{ color: 'var(--text)', fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{vendor.key}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 6 }}>{vendor.category}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 6 }}>{vendor.coverage.join(', ')}</div>
                <span style={{ ...(vendor.configured ? BADGE_UP : BADGE_STABLE) }}>
                  {vendor.configured ? 'configured' : 'not configured'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Discover Keywords</h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
            gap: 12,
            marginBottom: 14,
          }}
        >
          <input
            value={seedKeyword}
            onChange={(event) => setSeedKeyword(event.target.value)}
            placeholder="Seed keyword"
            style={INPUT_STYLE}
          />
          <input
            value={location}
            onChange={(event) => setLocation(event.target.value)}
            placeholder="Location"
            style={INPUT_STYLE}
          />
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--muted)', fontSize: 13 }}>
            <input
              type="checkbox"
              checked={includeQuestions}
              onChange={(event) => setIncludeQuestions(event.target.checked)}
            />
            <span>Include question keywords</span>
          </label>
        </div>
        <button onClick={discoverKeywords} style={BTN_PRIMARY} disabled={loadingDiscover}>
          {loadingDiscover ? 'Analyzing…' : 'Discover Opportunities'}
        </button>
      </div>

      {(discoverProvider || discoverProviderAttempts.length > 0 || discoverTelemetry) && (
        <div style={{ ...PANEL, padding: 18, marginBottom: 24 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>
            Discover Provider Telemetry
          </h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))',
              gap: 10,
              marginBottom: 12,
            }}
          >
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Selected provider</div>
              <div style={{ color: 'var(--text)', fontWeight: 700, fontSize: 13 }}>{discoverProvider || '-'}</div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Provider strategy</div>
              <div style={{ color: 'var(--muted)', fontWeight: 700, fontSize: 13 }}>{discoverProviderStrategy || '-'}</div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Fallback response</div>
              <div style={{ color: discoverFallbackUsed ? '#F59E0B' : '#10B981', fontWeight: 700, fontSize: 13 }}>
                {discoverFallbackUsed ? 'yes' : 'no'}
              </div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Pipeline latency</div>
              <div style={{ color: '#06B6D4', fontWeight: 700, fontSize: 13 }}>
                {discoverTelemetry ? `${discoverTelemetry.pipeline_latency_ms} ms` : '-'}
              </div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Provider latency</div>
              <div style={{ color: '#06B6D4', fontWeight: 700, fontSize: 13 }}>
                {discoverTelemetry ? `${discoverTelemetry.provider_latency_total_ms} ms` : '-'}
              </div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Attempts</div>
              <div style={{ color: 'var(--text)', fontWeight: 700, fontSize: 13 }}>
                {discoverTelemetry
                  ? `${discoverTelemetry.attempt_count} total / ${discoverTelemetry.attempted_live_providers} live`
                  : '-'}
              </div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Failed live attempts</div>
              <div style={{ color: '#F59E0B', fontWeight: 700, fontSize: 13 }}>
                {discoverTelemetry ? discoverTelemetry.failed_live_attempts : '-'}
              </div>
            </div>
          </div>
          {discoverFallbackReason && (
            <div style={{ color: '#F59E0B', fontSize: 12, marginBottom: 10 }}>
              Fallback response reason: {discoverFallbackReason}
            </div>
          )}
          {discoverProviderAttempts.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 10 }}>
              {discoverProviderAttempts.map((attempt, index) => (
                <div key={`${attempt.provider}-${attempt.status}-${index}`} style={{ ...CARD, padding: 10 }}>
                  <div style={{ color: 'var(--text)', fontSize: 13, fontWeight: 700, marginBottom: 4 }}>
                    {attempt.provider}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 2 }}>status: {attempt.status}</div>
                  <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 2 }}>
                    configured: {attempt.configured ? 'yes' : 'no'} | attempted: {attempt.attempted ? 'yes' : 'no'}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 2 }}>
                    latency: {attempt.latency_ms} ms
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 2 }}>
                    {attempt.error_code ?? 'no error'}
                  </div>
                  {attempt.error_message && (
                    <div style={{ color: '#F59E0B', fontSize: 11 }}>{attempt.error_message}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {opportunities.length > 0 && (
        <div style={{ ...PANEL, overflowX: 'auto', marginBottom: 24 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['Keyword', 'Intent', 'Volume', 'Difficulty', 'CPC', 'Priority', 'SERP Features'].map((header) => (
                  <th key={header} style={TABLE_TH}>
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {opportunities.slice(0, 40).map((item) => (
                <tr key={item.keyword}>
                  <td style={TABLE_TD}>{item.keyword}</td>
                  <td style={TABLE_TD}>
                    <IntentBadge intent={item.intent} />
                  </td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{item.search_volume.toLocaleString()}</td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{item.keyword_difficulty}</td>
                  <td style={{ ...TABLE_TD, color: '#10B981', fontWeight: 700 }}>${item.cpc_usd.toFixed(2)}</td>
                  <td style={{ ...TABLE_TD, color: '#06B6D4', fontWeight: 700 }}>{item.priority_score}</td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)', fontSize: 12 }}>{item.serp_features.join(', ')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {clusters.length > 0 && (
        <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Top Clusters</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 12 }}>
            {clusters.slice(0, 8).map((cluster) => (
              <div key={cluster.topic} style={{ ...CARD, padding: 12 }}>
                <div style={{ color: 'var(--text)', fontWeight: 700, fontSize: 13, marginBottom: 4 }}>{cluster.topic}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 2 }}>
                  {cluster.keywords.length} keywords
                </div>
                <div style={{ color: '#10B981', fontSize: 12, marginBottom: 2 }}>
                  Volume: {cluster.total_volume.toLocaleString()}
                </div>
                <div style={{ color: '#F59E0B', fontSize: 12 }}>Avg difficulty: {cluster.avg_difficulty}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ ...PANEL, padding: 24, marginBottom: 16 }}>
        <h3 style={{ margin: '0 0 14px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Content Gap</h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))',
            gap: 12,
            marginBottom: 14,
          }}
        >
          <input
            value={gapDomain}
            onChange={(event) => setGapDomain(event.target.value)}
            placeholder="Your domain"
            style={INPUT_STYLE}
          />
          <input
            value={competitorDomains}
            onChange={(event) => setCompetitorDomains(event.target.value)}
            placeholder="competitor1.com, competitor2.com"
            style={INPUT_STYLE}
          />
        </div>
        <button onClick={runGapAnalysis} style={BTN_PRIMARY} disabled={loadingGap}>
          {loadingGap ? 'Computing…' : 'Run Content Gap'}
        </button>
      </div>

      {(gapProvider || gapProviderAttempts.length > 0 || gapTelemetry) && (
        <div style={{ ...PANEL, padding: 18, marginBottom: 16 }}>
          <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700, color: 'var(--text)' }}>
            Content Gap Provider Telemetry
          </h3>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))',
              gap: 10,
              marginBottom: 12,
            }}
          >
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Selected provider</div>
              <div style={{ color: 'var(--text)', fontWeight: 700, fontSize: 13 }}>{gapProvider || '-'}</div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Provider strategy</div>
              <div style={{ color: 'var(--muted)', fontWeight: 700, fontSize: 13 }}>{gapProviderStrategy || '-'}</div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Fallback response</div>
              <div style={{ color: gapFallbackUsed ? '#F59E0B' : '#10B981', fontWeight: 700, fontSize: 13 }}>
                {gapFallbackUsed ? 'yes' : 'no'}
              </div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Pipeline latency</div>
              <div style={{ color: '#06B6D4', fontWeight: 700, fontSize: 13 }}>
                {gapTelemetry ? `${gapTelemetry.pipeline_latency_ms} ms` : '-'}
              </div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Provider latency</div>
              <div style={{ color: '#06B6D4', fontWeight: 700, fontSize: 13 }}>
                {gapTelemetry ? `${gapTelemetry.provider_latency_total_ms} ms` : '-'}
              </div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Attempts</div>
              <div style={{ color: 'var(--text)', fontWeight: 700, fontSize: 13 }}>
                {gapTelemetry
                  ? `${gapTelemetry.attempt_count} total / ${gapTelemetry.attempted_live_providers} live`
                  : '-'}
              </div>
            </div>
            <div style={{ ...CARD, padding: 12 }}>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Failed live attempts</div>
              <div style={{ color: '#F59E0B', fontWeight: 700, fontSize: 13 }}>
                {gapTelemetry ? gapTelemetry.failed_live_attempts : '-'}
              </div>
            </div>
          </div>
          {gapFallbackReason && (
            <div style={{ color: '#F59E0B', fontSize: 12, marginBottom: 10 }}>
              Fallback response reason: {gapFallbackReason}
            </div>
          )}
          {gapProviderAttempts.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 220px), 1fr))', gap: 10 }}>
              {gapProviderAttempts.map((attempt, index) => (
                <div key={`${attempt.provider}-${attempt.status}-${index}`} style={{ ...CARD, padding: 10 }}>
                  <div style={{ color: 'var(--text)', fontSize: 13, fontWeight: 700, marginBottom: 4 }}>
                    {attempt.provider}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 2 }}>status: {attempt.status}</div>
                  <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 2 }}>
                    configured: {attempt.configured ? 'yes' : 'no'} | attempted: {attempt.attempted ? 'yes' : 'no'}
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 2 }}>
                    latency: {attempt.latency_ms} ms
                  </div>
                  <div style={{ color: 'var(--muted)', fontSize: 12, marginBottom: 2 }}>
                    {attempt.error_code ?? 'no error'}
                  </div>
                  {attempt.error_message && (
                    <div style={{ color: '#F59E0B', fontSize: 11 }}>{attempt.error_message}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {gapResults.length > 0 && (
        <div style={{ ...PANEL, overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['Keyword', 'Volume', 'Difficulty', 'Competitor Coverage', 'Est. Clicks', 'Recommended Asset'].map(
                  (header) => (
                    <th key={header} style={TABLE_TH}>
                      {header}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {gapResults.slice(0, 30).map((item) => (
                <tr key={`${item.keyword}-${item.recommended_content_type}`}>
                  <td style={TABLE_TD}>{item.keyword}</td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{item.search_volume.toLocaleString()}</td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{item.difficulty}</td>
                  <td style={{ ...TABLE_TD, color: '#F59E0B', fontWeight: 700 }}>{item.covered_by_competitors}</td>
                  <td style={{ ...TABLE_TD, color: '#10B981', fontWeight: 700 }}>
                    {item.estimated_monthly_clicks.toLocaleString()}
                  </td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{item.recommended_content_type}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Projects
// ---------------------------------------------------------------------------

function ProjectsTab() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [newDomain, setNewDomain] = useState('');
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const d = await apiGet<any>('/rank-tracker/projects');
      setProjects(d.projects ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const add = async () => {
    if (!newDomain) return;
    await apiSend('/rank-tracker/add-project', 'POST', { domain: newDomain });
    setNewDomain('');
    fetch();
  };

  const remove = async (id: string) => {
    await apiSend(`/rank-tracker/projects/${id}`, 'DELETE', undefined);
    fetch();
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 24px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Tracking Projects</h2>

      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>New Project</h3>
        <div style={{ display: 'flex', gap: 12 }}>
          <input
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            placeholder="example.com"
            style={{ ...INPUT_STYLE, maxWidth: 280 }}
          />
          <button onClick={add} style={BTN_PRIMARY}>
            + Create Project
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 220px), 1fr))', gap: 16 }}>
        {projects.map((p) => (
          <div key={p.id} style={CARD}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 12 }}>
              <div>
                <div style={{ fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>{p.domain}</div>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>{p.location}</div>
              </div>
              <button onClick={() => remove(p.id)} style={{ ...BTN_SM, color: '#dc2626', padding: '4px 8px' }}>
                ✕
              </button>
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#06B6D4', marginBottom: 8 }}>
              {p.tracking_keywords}
            </div>
            <div style={{ fontSize: 12, color: 'var(--muted)' }}>keywords tracked</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Competitors
// ---------------------------------------------------------------------------

function CompetitorsTab() {
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [newDomain, setNewDomain] = useState('');
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const d = await apiGet<any>('/rank-tracker/competitors');
      setCompetitors(d.competitors ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const add = async () => {
    if (!newDomain) return;
    await apiSend('/rank-tracker/competitors', 'POST', { domain: newDomain });
    setNewDomain('');
    fetch();
  };

  const remove = async (id: string) => {
    await apiSend(`/rank-tracker/competitors/${id}`, 'DELETE', undefined);
    fetch();
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 24px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Tracked Competitors</h2>

      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Add Competitor</h3>
        <div style={{ display: 'flex', gap: 12 }}>
          <input
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            placeholder="competitor.com"
            style={{ ...INPUT_STYLE, maxWidth: 280 }}
          />
          <button onClick={add} style={BTN_PRIMARY}>
            + Add Competitor
          </button>
        </div>
      </div>

      <div style={{ ...PANEL, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Domain', 'Authority', 'Organic Keywords', 'Est. Traffic', 'Action'].map((h) => (
                <th key={h} style={TABLE_TH}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ ...TABLE_TD, textAlign: 'center', color: 'var(--muted)' }}>
                  Loading…
                </td>
              </tr>
            ) : competitors.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ ...TABLE_TD, textAlign: 'center', color: 'var(--muted)' }}>
                  No competitors tracked yet.
                </td>
              </tr>
            ) : (
              competitors.map((c) => (
                <tr key={c.id}>
                  <td style={TABLE_TD}>
                    <a
                      href={`https://${c.domain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#06B6D4', textDecoration: 'none' }}
                    >
                      {c.domain}
                    </a>
                  </td>
                  <td
                    style={{
                      ...TABLE_TD,
                      fontWeight: 700,
                      color: c.authority_score >= 60 ? '#10B981' : c.authority_score >= 35 ? '#F59E0B' : '#dc2626',
                    }}
                  >
                    {c.authority_score}
                  </td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{c.organic_keywords.toLocaleString()}</td>
                  <td style={{ ...TABLE_TD, fontWeight: 700, color: '#06B6D4' }}>
                    {(c.organic_traffic_estimate / 1000).toFixed(0)}k
                  </td>
                  <td style={TABLE_TD}>
                    <button onClick={() => remove(c.id)} style={{ ...BTN_SM, color: '#dc2626' }}>
                      ✕
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: History (Timeseries)
// ---------------------------------------------------------------------------

function HistoryTab() {
  const [history, setHistory] = useState<any>(null);
  const [days, setDays] = useState(90);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    apiGet<any>(`/rank-tracker/history?days=${days}`)
      .then((d) => setHistory(d.history))
      .catch(() => setHistory(null))
      .finally(() => setLoading(false));
  }, [days]);

  if (loading) return <div style={{ color: 'var(--muted)', padding: 40, textAlign: 'center' }}>Loading…</div>;
  if (!history) return <div style={{ color: 'var(--muted)', padding: 40, textAlign: 'center' }}>No history data.</div>;

  const ts = history.timeseries || [];
  const maxPos = Math.max(1, ...ts.map((t: any) => t.avg_position || 1));

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Ranking History</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          {[7, 30, 90, 180, 365].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              style={{
                ...BTN_SM,
                borderColor: days === d ? '#06B6D4' : '#e7e9ef',
                color: days === d ? '#06B6D4' : 'var(--muted)',
              }}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      <div style={{ ...PANEL, padding: 24 }}>
        <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, marginBottom: 16 }}>
          AVERAGE POSITION OVER TIME
        </div>
        {ts.length === 0 ? (
          <div style={{ color: '#e7e9ef', textAlign: 'center', padding: 40 }}>No timeseries data.</div>
        ) : (
          <div style={{ display: 'flex', gap: 2, alignItems: 'flex-end', height: 150, overflowX: 'auto' }}>
            {ts.map((t: any, i: number) => (
              <div
                key={i}
                style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, minWidth: 20 }}
              >
                <div
                  style={{
                    width: 14,
                    height: Math.max(2, ((maxPos - (t.avg_position || maxPos)) / maxPos) * 120),
                    backgroundColor: '#06B6D4',
                    borderRadius: 2,
                  }}
                  title={`Pos: ${t.avg_position}`}
                />
                <div
                  style={{
                    fontSize: 8,
                    color: '#e7e9ef',
                    height: 30,
                    writingMode: 'vertical-rl',
                    transform: 'rotate(180deg)',
                  }}
                >
                  {t.date?.slice(5)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Forecasts
// ---------------------------------------------------------------------------

function ForecastsTab() {
  const [forecasts, setForecasts] = useState<any[]>([]);

  useEffect(() => {
    apiGet<any>('/rank-tracker/forecasts')
      .then((d) => setForecasts(d.forecasts ?? []))
      .catch(() => {});
  }, []);

  return (
    <div>
      <h2 style={{ margin: '0 0 24px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Traffic Forecast by Rank</h2>

      <div style={{ ...PANEL, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Rank Position', 'Est. CTR', 'Monthly Clicks (10k searches)', 'Relative Traffic'].map((h) => (
                <th key={h} style={TABLE_TH}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {forecasts.map((f, i) => (
              <tr key={i}>
                <td style={{ ...TABLE_TD, fontWeight: 700, color: '#06B6D4' }}>#{f.position}</td>
                <td style={{ ...TABLE_TD, color: '#F59E0B' }}>{f.estimated_ctr}</td>
                <td style={{ ...TABLE_TD, fontWeight: 700, color: '#10B981' }}>
                  {f.estimated_monthly_clicks.toLocaleString()} clicks
                </td>
                <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{f.relative_traffic}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ ...PANEL, padding: 20, marginTop: 20 }}>
        <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, marginBottom: 12 }}>KEY INSIGHT</div>
        <p style={{ margin: 0, color: 'var(--muted)', fontSize: 14, lineHeight: 1.6 }}>
          Based on typical click-through rates, moving from rank 10 to rank 3 can increase your monthly organic traffic
          by <strong style={{ color: '#10B981' }}>~7-10x</strong>. Focus on improving top keywords to maximize traffic
          impact.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Analytics
// ---------------------------------------------------------------------------

function AnalyticsTab() {
  const [analytics, setAnalytics] = useState<any>(null);

  useEffect(() => {
    apiGet<any>('/rank-tracker/analytics')
      .then((d) => setAnalytics(d.analytics))
      .catch(() => {});
  }, []);

  if (!analytics) return <div style={{ color: 'var(--muted)', padding: 40 }}>Loading…</div>;

  return (
    <div>
      <h2 style={{ margin: '0 0 24px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Ranking Analytics</h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 260px), 1fr))', gap: 14, marginBottom: 24 }}>
        <MetricCard label="Total Keywords" value={analytics.total_keywords} />
        <MetricCard label="Improved 30d" value={analytics.improved_count} color="#34D399" />
        <MetricCard label="Declined 30d" value={analytics.declined_count} color="#dc2626" />
        <MetricCard label="Stable" value={analytics.stable_count} color="var(--brand)" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 }}>
        <div style={{ ...PANEL, padding: 20 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: '#10B981' }}>⬆ Top Gainers</h3>
          {analytics.top_movers_up.slice(0, 5).map((m: any, i: number) => (
            <div
              key={i}
              style={{ marginBottom: 12, paddingBottom: 12, borderBottom: i < 4 ? '1px solid var(--line)' : 'none' }}
            >
              <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>{m.keyword}</div>
              <div style={{ fontSize: 12, color: '#34D399' }}>
                #{m.current_position} (was #{Math.round(m.previous_position)})
              </div>
            </div>
          ))}
        </div>

        <div style={{ ...PANEL, padding: 20 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: '#dc2626' }}>⬇ Top Decliners</h3>
          {analytics.top_movers_down.slice(0, 5).map((m: any, i: number) => (
            <div
              key={i}
              style={{ marginBottom: 12, paddingBottom: 12, borderBottom: i < 4 ? '1px solid var(--line)' : 'none' }}
            >
              <div style={{ fontWeight: 600, color: 'var(--text)', marginBottom: 4 }}>{m.keyword}</div>
              <div style={{ fontSize: 12, color: '#dc2626' }}>
                #{m.current_position} (was #{Math.round(m.previous_position)})
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Alerts
// ---------------------------------------------------------------------------

function AlertsTab() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [keywords, setKeywords] = useState<Keyword[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ keyword_id: '', alert_type: 'rank_drop', threshold: 5 });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      apiGet<any>('/rank-tracker/alerts').then((d) => setAlerts(d.alerts ?? [])),
      apiGet<any>('/rank-tracker/tracked-keywords').then((d) => setKeywords(d.keywords ?? [])),
    ]).catch(() => {});
  }, []);

  const add = async () => {
    if (!form.keyword_id) return;
    setLoading(true);
    try {
      await apiSend('/rank-tracker/alerts/set', 'POST', {
        keyword_id: form.keyword_id,
        alert_type: form.alert_type,
        threshold: form.threshold,
      });
      setForm({ keyword_id: '', alert_type: 'rank_drop', threshold: 5 });
      setShowAdd(false);
      const d = await apiGet<any>('/rank-tracker/alerts');
      setAlerts(d.alerts ?? []);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Rank Alerts</h2>
        <button onClick={() => setShowAdd(!showAdd)} style={BTN_PRIMARY}>
          + New Alert
        </button>
      </div>

      {showAdd && (
        <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Set Alert</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 12 }}>
            <div>
              <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                Keyword
              </label>
              <select
                value={form.keyword_id}
                onChange={(e) => setForm((f) => ({ ...f, keyword_id: e.target.value }))}
                style={INPUT_STYLE}
              >
                <option value="">Select keyword…</option>
                {keywords.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.keyword}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                Alert Type
              </label>
              <select
                value={form.alert_type}
                onChange={(e) => setForm((f) => ({ ...f, alert_type: e.target.value }))}
                style={INPUT_STYLE}
              >
                <option value="rank_drop">Rank Drop</option>
                <option value="rank_gain">Rank Gain</option>
              </select>
            </div>
            <div>
              <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
                Threshold (positions)
              </label>
              <input
                type="number"
                value={form.threshold}
                onChange={(e) => setForm((f) => ({ ...f, threshold: parseInt(e.target.value) }))}
                style={INPUT_STYLE}
                min={1}
                max={50}
              />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button onClick={add} style={BTN_PRIMARY} disabled={loading}>
              {loading ? 'Creating…' : 'Create Alert'}
            </button>
            <button onClick={() => setShowAdd(false)} style={BTN_SM}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div style={{ ...PANEL, padding: 0 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Keyword', 'Alert Type', 'Threshold', 'Status'].map((h) => (
                <th key={h} style={TABLE_TH}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ ...TABLE_TD, textAlign: 'center', color: 'var(--muted)' }}>
                  No alerts configured.
                </td>
              </tr>
            ) : (
              alerts.map((a, i) => (
                <tr key={i}>
                  <td style={TABLE_TD}>{a.keyword}</td>
                  <td style={{ ...TABLE_TD, color: a.alert_type === 'rank_drop' ? '#dc2626' : '#34D399' }}>
                    {a.alert_type === 'rank_drop' ? '📉 Rank Drop' : '📈 Rank Gain'}
                  </td>
                  <td style={{ ...TABLE_TD, fontWeight: 700 }}>{a.threshold} positions</td>
                  <td style={{ ...TABLE_TD, color: a.is_active ? '#34D399' : 'var(--muted)' }}>
                    {a.is_active ? '✓ Active' : 'Inactive'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: SERP Check
// ---------------------------------------------------------------------------

function SERPCheckTab() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const check = async () => {
    if (!query.trim()) return;
    const kws = query
      .split('\n')
      .map((k) => k.trim())
      .filter(Boolean);
    setLoading(true);
    try {
      const d = await apiSend<any>('/rank-tracker/positions/check', 'POST', { keywords: kws });
      setResults(d.serp_check ?? []);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 24px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Manual SERP Check</h2>

      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 8 }}>
          Enter keywords (one per line)
        </label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="digital marketing\nSEO tools\nkeyword research"
          style={{ ...INPUT_STYLE, minHeight: 120, fontFamily: 'monospace', padding: 12, resize: 'vertical' }}
        />
        <button onClick={check} style={{ ...BTN_PRIMARY, marginTop: 16 }} disabled={loading}>
          {loading ? 'Checking…' : '🔍 Check SERP'}
        </button>
      </div>

      {results.length > 0 && (
        <div style={{ ...PANEL, overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['Keyword', 'Position', 'Search Volume', 'Keyword Difficulty', 'CTR Est.'].map((h) => (
                  <th key={h} style={TABLE_TH}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i}>
                  <td style={TABLE_TD}>{r.keyword}</td>
                  <td
                    style={{
                      ...TABLE_TD,
                      fontWeight: 700,
                      color: r.position <= 10 ? '#10B981' : r.position <= 30 ? '#F59E0B' : '#dc2626',
                    }}
                  >
                    {r.position}
                  </td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{r.search_volume.toLocaleString()}</td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{r.keyword_difficulty}</td>
                  <td style={{ ...TABLE_TD, fontWeight: 600, color: 'var(--brand)' }}>{r.ctr_estimate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
