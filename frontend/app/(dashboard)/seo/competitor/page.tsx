'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

interface CompetitorData {
  domain: string;
  traffic_estimate: number;
  domain_authority: number;
  top_keywords: string[];
  content_velocity: string;
  ai_visibility_score: number;
}

interface SharedKeyword {
  keyword: string;
  your_position: number | null;
  competitor_position: number;
  search_volume: number;
  opportunity_score: number;
}

interface ContentGap {
  topic: string;
  competitor_coverage: string;
  priority: 'high' | 'medium' | 'low';
  content_format: string;
}

interface CompetitorResult {
  analysis_id: string;
  competitive_score: number;
  competitors: CompetitorData[];
  shared_keywords: SharedKeyword[];
  content_gaps: ContentGap[];
  ai_visibility: {
    mention_likelihood: number;
    citation_topics: string[];
    improvement_actions: string[];
  };
  quick_wins: string[];
  domain: string;
  analyzed_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
}

const PRIORITY_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-700 border-red-200',
  medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  low: 'bg-green-100 text-green-700 border-green-200',
};

export default function CompetitorPage() {
  const [domain, setDomain] = useState('');
  const [competitors, setCompetitors] = useState<string[]>(['']);
  const [targetKeyword, setTargetKeyword] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompetitorResult | null>(null);
  const [error, setError] = useState('');

  function addCompetitor() {
    if (competitors.length < 5) setCompetitors((prev) => [...prev, '']);
  }
  function updateCompetitor(i: number, val: string) {
    setCompetitors((prev) => prev.map((c, idx) => (idx === i ? val : c)));
  }
  function removeCompetitor(i: number) {
    setCompetitors((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    const filteredCompetitors = competitors.filter((c) => c.trim());
    try {
      const data = await apiSend<CompetitorResult>(
        '/seo-platform/competitor/analyze',
        'POST',
        { domain, competitors: filteredCompetitors, target_keyword: targetKeyword, notes },
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

  const scoreColor = (s: number) => (s >= 80 ? 'text-green-600' : s >= 60 ? 'text-yellow-600' : 'text-red-600');

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Competitor Intelligence Engine</h1>
        <p className="text-gray-500 mt-1">
          Competitive search, AI visibility, and content gap intelligence for strategic SEO.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Your Domain *</label>
          <input
            type="text"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            required
            placeholder="yourdomain.com"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">Competitors (up to 5)</label>
            {competitors.length < 5 && (
              <button
                type="button"
                onClick={addCompetitor}
                className="text-xs text-[var(--brand)] hover:text-blue-800 font-medium"
              >
                + Add competitor
              </button>
            )}
          </div>
          <div className="space-y-2">
            {competitors.map((c, i) => (
              <div key={`item-${i}`} className="flex items-center gap-2">
                <input
                  type="text"
                  value={c}
                  onChange={(e) => updateCompetitor(i, e.target.value)}
                  placeholder={`competitor${i + 1}.com`}
                  className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
                />
                {competitors.length > 1 && (
                  <button
                    type="button"
                    onClick={() => removeCompetitor(i)}
                    className="text-[var(--muted)] hover:text-red-500 text-sm font-medium px-2"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Target Keyword</label>
          <input
            type="text"
            value={targetKeyword}
            onChange={(e) => setTargetKeyword(e.target.value)}
            placeholder="e.g. ai seo platform"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Market context, goals, specific angles to investigate..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>

        <button
          type="submit"
          disabled={loading || !domain}
          className="w-full bg-[var(--brand)] text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-[var(--brand)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Analyzing competitors…' : 'Run Competitor Intelligence'}
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
          {/* Competitive Score */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
            <div className={`text-5xl font-bold ${scoreColor(result.competitive_score)}`}>
              {result.competitive_score}
            </div>
            <div className="text-sm text-gray-500 mt-1">Competitive Position Score</div>
            <div className="text-xs text-[var(--muted)] mt-0.5">{result.domain}</div>
          </div>

          {/* Competitors Table */}
          {result.competitors.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 overflow-x-auto">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Competitor Overview</h2>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-xs text-gray-500 text-left">
                    <th className="pb-2 pr-4">Domain</th>
                    <th className="pb-2 pr-4">Est. Traffic</th>
                    <th className="pb-2 pr-4">Domain Authority</th>
                    <th className="pb-2 pr-4">Content Velocity</th>
                    <th className="pb-2">AI Visibility</th>
                  </tr>
                </thead>
                <tbody>
                  {result.competitors.map((comp, i) => (
                    <tr key={`item-${i}`} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-2 pr-4 font-mono text-[var(--brand)]">{comp.domain}</td>
                      <td className="py-2 pr-4">{comp.traffic_estimate.toLocaleString()}/mo</td>
                      <td className="py-2 pr-4">
                        <span className={`font-bold ${scoreColor(comp.domain_authority)}`}>
                          {comp.domain_authority}
                        </span>
                      </td>
                      <td className="py-2 pr-4 capitalize">{comp.content_velocity}</td>
                      <td className="py-2">
                        <span className={`font-bold ${scoreColor(comp.ai_visibility_score)}`}>
                          {comp.ai_visibility_score}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Shared Keywords */}
          {result.shared_keywords.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Keyword Opportunities</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-xs text-gray-500 text-left">
                      <th className="pb-2 pr-4">Keyword</th>
                      <th className="pb-2 pr-4">Your Position</th>
                      <th className="pb-2 pr-4">Competitor</th>
                      <th className="pb-2 pr-4">Volume</th>
                      <th className="pb-2">Opportunity</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.shared_keywords.map((kw, i) => (
                      <tr key={`item-${i}`} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="py-2 pr-4 font-medium">{kw.keyword}</td>
                        <td className="py-2 pr-4">
                          {kw.your_position ? (
                            <span className="text-gray-700">#{kw.your_position}</span>
                          ) : (
                            <span className="text-red-500">Unranked</span>
                          )}
                        </td>
                        <td className="py-2 pr-4 text-[var(--brand)]">#{kw.competitor_position}</td>
                        <td className="py-2 pr-4 text-gray-500">{kw.search_volume.toLocaleString()}</td>
                        <td className="py-2">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-gray-100 rounded-full h-1.5 w-20">
                              <div
                                className="h-1.5 rounded-full bg-[var(--brand)]"
                                style={{ width: `${kw.opportunity_score}%` }}
                              />
                            </div>
                            <span className="text-xs font-medium text-[var(--brand)]">{kw.opportunity_score}</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Content Gaps */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Content Gaps</h2>
            <div className="space-y-2">
              {result.content_gaps.map((gap, i) => (
                <div
                  key={`item-${i}`}
                  className={`border rounded-lg p-3 ${PRIORITY_COLORS[gap.priority] ?? 'bg-gray-50'}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold uppercase">{gap.priority}</span>
                    <span className="text-xs font-medium bg-white bg-opacity-60 px-2 py-0.5 rounded">
                      {gap.content_format}
                    </span>
                  </div>
                  <div className="text-sm font-medium">{gap.topic}</div>
                  <div className="text-xs opacity-75 mt-0.5">Competitor covers: {gap.competitor_coverage}</div>
                </div>
              ))}
            </div>
          </div>

          {/* AI Visibility */}
          <div className="bg-blue-50 rounded-xl border border-blue-200 p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="text-2xl">🤖</div>
              <div>
                <h2 className="text-base font-semibold text-blue-900">AI Visibility</h2>
                <div className="text-xs text-[var(--brand)]">
                  How likely is your brand to appear in AI-generated answers?
                </div>
              </div>
              <div className="ml-auto text-center">
                <div
                  className={`text-3xl font-bold ${scoreColor(Math.round(result.ai_visibility.mention_likelihood * 100))}`}
                >
                  {Math.round(result.ai_visibility.mention_likelihood * 100)}%
                </div>
                <div className="text-xs text-[var(--brand)]">mention likelihood</div>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 mt-3">
              <div>
                <div className="text-xs font-semibold text-blue-800 mb-1">Citation Topics</div>
                <div className="flex flex-wrap gap-1.5">
                  {result.ai_visibility.citation_topics.map((t, i) => (
                    <span key={`item-${i}`} className="text-xs bg-blue-100 text-[var(--brand)] px-2 py-0.5 rounded-full">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold text-blue-800 mb-1">Improvement Actions</div>
                <ul className="space-y-1">
                  {result.ai_visibility.improvement_actions.map((a, i) => (
                    <li key={`item-${i}`} className="text-xs text-[var(--brand)]">
                      • {a}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          {/* Quick Wins */}
          <div className="bg-green-50 rounded-xl border border-green-200 p-6">
            <h2 className="text-base font-semibold text-green-800 mb-3">Quick Wins</h2>
            <ul className="space-y-2">
              {result.quick_wins.map((w, i) => (
                <li key={`item-${i}`} className="flex items-start gap-2 text-sm text-green-700">
                  <span className="mt-0.5">✓</span>
                  {w}
                </li>
              ))}
            </ul>
          </div>

          <p className="text-xs text-[var(--muted)] text-right">
            Analyzed: {new Date(result.analyzed_at).toLocaleString()} · ID: {result.analysis_id.slice(0, 8)}
          </p>
        </div>
      )}
    </div>
  );
}
