'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

const SXO_AUDIT_PHASES = [
  'Collect intent and keyword context',
  'Assess UX and engagement quality signals',
  'Prioritize experience-led ranking improvements',
];

type SxoImprovement =
  | string
  | {
      area?: string;
      action?: string;
      impact?: string;
      effort?: string;
      expected_delta_pct?: number;
    };

type SxoResult = {
  analysis_id?: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  sxo_score?: number;
  dwell_time_score?: number;
  ctr_score?: number;
  ux_quality_score?: number;
  engagement_signals?: Record<string, unknown>;
  improvements?: SxoImprovement[];
  fallback?: boolean;
};

function formatImprovement(item: SxoImprovement): string {
  if (typeof item === 'string') return item;
  const action = item.action ?? 'Improve experience signals';
  const area = item.area ? `[${item.area}] ` : '';
  const impact = item.impact ? ` (${item.impact} impact)` : '';
  return `${area}${action}${impact}`;
}

export default function SXOPage() {
  const [url, setUrl] = useState('');
  const [keywords, setKeywords] = useState('');
  const [content, setContent] = useState('');
  const [result, setResult] = useState<SxoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function run() {
    if (!url) {
      setError('URL is required.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const data = await apiSend<SxoResult>(
        '/seo-platform/sxo/analyze',
        'POST',
        {
          url,
          keywords: keywords
            .split(',')
            .map((k) => k.trim())
            .filter(Boolean),
          content,
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
      setError(e instanceof Error ? e.message : 'SXO analysis failed');
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    void run();
  }

  return (
    <main className="min-h-screen p-4 md:p-6 lg:p-8 text-[var(--text)]">
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="relative overflow-hidden rounded-2xl border border-[var(--line)] bg-white p-6 md:p-8 backdrop-blur-xl">
          <div className="pointer-events-none absolute -right-20 -top-20 h-60 w-60 rounded-full bg-[var(--brand)]/20 blur-3xl" />
          <div className="pointer-events-none absolute -left-24 -bottom-20 h-60 w-60 rounded-full bg-emerald-500/15 blur-3xl" />
          <div className="relative grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
            <div>
              <div className="mb-4 flex flex-wrap gap-2">
                <span className="rounded-full border border-[var(--line)] bg-[var(--brand)]/15 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-cyan-100">
                  SXO Engine
                </span>
                <span className="rounded-full border border-[var(--line)] bg-white/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
                  SEO + UX Signal Fusion
                </span>
              </div>
              <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-[var(--text)]">
                SXO - Search Experience Optimization
              </h1>
              <p className="mt-3 max-w-3xl text-sm md:text-base text-[var(--muted)] leading-relaxed">
                Align rankings with real experience outcomes. Optimize dwell time, CTR quality, and behavioral
                engagement to reduce pogo-sticking and increase conversion readiness.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-2 sm:min-w-[260px]">
              <div className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Primary URL</div>
                <div className="mt-1 truncate text-sm font-semibold text-cyan-100">{url || 'Not set'}</div>
              </div>
              <div className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Keyword Scope</div>
                <div className="mt-1 text-sm font-semibold text-emerald-100">
                  {keywords
                    .split(',')
                    .map((k) => k.trim())
                    .filter(Boolean).length || 0}{' '}
                  tracked
                </div>
              </div>
              <div className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Method</div>
                <div className="mt-1 text-sm font-semibold text-[var(--text)]">Behavior + Intent</div>
              </div>
              <div className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3 py-2">
                <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Output</div>
                <div className="mt-1 text-sm font-semibold text-[var(--text)]">Improvement Roadmap</div>
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
                <h2 className="text-base font-semibold text-[var(--text)]">Analysis Inputs</h2>
                <p className="mt-0.5 text-xs text-[var(--muted)]">Define intent, URL target, and content context</p>
              </div>
              <div className="rounded-lg border border-[var(--line)] bg-[var(--brand)]/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-cyan-200">
                Advanced Mode
              </div>
            </div>

            <div>
              <label
                htmlFor="sxo-url"
                className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]"
              >
                Page URL
              </label>
              <input
                id="sxo-url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://your-site.com/page"
                className="w-full rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--faint)] outline-none transition-all focus:border-[var(--line)] focus:ring-2 focus:ring-[var(--brand)]/30"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label
                  htmlFor="sxo-keywords"
                  className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]"
                >
                  Target Keywords
                </label>
                <input
                  id="sxo-keywords"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="keyword1, keyword2"
                  className="w-full rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--faint)] outline-none transition-all focus:border-[var(--line)] focus:ring-2 focus:ring-[var(--brand)]/30"
                />
              </div>

              <div>
                <label
                  htmlFor="sxo-content"
                  className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]"
                >
                  Page Content (optional)
                </label>
                <textarea
                  id="sxo-content"
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Paste content for deeper analysis..."
                  className="min-h-[120px] w-full rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--faint)] outline-none transition-all focus:border-[var(--line)] focus:ring-2 focus:ring-[var(--brand)]/30"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex w-full items-center justify-center rounded-xl border border-[var(--line)] bg-gradient-to-r from-cyan-500/80 to-teal-500/80 px-4 py-3 text-sm font-semibold text-[var(--text)] transition-all hover:from-cyan-400 hover:to-teal-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? 'Analyzing SXO...' : 'Analyze Search Experience'}
            </button>
          </form>

          <aside className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl space-y-4">
            <div>
              <h3 className="text-base font-semibold text-[var(--text)]">Audit Blueprint</h3>
              <p className="mt-1 text-xs text-[var(--muted)]">Execution stages for SXO diagnostics and optimization.</p>
            </div>

            <div className="space-y-2.5">
              {SXO_AUDIT_PHASES.map((phase, index) => (
                <div
                  key={phase}
                  className="flex items-start gap-3 rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3 py-2.5"
                >
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-[var(--line)] bg-[var(--brand)]/15 text-[11px] font-semibold text-cyan-200">
                    {index + 1}
                  </div>
                  <p className="text-xs leading-relaxed text-[var(--muted)]">{phase}</p>
                </div>
              ))}
            </div>

            <div className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-3.5 py-3">
              <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--muted)]">Current Scope</div>
              <div className="mt-2 flex flex-wrap gap-2">
                <span className="rounded-full border border-[var(--line)] bg-[var(--brand)]/12 px-2.5 py-1 text-[11px] font-medium text-cyan-100">
                  {keywords
                    .split(',')
                    .map((k) => k.trim())
                    .filter(Boolean).length || 0}{' '}
                  keywords
                </span>
                <span className="rounded-full border border-emerald-300/30 bg-emerald-500/12 px-2.5 py-1 text-[11px] font-medium text-emerald-100">
                  {content ? 'Content included' : 'URL-first analysis'}
                </span>
              </div>
            </div>
          </aside>
        </div>

        {result && (
          <>
            <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
              {[
                { label: 'SXO Score', value: result.sxo_score, color: '#22c55e' },
                { label: 'Dwell Time', value: result.dwell_time_score, color: '#22d3ee' },
                { label: 'CTR Score', value: result.ctr_score, color: '#2563eb' },
                { label: 'UX Quality', value: result.ux_quality_score, color: '#f59e0b' },
              ].map((m) => (
                <div key={m.label} className="rounded-xl border border-[var(--line)] bg-white p-4 text-center">
                  <div className="text-[10px] uppercase tracking-[0.1em] text-[var(--muted)]">{m.label}</div>
                  <div className="mt-1 text-3xl font-extrabold" style={{ color: m.color }}>
                    {m.value ?? '—'}
                  </div>
                  {m.label === 'SXO Score' && (
                    <div className="mt-2 text-[11px] text-[var(--muted)]">
                      {result.cached ? 'Cached · ' : ''}
                      {result.analysis_mode === 'llm'
                        ? 'AI model'
                        : 'Heuristic (URL + content signals)'}
                    </div>
                  )}
                  <div className="mt-2 h-1 rounded bg-white/10">
                    <div
                      style={{
                        width: `${m.value ?? 0}%`,
                        height: '100%',
                        background: m.color,
                        borderRadius: 999,
                      }}
                    />
                  </div>
                </div>
              ))}
            </section>
            {(result.engagement_signals as Record<string, unknown> | undefined) && (
              <section className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl">
                <p className="mb-3 text-base font-semibold text-[var(--text)]">Engagement Signals</p>
                <div className="flex flex-wrap gap-3">
                  {Object.entries(result.engagement_signals as Record<string, unknown>).map(([k, v]) => (
                    <div key={`item-${k}`} className="rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-4 py-3">
                      <div className="text-xs capitalize text-[var(--muted)]">{k.replaceAll('_', ' ')}</div>
                      <div className="text-base font-semibold text-[var(--text)]">{String(v)}</div>
                    </div>
                  ))}
                </div>
              </section>
            )}
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
            <p className="text-right text-xs text-[var(--muted)]">Analysis ID: {result.analysis_id as string}</p>
          </>
        )}
      </div>
    </main>
  );
}
