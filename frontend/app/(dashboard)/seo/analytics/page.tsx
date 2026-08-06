'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type AnalyticsResult = {
  analysis_id: string;
  report_score: number;
  domain: string;
  kpi_trends: { kpi: string; trend: string; change_pct: number }[];
  module_highlights: { module: string; impact: string; note: string }[];
  risks: string[];
  next_actions: string[];
  recommended_tools: string[];
  generated_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function AnalyticsReportingPage() {
  const [goal, setGoal] = useState('Increase organic traffic across core product pages');
  const [domain, setDomain] = useState('example.com');
  const [primaryKeyword, setPrimaryKeyword] = useState('crm');
  const [market, setMarket] = useState('us');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<AnalyticsResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await apiSend<AnalyticsResult>(
        '/seo-platform/analytics/report',
        'POST',
        {
          goal: goal.trim(),
          domain: domain.trim(),
          primary_keyword: primaryKeyword.trim(),
          market: market.trim(),
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
      setError(e instanceof Error ? e.message : 'Analytics report failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics, Reporting & Intelligence</h1>
        <p className="text-gray-500 mt-1">Cross-module KPI trends, highlights, risks, and next actions.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label htmlFor="goal" className="block text-sm font-medium text-gray-700 mb-1">
            Goal *
          </label>
          <textarea
            id="goal"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            required
            rows={2}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="domain" className="block text-sm font-medium text-gray-700 mb-1">
              Domain
            </label>
            <input
              id="domain"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="market" className="block text-sm font-medium text-gray-700 mb-1">
              Market
            </label>
            <input
              id="market"
              value={market}
              onChange={(e) => setMarket(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label htmlFor="keyword" className="block text-sm font-medium text-gray-700 mb-1">
            Primary Keyword
          </label>
          <input
            id="keyword"
            value={primaryKeyword}
            onChange={(e) => setPrimaryKeyword(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-[var(--brand)] text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-[var(--brand)] disabled:opacity-50"
        >
          {loading ? 'Generating report…' : 'Generate Analytics Report'}
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
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="text-4xl font-bold text-gray-800">{result.report_score}</div>
            <div className="text-xs text-gray-500">Report Score · {result.domain}</div>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">KPI Trends</h2>
            <div className="space-y-2">
              {result.kpi_trends.map((k) => (
                <div key={k.kpi} className="flex justify-between text-sm border-b border-gray-100 pb-2">
                  <span>{k.kpi}</span>
                  <span className="capitalize">{k.trend} ({k.change_pct}%)</span>
                </div>
              ))}
            </div>
          </div>
          {result.next_actions.length > 0 && (
            <div className="bg-green-50 rounded-xl border border-green-200 p-6">
              <h2 className="text-base font-semibold text-green-800 mb-3">Next Actions</h2>
              <ul className="space-y-2 text-sm text-green-700">
                {result.next_actions.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
