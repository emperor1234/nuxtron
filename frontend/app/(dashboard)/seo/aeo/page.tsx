'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type AeoSnippetOpportunity = {
  question?: string;
  answer?: string;
  format?: string;
  snippet_probability?: number;
};

type AeoFaqItem = {
  question?: string;
  answer?: string;
};

type AeoResult = {
  aeo_score?: number;
  voice_readiness_score?: number;
  snippet_opportunities?: AeoSnippetOpportunity[];
  faq_section?: AeoFaqItem[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
  [key: string]: unknown;
};

const AEO_AUDIT_PHASES = [
  'Define topic, entities, and question set',
  'Assess snippet probability and voice readiness',
  'Generate structured answer and schema improvements',
];

export default function AEOPage() {
  const [topic, setTopic] = useState('');
  const [content, setContent] = useState('');
  const [questions, setQuestions] = useState('');
  const [entityTargets, setEntityTargets] = useState('Brand\nProduct\nCategory');
  const [schemaTypes, setSchemaTypes] = useState('FAQPage\nHowTo\nQAPage');
  const [useOpenLens, setUseOpenLens] = useState(true);
  const [usePlaywrightValidation, setUsePlaywrightValidation] = useState(true);
  const [result, setResult] = useState<AeoResult | null>(null);
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
      const data = await apiSend<AeoResult>(
        '/seo-platform/aeo/optimize',
        'POST',
        {
          topic,
          content,
          target_questions: questions
            .split('\n')
            .map((q) => q.trim())
            .filter(Boolean),
          entity_targets: entityTargets
            .split('\n')
            .map((v) => v.trim())
            .filter(Boolean),
          schema_types: schemaTypes
            .split('\n')
            .map((v) => v.trim())
            .filter(Boolean),
          use_openlens: useOpenLens,
          use_playwright_validation: usePlaywrightValidation,
          retrieval_framework: 'llamaindex',
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
      setError(e instanceof Error ? e.message : 'AEO analysis failed');
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    void run();
  }

  const card = {
    background: 'var(--card)',
    border: '1px solid var(--line)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    boxShadow: 'var(--shadow-sm)',
  };
  const inp = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: 12,
    border: '1px solid var(--line)',
    background: '#ffffff',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };
  const snippets = result?.snippet_opportunities;
  const faqs = result?.faq_section;

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
                    color: '#0e7490',
                    border: '1px solid rgba(125,211,252,0.45)',
                    borderRadius: 999,
                    padding: '3px 10px',
                    background: 'rgba(34,211,238,0.14)',
                  }}
                >
                  AEO Engine
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
                  Snippet + Voice Optimization
                </span>
              </div>
              <h1 style={{ margin: '0 0 4px', fontSize: 30, fontWeight: 800, color: 'var(--text)' }}>AEO</h1>
              <p style={{ color: 'var(--muted)', margin: 0 }}>
                Win featured snippets, PAA boxes, and voice answers with direct-answer formatting and entity-first
                context.
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
                  Topic
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: '#0e7490' }}>
                  {topic.trim() ? 'Defined' : 'Pending'}
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
                  Questions
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>
                  {questions
                    .split('\n')
                    .map((q) => q.trim())
                    .filter(Boolean).length || 0}
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
                  OpenLens
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: '#0e7490' }}>
                  {useOpenLens ? 'Enabled' : 'Disabled'}
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
                  Output
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>Snippet Plan</div>
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
                  Configure entities, schema, and answer-engine context
                </p>
              </div>
            </div>

            <label htmlFor="aeo-topic" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Topic
            </label>
            <input
              id="aeo-topic"
              style={inp}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. How to do keyword research"
            />
            <label htmlFor="aeo-questions" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Target Questions (one per line, optional)
            </label>
            <textarea
              id="aeo-questions"
              style={{ ...inp, minHeight: 80 }}
              value={questions}
              onChange={(e) => setQuestions(e.target.value)}
              placeholder="What is keyword research?&#10;How long does SEO take?&#10;What is a good keyword difficulty?"
            />
            <label htmlFor="aeo-entities" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Entity Targets (one per line)
            </label>
            <textarea
              id="aeo-entities"
              style={{ ...inp, minHeight: 80 }}
              value={entityTargets}
              onChange={(e) => setEntityTargets(e.target.value)}
              placeholder="Brand&#10;Product&#10;Use case"
            />
            <label htmlFor="aeo-schema" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              JSON-LD Schema Types (one per line)
            </label>
            <textarea
              id="aeo-schema"
              style={{ ...inp, minHeight: 70 }}
              value={schemaTypes}
              onChange={(e) => setSchemaTypes(e.target.value)}
              placeholder="FAQPage&#10;HowTo&#10;QAPage"
            />
            <label
              htmlFor="aeo-openlens"
              style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginBottom: 8 }}
            >
              <input
                id="aeo-openlens"
                type="checkbox"
                checked={useOpenLens}
                onChange={(e) => setUseOpenLens(e.target.checked)}
              />{' '}
              Use OpenLens checks
            </label>
            <label
              htmlFor="aeo-playwright"
              style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginBottom: 10 }}
            >
              <input
                id="aeo-playwright"
                type="checkbox"
                checked={usePlaywrightValidation}
                onChange={(e) => setUsePlaywrightValidation(e.target.checked)}
              />{' '}
              Use Playwright validation
            </label>
            <label htmlFor="aeo-content" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Content
            </label>
            <textarea
              id="aeo-content"
              style={{ ...inp, minHeight: 180 }}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste your content here to analyze and optimize for answer engines..."
            />
            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '8px 16px',
                borderRadius: 10,
                border: '1px solid rgba(125,211,252,0.35)',
                background: 'linear-gradient(90deg, rgba(6,182,212,0.9) 0%, rgba(20,184,166,0.88) 100%)',
                color: '#ecfeff',
                fontWeight: 700,
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? 'Optimizing for AEO...' : 'Optimize for Answer Engines'}
            </button>
          </form>

          <aside style={{ ...card, marginBottom: 0 }}>
            <div>
              <h3 style={{ margin: '0 0 6px', fontSize: 16, color: 'var(--text)' }}>Audit Blueprint</h3>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                Execution flow for answer-engine optimization.
              </p>
            </div>
            <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
              {AEO_AUDIT_PHASES.map((phase, index) => (
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
                      border: '1px solid rgba(125,211,252,0.4)',
                      background: 'rgba(34,211,238,0.16)',
                      color: '#0e7490',
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
                    border: '1px solid rgba(125,211,252,0.35)',
                    background: 'rgba(34,211,238,0.14)',
                    color: '#0e7490',
                    borderRadius: 999,
                    padding: '3px 8px',
                    fontSize: 11,
                    fontWeight: 600,
                  }}
                >
                  {entityTargets
                    .split('\n')
                    .map((item) => item.trim())
                    .filter(Boolean).length || 0}{' '}
                  entities
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
                  {schemaTypes
                    .split('\n')
                    .map((item) => item.trim())
                    .filter(Boolean).length || 0}{' '}
                  schema types
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
                  <span style={{ fontSize: 11, fontWeight: 700, padding: '4px 10px', borderRadius: 999, background: 'rgba(56,189,248,0.15)', color: '#38bdf8' }}>
                    Cached result
                  </span>
                )}
              </div>
            )}
            <section
              style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 180px), 1fr))', gap: 10 }}
            >
              {[
                { label: 'AEO Score', value: `${typeof result.aeo_score === 'number' ? result.aeo_score : '—'}/100` },
                {
                  label: 'Voice Readiness',
                  value: `${typeof result.voice_readiness_score === 'number' ? result.voice_readiness_score : '—'}/100`,
                },
                { label: 'Snippet Opportunities', value: snippets?.length ?? 0 },
              ].map((m) => (
                <div
                  key={m.label}
                  style={{
                    background: 'var(--bg)',
                    borderRadius: 8,
                    padding: '10px 12px',
                    border: '1px solid var(--line)',
                  }}
                >
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{m.label}</div>
                  <div style={{ fontSize: 22, fontWeight: 800 }}>{m.value}</div>
                </div>
              ))}
            </section>
            {snippets && snippets.length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Featured Snippet Opportunities</h3>
                {snippets.map((s) => (
                  <div
                    key={`${s.question ?? 'snippet'}-${s.format ?? 'format'}`}
                    style={{
                      marginBottom: 12,
                      padding: 12,
                      background: 'var(--bg)',
                      borderRadius: 8,
                      border: '1px solid var(--line)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <strong style={{ fontSize: 13 }}>{s.question}</strong>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <span
                          style={{
                            fontSize: 10,
                            background: 'rgba(27,199,255,0.15)',
                            color: 'var(--brand)',
                            borderRadius: 4,
                            padding: '1px 6px',
                          }}
                        >
                          {s.format}
                        </span>
                        <span style={{ fontSize: 10, color: 'var(--muted)' }}>
                          {Math.round((s.snippet_probability ?? 0) * 100)}% prob.
                        </span>
                      </div>
                    </div>
                    <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)', lineHeight: 1.5 }}>{s.answer}</p>
                  </div>
                ))}
              </section>
            )}
            {faqs && faqs.length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Generated FAQ Section</h3>
                {faqs.map((f) => (
                  <div key={`${f.question ?? 'faq'}-${f.answer ?? 'answer'}`} style={{ marginBottom: 10 }}>
                    <strong style={{ fontSize: 13 }}>{f.question}</strong>
                    <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>{f.answer}</p>
                  </div>
                ))}
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
