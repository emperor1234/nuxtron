'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type KGEntity = { name: string; type: string; confidence: number };
type KGRelationship = { from: string; to: string; type: string; confidence: number };

type KGResult = {
  analysis_id: string;
  graph_health_score: number;
  entities: KGEntity[];
  relationships: KGRelationship[];
  coverage: { entity_pages_pct: number; orphan_entities: number; duplicate_entities: number };
  gaps: string[];
  next_entities_to_build: string[];
  quick_wins: string[];
  analyzed_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function KnowledgeGraphPage() {
  const [domain, setDomain] = useState('');
  const [seedEntities, setSeedEntities] = useState('brand\ncore product\nindustry concept');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<KGResult | null>(null);

  async function runAnalyze(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const seeds = seedEntities
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean);
      const data = await apiSend<KGResult>(
        '/seo-platform/knowledge-graph/analyze',
        'POST',
        { domain, seed_entities: seeds, notes },
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
        <h1 className="text-2xl font-bold text-gray-900">Knowledge Graph Management</h1>
        <p className="text-gray-500 mt-1">
          Analyze entity graph health, relationships, and missing nodes for stronger entity SEO.
        </p>
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
        <div>
          <label htmlFor="seed-entities" className="block text-sm font-medium text-gray-700 mb-1">
            Seed Entities (one per line)
          </label>
          <textarea
            id="seed-entities"
            value={seedEntities}
            onChange={(e) => setSeedEntities(e.target.value)}
            rows={4}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
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
          {loading ? 'Analyzing...' : 'Analyze Knowledge Graph'}
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
          <div className="bg-white rounded-xl border border-gray-200 p-6 grid grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-4xl font-bold text-gray-800">{result.graph_health_score}</div>
              <div className="text-xs text-gray-500">Graph Health</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-800">{result.entities.length}</div>
              <div className="text-xs text-gray-500">Entities</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-800">{result.relationships.length}</div>
              <div className="text-xs text-gray-500">Relations</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-600">{result.coverage.orphan_entities}</div>
              <div className="text-xs text-gray-500">Orphans</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Entities</h2>
            <div className="flex flex-wrap gap-2">
              {result.entities.map((e, i) => (
                <span
                  key={`${e.name}-${e.type}-${i}`}
                  className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full"
                >
                  {e.name} ({e.type})
                </span>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Gaps</h2>
            <ul className="space-y-1">
              {result.gaps.map((g, i) => (
                <li key={`${g}-${i}`} className="text-sm text-gray-700">
                  - {g}
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
