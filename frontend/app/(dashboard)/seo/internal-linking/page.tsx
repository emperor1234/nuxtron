'use client';

import { useState, useMemo } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { Link2, RefreshCw, Download, ArrowRight, AlertCircle } from 'lucide-react';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type Opportunity = {
  from_url: string;
  anchor_text: string;
  to_url: string;
  relevance_score: number;
  link_type: 'hub' | 'spoke' | 'bridge' | 'support';
};
type OrphanPage = { url: string; title: string; traffic_potential: 'high' | 'medium' | 'low' };
type HubSpoke = { hub_url: string; hub_title: string; spoke_urls: string[]; coverage_pct: number };
type InternalLinkResult = {
  analysis_id: string;
  linking_score: number;
  opportunities: Opportunity[];
  orphan_pages: OrphanPage[];
  hub_spoke_clusters: HubSpoke[];
  total_opportunities: number;
  crawl_depth_issues: string[];
  recommendations: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

function ScoreGauge({ score }: { score: number }) {
  const r = 38,
    s = 7,
    c = Math.PI * r;
  const color = score >= 75 ? '#26d78e' : score >= 50 ? '#ffb867' : '#f87171';
  return (
    <svg width={100} height={60} viewBox="0 0 100 60">
      <path
        d={`M 11,55 A ${r},${r} 0 0,1 89,55`}
        fill="none"
        stroke="rgba(255,255,255,0.08)"
        strokeWidth={s}
        strokeLinecap="round"
      />
      <path
        d={`M 11,55 A ${r},${r} 0 0,1 89,55`}
        fill="none"
        stroke={color}
        strokeWidth={s}
        strokeLinecap="round"
        strokeDasharray={c}
        strokeDashoffset={c * (1 - score / 100)}
        style={{ transition: 'stroke-dashoffset 0.8s ease' }}
      />
      <text x={50} y={50} textAnchor="middle" fill={color} style={{ fontSize: 18, fontWeight: 800 }}>
        {score}
      </text>
    </svg>
  );
}

export default function InternalLinkingPage() {
  const [siteUrl, setSiteUrl] = useState('');
  const [urls, setUrls] = useState('');
  const [result, setResult] = useState<InternalLinkResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'opportunities' | 'orphans' | 'hubs' | 'recommendations'>('opportunities');
  const [sortBy, setSortBy] = useState<'relevance_score' | 'from_url'>('relevance_score');
  const [typeFilter, setTypeFilter] = useState('all');

  async function run() {
    if (!siteUrl) {
      setError('Site URL is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const payload = {
        site_url: siteUrl,
        url_list: urls
          ? urls
              .split('\n')
              .map((s) => s.trim())
              .filter(Boolean)
          : undefined,
      };
      const data = await apiSend<InternalLinkResult>(
        '/seo-platform/internal-linking/suggest',
        'POST',
        payload,
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
      setActiveTab('opportunities');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }

  const filtered = useMemo(() => {
    if (!result?.opportunities) return [];
    let opps = [...result.opportunities];
    if (typeFilter !== 'all') opps = opps.filter((o) => o.link_type === typeFilter);
    opps.sort((a, b) =>
      sortBy === 'relevance_score' ? b.relevance_score - a.relevance_score : a.from_url.localeCompare(b.from_url)
    );
    return opps;
  }, [result, typeFilter, sortBy]);

  function csvExport() {
    if (!result?.opportunities) return;
    const rows = [
      'from_url,anchor_text,to_url,relevance_score,link_type',
      ...result.opportunities.map(
        (o) => `"${o.from_url}","${o.anchor_text}","${o.to_url}",${o.relevance_score},${o.link_type}`
      ),
    ];
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([rows.join('\n')], { type: 'text/csv' }));
    a.download = 'internal-link-opportunities.csv';
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
    width: '100%',
    padding: '9px 12px',
    borderRadius: 8,
    border: '1px solid var(--line)',
    background: 'var(--bg)',
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
  };
  const td: React.CSSProperties = { padding: '9px 12px', fontSize: 12, borderBottom: '1px solid var(--line)' };
  const LINK_COLORS = { hub: '#1bc7ff', spoke: '#26d78e', bridge: '#ffb867', support: '#ec4899' };
  const TRAFFIC_COLORS = { high: '#f87171', medium: '#ffb867', low: 'var(--muted)' };

  const tabs = [
    { key: 'opportunities' as const, label: `Opportunities (${result?.total_opportunities ?? 0})` },
    { key: 'orphans' as const, label: `Orphan Pages (${result?.orphan_pages?.length ?? 0})` },
    { key: 'hubs' as const, label: 'Hub-Spoke' },
    { key: 'recommendations' as const, label: 'Recommendations' },
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
          <Link2 size={24} color="var(--brand)" />
          Internal Linking
        </h1>
        <p style={{ margin: '0 0 24px', color: 'var(--muted)', fontSize: 14 }}>
          Link opportunity analysis, orphan page detection, hub-spoke structure, and crawl depth optimization
        </p>

        {error && (
          <div style={{ ...card, color: '#f87171', borderColor: '#f8717144', background: '#f8717111' }}>{error}</div>
        )}

        <section style={card}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
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
                Site URL
              </label>
              <input
                style={input}
                value={siteUrl}
                onChange={(e) => setSiteUrl(e.target.value)}
                placeholder="https://example.com"
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
                Specific URLs to Analyze (one per line, optional)
              </label>
              <textarea
                style={{ ...input, minHeight: 90, resize: 'vertical' }}
                value={urls}
                onChange={(e) => setUrls(e.target.value)}
                placeholder="/blog/post-1&#10;/products/widget"
              />
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
                Analyzing...
              </>
            ) : (
              <>
                <Link2 size={15} />
                Find Link Opportunities
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
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))',
                gap: 12,
                marginBottom: 20,
              }}
            >
              <div
                style={{
                  ...card,
                  marginBottom: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <span style={{ fontSize: 10, color: 'var(--muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  Linking Score
                </span>
                <ScoreGauge score={result.linking_score} />
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
                  Opportunities
                </div>
                <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--brand)' }}>{result.total_opportunities}</div>
              </div>
              <div style={{ ...card, marginBottom: 0 }}>
                <div
                  style={{
                    fontSize: 10,
                    color: '#f87171',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    marginBottom: 6,
                  }}
                >
                  Orphan Pages
                </div>
                <div style={{ fontSize: 32, fontWeight: 800, color: '#f87171' }}>
                  {result.orphan_pages?.length ?? 0}
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
                  Hub Clusters
                </div>
                <div style={{ fontSize: 32, fontWeight: 800 }}>{result.hub_spoke_clusters?.length ?? 0}</div>
              </div>
            </div>

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

            {activeTab === 'opportunities' && (
              <div style={card}>
                <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
                  <select
                    value={typeFilter}
                    onChange={(e) => setTypeFilter(e.target.value)}
                    style={{ ...input, width: 140, marginBottom: 0 }}
                  >
                    <option value="all">All Types</option>
                    {['hub', 'spoke', 'bridge', 'support'].map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                    style={{ ...input, width: 160, marginBottom: 0 }}
                  >
                    <option value="relevance_score">Sort: Relevance</option>
                    <option value="from_url">Sort: From URL</option>
                  </select>
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
                    }}
                  >
                    <Download size={12} />
                    Export CSV
                  </button>
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={th}>From URL</th>
                        <th style={th}>Anchor Text</th>
                        <th style={th}></th>
                        <th style={th}>To URL</th>
                        <th style={th}>Type</th>
                        <th style={th}>Relevance</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtered.map((o, i) => (
                        <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                          <td
                            style={{
                              ...td,
                              maxWidth: 200,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {o.from_url}
                          </td>
                          <td style={{ ...td, color: 'var(--brand)', fontStyle: 'italic' }}>{o.anchor_text}</td>
                          <td style={td}>
                            <ArrowRight size={12} color="var(--muted)" />
                          </td>
                          <td
                            style={{
                              ...td,
                              maxWidth: 200,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {o.to_url}
                          </td>
                          <td style={td}>
                            <span
                              style={{
                                padding: '2px 8px',
                                borderRadius: 4,
                                fontSize: 10,
                                fontWeight: 700,
                                background: (LINK_COLORS[o.link_type] ?? 'var(--muted)') + '22',
                                color: LINK_COLORS[o.link_type] ?? 'var(--muted)',
                              }}
                            >
                              {o.link_type}
                            </span>
                          </td>
                          <td
                            style={{
                              ...td,
                              fontWeight: 700,
                              color:
                                o.relevance_score >= 0.7
                                  ? '#26d78e'
                                  : o.relevance_score >= 0.4
                                    ? '#ffb867'
                                    : 'var(--muted)',
                            }}
                          >
                            {Math.round(o.relevance_score * 100)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'orphans' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700, color: '#f87171' }}>
                  Orphan Pages — No Inbound Internal Links
                </h3>
                {result.orphan_pages?.length === 0 ? (
                  <div style={{ color: '#26d78e', fontSize: 13 }}>No orphan pages found!</div>
                ) : (
                  <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={th}>URL</th>
                        <th style={th}>Page Title</th>
                        <th style={th}>Traffic Potential</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.orphan_pages?.map((p, i) => (
                        <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                          <td style={{ ...td, color: '#f87171' }}>{p.url}</td>
                          <td style={td}>{p.title}</td>
                          <td style={td}>
                            <span
                              style={{
                                padding: '2px 8px',
                                borderRadius: 4,
                                fontSize: 10,
                                fontWeight: 700,
                                background: TRAFFIC_COLORS[p.traffic_potential] + '22',
                                color: TRAFFIC_COLORS[p.traffic_potential],
                              }}
                            >
                              {p.traffic_potential}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}

            {activeTab === 'hubs' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Hub-Spoke Clusters</h3>
                <div style={{ display: 'grid', gap: 12 }}>
                  {result.hub_spoke_clusters?.map((cl, i) => (
                    <div
                      key={i}
                      style={{
                        background: 'var(--bg)',
                        borderRadius: 10,
                        padding: '14px 16px',
                        border: '1px solid var(--line)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                        <div>
                          <span
                            style={{ fontSize: 11, color: 'var(--brand)', fontWeight: 700, textTransform: 'uppercase' }}
                          >
                            HUB
                          </span>
                          <div style={{ fontWeight: 700, fontSize: 13, marginTop: 2 }}>{cl.hub_title}</div>
                          <div style={{ fontSize: 11, color: 'var(--muted)' }}>{cl.hub_url}</div>
                        </div>
                        <div style={{ textAlign: 'right' }}>
                          <span style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase' }}>
                            Coverage
                          </span>
                          <div
                            style={{
                              fontSize: 18,
                              fontWeight: 800,
                              color: cl.coverage_pct >= 70 ? '#26d78e' : '#ffb867',
                            }}
                          >
                            {cl.coverage_pct}%
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
                        {cl.spoke_urls.map((s) => (
                          <span
                            key={s}
                            style={{
                              padding: '3px 8px',
                              borderRadius: 4,
                              fontSize: 10,
                              background: 'rgba(38,215,142,0.08)',
                              color: '#26d78e',
                              border: '1px solid rgba(38,215,142,0.2)',
                            }}
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'recommendations' && (
              <div style={card}>
                {result.crawl_depth_issues?.length > 0 && (
                  <div style={{ marginBottom: 20 }}>
                    <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700, color: '#f87171' }}>
                      Crawl Depth Issues
                    </h3>
                    {result.crawl_depth_issues.map((issue, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
                        <AlertCircle size={13} color="#f87171" style={{ flexShrink: 0, marginTop: 1 }} />
                        <span style={{ fontSize: 13 }}>{issue}</span>
                      </div>
                    ))}
                  </div>
                )}
                <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700 }}>Recommendations</h3>
                {result.recommendations?.map((rec, i) => (
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
                    <span style={{ fontSize: 13, lineHeight: 1.5 }}>{rec}</span>
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
