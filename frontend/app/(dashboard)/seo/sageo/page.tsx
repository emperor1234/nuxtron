'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

const SAGEO_AUDIT_PHASES = [
  'Define topic intent and synthesis targets',
  'Prioritize authoritative source types and entry points',
  'Produce actionable next-step generative SEO plan',
];

type SageoSourcePriority = {
  source_type?: string;
  reason?: string;
  priority?: string;
};

type SageoEntryPoint =
  | string
  | {
      surface?: string;
      content_type?: string;
      probability?: number;
    };

type SageoBlueprintItem =
  | string
  | {
      section?: string;
      word_count?: number;
      format?: string;
      guidance?: string;
    };

type SageoResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  sageo_score?: number;
  intent_map?: {
    primary_intent?: string;
    supporting_intents?: string[];
  };
  source_priorities?: SageoSourcePriority[];
  generative_entry_points?: SageoEntryPoint[];
  answer_blueprint?: SageoBlueprintItem[];
  next_actions?: Array<string | { action?: string; priority?: string; expected_impact?: string }>;
  fallback?: boolean;
};

function formatEntryPoint(item: SageoEntryPoint): string {
  if (typeof item === 'string') return item;
  const surface = item.surface ?? 'Engine';
  const contentType = item.content_type ?? 'content';
  const probability =
    typeof item.probability === 'number' ? ` · ${Math.round(item.probability * 100)}%` : '';
  return `${surface}: ${contentType}${probability}`;
}

function formatBlueprintItem(item: SageoBlueprintItem): string {
  if (typeof item === 'string') return item;
  const section = item.section ?? 'section';
  const format = item.format ? ` (${item.format})` : '';
  const words = typeof item.word_count === 'number' ? ` · ${item.word_count} words` : '';
  const guidance = item.guidance ? ` — ${item.guidance}` : '';
  return `${section}${format}${words}${guidance}`;
}

