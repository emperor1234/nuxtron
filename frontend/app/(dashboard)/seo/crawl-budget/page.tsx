'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type CrawlIssue = { type: string; severity: string; detail: string; fix: string };

type CrawlBudgetResult = {
  analysis_id: string;
  crawl_budget_score: number;
  waste_pct: number;
  priority_buckets: { high: string[]; medium: string[]; low: string[] };
  issues: CrawlIssue[];
  bot_efficiency: { googlebot_efficiency: number; bingbot_efficiency: number };
  exclude_recommendations: string[];
  quick_wins: string[];
  analyzed_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function CrawlBudgetPage() {
  const [domain, setDomain] = useState('');
  const [sampleUrls, setSampleUrls] = useState('/\n/blog/\n/tag/\n/page/2/');
  const [logSnippet, setLogSnippet] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<CrawlBudgetResult | null>(null);

  async function runAnalyze(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const urls = sampleUrls
        .split('\n')
        .map((u) => u.trim())
        .filter(Boolean);
      const data = await apiSend<CrawlBudgetResult>(
        '/seo-platform/crawl-budget/analyze',
        'POST',
        { domain, sample_urls: urls, log_snippet: logSnippet, notes },
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

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Crawl Budget Optimizer</h1>
        <p className="text-gray-500 mt-1">Prioritize high-value URLs and reduce crawl waste from low-value paths.</p>
      </div>

      <form onSubmit={runAnalyze} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label htmlFor="domain" className="block text-sm font-medium text-gray-700 mb-1">
            Domain *
          </label>
          <input
            id="domain"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="sample-urls" className="block text-sm font-medium text-gray-700 mb-1">
              Sample URLs (one per line)
            </label>
            <textarea
              id="sample-urls"
              value={sampleUrls}
              onChange={(e) => setSampleUrls(e.target.value)}
              rows={5}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="log-snippet" className="block text-sm font-medium text-gray-700 mb-1">
              Log Snippet (optional)
            </label>
            <textarea
              id="log-snippet"
              value={logSnippet}
              onChange={(e) => setLogSnippet(e.target.value)}
              rows={5}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono"
            />
          </div>
        </div>
        <div>
          <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-1">
            Notes
          </label>
          <textarea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !domain}
          className="w-full bg-[var(--brand)] text-white py-2 px-4 rounded-lg text-sm font-medium disabled:opacity-50"
        >
          {loading ? 'Analyzing...' : 'Analyze Crawl Budget'}
        </button>
      </form>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">{error}</div>
      )}

      {result && (
        <div className="space-y-4">
          {(result.analysis_mode || result.cached) && (
            <div className="flex gap-2 flex-wrap">
              {result.analysis_mode && (
                <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${result.analysis_mode === 'llm' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                  {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                </span>
              )}
              {result.cached && (
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-sky-100 text-[var(--brand)]">Cached result</span>
              )}
            </div>
          )}
          <div className="bg-white rounded-xl border border-gray-200 p-6 grid grid-cols-2 gap-6 text-center">
            <div>
              <div className="text-4xl font-bold text-gray-800">{result.crawl_budget_score}</div>
              <div className="text-xs text-gray-500">Crawl Budget Score</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-red-600">{result.waste_pct}%</div>
              <div className="text-xs text-gray-500">Estimated Waste</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Issues</h2>
            <div className="space-y-2">
              {result.issues.map((i) => (
                <div key={`${i.type}-${i.detail}`} className="border border-gray-100 rounded-lg p-3">
                  <div className="text-xs font-mono text-gray-500">
                    {i.severity.toUpperCase()} · {i.type}
                  </div>
                  <div className="text-sm text-gray-700">{i.detail}</div>
                  <div className="text-xs text-[var(--brand)]">Fix: {i.fix}</div>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-[var(--muted)] text-right">
            Analyzed: {new Date(result.analyzed_at).toLocaleString()} · ID: {result.analysis_id.slice(0, 8)}
          </p>
        </div>
      )}
    </div>
  );
}
