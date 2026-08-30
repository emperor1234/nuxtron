'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { Search, Zap, AlertTriangle, CheckCircle, RefreshCw, Copy, BarChart2 } from 'lucide-react';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type SeoSignal = {
  signal: string;
  status: 'pass' | 'fail' | 'warn';
  detail: string;
  priority: 'high' | 'medium' | 'low';
};
type ContentSuggestion = { section: string; suggestion: string; impact: string };
type OnPageResult = {
  analysis_id: string;
  seo_score: number;
  readability_score: number;
  keyword_density: number;
  word_count: number;
  signals: SeoSignal[];
  content_suggestions: ContentSuggestion[];
  title_tags: { current?: string; recommended?: string; issues?: string[] };
  meta_description: { current?: string; recommended?: string; issues?: string[] };
  heading_structure: { h1: string[]; h2: string[]; h3: string[] };
  internal_link_opportunities: string[];
  quick_wins: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

type ScoreRingProps = Readonly<{ score: number; label: string }>;
type SignalRowProps = Readonly<{ s: SeoSignal }>;

const ONPAGE_AUDIT_PHASES = [
  'Capture URL and keyword intent context',
  'Evaluate metadata, structure, and signal quality',
  'Prioritize quick wins and content improvements',
];

function getIndentForLevel(level: 'h1' | 'h2' | 'h3'): number {
  if (level === 'h2') return 24;
  if (level === 'h3') return 40;
  return 12;
}

function ScoreRing({ score, label }: ScoreRingProps) {
  const r = 36,
    s = 7,
    c = 2 * Math.PI * r;
  let color = '#dc2626';
  if (score >= 75) {
    color = '#26d78e';
  } else if (score >= 50) {
    color = '#ffb867';
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <svg width={90} height={90} viewBox="0 0 90 90">
        <circle cx={45} cy={45} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={s} />
        <circle
          cx={45}
          cy={45}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={s}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - score / 100)}
          transform="rotate(-90 45 45)"
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
        <text x={45} y={49} textAnchor="middle" fill={color} style={{ fontSize: 18, fontWeight: 800 }}>
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

function SignalRow({ s }: SignalRowProps) {
  const Icon = s.status === 'pass' ? CheckCircle : AlertTriangle;
  let color = '#ffb867';
  if (s.status === 'pass') {
    color = '#26d78e';
  } else if (s.status === 'fail') {
    color = '#dc2626';
  }

  let prColor = 'var(--muted)';
  if (s.priority === 'high') {
    prColor = '#dc2626';
  } else if (s.priority === 'medium') {
    prColor = '#ffb867';
  }
  return (
    <tr>
      <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--line)', width: 32 }}>
        <Icon size={14} color={color} />
      </td>
      <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--line)', fontWeight: 600, fontSize: 13 }}>
        {s.signal}
      </td>
      <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--line)', color: 'var(--muted)', fontSize: 12 }}>
        {s.detail}
      </td>
      <td style={{ padding: '10px 12px', borderBottom: '1px solid var(--line)' }}>
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            textTransform: 'uppercase',
            padding: '2px 6px',
            borderRadius: 4,
            background: prColor + '22',
            color: prColor,
          }}
        >
          {s.priority}
        </span>
      </td>
    </tr>
  );
}

