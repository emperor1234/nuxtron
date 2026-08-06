'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

interface PillarPage {
  title: string;
  slug: string;
  target_keyword: string;
  word_count_target: number;
}

interface ClusterPage {
  pillar: string;
  title: string;
  slug: string;
  target_keyword: string;
  internal_links: string[];
}

interface Hub {
  hub: string;
  spokes: string[];
}

interface TopicalMapResult {
  analysis_id: string;
  topical_authority_score: number;
  pillar_pages: PillarPage[];
  cluster_pages: ClusterPage[];
  silo_structure: { depth: number; hubs: Hub[] };
  content_gaps: string[];
  quick_wins: string[];
  recommended_publishing_order: string[];
  seed_topic: string;
  generated_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
}

export default function TopicalMapPage() {
  const [seedTopic, setSeedTopic] = useState('');
  const [domain, setDomain] = useState('');
  const [depth, setDepth] = useState(2);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TopicalMapResult | null>(null);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await apiSend<TopicalMapResult>(
        '/seo-platform/topical-map/build',
        'POST',
        { seed_topic: seedTopic.trim(), domain: domain.trim(), depth, notes: notes.trim() },
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

  const score = result?.topical_authority_score ?? 0;
  const scoreColor = score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600';

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Topical Map & Silo Builder</h1>
        <p className="text-gray-500 mt-1">Topic clustering, hub-spoke architecture, and editorial map generation.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Seed Topic *</label>
          <input
            type="text"
            value={seedTopic}
            onChange={(e) => setSeedTopic(e.target.value)}
            placeholder="e.g. AI SEO tools"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Domain (optional)</label>
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="e.g. example.com"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Silo Depth</label>
            <select
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
            >
              {[1, 2, 3, 4].map((d) => (
                <option key={d} value={d}>
                  {d} level{d > 1 ? 's' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Additional context..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--brand)]"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !seedTopic}
          className="w-full bg-[var(--brand)] text-white py-2 px-4 rounded-lg text-sm font-medium hover:bg-[var(--brand)] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Building map…' : 'Build Topical Map'}
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
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                    result.analysis_mode === 'llm'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {result.analysis_mode === 'llm' ? 'LLM analysis' : 'Heuristic analysis'}
                </span>
              )}
              {result.cached && (
                <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-sky-100 text-[var(--brand)]">
                  Cached result
                </span>
              )}
            </div>
          )}
          {/* Score */}
          <div className="bg-white rounded-xl border border-gray-200 p-6 flex items-center gap-6">
            <div className="text-center">
              <div className={`text-4xl font-bold ${scoreColor}`}>{score}</div>
              <div className="text-xs text-gray-500 mt-1">Authority Score</div>
            </div>
            <div className="flex-1 grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-xl font-semibold text-gray-800">{result.pillar_pages.length}</div>
                <div className="text-xs text-gray-500">Pillar Pages</div>
              </div>
              <div>
                <div className="text-xl font-semibold text-gray-800">{result.cluster_pages.length}</div>
                <div className="text-xs text-gray-500">Cluster Pages</div>
              </div>
              <div>
                <div className="text-xl font-semibold text-gray-800">{result.silo_structure.depth}</div>
                <div className="text-xs text-gray-500">Silo Depth</div>
              </div>
            </div>
          </div>

          {/* Pillar Pages */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Pillar Pages</h2>
            <div className="space-y-3">
              {result.pillar_pages.map((p, i) => (
                <div
                  key={`item-${i}`}
                  className="flex items-start justify-between border-b border-gray-100 pb-3 last:border-0 last:pb-0"
                >
                  <div>
                    <div className="text-sm font-medium text-gray-800">{p.title}</div>
                    <div className="text-xs text-gray-500 mt-0.5">/{p.slug}</div>
                    <div className="text-xs text-[var(--brand)] mt-0.5">Keyword: {p.target_keyword}</div>
                  </div>
                  <span className="text-xs bg-blue-50 text-[var(--brand)] px-2 py-0.5 rounded font-medium whitespace-nowrap ml-4">
                    {p.word_count_target.toLocaleString()} words
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Silo Structure */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Silo Structure</h2>
            <div className="space-y-4">
              {result.silo_structure.hubs.map((hub, i) => (
                <div key={`item-${i}`}>
                  <div className="text-sm font-semibold text-gray-700 mb-1">🏛 {hub.hub}</div>
                  <div className="ml-4 space-y-1">
                    {hub.spokes.map((spoke, j) => (
                      <div key={`item-${j}`} className="text-xs text-gray-600 flex items-center gap-2">
                        <span className="text-[var(--muted)]">↳</span>/{spoke}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cluster Pages */}
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">
              Cluster Pages ({result.cluster_pages.length})
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 px-3 font-medium text-gray-600">Title</th>
                    <th className="text-left py-2 px-3 font-medium text-gray-600">Slug</th>
                    <th className="text-left py-2 px-3 font-medium text-gray-600">Target Keyword</th>
                    <th className="text-left py-2 px-3 font-medium text-gray-600">Hub</th>
                  </tr>
                </thead>
                <tbody>
                  {result.cluster_pages.map((c, i) => (
                    <tr key={`item-${i}`} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-2 px-3 text-gray-800">{c.title}</td>
                      <td className="py-2 px-3 text-gray-500 font-mono">/{c.slug}</td>
                      <td className="py-2 px-3 text-[var(--brand)]">{c.target_keyword}</td>
                      <td className="py-2 px-3 text-gray-500 text-xs max-w-[150px] truncate">{c.pillar}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Publishing Order + Gaps */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Publishing Order</h2>
              <ol className="space-y-2">
                {result.recommended_publishing_order.map((item, i) => (
                  <li key={`item-${i}`} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-xs bg-[var(--brand)] text-white rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">
                      {i + 1}
                    </span>
                    {item}
                  </li>
                ))}
              </ol>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-semibold text-gray-800 mb-3">Content Gaps</h2>
              <ul className="space-y-2">
                {result.content_gaps.map((gap, i) => (
                  <li key={`item-${i}`} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-orange-500 mt-0.5">⚠</span>
                    {gap}
                  </li>
                ))}
              </ul>
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
            Generated: {new Date(result.generated_at).toLocaleString()} · ID: {result.analysis_id.slice(0, 8)}
          </p>
        </div>
      )}
    </div>
  );
}
