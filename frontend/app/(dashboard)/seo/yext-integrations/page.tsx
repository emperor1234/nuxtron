'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type ChecklistItem = {
  provider: string;
  kind: string;
  configured: boolean;
  required_missing: string[];
};

type ChecklistResponse = {
  status: string;
  configured: number;
  total: number;
  configured_pct: number;
  checklist: ChecklistItem[];
};

type PreflightResponse = {
  status: string;
  configured_pct: number;
  missing_provider_steps: Array<{
    provider: string;
    priority: string;
    required_missing: string[];
  }>;
};

type RemediationResponse = {
  status: string;
  remediation_steps: Array<{
    provider: string;
    priority: string;
    required_missing: string[];
  }>;
};

type WiringApplyResponse = {
  status: string;
  checklist_summary?: {
    configured_pct: number;
  };
  gate?: {
    passed: boolean;
    blockers?: string[];
  };
};

export default function YextIntegrationsPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
  const [remediation, setRemediation] = useState<RemediationResponse | null>(null);
  const [wiringApply, setWiringApply] = useState<WiringApplyResponse | null>(null);

  async function refreshAll() {
    setLoading(true);
    setError('');
    try {
      const [checklistData, preflightData] = await Promise.all([
        apiGet<ChecklistResponse>('/search-everywhere/yext/provider-checklist', tenantId),
        apiGet<PreflightResponse>('/search-everywhere/yext/preflight', tenantId),
      ]);
      setChecklist(checklistData);
      setPreflight(preflightData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load integration state');
    } finally {
      setLoading(false);
    }
  }

  async function buildRemediationBundle() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<RemediationResponse>(
        '/search-everywhere/yext/remediation-bundle',
        'POST',
        {
          include_optional: false,
          include_configured: false,
          top_steps: 12,
        },
        tenantId
      );
      setRemediation(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to build remediation bundle');
    } finally {
      setLoading(false);
    }
  }

  async function applyAllMissingWiring() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<WiringApplyResponse>(
        '/search-everywhere/yext/wiring/apply',
        'POST',
        {
          providers: [],
          include_all_missing: true,
          include_optional_auth: true,
        },
        tenantId
      );
      setWiringApply(response);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to apply Yext wiring');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
  }, []);

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">Yext Integrations</p>
        <h1>Provider Wiring And Remediation</h1>
        <p>
          Review provider checklist, preflight gaps, apply tenant wiring, and generate actionable remediation steps.
        </p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button onClick={() => void refreshAll()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button onClick={() => void buildRemediationBundle()} disabled={loading}>
            {loading ? 'Building...' : 'Build Remediation Bundle'}
          </button>
          <button onClick={() => void applyAllMissingWiring()} disabled={loading}>
            {loading ? 'Applying...' : 'Apply All Missing Wiring'}
          </button>
          <a
            className="button"
            href="/api/fastapi/search-everywhere/yext/remediation-bundle/export?format=csv"
            style={{ textDecoration: 'none' }}
          >
            Export CSV
          </a>
        </div>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
        {wiringApply ? (
          <p style={{ marginTop: 10, opacity: 0.85 }}>
            Wiring result: {wiringApply.checklist_summary?.configured_pct ?? '--'}% configured, gate{' '}
            {wiringApply.gate?.passed ? 'PASSED' : 'FAILED'}.
          </p>
        ) : null}
      </section>

      {checklist ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Provider Checklist</h3>
          <p style={{ opacity: 0.8 }}>
            {checklist.configured}/{checklist.total} configured ({checklist.configured_pct}%)
          </p>
          <ul className="bullet-list">
            {checklist.checklist.slice(0, 16).map((item) => (
              <li key={item.provider}>
                <strong>{item.provider}</strong> ({item.kind}) -{' '}
                {item.configured ? 'configured' : `missing: ${item.required_missing.join(', ') || 'oauth dependency'}`}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {preflight ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Preflight</h3>
          <p style={{ opacity: 0.8 }}>Configured: {preflight.configured_pct}%</p>
          <ul className="bullet-list">
            {preflight.missing_provider_steps.slice(0, 12).map((step) => (
              <li key={step.provider}>
                <strong>{step.provider}</strong> [{step.priority}] -{' '}
                {step.required_missing.join(', ') || 'oauth dependency'}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {remediation ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Remediation Bundle</h3>
          <ul className="bullet-list">
            {remediation.remediation_steps.map((step) => (
              <li key={step.provider}>
                <strong>{step.provider}</strong> [{step.priority}] -{' '}
                {step.required_missing.join(', ') || 'oauth dependency'}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </main>
  );
}
