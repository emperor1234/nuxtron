'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

const PAGE_TYPES = ['landing', 'blog', 'product', 'category', 'homepage', 'contact', 'pricing'];
const TRAFFIC_SOURCES = ['organic', 'paid', 'social', 'email', 'direct'];

interface FrictionPoint {
  location: string;
  type: string;
  impact: 'high' | 'medium' | 'low';
  fix: string;
}

interface AbTest {
  element: string;
  variant_a: string;
  variant_b: string;
  hypothesis: string;
}

interface UxResult {
  analysis_id: string;
  ux_score: number;
  conversion_score: number;
  above_fold: { cta_visible: boolean; load_time_estimate: number; hero_clarity_score: number };
  friction_points: FrictionPoint[];
  trust_signals: { present: string[]; missing: string[] };
  heatmap_insights: string[];
  ab_test_ideas: AbTest[];
  quick_wins: string[];
  recommended_tools: string[];
  url: string;
  page_type: string;
  audited_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
}

const IMPACT_COLORS: Record<string, string> = {
  high: 'bg-red-500/10 text-red-200 border-red-400/40',
  medium: 'bg-amber-500/10 text-amber-200 border-amber-400/40',
  low: 'bg-emerald-500/10 text-emerald-200 border-emerald-400/40',
};

const UX_AUDIT_PHASES = [
  'Capture page context and intent',
  'Evaluate UX friction and trust layers',
  'Generate experiments and quick wins',
];

