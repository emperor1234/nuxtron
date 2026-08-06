'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type Alert = {
  severity: 'critical' | 'high' | 'medium' | 'low';
  type: string;
  query: string;
  impact: string;
  recommended_action: string;
};

type Snapshot = {
  query: string;
  current_position: number;
  position_change: number;
  serp_features: string[];
  trend: 'up' | 'down' | 'stable';
};

type RealtimeResult = {
  analysis_id: string;
  volatility_score: number;
  visibility_score: number;
  alerts: Alert[];
  query_snapshots: Snapshot[];
  ai_surface_presence: { chatgpt: number; perplexity: number; google_ai_overview: number };
  anomalies: string[];
  quick_wins: string[];
  recommended_tools: string[];
  monitored_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function RealtimeMonitoringPage() {
  const [domain, setDomain] = useState('');
  const [trackedQueries, setTrackedQueries] = useState('brand query\nmoney query');
  const [lookbackHours, setLookbackHours] = useState(24);
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<RealtimeResult | null>(null);

  async function runMonitor(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const queries = trackedQueries
        .split('\n')
        .map((q) => q.trim())
        .filter(Boolean);
      const data = await apiSend<RealtimeResult>(
        '/seo-platform/realtime/monitor',
        'POST',
        { domain, tracked_queries: queries, lookback_hours: lookbackHours, notes },
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
      setError(e instanceof Error ? e.message : 'Monitoring failed');
    } finally {
      setLoading(false);
    }
  }

  const scoreColor = (s: number) => {
    if (s >= 80) return 'text-green-600';
    if (s >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Real-Time Search & AI Monitoring</h1>
        <p className="text-gray-500 mt-1">
          Track volatility, ranking anomalies, and AI answer-surface visibility shifts.
        </p>
      </div>

      <form onSubmit={runMonitor} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label htmlFor="domain" className="block text-sm font-medium text-gray-700 mb-1">
            Domain *
          </label>
          <input
            id="domain"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            required
            placeholder="example.com"
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="tracked-queries" className="block text-sm font-medium text-gray-700 mb-1">
              Tracked Queries (one per line)
            </label>
            <textarea
              id="tracked-queries"
              value={trackedQueries}
              onChange={(e) => setTrackedQueries(e.target.value)}
              rows={4}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="lookback-hours" className="block text-sm font-medium text-gray-700 mb-1">
              Lookback Hours
            </label>
            <input
              id="lookback-hours"
              type="number"
              min={1}
              max={168}
              value={lookbackHours}
              onChange={(e) => setLookbackHours(Number(e.target.value))}
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
          {loading ? 'Monitoring...' : 'Run Real-Time Monitor'}
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
              <div className={`text-4xl font-bold ${scoreColor(result.volatility_score)}`}>
                {result.volatility_score}
              </div>
              <div className="text-xs text-gray-500">Volatility Score</div>
            </div>
            <div>
              <div className={`text-4xl font-bold ${scoreColor(result.visibility_score)}`}>
                {result.visibility_score}
              </div>
              <div className="text-xs text-gray-500">Visibility Score</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Alerts</h2>
            <div className="space-y-2">
              {result.alerts.map((a, i) => (
                <div key={i} className="border border-gray-200 rounded-lg p-3">
                  <div className="text-xs font-mono text-gray-500">
                    {a.severity.toUpperCase()} · {a.type}
                  </div>
                  <div className="text-sm font-medium text-gray-800">{a.query}</div>
                  <div className="text-xs text-gray-600">{a.impact}</div>
                  <div className="text-xs text-[var(--brand)] mt-1">Action: {a.recommended_action}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Query Snapshots</h2>
            <div className="space-y-2">
              {result.query_snapshots.map((q, i) => (
                <div
                  key={`${q.query}-${q.current_position}-${i}`}
                  className="flex items-center justify-between border border-gray-100 rounded p-2 text-sm"
                >
                  <span>{q.query}</span>
                  <span className="text-gray-500">Pos {q.current_position}</span>
                  <span className={q.position_change < 0 ? 'text-red-600' : 'text-green-600'}>
                    {q.position_change > 0 ? '+' : ''}
                    {q.position_change}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-[var(--muted)] text-right">
            Monitored: {new Date(result.monitored_at).toLocaleString()} · ID: {result.analysis_id.slice(0, 8)}
          </p>
        </div>
      )}
    </div>
  );
}
