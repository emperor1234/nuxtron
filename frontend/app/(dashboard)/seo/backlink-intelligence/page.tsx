'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

interface TopicalCluster {
  topic: string;
  link_count: number;
  anchor_diversity: number;
}

interface CompetitorEntry {
  competitor: string;
  backlinks: number;
  gap_opportunity: string;
  acquisition_tactics: string[];
}

interface AcquisitionOpportunity {
  type: string;
  difficulty: string;
  potential_links: number;
}

interface AuthorityDistribution {
  tier_1_domains_pct: number;
  tier_2_domains_pct: number;
  long_tail_pct: number;
}

interface LinkGraph {
  total_estimated_backlinks: number;
  referring_domains: number;
  authority_distribution: string;
  topical_clusters: TopicalCluster[];
}

interface BacklinkResult {
  analysis_id: string;
  backlink_intelligence_score: number;
  domain_authority_estimate: number;
  link_graph: LinkGraph;
  competitor_analysis: CompetitorEntry[];
  authority_distribution: AuthorityDistribution;
  acquisition_opportunities: AcquisitionOpportunity[];
  next_actions: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
}

const DIFFICULTY_COLOR: Record<string, string> = {
  low: '#22c55e',
  medium: '#f59e0b',
  high: '#ef4444',
};

function ScoreRing({ score, label, color }: { score: number; label: string; color: string }) {
  const r = 38;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg width={96} height={96} viewBox="0 0 96 96">
        <circle cx={48} cy={48} r={r} fill="none" stroke="var(--line)" strokeWidth={8} />
        <circle
          cx={48}
          cy={48}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={8}
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 48 48)"
        />
        <text x={48} y={53} textAnchor="middle" fill="var(--text)" fontSize={18} fontWeight={700}>
          {score}
        </text>
      </svg>
      <span style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'center' }}>{label}</span>
    </div>
  );
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div style={{ background: 'var(--line)', borderRadius: 6, height: 8, width: '100%', overflow: 'hidden' }}>
      <div
        style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: 6, transition: 'width 0.6s ease' }}
      />
    </div>
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      style={{
        background: color + '22',
        color,
        border: `1px solid ${color}55`,
        borderRadius: 99,
        padding: '2px 10px',
        fontSize: 11,
        fontWeight: 700,
        textTransform: 'capitalize' as const,
      }}
    >
      {label}
    </span>
  );
}

