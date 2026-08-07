'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';
import { FileSearch, Zap, RefreshCw, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type FactCheck = {
  claim: string;
  verdict: 'verified' | 'unverified' | 'risky';
  confidence: number;
  evidence_hint: string;
};
type Rewrite = { issue: string; fix: string; priority: 'critical' | 'high' | 'medium' | 'low' };
type EeatSignals = { expertise: number; experience: number; authority: number; trust: number };
type ContentResult = {
  analysis_id: string;
  quality_score: number;
  hallucination_risk: 'low' | 'medium' | 'high';
  fact_checks: FactCheck[];
  eeat_signals: EeatSignals;
  citation_coverage_pct: number;
  rewrite_recommendations: Rewrite[];
  risky_sections: string[];
  quick_wins: string[];
  audited_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

function ScoreBar({ value, max = 100, label, color }: { value: number; max?: number; label: string; color: string }) {
  const pct = Math.round((value / max) * 100);
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 12, fontWeight: 600 }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 800, color }}>
          {value}
          <span style={{ color: 'var(--muted)', fontWeight: 400 }}>/{max}</span>
        </span>
      </div>
      <div style={{ height: 6, background: 'rgba(255,255,255,0.08)', borderRadius: 3, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            background: color,
            borderRadius: 3,
            transition: 'width 0.6s ease',
          }}
        />
      </div>
    </div>
  );
}

function RiskBadge({ risk }: { risk: string }) {
  const cfg = {
    low: { bg: 'rgba(38,215,142,0.1)', color: '#26d78e', border: 'rgba(38,215,142,0.3)', label: 'Low Risk' },
    medium: { bg: 'rgba(255,184,103,0.1)', color: '#ffb867', border: 'rgba(255,184,103,0.3)', label: 'Medium Risk' },
    high: { bg: 'rgba(248,113,113,0.1)', color: '#dc2626', border: 'rgba(248,113,113,0.3)', label: 'High Risk' },
  };
  const c = cfg[risk as keyof typeof cfg] ?? cfg.low;
  return (
    <span
      style={{
        padding: '4px 12px',
        borderRadius: 999,
        background: c.bg,
        color: c.color,
        border: `1px solid ${c.border}`,
        fontSize: 12,
        fontWeight: 700,
      }}
    >
      {c.label}
    </span>
  );
}

