'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { Network, Zap, RefreshCw, Copy, BarChart2, Globe, Star } from 'lucide-react';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type EntityMention = { entity: string; type: string; prominence: number; context: string };
type EntityRelation = { subject: string; relation: string; object: string; confidence: number };
type KgEntry = { entity: string; kg_id?: string; description?: string; types: string[]; prominence: number };
type EntityResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  entity_seo_score?: number;
  entity_coverage_pct?: number;
  entity_coverage_score?: number;
  authority_score?: number;
  entities_found?: EntityMention[];
  knowledge_graph_entries?: KgEntry[];
  entity_relations?: EntityRelation[];
  missing_entities?: string[];
  co_occurrence_clusters?: { cluster: string; entities: string[] }[];
  schema_recommendations?: string[];
  optimization_plan?: string[];
  fallback?: boolean;
};

function ScoreRing({ score, label, color = 'var(--brand)' }: { score: number; label: string; color?: string }) {
  const r = 32,
    s = 6,
    c = 2 * Math.PI * r;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
      <svg width={80} height={80} viewBox="0 0 80 80">
        <circle cx={40} cy={40} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={s} />
        <circle
          cx={40}
          cy={40}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={s}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - score / 100)}
          transform="rotate(-90 40 40)"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
        <text x={40} y={44} textAnchor="middle" fill={color} style={{ fontSize: 16, fontWeight: 800 }}>
          {score}
        </text>
      </svg>
      <span
        style={{
          fontSize: 10,
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

function ProminenceBar({ value }: { value: number }) {
  const color = value >= 0.7 ? '#26d78e' : value >= 0.4 ? '#ffb867' : 'var(--muted)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 100 }}>
      <div style={{ flex: 1, height: 4, background: 'rgba(255,255,255,0.08)', borderRadius: 2 }}>
        <div style={{ height: '100%', width: `${Math.round(value * 100)}%`, background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 10, color, fontWeight: 700, minWidth: 28 }}>{Math.round(value * 100)}%</span>
    </div>
  );
}

export default function EntityPage() {
  const [topic, setTopic] = useState('');
  const [content, setContent] = useState('');
  const [domain, setDomain] = useState('');
  const [result, setResult] = useState<EntityResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'entities' | 'kg' | 'relations' | 'plan'>('entities');
  const [copied, setCopied] = useState(false);

  async function run() {
    if (!content) {
      setError('Content is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<EntityResult>(
        '/seo-platform/entity/analyze',
        'POST',
        {
          topic,
          content,
          domain: domain || undefined,
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
      setActiveTab('entities');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }

  function copyPlan() {
    if (!result?.optimization_plan) return;
    void navigator.clipboard.writeText(result.optimization_plan.join('\n')).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
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
  const td: React.CSSProperties = { padding: '10px 12px', fontSize: 13, borderBottom: '1px solid var(--line)' };

  const ENTITY_TYPE_COLORS: Record<string, string> = {
    PERSON: '#1bc7ff',
    ORG: '#26d78e',
    LOC: '#ffb867',
    PRODUCT: '#ec4899',
    EVENT: '#f87171',
    CONCEPT: '#60a5fa',
  };

  const tabs = [
    { key: 'entities' as const, label: `Entities (${result?.entities_found?.length ?? 0})` },
    { key: 'kg' as const, label: 'Knowledge Graph' },
    { key: 'relations' as const, label: 'Relations' },
    { key: 'plan' as const, label: 'Optimization Plan' },
  ];

  const entityScore = result?.entity_seo_score ?? 0;
  const coverageScore = result?.entity_coverage_pct ?? result?.entity_coverage_score ?? 0;
  const authorityScore = result?.authority_score ?? 0;

  return (
    <main
      className="seo-advanced-page"
      style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', padding: 24 }}
    >
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <h1
          style={{ margin: '0 0 4px', fontSize: 24, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 10 }}
        >
          <Network size={24} color="var(--brand)" />
          Entity SEO
        </h1>
        <p style={{ margin: '0 0 24px', color: 'var(--muted)', fontSize: 14 }}>
          Entity extraction, knowledge graph mapping, relationship analysis &amp; topical authority
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
                Main Topic / Query
              </label>
              <input
                style={input}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="machine learning, SEO, etc."
              />
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
                Domain (optional)
              </label>
              <input
                style={input}
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
                Content to Analyze
              </label>
              <textarea
                style={{ ...input, minHeight: 120, resize: 'vertical' }}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Paste article, page content, or description..."
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
                <Network size={15} />
                Extract Entities
              </>
            )}
          </button>
        </section>

        {result && (
          <>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 130px), 1fr))',
                gap: 12,
                marginBottom: 20,
              }}
            >
              <div style={{ ...card, marginBottom: 0, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <ScoreRing score={entityScore} label="Entity Score" color="var(--brand)" />
                <div style={{ fontSize: 10, color: 'var(--muted)', textAlign: 'center', marginTop: 4 }}>
                  {result.cached ? 'Cached · ' : ''}
                  {result.analysis_mode === 'llm' ? 'AI model' : 'Heuristic (entity signals)'}
                </div>
              </div>
              <div style={{ ...card, marginBottom: 0, display: 'flex', justifyContent: 'center' }}>
                <ScoreRing score={coverageScore} label="Coverage" color="#26d78e" />
              </div>
              <div style={{ ...card, marginBottom: 0, display: 'flex', justifyContent: 'center' }}>
                <ScoreRing score={authorityScore} label="Authority" color="#ffb867" />
              </div>
              <div
                style={{
                  ...card,
                  marginBottom: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                  justifyContent: 'center',
                }}
              >
                <span style={{ fontSize: 10, color: 'var(--muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                  KG Entries
                </span>
                <span style={{ fontSize: 24, fontWeight: 800 }}>{result.knowledge_graph_entries?.length ?? 0}</span>
              </div>
              <div
                style={{
                  ...card,
                  marginBottom: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 4,
                  justifyContent: 'center',
                }}
              >
                <span style={{ fontSize: 10, color: '#f87171', fontWeight: 700, textTransform: 'uppercase' }}>
                  Missing
                </span>
                <span style={{ fontSize: 24, fontWeight: 800, color: '#f87171' }}>
                  {result.missing_entities?.length ?? 0}
                </span>
              </div>
            </div>

            {(result.missing_entities ?? []).length > 0 && (
              <div style={{ ...card }}>
                <div
                  style={{
                    fontSize: 12,
                    fontWeight: 700,
                    color: '#f87171',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    marginBottom: 10,
                  }}
                >
                  Missing Entities — Add to Content
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(result.missing_entities ?? []).map((e) => (
                    <span
                      key={e}
                      style={{
                        padding: '4px 12px',
                        borderRadius: 999,
                        background: 'rgba(248,113,113,0.1)',
                        color: '#f87171',
                        fontSize: 12,
                        fontWeight: 700,
                        border: '1px solid rgba(248,113,113,0.25)',
                      }}
                    >
                      {e}
                    </span>
                  ))}
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

            {activeTab === 'entities' && (
              <div style={card}>
                <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={th}>Entity</th>
                      <th style={th}>Type</th>
                      <th style={th}>Prominence</th>
                      <th style={th}>Context</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.entities_found?.map((e, i) => (
                      <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                        <td style={{ ...td, fontWeight: 600 }}>{e.entity ?? (e as { name?: string }).name ?? '—'}</td>
                        <td style={td}>
                          <span
                            style={{
                              padding: '2px 8px',
                              borderRadius: 4,
                              fontSize: 10,
                              fontWeight: 700,
                              background: (ENTITY_TYPE_COLORS[e.type] ?? 'var(--muted)') + '22',
                              color: ENTITY_TYPE_COLORS[e.type] ?? 'var(--muted)',
                            }}
                          >
                            {e.type}
                          </span>
                        </td>
                        <td style={td}>
                          <ProminenceBar value={e.prominence} />
                        </td>
                        <td style={{ ...td, color: 'var(--muted)', fontSize: 12 }}>{e.context}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {activeTab === 'kg' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Knowledge Graph Entries</h3>
                <div style={{ display: 'grid', gap: 10 }}>
                  {result.knowledge_graph_entries?.map((kg, i) => (
                    <div
                      key={i}
                      style={{
                        background: 'var(--bg)',
                        borderRadius: 10,
                        padding: '14px 16px',
                        border: '1px solid var(--line)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                        <Globe size={14} color="var(--brand)" />
                        <span style={{ fontWeight: 700, fontSize: 14 }}>{kg.entity}</span>
                        {kg.kg_id && (
                          <span style={{ fontSize: 11, color: 'var(--muted)', fontFamily: 'monospace' }}>
                            {kg.kg_id}
                          </span>
                        )}
                        <ProminenceBar value={kg.prominence} />
                      </div>
                      {kg.description && (
                        <p style={{ margin: '0 0 8px', fontSize: 13, color: 'var(--muted)', lineHeight: 1.5 }}>
                          {kg.description}
                        </p>
                      )}
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {kg.types.map((t) => (
                          <span
                            key={t}
                            style={{
                              padding: '2px 8px',
                              borderRadius: 4,
                              fontSize: 10,
                              fontWeight: 700,
                              background: 'rgba(27,199,255,0.1)',
                              color: 'var(--brand)',
                            }}
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'relations' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Entity Relations</h3>
                <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      <th style={th}>Subject</th>
                      <th style={th}>Relation</th>
                      <th style={th}>Object</th>
                      <th style={th}>Confidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.entity_relations?.map((r, i) => (
                      <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}>
                        <td style={{ ...td, fontWeight: 600 }}>{r.subject}</td>
                        <td style={{ ...td, color: 'var(--brand)', fontStyle: 'italic', fontSize: 12 }}>
                          {r.relation}
                        </td>
                        <td style={{ ...td, fontWeight: 600 }}>{r.object}</td>
                        <td style={td}>
                          <ProminenceBar value={r.confidence} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {(result.co_occurrence_clusters ?? []).length > 0 && (
                  <div style={{ marginTop: 20 }}>
                    <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700 }}>Co-occurrence Clusters</h3>
                    <div style={{ display: 'grid', gap: 10 }}>
                      {(result.co_occurrence_clusters ?? []).map((cl, i) => (
                        <div
                          key={i}
                          style={{
                            background: 'var(--bg)',
                            borderRadius: 10,
                            padding: '12px 16px',
                            border: '1px solid var(--line)',
                          }}
                        >
                          <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8, color: '#ffb867' }}>
                            {cl.cluster}
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {cl.entities.map((e) => (
                              <span
                                key={e}
                                style={{
                                  padding: '3px 10px',
                                  borderRadius: 999,
                                  background: 'rgba(255,184,103,0.1)',
                                  color: '#ffb867',
                                  fontSize: 11,
                                  fontWeight: 700,
                                  border: '1px solid rgba(255,184,103,0.25)',
                                }}
                              >
                                {e}
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'plan' && (
              <div style={card}>
                <div
                  style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}
                >
                  <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>Entity Optimization Plan</h3>
                  <button
                    onClick={copyPlan}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      background: 'none',
                      border: '1px solid var(--line)',
                      borderRadius: 6,
                      color: copied ? '#26d78e' : 'var(--muted)',
                      cursor: 'pointer',
                      fontSize: 12,
                      padding: '6px 12px',
                    }}
                  >
                    <Copy size={11} />
                    {copied ? 'Copied!' : 'Copy Plan'}
                  </button>
                </div>
                {result.optimization_plan?.map((step, i) => (
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
                        width: 24,
                        height: 24,
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
                    <span style={{ fontSize: 13, lineHeight: 1.5 }}>{step}</span>
                  </div>
                ))}
                {(result.schema_recommendations ?? []).length > 0 && (
                  <div style={{ marginTop: 20 }}>
                    <h3 style={{ margin: '0 0 12px', fontSize: 14, fontWeight: 700 }}>Schema Markup Recommendations</h3>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {(result.schema_recommendations ?? []).map((s) => (
                        <span
                          key={s}
                          style={{
                            padding: '4px 12px',
                            borderRadius: 999,
                            background: 'rgba(37,99,235,0.1)',
                            color: '#2563eb',
                            fontSize: 12,
                            fontWeight: 700,
                            border: '1px solid rgba(37,99,235,0.25)',
                          }}
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </main>
  );
}
