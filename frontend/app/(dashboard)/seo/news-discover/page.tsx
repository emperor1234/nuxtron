'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type NewsDiscoverResult = {
  analysis_id: string;
  discover_readiness_score: number;
  freshness_score: number;
  top_stories_eligibility: 'low' | 'medium' | 'high';
  headline_improvements: { original: string; improved: string; reason: string }[];
  content_velocity: { past_7d: number; recommended_per_week: number };
  discover_signals: { image_quality: number; author_trust: number; topic_authority: number };
  priority_topics: string[];
  quick_wins: string[];
  analyzed_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function NewsDiscoverPage() {
  const [domain, setDomain] = useState('');
  const [recentHeadlines, setRecentHeadlines] = useState(
    'AI Search Trends 2026\nHow to Win Google Discover\nTop Stories Ranking Signals'
  );
  const [focusTopics, setFocusTopics] = useState('ai seo\ndiscover\nnews freshness');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<NewsDiscoverResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await apiSend<NewsDiscoverResult>(
        '/seo-platform/news-discover/analyze',
        'POST',
        {
          domain,
          recent_headlines: recentHeadlines
            .split('\n')
            .map((h) => h.trim())
            .filter(Boolean),
          focus_topics: focusTopics
            .split('\n')
            .map((t) => t.trim())
            .filter(Boolean),
          notes,
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
      setError(e instanceof Error ? e.message : 'News analysis failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">News SEO & Google Discover</h1>
        <p className="text-gray-500 mt-1">Freshness, Top Stories readiness, and Discover optimization diagnostics.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
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
            <label htmlFor="headlines" className="block text-sm font-medium text-gray-700 mb-1">
              Recent Headlines
            </label>
            <textarea
              id="headlines"
              value={recentHeadlines}
              onChange={(e) => setRecentHeadlines(e.target.value)}
              rows={5}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="topics" className="block text-sm font-medium text-gray-700 mb-1">
              Focus Topics
            </label>
            <textarea
              id="topics"
              value={focusTopics}
              onChange={(e) => setFocusTopics(e.target.value)}
              rows={5}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
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
          {loading ? 'Analyzing...' : 'Analyze News & Discover'}
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
          <div className="bg-white rounded-xl border border-gray-200 p-6 grid grid-cols-3 gap-6 text-center">
            <div>
              <div className="text-4xl font-bold text-gray-800">{result.discover_readiness_score}</div>
              <div className="text-xs text-gray-500">Discover Readiness</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-gray-800">{result.freshness_score}</div>
              <div className="text-xs text-gray-500">Freshness Score</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-[var(--brand)] capitalize">{result.top_stories_eligibility}</div>
              <div className="text-xs text-gray-500">Top Stories Eligibility</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Headline Improvements</h2>
            <div className="space-y-2">
              {result.headline_improvements.map((h) => (
                <div key={`${h.original}-${h.improved}`} className="border border-gray-100 rounded-lg p-3">
                  <div className="text-xs text-red-500">Before: {h.original}</div>
                  <div className="text-sm text-green-700">After: {h.improved}</div>
                  <div className="text-xs text-gray-500">{h.reason}</div>
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
