'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type KeywordRow = {
  keyword: string;
  monthly_searches: number;
  difficulty: number;
  opportunity_score: number;
  intent: string;
  serp_features: string[];
};

type KeywordResult = {
  analysis_id: string;
  keyword_research_score: number;
  keywords: KeywordRow[];
  semantic_clusters: { cluster: string; keywords: string[]; opportunity: string }[];
  quick_wins: string[];
  featured_snippet_opportunities: string[];
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function KeywordsPage() {
  const [seedKeyword, setSeedKeyword] = useState('crm software');
  const [domain, setDomain] = useState('example.com');
  const [country, setCountry] = useState('US');
  const [count, setCount] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<KeywordResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await apiSend<KeywordResult>(
        '/seo-platform/keywords/research',
        'POST',
        { seed_keyword: seedKeyword.trim(), domain: domain.trim(), country, count },
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Keyword research failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Keyword Research</h1>
        <p className="text-gray-500 mt-1">Intent, clustering, SERP features, and opportunity scoring.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label htmlFor="seed" className="block text-sm font-medium text-gray-700 mb-1">
            Seed Keyword *
          </label>
          <input
            id="seed"
            value={seedKeyword}
            onChange={(e) => setSeedKeyword(e.target.value)}
            required
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
            <label htmlFor="country" className="block text-sm font-medium text-gray-700 mb-1">
              Country
            </label>
            <input
              id="country"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
        </div>
        <div>
          <label htmlFor="count" className="block text-sm font-medium text-gray-700 mb-1">
            Keyword Count
          </label>
          <input
            id="count"
            type="number"
            min={1}
            max={100}
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-[var(--brand)] text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-[var(--brand)] disabled:opacity-50"
        >
          {loading ? 'Researching keywords…' : 'Run Keyword Research'}
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
            <div className="text-4xl font-bold text-gray-800">{result.keyword_research_score}</div>
            <p className="text-xs text-gray-500">Keyword Research Score</p>
          </div>
          {result.keywords?.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 overflow-x-auto">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Keywords</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-500 border-b">
                    <th className="pb-2 pr-4">Keyword</th>
                    <th className="pb-2 pr-4">Volume</th>
                    <th className="pb-2 pr-4">KD</th>
                    <th className="pb-2 pr-4">Opportunity</th>
                    <th className="pb-2">Intent</th>
                  </tr>
                </thead>
                <tbody>
                  {result.keywords.map((k) => (
                    <tr key={k.keyword} className="border-b border-gray-100">
                      <td className="py-2 pr-4 font-medium">{k.keyword}</td>
                      <td className="py-2 pr-4">{k.monthly_searches?.toLocaleString()}</td>
                      <td className="py-2 pr-4">{k.difficulty}</td>
                      <td className="py-2 pr-4">{k.opportunity_score}</td>
                      <td className="py-2 capitalize">{k.intent}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {result.quick_wins?.length > 0 && (
            <div className="bg-green-50 rounded-xl border border-green-200 p-6">
              <h2 className="text-base font-semibold text-green-800 mb-3">Quick Wins</h2>
              <ul className="space-y-2 text-sm text-green-700">
                {result.quick_wins.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
