'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { apiGet, apiSend } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Overview {
  authority_score: number;
  authority_score_label: string;
  total_backlinks: number;
  active_backlinks: number;
  referring_domains: number;
  dofollow_count: number;
  dofollow_pct: number;
  nofollow_count: number;
  new_backlinks_30d: number;
  lost_backlinks_30d: number;
  toxic_count: number;
  suspicious_count: number;
  avg_source_authority: number;
  tracked_domains: number;
}

interface Backlink {
  id: string;
  source_domain: string;
  source_url: string;
  target_url: string;
  anchor_text: string;
  link_type: string;
  link_follow: string;
  source_authority: number;
  status: string;
  toxic_score: number;
  is_new: boolean;
  is_lost: boolean;
  first_seen: string;
  last_seen: string;
  signals?: string[];
}

interface Prospect {
  id: string;
  domain: string;
  target_page: string;
  authority_score: number;
  contact_email: string;
  status: string;
  pitch_sent: boolean;
  notes: string;
}

interface AuditResult {
  id: string;
  domain: string;
  total_links_audited: number;
  toxic_count: number;
  suspicious_count: number;
  healthy_count: number;
  overall_risk_pct: number;
  risk_level: string;
  results: Backlink[];
  audited_at: string;
}

interface Analytics {
  timeseries: { week: string; new_backlinks: number; lost_backlinks: number }[];
  anchor_distribution: { anchor: string; count: number }[];
  follow_distribution: Record<string, number>;
  authority_buckets: Record<string, number>;
  total_analyzed: number;
  days: number;
}

interface GapOpportunity {
  domain: string;
  authority_score: number;
  competitor_count: number;
}

interface GapResult {
  your_domain: string;
  your_authority_score: number;
  your_referring_domains: number;
  competitors: {
    domain: string;
    authority_score: number;
    referring_domains: number;
    exclusive_domains: number;
    shared_domains: number;
  }[];
  unique_opportunities: number;
  opportunities: GapOpportunity[];
  analyzed_at: string;
}

type OverviewResponse = { overview?: Overview | null };
type BacklinksResponse = { backlinks?: Backlink[]; total?: number; pages?: number };
type AuditMutationResponse = { audit: AuditResult };
type AuditHistoryResponse = { audits?: AuditResult[] };
type GapAnalysisResponse = { gap_analysis: GapResult };
type ProspectsResponse = { prospects?: Prospect[] };
type AnalyticsResponse = { analytics: Analytics };
type AuthorityScoreResponse = {
  authority_score: { domain: string; score: number; label: string; your_score: number; delta: number };
};
type DisavowResponse = { disavow?: { content?: string } };
type DomainsResponse = {
  domains?: { id: string; domain: string; label: string; authority_score: number; created_at: string }[];
};

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
const BADGE_DOFOLLOW: React.CSSProperties = {
  backgroundColor: '#d1fae5',
  color: '#10B981',
  borderRadius: 4,
  padding: '2px 7px',
  fontSize: 11,
  fontWeight: 600,
};
const BADGE_NOFOLLOW: React.CSSProperties = {
  backgroundColor: 'var(--card)',
  color: 'var(--brand)',
  borderRadius: 4,
  padding: '2px 7px',
  fontSize: 11,
  fontWeight: 600,
};
const BADGE_TOXIC: React.CSSProperties = {
  backgroundColor: '#fee2e2',
  color: '#dc2626',
  borderRadius: 4,
  padding: '2px 7px',
  fontSize: 11,
  fontWeight: 600,
};
const BADGE_SUSPICIOUS: React.CSSProperties = {
  backgroundColor: '#fef3c7',
  color: '#FB923C',
  borderRadius: 4,
  padding: '2px 7px',
  fontSize: 11,
  fontWeight: 600,
};
const BADGE_HEALTHY: React.CSSProperties = {
  backgroundColor: '#dcfce7',
  color: '#34D399',
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
  'Backlinks',
  'Audit',
  'Gap Analysis',
  'Prospects',
  'Analytics',
  'Authority Score',
  'Disavow',
  'Domains',
] as const;
type Tab = (typeof TABS)[number];

// ---------------------------------------------------------------------------
// Utility components
// ---------------------------------------------------------------------------

function ScoreRing({ score, color, size = 120 }: { score: number; color: string; size?: number }) {
  const r = (size - 20) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - score / 100);
  return (
    <svg width={size} height={size}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#eef0f4" strokeWidth={10} />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={r}
        fill="none"
        stroke={color}
        strokeWidth={10}
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text
        x={size / 2}
        y={size / 2 + 6}
        textAnchor="middle"
        fill={color}
        fontSize={size === 120 ? 24 : 18}
        fontWeight="700"
      >
        {score}
      </text>
    </svg>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = status?.toLowerCase();
  const style = s === 'toxic' ? BADGE_TOXIC : s === 'suspicious' ? BADGE_SUSPICIOUS : BADGE_HEALTHY;
  return <span style={style}>{status}</span>;
}

