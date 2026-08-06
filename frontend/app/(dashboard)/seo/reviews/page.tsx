'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

interface Theme {
  theme: string;
  sentiment: 'positive' | 'negative' | 'neutral';
  frequency: number;
  example_quote: string;
}

interface ResponseTemplate {
  scenario: string;
  template: string;
}

interface ReviewResult {
  analysis_id: string;
  reputation_score: number;
  sentiment: { overall: string; positive_pct: number; neutral_pct: number; negative_pct: number };
  themes: Theme[];
  review_summary: { total_reviews: number; avg_rating: number; platform_breakdown: Record<string, number> };
  response_templates: ResponseTemplate[];
  reputation_risks: string[];
  quick_wins: string[];
  recommended_tools: string[];
  brand: string;
  platforms: string[];
  analyzed_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
}

const PLATFORMS = ['google', 'trustpilot', 'yelp', 'tripadvisor', 'g2', 'capterra'];

function getSentimentColorClass(sentiment: string): string {
  if (sentiment === 'positive') return 'text-green-600';
  if (sentiment === 'negative') return 'text-red-600';
  return 'text-yellow-600';
}

function getSentimentBgClass(sentiment: string): string {
  if (sentiment === 'positive') return 'bg-green-100 text-green-700';
  if (sentiment === 'negative') return 'bg-red-100 text-red-700';
  return 'bg-gray-100 text-gray-600';
}

