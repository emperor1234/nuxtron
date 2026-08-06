'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

function getBrandScoreColor(score: number): string {
  if (score >= 80) return 'text-green-600';
  if (score >= 60) return 'text-yellow-600';
  return 'text-red-600';
}

function getAlignmentBarColor(pct: number): string {
  if (pct >= 80) return 'bg-green-500';
  if (pct >= 60) return 'bg-yellow-500';
  return 'bg-red-500';
}

interface StyleViolation {
  type: string;
  text: string;
  suggestion: string;
}

interface Change {
  original: string;
  rewritten: string;
  reason: string;
}

interface BrandVoiceResult {
  analysis_id: string;
  brand_alignment_score: number;
  tone_analysis: { detected_tone: string; target_tone: string; alignment_pct: number };
  rewritten_content: string;
  changes: Change[];
  style_violations: StyleViolation[];
  seo_preservation: { keywords_retained: boolean; density_unchanged: boolean; meta_impact: string };
  quick_wins: string[];
  recommended_tools: string[];
  brand_name: string;
  tone: string;
  rewritten_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
}

const TONES = ['professional', 'friendly', 'authoritative', 'conversational', 'playful', 'empathetic', 'bold'];

export default function BrandVoicePage() {
  const [content, setContent] = useState('');
  const [brandName, setBrandName] = useState('');
  const [tone, setTone] = useState('professional');
  const [targetAudience, setTargetAudience] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BrandVoiceResult | null>(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'rewritten' | 'changes'>('rewritten');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await apiSend<BrandVoiceResult>(
        '/seo-platform/brand-voice/rewrite',
        'POST',
        {
          content: content.trim(),
          brand_name: brandName.trim(),
          tone,
          target_audience: targetAudience.trim(),
          notes: notes.trim(),
        },
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

  const score = result?.brand_alignment_score ?? 0;
  const scoreColor = getBrandScoreColor(score);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Brand Voice & Style Engine</h1>
        <p className="text-gray-500 mt-1">Brand-consistent rewriting and tone governance for SEO content.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label htmlFor="bv-content" className="block text-sm font-medium text-gray-700 mb-1">
            Content to Rewrite *
          </label>
          <textarea
            id="bv-content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={8}
            placeholder="Paste the content you want to rewrite in your brand voice..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="bv-brand" className="block text-sm font-medium text-gray-700 mb-1">
              Brand Name
            </label>
            <input
              id="bv-brand"
              type="text"
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              placeholder="e.g. Nuxtron AI"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
            />
          </div>
          <div>
            <label htmlFor="bv-audience" className="block text-sm font-medium text-gray-700 mb-1">
              Target Audience
            </label>
            <input
              id="bv-audience"
              type="text"
              value={targetAudience}
              onChange={(e) => setTargetAudience(e.target.value)}
              placeholder="e.g. B2B marketers, startup founders"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
            />
          </div>
        </div>
        <div>
          <div className="block text-sm font-medium text-gray-700 mb-2">Target Tone</div>
          <div className="flex flex-wrap gap-2">
            {TONES.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setTone(t)}
                className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors capitalize ${
                  tone === t
                    ? 'bg-[var(--brand)] text-white border-[var(--brand)]'
                    : 'bg-white text-gray-600 border-gray-300 hover:border-[var(--brand)]'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label htmlFor="bv-notes" className="block text-sm font-medium text-gray-700 mb-1">
            Notes
          </label>
          <textarea
            id="bv-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Style guidelines, brand keywords to preserve..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !content}
          className="w-full bg-[var(--brand)] text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-[var(--brand)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Rewriting…' : 'Rewrite in Brand Voice'}
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
          {/* Score + Tone Analysis */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-8">
            <div className="text-center">
              <div className={`text-4xl font-bold ${scoreColor}`}>{score}</div>
              <div className="text-xs text-gray-500 mt-1">Brand Alignment</div>
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-500 w-32">Detected Tone:</span>
                <span className="font-medium text-gray-800 capitalize">{result.tone_analysis.detected_tone}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-500 w-32">Target Tone:</span>
                <span className="font-medium text-[var(--brand)] capitalize">{result.tone_analysis.target_tone}</span>
              </div>
              <div>
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>Alignment</span>
                  <span>{result.tone_analysis.alignment_pct}%</span>
                </div>
                <div className="h-2 bg-gray-200 rounded-full">
                  <div
                    className={`h-2 rounded-full ${getAlignmentBarColor(result.tone_analysis.alignment_pct)}`}
                    style={{ width: `${result.tone_analysis.alignment_pct}%` }}
                  />
                </div>
              </div>
            </div>
            <div className="space-y-1 text-center">
              <div
                className={`text-sm font-medium ${result.seo_preservation.keywords_retained ? 'text-green-600' : 'text-red-600'}`}
              >
                {result.seo_preservation.keywords_retained ? '✓' : '✗'} Keywords Retained
              </div>
              <div
                className={`text-sm font-medium ${result.seo_preservation.density_unchanged ? 'text-green-600' : 'text-orange-600'}`}
              >
                {result.seo_preservation.density_unchanged ? '✓' : '~'} Density Unchanged
              </div>
              <div className="text-xs text-gray-500">SEO Impact: {result.seo_preservation.meta_impact}</div>
            </div>
          </div>

          {/* Rewritten Content / Changes Tabs */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <div className="flex border-b border-gray-200 mb-4">
              <button
                onClick={() => setActiveTab('rewritten')}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'rewritten' ? 'border-[var(--brand)] text-[var(--brand)]' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
              >
                Rewritten Content
              </button>
              <button
                onClick={() => setActiveTab('changes')}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'changes' ? 'border-[var(--brand)] text-[var(--brand)]' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
              >
                Changes Made ({result.changes.length})
              </button>
            </div>
            {activeTab === 'rewritten' ? (
              <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                {result.rewritten_content}
              </div>
            ) : (
              <div className="space-y-4">
                {result.changes.map((c) => (
                  <div key={c.original} className="border border-gray-200 rounded-lg overflow-hidden">
                    <div className="bg-red-50 px-3 py-2 border-b border-gray-200">
                      <span className="text-xs text-red-400 font-medium">Before</span>
                      <p className="text-sm text-red-700 mt-0.5">{c.original}</p>
                    </div>
                    <div className="bg-green-50 px-3 py-2 border-b border-gray-200">
                      <span className="text-xs text-green-400 font-medium">After</span>
                      <p className="text-sm text-green-700 mt-0.5">{c.rewritten}</p>
                    </div>
                    <div className="px-3 py-2 bg-gray-50">
                      <p className="text-xs text-gray-500">Reason: {c.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Style Violations */}
          {result.style_violations.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-3">
                Style Violations ({result.style_violations.length})
              </h2>
              <div className="space-y-3">
                {result.style_violations.map((v) => (
                  <div key={`${v.type}-${v.text}`} className="flex items-start gap-3 text-sm">
                    <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded font-mono whitespace-nowrap mt-0.5">
                      {v.type}
                    </span>
                    <div>
                      <span className="line-through text-[var(--muted)] mr-2">
                        {'"'}
                        {v.text}
                        {'"'}
                      </span>
                      <span className="text-green-600">
                        → {'"'}
                        {v.suggestion}
                        {'"'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
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
            Rewritten: {new Date(result.rewritten_at).toLocaleString()} · ID: {result.analysis_id.slice(0, 8)}
          </p>
        </div>
      )}
    </div>
  );
}