function FollowBadge({ follow }: { follow: string }) {
  return <span style={follow === 'dofollow' ? BADGE_DOFOLLOW : BADGE_NOFOLLOW}>{follow}</span>;
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

export default function BacklinkIntelligencePage() {
  const [tab, setTab] = useState<Tab>('Overview');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [ovLoading, setOvLoading] = useState(false);

  const fetchOverview = useCallback(async () => {
    setOvLoading(true);
    try {
      const d = await apiGet<OverviewResponse>('/backlink-intel/overview');
      setOverview(d.overview ?? null);
    } catch {
      setOverview(null);
    } finally {
      setOvLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const authorityColor = (score: number) => (score >= 60 ? '#10B981' : score >= 35 ? '#F59E0B' : '#dc2626');

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
          <span style={{ fontSize: 32 }}>🔗</span>
          <div>
            <h1 style={{ margin: 0, fontSize: 26, fontWeight: 800, color: 'var(--text)' }}>Backlink Intelligence</h1>
            <p style={{ margin: 0, color: 'var(--muted)', fontSize: 14 }}>
              Semrush-grade backlink analytics: 43T-link database, Authority Score, toxicity audit, gap analysis &amp;
              link building
            </p>
          </div>
        </div>
        {/* Tab bar */}
        <div style={{ display: 'flex', gap: 2, marginTop: 20, overflowX: 'auto' }}>
          {TABS.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
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
        {/* Overview Tab */}
        {tab === 'Overview' && (
          <OverviewTab
            overview={overview}
            loading={ovLoading}
            authorityColor={authorityColor}
            onRefresh={fetchOverview}
          />
        )}
        {tab === 'Backlinks' && <BacklinksTab />}
        {tab === 'Audit' && <AuditTab />}
        {tab === 'Gap Analysis' && <GapAnalysisTab />}
        {tab === 'Prospects' && <ProspectsTab />}
        {tab === 'Analytics' && <AnalyticsTab />}
        {tab === 'Authority Score' && <AuthorityScoreTab />}
        {tab === 'Disavow' && <DisavowTab />}
        {tab === 'Domains' && <DomainsTab onDomainChange={fetchOverview} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Overview
// ---------------------------------------------------------------------------

function OverviewTab({
  overview,
  loading,
  authorityColor,
  onRefresh,
}: {
  overview: Overview | null;
  loading: boolean;
  authorityColor: (s: number) => string;
  onRefresh: () => void;
}) {
  if (!overview) {
    return (
      <div style={PANEL}>
        <div style={{ color: 'var(--text)', fontSize: 15, fontWeight: 700, marginBottom: 8 }}>Domain Overview</div>
        <div style={{ color: '#dc2626', fontSize: 13 }}>Live backlink overview is unavailable in fail-closed mode.</div>
      </div>
    );
  }

  const ov = overview;
  const color = authorityColor(ov.authority_score);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Domain Overview</h2>
        <button onClick={onRefresh} style={BTN_SM} disabled={loading}>
          {loading ? 'Loading…' : '↻ Refresh'}
        </button>
      </div>

      {/* Authority Score + Key Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 32, marginBottom: 32 }}>
        <div
          style={{
            ...PANEL,
            padding: 28,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 8,
            minWidth: 180,
          }}
        >
          <div style={{ color: 'var(--muted)', fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Authority Score</div>
          <ScoreRing score={ov.authority_score} color={color} size={130} />
          <div style={{ color, fontWeight: 700, fontSize: 15 }}>{ov.authority_score_label}</div>
          <div style={{ color: '#e7e9ef', fontSize: 12, textAlign: 'center' }}>Based on backlink profile quality</div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 160px), 1fr))', gap: 14 }}>
          <MetricCard
            label="Total Backlinks"
            value={ov.total_backlinks.toLocaleString()}
            sub={`${ov.active_backlinks} active`}
          />
          <MetricCard
            label="Referring Domains"
            value={ov.referring_domains.toLocaleString()}
            sub="Unique linking domains"
            color="var(--brand)"
          />
          <MetricCard
            label="Dofollow %"
            value={`${ov.dofollow_pct}%`}
            sub={`${ov.dofollow_count} dofollow links`}
            color="#10B981"
          />
          <MetricCard label="New (30d)" value={`+${ov.new_backlinks_30d}`} sub="New backlinks" color="#34D399" />
          <MetricCard label="Lost (30d)" value={`-${ov.lost_backlinks_30d}`} sub="Lost backlinks" color="#dc2626" />
          <MetricCard
            label="Toxic Links"
            value={ov.toxic_count}
            sub={`${ov.suspicious_count} suspicious`}
            color="#dc2626"
          />
          <MetricCard
            label="Avg Source Authority"
            value={ov.avg_source_authority}
            sub="Avg linking domain score"
            color="#F59E0B"
          />
          <MetricCard label="Tracked Domains" value={ov.tracked_domains} sub="Monitored domains" color="var(--brand)" />
        </div>
      </div>

      {/* Health summary */}
      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Link Health Breakdown</h3>
        {[
          {
            label: 'Healthy',
            count: ov.active_backlinks - ov.toxic_count - ov.suspicious_count,
            color: '#10B981',
            total: ov.active_backlinks,
          },
          { label: 'Suspicious', count: ov.suspicious_count, color: '#F59E0B', total: ov.active_backlinks },
          { label: 'Toxic', count: ov.toxic_count, color: '#dc2626', total: ov.active_backlinks },
        ].map(({ label, count, color: c, total }) => (
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
                  width: `${Math.max(0, Math.min(100, (count / Math.max(1, total)) * 100))}%`,
                  transition: 'width 0.5s',
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Follow distribution */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 }}>
        <div style={{ ...PANEL, padding: 20 }}>
          <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, marginBottom: 12 }}>FOLLOW TYPE SPLIT</div>
          {[
            { label: 'Dofollow', count: ov.dofollow_count, color: '#10B981' },
            { label: 'Nofollow', count: ov.nofollow_count, color: 'var(--brand)' },
          ].map(({ label, count, color: c }) => (
            <div
              key={label}
              style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, alignItems: 'center' }}
            >
              <span style={{ fontSize: 13, color: 'var(--muted)' }}>{label}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: c }}>{count}</span>
            </div>
          ))}
        </div>
        <div style={{ ...PANEL, padding: 20 }}>
          <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, marginBottom: 12 }}>QUICK ACTIONS</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {[
              'Run Backlink Audit',
              'Find Link Opportunities',
              'Download Disavow File',
              'Add Competitor for Gap Analysis',
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
// Tab: Backlinks
// ---------------------------------------------------------------------------

function BacklinksTab() {
  const [backlinks, setBacklinks] = useState<Backlink[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [followFilter, setFollowFilter] = useState('');

  const fetchBacklinks = useCallback(
    async (p: number) => {
      setLoading(true);
      try {
        const params = new URLSearchParams({ page: String(p), page_size: '20' });
        if (search) params.set('search', search);
        if (statusFilter) params.set('status', statusFilter);
        if (followFilter) params.set('link_follow', followFilter);
        const d = await apiGet<BacklinksResponse>(`/backlink-intel/backlinks?${params}`);
        setBacklinks(d.backlinks ?? []);
        setTotal(d.total ?? 0);
        setPages(d.pages ?? 1);
        setPage(p);
      } catch {
        setBacklinks([]);
      } finally {
        setLoading(false);
      }
    },
    [search, statusFilter, followFilter]
  );

  useEffect(() => {
    fetchBacklinks(1);
  }, [fetchBacklinks]);

  const updateStatus = async (id: string, status: string) => {
    await apiSend(`/backlink-intel/backlinks/${id}/status`, 'PATCH', { status });
    fetchBacklinks(page);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Backlink Explorer</h2>
        <span style={{ color: 'var(--muted)', fontSize: 13 }}>{total.toLocaleString()} backlinks</span>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <input
          placeholder="Search anchor, domain, URL…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ ...INPUT_STYLE, maxWidth: 280 }}
        />
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ ...INPUT_STYLE, maxWidth: 160 }}
        >
          <option value="">All statuses</option>
          <option value="healthy">Healthy</option>
          <option value="suspicious">Suspicious</option>
          <option value="toxic">Toxic</option>
        </select>
        <select
          value={followFilter}
          onChange={(e) => setFollowFilter(e.target.value)}
          style={{ ...INPUT_STYLE, maxWidth: 160 }}
        >
          <option value="">All follow types</option>
          <option value="dofollow">Dofollow</option>
          <option value="nofollow">Nofollow</option>
          <option value="sponsored">Sponsored</option>
          <option value="ugc">UGC</option>
        </select>
        <button onClick={() => fetchBacklinks(1)} style={BTN_PRIMARY}>
          Search
        </button>
      </div>

      {/* Table */}
      <div style={{ ...PANEL, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Source Domain', 'Anchor Text', 'Follow', 'Type', 'Authority', 'Status', 'First Seen', 'Actions'].map(
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
            ) : backlinks.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ ...TABLE_TD, textAlign: 'center', color: 'var(--muted)' }}>
                  No backlinks found
                </td>
              </tr>
            ) : (
              backlinks.map((bl) => (
                <tr key={bl.id}>
                  <td style={TABLE_TD}>
                    <a
                      href={bl.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#06B6D4', textDecoration: 'none' }}
                    >
                      {bl.source_domain}
                    </a>
                    {bl.is_new && <span style={{ ...BADGE_HEALTHY, marginLeft: 6, fontSize: 10 }}>NEW</span>}
                    {bl.is_lost && <span style={{ ...BADGE_TOXIC, marginLeft: 6, fontSize: 10 }}>LOST</span>}
                  </td>
                  <td
                    style={{
                      ...TABLE_TD,
                      maxWidth: 180,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {bl.anchor_text || '—'}
                  </td>
                  <td style={TABLE_TD}>
                    <FollowBadge follow={bl.link_follow} />
                  </td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{bl.link_type}</td>
                  <td
                    style={{
                      ...TABLE_TD,
                      fontWeight: 700,
                      color: bl.source_authority >= 60 ? '#10B981' : bl.source_authority >= 35 ? '#F59E0B' : '#dc2626',
                    }}
                  >
                    {bl.source_authority}
                  </td>
                  <td style={TABLE_TD}>
                    <StatusBadge status={bl.status} />
                  </td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)', fontSize: 12 }}>{bl.first_seen?.slice(0, 10)}</td>
                  <td style={TABLE_TD}>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button
                        onClick={() => updateStatus(bl.id, bl.status === 'toxic' ? 'healthy' : 'toxic')}
                        style={{ ...BTN_SM, color: bl.status === 'toxic' ? '#34D399' : '#dc2626' }}
                      >
                        {bl.status === 'toxic' ? '✓ Clear' : '⚠ Flag'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'center', alignItems: 'center' }}>
        <button onClick={() => fetchBacklinks(Math.max(1, page - 1))} disabled={page <= 1} style={BTN_SM}>
          ← Prev
        </button>
        <span style={{ color: 'var(--muted)', fontSize: 13 }}>
          Page {page} of {pages}
        </span>
        <button onClick={() => fetchBacklinks(Math.min(pages, page + 1))} disabled={page >= pages} style={BTN_SM}>
          Next →
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Audit
// ---------------------------------------------------------------------------

function AuditTab() {
  const [domain, setDomain] = useState('yourdomain.com');
  const [audit, setAudit] = useState<AuditResult | null>(null);
  const [history, setHistory] = useState<AuditResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [view, setView] = useState<'run' | 'history'>('run');

  const runAudit = async () => {
    setLoading(true);
    try {
      const d = await apiSend<AuditMutationResponse>('/backlink-intel/audit', 'POST', { domain });
      setAudit(d.audit);
      setView('run');
    } catch {
      setAudit(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    const d = await apiGet<AuditHistoryResponse>('/backlink-intel/audit/history');
    setHistory(d.audits ?? []);
    setView('history');
  };

  const riskColor = (level: string) =>
    level === 'Critical' ? '#dc2626' : level === 'Moderate' ? '#F59E0B' : '#10B981';

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Backlink Audit</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={fetchHistory} style={BTN_SM}>
            Audit History
          </button>
        </div>
      </div>

      {/* Run audit */}
      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
          <input
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="yourdomain.com"
            style={{ ...INPUT_STYLE, maxWidth: 320 }}
          />
          <button onClick={runAudit} style={BTN_PRIMARY} disabled={loading}>
            {loading ? 'Running audit…' : '🔍 Run Audit'}
          </button>
        </div>
        <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13 }}>
          Scores every backlink for toxicity, flags suspicious links, and identifies disavow candidates.
        </p>
      </div>

      {view === 'history' && (
        <div style={{ ...PANEL, padding: 20 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Audit History</h3>
          {history.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>No past audits yet.</p>
          ) : (
            history.map((a) => (
              <div key={a.id} style={{ ...CARD, marginBottom: 10 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: 600, color: 'var(--text)' }}>{a.domain}</div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                      {a.audited_at?.slice(0, 16)?.replace('T', ' ')}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ color: '#dc2626', fontWeight: 700 }}>{a.toxic_count}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)' }}>Toxic</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ color: '#F59E0B', fontWeight: 700 }}>{a.suspicious_count}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)' }}>Suspicious</div>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                      <div style={{ color: '#10B981', fontWeight: 700 }}>{a.healthy_count}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)' }}>Healthy</div>
                    </div>
                    <span
                      style={{
                        ...BADGE_TOXIC,
                        ...(a.risk_level !== 'Critical' ? {} : {}),
                        backgroundColor:
                          a.risk_level === 'Critical' ? '#fee2e2' : a.risk_level === 'Moderate' ? '#fef3c7' : '#dcfce7',
                        color: riskColor(a.risk_level),
                      }}
                    >
                      {a.risk_level}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {audit && view === 'run' && (
        <div>
          {/* Audit summary */}
          <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 24, marginBottom: 24 }}>
            <div
              style={{ ...PANEL, padding: 28, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}
            >
              <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600 }}>OVERALL RISK</div>
              <ScoreRing score={Math.round(audit.overall_risk_pct)} color={riskColor(audit.risk_level)} size={120} />
              <span style={{ color: riskColor(audit.risk_level), fontWeight: 700 }}>{audit.risk_level} Risk</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 14 }}>
              <MetricCard label="Toxic Links" value={audit.toxic_count} color="#dc2626" sub="Recommend disavow" />
              <MetricCard
                label="Suspicious Links"
                value={audit.suspicious_count}
                color="#F59E0B"
                sub="Monitor closely"
              />
              <MetricCard label="Healthy Links" value={audit.healthy_count} color="#10B981" sub="Safe links" />
            </div>
          </div>

          {/* Results table */}
          <div style={{ ...PANEL, overflowX: 'auto' }}>
            <div
              style={{
                padding: '14px 20px',
                borderBottom: '1px solid var(--line)',
                fontWeight: 600,
                color: 'var(--text)',
                fontSize: 14,
              }}
            >
              Audit Results ({audit.total_links_audited} links)
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Source Domain', 'Anchor', 'Toxic Score', 'Status', 'Signals'].map((h) => (
                    <th key={h} style={TABLE_TH}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {audit.results.slice(0, 30).map((bl) => (
                  <tr key={bl.id}>
                    <td style={TABLE_TD}>{bl.source_domain}</td>
                    <td
                      style={{
                        ...TABLE_TD,
                        color: 'var(--muted)',
                        maxWidth: 160,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {bl.anchor_text || '—'}
                    </td>
                    <td
                      style={{
                        ...TABLE_TD,
                        fontWeight: 700,
                        color: bl.toxic_score >= 60 ? '#dc2626' : bl.toxic_score >= 30 ? '#F59E0B' : '#10B981',
                      }}
                    >
                      {bl.toxic_score}
                    </td>
                    <td style={TABLE_TD}>
                      <StatusBadge status={bl.status} />
                    </td>
                    <td style={{ ...TABLE_TD, color: 'var(--muted)', fontSize: 12 }}>
                      {(bl.signals ?? []).length === 0 ? '—' : (bl.signals ?? []).join('; ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Gap Analysis
// ---------------------------------------------------------------------------

function GapAnalysisTab() {
  const [yourDomain, setYourDomain] = useState('yourdomain.com');
  const [competitors, setCompetitors] = useState(['ahrefs.com', 'moz.com', '', '']);
  const [result, setResult] = useState<GapResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runGap = async () => {
    const comps = competitors.filter(Boolean);
    if (comps.length === 0) return;
    setLoading(true);
    try {
      const d = await apiSend<GapAnalysisResponse>('/backlink-intel/gap-analysis', 'POST', {
        your_domain: yourDomain,
        competitor_domains: comps.slice(0, 4),
      });
      setResult(d.gap_analysis);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 24px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Backlink Gap Analysis</h2>
      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 16 }}>
          <div>
            <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
              YOUR DOMAIN
            </label>
            <input value={yourDomain} onChange={(e) => setYourDomain(e.target.value)} style={INPUT_STYLE} />
          </div>
          <div>
            <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
              COMPETITOR 1
            </label>
            <input
              value={competitors[0]}
              onChange={(e) => {
                const c = [...competitors];
                c[0] = e.target.value;
                setCompetitors(c);
              }}
              style={INPUT_STYLE}
            />
          </div>
          <div>
            <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
              COMPETITOR 2
            </label>
            <input
              value={competitors[1]}
              onChange={(e) => {
                const c = [...competitors];
                c[1] = e.target.value;
                setCompetitors(c);
              }}
              style={INPUT_STYLE}
            />
          </div>
          <div>
            <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
              COMPETITOR 3 (optional)
            </label>
            <input
              value={competitors[2]}
              onChange={(e) => {
                const c = [...competitors];
                c[2] = e.target.value;
                setCompetitors(c);
              }}
              style={INPUT_STYLE}
            />
          </div>
          <div>
            <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 6 }}>
              COMPETITOR 4 (optional)
            </label>
            <input
              value={competitors[3]}
              onChange={(e) => {
                const c = [...competitors];
                c[3] = e.target.value;
                setCompetitors(c);
              }}
              style={INPUT_STYLE}
            />
          </div>
        </div>
        <button onClick={runGap} style={BTN_PRIMARY} disabled={loading}>
          {loading ? 'Analyzing…' : '🔍 Run Gap Analysis'}
        </button>
      </div>

      {result && (
        <div>
          {/* Competitor comparison */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 200px), 1fr))',
              gap: 14,
              marginBottom: 24,
            }}
          >
            <div style={{ ...CARD, borderColor: '#06B6D4' }}>
              <div style={{ color: 'var(--muted)', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>YOUR DOMAIN</div>
              <div style={{ color: '#06B6D4', fontWeight: 700, fontSize: 15 }}>{result.your_domain}</div>
              <div style={{ marginTop: 8 }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)' }}>{result.your_authority_score}</div>
                <div style={{ color: 'var(--muted)', fontSize: 12 }}>Authority Score</div>
              </div>
              <div style={{ marginTop: 8, color: 'var(--muted)', fontSize: 13 }}>
                {result.your_referring_domains} referring domains
              </div>
            </div>
            {result.competitors.map((c) => (
              <div key={c.domain} style={CARD}>
                <div style={{ color: 'var(--muted)', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>COMPETITOR</div>
                <div style={{ color: 'var(--brand)', fontWeight: 700, fontSize: 15 }}>{c.domain}</div>
                <div style={{ marginTop: 8 }}>
                  <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)' }}>{c.authority_score}</div>
                  <div style={{ color: 'var(--muted)', fontSize: 12 }}>Authority Score</div>
                </div>
                <div style={{ marginTop: 8, fontSize: 12, color: 'var(--muted)' }}>
                  {c.referring_domains} referring domains
                  <br />
                  <span style={{ color: '#dc2626' }}>{c.exclusive_domains} links you don&apos;t have</span>
                </div>
              </div>
            ))}
          </div>

          {/* Opportunities */}
          <div style={{ ...PANEL, padding: 0 }}>
            <div
              style={{
                padding: '14px 20px',
                borderBottom: '1px solid var(--line)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div style={{ fontWeight: 600, color: 'var(--text)', fontSize: 14 }}>
                🎯 Link Opportunities ({result.unique_opportunities})
              </div>
              <div style={{ color: 'var(--muted)', fontSize: 12 }}>Domains linking to competitors but not you</div>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['Domain', 'Authority Score', 'Action'].map((h) => (
                    <th key={h} style={TABLE_TH}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.opportunities.slice(0, 25).map((op, i) => (
                  <tr key={i}>
                    <td style={TABLE_TD}>
                      <a
                        href={`https://${op.domain}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: '#06B6D4', textDecoration: 'none' }}
                      >
                        {op.domain}
                      </a>
                    </td>
                    <td
                      style={{
                        ...TABLE_TD,
                        fontWeight: 700,
                        color: op.authority_score >= 60 ? '#10B981' : op.authority_score >= 35 ? '#F59E0B' : '#dc2626',
                      }}
                    >
                      {op.authority_score}
                    </td>
                    <td style={TABLE_TD}>
                      <button style={BTN_SM}>+ Add to Prospects</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Prospects
// ---------------------------------------------------------------------------

function ProspectsTab() {
  const [prospects, setProspects] = useState<Prospect[]>([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ domain: '', target_page: '', contact_email: '', notes: '' });

  const fetchProspects = useCallback(async () => {
    setLoading(true);
    try {
      const params = statusFilter ? `?status=${statusFilter}` : '';
      const d = await apiGet<ProspectsResponse>(`/backlink-intel/prospects${params}`);
      setProspects(d.prospects ?? []);
    } catch {
      setProspects([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchProspects();
  }, [fetchProspects]);

  const addProspect = async () => {
    if (!form.domain) return;
    await apiSend('/backlink-intel/prospects', 'POST', form);
    setForm({ domain: '', target_page: '', contact_email: '', notes: '' });
    setShowAdd(false);
    fetchProspects();
  };

  const updateStatus = async (id: string, status: string) => {
    await apiSend(`/backlink-intel/prospects/${id}/status`, 'PATCH', { status });
    fetchProspects();
  };

  const statusOptions = ['new', 'contacted', 'replied', 'won', 'rejected'];
  const statusColor: Record<string, string> = {
    new: 'var(--muted)',
    contacted: 'var(--brand)',
    replied: '#F59E0B',
    won: '#10B981',
    rejected: '#dc2626',
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Link Building Prospects</h2>
        <button onClick={() => setShowAdd(!showAdd)} style={BTN_PRIMARY}>
          + Add Prospect
        </button>
      </div>

      {showAdd && (
        <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>New Prospect</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 12 }}>
            {[
              { key: 'domain', label: 'Domain*', placeholder: 'example.com' },
              { key: 'contact_email', label: 'Contact Email', placeholder: 'editor@example.com' },
              { key: 'target_page', label: 'Target Page', placeholder: 'https://example.com/resources' },
              { key: 'notes', label: 'Notes', placeholder: 'Good fit for guest post…' },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 4 }}>
                  {label}
                </label>
                <input
                  value={form[key as keyof typeof form]}
                  onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                  placeholder={placeholder}
                  style={INPUT_STYLE}
                />
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
            <button onClick={addProspect} style={BTN_PRIMARY}>
              Save Prospect
            </button>
            <button onClick={() => setShowAdd(false)} style={BTN_SM}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Pipeline summary */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {['', ...statusOptions].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            style={{
              ...BTN_SM,
              color: s ? statusColor[s] : 'var(--muted)',
              borderColor: statusFilter === s ? '#06B6D4' : '#e7e9ef',
            }}
          >
            {s || 'All'} {s && `(${prospects.filter((p) => !s || p.status === s).length})`}
          </button>
        ))}
      </div>

      {/* Prospects table */}
      <div style={{ ...PANEL, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Domain', 'Authority', 'Contact', 'Status', 'Pitch Sent', 'Actions'].map((h) => (
                <th key={h} style={TABLE_TH}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} style={{ ...TABLE_TD, textAlign: 'center', color: 'var(--muted)' }}>
                  Loading…
                </td>
              </tr>
            ) : prospects.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ ...TABLE_TD, textAlign: 'center', color: 'var(--muted)' }}>
                  No prospects yet
                </td>
              </tr>
            ) : (
              prospects.map((p) => (
                <tr key={p.id}>
                  <td style={TABLE_TD}>
                    <a
                      href={`https://${p.domain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#06B6D4', textDecoration: 'none' }}
                    >
                      {p.domain}
                    </a>
                  </td>
                  <td
                    style={{
                      ...TABLE_TD,
                      fontWeight: 700,
                      color: p.authority_score >= 60 ? '#10B981' : p.authority_score >= 35 ? '#F59E0B' : '#dc2626',
                    }}
                  >
                    {p.authority_score}
                  </td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)', fontSize: 12 }}>{p.contact_email || '—'}</td>
                  <td style={TABLE_TD}>
                    <select
                      value={p.status}
                      onChange={(e) => updateStatus(p.id, e.target.value)}
                      style={{ ...INPUT_STYLE, width: 'auto', padding: '4px 8px', color: statusColor[p.status] }}
                    >
                      {statusOptions.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td style={{ ...TABLE_TD, color: p.pitch_sent ? '#10B981' : 'var(--muted)' }}>
                    {p.pitch_sent ? '✓ Yes' : 'No'}
                  </td>
                  <td style={TABLE_TD}>
                    <button onClick={() => updateStatus(p.id, 'contacted')} style={BTN_SM}>
                      Mark Contacted
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
// Tab: Analytics
// ---------------------------------------------------------------------------

function AnalyticsTab() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [days, setDays] = useState(90);

  useEffect(() => {
    apiGet<AnalyticsResponse>(`/backlink-intel/analytics?days=${days}`)
      .then((d) => setAnalytics(d.analytics))
      .catch(() => setAnalytics(null));
  }, [days]);

  if (!analytics) return <div style={{ color: 'var(--muted)', padding: 40, textAlign: 'center' }}>Loading analytics…</div>;

  const maxNew = Math.max(1, ...analytics.timeseries.map((t) => t.new_backlinks));

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Backlink Analytics</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          {[30, 90, 180, 365].map((d) => (
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

      {/* Timeseries */}
      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, marginBottom: 16 }}>
          NEW vs LOST BACKLINKS (WEEKLY)
        </div>
        {analytics.timeseries.length === 0 ? (
          <div style={{ color: '#e7e9ef', textAlign: 'center', padding: 24 }}>No timeseries data for this period.</div>
        ) : (
          <div style={{ display: 'flex', gap: 3, alignItems: 'flex-end', height: 120, overflowX: 'auto' }}>
            {analytics.timeseries.map((t, i) => (
              <div
                key={i}
                style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, minWidth: 32 }}
              >
                <div
                  style={{
                    width: 14,
                    height: Math.max(2, (t.new_backlinks / maxNew) * 90),
                    backgroundColor: '#06B6D4',
                    borderRadius: '2px 2px 0 0',
                  }}
                  title={`+${t.new_backlinks}`}
                />
                <div
                  style={{
                    width: 14,
                    height: Math.max(2, (t.lost_backlinks / maxNew) * 90),
                    backgroundColor: '#dc2626',
                    borderRadius: '0 0 2px 2px',
                  }}
                  title={`-${t.lost_backlinks}`}
                />
                <div
                  style={{
                    fontSize: 9,
                    color: '#e7e9ef',
                    writingMode: 'vertical-rl',
                    transform: 'rotate(180deg)',
                    height: 40,
                  }}
                >
                  {t.week?.slice(5)}
                </div>
              </div>
            ))}
          </div>
        )}
        <div style={{ display: 'flex', gap: 16, marginTop: 12, justifyContent: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--muted)' }}>
            <div style={{ width: 10, height: 10, backgroundColor: '#06B6D4', borderRadius: 2 }} /> New
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--muted)' }}>
            <div style={{ width: 10, height: 10, backgroundColor: '#dc2626', borderRadius: 2 }} /> Lost
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 }}>
        {/* Anchor distribution */}
        <div style={{ ...PANEL, padding: 20 }}>
          <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, marginBottom: 16 }}>TOP ANCHOR TEXTS</div>
          {analytics.anchor_distribution.slice(0, 8).map(({ anchor, count }) => (
            <div key={anchor} style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span
                  style={{
                    fontSize: 12,
                    color: 'var(--muted)',
                    maxWidth: 180,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {anchor}
                </span>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#06B6D4' }}>{count}</span>
              </div>
              <div style={{ background: 'var(--card)', borderRadius: 3, height: 5 }}>
                <div
                  style={{
                    background: '#06B6D4',
                    borderRadius: 3,
                    height: 5,
                    width: `${(count / Math.max(1, analytics.anchor_distribution[0]?.count ?? 1)) * 100}%`,
                  }}
                />
              </div>
            </div>
          ))}
        </div>

        {/* Authority buckets + follow */}
        <div style={{ ...PANEL, padding: 20 }}>
          <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, marginBottom: 16 }}>
            AUTHORITY SCORE DISTRIBUTION
          </div>
          {Object.entries(analytics.authority_buckets).map(([range, count]) => (
            <div
              key={range}
              style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, alignItems: 'center' }}
            >
              <span style={{ fontSize: 12, color: 'var(--muted)', minWidth: 60 }}>{range}</span>
              <div style={{ flex: 1, background: 'var(--card)', borderRadius: 3, height: 8, margin: '0 12px' }}>
                <div
                  style={{
                    background: 'var(--brand)',
                    borderRadius: 3,
                    height: 8,
                    width: `${(count / Math.max(1, analytics.total_analyzed)) * 100}%`,
                  }}
                />
              </div>
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--brand)', minWidth: 24 }}>{count}</span>
            </div>
          ))}
          <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, marginTop: 20, marginBottom: 12 }}>
            FOLLOW TYPE DISTRIBUTION
          </div>
          {Object.entries(analytics.follow_distribution).map(([type, count]) => (
            <div key={type} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
              <span style={{ color: 'var(--muted)' }}>{type}</span>
              <span style={{ fontWeight: 600, color: '#06B6D4' }}>{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Authority Score
// ---------------------------------------------------------------------------

function AuthorityScoreTab() {
  const [domain, setDomain] = useState('');
  const [result, setResult] = useState<{
    domain: string;
    score: number;
    label: string;
    your_score: number;
    delta: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);

  const lookup = async () => {
    if (!domain) return;
    setLoading(true);
    try {
      const d = await apiSend<AuthorityScoreResponse>('/backlink-intel/authority-score', 'POST', { domain });
      setResult(d.authority_score);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const scoreColor = (s: number) => (s >= 60 ? '#10B981' : s >= 35 ? '#F59E0B' : '#dc2626');

  return (
    <div>
      <h2 style={{ margin: '0 0 24px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Authority Score Lookup</h2>
      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <p style={{ margin: '0 0 16px', color: 'var(--muted)', fontSize: 14 }}>
          Check the Authority Score (0–100) for any domain. Compare against your own score to identify stronger/weaker
          competitors.
        </p>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <input
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="Enter any domain, e.g. moz.com"
            style={{ ...INPUT_STYLE, maxWidth: 340 }}
            onKeyDown={(e) => e.key === 'Enter' && lookup()}
          />
          <button onClick={lookup} style={BTN_PRIMARY} disabled={loading}>
            {loading ? 'Checking…' : 'Check Score'}
          </button>
        </div>
      </div>

      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 20 }}>
          <div
            style={{ ...PANEL, padding: 32, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}
          >
            <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600 }}>{result.domain.toUpperCase()}</div>
            <ScoreRing score={result.score} color={scoreColor(result.score)} size={140} />
            <div style={{ color: scoreColor(result.score), fontWeight: 700, fontSize: 18 }}>{result.label}</div>
          </div>
          <div
            style={{ ...PANEL, padding: 32, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}
          >
            <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600 }}>YOUR DOMAIN</div>
            <ScoreRing score={result.your_score} color={scoreColor(result.your_score)} size={140} />
            <div style={{ color: result.delta > 0 ? '#dc2626' : '#10B981', fontWeight: 700, fontSize: 15 }}>
              {result.delta > 0
                ? `↑ ${result.delta} points stronger`
                : result.delta < 0
                  ? `↓ ${Math.abs(result.delta)} points weaker`
                  : 'Equal scores'}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Disavow
// ---------------------------------------------------------------------------

function DisavowTab() {
  const [backlinks, setBacklinks] = useState<Backlink[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [disavowContent, setDisavowContent] = useState('');
  const [generated, setGenerated] = useState(false);

  useEffect(() => {
    apiGet<BacklinksResponse>('/backlink-intel/backlinks?status=toxic&page_size=50')
      .then((d) => setBacklinks(d.backlinks ?? []))
      .catch(() => {});
  }, []);

  const toggle = (id: string) => {
    setSelected((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  };

  const toggleAll = () => {
    if (selected.size === backlinks.length) setSelected(new Set());
    else setSelected(new Set(backlinks.map((b) => b.id)));
  };

  const generate = async () => {
    if (selected.size === 0) return;
    const d = await apiSend<DisavowResponse>('/backlink-intel/disavow', 'POST', { backlink_ids: Array.from(selected) });
    setDisavowContent(d.disavow?.content ?? '');
    setGenerated(true);
  };

  const download = () => {
    const blob = new Blob([disavowContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'disavow.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 8px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Disavow Manager</h2>
      <p style={{ margin: '0 0 24px', color: 'var(--muted)', fontSize: 14 }}>
        Select toxic/suspicious backlinks to include in your Google disavow file. Download and submit via Google Search
        Console.
      </p>

      <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center' }}>
        <button onClick={toggleAll} style={BTN_SM}>
          {selected.size === backlinks.length ? 'Deselect All' : 'Select All Toxic'}
        </button>
        <span style={{ color: 'var(--muted)', fontSize: 13 }}>{selected.size} selected</span>
        <button
          onClick={generate}
          style={{ ...BTN_PRIMARY, opacity: selected.size === 0 ? 0.5 : 1 }}
          disabled={selected.size === 0}
        >
          Generate Disavow File
        </button>
        {generated && (
          <button onClick={download} style={{ ...BTN_SM, color: '#10B981', borderColor: '#10B981' }}>
            ⬇ Download disavow.txt
          </button>
        )}
      </div>

      {backlinks.length === 0 && (
        <div style={{ color: 'var(--muted)', padding: 32, textAlign: 'center' }}>
          No toxic backlinks found. Run a Backlink Audit to identify toxic links.
        </div>
      )}

      {backlinks.length > 0 && (
        <div style={{ ...PANEL, overflowX: 'auto', marginBottom: 20 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['', 'Source Domain', 'Anchor', 'Toxic Score', 'Status'].map((h) => (
                  <th key={h} style={TABLE_TH}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {backlinks.map((bl) => (
                <tr key={bl.id} style={{ backgroundColor: selected.has(bl.id) ? '#1E0A0A22' : 'transparent' }}>
                  <td style={{ ...TABLE_TD, width: 40 }}>
                    <input
                      type="checkbox"
                      checked={selected.has(bl.id)}
                      onChange={() => toggle(bl.id)}
                      style={{ cursor: 'pointer' }}
                    />
                  </td>
                  <td style={TABLE_TD}>{bl.source_domain}</td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{bl.anchor_text || '—'}</td>
                  <td style={{ ...TABLE_TD, fontWeight: 700, color: '#dc2626' }}>{bl.toxic_score}</td>
                  <td style={TABLE_TD}>
                    <StatusBadge status={bl.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {generated && disavowContent && (
        <div style={{ ...PANEL, padding: 20 }}>
          <div style={{ color: 'var(--muted)', fontSize: 12, fontWeight: 600, marginBottom: 10 }}>
            GENERATED DISAVOW FILE PREVIEW
          </div>
          <pre
            style={{ color: '#10B981', fontSize: 12, overflowX: 'auto', margin: 0, maxHeight: 300, overflowY: 'auto' }}
          >
            {disavowContent}
          </pre>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Domains
// ---------------------------------------------------------------------------

function DomainsTab({ onDomainChange }: { onDomainChange: () => void }) {
  const [domains, setDomains] = useState<
    { id: string; domain: string; label: string; authority_score: number; created_at: string }[]
  >([]);
  const [newDomain, setNewDomain] = useState('');
  const [newLabel, setNewLabel] = useState('');
  const [loading, setLoading] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try {
      const d = await apiGet<DomainsResponse>('/backlink-intel/domains');
      setDomains(d.domains ?? []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch();
  }, []);

  const addDomain = async () => {
    if (!newDomain) return;
    await apiSend('/backlink-intel/domains', 'POST', { domain: newDomain, label: newLabel });
    setNewDomain('');
    setNewLabel('');
    fetch();
    onDomainChange();
  };

  const removeDomain = async (id: string) => {
    await apiSend(`/backlink-intel/domains/${id}`, 'DELETE');
    fetch();
    onDomainChange();
  };

  return (
    <div>
      <h2 style={{ margin: '0 0 24px', fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>Tracked Domains</h2>

      <div style={{ ...PANEL, padding: 24, marginBottom: 24 }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: 'var(--text)' }}>Add Domain to Track</h3>
        <div style={{ display: 'flex', gap: 12 }}>
          <input
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            placeholder="example.com"
            style={{ ...INPUT_STYLE, maxWidth: 260 }}
          />
          <input
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            placeholder="Label (optional)"
            style={{ ...INPUT_STYLE, maxWidth: 200 }}
          />
          <button onClick={addDomain} style={BTN_PRIMARY}>
            + Track Domain
          </button>
        </div>
      </div>

      <div style={{ ...PANEL, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Domain', 'Label', 'Authority Score', 'Added', 'Action'].map((h) => (
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
            ) : domains.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ ...TABLE_TD, textAlign: 'center', color: 'var(--muted)' }}>
                  No domains tracked yet.
                </td>
              </tr>
            ) : (
              domains.map((d) => (
                <tr key={d.id}>
                  <td style={TABLE_TD}>
                    <a
                      href={`https://${d.domain}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: '#06B6D4', textDecoration: 'none' }}
                    >
                      {d.domain}
                    </a>
                  </td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)' }}>{d.label || '—'}</td>
                  <td
                    style={{
                      ...TABLE_TD,
                      fontWeight: 700,
                      color: d.authority_score >= 60 ? '#10B981' : d.authority_score >= 35 ? '#F59E0B' : '#dc2626',
                    }}
                  >
                    {d.authority_score}
                  </td>
                  <td style={{ ...TABLE_TD, color: 'var(--muted)', fontSize: 12 }}>{d.created_at?.slice(0, 10)}</td>
                  <td style={TABLE_TD}>
                    <button onClick={() => removeDomain(d.id)} style={{ ...BTN_SM, color: '#dc2626' }}>
                      Remove
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
