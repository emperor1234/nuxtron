'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type IntegrationResult = {
  analysis_id: string;
  integration_coverage_score: number;
  connected: string[];
  missing: string[];
  automation_backlog: {
    workflow: string;
    impact: 'high' | 'medium' | 'low';
    complexity: 'low' | 'medium' | 'high';
    owner: string;
  }[];
  connector_health: { connector: string; status: 'ok' | 'degraded' | 'down'; latency_ms: number }[];
  event_flow_risks: string[];
  quick_wins: string[];
  analyzed_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function IntegrationsAutomationPage() {
  const [domain, setDomain] = useState('');
  const [integrations, setIntegrations] = useState('search_console\nanalytics\nslack\nwebhooks');
  const [goals, setGoals] = useState('alerting\nreporting\ncontent_sync');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<IntegrationResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await apiSend<IntegrationResult>(
        '/seo-platform/integrations-automation/analyze',
        'POST',
        {
          domain,
          integrations: integrations
            .split('\n')
            .map((i) => i.trim())
            .filter(Boolean),
          automation_goals: goals
            .split('\n')
            .map((g) => g.trim())
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
      setError(e instanceof Error ? e.message : 'Integrations analysis failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Integrations & Automation Layer</h1>
        <p className="text-gray-500 mt-1">Connector coverage, automation backlog, and event-flow risk analysis.</p>
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
            <label htmlFor="integrations" className="block text-sm font-medium text-gray-700 mb-1">
              Integrations
            </label>
            <textarea
              id="integrations"
              value={integrations}
              onChange={(e) => setIntegrations(e.target.value)}
              rows={4}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label htmlFor="goals" className="block text-sm font-medium text-gray-700 mb-1">
              Automation Goals
            </label>
            <textarea
              id="goals"
              value={goals}
              onChange={(e) => setGoals(e.target.value)}
              rows={4}
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
          {loading ? 'Analyzing...' : 'Analyze Integrations & Automation'}
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
          <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
            <div className="text-4xl font-bold text-gray-800">{result.integration_coverage_score}</div>
            <div className="text-xs text-gray-500">Integration Coverage Score</div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Automation Backlog</h2>
            <div className="space-y-2">
              {result.automation_backlog.map((a) => (
                <div key={`${a.workflow}-${a.owner}`} className="border border-gray-100 rounded-lg p-3 text-sm">
                  <div className="font-medium text-gray-800">{a.workflow}</div>
                  <div className="text-xs text-gray-500">
                    Impact: {a.impact} · Complexity: {a.complexity} · Owner: {a.owner}
                  </div>
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
