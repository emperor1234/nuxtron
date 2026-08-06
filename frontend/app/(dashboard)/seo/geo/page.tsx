'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type GeoResult = {
  geo_score?: number;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
  engine_scores?: Record<string, number>;
  [key: string]: unknown;
};

const GEO_AUDIT_PHASES = [
  'Map topic and multi-engine context',
  'Score citation, structure, and authority signals',
  'Prioritize cross-engine optimization actions',
];

export default function GEOPage() {
  const [topic, setTopic] = useState('');
  const [content, setContent] = useState('');
  const engines = ['ChatGPT', 'Perplexity', 'Gemini', 'Google AI Overview'];
  const [serpContext, setSerpContext] = useState('Top SERP findings and answer snapshots');
  const [siteContentContext, setSiteContentContext] = useState('Site pillars, authoritative pages, and existing FAQs');
  const [ragEnabled, setRagEnabled] = useState(true);
  const [aiModel, setAiModel] = useState('llama3');
  const [result, setResult] = useState<GeoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!content || !topic) {
      setError('Topic and content are required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<GeoResult>(
        '/seo-platform/geo/optimize',
        'POST',
        {
          topic,
          content,
          target_engines: engines,
          ai_model: aiModel,
          rag_enabled: ragEnabled,
          serp_context: serpContext,
          site_content_context: siteContentContext,
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
      setError(e instanceof Error ? e.message : 'GEO analysis failed');
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    void run();
  }

  const card = {
    background: '#ffffff',
    border: '1px solid rgba(148, 163, 184, 0.16)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    backdropFilter: 'blur(12px)',
    boxShadow: '0 20px 60px -45px rgba(59, 130, 246, 0.65)',
  };
  const inp = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: 12,
    border: '1px solid rgba(148, 163, 184, 0.22)',
    background: '#ffffff',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };
  const engineScores = result?.engine_scores as Record<string, number> | undefined;

  return (
    <main style={{ minHeight: '100vh', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <section
          style={{
            position: 'relative',
            overflow: 'hidden',
            borderRadius: 16,
            border: '1px solid var(--line)',
            background: 'var(--card)',
            boxShadow: 'var(--shadow-sm)',
            padding: '22px 24px',
            marginBottom: 20,
          }}
        >
          <div
            style={{
              display: 'grid',
              gap: 16,
              alignItems: 'end',
              gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))',
            }}
          >
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
                  GEO Engine
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
                  LLM Citation Optimization
                </span>
              </div>
              <h1 style={{ margin: '0 0 4px', fontSize: 30, fontWeight: 800, color: 'var(--text)' }}>GEO</h1>
              <p style={{ color: 'var(--muted)', margin: 0 }}>
                Optimize content to be cited by ChatGPT, Perplexity, Gemini, and Google AI Overviews.
              </p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 420px), 1fr))', gap: 8 }}>
              <div
                style={{
                  background: '#f6f7fa',
                  border: '1px solid rgba(148,163,184,0.2)',
                  borderRadius: 10,
                  padding: '8px 10px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  AI Model
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--brand)' }}>
                  {aiModel || 'llama3'}
                </div>
              </div>
              <div
                style={{
                  background: '#f6f7fa',
                  border: '1px solid rgba(148,163,184,0.2)',
                  borderRadius: 10,
                  padding: '8px 10px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  RAG
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--brand)' }}>
                  {ragEnabled ? 'Enabled' : 'Disabled'}
                </div>
              </div>
              <div
                style={{
                  background: '#f6f7fa',
                  border: '1px solid rgba(148,163,184,0.2)',
                  borderRadius: 10,
                  padding: '8px 10px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  Engines
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>{engines.length}</div>
              </div>
              <div
                style={{
                  background: '#f6f7fa',
                  border: '1px solid rgba(148,163,184,0.2)',
                  borderRadius: 10,
                  padding: '8px 10px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  Output
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>Citation Plan</div>
              </div>
            </div>
          </div>
        </section>
        {error && <div style={{ ...card, color: '#b91c1c' }}>{error}</div>}
        <div
          style={{
            display: 'grid',
            gap: 16,
            gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 320px), 1fr))',
            marginBottom: 16,
          }}
        >
          <form style={{ ...card, marginBottom: 0 }} onSubmit={handleSubmit}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                marginBottom: 10,
              }}
            >
              <div>
                <h2 style={{ margin: 0, fontSize: 16, color: 'var(--text)' }}>Optimization Inputs</h2>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                  Configure context for multi-engine GEO optimization
                </p>
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

            <label htmlFor="geo-topic" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Topic
            </label>
            <input
              id="geo-topic"
              style={inp}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Best CRM software for startups"
            />
            <label htmlFor="geo-content" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Content to Optimize
            </label>
            <textarea
              id="geo-content"
              style={{ ...inp, minHeight: 180 }}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste your article or content here..."
            />
            <label
              htmlFor="geo-serp-context"
              style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
            >
              SERP + AI Answer Context
            </label>
            <textarea
              id="geo-serp-context"
              style={{ ...inp, minHeight: 90 }}
              value={serpContext}
              onChange={(e) => setSerpContext(e.target.value)}
              placeholder="Summarize SERP intent, AI answers, and citation patterns"
            />
            <label
              htmlFor="geo-site-context"
              style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}
            >
              Site Content Context
            </label>
            <textarea
              id="geo-site-context"
              style={{ ...inp, minHeight: 90 }}
              value={siteContentContext}
              onChange={(e) => setSiteContentContext(e.target.value)}
              placeholder="Core pages, existing hubs, and authority assets"
            />
            <label htmlFor="geo-ai-model" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              AI Model
            </label>
            <input
              id="geo-ai-model"
              style={{ ...inp, maxWidth: 280 }}
              value={aiModel}
              onChange={(e) => setAiModel(e.target.value)}
              placeholder="llama3"
            />
            <label
              htmlFor="geo-rag"
              style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginBottom: 10 }}
            >
              <input
                id="geo-rag"
                type="checkbox"
                checked={ragEnabled}
                onChange={(e) => setRagEnabled(e.target.checked)}
              />{' '}
              Enable RAG over SERP and site context
            </label>
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '8px 16px',
                borderRadius: 10,
                border: '1px solid rgba(147,197,253,0.4)',
                background: 'linear-gradient(90deg, rgba(59,130,246,0.9) 0%, rgba(14,165,233,0.86) 100%)',
                color: '#eff6ff',
                fontWeight: 700,
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? 'Analyzing GEO...' : 'Optimize for AI Engines'}
            </button>
          </form>

          <aside style={{ ...card, marginBottom: 0 }}>
            <div>
              <h3 style={{ margin: '0 0 6px', fontSize: 16, color: 'var(--text)' }}>Audit Blueprint</h3>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                Execution map for generative-engine optimization.
              </p>
            </div>
            <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
              {GEO_AUDIT_PHASES.map((phase, index) => (
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
                  {topic.trim() ? 'Topic set' : 'Topic pending'}
                </span>
                <span
                  style={{
                    border: '1px solid rgba(34,211,238,0.35)',
                    background: 'rgba(34,211,238,0.14)',
                    color: 'var(--brand)',
                    borderRadius: 999,
                    padding: '3px 8px',
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  {engines.length} engines
                </span>
              </div>
            </div>
          </aside>
        </div>
        {result && (
          <>
            <section
              style={{
                ...card,
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(min(100%, 140px), 1fr))',
                gap: 10,
              }}
            >
              <div
                style={{
                  background: 'var(--bg)',
                  borderRadius: 8,
                  padding: '10px 12px',
                  border: '1px solid var(--line)',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>GEO Score</div>
                <div style={{ fontSize: 24, fontWeight: 800, color: '#22c55e' }}>
                  {(result.geo_score as number) ?? '—'}
                  <span style={{ fontSize: 12, fontWeight: 400 }}>/100</span>
                </div>
                <div style={{ fontSize: 11, marginTop: 6, color: 'var(--muted)' }}>
                  {result.cached ? 'Cached · ' : ''}
                  {result.analysis_mode === 'llm' ? 'AI model' : 'Heuristic (content signals)'}
                </div>
              </div>
              {engineScores &&
                Object.entries(engineScores).map(([engine, score]) => (
                  <div
                    key={engine}
                    style={{
                      background: 'var(--bg)',
                      borderRadius: 8,
                      padding: '10px 12px',
                      border: '1px solid var(--line)',
                      textAlign: 'center',
                    }}
                  >
                    <div style={{ fontSize: 10, color: 'var(--muted)' }}>{engine.replaceAll('_', ' ')}</div>
                    <div style={{ fontSize: 20, fontWeight: 800 }}>
                      {score}
                      <span style={{ fontSize: 11, fontWeight: 400 }}>/100</span>
                    </div>
                    <div style={{ background: 'var(--line)', borderRadius: 4, height: 4, marginTop: 6 }}>
                      <div style={{ width: `${score}%`, height: '100%', background: '#22d3ee', borderRadius: 4 }} />
                    </div>
                  </div>
                ))}
            </section>
            <section style={card}>
              <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 14 }}>📊 GEO Dimensions</p>
              {(
                [
                  { key: 'citability_score', label: 'Citability' },
                  { key: 'factual_density_score', label: 'Factual Density' },
                  { key: 'question_coverage_score', label: 'Question Coverage' },
                  { key: 'authority_signals_score', label: 'Authority Signals' },
                  { key: 'structure_score', label: 'Structure' },
                  { key: 'entity_clarity_score', label: 'Entity Clarity' },
                ] as const
              ).map(({ key, label }) => {
                const val = result[key] as number;
                if (val === undefined) return null;

                let barColor = '#ef4444';
                if (val >= 80) {
                  barColor = '#22c55e';
                } else if (val >= 60) {
                  barColor = '#f59e0b';
                }

                return (
                  <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                    <span style={{ fontSize: 12, width: 160, color: 'var(--muted)', flexShrink: 0 }}>{label}</span>
                    <div style={{ flex: 1, background: 'var(--line)', borderRadius: 6, height: 8 }}>
                      <div
                        style={{
                          width: `${val}%`,
                          height: '100%',
                          background: barColor,
                          borderRadius: 6,
                        }}
                      />
                    </div>
                    <span style={{ fontSize: 12, fontWeight: 700, width: 36, textAlign: 'right' }}>{val}</span>
                  </div>
                );
              })}
            </section>
            {(result.recommendations as string[] | undefined)?.length ? (
              <section style={card}>
                <p style={{ fontSize: 14, fontWeight: 700, marginTop: 0, marginBottom: 12 }}>🚀 Recommendations</p>
                <ol style={{ margin: 0, paddingLeft: 20 }}>
                  {(result.recommendations as string[]).map((r) => (
                    <li key={r} style={{ fontSize: 13, marginBottom: 8, lineHeight: 1.5 }}>
                      {r}
                    </li>
                  ))}
                </ol>
              </section>
            ) : null}
            <p style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'right' }}>
              Analysis ID: {result.analysis_id as string}
            </p>
          </>
        )}
      </div>
    </main>
  );
}
