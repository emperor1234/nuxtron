'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

const GXO_AUDIT_PHASES = [
  'Capture topic and content positioning',
  'Evaluate citation and schema readiness',
  'Generate high-priority AI overview improvements',
];

type GxoSchemaRecommendation =
  | string
  | {
      type?: string;
      missing_fields?: string[];
      implementation_effort?: string;
    };

type GxoImprovement =
  | string
  | {
      priority?: string;
      action?: string;
      expected_citation_lift_pct?: number;
      effort?: string;
    };

type GxoResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  gxo_score?: number;
  ai_overview_citation_probability?: number;
  structured_data_score?: number;
  schema_recommendations?: GxoSchemaRecommendation[];
  improvements?: GxoImprovement[];
  fallback?: boolean;
};

function formatSchemaRecommendation(item: GxoSchemaRecommendation): string {
  if (typeof item === 'string') return item;
  const effort = item.implementation_effort ? ` · ${item.implementation_effort} effort` : '';
  return `${item.type ?? 'Schema'}${effort}`;
}

function formatImprovement(item: GxoImprovement): string {
  if (typeof item === 'string') return item;
  const priority = item.priority ? `[${item.priority}] ` : '';
  return `${priority}${item.action ?? 'Improve AI Overview readiness'}`;
}