export default function SageoPage() {
  const [topic, setTopic] = useState('');
  const [searchIntent, setSearchIntent] = useState('informational');
  const [sourceMaterial, setSourceMaterial] = useState('');
  const [targetEngines, setTargetEngines] = useState('Google AI Overview, ChatGPT, Perplexity');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<SageoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!topic.trim()) {
      setError('Topic is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<SageoResult>(
        '/seo-platform/sageo/analyze',
        'POST',
        {
          topic: topic.trim(),
          search_intent: searchIntent.trim(),
          source_material: sourceMaterial.trim(),
          target_engines: targetEngines
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
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
      setError(e instanceof Error ? e.message : 'SAGEO analysis failed');
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
    boxShadow: '0 20px 60px -45px rgba(56, 189, 248, 0.65)',
  };
  const input = {
    width: '100%',
    padding: '10px 12px',
    borderRadius: 12,
    border: '1px solid rgba(148, 163, 184, 0.22)',
    background: '#ffffff',
    color: 'var(--text)',
    marginBottom: 10,
    boxSizing: 'border-box' as const,
  };

  return (
    <main style={{ minHeight: '100vh', color: 'var(--text)', padding: 24 }}>
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <section
          style={{
            position: 'relative',
            overflow: 'hidden',
            borderRadius: 16,
            border: '1px solid rgba(56,189,248,0.28)',
            background:
              'var(--card)',
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
                    border: '1px solid rgba(125,211,252,0.45)',
                    borderRadius: 999,
                    padding: '3px 10px',
                    background: 'rgba(34,211,238,0.14)',
                  }}
                >
                  SAGEO Planner
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
                  Search-Augmented Synthesis
                </span>
              </div>
              <h1 style={{ marginTop: 0, marginBottom: 4, fontSize: 30, fontWeight: 800, color: 'var(--text)' }}>SAGEO</h1>
              <p style={{ color: 'var(--muted)', margin: 0 }}>Search-augmented generative SEO planning and synthesis.</p>
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
                  Intent
                </div>
                <div
                  style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--brand)', textTransform: 'capitalize' }}
                >
                  {searchIntent || 'informational'}
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
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>
                  {targetEngines
                    .split(',')
                    .map((item) => item.trim())
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
                  Topic
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>
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
                  Output
                </div>
                <div style={{ marginTop: 2, fontSize: 13, fontWeight: 700, color: 'var(--text)' }}>Action Plan</div>
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
                <h2 style={{ margin: 0, fontSize: 16, color: 'var(--text)' }}>Synthesis Inputs</h2>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--muted)' }}>
                  Configure search-intent and source strategy inputs
                </p>
              </div>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.1em',
                  color: 'var(--brand)',
                  border: '1px solid rgba(125,211,252,0.35)',
                  borderRadius: 8,
                  padding: '4px 8px',
                  background: 'rgba(34,211,238,0.12)',
                }}
              >
                Advanced Mode
              </div>
            </div>

            <label htmlFor="sageo-topic" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Topic
            </label>
            <input
              id="sageo-topic"
              style={input}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="best crm for startups"
            />

            <label htmlFor="sageo-intent" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Search Intent
            </label>
            <input
              id="sageo-intent"
              style={input}
              value={searchIntent}
              onChange={(e) => setSearchIntent(e.target.value)}
              placeholder="informational"
            />

            <label htmlFor="sageo-source" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Source Material
            </label>
            <textarea
              id="sageo-source"
              style={{ ...input, minHeight: 110 }}
              value={sourceMaterial}
              onChange={(e) => setSourceMaterial(e.target.value)}
              placeholder="Current article outline, SME notes, citations, product facts"
            />

            <label htmlFor="sageo-engines" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Target Engines
            </label>
            <input
              id="sageo-engines"
              style={input}
              value={targetEngines}
              onChange={(e) => setTargetEngines(e.target.value)}
              placeholder="Google AI Overview, ChatGPT, Perplexity"
            />

            <label htmlFor="sageo-notes" style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>
              Notes
            </label>
            <textarea
              id="sageo-notes"
              style={{ ...input, minHeight: 80 }}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Priority angles, authority constraints, proof requirements"
            />

            <button
              type="submit"
              disabled={loading}
              style={{
                padding: '8px 16px',
                borderRadius: 10,
                border: '1px solid rgba(125,211,252,0.4)',
                background: 'linear-gradient(90deg, rgba(6,182,212,0.9) 0%, rgba(14,165,233,0.86) 100%)',
                color: '#ecfeff',
                fontWeight: 700,
                cursor: 'pointer',
                opacity: loading ? 0.7 : 1,
              }}
            >
              {loading ? 'Synthesizing search-augmented plan...' : 'Analyze SAGEO'}
            </button>
          </form>

          <aside style={{ ...card, marginBottom: 0 }}>
            <div>
              <h3 style={{ margin: '0 0 6px', fontSize: 16, color: 'var(--text)' }}>Audit Blueprint</h3>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--muted)' }}>
                Execution stages for search-augmented planning.
              </p>
            </div>
            <div style={{ marginTop: 12, display: 'grid', gap: 8 }}>
              {SAGEO_AUDIT_PHASES.map((phase, index) => (
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
                    border: '1px solid rgba(125,211,252,0.35)',
                    background: 'rgba(34,211,238,0.14)',
                    color: 'var(--brand)',
                    borderRadius: 999,
                    padding: '3px 8px',
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: 'capitalize',
                  }}
                >
                  {searchIntent || 'informational'}
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
                  {targetEngines
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean).length || 0}{' '}
                  engines
                </span>
              </div>
            </div>
          </aside>
        </div>

        {result && (
          <>
            <section
              style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 240px), 1fr))', gap: 10 }}
            >
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>SAGEO Score</div>
                <div style={{ fontSize: 28, fontWeight: 800 }}>{result.sageo_score ?? '--'}</div>
                <div style={{ fontSize: 11, marginTop: 6, color: 'var(--muted)' }}>
                  {result.cached ? 'Cached · ' : ''}
                  {result.analysis_mode === 'llm'
                    ? 'AI model'
                    : 'Heuristic (topic + source signals)'}
                </div>
              </div>
              <div
                style={{
                  background: 'var(--bg)',
                  border: '1px solid var(--line)',
                  borderRadius: 8,
                  padding: '10px 12px',
                }}
              >
                <div style={{ fontSize: 10, color: 'var(--muted)' }}>Intent Map</div>
                <div style={{ fontSize: 12, marginTop: 4 }}>
                  <strong>Primary:</strong> {result.intent_map?.primary_intent ?? '--'}
                </div>
                <div style={{ fontSize: 12, marginTop: 4 }}>
                  <strong>Supporting:</strong> {(result.intent_map?.supporting_intents ?? []).join(', ') || '--'}
                </div>
              </div>
            </section>

            {(result.source_priorities ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Source Priorities</h3>
                {(result.source_priorities ?? []).map((item, index) => (
                  <div
                    key={`${item.source_type ?? 'source'}-${item.priority ?? 'priority'}-${item.reason ?? 'reason'}`}
                    style={{
                      padding: '8px 0',
                      borderBottom:
                        index < (result.source_priorities ?? []).length - 1 ? '1px solid var(--line)' : 'none',
                    }}
                  >
                    <div style={{ fontSize: 12, fontWeight: 700 }}>
                      {item.source_type ?? '--'} · {item.priority ?? 'medium'}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--muted)' }}>{item.reason ?? ''}</div>
                  </div>
                ))}
              </section>
            )}

            {(result.generative_entry_points ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Generative Entry Points</h3>
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.generative_entry_points ?? []).map((item, index) => (
                    <li key={`entry-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {formatEntryPoint(item)}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {(result.answer_blueprint ?? []).length > 0 && (
              <section style={card}>
                <h3 style={{ marginTop: 0, fontSize: 14 }}>Answer Blueprint</h3>
                <ol style={{ margin: 0, paddingLeft: 18 }}>
                  {(result.answer_blueprint ?? []).map((item, index) => (
                    <li key={`blueprint-${index}`} style={{ marginBottom: 6, fontSize: 12, color: 'var(--muted)' }}>
                      {formatBlueprintItem(item)}
                    </li>
                  ))}
                </ol>
              </section>
            )}
          </>
        )}
      </div>
    </main>
  );
}