export default function OnPagePage() {
  const [url, setUrl] = useState('');
  const [keyword, setKeyword] = useState('');
  const [content, setContent] = useState('');
  const [result, setResult] = useState<OnPageResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'signals' | 'content' | 'meta' | 'structure'>('signals');
  const [copied, setCopied] = useState<string | null>(null);

  async function run() {
    if (!url || !keyword) {
      setError('URL and focus keyword are required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<OnPageResult>(
        '/seo-platform/on-page/analyze',
        'POST',
        { url, keyword, content: content || undefined },
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
      setActiveTab('signals');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }

  function copyText(text: string, id: string) {
    void navigator.clipboard.writeText(text).then(() => {
      setCopied(id);
      setTimeout(() => setCopied(null), 2000);
    });
  }

  const card: React.CSSProperties = {
    background: '#ffffff',
    border: '1px solid rgba(148, 163, 184, 0.16)',
    borderRadius: 16,
    padding: '20px 24px',
    marginBottom: 20,
    backdropFilter: 'blur(12px)',
    boxShadow: '0 20px 60px -45px rgba(45, 212, 191, 0.6)',
  };
  const input: React.CSSProperties = {
    width: '100%',
    padding: '11px 14px',
    borderRadius: 12,
    border: '1px solid rgba(148, 163, 184, 0.2)',
    background: '#ffffff',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box',
    fontSize: 14,
  };
  const tabs = [
    { key: 'signals' as const, label: `SEO Signals (${result?.signals?.length ?? 0})` },
    { key: 'content' as const, label: 'Content' },
    { key: 'meta' as const, label: 'Title & Meta' },
    { key: 'structure' as const, label: 'Structure' },
  ];
  const passes = result?.signals?.filter((s) => s.status === 'pass').length ?? 0;
  const fails = result?.signals?.filter((s) => s.status === 'fail').length ?? 0;

  return (
    <main className="seo-advanced-page" style={{ minHeight: '100vh', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <section style={{ marginBottom: 20 }}>
          <h1 style={{ margin: '0 0 6px', fontSize: 27, fontWeight: 700, letterSpacing: '-0.6px', color: 'var(--nx-ink, var(--text))' }}>
            On-Page Optimizer
          </h1>
          <p style={{ margin: 0, color: 'var(--nx-muted, var(--muted))', fontSize: 14 }}>
            SEO signals, meta tags, heading structure, keyword density, and practical content recommendations.
          </p>
        </section>

        {error && (
          <div style={{ ...card, color: '#dc2626', borderColor: '#dc262644', background: '#dc262611' }}>{error}</div>
        )}

        <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))' }}>
          <section style={{ ...card, marginBottom: 0 }}>
            <div style={{ marginBottom: 12 }}>
              <h2 style={{ margin: 0, fontSize: 16, color: 'var(--text)' }}>Audit Inputs</h2>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                Configure core signals for on-page diagnosis
              </p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 16 }}>
              <div>
                <label
                  htmlFor="onpage-url"
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
                  Page URL
                </label>
                <input
                  id="onpage-url"
                  style={input}
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://example.com/article"
                />
                <label
                  htmlFor="onpage-keyword"
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
                  Focus Keyword
                </label>
                <input
                  id="onpage-keyword"
                  style={input}
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="seo best practices"
                />
              </div>
              <div>
                <label
                  htmlFor="onpage-content"
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
                  Page Content (optional)
                </label>
                <textarea
                  id="onpage-content"
                  style={{ ...input, minHeight: 100, resize: 'vertical' }}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Paste page content for deeper analysis..."
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
                borderRadius: 8,
                background: loading ? 'var(--muted)' : 'var(--brand)',
                color: '#ecfeff',
                fontWeight: 800,
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: 14,
                border: '1px solid rgba(94,234,212,0.35)',
                backgroundImage: loading
                  ? 'none'
                  : 'linear-gradient(90deg, rgba(20,184,166,0.9) 0%, rgba(6,182,212,0.85) 100%)',
              }}
            >
              {loading ? (
                <>
                  <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} />
                  Analyzing...
                </>
              ) : (
                <>
                  <Search size={15} />
                  Analyze Page
                </>
              )}
            </button>
          </section>

          <aside style={{ ...card, marginBottom: 0 }}>
            <div>
              <h3 style={{ margin: '0 0 6px', fontSize: 16, color: 'var(--text)' }}>Audit Blueprint</h3>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>Execution stages for on-page optimization.</p>
            </div>
            <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
              {ONPAGE_AUDIT_PHASES.map((phase, index) => (
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
                      border: '1px solid rgba(94,234,212,0.4)',
                      background: 'rgba(45,212,191,0.16)',
                      color: '#99f6e4',
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
                    border: '1px solid rgba(94,234,212,0.35)',
                    background: 'rgba(45,212,191,0.14)',
                    color: '#99f6e4',
                    borderRadius: 999,
                    padding: '3px 8px',
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  {keyword.trim() ? 'Keyword set' : 'Keyword pending'}
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
                  {content.trim() ? 'Content provided' : 'URL-first analysis'}
                </span>
              </div>
            </div>
          </aside>
        </div>

        {result && (
          <>
            {(result.analysis_mode || result.cached) && (
              <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                {result.analysis_mode && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background: result.analysis_mode === 'llm' ? 'rgba(34,197,94,0.15)' : 'rgba(148,163,184,0.15)',
                      color: result.analysis_mode === 'llm' ? '#4ade80' : 'var(--muted)',
                    }}
                  >
                    {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                  </span>
                )}
                {result.cached && (
                  <span
                    style={{
                      fontSize: 11,
                      fontWeight: 700,
                      padding: '4px 10px',
                      borderRadius: 999,
                      background: 'rgba(56,189,248,0.15)',
                      color: '#38bdf8',
                    }}
                  >
                    Cached result
                  </span>
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
              <div style={{ ...card, marginBottom: 0, display: 'flex', justifyContent: 'center' }}>
                <ScoreRing score={result.seo_score} label="SEO Score" />
              </div>
              <div style={{ ...card, marginBottom: 0, display: 'flex', justifyContent: 'center' }}>
                <ScoreRing score={result.readability_score} label="Readability" />
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
                  Word Count
                </span>
                <span style={{ fontSize: 24, fontWeight: 800 }}>{result.word_count?.toLocaleString()}</span>
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
                  KW Density
                </span>
                <span
                  style={{ fontSize: 24, fontWeight: 800, color: result.keyword_density > 3 ? '#dc2626' : '#26d78e' }}
                >
                  {result.keyword_density?.toFixed(1)}%
                </span>
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
                <span style={{ fontSize: 10, color: '#26d78e', fontWeight: 700, textTransform: 'uppercase' }}>
                  Passing
                </span>
                <span style={{ fontSize: 24, fontWeight: 800, color: '#26d78e' }}>{passes}</span>
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
                <span style={{ fontSize: 10, color: '#dc2626', fontWeight: 700, textTransform: 'uppercase' }}>
                  Failing
                </span>
                <span style={{ fontSize: 24, fontWeight: 800, color: '#dc2626' }}>{fails}</span>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 6, marginBottom: 16, borderBottom: '1px solid rgba(148,163,184,0.2)' }}>
              {tabs.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setActiveTab(t.key)}
                  style={{
                    padding: '8px 16px',
                    border: '1px solid transparent',
                    borderRadius: '10px 10px 0 0',
                    background: activeTab === t.key ? 'transparent' : 'transparent',
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

            {activeTab === 'signals' && (
              <div style={card}>
                <div style={{ overflowX: 'auto' }}>
                  <table className="data-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr>
                        <th style={{ width: 32, padding: '8px 12px', borderBottom: '1px solid var(--line)' }}></th>
                        <th
                          style={{
                            textAlign: 'left',
                            padding: '8px 12px',
                            fontSize: 11,
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            color: 'var(--muted)',
                            borderBottom: '1px solid var(--line)',
                          }}
                        >
                          Signal
                        </th>
                        <th
                          style={{
                            textAlign: 'left',
                            padding: '8px 12px',
                            fontSize: 11,
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            color: 'var(--muted)',
                            borderBottom: '1px solid var(--line)',
                          }}
                        >
                          Detail
                        </th>
                        <th
                          style={{
                            textAlign: 'left',
                            padding: '8px 12px',
                            fontSize: 11,
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            color: 'var(--muted)',
                            borderBottom: '1px solid var(--line)',
                          }}
                        >
                          Priority
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.signals?.map((s) => (
                        <SignalRow key={`${s.signal}-${s.status}-${s.priority}`} s={s} />
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {activeTab === 'content' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Content Suggestions</h3>
                <div style={{ display: 'grid', gap: 10, marginBottom: 20 }}>
                  {result.content_suggestions?.map((s) => (
                    <div
                      key={`${s.section}-${s.impact}-${s.suggestion}`}
                      style={{
                        background: 'var(--bg)',
                        borderRadius: 10,
                        padding: '14px 16px',
                        border: '1px solid var(--line)',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          marginBottom: 6,
                        }}
                      >
                        <span
                          style={{ fontSize: 12, fontWeight: 700, color: 'var(--brand)', textTransform: 'uppercase' }}
                        >
                          {s.section}
                        </span>
                        <span style={{ fontSize: 11, color: '#26d78e' }}>Impact: {s.impact}</span>
                      </div>
                      <p style={{ margin: 0, fontSize: 13, color: 'var(--muted)', lineHeight: 1.5 }}>{s.suggestion}</p>
                    </div>
                  ))}
                </div>
                {result.quick_wins?.length > 0 && (
                  <div>
                    <h3 style={{ margin: '0 0 12px', fontSize: 15, fontWeight: 700 }}>Quick Wins</h3>
                    {result.quick_wins.map((w) => (
                      <div
                        key={`win-${w}`}
                        style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}
                      >
                        <Zap size={12} color="#26d78e" style={{ marginTop: 2, flexShrink: 0 }} />
                        <span style={{ fontSize: 13 }}>{w}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'meta' && (
              <div style={card}>
                {[
                  {
                    label: 'Title Tag',
                    current: result.title_tags?.current,
                    recommended: result.title_tags?.recommended,
                    issues: result.title_tags?.issues,
                  },
                  {
                    label: 'Meta Description',
                    current: result.meta_description?.current,
                    recommended: result.meta_description?.recommended,
                    issues: result.meta_description?.issues,
                  },
                ].map((m) => (
                  <div key={m.label} style={{ marginBottom: 24 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>{m.label}</div>
                    {m.current && (
                      <div
                        style={{
                          background: 'var(--bg)',
                          borderRadius: 8,
                          padding: '10px 14px',
                          border: '1px solid var(--line)',
                          marginBottom: 8,
                        }}
                      >
                        <div
                          style={{
                            fontSize: 10,
                            color: 'var(--muted)',
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            marginBottom: 4,
                          }}
                        >
                          Current
                        </div>
                        <div style={{ fontSize: 13 }}>{m.current}</div>
                      </div>
                    )}
                    {m.recommended && (
                      <div
                        style={{
                          background: 'rgba(38,215,142,0.06)',
                          borderRadius: 8,
                          padding: '10px 14px',
                          border: '1px solid rgba(38,215,142,0.25)',
                          marginBottom: 8,
                        }}
                      >
                        <div
                          style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: 4,
                          }}
                        >
                          <span style={{ fontSize: 10, color: '#26d78e', fontWeight: 700, textTransform: 'uppercase' }}>
                            Recommended
                          </span>
                          <button
                            onClick={() => copyText(m.recommended!, m.label)}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 4,
                              background: 'none',
                              border: 'none',
                              color: copied === m.label ? '#26d78e' : 'var(--muted)',
                              cursor: 'pointer',
                              fontSize: 11,
                            }}
                          >
                            <Copy size={11} />
                            {copied === m.label ? 'Copied!' : 'Copy'}
                          </button>
                        </div>
                        <div style={{ fontSize: 13, color: '#26d78e' }}>{m.recommended}</div>
                      </div>
                    )}
                    {m.issues?.map((issue) => (
                      <div
                        key={`${m.label}-${issue}`}
                        style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}
                      >
                        <AlertTriangle size={12} color="#ffb867" />
                        <span style={{ fontSize: 12, color: 'var(--muted)' }}>{issue}</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'structure' && (
              <div style={card}>
                <h3 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 700 }}>Heading Structure</h3>
                {result.heading_structure &&
                  (['h1', 'h2', 'h3'] as const).map((level) => {
                    const headings = result.heading_structure[level];
                    if (!headings?.length) return null;
                    return (
                      <div key={level} style={{ marginBottom: 20 }}>
                        <div
                          style={{
                            fontSize: 12,
                            fontWeight: 700,
                            color: 'var(--brand)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.06em',
                            marginBottom: 8,
                          }}
                        >
                          {level.toUpperCase()} ({headings.length})
                        </div>
                        {headings.map((h) => (
                          <div
                            key={`${level}-${h}`}
                            style={{
                              padding: '8px 12px',
                              marginBottom: 4,
                              background: 'var(--bg)',
                              borderRadius: 6,
                              border: '1px solid var(--line)',
                              fontSize: 13,
                              paddingLeft: getIndentForLevel(level),
                            }}
                          >
                            {h}
                          </div>
                        ))}
                      </div>
                    );
                  })}
                {result.internal_link_opportunities?.length > 0 && (
                  <div>
                    <h3 style={{ margin: '16px 0 12px', fontSize: 14, fontWeight: 700 }}>
                      Internal Link Opportunities
                    </h3>
                    {result.internal_link_opportunities.map((opp) => (
                      <div
                        key={`opp-${opp}`}
                        style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}
                      >
                        <BarChart2 size={12} color="var(--brand)" style={{ marginTop: 2, flexShrink: 0 }} />
                        <span style={{ fontSize: 13 }}>{opp}</span>
                      </div>
                    ))}
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
