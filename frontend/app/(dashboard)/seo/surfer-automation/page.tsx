'use client';

import { useEffect, useState } from 'react';

import { DEFAULT_TENANT_ID, apiGet, apiSend } from '@/app/lib/platform-api';

type ParityResponse = {
  status: string;
  summary: {
    modules_total: number;
    modules_implemented: number;
    implementation_pct: number;
    integration_configured_units: number;
    integration_total_units: number;
    integration_configured_pct: number;
  };
};

type ChecklistItem = {
  provider: string;
  configured: boolean;
  kind: string;
  required_missing: string[];
};

type ChecklistResponse = {
  status: string;
  configured: number;
  total: number;
  configured_pct: number;
  checklist: ChecklistItem[];
};

type GateResponse = {
  status: string;
  gate: {
    passed: boolean;
    implementation_ok: boolean;
    integration_ok: boolean;
    strict_probe_ok: boolean;
    blockers: string[];
  };
};

export default function SurferAutomationPage() {
  const [tenantId] = useState(DEFAULT_TENANT_ID);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [parity, setParity] = useState<ParityResponse | null>(null);
  const [checklist, setChecklist] = useState<ChecklistResponse | null>(null);
  const [gate, setGate] = useState<GateResponse | null>(null);

  async function refreshAll() {
    setLoading(true);
    setError('');
    try {
      const [parityData, checklistData] = await Promise.all([
        apiGet<ParityResponse>('/search-everywhere/surfer/parity-audit', tenantId),
        apiGet<ChecklistResponse>('/search-everywhere/surfer/provider-checklist', tenantId),
      ]);
      setParity(parityData);
      setChecklist(checklistData);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load Surfer automation data');
    } finally {
      setLoading(false);
    }
  }

  async function runProductionGate() {
    setLoading(true);
    setError('');
    try {
      const response = await apiSend<GateResponse>(
        '/search-everywhere/surfer/production-gate',
        'POST',
        {
          seed_keyword: 'social media management',
          your_domain: 'nuxtron.ai',
          competitor_domains: ['semrush.com', 'ahrefs.com'],
          max_results: 10,
        },
        tenantId
      );
      setGate(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to run production gate');
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
        <p className="eyebrow">Search Everywhere Automation</p>
        <h1>Surfer Automation Command</h1>
        <p>Monitor Surfer parity, provider readiness, and production-gate status in one place.</p>
      </section>

      <section className="card" style={{ marginTop: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ marginTop: 0, marginBottom: 8 }}>Control Actions</h2>
            <p style={{ margin: 0, opacity: 0.82 }}>
              This view calls /search-everywhere/surfer/parity-audit, /provider-checklist, and /production-gate.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button onClick={() => void refreshAll()} disabled={loading}>
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
            <button onClick={() => void runProductionGate()} disabled={loading}>
              {loading ? 'Running...' : 'Run Production Gate'}
            </button>
          </div>
        </div>
        {error ? <p style={{ color: '#f87171' }}>{error}</p> : null}
      </section>

      {parity ? (
        <section className="grid" style={{ marginTop: 20 }}>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Modules</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>
              {parity.summary.modules_implemented}/{parity.summary.modules_total}
            </p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Implementation</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{parity.summary.implementation_pct}%</p>
          </article>
          <article className="card">
            <h3 style={{ marginTop: 0 }}>Integration Wiring</h3>
            <p style={{ fontSize: 28, fontWeight: 700 }}>{parity.summary.integration_configured_pct}%</p>
          </article>
        </section>
      ) : null}

      {checklist ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Provider Checklist</h3>
          <p style={{ opacity: 0.78 }}>
            {checklist.configured}/{checklist.total} configured ({checklist.configured_pct}%)
          </p>
          <ul className="bullet-list">
            {checklist.checklist.slice(0, 12).map((item) => (
              <li key={item.provider}>
                <strong>{item.provider}</strong> ({item.kind}) -{' '}
                {item.configured ? 'configured' : `missing: ${item.required_missing.join(', ')}`}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {gate ? (
        <section className="card" style={{ marginTop: 20 }}>
          <h3 style={{ marginTop: 0 }}>Production Gate</h3>
          <p>
            Status: <strong>{gate.gate.passed ? 'PASSED' : 'FAILED'}</strong>
          </p>
          {!gate.gate.passed ? (
            <ul className="bullet-list">
              {gate.gate.blockers.map((blocker) => (
                <li key={blocker}>{blocker}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </main>
  );
}