export default function ContentAuditorPage() {
  const [url, setUrl] = useState('');
  const [content, setContent] = useState('');
  const [topic, setTopic] = useState('');
  const [result, setResult] = useState<ContentResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'factcheck' | 'rewrites' | 'eeat'>('overview');

  async function run() {
    if (!content && !url) {
      setError('URL or content is required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<ContentResult>(
        '/seo-platform/content-auditor/analyze',
        'POST',
        { url: url || undefined, content: content || undefined, topic: topic || undefined },
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
      setError(e instanceof Error ? e.message : 'Audit failed');
    } finally {
      setLoading(false);
    }
  }

  const card: React.CSSProperties = {
    background: '#ffffff',
    border: '1px solid rgba(148, 163, 184, 0.16)',
    borderRadius: 16,
    padding: '20px 24px',
    marginBottom: 20,
    backdropFilter: 'blur(12px)',
    boxShadow: '0 20px 60px -45px rgba(56, 189, 248, 0.55)',
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
  const PRIORITY_COLORS = { critical: '#dc2626', high: '#ff8800', medium: '#ffb867', low: 'var(--muted)' };
  const tabs = [
    { key: 'overview' as const, label: 'Overview' },
    { key: 'factcheck' as const, label: `Fact Checks (${result?.fact_checks?.length ?? 0})` },
    { key: 'rewrites' as const, label: `Rewrites (${result?.rewrite_recommendations?.length ?? 0})` },
    { key: 'eeat' as const, label: 'E-E-A-T' },
  ];

  return (
    <main className="seo-advanced-page" style={{ minHeight: '100vh', padding: 24 }}>
      <div style={{ maxWidth: 1100, margin: '0 auto' }}>
        <section
          style={{
            position: 'relative',
            overflow: 'hidden',
            borderRadius: 16,
            border: '1px solid rgba(56, 189, 248, 0.25)',
            background: 'var(--card)',
            padding: '22px 24px',
            marginBottom: 20,
          }}
        >
          <div style={{ display: 'inline-flex', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.12em',
                color: 'var(--brand)',
                border: '1px solid rgba(125,211,252,0.45)',
                borderRadius: 999,
                padding: '3px 10px',
                background: 'rgba(34,211,238,0.12)',
              }}
            >
              AI QA Engine
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
              Trust & Fact Validation
            </span>
          </div>
          <h1
            style={{
              margin: '0 0 4px',
              fontSize: 30,
              fontWeight: 800,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              color: 'var(--text)',
            }}
          >
            <FileSearch size={26} color="#22d3ee" />
            Content Auditor
          </h1>
          <p style={{ margin: '0', color: 'var(--muted)', fontSize: 15 }}>
            AI fact-checking, hallucination detection, E-E-A-T signals, and rewrite recommendations.
          </p>
        </section>

        {error && (
          <div style={{ ...card, color: '#dc2626', borderColor: '#dc262644', background: '#dc262611' }}>{error}</div>
        )}

        <section style={card}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 280px), 1fr))', gap: 16 }}>
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
                Page URL (optional)
              </label>
              <input
                style={input}
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/article"
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
                Topic / Subject
              </label>
              <input
                style={input}
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="AI in healthcare, SEO basics..."
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
                Content to Audit
              </label>
              <textarea
                style={{ ...input, minHeight: 110, resize: 'vertical' }}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Paste your article content here..."
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
              border: '1px solid rgba(125,211,252,0.35)',
              borderRadius: 10,
              background: loading
                ? 'rgba(100,116,139,0.35)'
                : 'linear-gradient(90deg, rgba(6,182,212,0.9) 0%, rgba(20,184,166,0.9) 100%)',
              color: '#ecfeff',
              fontWeight: 800,
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: 14,
            }}
          >
            {loading ? (
              <>
                <RefreshCw size={15} style={{ animation: 'spin 1s linear infinite' }} />
                Auditing...
              </>
            ) : (
              <>
                <FileSearch size={15} />
                Audit Content
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
                  Quality Score
                </div>
                <div
                  style={{
                    fontSize: 32,
                    fontWeight: 800,
                    color: result.quality_score >= 70 ? '#26d78e' : result.quality_score >= 50 ? '#ffb867' : '#dc2626',
                  }}
                >
                  {result.quality_score}
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
                  Hallucination Risk
                </div>
                <RiskBadge risk={result.hallucination_risk} />
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
                  Citation Coverage
                </div>
                <div
                  style={{
                    fontSize: 32,
                    fontWeight: 800,
                    color: result.citation_coverage_pct >= 60 ? '#26d78e' : '#ffb867',
                  }}
                >
                  {result.citation_coverage_pct}%
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
                  Risky Sections
                </div>
                <div
                  style={{
                    fontSize: 32,
                    fontWeight: 800,
                    color: (result.risky_sections?.length ?? 0) > 0 ? '#dc2626' : '#26d78e',
                  }}
                >
                  {result.risky_sections?.length ?? 0}
                </div>
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

            {activeTab === 'overview' && (
              <div style={card}>
                {result.risky_sections?.length > 0 && (
                  <div style={{ marginBottom: 20 }}>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: '#dc2626',
                        textTransform: 'uppercase',
                        letterSpacing: '0.06em',
                        marginBottom: 10,
                      }}
                    >
                      Risky Sections
                    </div>
                    {result.risky_sections.map((s, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
                        <AlertTriangle size={13} color="#dc2626" style={{ marginTop: 1, flexShrink: 0 }} />
                        <span style={{ fontSize: 13 }}>{s}</span>
                      </div>
                    ))}
                  </div>
                )}
                <div>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: '#26d78e',
                      textTransform: 'uppercase',
                      letterSpacing: '0.06em',
                      marginBottom: 10,
                    }}
                  >
                    Quick Wins
                  </div>
                  {result.quick_wins?.map((w, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 8 }}>
                      <Zap size={12} color="#26d78e" style={{ marginTop: 2, flexShrink: 0 }} />
                      <span style={{ fontSize: 13 }}>{w}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'factcheck' && (
              <div style={card}>
                <div style={{ display: 'grid', gap: 10 }}>
                  {result.fact_checks?.map((fc, i) => {
                    const color =
                      fc.verdict === 'verified' ? '#26d78e' : fc.verdict === 'risky' ? '#dc2626' : '#ffb867';
                    return (
                      <div
                        key={i}
                        style={{
                          background: 'var(--bg)',
                          borderRadius: 10,
                          padding: '14px 16px',
                          border: `1px solid ${color}44`,
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
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            {fc.verdict === 'verified' ? (
                              <CheckCircle size={14} color="#26d78e" />
                            ) : (
                              <AlertTriangle size={14} color={color} />
                            )}
                            <span
                              style={{
                                fontSize: 11,
                                fontWeight: 700,
                                textTransform: 'uppercase',
                                color,
                                padding: '2px 6px',
                                borderRadius: 4,
                                background: color + '22',
                              }}
                            >
                              {fc.verdict}
                            </span>
                          </div>
                          <span style={{ fontSize: 11, color: 'var(--muted)' }}>
                            Confidence: <strong style={{ color }}>{Math.round(fc.confidence * 100)}%</strong>
                          </span>
                        </div>
                        <p style={{ margin: '0 0 6px', fontSize: 13, fontWeight: 600 }}>{fc.claim}</p>
                        <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 }}>
                          {fc.evidence_hint}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {activeTab === 'rewrites' && (
              <div style={card}>
                <div style={{ display: 'grid', gap: 10 }}>
                  {result.rewrite_recommendations?.map((r, i) => (
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
                        <span
                          style={{
                            fontSize: 11,
                            fontWeight: 700,
                            textTransform: 'uppercase',
                            padding: '2px 6px',
                            borderRadius: 4,
                            background: PRIORITY_COLORS[r.priority] + '22',
                            color: PRIORITY_COLORS[r.priority],
                          }}
                        >
                          {r.priority}
                        </span>
                      </div>
                      <p style={{ margin: '0 0 6px', fontSize: 13, fontWeight: 600, color: '#dc2626' }}>
                        Issue: {r.issue}
                      </p>
                      <p style={{ margin: 0, fontSize: 13, color: '#26d78e', lineHeight: 1.5 }}>Fix: {r.fix}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'eeat' && result.eeat_signals && (
              <div style={card}>
                <h3 style={{ margin: '0 0 20px', fontSize: 15, fontWeight: 700 }}>E-E-A-T Signals</h3>
                <ScoreBar value={result.eeat_signals.expertise} label="Expertise" color="#1bc7ff" />
                <ScoreBar value={result.eeat_signals.experience} label="Experience" color="#26d78e" />
                <ScoreBar value={result.eeat_signals.authority} label="Authoritativeness" color="#ffb867" />
                <ScoreBar value={result.eeat_signals.trust} label="Trustworthiness" color="#2563eb" />
                <div
                  style={{
                    marginTop: 16,
                    padding: '12px 16px',
                    background: 'var(--bg)',
                    borderRadius: 10,
                    border: '1px solid var(--line)',
                    fontSize: 13,
                    color: 'var(--muted)',
                    lineHeight: 1.6,
                  }}
                >
                  E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness) is Google's quality rater
                  framework. Aim for scores above 70 in all areas for YMYL content.
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
