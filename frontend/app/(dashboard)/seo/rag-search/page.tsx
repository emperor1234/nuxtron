'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

function getConfidenceTextColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-green-600';
  if (confidence >= 0.6) return 'text-yellow-600';
  return 'text-red-600';
}

function getRelevanceTextColor(score: number): string {
  if (score >= 0.8) return 'text-green-600';
  if (score >= 0.6) return 'text-yellow-600';
  return 'text-red-500';
}

interface SearchResult {
  rank: number;
  title: string;
  url: string;
  snippet: string;
  relevance_score: number;
  reasoning: string;
}

interface RagResult {
  analysis_id: string;
  query: string;
  search_results: SearchResult[];
  answer_synthesis: string;
  entities_detected: string[];
  intent: string;
  related_queries: string[];
  confidence: number;
  site_domain: string;
  searched_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
}

export default function RagSearchPage() {
  const [query, setQuery] = useState('');
  const [siteDomain, setSiteDomain] = useState('');
  const [contentCorpus, setContentCorpus] = useState('');
  const [topK, setTopK] = useState(5);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RagResult | null>(null);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await apiSend<RagResult>(
        '/seo-platform/rag-search/query',
        'POST',
        { query, site_domain: siteDomain, content_corpus: contentCorpus, top_k: topK, notes },
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
      setError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  const INTENT_COLORS: Record<string, string> = {
    informational: 'bg-blue-100 text-[var(--brand)]',
    navigational: 'bg-teal-100 text-teal-700',
    transactional: 'bg-green-100 text-green-700',
    commercial: 'bg-orange-100 text-orange-700',
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">RAG Site Search Engine</h1>
        <p className="text-gray-500 mt-1">
          Semantic site search powered by retrieval and reasoning — find answers, not just keywords.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label htmlFor="rag-query" className="block text-sm font-medium text-gray-700 mb-1">
            Search Query *
          </label>
          <input
            id="rag-query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
            placeholder="e.g. how does AI SEO improve rankings?"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="rag-domain" className="block text-sm font-medium text-gray-700 mb-1">
              Site Domain (optional)
            </label>
            <input
              id="rag-domain"
              type="text"
              value={siteDomain}
              onChange={(e) => setSiteDomain(e.target.value)}
              placeholder="example.com"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Top-K Results: {topK}</label>
            <input
              type="range"
              min={1}
              max={20}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="w-full mt-2"
            />
          </div>
        </div>
        <div>
          <label htmlFor="rag-corpus" className="block text-sm font-medium text-gray-700 mb-1">
            Content Corpus (optional)
          </label>
          <textarea
            id="rag-corpus"
            value={contentCorpus}
            onChange={(e) => setContentCorpus(e.target.value)}
            rows={5}
            placeholder="Paste your site content, page excerpts, or sitemap data. The AI will perform semantic retrieval over this corpus to find the most relevant results."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
          <p className="text-xs text-[var(--muted)] mt-1">
            Leave empty to get AI-generated representative results based on your domain.
          </p>
        </div>
        <div>
          <label htmlFor="rag-notes" className="block text-sm font-medium text-gray-700 mb-1">
            Notes
          </label>
          <textarea
            id="rag-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Search context, audience, intent..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query}
          className="w-full bg-[var(--brand)] text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-[var(--brand)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Searching…' : 'Run Semantic Search'}
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
          {/* Query meta */}
          <div className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4">
            <div className="flex-1">
              <div className="text-sm font-medium text-gray-700 mb-1">
                Query:{' '}
                <span className="text-[var(--brand)]">
                  {'"'}
                  {result.query}
                  {'"'}
                </span>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${INTENT_COLORS[result.intent] ?? 'bg-gray-100 text-gray-600'}`}
                >
                  {result.intent} intent
                </span>
                {result.entities_detected.map((e) => (
                  <span key={`entity-${e}`} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                    {e}
                  </span>
                ))}
              </div>
            </div>
            <div className="text-center">
              <div className={`text-2xl font-bold ${getConfidenceTextColor(result.confidence)}`}>
                {Math.round(result.confidence * 100)}%
              </div>
              <div className="text-xs text-gray-500">Confidence</div>
            </div>
          </div>

          {/* Answer Synthesis */}
          <div className="bg-blue-50 rounded-xl border border-blue-200 p-6">
            <h2 className="text-sm font-semibold text-blue-800 mb-2">Synthesized Answer</h2>
            <p className="text-sm text-blue-900 leading-relaxed">{result.answer_synthesis}</p>
          </div>

          {/* Search Results */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">
              Search Results ({result.search_results.length})
            </h2>
            <div className="space-y-4">
              {result.search_results.map((r) => (
                <div
                  key={r.url || r.title}
                  className="border border-gray-100 rounded-lg p-4 hover:border-blue-200 transition-colors"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs bg-[var(--brand)] text-white rounded-full w-5 h-5 flex items-center justify-center font-bold flex-shrink-0">
                          {r.rank}
                        </span>
                        <span className="text-sm font-medium text-[var(--brand)]">{r.title}</span>
                      </div>
                      <div className="text-xs text-[var(--muted)] font-mono mb-2">{r.url}</div>
                      <p className="text-sm text-gray-600">{r.snippet}</p>
                      <p className="text-xs text-[var(--muted)] mt-1 italic">Why: {r.reasoning}</p>
                    </div>
                    <div className="text-center flex-shrink-0">
                      <div className={`text-sm font-bold ${getRelevanceTextColor(r.relevance_score)}`}>
                        {Math.round(r.relevance_score * 100)}%
                      </div>
                      <div className="text-xs text-[var(--muted)]">relevance</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Related Queries */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Related Queries</h2>
            <div className="flex flex-wrap gap-2">
              {result.related_queries.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setQuery(q)}
                  className="text-xs bg-gray-100 hover:bg-blue-50 hover:text-[var(--brand)] text-gray-700 px-3 py-1.5 rounded-full border border-gray-200 hover:border-[var(--brand)] transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          <p className="text-xs text-[var(--muted)] text-right">
            Searched: {new Date(result.searched_at).toLocaleString()} · ID: {result.analysis_id.slice(0, 8)}
          </p>
        </div>
      )}
    </div>
  );
}