export default function GXOPage() {
  const [topic, setTopic] = useState('');
  const [url, setUrl] = useState('');
  const [content, setContent] = useState('');
  const [result, setResult] = useState<GxoResult | null>(null);
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
      const data = await apiSend<GxoResult>(
        '/seo-platform/gxo/optimize',
        'POST',
        { topic, url, content },
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
      setError(e instanceof Error ? e.message : 'GXO optimization failed');
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    void run();
  }

  const gxoScoreValue = typeof result?.gxo_score === 'number' ? `${result.gxo_score}/100` : '—/100';
  const structuredDataValue =
    typeof result?.structured_data_score === 'number' ? `${result.structured_data_score}/100` : '—/100';
  const citationProbability =
    typeof result?.ai_overview_citation_probability === 'number'
      ? `${Math.round(result.ai_overview_citation_probability * 100)}%`
      : '0%';

  return (
    <main className="min-h-screen p-4 md:p-6 lg:p-8 text-[var(--text)]">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="relative overflow-hidden rounded-2xl border border-[var(--line)] bg-white p-6 md:p-8 backdrop-blur-xl">
          <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-[var(--brand)]/20 blur-3xl" />
          <div className="pointer-events-none absolute -left-28 -bottom-24 h-64 w-64 rounded-full bg-[var(--brand)]/15 blur-3xl" />
          <div className="relative grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
            <div>
              <div className="mb-4 flex flex-wrap gap-2">
                <span className="rounded-full border border-[var(--line)] bg-[var(--brand)]/15 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-indigo-100">
                  GXO Optimizer
                </span>
                <span className="rounded-full border border-[var(--line)] bg-white/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
                  Google AI Overviews
                </span>
              </div>
              <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-[var(--text)]">GXO</h1>
              <p className="mt-3 max-w-3xl text-sm md:text-base text-[var(--muted)] leading-relaxed">
                Optimize structure and narrative for citation probability in Google AI Overviews and next-generation
                generative search responses.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:min-w-[260px]">
              <div className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Topic</div>
                <div className="mt-1 truncate text-sm font-semibold text-indigo-100">{topic || 'Not set'}</div>
              </div>
              <div className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Source URL</div>
                <div className="mt-1 truncate text-sm font-semibold text-cyan-100">{url || 'Optional'}</div>
              </div>
              <div className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Method</div>
                <div className="mt-1 text-sm font-semibold text-[var(--text)]">Entity + Schema Focus</div>
              </div>
              <div className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Output</div>
                <div className="mt-1 text-sm font-semibold text-[var(--text)]">Citation Plan</div>
              </div>
            </div>
          </div>
        </section>

        {error && (
          <div className="rounded-xl border border-rose-400/35 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        <div className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
          <form
            onSubmit={handleSubmit}
            className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl space-y-4"
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-[var(--text)]">Optimization Inputs</h2>
                <p className="mt-0.5 text-xs text-[var(--muted)]">Frame context for AI overview citation improvement</p>
              </div>
              <div className="rounded-lg border border-[var(--line)] bg-[var(--brand)]/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-indigo-200">
                Advanced Mode
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="gxo-topic"
                  className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]"
                >
                  Topic
                </label>
                <input
                  id="gxo-topic"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. how to choose a CRM"
                  className="w-full rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--faint)] outline-none transition-all focus:border-[var(--line)] focus:ring-2 focus:ring-[var(--brand)]/30"
                />
              </div>
              <div>
                <label
                  htmlFor="gxo-url"
                  className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]"
                >
                  Page URL (optional)
                </label>
                <input
                  id="gxo-url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://your-site.com/page"
                  className="w-full rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--faint)] outline-none transition-all focus:border-[var(--line)] focus:ring-2 focus:ring-[var(--brand)]/30"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="gxo-content"
                className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]"
              >
                Content
              </label>
              <textarea
                id="gxo-content"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Paste content to optimize for Google AI Overviews..."
                className="min-h-[220px] w-full rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--faint)] outline-none transition-all focus:border-[var(--line)] focus:ring-2 focus:ring-[var(--brand)]/30"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex w-full items-center justify-center rounded-xl border border-[var(--line)] bg-gradient-to-r from-indigo-500/80 to-cyan-500/80 px-4 py-3 text-sm font-semibold text-[var(--text)] transition-all hover:from-indigo-400 hover:to-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? 'Optimizing for GXO...' : 'Optimize for Google AI Overviews'}
            </button>
          </form>

          <aside className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl space-y-4">
            <div>
              <h3 className="text-base font-semibold text-[var(--text)]">Audit Blueprint</h3>
              <p className="mt-1 text-xs text-[var(--muted)]">Structured workflow for generative-search optimization.</p>
            </div>

            <div className="space-y-2.5">
              {GXO_AUDIT_PHASES.map((phase, index) => (
                <div
                  key={phase}
                  className="flex items-start gap-3 rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3 py-2.5"
                >
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[var(--line)] bg-[var(--brand)]/15 text-[11px] font-semibold text-indigo-200">
                    {index + 1}
                  </div>
                  <p className="text-xs leading-relaxed text-[var(--muted)]">{phase}</p>
                </div>
              ))}
            </div>

            <div className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3.5 py-3">
              <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Current Scope</div>
              <div className="mt-2 flex flex-wrap gap-2">
                <span className="rounded-full border border-[var(--line)] bg-[var(--brand)]/12 px-2.5 py-1 text-[11px] font-medium text-indigo-100">
                  {topic ? 'Topic defined' : 'Topic pending'}
                </span>
                <span className="rounded-full border border-[var(--line)] bg-[var(--brand)]/12 px-2.5 py-1 text-[11px] font-medium text-cyan-100">
                  {content.length > 0 ? `${content.length} chars` : 'Content pending'}
                </span>
              </div>
            </div>
          </aside>
        </div>

        {result && (
          <>
            <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {[
                { label: 'GXO Score', value: gxoScoreValue },
                { label: 'AI Overview Citation Prob.', value: citationProbability },
                { label: 'Structured Data Score', value: structuredDataValue },
              ].map((m) => (
                <div key={m.label} className="rounded-xl border border-[var(--line)] bg-white px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.08em] text-[var(--muted)]">{m.label}</div>
                  <div className="mt-1 text-2xl font-extrabold text-indigo-100">{m.value}</div>
                  {m.label === 'GXO Score' && (
                    <div className="mt-2 text-[11px] text-[var(--muted)]">
                      {result.cached ? 'Cached · ' : ''}
                      {result.analysis_mode === 'llm'
                        ? 'AI model'
                        : 'Heuristic (topic + content signals)'}
                    </div>
                  )}
                </div>
              ))}
            </section>
            {(result.schema_recommendations ?? []).length > 0 ? (
              <section className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl">
                <p className="mb-3 text-base font-semibold text-[var(--text)]">Schema Recommendations</p>
                <div className="flex flex-wrap gap-2">
                  {(result.schema_recommendations ?? []).map((s, index) => (
                    <span
                      key={`schema-${index}`}
                      className="rounded-full border border-[var(--line)] bg-[var(--brand)]/10 px-3 py-1.5 text-xs font-semibold text-cyan-100"
                    >
                      {formatSchemaRecommendation(s)}
                    </span>
                  ))}
                </div>
              </section>
            ) : null}
            {(result.improvements ?? []).length > 0 ? (
              <section className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl">
                <p className="mb-3 text-base font-semibold text-[var(--text)]">Priority Improvements</p>
                <ol className="list-decimal space-y-2 pl-5">
                  {(result.improvements ?? []).map((imp, index) => (
                    <li key={`imp-${index}`} className="text-sm leading-relaxed text-[var(--text)]">
                      {formatImprovement(imp)}
                    </li>
                  ))}
                </ol>
              </section>
            ) : null}
            <p className="text-right text-xs text-[var(--muted)]">
              Analysis ID: {result.analysis_id ?? '—'}
            </p>
          </>
        )}
      </div>
    </main>
  );
}
