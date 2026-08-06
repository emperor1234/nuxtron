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

type WiringStateResponse = {
  status: string;
  wired_providers: string[];
  wired_count: number;
  missing_providers: string[];
  generated_at?: string;
};

export default function WritesonicIntegrationsPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
  const [remediation, setRemediation] = useState<RemediationResponse | null>(null);
  const [wiringApply, setWiringApply] = useState<WiringApplyResponse | null>(null);
  const [wiringState, setWiringState] = useState<WiringStateResponse | null>(null);

  async function refreshAll() {
    setLoading(true);
    setError('');
    try {
      const [checklistData, preflightData, wiringStateData] = await Promise.all([
        apiGet<ChecklistResponse>('/search-everywhere/writesonic/provider-checklist', tenantId),
        apiGet<PreflightResponse>('/search-everywhere/writesonic/preflight', tenantId),
        apiGet<WiringStateResponse>('/search-everywhere/writesonic/wiring', tenantId),
      ]);
      setChecklist(checklistData);
      setPreflight(preflightData);
      setWiringState(wiringStateData);
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
        '/search-everywhere/writesonic/remediation-bundle',
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
        '/search-everywhere/writesonic/wiring/apply',
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
      setError(e instanceof Error ? e.message : 'Failed to apply Writesonic wiring');
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
        <p className="eyebrow">Writesonic Integrations</p>
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
            href="/api/fastapi/search-everywhere/writesonic/remediation-bundle/export?format=csv"
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

      {wiringState ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Current Wiring State</h3>
          <p style={{ opacity: 0.8 }}>
            Wired providers: <strong>{wiringState.wired_count}</strong> | Missing providers:{' '}
            <strong>{wiringState.missing_providers.length}</strong>
          </p>
          <h4>Wired Providers</h4>
          <ul className="bullet-list">
            {wiringState.wired_providers.map((provider) => (
              <li key={provider}>{provider}</li>
            ))}
          </ul>
          <h4>Missing Providers</h4>
          <ul className="bullet-list">
            {wiringState.missing_providers.map((provider) => (
              <li key={provider}>{provider}</li>
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
