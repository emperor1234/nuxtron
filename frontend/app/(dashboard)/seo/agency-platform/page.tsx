'use client';

import { useState } from 'react';
import { apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

const STRICT_NO_MOCK_FALSY = new Set(['0', 'false', 'no', 'off']);
const STRICT_NO_MOCK_RAW = (process.env.NEXT_PUBLIC_STRICT_NO_MOCK || '').trim().toLowerCase();
const IS_STRICT_NO_MOCK_MODE = STRICT_NO_MOCK_RAW
  ? !STRICT_NO_MOCK_FALSY.has(STRICT_NO_MOCK_RAW)
  : process.env.NODE_ENV === 'production';

type AgencyResult = {
  analysis_id: string;
  platform_health_score: number;
  workspace_health?: { workspace: string; status: 'healthy' | 'warning' | 'critical'; primary_risk: string }[];
  governance?: { role_coverage_pct?: number; policy_compliance_pct?: number; audit_trail_score?: number };
  sla_risk_accounts?: string[];
  standardization_gaps?: string[];
  automation_opportunities?: string[];
  quick_wins?: string[];
  analyzed_at: string;
  cached?: boolean;
  analysis_mode?: 'llm' | 'heuristic';
  fallback?: boolean;
};

export default function AgencyPlatformPage() {
  const [agencyName, setAgencyName] = useState('');
  const [workspaces, setWorkspaces] = useState('acme\nnorthstar\nvelocity');
  const [governanceFocus, setGovernanceFocus] = useState('rbac and reporting standards');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<AgencyResult | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await apiSend<AgencyResult>(
        '/seo-platform/agency-platform/analyze',
        'POST',
        {
          agency_name: agencyName,
          workspaces: workspaces
            .split('\n')
            .map((w) => w.trim())
            .filter(Boolean),
          governance_focus: governanceFocus,
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
      setError(e instanceof Error ? e.message : 'Agency platform analysis failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Agency & Multi-Tenant Platform</h1>
        <p className="text-gray-500 mt-1">Tenant operations, governance posture, and workspace health diagnostics.</p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div>
          <label htmlFor="agency-name" className="block text-sm font-medium text-gray-700 mb-1">
            Agency Name *
          </label>
          <input
            id="agency-name"
            value={agencyName}
            onChange={(e) => setAgencyName(e.target.value)}
            required
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label htmlFor="workspaces" className="block text-sm font-medium text-gray-700 mb-1">
            Workspaces (one per line)
          </label>
          <textarea
            id="workspaces"
            value={workspaces}
            onChange={(e) => setWorkspaces(e.target.value)}
            rows={4}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label htmlFor="governance-focus" className="block text-sm font-medium text-gray-700 mb-1">
            Governance Focus
          </label>
          <input
            id="governance-focus"
            value={governanceFocus}
            onChange={(e) => setGovernanceFocus(e.target.value)}
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
          disabled={loading || !agencyName}
          className="w-full bg-[var(--brand)] text-white py-2 px-4 rounded-lg text-sm font-medium disabled:opacity-50"
        >
          {loading ? 'Analyzing...' : 'Analyze Agency Platform'}
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
              <div className="text-4xl font-bold text-gray-800">{result.platform_health_score}</div>
              <div className="text-xs text-gray-500">Platform Health</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-800">{result.governance?.role_coverage_pct ?? 0}%</div>
              <div className="text-xs text-gray-500">Role Coverage</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-800">{result.governance?.policy_compliance_pct ?? 0}%</div>
              <div className="text-xs text-gray-500">Policy Compliance</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-gray-800">{result.governance?.audit_trail_score ?? 0}</div>
              <div className="text-xs text-gray-500">Audit Trail</div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-base font-semibold text-gray-800 mb-3">Workspace Health</h2>
            <div className="space-y-2">
              {(result.workspace_health ?? []).map((w) => (
                <div key={`${w.workspace}-${w.status}`} className="border border-gray-100 rounded-lg p-3 text-sm">
                  <div className="font-medium text-gray-800">
                    {w.workspace} · <span className="capitalize">{w.status}</span>
                  </div>
                  <div className="text-xs text-gray-500">Risk: {w.primary_risk}</div>
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