export default function ReviewReputationPage() {
  const [brand, setBrand] = useState('');
  const [reviewsText, setReviewsText] = useState('');
  const [platforms, setPlatforms] = useState<string[]>(['google', 'trustpilot']);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [error, setError] = useState('');

  function togglePlatform(p: string) {
    setPlatforms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await apiSend<ReviewResult>(
        '/seo-platform/reviews/analyze',
        'POST',
        { brand: brand.trim(), reviews_text: reviewsText.trim(), platforms, notes: notes.trim() },
        DEFAULT_TENANT_ID
      );
      if (response?.fallback === true && response?.analysis_mode !== 'heuristic') {
        throw new Error(
          IS_STRICT_NO_MOCK_MODE
            ? 'Live LLM backend is unavailable in strict no-mock mode.'
            : 'Live LLM backend is unavailable in fail-closed mode.'
        );
      }
      setResult(response);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  const score = result?.reputation_score ?? 0;
  const getScoreColor = () => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };
  const scoreColor = getScoreColor();

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Review & Reputation Engine</h1>
        <p className="text-gray-500 mt-1">Review mining, sentiment analysis, and reputation response workflows.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label htmlFor="brand-name" className="block text-sm font-medium text-gray-700 mb-1">
            Brand Name *
          </label>
          <input
            id="brand-name"
            type="text"
            value={brand}
            onChange={(e) => setBrand(e.target.value)}
            placeholder="e.g. Nuxtron AI"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
            required
          />
        </div>
        <div>
          <p className="block text-sm font-medium text-gray-700 mb-2">Platforms</p>
          <fieldset className="flex flex-wrap gap-2 border-0 p-0 m-0">
            <legend className="sr-only">Select review platforms</legend>
            {PLATFORMS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => togglePlatform(p)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                  platforms.includes(p)
                    ? 'bg-[var(--brand)] text-white border-[var(--brand)]'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-[var(--brand)]'
                }`}
                aria-pressed={platforms.includes(p)}
              >
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </button>
            ))}
          </fieldset>
        </div>
        <div>
          <label htmlFor="reviews-input" className="block text-sm font-medium text-gray-700 mb-1">
            Paste Reviews (optional)
          </label>
          <textarea
            id="reviews-input"
            value={reviewsText}
            onChange={(e) => setReviewsText(e.target.value)}
            rows={6}
            placeholder={
              'Paste raw review text here. If left empty, AI will generate representative analysis.\n\n"Great product, love the quality!"\n"Shipping was extremely slow, 2 weeks late."\n"Support team resolved my issue quickly."'
            }
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>
        <div>
          <label htmlFor="notes-input" className="block text-sm font-medium text-gray-700 mb-1">
            Notes
          </label>
          <textarea
            id="notes-input"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Additional context..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !brand}
          className="w-full bg-[var(--brand)] text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-[var(--brand)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Analyzing reviews…' : 'Analyze Reviews'}
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
          {/* Score + Sentiment */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex items-center gap-8">
              <div className="text-center">
                <div className={`text-4xl font-bold ${scoreColor}`}>{score}</div>
                <div className="text-xs text-gray-500 mt-1">Reputation Score</div>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-medium text-gray-700">Overall Sentiment:</span>
                  <span className={`text-sm font-bold capitalize ${getSentimentColorClass(result.sentiment.overall)}`}>
                    {result.sentiment.overall}
                  </span>
                </div>
                <div className="flex gap-2 h-4 rounded-full overflow-hidden">
                  <div className="bg-green-500" style={{ width: `${result.sentiment.positive_pct}%` }} />
                  <div className="bg-gray-300" style={{ width: `${result.sentiment.neutral_pct}%` }} />
                  <div className="bg-red-400" style={{ width: `${result.sentiment.negative_pct}%` }} />
                </div>
                <div className="flex gap-4 mt-1 text-xs text-gray-500">
                  <span className="text-green-600">▲ {result.sentiment.positive_pct}% positive</span>
                  <span className="text-gray-500">● {result.sentiment.neutral_pct}% neutral</span>
                  <span className="text-red-500">▼ {result.sentiment.negative_pct}% negative</span>
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-800">{result.review_summary.avg_rating.toFixed(1)}★</div>
                <div className="text-xs text-gray-500">{result.review_summary.total_reviews} reviews</div>
              </div>
            </div>
          </div>

          {/* Themes */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Review Themes</h2>
            <div className="space-y-3">
              {result.themes.map((t) => (
                <div key={`theme-${t.theme}`} className="border border-gray-100 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-800">{t.theme}</span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${getSentimentBgClass(t.sentiment)}`}
                      >
                        {t.sentiment}
                      </span>
                      <span className="text-xs text-gray-500">{t.frequency} mentions</span>
                    </div>
                  </div>
                  <p className="text-xs text-gray-500 italic">
                    {'"'}
                    {t.example_quote}
                    {'"'}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Platform Breakdown */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Platform Breakdown</h2>
            <div className="grid grid-cols-3 gap-3">
              {Object.entries(result.review_summary.platform_breakdown).map(([platform, count]) => (
                <div key={platform} className="bg-gray-50 rounded-lg p-3 text-center">
                  <div className="text-xl font-bold text-gray-800">{count}</div>
                  <div className="text-xs text-gray-500 capitalize mt-0.5">{platform}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Response Templates */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Response Templates</h2>
            <div className="space-y-3">
              {result.response_templates.map((t) => (
                <div key={`template-${t.scenario}`} className="border border-gray-200 rounded-lg p-3">
                  <div className="text-xs font-mono text-[var(--brand)] mb-1">{t.scenario}</div>
                  <p className="text-sm text-gray-700">{t.template}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Risks */}
          {result.reputation_risks.length > 0 && (
            <div className="bg-red-50 rounded-xl border border-red-200 p-6">
              <h2 className="text-base font-semibold text-red-800 mb-3">Reputation Risks</h2>
              <ul className="space-y-2">
                {result.reputation_risks.map((r) => (
                  <li key={r} className="flex items-start gap-2 text-sm text-red-700">
                    <span>⚠</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Quick Wins */}
          <div className="bg-green-50 rounded-xl border border-green-200 p-6">
            <h2 className="text-base font-semibold text-green-800 mb-3">Quick Wins</h2>
            <ul className="space-y-2">
              {result.quick_wins.map((w) => (
                <li key={w} className="flex items-start gap-2 text-sm text-green-700">
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