export default function BacklinkIntelligencePage() {
  const [domain, setDomain] = useState('');
  const [competitorDomains, setCompetitorDomains] = useState('');
  const [analysisDepth, setAnalysisDepth] = useState('standard');
  const [includeTopical, setIncludeTopical] = useState(true);
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<BacklinkResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function runAnalysis() {
    if (!domain) {
      setError('Domain is required');
      return;
    }
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const competitors = competitorDomains
        .split('\n')
        .map((d) => d.trim())
        .filter(Boolean);
      const data = await apiSend<BacklinkResult>(
        '/seo-platform/backlink-intelligence/analyze',
        'POST',
        {
          domain: domain.trim(),
          competitor_domains: competitors,
          link_analysis_depth: analysisDepth,
          include_topical_clusters: includeTopical,
          notes: notes.trim(),
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
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }

  const s = {
    card: {
      background: 'var(--bg-soft)',
      border: '1px solid var(--line)',
      borderRadius: 16,
      padding: '20px 24px',
      marginBottom: 20,
    } as React.CSSProperties,
    input: {
      width: '100%',
      padding: '9px 12px',
      borderRadius: 8,
      border: '1px solid var(--line)',
      background: 'var(--bg)',
      color: 'var(--text)',
      marginBottom: 10,
      boxSizing: 'border-box' as const,
      fontSize: 14,
    } as React.CSSProperties,
    label: { display: 'block', marginBottom: 5, fontWeight: 600, fontSize: 13 } as React.CSSProperties,
    th: {
      textAlign: 'left' as const,
      padding: '8px 12px',
      fontSize: 11,
      fontWeight: 700,
      textTransform: 'uppercase' as const,
      color: 'var(--muted)',
      borderBottom: '1px solid var(--line)',
    },
    td: { padding: '10px 12px', fontSize: 13, borderBottom: '1px solid var(--line)', verticalAlign: 'top' as const },
    sectionTitle: {
      fontSize: 14,
      fontWeight: 700,
      marginBottom: 14,
      marginTop: 0,
      display: 'flex',
      alignItems: 'center',
      gap: 8,
    } as React.CSSProperties,
  };

  const lk = result?.link_graph;
  const ad = result?.authority_distribution;

  return (
    <main style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ margin: 0, fontSize: 24, fontWeight: 800 }}>🔗 Backlink Intelligence</h1>
          <p style={{ margin: '4px 0 0', color: 'var(--muted)', fontSize: 14 }}>
            Deep link profile analysis — authority tiers, competitor gaps, and link acquisition pipeline
          </p>
        </div>

        {error && (
          <div style={{ ...s.card, color: '#dc2626', borderColor: '#dc262644', background: '#dc262611' }}>{error}</div>
        )}

        {/* Input Form */}
        <section style={s.card}>
          <p style={s.sectionTitle}>⚙️ Analysis Configuration</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 16 }}>
            <div>
              <label style={s.label}>Target Domain</label>
              <input
                style={s.input}
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="yourdomain.com"
              />
              <label style={s.label}>Analysis Depth</label>
              <select style={s.input} value={analysisDepth} onChange={(e) => setAnalysisDepth(e.target.value)}>
                <option value="standard">Standard</option>
                <option value="deep">Deep</option>
                <option value="comprehensive">Comprehensive</option>
              </select>
              <label style={{ ...s.label, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input type="checkbox" checked={includeTopical} onChange={(e) => setIncludeTopical(e.target.checked)} />
                Include Topical Cluster Mapping
              </label>
            </div>
            <div>
              <label style={s.label}>Competitor Domains (one per line)</label>
              <textarea
                style={{ ...s.input, minHeight: 96, resize: 'vertical' }}
                value={competitorDomains}
                onChange={(e) => setCompetitorDomains(e.target.value)}
                placeholder={'competitor1.com\ncompetitor2.com\ncompetitor3.com'}
              />
              <label style={s.label}>Notes</label>
              <textarea
                style={{ ...s.input, minHeight: 48, resize: 'vertical' }}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Focus areas, context..."
              />
            </div>
          </div>
          <button
            onClick={() => void runAnalysis()}
            disabled={loading}
            style={{
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
            {loading ? '⏳ Analyzing...' : '🔍 Analyze Backlink Profile'}
          </button>
        </section>

        {loading && (
          <div style={{ ...s.card, textAlign: 'center', padding: 40, color: 'var(--muted)' }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>🔗</div>
            <p style={{ margin: 0, fontWeight: 600 }}>Running link graph analysis…</p>
            <p style={{ margin: '4px 0 0', fontSize: 13 }}>
              Mapping authority tiers, topical clusters, and competitor gaps
            </p>
          </div>
        )}

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
            {/* Score Row */}
            <section style={s.card}>
              <p style={s.sectionTitle}>
                📊 Profile Overview — <span style={{ color: 'var(--muted)', fontWeight: 400 }}>{domain}</span>
              </p>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 140px), 1fr))',
                  gap: 24,
                  alignItems: 'center',
                }}
              >
                <ScoreRing score={result.backlink_intelligence_score} label="Intelligence Score" color="#22d3ee" />
                <ScoreRing score={result.domain_authority_estimate} label="Domain Authority Est." color="#2563eb" />
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 28, fontWeight: 800, color: 'var(--brand)' }}>
                    {lk?.total_estimated_backlinks?.toLocaleString() ?? '—'}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>Total Backlinks (est.)</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 28, fontWeight: 800, color: '#22c55e' }}>
                    {lk?.referring_domains?.toLocaleString() ?? '—'}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>Referring Domains</div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 28, fontWeight: 800, color: '#f59e0b' }}>
                    {result.acquisition_opportunities?.length ?? 0}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--muted)' }}>Opportunities Found</div>
                </div>
              </div>
            </section>

            {/* Authority Distribution */}
            {ad && (
              <section style={s.card}>
                <p style={s.sectionTitle}>🏛️ Authority Tier Distribution</p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 300px), 1fr))', gap: 20 }}>
                  {[
                    { label: 'Tier 1 — High Authority', value: ad.tier_1_domains_pct, color: '#22c55e' },
                    { label: 'Tier 2 — Mid Authority', value: ad.tier_2_domains_pct, color: '#f59e0b' },
                    { label: 'Long Tail', value: ad.long_tail_pct, color: '#94a3b8' },
                  ].map(({ label, value, color }) => (
                    <div key={label}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
                        <span style={{ color: 'var(--muted)' }}>{label}</span>
                        <span style={{ fontWeight: 700, color }}>{value}%</span>
                      </div>
                      <ProgressBar value={value} max={100} color={color} />
                    </div>
                  ))}
                </div>
                {lk?.authority_distribution && (
                  <p style={{ margin: '16px 0 0', fontSize: 13, color: 'var(--muted)', fontStyle: 'italic' }}>
                    💡 {lk.authority_distribution}
                  </p>
                )}
              </section>
            )}

            {/* Topical Clusters */}
            {lk?.topical_clusters && lk.topical_clusters.length > 0 && (
              <section style={s.card}>
                <p style={s.sectionTitle}>🗺️ Topical Cluster Mapping</p>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      {['Topic', 'Link Count', 'Anchor Diversity', 'Strength'].map((h) => (
                        <th key={h} style={s.th}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {lk.topical_clusters.map((c, i) => (
                      <tr key={`item-${i}`} style={{ background: i % 2 === 0 ? 'transparent' : 'var(--bg)' }}>
                        <td style={s.td}>
                          <strong>{c.topic}</strong>
                        </td>
                        <td style={s.td}>{c.link_count.toLocaleString()}</td>
                        <td style={s.td}>{(c.anchor_diversity * 100).toFixed(0)}%</td>
                        <td style={{ ...s.td, width: 180 }}>
                          <ProgressBar value={c.anchor_diversity * 100} max={100} color="#22d3ee" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}

            {/* Competitor Analysis */}
            {result.competitor_analysis && result.competitor_analysis.length > 0 && (
              <section style={s.card}>
                <p style={s.sectionTitle}>⚔️ Competitor Link Gap Analysis</p>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      {['Competitor', 'Backlinks', 'Gap Opportunity', 'Acquisition Tactics'].map((h) => (
                        <th key={h} style={s.th}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.competitor_analysis.map((c, i) => (
                      <tr key={`item-${i}`} style={{ background: i % 2 === 0 ? 'transparent' : 'var(--bg)' }}>
                        <td style={s.td}>
                          <strong>{c.competitor}</strong>
                        </td>
                        <td style={s.td}>{c.backlinks.toLocaleString()}</td>
                        <td style={{ ...s.td, maxWidth: 280 }}>{c.gap_opportunity}</td>
                        <td style={s.td}>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                            {c.acquisition_tactics.map((t) => (
                              <Badge key={t} label={t} color="#22d3ee" />
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            )}

            {/* Acquisition Opportunities */}
            {result.acquisition_opportunities && result.acquisition_opportunities.length > 0 && (
              <section style={s.card}>
                <p style={s.sectionTitle}>🎯 Link Acquisition Pipeline</p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 200px), 1fr))', gap: 12 }}>
                  {result.acquisition_opportunities.map((opp, i) => (
                    <div
                      key={`item-${i}`}
                      style={{
                        background: 'var(--bg)',
                        border: '1px solid var(--line)',
                        borderRadius: 10,
                        padding: 16,
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'flex-start',
                          marginBottom: 10,
                        }}
                      >
                        <span style={{ fontSize: 13, fontWeight: 700, textTransform: 'capitalize' }}>
                          {opp.type.replace(/_/g, ' ')}
                        </span>
                        <Badge label={opp.difficulty} color={DIFFICULTY_COLOR[opp.difficulty] ?? '#94a3b8'} />
                      </div>
                      <div style={{ fontSize: 26, fontWeight: 800, color: 'var(--brand)' }}>{opp.potential_links}</div>
                      <div style={{ fontSize: 11, color: 'var(--muted)' }}>potential links</div>
                      <ProgressBar
                        value={opp.potential_links}
                        max={30}
                        color={DIFFICULTY_COLOR[opp.difficulty] ?? '#94a3b8'}
                      />
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Next Actions */}
            {result.next_actions && result.next_actions.length > 0 && (
              <section style={s.card}>
                <p style={s.sectionTitle}>🚀 Recommended Next Actions</p>
                <ol style={{ margin: 0, paddingLeft: 20 }}>
                  {result.next_actions.map((action, i) => (
                    <li
                      key={`item-${i}`}
                      style={{ fontSize: 14, marginBottom: 8, color: 'var(--text)', lineHeight: 1.5 }}
                    >
                      {action}
                    </li>
                  ))}
                </ol>
              </section>
            )}

            {/* Footer meta */}
            <p style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'right' }}>Analysis ID: {result.analysis_id}</p>
          </>
        )}
      </div>
    </main>
  );
}
