'use client';

import { useState, useMemo } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { ExternalLink, RefreshCw, Download, Star, Filter } from 'lucide-react';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type Prospect = {
  domain: string;
  url: string;
  opportunity_type: string;
  domain_rating: number;
  monthly_traffic: number;
  relevance_score: number;
  contact_hint: string;
  status: 'new' | 'contacted' | 'in_progress' | 'won' | 'lost';
};
type LinkBuildingResult = {
  analysis_id: string;
  total_prospects: number;
  prospects: Prospect[];
  top_opportunity_types: { type: string; count: number }[];
  average_domain_rating: number;
  estimated_link_velocity: number;
  strategy_notes: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function LinkbuildingPage() {
  const [domain, setDomain] = useState('');
  const [keywords, setKeywords] = useState('');
  const [oppTypes, setOppTypes] = useState<string[]>(['guest_post', 'resource_page', 'broken_link']);
  const [result, setResult] = useState<LinkBuildingResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'prospects' | 'strategy'>('prospects');
  const [sortBy, setSortBy] = useState<'domain_rating' | 'relevance_score' | 'monthly_traffic'>('domain_rating');
  const [typeFilter, setTypeFilter] = useState('all');
  const [drMin, setDrMin] = useState(0);

  const ALL_OPP_TYPES = [
    'guest_post',
    'resource_page',
    'broken_link',
    'skyscraper',
    'unlinked_mention',
    'podcast',
    'interview',
  ];

  async function run() {
    if (!domain) {
      setError('Domain is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<LinkBuildingResult>(
        '/seo-platform/linkbuilding/analyze',
        'POST',
        {
          domain,
          target_keywords: keywords
            .split(',')
            .map((s) => s.trim())
            .filter(Boolean),
          opportunity_types: oppTypes,
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
      setActiveTab('prospects');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }

  const filtered = useMemo(() => {
    if (!result?.prospects) return [];
    let p = [...result.prospects];
    if (typeFilter !== 'all') p = p.filter((x) => x.opportunity_type === typeFilter);
    if (drMin > 0) p = p.filter((x) => x.domain_rating >= drMin);
    p.sort((a, b) => b[sortBy] - a[sortBy]);
    return p;
  }, [result, typeFilter, sortBy, drMin]);

  function csvExport() {
    if (!result?.prospects) return;
    const rows = [
      'domain,url,opportunity_type,domain_rating,monthly_traffic,relevance_score,contact_hint,status',
      ...result.prospects.map(
        (p) =>
          `"${p.domain}","${p.url}","${p.opportunity_type}",${p.domain_rating},${p.monthly_traffic},${p.relevance_score},"${p.contact_hint}",${p.status}`
      ),
    ];
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([rows.join('\n')], { type: 'text/csv' }));
    a.download = 'link-prospects.csv';
    a.click();
  }

  const card: React.CSSProperties = {
    background: 'var(--bg-soft)',
    border: '1px solid var(--line)',
    borderRadius: 16,
    padding: '20px 24px',
    marginBottom: 20,
  };
  const input: React.CSSProperties = {
    padding: '9px 12px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
    color: 'var(--text)',
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
  };
  const td: React.CSSProperties = { padding: '10px 12px', fontSize: 12, borderBottom: '1px solid var(--line)' };
  const STATUS_COLORS: Record<string, string> = {
    new: '#1bc7ff',
    contacted: '#ffb867',
    in_progress: '#a78bfa',
    won: '#26d78e',
    lost: '#f87171',
  };
  const OPP_COLORS: Record<string, string> = {
    guest_post: '#1bc7ff',
    resource_page: '#26d78e',
    broken_link: '#ffb867',
    skyscraper: '#a78bfa',
    unlinked_mention: '#60a5fa',
    podcast: '#f97316',
    interview: '#ec4899',
  };
  const tabs = [
    { key: 'prospects' as const, label: `Prospects (${result?.total_prospects ?? 0})` },
    { key: 'strategy' as const, label: 'Strategy' },
  ];

  return (
    <main
      className="seo-advanced-page"
      style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}
    >
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <h1
          style={{ margin: '0 0 4px', fontSize: 24, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 10 }}
        >
          <ExternalLink size={24} color="var(--brand)" />
          Link Building
        </h1>
        <p style={{ margin: '0 0 24px', color: 'var(--muted)', fontSize: 14 }}>
          AI-powered link prospects with DR/traffic scoring, opportunity classification, and outreach pipeline
        </p>

        {error && (
          <div style={{ ...card, color: '#f87171', borderColor: '#f8717144', background: '#f8717111' }}>{error}</div>
        )}

        <section style={card}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16, marginBottom: 16 }}>
            <div>
              <label
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
                Your Domain
              </label>
              <input
                style={{ ...input, width: '100%', boxSizing: 'border-box' }}
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="example.com"
              />
            </div>
            <div>
              <label
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
                Target Keywords (comma-separated)
              </label>
              <input
                style={{ ...input, width: '100%', boxSizing: 'border-box' }}
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="SEO tools, keyword research, backlink checker"
              />
            </div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label
              style={{
                display: 'block',
                fontSize: 12,
                fontWeight: 600,
                marginBottom: 8,
                color: 'var(--muted)',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Opportunity Types
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {ALL_OPP_TYPES.map((t) => {
                const active = oppTypes.includes(t);
                const color = OPP_COLORS[t] ?? 'var(--brand)';
                return (
                  <button
                    key={t}
                    onClick={() => setOppTypes(active ? oppTypes.filter((x) => x !== t) : [...oppTypes, t])}
                    style={{
                      padding: '5px 12px',
                      borderRadius: 999,
                      border: `1px solid ${active ? color : 'var(--line)'}`,
                      background: active ? color + '22' : 'transparent',
                      color: active ? color : 'var(--muted)',
                      fontSize: 12,
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    {t.replace(/_/g, ' ')}
                  </button>
                );
              })}
            </div>
          </div>
          <button
            onClick={() => void run()}
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
            }}
          >
            {loading ? (
              <>
                <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} />
                Finding Prospects...
              </>
            ) : (
              <>
                <ExternalLink size={15} />
                Find Prospects
              </>
            )}
          </button>
        </section>

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
              <div style={{ ...card, marginBottom: 0 }}>
                <div
                  style={{
                    fontSize: 10,
                    color: 'var(--muted)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    marginBottom: 6,
                  }}
                >
                  Total Prospects
                </div>
                <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--brand)' }}>{result.total_prospects}</div>
              </div>
              <div style={{ ...card, marginBottom: 0 }}>
                <div
                  style={{
                    fontSize: 10,
                    color: 'var(--muted)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    marginBottom: 6,
                  }}
                >
                  Avg Domain Rating
                </div>
                <div style={{ fontSize: 32, fontWeight: 800, color: '#26d78e' }}>
                  {Math.round(result.average_domain_rating ?? 0)}
                </div>
              </div>
              <div style={{ ...card, marginBottom: 0 }}>
                <div
                  style={{
                    fontSize: 10,
                    color: 'var(--muted)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    marginBottom: 6,
                  }}
                >
                  Est. Link Velocity
                </div>
                <div style={{ fontSize: 32, fontWeight: 800, color: '#ffb867' }}>
                  {result.estimated_link_velocity}/mo
                </div>
              </div>
            </div>

            {result.top_opportunity_types?.length > 0 && (
              <div style={{ ...card, marginBottom: 20 }}>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 12,
                    color: 'var(--muted)',
                  }}
                >
                  Opportunity Breakdown
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {result.top_opportunity_types.map((t) => {
                    const c = OPP_COLORS[t.type] ?? 'var(--brand)';
                    return (
                      <div
                        key={t.type}
                        style={{
                          padding: '6px 14px',
                          borderRadius: 999,
                          background: c + '22',
                          color: c,
                          fontSize: 12,
                          fontWeight: 700,
                          border: `1px solid ${c}44`,
                        }}
                      >
                        {t.type.replace(/_/g, ' ')}: <strong>{t.count}</strong>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid var(--line)' }}>
              {tabs.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setActiveTab(t.key)}
                  style={{
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
                  {t.label}
                </button>
              ))}
            </div>

            {activeTab === 'prospects' && (
              <div style={card}>
                <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap', alignItems: 'center' }}>
                  <select
                    value={typeFilter}
                    onChange={(e) => setTypeFilter(e.target.value)}
                    style={{ ...input, width: 160 }}
                  >
                    <option value="all">All Types</option>
                    {ALL_OPP_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                    style={{ ...input, width: 180 }}
                  >
                    <option value="domain_rating">Sort: Domain Rating</option>
                    <option value="relevance_score">Sort: Relevance</option>
                    <option value="monthly_traffic">Sort: Traffic</option>
                  </select>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Filter size={12} color="var(--muted)" />
                    <span style={{ fontSize: 12, color: 'var(--muted)' }}>Min DR:</span>
                    <input
                      type="number"
                      value={drMin}
                      onChange={(e) => setDrMin(Number(e.target.value))}
                      style={{ ...input, width: 60 }}
                      min={0}
                      max={100}
                    />
                  </div>
                  <button
                    onClick={csvExport}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      padding: '8px 14px',
                      border: '1px solid var(--line)',
                      borderRadius: 8,
                      background: 'transparent',
                      color: 'var(--muted)',
                      cursor: 'pointer',
                      fontSize: 12,
                      marginLeft: 'auto',
                    }}
                  >
                    <Download size={12} />
                    Export CSV
                  </button>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse', minWidth: 800 }}>
                    <thead>
                      <tr>
                        <th style={th}>Domain</th>
                        <th style={th}>Type</th>
                        <th style={{ ...th, textAlign: 'right' }}>DR</th>
                        <th style={{ ...th, textAlign: 'right' }}>Traffic</th>
                        <th style={{ ...th, textAlign: 'right' }}>Relevance</th>
                        <th style={th}>Contact Hint</th>
                        <th style={th}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((p, i) => (
                        <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                          <td style={td}>
                            <div style={{ fontWeight: 600 }}>{p.domain}</div>
                            <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 2 }}>{p.url}</div>
                          </td>
                          <td style={td}>
                            <span
                              style={{
                                padding: '2px 8px',
                                borderRadius: 4,
                                fontSize: 10,
                                fontWeight: 700,
                                background: (OPP_COLORS[p.opportunity_type] ?? 'var(--brand)') + '22',
                                color: OPP_COLORS[p.opportunity_type] ?? 'var(--brand)',
                              }}
                            >
                              {p.opportunity_type.replace(/_/g, ' ')}
                            </span>
                          </td>
                          <td
                            style={{
                              ...td,
                              textAlign: 'right',
                              fontWeight: 800,
                              color:
                                p.domain_rating >= 70 ? '#26d78e' : p.domain_rating >= 40 ? '#ffb867' : 'var(--muted)',
                            }}
                          >
                            {p.domain_rating}
                          </td>
                          <td style={{ ...td, textAlign: 'right', color: 'var(--muted)' }}>
                            {p.monthly_traffic >= 1000
                              ? `${(p.monthly_traffic / 1000).toFixed(1)}K`
                              : p.monthly_traffic}
                          </td>
                          <td
                            style={{
                              ...td,
                              textAlign: 'right',
                              fontWeight: 700,
                              color: p.relevance_score >= 0.7 ? '#26d78e' : '#ffb867',
                            }}
                          >
                            {Math.round(p.relevance_score * 100)}%
                          </td>
                          <td style={{ ...td, fontSize: 11, color: 'var(--muted)', maxWidth: 180 }}>
                            {p.contact_hint}
                          </td>
                          <td style={td}>
                            <span
                              style={{
                                padding: '2px 8px',
                                borderRadius: 4,
                                fontSize: 10,
                                fontWeight: 700,
                                background: (STATUS_COLORS[p.status] ?? 'var(--muted)') + '22',
                                color: STATUS_COLORS[p.status] ?? 'var(--muted)',
                              }}
                            >
                              {p.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'strategy' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Link Building Strategy</h3>
                {result.strategy_notes?.map((note, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 12,
                      background: 'var(--bg)',
                      borderRadius: 10,
                      padding: '12px 16px',
                      border: '1px solid var(--line)',
                      marginBottom: 8,
                    }}
                  >
                    <div
                      style={{
                        width: 22,
                        height: 22,
                        borderRadius: 6,
                        background: 'rgba(27,199,255,0.15)',
                        color: 'var(--brand)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        fontSize: 11,
                        fontWeight: 800,
                      }}
                    >
                      {i + 1}
                    </div>
                    <span style={{ fontSize: 13, lineHeight: 1.5 }}>{note}</span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </main>
  );
}