export default function UxConversionPage() {
  const [url, setUrl] = useState('');
  const [pageType, setPageType] = useState('landing');
  const [trafficSource, setTrafficSource] = useState('organic');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<UxResult | null>(null);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await apiSend<UxResult>(
        '/seo-platform/ux/audit',
        'POST',
        { url, page_type: pageType, traffic_source: trafficSource, notes },
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
      setError(e instanceof Error ? e.message : 'Audit failed');
    } finally {
      setLoading(false);
    }
  }

  const uxScore = result?.ux_score ?? 0;
  const cvScore = result?.conversion_score ?? 0;
  const scoreColor = (s: number) => {
    if (s >= 80) return 'text-emerald-300';
    if (s >= 60) return 'text-amber-300';
    return 'text-rose-300';
  };

  return (
    <div className="mx-auto w-full max-w-7xl p-4 md:p-6 lg:p-8 space-y-6 text-[var(--text)]">
      <div>
        <h1 className="text-[27px] font-semibold tracking-tight text-[var(--nx-ink,var(--text))]">
          UX & Conversion Optimizer
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-[var(--nx-muted,var(--muted))] leading-relaxed">
          Diagnose friction, evaluate conversion quality, and generate experiment-ready improvements for SEO traffic
          journeys.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.35fr_0.65fr]">
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl shadow-[0_18px_55px_-30px_rgba(6,182,212,0.65)] space-y-5"
        >
          <div>
            <h2 className="text-base font-semibold text-[var(--text)]">Audit Inputs</h2>
            <p className="mt-0.5 text-xs text-[var(--muted)]">Provide context for conversion-quality analysis</p>
          </div>

          <div>
            <label
              htmlFor="ux-url"
              className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]"
            >
              Page URL *
            </label>
            <input
              id="ux-url"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              placeholder="https://example.com/pricing"
              className="w-full rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--faint)] outline-none transition-all focus:border-[var(--line)] focus:ring-2 focus:ring-[var(--brand)]/30"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <p className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">Page Type</p>
              <div className="flex flex-wrap gap-2">
                {PAGE_TYPES.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setPageType(t)}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold capitalize transition-all ${
                      pageType === t
                        ? 'border-[var(--line)] bg-[var(--brand)]/20 text-cyan-100 shadow-[0_0_0_1px_rgba(125,211,252,0.35)]'
                        : 'border-[var(--line)] bg-white/5 text-[var(--muted)] hover:border-[var(--line)] hover:text-cyan-100'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]">
                Traffic Source
              </p>
              <div className="flex flex-wrap gap-2">
                {TRAFFIC_SOURCES.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setTrafficSource(s)}
                    className={`rounded-full border px-3.5 py-1.5 text-xs font-semibold capitalize transition-all ${
                      trafficSource === s
                        ? 'border-emerald-300/70 bg-emerald-400/20 text-emerald-100 shadow-[0_0_0_1px_rgba(110,231,183,0.35)]'
                        : 'border-[var(--line)] bg-white/5 text-[var(--muted)] hover:border-emerald-300/40 hover:text-emerald-100'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div>
            <label
              htmlFor="ux-notes"
              className="mb-2 block text-xs font-semibold uppercase tracking-[0.12em] text-[var(--muted)]"
            >
              Notes
            </label>
            <textarea
              id="ux-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Known issues, goals, current conversion rate..."
              className="w-full rounded-xl border border-[var(--line)] bg-[#f6f7fa] px-4 py-3 text-sm text-[var(--text)] placeholder:text-[var(--faint)] outline-none transition-all focus:border-[var(--line)] focus:ring-2 focus:ring-[var(--brand)]/30"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !url}
            className="inline-flex w-full items-center justify-center rounded-xl border border-[var(--line)] bg-gradient-to-r from-cyan-500/80 to-teal-500/80 px-4 py-3 text-sm font-semibold text-[var(--text)] transition-all hover:from-cyan-400 hover:to-teal-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? 'Auditing…' : 'Audit UX & Conversion'}
          </button>
        </form>

        <aside className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl space-y-4">
          <div>
            <h3 className="text-base font-semibold text-[var(--text)]">Audit Blueprint</h3>
            <p className="mt-1 text-xs text-[var(--muted)]">Structured execution path for conversion diagnostics.</p>
          </div>

          <div className="space-y-2.5">
            {UX_AUDIT_PHASES.map((phase, index) => (
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
              <span className="rounded-full border border-[var(--line)] bg-[var(--brand)]/12 px-2.5 py-1 text-[11px] font-medium text-cyan-100 capitalize">
                {pageType}
              </span>
              <span className="rounded-full border border-emerald-300/30 bg-emerald-500/12 px-2.5 py-1 text-[11px] font-medium text-emerald-100 capitalize">
                {trafficSource}
              </span>
            </div>
          </div>
        </aside>
      </div>

      {error && (
        <div className="rounded-xl border border-rose-400/35 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-4">
          {(result.analysis_mode || result.cached) && (
            <div className="flex gap-2 flex-wrap">
              {result.analysis_mode && (
                <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${result.analysis_mode === 'llm' ? 'bg-green-500/15 text-green-300' : 'bg-slate-500/15 text-[var(--muted)]'}`}>
                  {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                </span>
              )}
              {result.cached && (
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-[var(--brand)]/15 text-sky-300">Cached result</span>
              )}
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <div>
              <div className="rounded-xl border border-[var(--line)] bg-white p-4 text-center">
                <div className={`text-4xl font-bold ${scoreColor(uxScore)}`}>{uxScore}</div>
                <div className="mt-1 text-xs uppercase tracking-[0.1em] text-[var(--muted)]">UX Score</div>
              </div>
            </div>
            <div>
              <div className="rounded-xl border border-[var(--line)] bg-white p-4 text-center">
                <div className={`text-4xl font-bold ${scoreColor(cvScore)}`}>{cvScore}</div>
                <div className="mt-1 text-xs uppercase tracking-[0.1em] text-[var(--muted)]">Conversion Score</div>
              </div>
            </div>
            <div>
              <div className="rounded-xl border border-[var(--line)] bg-white p-4 text-center">
                <div
                  className={`text-2xl font-bold ${result.above_fold.load_time_estimate <= 2.5 ? 'text-emerald-300' : 'text-rose-300'}`}
                >
                  {result.above_fold.load_time_estimate}s
                </div>
                <div className="mt-1 text-xs uppercase tracking-[0.1em] text-[var(--muted)]">Est. Load Time</div>
              </div>
            </div>
            <div>
              <div className="rounded-xl border border-[var(--line)] bg-white p-4 text-center">
                <div
                  className={`text-2xl font-bold ${result.above_fold.hero_clarity_score >= 70 ? 'text-emerald-300' : 'text-amber-300'}`}
                >
                  {result.above_fold.hero_clarity_score}
                </div>
                <div className="mt-1 text-xs uppercase tracking-[0.1em] text-[var(--muted)]">Hero Clarity</div>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl">
            <h2 className="mb-3 text-base font-semibold text-[var(--text)]">
              Friction Points ({result.friction_points.length})
            </h2>
            <div className="space-y-3">
              {result.friction_points.map((fp) => (
                <div
                  key={`${fp.location}-${fp.type}-${fp.fix}`}
                  className={`rounded-xl border p-3 ${IMPACT_COLORS[fp.impact] ?? 'border-[var(--line)] bg-white/5 text-[var(--text)]'}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold uppercase">{fp.impact}</span>
                    <span className="rounded bg-[#f6f7fa] px-1.5 py-0.5 font-mono text-xs text-[var(--text)]">
                      {fp.type}
                    </span>
                    <span className="text-xs opacity-80">{fp.location}</span>
                  </div>
                  <p className="mt-1 text-xs opacity-95">→ {fp.fix}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-emerald-300/30 bg-emerald-500/10 p-5">
              <h2 className="mb-2 text-sm font-semibold text-emerald-200">Trust Signals Present</h2>
              <ul className="space-y-1">
                {result.trust_signals.present.map((s) => (
                  <li key={`present-${s}`} className="text-sm text-emerald-100">
                    • {s}
                  </li>
                ))}
              </ul>
            </div>
            <div className="rounded-2xl border border-rose-300/30 bg-rose-500/10 p-5">
              <h2 className="mb-2 text-sm font-semibold text-rose-200">Missing Trust Signals</h2>
              <ul className="space-y-1">
                {result.trust_signals.missing.map((s) => (
                  <li key={`missing-${s}`} className="text-sm text-rose-100">
                    • {s}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl">
            <h2 className="mb-3 text-base font-semibold text-[var(--text)]">Heatmap Insights</h2>
            <ul className="space-y-2">
              {result.heatmap_insights.map((h) => (
                <li key={`heat-${h}`} className="flex items-start gap-2 text-sm text-[var(--text)]">
                  <span className="mt-0.5 text-cyan-300">◉</span>
                  {h}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-[var(--line)] bg-white p-5 md:p-6 backdrop-blur-xl">
            <h2 className="mb-3 text-base font-semibold text-[var(--text)]">A/B Test Ideas</h2>
            <div className="space-y-4">
              {result.ab_test_ideas.map((ab) => (
                <div
                  key={`${ab.element}-${ab.hypothesis}`}
                  className="overflow-hidden rounded-xl border border-[var(--line)]"
                >
                  <div className="bg-[var(--brand)]/15 px-3 py-2 text-xs font-mono text-cyan-100">{ab.element}</div>
                  <div className="grid grid-cols-1 divide-y divide-white/10 md:grid-cols-2 md:divide-x md:divide-y-0">
                    <div className="bg-[#f6f7fa] px-3 py-3">
                      <div className="mb-0.5 text-xs text-[var(--muted)]">Variant A</div>
                      <div className="text-sm text-[var(--text)]">{ab.variant_a}</div>
                    </div>
                    <div className="bg-[#f6f7fa] px-3 py-3">
                      <div className="mb-0.5 text-xs text-[var(--muted)]">Variant B</div>
                      <div className="text-sm text-[var(--text)]">{ab.variant_b}</div>
                    </div>
                  </div>
                  <div className="border-t border-[var(--line)] bg-[var(--brand)]/10 px-3 py-2 text-xs text-cyan-100">
                    Hypothesis: {ab.hypothesis}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <div className="rounded-2xl border border-emerald-300/30 bg-emerald-500/10 p-5 md:p-6">
              <h2 className="mb-3 text-base font-semibold text-emerald-100">Quick Wins</h2>
              <ul className="space-y-2">
                {result.quick_wins.map((w) => (
                  <li key={`win-${w}`} className="flex items-start gap-2 text-sm text-emerald-50">
                    <span className="mt-0.5">✓</span>
                    {w}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl border border-[var(--line)] bg-[var(--brand)]/10 p-5 md:p-6">
              <h2 className="mb-3 text-base font-semibold text-cyan-100">Recommended Tooling</h2>
              <ul className="space-y-2">
                {result.recommended_tools.map((tool) => (
                  <li key={`tool-${tool}`} className="flex items-start gap-2 text-sm text-cyan-50">
                    <span className="mt-0.5">•</span>
                    {tool}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="rounded-xl border border-[var(--line)] bg-white px-4 py-3 text-right text-xs text-[var(--muted)]">
            Audited: {new Date(result.audited_at).toLocaleString()} · ID: {result.analysis_id.slice(0, 8)}
          </div>
        </div>
      )}
    </div>
  );
}
